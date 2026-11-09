"""Independent checker mutation tests over constructed process/lifecycle records."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_agentops_interpreter_exit_v2 import validate_interpreter_exit


class InterpreterExitCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = Path(self.temp.name) / 'N11'
        self.case.mkdir()
        self.epoch = 1_800_000_000
        def stamp(offset):
            return datetime.fromtimestamp(self.epoch + offset, timezone.utc).isoformat()
        self.stamp = stamp
        self.argv = ['/sealed/python', '-B', '/sealed/scripts/serve_agentops_bridge_diagnostic_v4.py',
                     '--output', '/sealed/runs/agentops-http-control/N11/service', '--port', '18764']
        group = {'schema_version': 'agentops-owned-process-group/1', 'pgid': 123,
                 'initially_empty': True, 'final_empty': True, 'forced_cleanup': False,
                 'members': [], 'final_members': [],
                 'snapshots': [{'phase': 'initial', 'monotonic_ns': 2_500_000_000,
                                'members': [], 'errors': []}], 'signals': [], 'errors': []}
        child = {'schema_version': 'agentops-owned-child-finish/1', 'pid': 123, 'argv': self.argv,
                 'returncode': 0, 'graceful_timeout': False, 'signal_requests': [],
                 'reaped_before_group_check': True, 'errors': [], 'owned_group': group}
        result = {'started_at_utc': stamp(0), 'finished_at_utc': stamp(3),
                  'service_returncode': 0, 'forced_service_stop': False, 'cleanup_errors': [],
                  'service_child_cleanup': child, 'service_group_cleanup': group}
        self.files = {
            'service-process.json': {'argv': self.argv, 'pid': 123, 'started_at_utc': stamp(0.1)},
            'result.json': result,
            'service/service-result.json': {'status': 'stopped', 'finished_at_utc': stamp(1.1),
                                            'capture_errors': [], 'network_errors': []},
            'service/stop-requested.json': {'requested_at_utc': stamp(1.0)}}
        phases = ['interpreter_exit_observer_installed', 'entrypoint_boundary',
                  'interpreter_exit_watchdog_armed', 'atexit_early_boundary', 'atexit_late_boundary']
        offsets = [0.2, 2.1, 2.2, 2.3, 2.4]
        self.events = []
        for i, (phase, offset) in enumerate(zip(phases, offsets)):
            row = {'schema_version': 'agentops-interpreter-exit-event/1', 'sequence': i + 1,
                   'pid': 123, 'phase': phase, 'monotonic_ns': int(offset * 1_000_000_000),
                   'at_epoch_ns': self.epoch * 1_000_000_000 + int(offset * 1_000_000_000),
                   'watchdog_armed': i >= 2, 'diagnostic_errors': []}
            if phase == 'entrypoint_boundary': row.update(boundary='asyncio_observer', outcome='returned')
            if phase == 'interpreter_exit_watchdog_armed': row.update(seconds=5.0, repeat=True, exit=False)
            self.events.append(row)
        self.old = []
        for i, (phase, offset) in enumerate(zip(
                ['asyncio_run_entered', 'teardown_watchdog_armed', 'coroutine_finished', 'asyncio_run_exited'],
                [0.3, 1.2, 1.3, 2.0])):
            self.old.append({'schema_version': 'agentops-shutdown-event/2', 'sequence': i + 1,
                             'pid': 123, 'phase': phase, 'monotonic_ns': int(offset * 1_000_000_000),
                             'at_utc': stamp(offset), 'diagnostic_errors': []})
        self.old[-1]['outcome'] = 'returned'
        self.trace = b''

    def check(self):
        for name, value in self.files.items():
            target = self.case / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value), encoding='utf-8')
        for name, rows in [('interpreter-exit-diagnostics', self.events), ('shutdown-diagnostics', self.old)]:
            target = self.case / 'service' / name / 'lifecycle.jsonl'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        trace = self.case / 'service/interpreter-exit-diagnostics/interpreter-exit-stacks.txt'
        trace.write_bytes(self.trace)
        before = {str(p): p.read_bytes() for p in self.case.rglob('*') if p.is_file()}
        result = validate_interpreter_exit(self.case)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.case.rglob('*') if p.is_file()})
        return result

    def forced(self, code=-15):
        result = self.files['result.json']
        result.update(service_returncode=code, forced_service_stop=True)
        result['service_child_cleanup'].update(returncode=code, graceful_timeout=True,
            signal_requests=[{'signal': 'SIGTERM', 'method_returned': True}])

    def test_complete_requires_clean_coherent_process_and_all_markers(self):
        result = self.check()
        self.assertTrue(result['valid'], result)
        self.assertTrue(result['complete'], result)
        self.assertFalse(result['root_cause_established'])
        self.assertEqual(result['scientific_gate_credit_added'], 0)
        self.assertEqual(len(result['files']), 7)

    def test_explicit_v4_options_are_bound_and_v3_is_not_relabelled(self):
        self.argv.extend(['--exit-watchdog-seconds', '5.0', '--startup-stack-seconds', '5.0'])
        result = self.check()
        self.assertTrue(result['complete'], result)
        self.assertEqual(result['schema_version'], 'agentops-interpreter-exit-check/2')
        self.argv[8] = '6.0'
        self.assertFalse(self.check()['valid'])
        self.argv[8] = '5.0'
        self.argv[2] = '/sealed/scripts/serve_agentops_bridge_diagnostic_v3.py'
        self.assertFalse(self.check()['valid'])

    def test_forced_atexit_hang_is_valid_but_incomplete(self):
        self.events.pop()
        self.trace = b'Timeout (0:00:05)!\nThread in constructed_atexit_hang\n'
        self.forced()
        result = self.check()
        self.assertTrue(result['valid'], result)
        self.assertFalse(result['complete'])
        self.assertTrue(result['timeout_trace_observed'])
        self.assertFalse(result['root_cause_established'])

    def test_all_markers_do_not_excuse_forced_exit_even_with_zero_returncode(self):
        self.forced(code=0)
        result = self.check()
        self.assertTrue(result['valid'], result)
        self.assertFalse(result['complete'])
        self.assertIn('Service did not exit cleanly without intervention', result['completion_blockers'])

    def test_hidden_forced_cleanup_is_invalid(self):
        self.forced()
        self.files['result.json']['forced_service_stop'] = False
        result = self.check()
        self.assertFalse(result['valid'])
        self.assertIn('Forced-service flag', result['validation_errors'][0])

    def test_lifecycle_pid_mismatch_is_invalid(self):
        self.events[-1]['pid'] += 1
        self.assertFalse(self.check()['valid'])

    def test_child_argv_and_returncode_mismatches_are_invalid(self):
        baseline = copy.deepcopy(self.files)
        self.files['result.json']['service_child_cleanup']['argv'] = ['unrelated']
        self.assertFalse(self.check()['valid'])
        self.files = baseline
        self.files['result.json']['service_returncode'] = -15
        self.assertFalse(self.check()['valid'])

    def test_post_asyncio_handoff_must_follow_old_asyncio_exit(self):
        self.old[-1]['monotonic_ns'] = self.events[1]['monotonic_ns'] + 1
        self.assertFalse(self.check()['valid'])

    def test_reordered_or_out_of_window_events_are_invalid(self):
        original = copy.deepcopy(self.events)
        self.events[-1]['monotonic_ns'] = self.events[-2]['monotonic_ns'] - 1
        self.assertFalse(self.check()['valid'])
        self.events = original
        self.events[-1]['at_epoch_ns'] += 10_000_000_000
        self.assertFalse(self.check()['valid'])

    def test_diagnostic_failure_is_valid_but_incomplete(self):
        for event in self.events[2:]:
            event['diagnostic_errors'] = [{'stage': 'inert', 'error_type': 'OSError'}]
        result = self.check()
        self.assertTrue(result['valid'], result)
        self.assertFalse(result['complete'])

    def test_unreaped_child_cannot_be_complete(self):
        self.forced(code=None)
        result = self.files['result.json']
        result['service_child_cleanup'].update(reaped_before_group_check=False, owned_group=None,
                                               errors=['Owned child exit is unconfirmed'])
        result.update(service_group_cleanup={}, cleanup_errors=['Owned child exit is unconfirmed'])
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])

    def test_group_and_cleanup_errors_cannot_be_hidden(self):
        group = self.files['result.json']['service_group_cleanup']
        group.update(initially_empty=False, final_empty=False, errors=['inert scan failure'])
        checked = self.check()
        self.assertFalse(checked['valid'])
        self.files['result.json']['cleanup_errors'] = ['inert scan failure']
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])

    def test_group_exception_after_reaping_is_valid_incomplete_evidence(self):
        result = self.files['result.json']
        result['service_child_cleanup'].update(owned_group=None, errors=['group: OSError: inert'])
        result.update(service_group_cleanup={}, cleanup_errors=['group: OSError: inert'])
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])
        self.assertTrue(checked['process_exit']['reaped_before_group_check'])

    def test_group_signal_cannot_be_hidden_behind_clean_flags(self):
        group = self.files['result.json']['service_group_cleanup']
        group['signals'] = [{'signal': 'SIGTERM', 'sent': True, 'monotonic_ns': 2_600_000_000}]
        checked = self.check()
        self.assertFalse(checked['valid'])
        self.assertIn('sent signals', checked['validation_errors'][0])

    def test_clean_group_requires_an_actual_single_empty_initial_snapshot(self):
        group = self.files['result.json']['service_group_cleanup']
        original = copy.deepcopy(group['snapshots'])
        for snapshots in ([], original + [dict(original[0], monotonic_ns=2_600_000_000)],
                          [dict(original[0], errors=['inert read error'])],
                          [dict(original[0], members=[{'pid': 456}])]):
            with self.subTest(snapshots=snapshots):
                group['snapshots'] = snapshots
                checked = self.check()
                self.assertFalse(checked['valid'], checked)
                self.assertFalse(checked['complete'])

    def test_unsent_group_signal_record_is_not_clean_observation(self):
        group = self.files['result.json']['service_group_cleanup']
        group['signals'] = [{'signal': 'SIGTERM', 'sent': False, 'monotonic_ns': 2_600_000_000}]
        self.assertFalse(self.check()['complete'])

    def test_coherent_forced_group_cleanup_remains_valid_incomplete(self):
        result = self.files['result.json']
        group = result['service_group_cleanup']
        member = {'pid': 456, 'pgrp': 123, 'session': 123, 'starttick': 100,
                  'state': 'S', 'argv': self.argv}
        group.update(initially_empty=False, forced_cleanup=True, members=[member],
                     signals=[{'signal': 'SIGTERM', 'sent': True, 'monotonic_ns': 2_650_000_000}],
                     snapshots=[{'phase': 'initial', 'monotonic_ns': 2_500_000_000,
                                 'members': [member], 'errors': []},
                                {'phase': 'before_sigterm', 'monotonic_ns': 2_600_000_000,
                                 'members': [member], 'errors': []},
                                {'phase': 'after_sigterm', 'monotonic_ns': 2_700_000_000,
                                 'members': [], 'errors': []}])
        result['forced_service_stop'] = True
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])

    def test_process_start_receipt_may_follow_fast_child_installation(self):
        self.files['service-process.json']['started_at_utc'] = self.stamp(0.25)
        self.assertTrue(self.check()['complete'])

    def test_missing_and_duplicate_markers_do_not_count_as_complete(self):
        self.events.pop()
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])
        self.events.append(copy.deepcopy(self.events[-1]))
        self.assertFalse(self.check()['valid'])


if __name__ == '__main__':
    unittest.main()
