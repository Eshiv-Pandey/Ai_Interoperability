"""Constructed V2 analyzer controls; never actual run or gold substitutes."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_shopper_V2_analysis_controls', ROOT / 'scripts/analyze_ap2_native_shopper_provider_v2.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
PLAN = M.frozen_plan()


class MemoryRead:
    def __init__(self, members):
        self.members = members
        self.manifest = {key: M.V1.digest(raw) for key, raw in members.items()}
        self.reads = {}
        self.receipt = {'run_id': 7, 'head_sha': 'constructed-fixture-only', 'archive_sha256': 'constructed-fixture-only'}

    def raw(self, name, optional=False):
        raw = self.members.get(name)
        if raw is None and not optional:
            raise ValueError('constructed_required_member_absent:' + name)
        if raw is not None:
            self.reads[name] = M.V1.digest(raw)
        return raw

    def rows(self, name):
        raw = self.raw(name, optional=True)
        return [json.loads(line) for line in raw.splitlines() if line.strip()] if raw else []

    def json(self, name, optional=False):
        raw = self.raw(name, optional=optional)
        return json.loads(raw) if raw is not None else None


def fixture(unclosed=False, active_at_freeze=0, summary_active=0, close_after_freeze=False):
    request, response = b'{"contents":[]}', b'{"usageMetadata":{"totalTokenCount":7}}'
    ledger = []
    if unclosed or close_after_freeze:
        ledger.append({'allocation': 0, 'phase': 'started', 'time': '2026-01-01T00:00:00+00:00',
                       'path': PLAN['provider_path'], 'request': M.V1.digest(request)})
    if close_after_freeze:
        ledger.append({'allocation': 0, 'phase': 'finished', 'time': '2026-01-01T00:00:03+00:00',
                       'http_status': 200, 'response': M.V1.digest(response)})
    members = {'execution/provider/ledger.jsonl': b'\n'.join(json.dumps(row).encode() for row in ledger),
               'execution/provider/000.request.json': request, 'execution/provider/000.response.json': response}
    read = MemoryRead(members)
    result = {'schema_version': 'ap2-native-shopper-provider-result/2', 'allocated_task_count': 1,
              'cases': [{'case_id': M.CASE_ID, 'status': 'unexecuted'}],
              'provider': {'upstream_allocations': int(bool(ledger)), 'cumulative_request_bytes': len(request) if ledger else 0,
                           'request_transport_timeout_seconds': 120, 'request_timeout_is_independent_whole_request_wall_cap': False,
                           'admission_closed': True, 'capture_frozen': True, 'active_handlers': summary_active}}
    provider = M.V1.provider_analysis(read, result)
    usage_fields = ('upstream_allocations', 'terminal_responses', 'known_reported_tokens',
                    'successful_responses_missing_or_invalid_usage', 'failed_responses_missing_or_invalid_usage',
                    'responses_missing_or_invalid_usage', 'unclosed_allocation_ids', 'allocations_with_unmeasured_usage', 'fully_measured')
    result['provider']['all_response_usage'] = {key: provider[key] for key in usage_fields}
    result['provider']['all_response_usage']['unknown_usage_is_zero'] = False
    drain = {'schema_version': 'ap2-provider-drain/2', 'time': '2026-01-01T00:00:02+00:00',
             'admission_closed': True, 'capture_frozen': True, 'all_handlers_completed': active_at_freeze == 0,
             'active_handlers_at_capture_freeze': active_at_freeze, 'maximum_drain_seconds': 0,
             'elapsed_drain_seconds': 0.0001, 'allocated_upstream_calls_at_capture_freeze': provider['upstream_allocations'],
             'request_bytes_at_capture_freeze': provider['recorded_cumulative_request_bytes'],
             'late_sender_outcomes_retained': False, 'unfinished_allocations_require_unknown_usage': True,
             'unclosed_allocation_ids': provider['unclosed_allocation_ids'],
             'allocations_with_unmeasured_usage': provider['allocations_with_unmeasured_usage']}
    result['provider_drain'] = drain
    members['execution/provider-drain.json'] = json.dumps(drain).encode()
    return read, result, provider


def update_drain(read, result, **updates):
    result['provider_drain'].update(updates)
    read.members['execution/provider-drain.json'] = json.dumps(result['provider_drain']).encode()


def full_fixture():
    read, result, _ = fixture()
    read.members['plan/plan.json'] = json.dumps(PLAN).encode()
    for name in PLAN['owned_sources']:
        read.members['plan/owned-source/' + name] = (M.FROZEN_PLAN.parent / 'owned-source' / name).read_bytes()
    runtime = {'required_original_versions': PLAN['versions'], 'distributions': PLAN['versions'],
               'source_stage_sha256': PLAN['source_stage_sha256'],
               'original_windows_environment_sha256': PLAN['original_windows_environment_sha256'], 'files': {}}
    raw = json.dumps(runtime).encode()
    read.members['execution/portable-runtime.json'] = raw
    result['portable_runtime_sha256'] = M.V1.digest(raw)['sha256']
    read.members['execution/result.json'] = json.dumps(result).encode()
    read.manifest = {key: M.V1.digest(raw) for key, raw in read.members.items()}
    return read, result


class DrainControls(unittest.TestCase):
    def test_completed_frozen_capture_joins_zero_allocations(self):
        read, result, provider = fixture()
        analyzed = M.drain_analysis(read, PLAN, result, provider)
        self.assertEqual(analyzed['consistency_questions'], [])
        self.assertTrue(analyzed['handler_census_is_distinct_from_consumed_allocation_count'])
        self.assertTrue(analyzed['elapsed_drain_exceeds_requested_wait'])

    def test_unclosed_consumption_is_unknown_even_if_handler_finishes_after_freeze(self):
        read, result, provider = fixture(unclosed=True, active_at_freeze=1, summary_active=0)
        analyzed = M.drain_analysis(read, PLAN, result, provider)
        self.assertEqual(analyzed['consistency_questions'], [])
        self.assertEqual(analyzed['unclosed_allocations_with_unmeasured_usage'], 1)
        self.assertFalse(analyzed['fully_measured_provider_consumption_claimed'])

    def test_active_handler_census_includes_unallocated_queued_work_separately(self):
        read, result, provider = fixture(unclosed=True, active_at_freeze=2, summary_active=1)
        analyzed = M.drain_analysis(read, PLAN, result, provider)
        self.assertEqual(analyzed['consistency_questions'], [])
        self.assertEqual(analyzed['standalone_drain_record']['active_handlers_at_capture_freeze'], 2)
        self.assertEqual(analyzed['unclosed_consumed_allocations'], [0])
        read, result, provider = fixture(active_at_freeze=1, summary_active=0)
        self.assertEqual(M.drain_analysis(read, PLAN, result, provider)['consistency_questions'], [])

    def test_unclosed_allocation_with_completed_handler_census_is_detected(self):
        read, result, provider = fixture(unclosed=True)
        analyzed = M.drain_analysis(read, PLAN, result, provider)
        self.assertIn('V2_completed_drain_has_unclosed_consumed_allocations', analyzed['consistency_questions'])

    def test_summary_handler_count_cannot_increase_after_freeze(self):
        read, result, provider = fixture(active_at_freeze=1, summary_active=2)
        self.assertIn('V2_active_handler_census_absent_invalid_or_increases_after_freeze', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])

    def test_late_terminal_timestamp_is_detected(self):
        read, result, provider = fixture(close_after_freeze=True)
        analyzed = M.drain_analysis(read, PLAN, result, provider)
        self.assertIn('V2_ledger_timestamp_after_recorded_capture_freeze', analyzed['consistency_questions'])

    def test_standalone_and_parent_capture_records_must_match(self):
        read, result, provider = fixture()
        result['provider_drain'] = dict(result['provider_drain'], request_bytes_at_capture_freeze=999)
        self.assertIn('standalone_and_parent_V2_provider_drain_records_differ', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])

    def test_admission_and_capture_freeze_are_required(self):
        for key in ('admission_closed', 'capture_frozen', 'unfinished_allocations_require_unknown_usage'):
            with self.subTest(key=key):
                read, result, provider = fixture()
                update_drain(read, result, **{key: False})
                self.assertIn('V2_drain_' + key + '_not_true', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])

    def test_bounded_wait_and_sender_timeout_records_are_checked(self):
        read, result, provider = fixture()
        update_drain(read, result, maximum_drain_seconds=151)
        self.assertIn('V2_drain_wait_bounds_or_elapsed_record_invalid', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])
        read, result, provider = fixture()
        result['provider']['request_transport_timeout_seconds'] = 45
        self.assertIn('V2_parent_sender_timeout_or_wall_cap_record_differs', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])

    def test_capture_counts_and_unknown_usage_policy_are_joined(self):
        read, result, provider = fixture(unclosed=True, active_at_freeze=1, summary_active=1)
        update_drain(read, result, allocations_with_unmeasured_usage=0)
        self.assertIn('V2_drain_allocations_with_unmeasured_usage_differs_from_retained_ledger_census', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])
        result['provider']['all_response_usage']['unknown_usage_is_zero'] = True
        self.assertIn('V2_parent_unknown_usage_zero_policy_record_differs', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])

    def test_provider_summary_inconsistency_prevents_a_full_measurement_claim(self):
        read, result, provider = fixture()
        provider['consistency_questions'] = ['constructed_provider_summary_difference']
        self.assertFalse(M.drain_analysis(read, PLAN, result, provider)['fully_measured_provider_consumption_claimed'])

    def test_runtime_preflight_failure_needs_no_provider_capture_but_cannot_contain_calls(self):
        read = MemoryRead({})
        result = {'status': 'runtime_preflight_failed_before_provider_or_application_calls', 'provider': {'upstream_allocations': 0}}
        self.assertEqual(M.drain_analysis(read, PLAN, result, {})['consistency_questions'], [])
        result['provider']['upstream_allocations'] = 1
        self.assertIn('runtime_preflight_failure_contains_provider_drain_or_allocations', M.drain_analysis(read, PLAN, result, {})['consistency_questions'])

    def test_missing_post_preflight_capture_record_is_detected(self):
        read, result, provider = fixture()
        del read.members['execution/provider-drain.json']
        self.assertIn('required_V2_provider_drain_record_absent', M.drain_analysis(read, PLAN, result, provider)['consistency_questions'])


class FrozenPlanControls(unittest.TestCase):
    def test_full_partial_runtime_preflight_preserves_unexecuted_case_and_error(self):
        read, result = full_fixture()
        result.update(status='runtime_preflight_failed_before_provider_or_application_calls', unexecuted_count=1,
                      error={'type': 'ValueError', 'message': 'constructed installed-version mismatch'})
        result.pop('provider_drain')
        result.pop('portable_runtime_sha256')
        result['provider'] = {'upstream_allocations': 0}
        del read.members['execution/provider-drain.json']
        del read.members['execution/portable-runtime.json']
        read.members['execution/result.json'] = json.dumps(result).encode()
        analyzed = M.analyze(read, PLAN)
        self.assertEqual(analyzed['consistency_questions'], [])
        self.assertEqual(analyzed['observed_case_outcome'], 'runtime_preflight_failed_before_provider_or_application_calls')
        self.assertEqual(analyzed['parent_case_status'], 'unexecuted')
        self.assertEqual(analyzed['case_denominator'], 1)
        self.assertEqual(analyzed['provider']['upstream_allocations'], 0)
        self.assertEqual(analyzed['parent_preflight_error']['message'], 'constructed installed-version mismatch')

    def test_full_constructed_V2_analysis_preserves_single_ungraded_case(self):
        read, _ = full_fixture()
        analyzed = M.analyze(read, PLAN)
        self.assertEqual(analyzed['consistency_questions'], [])
        self.assertEqual(analyzed['case_denominator'], 1)
        self.assertIsNone(analyzed['whole_task_grade'])
        self.assertFalse(analyzed['human_gold'])
        self.assertEqual(analyzed['run_id'], 7)

    def test_V1_schema_is_not_silently_rewritten_into_V2(self):
        read, _ = full_fixture()
        plan = copy.deepcopy(PLAN)
        plan['schema_version'] = 'ap2-native-shopper-provider-plan/1'
        read.members['plan/plan.json'] = json.dumps(plan).encode()
        with self.assertRaisesRegex(ValueError, 'explicit_V2_plan_schema_required'):
            M.check_plan(read, PLAN)

    def test_forged_source_snapshot_and_changed_plan_are_rejected(self):
        read, _ = full_fixture()
        read.members['plan/owned-source/scripts/ap2_native_shopper_provider_boundary_v2.py'] = b'constructed forged source'
        with self.assertRaisesRegex(ValueError, 'frozen_V2_owned_source_snapshot_differs'):
            M.check_plan(read, PLAN)
        read, _ = full_fixture()
        plan = copy.deepcopy(PLAN)
        plan['limits']['request_timeout_seconds'] = 121
        read.members['plan/plan.json'] = json.dumps(plan).encode()
        with self.assertRaisesRegex(ValueError, 'actual_V2_plan_differs'):
            M.check_plan(read, PLAN)

    def test_two_cases_and_boolean_denominator_are_rejected(self):
        for cases, count in (([{'case_id': M.CASE_ID}] * 2, 1), ([{'case_id': M.CASE_ID}], True)):
            read, result = full_fixture()
            result.update(cases=cases, allocated_task_count=count)
            read.members['execution/result.json'] = json.dumps(result).encode()
            with self.assertRaisesRegex(ValueError, 'single_declared_V2_result_schema_and_denominator_required'):
                M.analyze(read, PLAN)

    def test_reviewed_frozen_template_has_its_own_hash_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'constructed-template.json'
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'root_reviewed_V2_frozen_analysis_plan_differs'):
                M.frozen_plan(path)


if __name__ == '__main__':
    unittest.main()
