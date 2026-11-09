"""Mocked /proc and signals only; no real process launch or signal is used."""
import importlib.util
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('agentops_owned_process_v1',
    Path(__file__).resolve().parents[1] / 'scripts/agentops_owned_process_v1.py')
owned = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(owned)

GROUP = 43210
ARGV = ['/usr/bin/node', '/fixture/client.mjs', '--config', '/fixture/config.json']
BRIDGE = ['/usr/bin/node', '/fixture/bridge.mjs']
ORPHAN = {'pid': 43211, 'state': 'S', 'pgrp': GROUP, 'session': GROUP,
          'starttick': 123456, 'argv': BRIDGE}


def stat(pid, pgrp, session, starttick, comm='fixture ) with spaces'):
    fields = ['S', '1', str(pgrp), str(session)] + ['0'] * 15 + [str(starttick)]
    return f'{pid} ({comm}) ' + ' '.join(fields) + '\n'


class OwnedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.clock = 10.0
        self.patches = [patch.object(owned.sys, 'platform', 'linux'),
                        patch.object(owned.signal, 'SIGKILL', 9, create=True),
                        patch.object(owned.os, 'getpgrp', return_value=123, create=True),
                        patch.object(owned.time, 'monotonic', side_effect=lambda: self.clock),
                        patch.object(owned.time, 'monotonic_ns', side_effect=lambda: int(self.clock * 1e9)),
                        patch.object(owned.time, 'sleep', side_effect=self.advance),
                        patch.object(owned.os, 'killpg', create=True)]
        self.mocks = [item.start() for item in self.patches]
        self.kill = self.mocks[-1]
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def advance(self, seconds):
        self.clock += seconds

    def run_scans(self, scans):
        with patch.object(owned, '_scan_group', side_effect=scans):
            return owned.finish_owned_group(GROUP, [ARGV, BRIDGE])

    def test_empty_group_never_signalled(self):
        report = self.run_scans([([], [])])
        self.assertTrue(report['initially_empty'] and report['final_empty'])
        self.assertFalse(report['forced_cleanup'])
        self.assertEqual(report['errors'], [])
        self.kill.assert_not_called()

    def test_orphan_without_leader_is_detected_and_terminated(self):
        report = self.run_scans([([ORPHAN], []), ([ORPHAN], []), ([], [])])
        self.assertFalse(report['initially_empty'])
        self.assertTrue(report['final_empty'] and report['forced_cleanup'])
        self.assertEqual(report['members'][0]['starttick'], 123456)
        self.assertEqual(report['members'][0]['argv'], BRIDGE)
        self.kill.assert_called_once_with(GROUP, signal.SIGTERM)

    def test_unknown_argv_is_retained_without_signal(self):
        stranger = {**ORPHAN, 'argv': ['/usr/bin/unrelated']}
        report = self.run_scans([([stranger], [])])
        self.assertFalse(report['final_empty'])
        self.assertIn('unknown argv', report['errors'][0])
        self.assertEqual(report['members'], [stranger])
        self.kill.assert_not_called()

    def test_wrong_session_is_not_signalled_even_with_allowed_argv(self):
        report = self.run_scans([([{**ORPHAN, 'session': 99999}], [])])
        self.assertIn('owned session/group', report['errors'][0])
        self.kill.assert_not_called()

    def test_unknown_arrival_before_signal_rejects_entire_group(self):
        stranger = {**ORPHAN, 'pid': 43212, 'argv': ['/usr/bin/unrelated']}
        report = self.run_scans([([ORPHAN], []), ([ORPHAN, stranger], [])])
        self.assertFalse(report['forced_cleanup'])
        self.assertTrue(report['errors'])
        self.kill.assert_not_called()

    def test_starttick_change_blocks_signal(self):
        report = self.run_scans([([ORPHAN], []), ([{**ORPHAN, 'starttick': 999999}], [])])
        self.assertIn('starttick changed', report['errors'][0])
        self.kill.assert_not_called()

    def test_stubborn_group_escalates_and_stays_within_five_seconds(self):
        self.kill.side_effect = lambda pgid, signum: None
        with patch.object(owned, '_scan_group', return_value=([ORPHAN], [])):
            report = owned.finish_owned_group(GROUP, [ARGV, BRIDGE])
        self.assertEqual(self.kill.call_args_list[0].args, (GROUP, signal.SIGTERM))
        self.assertEqual(self.kill.call_args_list[1].args, (GROUP, signal.SIGKILL))
        self.assertEqual(self.kill.call_count, 2)
        self.assertGreaterEqual(self.clock, 15.0)
        self.assertLessEqual(self.clock, 15.000001)
        self.assertFalse(report['final_empty'])
        self.assertTrue(report['forced_cleanup'])
        self.assertIn('survived bounded', report['errors'][-1])

    def test_unknown_arrival_after_term_prevents_kill(self):
        stranger = {**ORPHAN, 'pid': 43212, 'argv': ['/usr/bin/unrelated']}
        report = self.run_scans([([ORPHAN], []), ([ORPHAN], []), ([ORPHAN, stranger], [])])
        self.kill.assert_called_once_with(GROUP, signal.SIGTERM)
        self.assertFalse(report['final_empty'])
        self.assertIn('unknown argv', report['errors'][0])

    def test_uncertain_membership_fails_closed(self):
        report = self.run_scans([([], ['Cannot inspect member'])])
        self.assertFalse(report['initially_empty'] or report['final_empty'])
        self.assertTrue(report['errors'])
        self.kill.assert_not_called()

    def test_group_disappearing_before_term_requires_no_signal(self):
        report = self.run_scans([([ORPHAN], []), ([], [])])
        self.assertFalse(report['initially_empty'])
        self.assertTrue(report['final_empty'])
        self.assertFalse(report['forced_cleanup'])
        self.kill.assert_not_called()

    def test_own_group_rejected_before_scan(self):
        with patch.object(owned, '_scan_group') as scan:
            report = owned.finish_owned_group(123, [ARGV])
        self.assertTrue(report['errors'])
        scan.assert_not_called()
        self.kill.assert_not_called()

    def test_fake_proc_scan_finds_orphan_and_never_reads_unrelated_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            orphan_dir = root / str(ORPHAN['pid'])
            orphan_dir.mkdir()
            (orphan_dir / 'stat').write_text(stat(ORPHAN['pid'], GROUP, GROUP, ORPHAN['starttick']))
            (orphan_dir / 'cmdline').write_bytes(b'\0'.join(value.encode() for value in BRIDGE) + b'\0')
            other_dir = root / '90001'
            other_dir.mkdir()
            (other_dir / 'stat').write_text(stat(90001, 90000, 90000, 876543))
            # Deliberately no cmdline file for the unrelated group.
            with patch.object(owned, '_PROC_ROOT', root):
                members, errors = owned._scan_group(GROUP)
        self.assertEqual(errors, [])
        self.assertEqual(members, [ORPHAN])
        self.kill.assert_not_called()


if __name__ == '__main__':
    unittest.main()
