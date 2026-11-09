"""Authored evidence mutations only; no application, signal, or process launch."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_agentops_bridge_diagnostic_v1 import validate_diagnostics

PID = 54321
FRAME = {'file': '/fixture/worker.py', 'line': 12, 'function': 'wait_for_work'}
THREAD = {'ident': 1001, 'daemon': False, 'alive': True, 'stack': [FRAME]}
TASK = {'current': True, 'done': False, 'cancelling': 0, 'stack': [FRAME]}
TRACE = 'Timeout (0:00:05)!\nThread 0x123 (most recent call first):\n  File "/fixture/worker.py", line 12 in wait_for_work\n'


def event(sequence, phase, seconds, **details):
    return {'schema_version': 'agentops-shutdown-event/2', 'sequence': sequence,
            'pid': PID, 'monotonic_ns': (seconds + 1) * 1_000_000_000,
            'at_utc': f'2026-10-28T00:00:{seconds:02d}+00:00',
            'phase': phase, **details}


class DiagnosticEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = Path(self.temp.name)
        self.diag = self.case / 'service/shutdown-diagnostics'
        self.diag.mkdir(parents=True)
        self.result = {'schema_version': 'agentops-bridge-case-result/1',
                       'case_id': 'B6', 'started_at_utc': '2026-10-28T00:00:00+00:00',
                       'finished_at_utc': '2026-10-28T00:00:40+00:00',
                       'forced_service_stop': False, 'service_returncode': 0}
        self.semantic = {'schema_version': 'agentops-bridge-case-check/1', 'case_id': 'B6',
                         'outcome': 'unknown_or_partial', 'strict_success': False}
        self.events = [event(1, 'asyncio_run_entered', 1),
                       event(2, 'teardown_watchdog_armed', 12, seconds=5.0),
                       event(3, 'coroutine_finished', 13, tasks=[copy.deepcopy(TASK)],
                             threads=[copy.deepcopy(THREAD)]),
                       event(4, 'asyncio_run_exited', 14, outcome='returned',
                             threads=[copy.deepcopy(THREAD)])]
        self.trace = ''
        self.write_json(self.case / 'service-process.json', {'pid': PID})
        self.write_json(self.case / 'service/service-result.json',
                        {'finished_at_utc': '2026-10-28T00:00:11+00:00'})

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def inspect(self):
        self.write_json(self.case / 'result.json', self.result)
        (self.diag / 'lifecycle.jsonl').write_text(
            ''.join(json.dumps(row) + '\n' for row in self.events), encoding='utf-8')
        (self.diag / 'teardown-stacks.txt').write_text(self.trace, encoding='utf-8')
        return validate_diagnostics(self.case, self.semantic)

    def test_clean_shutdown_does_not_promote_partial_continuation(self):
        before = copy.deepcopy(self.semantic)
        report = self.inspect()
        self.assertTrue(report['valid'] and report['complete'])
        self.assertEqual(report['classification'], 'asyncio_run_returned')
        self.assertEqual(report['case_outcome'], 'unknown_or_partial')
        self.assertFalse(report['case_strict_success'] or report['root_cause_established'])
        self.assertEqual(self.semantic, before)

    def test_cancel_stall_retains_timeout_and_forced_exit_without_claiming_cause(self):
        self.events.pop()
        self.trace = TRACE
        self.result.update(forced_service_stop=True, service_returncode=-15)
        report = self.inspect()
        self.assertTrue(report['valid'] and report['complete'])
        self.assertEqual(report['classification'], 'asyncio_teardown_stall_observed')
        self.assertFalse(report['root_cause_established'])

    def test_post_asyncio_survival_needs_no_promised_later_trace(self):
        self.result.update(forced_service_stop=True, service_returncode=-15)
        report = self.inspect()
        self.assertTrue(report['valid'] and report['complete'])
        self.assertEqual(report['classification'], 'post_asyncio_process_survival')
        self.assertFalse(report['timeout_trace_observed'] or report['root_cause_established'])

    def test_timeout_dump_can_precede_eventual_clean_exit(self):
        self.trace = TRACE
        self.events[-1]['at_utc'] = '2026-10-28T00:00:20+00:00'
        self.events[-1]['monotonic_ns'] = 21_000_000_000
        report = self.inspect()
        self.assertTrue(report['complete'] and report['timeout_trace_observed'])
        self.assertEqual(report['classification'], 'asyncio_run_returned')

    def test_forced_exit_without_trace_is_incomplete(self):
        self.events.pop()
        self.result.update(forced_service_stop=True, service_returncode=-15)
        report = self.inspect()
        self.assertTrue(report['valid'])
        self.assertFalse(report['complete'])
        self.assertEqual(report['classification'], 'forced_stop_without_teardown_trace')

    def test_missing_armed_after_diagnostic_error_is_incomplete_not_invalid(self):
        self.events.pop(1)
        self.events[-1]['diagnostic_errors'] = [{'stage': 'arm_watchdog', 'error_type': 'RuntimeError'}]
        report = self.inspect()
        self.assertTrue(report['valid'])
        self.assertFalse(report['complete'])
        self.assertIn('phase_missing:teardown_watchdog_armed', report['observation_gaps'])

    def test_missing_snapshot_with_disclosed_collection_error_is_incomplete(self):
        del self.events[2]['threads']
        self.events[2]['diagnostic_errors'] = [{'stage': 'thread_state', 'error_type': 'RuntimeError'}]
        report = self.inspect()
        self.assertTrue(report['valid'])
        self.assertFalse(report['complete'])

    def test_missing_snapshot_without_collection_error_is_invalid(self):
        del self.events[2]['tasks']
        self.assertFalse(self.inspect()['valid'])

    def test_missing_exit_without_forced_stop_does_not_assume_stall(self):
        self.events.pop()
        self.trace = TRACE
        report = self.inspect()
        self.assertTrue(report['valid'])
        self.assertFalse(report['complete'])
        self.assertEqual(report['classification'], 'unknown_or_partial')

    def test_wrong_pid_is_invalid(self):
        self.events[2]['pid'] += 1
        self.assertFalse(self.inspect()['valid'])

    def test_reordered_phases_are_invalid_even_with_increasing_clocks(self):
        self.events[1]['phase'], self.events[2]['phase'] = self.events[2]['phase'], self.events[1]['phase']
        self.assertFalse(self.inspect()['valid'])

    def test_duplicate_phase_is_invalid(self):
        self.events.append(copy.deepcopy(self.events[-1]))
        self.assertFalse(self.inspect()['valid'])

    def test_duplicate_sequence_is_invalid(self):
        self.events[-1]['sequence'] = self.events[-2]['sequence']
        self.assertFalse(self.inspect()['valid'])

    def test_nonmonotonic_clock_is_invalid(self):
        self.events[-1]['monotonic_ns'] = self.events[1]['monotonic_ns']
        self.assertFalse(self.inspect()['valid'])

    def test_timestamp_outside_controller_interval_is_invalid(self):
        self.events[-1]['at_utc'] = '2026-10-28T00:00:41+00:00'
        self.assertFalse(self.inspect()['valid'])

    def test_coroutine_finished_before_service_result_is_invalid(self):
        self.write_json(self.case / 'service/service-result.json',
                        {'finished_at_utc': '2026-10-28T00:00:15+00:00'})
        self.assertFalse(self.inspect()['valid'])

    def test_changed_watchdog_delay_is_invalid(self):
        self.events[1]['seconds'] = 20
        self.assertFalse(self.inspect()['valid'])

    def test_impossible_early_timeout_claim_is_invalid(self):
        self.events.pop()
        self.trace = TRACE
        self.result.update(forced_service_stop=True, service_returncode=-15,
                           finished_at_utc='2026-10-28T00:00:14+00:00')
        self.assertFalse(self.inspect()['valid'])

    def test_task_local_values_are_rejected(self):
        self.events[2]['tasks'][0]['stack'][0]['locals'] = {'private': 'inert'}
        self.assertFalse(self.inspect()['valid'])

    def test_zero_current_tasks_is_invalid(self):
        self.events[2]['tasks'][0]['current'] = False
        self.assertFalse(self.inspect()['valid'])

    def test_two_current_tasks_is_invalid(self):
        self.events[2]['tasks'].append(copy.deepcopy(TASK))
        self.assertFalse(self.inspect()['valid'])

    def test_duplicate_thread_identity_is_invalid(self):
        self.events[2]['threads'].append(copy.deepcopy(THREAD))
        self.assertFalse(self.inspect()['valid'])

    def test_bool_as_thread_id_is_invalid(self):
        self.events[2]['threads'][0]['ident'] = True
        self.assertFalse(self.inspect()['valid'])

    def test_missing_files_are_observation_gaps(self):
        self.inspect()
        (self.diag / 'lifecycle.jsonl').unlink()
        (self.diag / 'teardown-stacks.txt').unlink()
        report = validate_diagnostics(self.case, self.semantic)
        self.assertTrue(report['valid'])
        self.assertFalse(report['complete'])
        self.assertIn('lifecycle_file_missing', report['observation_gaps'])
        self.assertIn('trace_file_missing', report['observation_gaps'])

    def test_duplicate_json_key_is_invalid(self):
        self.inspect()
        path = self.diag / 'lifecycle.jsonl'
        raw = path.read_text()
        path.write_text(raw.replace('"pid": 54321', '"pid": 54321, "pid": 54321', 1))
        self.assertFalse(validate_diagnostics(self.case, self.semantic)['valid'])


if __name__ == '__main__':
    unittest.main()
