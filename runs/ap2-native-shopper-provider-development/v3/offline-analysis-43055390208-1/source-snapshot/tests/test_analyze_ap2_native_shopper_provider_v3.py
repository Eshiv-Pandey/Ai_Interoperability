"""New V3 schema/source/preflight controls; shared drain controls stay in V2."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_shopper_V3_analysis_controls', ROOT / 'scripts/analyze_ap2_native_shopper_provider_v3.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
PLAN = M.frozen_plan()


class MemoryRead:
    def __init__(self, members):
        self.members = members
        self.manifest = {key: M.V1.digest(raw) for key, raw in members.items()}
        self.reads = {}
        self.receipt = {'run_id': 7, 'head_sha': 'constructed-V3-fixture-only', 'archive_sha256': 'constructed-V3-fixture-only'}

    def raw(self, name, optional=False):
        value = self.members.get(name)
        if value is None and not optional:
            raise ValueError('constructed_required_member_absent:' + name)
        if value is not None:
            self.reads[name] = M.V1.digest(value)
        return value

    def json(self, name, optional=False):
        raw = self.raw(name, optional)
        return json.loads(raw) if raw is not None else None

    def rows(self, name):
        raw = self.raw(name, optional=True)
        return [json.loads(line) for line in raw.splitlines() if line.strip()] if raw else []


def fixture():
    result = {'schema_version': 'ap2-native-shopper-provider-result/3', 'allocated_task_count': 1,
              'unexecuted_count': 1, 'cases': [{'case_id': M.CASE_ID, 'status': 'unexecuted'}],
              'status': 'runtime_preflight_failed_before_provider_or_application_calls',
              'error': {'type': 'ValueError', 'message': 'constructed preflight error'},
              'provider': {'upstream_allocations': 0}}
    members = {'plan/plan.json': json.dumps(PLAN).encode(), 'execution/result.json': json.dumps(result).encode()}
    for name in PLAN['owned_sources']:
        members['plan/owned-source/' + name] = (M.FROZEN_PLAN.parent / 'owned-source' / name).read_bytes()
    return MemoryRead(members), result


class V3BindingControls(unittest.TestCase):
    def test_V3_partial_preflight_preserves_error_unexecuted_task_and_zero_consumption(self):
        read, _ = fixture()
        result = M.analyze(read, PLAN)
        self.assertEqual(result['consistency_questions'], [])
        self.assertEqual(result['case_denominator'], 1)
        self.assertEqual(result['observed_case_outcome'], 'runtime_preflight_failed_before_provider_or_application_calls')
        self.assertEqual(result['parent_preflight_error']['message'], 'constructed preflight error')
        self.assertEqual(result['parent_case_status'], 'unexecuted')
        self.assertEqual(result['provider']['upstream_allocations'], 0)
        self.assertIsNone(result['whole_task_grade'])
        self.assertFalse(result['human_gold'])
        self.assertEqual(result['inherited_boundary_drain_schema'], 'ap2-provider-drain/2')

    def test_V2_plan_or_case_cannot_be_rewritten_into_V3(self):
        for update in ({'schema_version': 'ap2-native-shopper-provider-plan/2'}, {'public_human_facts': dict(PLAN['public_human_facts'], case_id='ap2-native-shopper-provider-v2-correct-human')}):
            read, _ = fixture()
            plan = copy.deepcopy(PLAN)
            plan.update(update)
            read.members['plan/plan.json'] = json.dumps(plan).encode()
            with self.assertRaises(ValueError):
                M.check_plan(read, PLAN)

    def test_forged_V3_runner_snapshot_is_rejected(self):
        read, _ = fixture()
        read.members['plan/owned-source/scripts/run_ap2_native_shopper_provider_v3.py'] = b'constructed forged V3 runner'
        with self.assertRaisesRegex(ValueError, 'frozen_V3_owned_source_snapshot_differs'):
            M.check_plan(read, PLAN)

    def test_frozen_launcher_public_facts_and_owned_membership_are_bound(self):
        for key, value in (('original_venv_interpreter_symlink_preserved', False), ('public_human_facts', dict(PLAN['public_human_facts'], maximum_budget_USD=101)), ('owned_sources', {name: identity for name, identity in PLAN['owned_sources'].items() if name != 'scripts/run_ap2_native_shopper_provider_v3.py'})):
            read, _ = fixture()
            plan = copy.deepcopy(PLAN)
            plan[key] = value
            read.members['plan/plan.json'] = json.dumps(plan).encode()
            with self.assertRaisesRegex(ValueError, 'actual_V3_plan_differs'):
                M.check_plan(read, PLAN)

    def test_V2_result_schema_and_multiple_case_denominator_are_rejected(self):
        for update in ({'schema_version': 'ap2-native-shopper-provider-result/2'}, {'cases': [{'case_id': M.CASE_ID}] * 2}, {'allocated_task_count': True}):
            read, result = fixture()
            result.update(update)
            read.members['execution/result.json'] = json.dumps(result).encode()
            with self.assertRaisesRegex(ValueError, 'single_declared_V3_result_schema_and_denominator_required'):
                M.analyze(read, PLAN)

    def test_preflight_claim_with_executed_case_is_detected(self):
        read, result = fixture()
        result['cases'][0]['status'] = 'executed_returned'
        read.members['execution/result.json'] = json.dumps(result).encode()
        self.assertIn('V3_runtime_preflight_failure_has_executed_case_or_application_observations', M.analyze(read, PLAN)['consistency_questions'])

    def test_root_reviewed_V3_template_identity_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'constructed-V3-template.json'
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'root_reviewed_V3_frozen_analysis_plan_differs'):
                M.frozen_plan(path)


if __name__ == '__main__':
    unittest.main()
