"""Launcher-path regression controls; no original SDK/app/provider execution."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(version):
    spec = importlib.util.spec_from_file_location(
        'native_shopper_v' + str(version) + '_launcher_control',
        ROOT / ('scripts/run_ap2_native_shopper_provider_v' + str(version) + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V2, V3 = load(2), load(3)


class LauncherControls(unittest.TestCase):
    def test_actual_cli_preserves_venv_launcher_instead_of_resolved_global_binary(self):
        class VenvLauncher:
            def absolute(self):
                return Path('/constructed/venv/bin/python')

            def resolve(self):
                return Path('/constructed/global/bin/python3.13')

        # Invoke each actual CLI with its executor replaced. This reproduces the
        # owned path-selection defect without executing a Python runtime/app.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            args = SimpleNamespace(mode='execute', plan=base / 'plan', output=base / 'execution',
                                   python=VenvLauncher(), site_packages=base / 'site-packages',
                                   pip_report=base / 'pip.json', provider_mode='live')
            for module, expected in ((V2, args.python.resolve()), (V3, args.python.absolute())):
                with mock.patch.object(module.argparse.ArgumentParser, 'parse_args', return_value=args), \
                        mock.patch.object(module, 'execute') as executor:
                    module.main()
                    self.assertEqual(executor.call_args.args[2], expected)
            self.assertNotEqual(args.python.absolute(), args.python.resolve())

    def test_real_symlink_keeps_venv_entry_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            global_binary = base / 'global-python'
            global_binary.write_bytes(b'constructed executable path only')
            launcher = base / 'venv-python'
            try:
                launcher.symlink_to(global_binary)
            except OSError as error:
                if os.name != 'nt':
                    raise
                self.skipTest('Local symlink creation unavailable: ' + type(error).__name__)
            args = SimpleNamespace(mode='execute', plan=base / 'plan', output=base / 'execution',
                                   python=launcher, site_packages=base / 'site-packages',
                                   pip_report=base / 'pip.json', provider_mode='live')
            with mock.patch.object(V3.argparse.ArgumentParser, 'parse_args', return_value=args), \
                    mock.patch.object(V3, 'execute') as executor:
                V3.main()
                self.assertEqual(executor.call_args.args[2], launcher.absolute())
                self.assertNotEqual(executor.call_args.args[2], global_binary.resolve())

    def test_successor_preserves_original_runtime_actor_limits_and_timeout(self):
        prior, new = V2.fixed_plan_fields(), V3.fixed_plan_fields()
        changed = {'schema_version', 'prospective_successor_to_run', 'public_human_facts'}
        for name in prior:
            if name not in changed:
                self.assertEqual(prior[name], new[name], name)
        for name in prior['public_human_facts']:
            if name != 'case_id':
                self.assertEqual(prior['public_human_facts'][name], new['public_human_facts'][name], name)
        self.assertEqual(new['prospective_successor_to_run'], 43045731741)
        self.assertEqual(new['limits']['request_timeout_seconds'], 120)
        self.assertTrue(new['original_venv_interpreter_symlink_preserved'])
        self.assertTrue(new['inherited_v2_case_unexecuted_before_provider_and_application_calls'])

    def test_prepared_successor_freezes_the_actual_launcher_source_and_original_versions(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / 'plan'
            V3.prepare(plan)
            value = V3.check_plan(plan)
            self.assertEqual(value['versions'], V2.H.expected_versions())
            source = 'scripts/run_ap2_native_shopper_provider_v3.py'
            self.assertIn(source, value['owned_sources'])
            self.assertNotIn('scripts/run_ap2_native_shopper_provider_v2.py', value['owned_sources'])
            changed = json.loads((plan / 'plan.json').read_bytes())
            changed['original_venv_interpreter_symlink_preserved'] = False
            (plan / 'plan.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'prospective_fixed_plan'):
                V3.check_plan(plan)


if __name__ == '__main__':
    unittest.main()
