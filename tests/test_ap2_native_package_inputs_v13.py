"""Public fixture and Git-index packaging controls; no original apps execute."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_ap2_native_package_inputs_v13 as checker


def normalized_to_v12(text):
    schemas = ('agentops-bridge-diagnostic-group', 'ap2-declared-public-certificate-admission', 'ap2-independent-native-bridge-matrix-evaluation', 'ap2-independent-native-bridge-smoke-evaluation', 'ap2-native-bridge-allocation', 'ap2-native-bridge-client', 'ap2-native-bridge-development-matrix', 'ap2-native-bridge-development-private-evaluator', 'ap2-native-bridge-development', 'ap2-native-bridge-execution', 'ap2-native-bridge-initiation', 'ap2-native-guard-policy', 'ap2-offline-native-application-runtime', 'ap2-original-outgoing-map', 'ap2-owned-native-socket', 'ap2-owned-native-sockets')
    modules = ('ap2_reference_development', 'ap2_public_certificate_guard', 'ap2_native_guard_policy', 'ap2_native_bridge_runtime', 'ap2_bridge_client', 'ap2_bridge_network_guard', 'ap2_native_transport', 'run_ap2_native_bridge_matrix', 'evaluate_ap2_native_bridge_matrix', 'check_ap2_native_package_inputs', 'ap2_native_bridge_controls')
    for name in schemas:
        text = text.replace(name + "/13", name + "/12")
    for name in modules:
        text = text.replace(name + "_v13", name + "_v12")
    return text.replace("ap2-native-bridge-development-v13", "ap2-native-bridge-development-v12").replace("ap2-offline-v13-private-", "ap2-offline-v12-private-").replace("AP2 V13", "AP2 V12")


class PackageInputControls(unittest.TestCase):
    def fixture(self, base):
        base = Path(base)
        public = json.loads((ROOT / checker.PUBLIC).read_bytes())
        target = base / checker.PUBLIC; target.parent.mkdir(parents=True); target.write_text(json.dumps(public))
        actor = base / checker.ACTOR; actor.parent.mkdir(parents=True)
        actor.write_text("OWNED_COMPONENTS = ('scripts/ap2_reference_development_v13.py', 'scripts/check_ap2_native_package_inputs_v13.py')\n")
        (base / 'scripts/check_ap2_native_package_inputs_v13.py').write_text('# Constructed package-only placeholder\n')
        for relative in checker.REQUIRED_SUPPORT_FILES:
            target = base / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('# Constructed support-path placeholder\n')
        for row in public['original_outgoing_source_records'].values():
            target = base / row['retained_path']; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / row['retained_path']).read_bytes())
        return public

    def test_all_actual_candidate_declared_owned_and_original_source_paths_are_accessible(self):
        result = checker.check_package_inputs()
        self.assertEqual(result['original_outgoing_source_and_license_files_verified'], 9)
        self.assertEqual(result['original_application_or_provider_runs'], 0)

    def test_missing_or_changed_declared_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v13-package-path-control-') as temp:
            public = self.fixture(temp); relative = next(iter(public['original_outgoing_source_records'].values()))['retained_path']
            target = Path(temp) / relative; raw = target.read_bytes(); target.unlink()
            with self.assertRaisesRegex(ValueError, 'declared_public_package_input_missing_or_linked'):
                checker.check_package_inputs(temp)
            target.write_bytes(raw + b'\nChanged public source\n')
            with self.assertRaisesRegex(ValueError, 'declared_original_outgoing_source_bytes_changed'):
                checker.check_package_inputs(temp)

    def test_absent_owned_component_is_rejected_before_any_runtime_prepare(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v13-owned-path-control-') as temp:
            self.fixture(temp)
            (Path(temp) / 'scripts/check_ap2_native_package_inputs_v13.py').unlink()
            with self.assertRaisesRegex(ValueError, 'declared_public_package_input_missing_or_linked'):
                checker.check_package_inputs(temp)

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable for constructed index control')
    def test_ignored_local_file_fails_git_index_check_until_explicitly_staged(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v13-git-packaging-control-') as temp:
            base = Path(temp); relative = 'public/original-source/external/fixture.ts'
            target = base / relative; target.parent.mkdir(parents=True); target.write_text('// Constructed public fixture\n')
            (base / '.gitignore').write_text('**/external/*\n')
            subprocess.run(['git', 'init', '-q', str(base)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['git', '-C', str(base), 'add', '--', '.gitignore'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with self.assertRaisesRegex(ValueError, 'declared_public_package_input_not_in_git_index'):
                checker.check_tracked_paths(base, {relative})
            subprocess.run(['git', '-C', str(base), 'add', '-f', '--', relative], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(checker.check_tracked_paths(base, {relative}), 1)

    def test_V13_guard_runtime_and_evaluator_are_only_version_retags_of_V12(self):
        for name in ['scripts/ap2_native_guard_policy_v12.py', 'scripts/ap2_native_bridge_runtime_v12.py',
                     'scripts/ap2_public_certificate_guard_v12.py', 'scripts/evaluate_ap2_native_bridge_matrix_v12.py',
                     'src/interoperability/ap2_native_transport_v12.py']:
            old = (ROOT / name).read_text()
            new = normalized_to_v12((ROOT / name.replace('v12', 'v13')).read_text())
            self.assertEqual(ast.dump(ast.parse(old), include_attributes=False), ast.dump(ast.parse(new), include_attributes=False), name)
        for name in ["scripts/ap2_bridge_client_v12.mjs", "scripts/ap2_bridge_network_guard_v12.mjs", "tests/ap2_native_bridge_controls_v12.mjs"]:
            self.assertEqual((ROOT / name).read_text(), normalized_to_v12((ROOT / name.replace("v12", "v13")).read_text()), name)
        candidate = ast.parse(normalized_to_v12((ROOT / 'scripts/ap2_reference_development_v13.py').read_text()))
        assignment = next(row for row in candidate.body if isinstance(row, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == 'OWNED_COMPONENTS' for target in row.targets))
        assignment.value.elts = [row for row in assignment.value.elts
                                 if not (isinstance(row, ast.Constant) and row.value == 'scripts/check_ap2_native_package_inputs_v12.py')]
        original = ast.parse((ROOT / 'scripts/ap2_reference_development_v12.py').read_bytes())
        self.assertEqual(ast.dump(original, include_attributes=False), ast.dump(candidate, include_attributes=False))
        prelude = ast.parse((ROOT / 'tests/test_ap2_worker_stage_prelude_v13.py').read_bytes())
        actor_calls = [row.args[0].value for row in ast.walk(prelude) if isinstance(row, ast.Call)
                       and isinstance(row.func, ast.Name) and row.func.id == 'load_actor']
        self.assertEqual(actor_calls, [9, 13, 13, 13])


if __name__ == '__main__':
    unittest.main()
