"""Inert asyncio/process diagnostics; no AgentOps import, request or model call."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import agentops_shutdown_diagnostics_v1 as diagnostic


class ShutdownDiagnosticTests(unittest.TestCase):
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
from agentops_shutdown_diagnostics_v1 import run_observed
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
