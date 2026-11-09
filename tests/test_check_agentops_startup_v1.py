"""Synthetic retained startup records only; no process/application is launched."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_agentops_startup_v1 import validate_startup


class StartupCheckerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.case = Path(temp.name) / 'N11'
        self.case.mkdir()
        self.epoch = 1_800_000_000
        self.argv = ['/sealed/python', '-B', '/sealed/scripts/serve_agentops_bridge_diagnostic_v4.py',
                     '--output', '/sealed/runs/agentops-http-control/N11/service', '--port', '18764',
                     '--exit-watchdog-seconds', '5.0', '--startup-stack-seconds', '5.0']
        self.files = {'service-process.json': {'argv': self.argv, 'pid': 123, 'started_at_utc': self.stamp(.1)},
                      'result.json': {'started_at_utc': self.stamp(0), 'finished_at_utc': self.stamp(10)},
                      'service/service-ready.json': {'port': 18764, 'state_dir': '/sealed/runs/agentops-http-control/N11/service/state',
                                                     'started_at_utc': self.stamp(.6)}}
        self.events = [self.event('startup_observer_armed', .2, interval_seconds=5.0, poll_seconds=.05,
                                  capture_backend='daemon_dump_traceback'),
                       self.event('startup_monitor_started', .3), self.event('readiness_observed', .7),
                       self.event('startup_observer_stopped', .8, reason='readiness_observed', captures=0)]
        self.trace = b''
        self.other = {'interpreter-exit-diagnostics': [{'pid': 123, 'phase': 'interpreter_exit_observer_installed', 'monotonic_ns': 250_000_000}],
                      'shutdown-diagnostics': [{'pid': 123, 'phase': 'asyncio_run_entered', 'monotonic_ns': 400_000_000},
                                               {'pid': 123, 'phase': 'teardown_watchdog_armed', 'monotonic_ns': 5_000_000_000}]}

    def stamp(self, offset):
        return datetime.fromtimestamp(self.epoch + offset, timezone.utc).isoformat()

    def event(self, phase, offset, **details):
        tick = int(offset * 1_000_000_000)
        return {'schema_version': 'agentops-startup-event/1', 'sequence': 0, 'pid': 123,
                'monotonic_ns': tick, 'at_epoch_ns': self.epoch * 1_000_000_000 + tick,
                'phase': phase, 'diagnostic_errors': [], **details}

    def sampled(self, complete=True):
        self.events = self.events[:2] + [self.event('startup_stack_capture_started', 5.3,
                                                   capture=1, capture_monotonic_ns=5_299_999_999)]
        if complete:
            self.events.append(self.event('startup_stack_capture_completed', 5.4, capture=1))
        self.trace = b'Startup traceback 1; pid=123; monotonic_ns=5299999999\nThread 1:\n  File "fixture.py", line 1 in work\n'
        self.files.pop('service/service-ready.json')

    def check(self):
        # Remove only the explicitly created fixture file when this variant
        # represents absent readiness. All evidence is otherwise regenerated.
        ready = self.case / 'service/service-ready.json'
        if ready.exists() and 'service/service-ready.json' not in self.files:
            ready.unlink()
        for name, value in self.files.items():
            path = self.case / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding='utf-8')
        for index, event in enumerate(self.events, 1):
            event['sequence'] = index
        journals = {'startup-diagnostics': self.events, **self.other}
        for name, values in journals.items():
            path = self.case / 'service' / name / 'lifecycle.jsonl'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(''.join(json.dumps(row) + '\n' for row in values), encoding='utf-8')
        (self.case / 'service/startup-diagnostics/startup-stacks.txt').write_bytes(self.trace)
        before = {p.relative_to(self.case): p.read_bytes() for p in self.case.rglob('*') if p.is_file()}
        result = validate_startup(self.case)
        self.assertEqual(before, {p.relative_to(self.case): p.read_bytes() for p in self.case.rglob('*') if p.is_file()})
        return result

    def test_clean_observation_requires_matching_ready_file_and_stopped_monitor(self):
        result = self.check()
        self.assertTrue(result['valid'], result)
        self.assertTrue(result['complete'], result)
        self.assertFalse(result['application_success_established'])
        self.assertFalse(result['root_cause_established'])

    def test_readiness_stall_retains_bound_samples_as_valid_incomplete(self):
        self.sampled()
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])
        self.assertEqual(checked['captures_completed'], 1)
        self.assertFalse(checked['readiness_observed'])

    def test_interrupted_sample_is_partial_not_a_completed_capture(self):
        self.sampled(complete=False)
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])
        self.assertEqual(checked['captures_started'], 1)
        self.assertEqual(checked['captures_completed'], 0)

    def test_stack_capture_does_not_prevent_a_later_clean_readiness_observation(self):
        ready = self.files['service/service-ready.json']
        self.sampled()
        ready['started_at_utc'] = self.stamp(5.5)
        self.files['service/service-ready.json'] = ready
        self.events += [self.event('readiness_observed', 5.6),
                        self.event('startup_observer_stopped', 5.7, reason='readiness_observed', captures=1)]
        self.other['shutdown-diagnostics'][-1]['monotonic_ns'] = 8_000_000_000
        checked = self.check()
        self.assertTrue(checked['complete'], checked)

    def test_pid_and_trace_headers_cannot_be_relabelled(self):
        self.sampled()
        original = self.trace
        for changed in (original.replace(b'pid=123', b'pid=999'),
                        original.replace(b'traceback 1', b'traceback 2'),
                        original.replace(b'5299999999', b'5299999998')):
            self.trace = changed
            self.assertFalse(self.check()['valid'])

    def test_claimed_completed_sample_requires_actual_stack_locations(self):
        self.sampled()
        self.trace = self.trace.split(b'Thread')[0]
        self.assertFalse(self.check()['valid'])
        self.trace = b''
        self.assertFalse(self.check()['valid'])

    def test_forged_readiness_missing_file_port_path_and_time_are_rejected(self):
        before = deepcopy(self.files)
        self.files.pop('service/service-ready.json')
        self.assertFalse(self.check()['valid'])
        for key, value in (('port', 18765), ('state_dir', '/other/state'), ('started_at_utc', self.stamp(2))):
            self.files = deepcopy(before)
            self.files['service/service-ready.json'][key] = value
            self.assertFalse(self.check()['valid'])

    def test_v3_launch_foreign_workspace_and_changed_interval_are_rejected(self):
        original = list(self.argv)
        for index, value in ((2, '/sealed/scripts/serve_agentops_bridge_diagnostic_v3.py'),
                             (2, '/other/scripts/serve_agentops_bridge_diagnostic_v4.py'),
                             (10, '6'), (10, 'nan'), (9, '--unregistered')):
            self.argv[:] = original
            self.argv[index] = value
            self.assertFalse(self.check()['valid'])

    def test_pre_readiness_wrapper_failure_is_valid_incomplete(self):
        self.files.pop('service/service-ready.json')
        self.events = self.events[:2] + [self.event('startup_observer_stopped', .8, reason='wrapper_finished', captures=0)]
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])

    def test_monitor_errors_never_count_as_complete(self):
        error = {'stage': 'close_startup_trace', 'error_type': 'OSError'}
        self.events[-1]['diagnostic_errors'] = [error]
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])

    def test_duplicate_out_of_order_and_post_stop_events_are_rejected(self):
        initial = deepcopy(self.events)
        self.events.append(deepcopy(self.events[-1]))
        self.assertFalse(self.check()['valid'])
        self.events = deepcopy(initial)
        self.events[-1]['monotonic_ns'] = 1
        self.assertFalse(self.check()['valid'])
        self.events = deepcopy(initial)
        self.events[-1]['at_epoch_ns'] += 20_000_000_000
        self.assertFalse(self.check()['valid'])

    def test_late_monitor_stop_is_valid_but_incomplete_and_wrong_pid_is_invalid(self):
        self.other['shutdown-diagnostics'][-1]['monotonic_ns'] = 750_000_000
        checked = self.check()
        self.assertTrue(checked['valid'], checked)
        self.assertFalse(checked['complete'])
        self.other['shutdown-diagnostics'][0]['pid'] = 456
        self.assertFalse(self.check()['valid'])

    def test_missing_startup_evidence_cannot_pass(self):
        checked = validate_startup(self.case)
        self.assertFalse(checked['valid'])
        self.assertFalse(checked['complete'])


if __name__ == '__main__':
    unittest.main()
