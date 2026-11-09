"""Inert asyncio/process diagnostics; no AgentOps import, request or model call."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import agentops_shutdown_diagnostics_v2 as diagnostic


class ShutdownDiagnosticV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'diagnostic'

    def events(self):
        return [json.loads(line) for line in (self.output / 'lifecycle.jsonl').read_text().splitlines()]

    def test_return_and_normal_pending_task_cancellation_are_preserved(self):
        cancelled = []

        async def pending():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)

        async def entry():
            asyncio.create_task(pending())
            await asyncio.sleep(0)
            return 42

        self.assertEqual(diagnostic.run_observed(entry, self.output), 42)
        self.assertEqual(cancelled, [True])
        events = self.events()
        self.assertEqual(events[-1]['phase'], 'asyncio_run_exited')
        self.assertEqual(events[-1]['outcome'], 'returned')
        observed = next(row for row in events if row['phase'] == 'coroutine_finished')
        self.assertTrue(any(not row['current'] for row in observed['tasks']))
        self.assertEqual((self.output / 'teardown-stacks.txt').read_bytes(), b'')

    def test_events_bind_process_and_order(self):
        async def entry():
            return None
        diagnostic.run_observed(entry, self.output)
        events = self.events()
        self.assertEqual([row['phase'] for row in events], [
            'asyncio_run_entered', 'teardown_watchdog_armed',
            'coroutine_finished', 'asyncio_run_exited'])
        self.assertEqual([row['sequence'] for row in events], [1, 2, 3, 4])
        self.assertTrue(all(row['pid'] == os.getpid() and
                            row['schema_version'] == 'agentops-shutdown-event/2' for row in events))
        self.assertTrue(all(left['monotonic_ns'] < right['monotonic_ns']
                            for left, right in zip(events, events[1:])))

    def test_snapshot_and_cancellation_failures_preserve_original_exception(self):
        marker = RuntimeError('inert application error')
        original_cancel = diagnostic.faulthandler.cancel_dump_traceback_later

        async def entry():
            raise marker

        def failed_cancel():
            original_cancel()
            raise OSError('inert diagnostic failure')

        try:
            with patch.object(diagnostic, 'thread_state', side_effect=OSError('inert snapshot failure')), \
                    patch.object(diagnostic.faulthandler, 'cancel_dump_traceback_later', failed_cancel), \
                    self.assertRaises(RuntimeError) as caught:
                diagnostic.run_observed(entry, self.output)
            self.assertIs(caught.exception, marker)
            stages = {row['stage'] for row in self.events()[-1]['diagnostic_errors']}
            self.assertTrue({'coroutine_thread_snapshot', 'exit_thread_snapshot', 'cancel_watchdog'} <= stages)
        finally:
            original_cancel()
            while diagnostic._UNRELEASED_TRACES:
                diagnostic._UNRELEASED_TRACES.pop().close()

    def test_failed_arming_is_recorded_without_changing_result(self):
        async def entry():
            return 3
        with patch.object(diagnostic.faulthandler, 'dump_traceback_later', side_effect=OSError('inert')):
            self.assertEqual(diagnostic.run_observed(entry, self.output), 3)
        events = self.events()
        self.assertNotIn('teardown_watchdog_armed', [row['phase'] for row in events])
        self.assertIn({'stage': 'arm_watchdog', 'error_type': 'OSError'}, events[-1]['diagnostic_errors'])

    def test_original_exception_propagates(self):
        marker = RuntimeError('inert sentinel')

        async def entry():
            raise marker

        with self.assertRaises(RuntimeError) as caught:
            diagnostic.run_observed(entry, self.output)
        self.assertIs(caught.exception, marker)
        self.assertEqual(self.events()[-1]['outcome'], 'raised')

    def test_diagnostic_write_failure_does_not_replace_original_exception(self):
        marker = RuntimeError('inert sentinel')

        async def entry():
            raise marker

        original = Path.open

        def opened(path, *args, **kwargs):
            if path.name == 'lifecycle.jsonl':
                raise OSError('inert unwritable event log')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'open', opened), self.assertRaises(RuntimeError) as caught:
            diagnostic.run_observed(entry, self.output)
        self.assertIs(caught.exception, marker)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / 'retained.txt'
        marker.write_text('retained')
        with self.assertRaises(FileExistsError):
            diagnostic.run_observed(lambda: None, self.output)
        self.assertEqual(marker.read_text(), 'retained')

    def test_invalid_delay_does_not_create_output(self):
        for value in [0, -1, float('inf'), float('nan'), True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                diagnostic.run_observed(lambda: None, self.output, watchdog_seconds=value)
        self.assertFalse(self.output.exists())

    def test_observations_exclude_local_values_and_task_names(self):
        secret = 'INERT_PRIVATE_VALUE_DO_NOT_CAPTURE'

        async def entry():
            local_value = secret
            asyncio.current_task().set_name(secret)
            return bool(local_value)

        self.assertTrue(diagnostic.run_observed(entry, self.output))
        self.assertNotIn(secret, (self.output / 'lifecycle.jsonl').read_text())

    def test_stalled_cancellation_dumps_stacks_without_ending_process(self):
        # This is a deliberately inert cancellation-resistant coroutine, not a
        # claim about the cause of B7. Only this owned test child is terminated.
        program = '''
import asyncio,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from agentops_shutdown_diagnostics_v2 import run_observed
async def pending():
    while True:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
async def entry():
    asyncio.create_task(pending())
    await asyncio.sleep(0)
run_observed(entry,Path(sys.argv[2]),watchdog_seconds=0.15)
'''
        child = subprocess.Popen([sys.executable, '-B', '-c', program,
                                  str(ROOT / 'scripts'), str(self.output)],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            trace = self.output / 'teardown-stacks.txt'
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    self.fail('Inert child exited unexpectedly: ' + child.stderr.read().decode())
                if trace.exists() and b'Timeout' in trace.read_bytes():
                    break
                time.sleep(0.05)
            self.assertIsNone(child.poll(), 'Observer must not terminate the process')
            self.assertIn(b'Timeout', trace.read_bytes())
            self.assertIn(b'asyncio', trace.read_bytes())
            self.assertNotIn('asyncio_run_exited', [row['phase'] for row in self.events()])
        finally:
            if child.poll() is None:
                child.terminate()
            child.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
