"""Check public AP2 package paths and Git packaging before runtime preparation."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = 'benchmark/ap2-native-bridge-development-v13/application.json'
ACTOR = 'scripts/ap2_reference_development_v13.py'
REQUIRED_SUPPORT_FILES = (
    'benchmark/ap2-native-bridge-development-v13/evaluator.json',
    '.github/workflows/ap2-native-bridge-development-v13.yml',
    'scripts/run_ap2_native_bridge_matrix_v13.py', 'scripts/evaluate_ap2_native_bridge_matrix_v13.py',
    'tests/test_ap2_reference_development_v5.py', 'tests/test_ap2_native_bridge_development_v13.py',
    'tests/test_ap2_public_certificate_guard_v13.py', 'tests/test_ap2_worker_stage_prelude_v13.py',
    'tests/test_ap2_grpc_public_ca_v13.py', 'tests/test_ap2_owned_diagnostics_v1.py',
    'tests/test_ap2_native_guard_policy_v13.py', 'tests/test_ap2_native_package_inputs_v13.py',
    'tests/ap2_native_bridge_controls_v13.mjs',
    'benchmark/ap2-native-bridge-development-v13/public-ca-fixtures/grpcio-1.85.0/roots.pem',
    'benchmark/ap2-native-bridge-development-v13/public-ca-fixtures/grpcio-1.85.0/LICENSE.txt',
    'benchmark/ap2-native-bridge-development-v13/public-ca-fixtures/grpcio-1.85.0/provenance.json',
    'docs/research/source-evidence/ap2-v12-runtime-guard-fixtures-v1/connection.py',
    'docs/research/source-evidence/ap2-v12-runtime-guard-fixtures-v1/LICENSE.txt',
    'docs/research/source-evidence/ap2-v12-runtime-guard-fixtures-v1/provenance.json',
)


def package_path(root, relative):
    if type(relative) is not str:
        raise ValueError('public_package_path_required')
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or '\\' in relative:
        raise ValueError('public_package_path_outside_repository')
    path = root / relative
    if path.is_symlink() or path.resolve() != path or not path.is_file():
        raise ValueError('declared_public_package_input_missing_or_linked: ' + relative)
    return path


def check_tracked_paths(root, required):
    result = subprocess.run(['git', 'ls-files', '--cached', '-z', '--', *sorted(required)],
                            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise ValueError('public_package_git_index_unavailable')
    tracked = set(result.stdout.decode('utf-8').split('\x00'))
    missing = sorted(set(required) - tracked)
    if missing:
        raise ValueError('declared_public_package_input_not_in_git_index: ' + missing[0])
    return len(required)


def check_package_inputs(root=ROOT, require_tracked=False):
    root = Path(root).resolve()
    public = json.loads(package_path(root, PUBLIC).read_bytes())
    if (public['schema_version'] != 'ap2-native-bridge-development-matrix/13'
            or public['declared_cells'] != 104 or len(public['cases']) * len(public['arms']) != 104
            or public['provider_requests_allowed'] != 0):
        raise ValueError('frozen_public_104_zero_provider_package_required')
    tree = ast.parse(package_path(root, ACTOR).read_bytes())
    assignment = next(row for row in tree.body if isinstance(row, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'OWNED_COMPONENTS' for target in row.targets))
    owned = ast.literal_eval(assignment.value)
    if type(owned) is not tuple or not owned or any(type(name) is not str for name in owned):
        raise ValueError('literal_owned_package_components_required')
    required = set(owned) | set(REQUIRED_SUPPORT_FILES) | {PUBLIC, ACTOR, 'scripts/check_ap2_native_package_inputs_v13.py'}
    for relative in required:
        package_path(root, relative)
    records = public['original_outgoing_source_records']
    if len(records) != 9:
        raise ValueError('nine_original_outgoing_source_and_license_files_required')
    for original, row in records.items():
        expected_relative = 'benchmark/ap2-native-bridge-development-v13/original-outgoing-sources/' + original
        if row['retained_path'] != expected_relative:
            raise ValueError('declared_original_outgoing_source_path_changed')
        raw = package_path(root, row['retained_path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('declared_original_outgoing_source_bytes_changed')
        required.add(row['retained_path'])
    count = check_tracked_paths(root, required) if require_tracked else None
    return {'schema_version': 'ap2-public-native-package-input-check/13',
            'owned_components_accessible': len(owned), 'original_outgoing_source_and_license_files_verified': 9,
            'support_paths_accessible': len(REQUIRED_SUPPORT_FILES),
            'required_paths_in_git_index': count, 'original_application_or_provider_runs': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-tracked', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check_package_inputs(require_tracked=args.require_tracked), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
