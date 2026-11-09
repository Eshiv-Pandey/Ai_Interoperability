"""Inert readiness/startup observation; no AgentOps imports or real launches."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import agentops_startup_diagnostics_v1 as diagnostic


class StartupDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base / 'diagnostic'
        self.ready = self.base / 'ready.json'

    def events(self, output=None):
        return [json.loads(line) for line in ((output or self.output) / 'lifecycle.jsonl').read_text().splitlines()]

    def test_readiness_stops_and_closes_noninheritable_descriptors(self):
        observer = diagnostic.StartupObserver(self.output, self.ready)
        descriptors = (observer._trace_fd, observer._events_fd)
        self.assertTrue(observer._thread.daemon)
        self.assertTrue(all(not os.get_inheritable(fd) for fd in descriptors))
        self.ready.write_text('{}')
        self.assertTrue(observer._done.wait(2))
        self.assertTrue(observer.stop())
        self.assertFalse(observer._thread.is_alive())
        for fd in descriptors:
            with self.assertRaises(OSError): os.fstat(fd)
        rows = self.events()
        self.assertEqual([r['phase'] for r in rows], ['startup_observer_armed', 'startup_monitor_started',
                         'readiness_observed', 'startup_observer_stopped'])
        self.assertEqual(rows[-1]['reason'], 'readiness_observed')
        self.assertEqual((self.output / 'startup-stacks.txt').read_bytes(), b'')

    def test_wrapper_stop_is_clean_idempotent_and_does_not_touch_global_timer(self):
        with patch.object(diagnostic.faulthandler, 'dump_traceback_later') as arm, \
                patch.object(diagnostic.faulthandler, 'cancel_dump_traceback_later') as cancel:
            observer = diagnostic.StartupObserver(self.output, self.ready)
            self.assertTrue(observer.stop())
            self.assertTrue(observer.stop())
            arm.assert_not_called()
            cancel.assert_not_called()
        rows = self.events()
        self.assertEqual(rows[-1]['phase'], 'startup_observer_stopped')
        self.assertEqual(rows[-1]['reason'], 'wrapper_finished')
        self.assertEqual([r['sequence'] for r in rows], list(range(1, len(rows) + 1)))
        self.assertTrue(all(r['pid'] == os.getpid() and r['schema_version'] == 'agentops-startup-event/1' for r in rows))
        self.assertTrue(all(a['monotonic_ns'] < b['monotonic_ns'] for a, b in zip(rows, rows[1:])))

    def test_pre_readiness_stall_is_sampled_without_ending_process_or_exposing_locals(self):
        program = '''
import sys,time,threading
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from agentops_startup_diagnostics_v1 import StartupObserver
observer=StartupObserver(Path(sys.argv[2]),Path(sys.argv[3]),interval_seconds=0.1,poll_seconds=0.01)
def constructed_startup_stall():
    secret='INERT_PRIVATE_LOCAL_MUST_NOT_BE_CAPTURED'
    threading.current_thread().name=secret
    while True: time.sleep(1)
constructed_startup_stall()
'''
        child = subprocess.Popen([sys.executable, '-B', '-c', program, str(ROOT / 'scripts'),
                                  str(self.output), str(self.ready)], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            trace = self.output / 'startup-stacks.txt'
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    self.fail('Constructed child exited: ' + child.stderr.read().decode(errors='replace'))
                data = trace.read_bytes() if trace.exists() else b''
                if data.count(b'Startup traceback') >= 2 and b'constructed_startup_stall' in data:
                    break
                time.sleep(0.025)
            self.assertIsNone(child.poll())
            self.assertGreaterEqual(data.count(b'Startup traceback'), 2)
            self.assertIn(b'constructed_startup_stall', data)
            self.assertNotIn(b'INERT_PRIVATE_LOCAL_MUST_NOT_BE_CAPTURED', data)
            self.assertNotIn('startup_observer_stopped', [r['phase'] for r in self.events()])
        finally:
            if child.poll() is None: child.terminate()
            child.communicate(timeout=10)
        self.assertNotEqual(child.returncode, 0)

    def test_dump_failure_is_recorded_and_monitor_can_stop(self):
        with patch.object(diagnostic.faulthandler, 'dump_traceback', side_effect=OSError('private error text')):
            observer = diagnostic.StartupObserver(self.output, self.ready, interval_seconds=0.01, poll_seconds=0.005)
            deadline = time.monotonic() + 2
            while not observer.errors and time.monotonic() < deadline: time.sleep(0.01)
            self.assertTrue(observer.stop())
        self.assertIn({'stage': 'dump_startup_stack', 'error_type': 'OSError'}, self.events()[-1]['diagnostic_errors'])
        self.assertNotIn('private error text', (self.output / 'lifecycle.jsonl').read_text())

    def test_timed_out_stop_does_not_recycle_a_descriptor_still_used_by_daemon(self):
        entered, release = threading.Event(), threading.Event()
        def held_dump(**kwargs):
            entered.set()
            release.wait(2)
        observer = None
        try:
            with patch.object(diagnostic.faulthandler, 'dump_traceback', held_dump):
                observer = diagnostic.StartupObserver(self.output, self.ready, interval_seconds=0.01,
                    poll_seconds=0.005, stop_wait_seconds=0.02)
            descriptor = observer._trace_fd
            self.assertTrue(entered.wait(2))
            self.assertFalse(observer.stop())
            os.fstat(descriptor)
            release.set()
            self.assertTrue(observer._done.wait(2))
            self.assertTrue(observer.stop())
            with self.assertRaises(OSError): os.fstat(descriptor)
        finally:
            release.set()
            if observer is not None: observer.stop()

    def test_existing_allocation_and_invalid_intervals_are_refused(self):
        for value in (0, -1, True, float('inf'), float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                diagnostic.StartupObserver(self.output, self.ready, interval_seconds=value)
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        marker = self.output / 'retained.txt'
        marker.write_text('retained')
        with self.assertRaises(FileExistsError): diagnostic.StartupObserver(self.output, self.ready)
        self.assertEqual(list(self.output.iterdir()), [marker])
        self.assertEqual(marker.read_text(), 'retained')

    def test_partial_descriptor_allocation_is_closed_on_failure(self):
        original = os.open
        acquired = []
        def open_once(path, *args):
            if acquired: raise OSError('inert allocation error')
            fd = original(path, *args)
            acquired.append(fd)
            return fd
        with patch.object(diagnostic.os, 'open', open_once), self.assertRaises(OSError):
            diagnostic.StartupObserver(self.output, self.ready)
        with self.assertRaises(OSError): os.fstat(acquired[0])

    def test_thread_construction_failure_closes_descriptors_before_any_start(self):
        original_open = os.open
        acquired = []
        def opened(path, *args):
            descriptor = original_open(path, *args)
            acquired.append(descriptor)
            return descriptor
        with patch.object(diagnostic.os, 'open', opened), \
                patch.object(diagnostic.threading, 'Thread', side_effect=RuntimeError('inert construction failure')):
            with self.assertRaisesRegex(RuntimeError, 'inert construction failure'):
                diagnostic.StartupObserver(self.output, self.ready)
        self.assertEqual(len(acquired), 2)
        for descriptor in acquired:
            with self.assertRaises(OSError): os.fstat(descriptor)
        self.assertEqual(self.events()[-1]['reason'], 'daemon_construction_failed')

    def test_start_then_raise_does_not_close_descriptors_owned_by_active_writer(self):
        entered, release = threading.Event(), threading.Event()
        descriptor = []
        original_start = threading.Thread.start
        owner = None
        def held_dump(**kwargs):
            descriptor.append(kwargs['file'])
            entered.set()
            release.wait(10)
            os.write(kwargs['file'], b'inert writer completed\n')
        def started_then_interrupted(thread):
            original_start(thread)
            if not entered.wait(10): raise AssertionError('Inert daemon did not enter its dump')
            raise KeyboardInterrupt('inert interruption after daemon launch')
        try:
            with patch.object(diagnostic.faulthandler, 'dump_traceback', held_dump), \
                    patch.object(diagnostic.threading.Thread, 'start', started_then_interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    diagnostic.StartupObserver(self.output, self.ready, interval_seconds=0.01, poll_seconds=0.005)
            owner = diagnostic._UNCONFIRMED_STARTS[-1]
            self.assertTrue(owner._thread.is_alive())
            os.fstat(descriptor[0])
            unrelated = self.base / 'unrelated.txt'
            with unrelated.open('xb') as handle:
                self.assertNotEqual(handle.fileno(), descriptor[0])
                handle.write(b'unrelated')
                release.set()
                self.assertTrue(owner._done.wait(2))
            self.assertEqual(unrelated.read_bytes(), b'unrelated')
            self.assertIn(b'inert writer completed', (self.output / 'startup-stacks.txt').read_bytes())
            self.assertEqual(self.events()[-1]['reason'], 'daemon_start_failed')
            with self.assertRaises(OSError): os.fstat(descriptor[0])
        finally:
            release.set()
            if owner is not None:
                owner._thread.join(timeout=2)
                if owner._done.is_set(): diagnostic._UNCONFIRMED_STARTS.remove(owner)

    def run_wrapper(self, failure):
        stubs = self.base / 'stubs'
        stubs.mkdir()
        target = self.base / 'runs/agentops-http-control/inert/service'
        target.mkdir(parents=True)
        (stubs / 'agentops_native_probe_v2.py').write_text(
            'from pathlib import Path\nWORKSPACE=Path(' + repr(str(self.base)) + ')\n'
            'def within(path,root):\n'
            '    assert path.resolve().is_relative_to(root.resolve())\n'
            '    return path.resolve()\n')
        (stubs / 'serve_agentops_bridge_v1.py').write_text('''
import asyncio,json
from pathlib import Path
TARGET=Path(''' + repr(str(target)) + ''')
phases=[json.loads(x)['phase'] for x in (TARGET/'startup-diagnostics/lifecycle.jsonl').read_text().splitlines()]
assert 'startup_observer_armed' in phases
async def serve(output,port):
    assert output==TARGET and port==18764
''' + ("    raise RuntimeError('inert original startup failure')\n" if failure else
       "    (TARGET/'service-ready.json').write_text('{}')\n    await asyncio.sleep(0.1)\n    return 42\n"))
        program = '''
import runpy,sys
sys.path[:0]=[sys.argv[1],sys.argv[2]]
entrypoint=sys.argv[3]
sys.argv=[entrypoint,'--output',sys.argv[4],'--port','18764']
runpy.run_path(entrypoint,run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-B', '-c', program, str(stubs), str(ROOT / 'scripts'),
            str(ROOT / 'scripts/serve_agentops_bridge_diagnostic_v4.py'), str(target)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
        return target, result

    def test_v4_readiness_stops_startup_before_preserved_teardown_and_exit_observers(self):
        target, result = self.run_wrapper(False)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        startup = self.events(target / 'startup-diagnostics')
        old = self.events(target / 'shutdown-diagnostics')
        late = self.events(target / 'interpreter-exit-diagnostics')
        self.assertEqual(startup[-1]['reason'], 'readiness_observed')
        self.assertLess(startup[-1]['monotonic_ns'], old[1]['monotonic_ns'])
        self.assertEqual(old[-1]['phase'], 'asyncio_run_exited')
        self.assertEqual(late[-1]['phase'], 'atexit_late_boundary')

    def test_v4_failure_preserves_original_exception_and_stops_before_teardown(self):
        target, result = self.run_wrapper(True)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'RuntimeError: inert original startup failure', result.stderr)
        startup = self.events(target / 'startup-diagnostics')
        old = self.events(target / 'shutdown-diagnostics')
        late = self.events(target / 'interpreter-exit-diagnostics')
        self.assertEqual(startup[-1]['reason'], 'service_coroutine_finished')
        self.assertLess(startup[-1]['monotonic_ns'], old[1]['monotonic_ns'])
        self.assertEqual(old[-1]['outcome'], 'raised')
        self.assertEqual(late[1]['outcome'], 'raised')


if __name__ == '__main__':
    unittest.main()
