"""Constructed subprocess exit stages only; no AgentOps runtime is imported."""
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
import agentops_interpreter_exit_diagnostics_v1 as diagnostic


BOOT = '''
import atexit, asyncio, gc, json, os, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from agentops_interpreter_exit_diagnostics_v1 import InterpreterExitObserver
output = Path(sys.argv[2])
observer = InterpreterExitObserver(output, watchdog_seconds=0.1)
'''


class InterpreterExitDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base / 'diagnostic'

    def events(self, output=None):
        return [json.loads(line) for line in ((output or self.output) / 'lifecycle.jsonl').read_text().splitlines()]

    def child(self, code):
        return subprocess.Popen([sys.executable, '-B', '-c', BOOT + code,
                                 str(ROOT / 'scripts'), str(self.output)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

    def completed(self, code, expected=0):
        child = self.child(code)
        try:
            stdout, stderr = child.communicate(timeout=10)
            self.assertEqual(child.returncode, expected, stderr.decode(errors='replace'))
            return stdout, stderr
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=10)

    def observe_hang(self, code, function, early, late):
        child = self.child(code)
        try:
            trace = self.output / 'interpreter-exit-stacks.txt'
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    self.fail('Constructed child exited: ' + child.stderr.read().decode(errors='replace'))
                raw = trace.read_bytes() if trace.exists() else b''
                if raw.count(b'Timeout') >= 2 and function.encode() in raw:
                    break
                time.sleep(0.025)
            self.assertIsNone(child.poll(), 'Diagnostic must never terminate its process')
            raw = trace.read_bytes()
            self.assertGreaterEqual(raw.count(b'Timeout'), 2, raw.decode(errors='replace'))
            self.assertIn(function.encode(), raw)
            phases = [row['phase'] for row in self.events()]
            self.assertEqual('atexit_early_boundary' in phases, early)
            self.assertEqual('atexit_late_boundary' in phases, late)
            self.assertNotIn(b'INERT_LOCAL_VALUE_NOT_FOR_CAPTURE', raw)
        finally:
            if child.poll() is None:
                child.terminate()
            child.communicate(timeout=10)
        self.assertNotEqual(child.returncode, 0, 'Parent-owned termination remains a failed process exit')

    def test_clean_exit_retains_ordered_markers_and_zero_process_status(self):
        stdout, stderr = self.completed('''
async def entry(): return 42
value = asyncio.run(entry())
observer.arm()
print(value)
''')
        self.assertEqual(stdout.strip(), b'42')
        self.assertEqual(stderr, b'')
        events = self.events()
        self.assertEqual([r['phase'] for r in events], [
            'interpreter_exit_observer_installed', 'entrypoint_boundary',
            'interpreter_exit_watchdog_armed', 'atexit_early_boundary', 'atexit_late_boundary'])
        self.assertEqual([r['sequence'] for r in events], list(range(1, 6)))
        self.assertEqual(len({r['pid'] for r in events}), 1)
        self.assertTrue(all(r['schema_version'] == 'agentops-interpreter-exit-event/1' for r in events))
        self.assertTrue(all(a['monotonic_ns'] < b['monotonic_ns'] for a, b in zip(events, events[1:])))
        self.assertTrue(all(not r['diagnostic_errors'] for r in events))
        self.assertEqual((self.output / 'interpreter-exit-stacks.txt').read_bytes(), b'')

    def test_watchdog_observes_constructed_atexit_hang_without_exiting(self):
        self.observe_hang('''
def constructed_atexit_hang():
    local_value = 'INERT_LOCAL_VALUE_NOT_FOR_CAPTURE'
    while True: time.sleep(1)
atexit.register(constructed_atexit_hang)
asyncio.run(asyncio.sleep(0))
observer.arm()
''', 'constructed_atexit_hang', early=True, late=False)

    def test_watchdog_observes_thread_join_before_atexit(self):
        self.observe_hang('''
import threading
def constructed_thread_wait():
    while True: time.sleep(1)
threading.Thread(target=constructed_thread_wait, daemon=False).start()
asyncio.run(asyncio.sleep(0))
observer.arm()
''', 'constructed_thread_wait', early=False, late=False)

    def test_watchdog_survives_late_marker_into_constructed_finalizer(self):
        self.observe_hang('''
class ConstructedFinalizer:
    def __del__(self):
        # Windows closes time.sleep's timer handle before this late phase.
        # Pure Python avoids depending on a module or OS service being alive.
        while True: pass
constructed_finalizer = ConstructedFinalizer()
asyncio.run(asyncio.sleep(0))
observer.arm()
''', '__del__', early=True, late=True)

    def test_raw_trace_descriptor_survives_gc_and_unrelated_file_opens(self):
        self.observe_hang('''
assert not os.get_inheritable(observer.trace_fd)
assert not os.get_inheritable(observer.events_fd)
stat = os.fstat(observer.trace_fd)
trace_identity = (stat.st_dev, stat.st_ino)
def constructed_descriptor_hang():
    gc.collect()
    other = [open(output.parent / ('unrelated-' + str(n)), 'xb') for n in range(64)]
    stat = os.fstat(observer.trace_fd)
    assert (stat.st_dev, stat.st_ino) == trace_identity
    for stream in other: stream.write(b'unrelated'); stream.close()
    while True: time.sleep(1)
atexit.register(constructed_descriptor_hang)
observer.arm()
''', 'constructed_descriptor_hang', early=True, late=False)
        self.assertTrue(all(p.read_bytes() == b'unrelated' for p in self.base.glob('unrelated-*')))

    def test_failed_arm_records_error_and_preserves_exception_status(self):
        _, stderr = self.completed('''
def failed_arm(*args, **kwargs): raise OSError('inert diagnostic failure')
observer._arm_watchdog = failed_arm
try:
    raise RuntimeError('inert original failure')
finally:
    observer.arm(outcome='raised')
''', expected=1)
        self.assertIn(b'RuntimeError: inert original failure', stderr)
        events = self.events()
        self.assertIn('interpreter_exit_watchdog_unavailable', [r['phase'] for r in events])
        self.assertEqual(events[1]['outcome'], 'raised')
        self.assertIn({'stage': 'arm_interpreter_exit_watchdog', 'error_type': 'OSError'}, events[-1]['diagnostic_errors'])

    def test_event_write_failure_does_not_replace_original_exception(self):
        _, stderr = self.completed('''
def failed_write(*args): raise OSError('inert event failure')
observer._write = failed_write
try:
    raise RuntimeError('inert original failure')
finally:
    observer.arm(outcome='raised')
''', expected=1)
        self.assertIn(b'RuntimeError: inert original failure', stderr)
        self.assertNotIn(b'inert event failure', stderr)

    def test_duplicate_observer_does_not_allocate_or_replace_watchdog(self):
        self.completed('''
try:
    InterpreterExitObserver(output.parent / 'second')
except RuntimeError:
    pass
else:
    raise AssertionError('second observer was accepted')
assert not (output.parent / 'second').exists()
observer.arm()
try:
    observer.arm()
except RuntimeError:
    pass
else:
    raise AssertionError('second handoff was accepted')
''')
        self.assertEqual(sum(r['phase'] == 'interpreter_exit_watchdog_armed' for r in self.events()), 1)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / 'retained.txt'
        marker.write_text('retained')
        with self.assertRaises(FileExistsError):
            diagnostic.InterpreterExitObserver(self.output)
        self.assertEqual(marker.read_text(), 'retained')
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_invalid_delay_does_not_allocate_files(self):
        for value in (0, -1, float('inf'), float('nan'), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                diagnostic.InterpreterExitObserver(self.output, watchdog_seconds=value)
        self.assertFalse(self.output.exists())

    def test_partial_initialization_closes_acquired_descriptors(self):
        acquired = []
        original_open = os.open
        def fail_second(path, *args):
            if acquired:
                raise OSError('inert second-open failure')
            descriptor = original_open(path, *args)
            acquired.append(descriptor)
            return descriptor
        with patch.object(diagnostic.os, 'open', fail_second), self.assertRaises(OSError):
            diagnostic.InterpreterExitObserver(self.output)
        self.assertEqual(len(acquired), 1)
        with self.assertRaises(OSError):
            os.fstat(acquired[0])
        self.assertIsNone(diagnostic._ACTIVE_OBSERVER)

    def test_real_entrypoint_retains_v2_and_brackets_inert_service_import(self):
        stubs = self.base / 'stubs'
        stubs.mkdir()
        target = self.base / 'runs/agentops-http-control/inert/service'
        target.mkdir(parents=True)
        (stubs / 'agentops_native_probe_v2.py').write_text(
            'from pathlib import Path\nWORKSPACE = Path(' + repr(str(self.base)) + ')\n'
            'def within(path, root):\n'
            '    assert path.resolve().is_relative_to(root.resolve())\n'
            '    return path.resolve()\n')
        (stubs / 'serve_agentops_bridge_v1.py').write_text('''
import atexit, json
from pathlib import Path
TARGET = Path(''' + repr(str(target)) + ''')
def imported_service_exit_callback():
    phases = [json.loads(x)['phase'] for x in (TARGET / 'interpreter-exit-diagnostics/lifecycle.jsonl').read_text().splitlines()]
    (TARGET / 'inert-callback.json').write_text(json.dumps(phases))
atexit.register(imported_service_exit_callback)
async def serve(output, port):
    assert output == TARGET and port == 18764
    return 42
''')
        program = '''
import runpy, sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
entrypoint = sys.argv[3]
sys.argv = [entrypoint, '--output', sys.argv[4], '--port', '18764']
runpy.run_path(entrypoint, run_name='__main__')
'''
        run = subprocess.run([sys.executable, '-B', '-c', program, str(stubs), str(ROOT / 'scripts'),
                              str(ROOT / 'scripts/serve_agentops_bridge_diagnostic_v3.py'), str(target)],
                             stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace'))
        old = self.events(target / 'shutdown-diagnostics')
        self.assertEqual(old[-1]['phase'], 'asyncio_run_exited')
        self.assertEqual(old[-1]['outcome'], 'returned')
        new = self.events(target / 'interpreter-exit-diagnostics')
        self.assertGreater(new[1]['monotonic_ns'], old[-1]['monotonic_ns'])
        callback_phases = json.loads((target / 'inert-callback.json').read_text())
        self.assertIn('atexit_early_boundary', callback_phases)
        self.assertNotIn('atexit_late_boundary', callback_phases)
        self.assertEqual(new[-1]['phase'], 'atexit_late_boundary')


if __name__ == '__main__':
    unittest.main()
