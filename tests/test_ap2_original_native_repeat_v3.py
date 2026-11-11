"""Controls for a new singleton allocation; no original application imports."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V2 = load('run_ap2_original_native_provider_v2')
V3 = load('run_ap2_original_native_repeat_v3')


class SingletonTests(unittest.TestCase):
    def test_only_one_fresh_repeat_and_adaptive_exposure_declared(self):
        facts = V3.task_facts()
        self.assertEqual(len(facts), 1)
        previous = next(row for row in V2.task_facts() if row['repeat_after_completed'])
        self.assertNotEqual(facts[0]['case_id'], previous['case_id'])
        self.assertEqual({k: v for k, v in facts[0].items() if k != 'case_id'},
                         {k: v for k, v in previous.items() if k != 'case_id'})
        fixed = V3.fixed_plan_fields()
        self.assertTrue(fixed['adaptive_development_followup'])
        self.assertEqual(fixed['preserved_source_run'], 42995902326)
        self.assertFalse(fixed['held_out_study'])
        self.assertFalse(fixed['human_gold_qualified'])
        self.assertEqual(fixed['limits'], V2.fixed_plan_fields()['limits'])

    def test_provider_port_runtime_and_cleanup_implementations_are_unchanged(self):
        def nodes(name):
            tree = ast.parse((ROOT / 'scripts' / (name + '.py')).read_text(encoding='utf-8'))
            return {node.name: ast.dump(node, include_attributes=False)
                    for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        before = nodes('run_ap2_original_native_provider_v2')
        after = nodes('run_ap2_original_native_repeat_v3')
        self.assertEqual(set(before), set(after))
        for name in before.keys() - {'task_facts', 'fixed_plan_fields', 'execute'}:
            with self.subTest(component=name):
                self.assertEqual(before[name], after[name])
        for name in ('MAX_CALLS', 'MIN_INTERVAL', 'MAX_REQUEST_BYTES', 'MAX_RESPONSE_BYTES',
                     'MAX_TOTAL_REQUEST_BYTES', 'MAX_TOTAL_USAGE_TOKENS', 'SERVICE_ENTRIES',
                     'MODEL', 'API_ORIGIN', 'API_PATH'):
            self.assertEqual(getattr(V2, name), getattr(V3, name))

    def test_preflight_failure_retains_one_missing_case_with_zero_provider_calls(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v3-singleton-control-') as temporary:
            base = Path(temporary).resolve()
            plan, output = base / 'plan', base / 'output'
            V3.prepare(plan)
            with mock.patch.dict(V3.os.environ, {'GOOGLE_API_KEY': 'owned-test-key-not-real'}), \
                    mock.patch.object(V3.sys, 'platform', 'linux'), \
                    mock.patch.object(V3, 'portable_runtime', side_effect=ValueError('constructed-preflight')), \
                    mock.patch.object(V3, 'ProviderBoundary', side_effect=AssertionError('unexpected provider')):
                V3.execute(plan, output, base / 'python', base / 'site', base / 'pip.json', 'live')
            result = json.loads((output / 'result.json').read_bytes())
            opening = json.loads((output / 'opening.json').read_bytes())
            self.assertEqual(result['allocated_task_count'], 1)
            self.assertEqual(result['unexecuted_count'], 1)
            self.assertEqual(len(result['cases']), 1)
            self.assertEqual(result['cases'], opening['prospective_tasks'])
            self.assertEqual(result['provider']['upstream_allocations'], 0)
            self.assertEqual(result['cases'][0]['case_id'], V3.task_facts()[0]['case_id'])


if __name__ == '__main__':
    unittest.main()
