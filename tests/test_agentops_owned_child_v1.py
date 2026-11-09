"""Exercise real owned-child exit ordering; never launch AgentOps."""
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import agentops_owned_child_v1 as owned


class OwnedChildTests(unittest.TestCase):
    def child(self, program):
        argv = [sys.executable, '-B', '-c', program]
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.addCleanup(cleanup)
        return process, argv

    def finish(self, process, argv, **kwargs):
        def inspect(pgid, commands):
            self.assertEqual(pgid, process.pid)
            self.assertEqual(commands, [argv])
            self.assertIsNotNone(process.returncode)
            self.assertIsNotNone(process.poll())
            return {'initially_empty': True, 'final_empty': True,
                    'forced_cleanup': False, 'errors': []}
        with patch.object(owned, 'finish_owned_group', side_effect=inspect) as check:
            result = owned.finish_owned_child(process, [argv], **kwargs)
        check.assert_called_once()
        self.assertTrue(result['reaped_before_group_check'])
        return result

    def test_normal_exit_is_reaped_before_group_inspection_without_signal(self):
        process, argv = self.child('pass')
        result = self.finish(process, argv, graceful_seconds=10)
        self.assertEqual(result['returncode'], 0)
        self.assertFalse(result['graceful_timeout'])
        self.assertEqual(result['signal_requests'], [])
        self.assertEqual(result['errors'], [])

    def test_timed_out_child_is_reaped_before_group_inspection(self):
        process, argv = self.child('import time; print("ready",flush=True); time.sleep(60)')
        self.assertEqual(process.stdout.readline().strip(), b'ready')
        result = self.finish(process, argv, graceful_seconds=0.01)
        self.assertTrue(result['graceful_timeout'])
        self.assertNotEqual(result['returncode'], 0)
        self.assertEqual([row['signal'] for row in result['signal_requests']], ['SIGTERM'])
        self.assertEqual(result['errors'], [])

    @unittest.skipUnless(sys.platform == 'linux', 'Linux SIGTERM/SIGKILL semantics')
    def test_sigterm_resistant_child_is_reaped_after_bounded_sigkill(self):
        process, argv = self.child('import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print("ready",flush=True); time.sleep(60)')
        self.assertEqual(process.stdout.readline().strip(), b'ready')
        result = self.finish(process, argv, graceful_seconds=0.01, terminate_seconds=0.05)
        self.assertEqual([row['signal'] for row in result['signal_requests']], ['SIGTERM', 'SIGKILL'])
        self.assertEqual(result['returncode'], -9)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux group inspection')
    def test_real_group_check_sees_no_unreaped_leader(self):
        process, argv = self.child('import time; print("ready",flush=True); time.sleep(60)')
        self.assertEqual(process.stdout.readline().strip(), b'ready')
        result = owned.finish_owned_child(process, [argv], graceful_seconds=0.01)
        self.assertTrue(result['graceful_timeout'])
        self.assertEqual(result['returncode'], -15)
        self.assertTrue(result['owned_group']['final_empty'])
        self.assertEqual(result['owned_group']['errors'], [])

    def test_mismatched_command_and_invalid_wait_cannot_signal_child(self):
        process, argv = self.child('import time; time.sleep(60)')
        with patch.object(process, 'terminate') as terminate, patch.object(process, 'kill') as kill:
            with self.assertRaises(ValueError):
                owned.finish_owned_child(process, [['unrelated']])
            for value in (-1, float('nan'), float('inf'), True):
                with self.assertRaises(ValueError):
                    owned.finish_owned_child(process, [argv], graceful_seconds=value)
            terminate.assert_not_called(); kill.assert_not_called()

    def test_poll_error_preserves_receipt_and_withholds_group_inspection(self):
        process, argv = self.child('pass')
        process.wait(timeout=10)
        with patch.object(process, 'poll', side_effect=OSError('inert poll failure')), \
                patch.object(owned, 'finish_owned_group') as group:
            result = owned.finish_owned_child(process, [argv])
        group.assert_not_called()
        self.assertFalse(result['reaped_before_group_check'])
        self.assertIsNone(result['returncode'])
        self.assertTrue(any('poll' in row for row in result['errors']))

    def test_group_exception_preserves_confirmed_child_exit(self):
        process, argv = self.child('pass')
        with patch.object(owned, 'finish_owned_group', side_effect=OSError('inert group failure')):
            result = owned.finish_owned_child(process, [argv], graceful_seconds=10)
        self.assertEqual(result['returncode'], 0)
        self.assertTrue(result['reaped_before_group_check'])
        self.assertIsNone(result['owned_group'])
        self.assertTrue(any('group:' in row for row in result['errors']))

    @unittest.skipUnless(sys.platform == 'linux', 'Linux SIGTERM semantics')
    def test_sigterm_handler_exit_zero_still_retains_forced_stop_evidence(self):
        process, argv = self.child('import signal,time,sys; signal.signal(signal.SIGTERM,lambda *_: sys.exit(0)); print("ready",flush=True); time.sleep(60)')
        self.assertEqual(process.stdout.readline().strip(), b'ready')
        result = self.finish(process, argv, graceful_seconds=0.01)
        self.assertEqual(result['returncode'], 0)
        self.assertTrue(result['graceful_timeout'])
        self.assertEqual([row['signal'] for row in result['signal_requests']], ['SIGTERM'])


if __name__ == '__main__':
    unittest.main()
