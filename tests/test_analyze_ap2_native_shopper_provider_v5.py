"""Constructed evidence-integrity controls; no application or provider calls."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('V5_analysis_controls', ROOT / 'scripts/analyze_ap2_native_shopper_provider_v5.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class MemoryRead:
    def __init__(self, values):
        self.values = values
        self.manifest = {name: {} for name in values}
        self.reads = {}

    def raw(self, name):
        value = self.values[name]
        return value if isinstance(value, bytes) else json.dumps(value).encode()

    def json(self, name):
        return json.loads(self.raw(name))


def event(call=None, response=None, usage=7):
    parts = []
    if call is not None:
        parts.append({'functionCall': call})
    if response is not None:
        parts.append({'functionResponse': response})
    return {'turn': 0, 'event': {'author': 'shopper', 'modelVersion': 'actual-version',
            'usageMetadata': {'totalTokenCount': usage}, 'content': {'parts': parts}}}


CALL = {'id': 'call-1', 'name': 'find_products', 'args': {'query': 'public shoes'}}


class CallIntegrityControls(unittest.TestCase):
    def test_failed_tool_attempt_is_retained_without_receipt_or_integrity_error(self):
        result = M.call_pairs([event(call=CALL)])
        self.assertEqual(result['business_call_attempts'], 1)
        self.assertEqual(result['business_terminal_responses'], 0)
        self.assertEqual(len(result['unmatched_calls']), 1)
        self.assertEqual(result['consistency_questions'], [])

    def test_transfer_terminal_does_not_count_as_business_completion(self):
        call = dict(CALL, name='transfer_to_agent')
        result = M.call_pairs([event(call=call), event(response=dict(call, response={'ok': True}))])
        self.assertEqual(result['business_call_attempts'], 0)
        self.assertEqual(result['business_terminal_responses'], 0)
        self.assertEqual(result['unmatched_calls'], [])

    def test_reordered_terminal_is_rejected(self):
        result = M.call_pairs([event(response=CALL), event(call=CALL)])
        self.assertIn('unmatched_reordered_or_duplicate_function_response', result['consistency_questions'])
        self.assertEqual(len(result['unmatched_calls']), 1)

    def test_duplicate_terminal_is_rejected(self):
        result = M.call_pairs([event(call=CALL), event(response=CALL), event(response=CALL)])
        self.assertIn('unmatched_reordered_or_duplicate_function_response', result['consistency_questions'])

    def test_reused_call_identity_is_rejected(self):
        result = M.call_pairs([event(call=CALL), event(call=CALL)])
        self.assertIn('missing_or_reused_function_call_ID', result['consistency_questions'])

    def test_mismatched_tool_name_is_rejected(self):
        result = M.call_pairs([event(call=CALL), event(response=dict(CALL, name='select_cart'))])
        self.assertEqual(len(result['unmatched_calls']), 1)
        self.assertIn('unmatched_reordered_or_duplicate_function_response', result['consistency_questions'])


class ProviderJoinControls(unittest.TestCase):
    def fixture(self, call=CALL):
        return MemoryRead({'execution/provider/001.response.json': {
            'modelVersion': 'actual-version', 'usageMetadata': {'totalTokenCount': 7},
            'candidates': [{'content': {'parts': [{'functionCall': call}]}}]}})

    def test_exact_provider_call_match(self):
        result = M.provider_call_join(self.fixture(), [event(call=CALL)])
        self.assertEqual(result['consistency_questions'], [])
        self.assertEqual(len(result['matches']), 1)

    def test_argument_change_does_not_join_by_ID_alone(self):
        result = M.provider_call_join(self.fixture(dict(CALL, args={'query': 'hidden value'})), [event(call=CALL)])
        self.assertIn('ADK_call_lacks_unique_exact_provider_match', result['consistency_questions'])
        self.assertEqual(result['matches'], [])

    def test_duplicate_provider_match_is_rejected(self):
        read = self.fixture()
        read.values['execution/provider/002.response.json'] = copy.deepcopy(read.values['execution/provider/001.response.json'])
        read.manifest['execution/provider/002.response.json'] = {}
        result = M.provider_call_join(read, [event(call=CALL)])
        self.assertIn('ADK_call_lacks_unique_exact_provider_match', result['consistency_questions'])

    def test_usage_disagreement_remains_visible(self):
        result = M.provider_call_join(self.fixture(), [event(call=CALL, usage=8)])
        self.assertIn('ADK_provider_model_version_or_usage_differs', result['consistency_questions'])

    def test_non_json_failure_does_not_become_a_call_match(self):
        read = MemoryRead({'execution/provider/001.response.json': b'unavailable'})
        result = M.provider_call_join(read, [event(call=CALL)])
        self.assertIn('ADK_call_lacks_unique_exact_provider_match', result['consistency_questions'])


class PlanBindingControls(unittest.TestCase):
    def fixture(self):
        plan = {'schema_version': 'ap2-native-shopper-provider-plan/5', 'allocated_task_count': 1,
                'public_human_facts': {'case_id': M.CASE, 'maximum_budget_USD': 100},
                'owned_sources': {'scripts/constructed.py': M.V1.digest(b'owned-source')},
                'prepared_at': 'constructed'}
        return MemoryRead({'plan/plan.json': plan, 'plan/owned-source/scripts/constructed.py': b'owned-source'}), copy.deepcopy(plan)

    def test_owned_source_mutation_fails(self):
        read, expected = self.fixture()
        read.values['plan/owned-source/scripts/constructed.py'] = b'mutated'
        with self.assertRaisesRegex(ValueError, 'frozen_owned_source_differs'):
            M.check_plan(read, expected)

    def test_typed_public_facts_drift_fails(self):
        read, expected = self.fixture()
        read.values['plan/plan.json']['public_human_facts']['maximum_budget_USD'] = '100'
        with self.assertRaisesRegex(ValueError, 'reviewed_frozen_plan_differs'):
            M.check_plan(read, expected)

    def test_bare_sha_fixture_is_rejected_against_actual_identity_schema(self):
        read, expected = self.fixture()
        bare = expected['owned_sources']['scripts/constructed.py']['sha256']
        expected['owned_sources']['scripts/constructed.py'] = bare
        read.values['plan/plan.json']['owned_sources']['scripts/constructed.py'] = bare
        with self.assertRaisesRegex(ValueError, 'frozen_owned_source_identity_schema_differs'):
            M.check_plan(read, expected)

    def test_prepared_time_is_only_allowed_plan_difference(self):
        read, expected = self.fixture()
        read.values['plan/plan.json']['prepared_at'] = 'another-constructed-time'
        self.assertEqual(M.check_plan(read, expected)['allocated_task_count'], 1)


if __name__ == '__main__':
    unittest.main()
