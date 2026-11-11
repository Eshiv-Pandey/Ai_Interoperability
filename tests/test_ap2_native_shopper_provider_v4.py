"""V4 public-facts/worker wiring regressions; no SDK/App/provider execution."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(version):
    spec = importlib.util.spec_from_file_location(
        'native_shopper_v' + str(version) + '_facts_control',
        ROOT / ('scripts/run_ap2_native_shopper_provider_v' + str(version) + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V3, V4 = load(3), load(4)


class PublicFactsWiringControls(unittest.TestCase):
    def test_new_worker_changes_only_case_id_and_result_schema_bytes(self):
        old = (ROOT / 'scripts/ap2_native_shopper_provider_worker_v1.py').read_bytes()
        new = V4.WORKER.read_bytes()
        old_id, new_id = b'ap2-native-shopper-provider-v1-correct-human', b'ap2-native-shopper-provider-v4-correct-human'
        old_schema, new_schema = b'ap2-native-shopper-provider-worker/1', b'ap2-native-shopper-provider-worker/2'
        self.assertEqual(old.count(old_id), 1)
        self.assertEqual(old.count(old_schema), 1)
        self.assertEqual(new, old.replace(old_id, new_id).replace(old_schema, new_schema))
        for name in ('MAX_TURNS', 'MAX_EVENTS', 'MAX_EVENT_BYTES', 'WORKER_SECONDS', 'SYNTHETIC_KEY'):
            self.assertEqual(getattr(V4.W, name), getattr(V3.W, name), name)

    def test_prior_v3_actual_worker_rejects_runner_facts_before_application_import(self):
        prior = V3.fixed_plan_fields()['public_human_facts']
        self.assertNotEqual(prior, V3.W.public_facts())
        self.assertEqual(prior['case_id'], 'ap2-native-shopper-provider-v3-correct-human')
        self.assertEqual(V3.W.public_facts()['case_id'], 'ap2-native-shopper-provider-v1-correct-human')
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            facts_path = base / 'public.json'
            facts_path.write_text(json.dumps(prior))
            with mock.patch.object(V3.W, 'application', side_effect=AssertionError('unexpected original application')) as application, \
                    mock.patch.object(V3.W, 'actor_guard', side_effect=AssertionError('unexpected actor startup')) as guard:
                with self.assertRaisesRegex(ValueError, 'only_frozen_public_human_facts_allowed'):
                    V3.W.execute(facts_path, base / 'output', base / 'original-source')
                application.assert_not_called()
                guard.assert_not_called()
            self.assertFalse((base / 'output').exists())

    def test_v4_plan_and_selected_worker_agree_in_every_public_field(self):
        prior, new = V3.fixed_plan_fields(), V4.fixed_plan_fields()
        self.assertEqual(new['public_human_facts'], V4.W.public_facts())
        self.assertEqual(new['public_human_facts']['case_id'], V4.CASE_ID)
        for name, value in prior['public_human_facts'].items():
            if name != 'case_id':
                self.assertEqual(new['public_human_facts'][name], value, name)
        proof = V4.public_facts_preflight(new)
        self.assertTrue(proof['exact_public_field_agreement'])
        self.assertTrue(proof['before_provider_smoke'])
        self.assertFalse(proof['original_application_or_SDK_imported_by_check'])
        self.assertEqual(proof['selected_worker_source_identity'], V4.H.digest(V4.WORKER.read_bytes()))

    def test_preflight_rejects_changed_public_fields_and_json_types(self):
        for field, changed in (('case_id', 'prior-case'), ('maximum_budget_USD', 101),
                               ('otp_response', '999'), ('initial_request', 'changed request'), ('cart_index', False)):
            with self.subTest(field=field):
                plan = V4.fixed_plan_fields()
                plan['public_human_facts'][field] = changed
                with self.assertRaisesRegex(ValueError, 'selected_worker_public_human_facts_mismatch'):
                    V4.public_facts_preflight(plan)

    def test_execute_fact_mismatch_stops_before_runtime_provider_smoke_or_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            plan = V4.fixed_plan_fields()
            plan['public_human_facts']['case_id'] = V3.CASE_ID
            with mock.patch.object(V4, 'check_plan', return_value=plan), \
                    mock.patch.object(V4.H, 'portable_runtime', side_effect=AssertionError('unexpected runtime')) as runtime, \
                    mock.patch.object(V4.H, 'smoke', side_effect=AssertionError('unexpected provider smoke')) as smoke, \
                    mock.patch.object(V4.B, 'ProviderBoundary', side_effect=AssertionError('unexpected provider allocation')) as boundary:
                with self.assertRaisesRegex(ValueError, 'selected_worker_public_human_facts_mismatch'):
                    V4.execute(base / 'plan', base / 'execution', base / 'python', base / 'site', base / 'pip.json', 'live')
                runtime.assert_not_called()
                smoke.assert_not_called()
                boundary.assert_not_called()
            self.assertFalse((base / 'execution').exists())

    def test_prepared_snapshot_contains_exact_selected_worker_and_detects_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan_dir = Path(temporary) / 'plan'
            V4.prepare(plan_dir)
            plan = V4.check_plan(plan_dir)
            worker = 'scripts/ap2_native_shopper_provider_worker_v2.py'
            self.assertIn(worker, plan['owned_sources'])
            self.assertEqual(plan['owned_sources'][worker], V4.H.digest(V4.WORKER.read_bytes()))
            snapshot = plan_dir / 'owned-source' / worker
            self.assertEqual(snapshot.read_bytes(), V4.WORKER.read_bytes())
            snapshot.write_bytes(b'constructed snapshot drift')
            with self.assertRaisesRegex(ValueError, 'prospective_owned_source_or_retained_snapshot_changed'):
                V4.check_plan(plan_dir)

    def test_actual_child_command_selects_the_v2_worker_and_unchanged_arguments(self):
        command = V4.worker_command(Path('/constructed/venv/bin/python'), Path('/public.json'), Path('/original-copy'), Path('/shopper'))
        self.assertEqual(command, [str(Path('/constructed/venv/bin/python')), '-B', str(V4.WORKER),
                                  '--public-human-facts', str(Path('/public.json')), '--source-root', str(Path('/original-copy')),
                                  '--output', str(Path('/shopper'))])
        self.assertEqual(Path(V4.W.__file__).resolve(), V4.WORKER.resolve())
        self.assertNotEqual(V4.WORKER, V3.V1.WORKER)

    def test_v4_actual_cli_retains_absolute_venv_launcher(self):
        class VenvLauncher:
            def absolute(self):
                return Path('/constructed/venv/bin/python')
            def resolve(self):
                return Path('/constructed/global/bin/python3.13')
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = SimpleNamespace(mode='execute', plan=base / 'plan', output=base / 'execution', python=VenvLauncher(),
                                   site_packages=base / 'site', pip_report=base / 'pip.json', provider_mode='live')
            with mock.patch.object(V4.argparse.ArgumentParser, 'parse_args', return_value=args), mock.patch.object(V4, 'execute') as executor:
                V4.main()
                self.assertEqual(executor.call_args.args[2], args.python.absolute())
                self.assertNotEqual(executor.call_args.args[2], args.python.resolve())

    def test_v4_preserves_provider_and_actor_limits_and_original_plan_fields(self):
        prior, new = V3.fixed_plan_fields(), V4.fixed_plan_fields()
        for name, value in prior.items():
            if name not in {'schema_version', 'prospective_successor_to_run', 'public_human_facts'}:
                self.assertEqual(new[name], value, name)
        self.assertEqual(new['limits'], prior['limits'])
        self.assertEqual(new['prospective_successor_to_run'], 43055390208)
        self.assertTrue(new['selected_worker_public_facts_preflight_before_provider_smoke'])
        self.assertEqual(new['selected_worker_relative_path'], 'scripts/ap2_native_shopper_provider_worker_v2.py')

    def test_agreement_receipt_precedes_runtime_failure_without_provider_allocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            plan_dir, output = base / 'plan', base / 'execution'
            V4.prepare(plan_dir)
            with mock.patch.dict(V4.os.environ, {'GOOGLE_API_KEY': 'constructed-not-provider-key'}), \
                    mock.patch.object(V4.sys, 'platform', 'linux'), \
                    mock.patch.object(V4.H, 'portable_runtime', side_effect=ValueError('constructed runtime stop')), \
                    mock.patch.object(V4.B, 'ProviderBoundary', side_effect=AssertionError('unexpected provider boundary')) as boundary:
                V4.execute(plan_dir, output, base / 'python', base / 'site', base / 'pip.json', 'live')
                boundary.assert_not_called()
            proof = json.loads((output / 'worker-public-facts-preflight.json').read_bytes())
            result = json.loads((output / 'result.json').read_bytes())
            self.assertEqual(proof['case_id'], V4.CASE_ID)
            self.assertTrue(proof['exact_public_field_agreement'])
            self.assertEqual(result['schema_version'], 'ap2-native-shopper-provider-result/4')
            self.assertEqual(result['provider']['upstream_allocations'], 0)
            self.assertEqual(result['unexecuted_count'], 1)

    def test_controls_import_no_original_application_or_official_adk(self):
        self.assertFalse(any(name == 'roles' or name.startswith(('roles.', 'google.adk')) for name in sys.modules))


if __name__ == '__main__':
    unittest.main()
