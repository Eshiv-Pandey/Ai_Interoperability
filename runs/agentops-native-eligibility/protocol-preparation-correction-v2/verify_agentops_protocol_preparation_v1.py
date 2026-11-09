"""Verify the sealed protocol-v9 preparation without executing AgentOps."""
import argparse
import base64
import csv
import io
import json
from pathlib import Path
from pathlib import PurePosixPath

import check_agentops_socket_resume_v8 as prior
import inspect_agentops_protocol_sources_v1 as source_inspector
import resume_agentops_protocol_v9 as resume
from check_agentops_linux_workspace_v5 import load, relative_file, require, verify_rows
from run_agentops_linux_workspace_v5 import record

ROOT = resume.ROOT
PREPARATION = ROOT / 'runs/agentops-native-eligibility/protocol-preparation-v1-5'
INSPECTION = ROOT / 'runs/agentops-native-eligibility/protocol-runtime-source-inspection-v1.json'
MODULE_PREFIX = 'external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages/'

LAUNCH_PATHS = [
    'docs/research/source-evidence/agentops-protocol-control-v1/protocol.md',
    'scripts/agentops_protocol_control_v1.py',
    'scripts/agentops_protocol_wire_v1.py',
    'scripts/check_agentops_protocol_v1.py',
    'scripts/resume_agentops_protocol_v9.py',
    'scripts/run_agentops_protocol_wsl_v9.ps1',
]

PREREQUISITE_PATHS = [
    'docs/research/source-evidence/agentops-protocol-control-v1/manifest.json',
    'docs/research/source-evidence/agentops-socket-export-check-v8/manifest.json',
    'runs/agentops-native-eligibility/linux-socket-resume-v8/execution.json',
    'runs/agentops-native-eligibility/linux-socket-resume-v8/export-manifest.json',
    'runs/agentops-native-eligibility/linux-socket-resume-v8/result.json',
    'runs/agentops-native-eligibility/protocol-preparation-check-v1.json',
    'runs/agentops-native-eligibility/protocol-preparation-v1-5/result.json',
    'runs/agentops-native-eligibility/protocol-preparation-v1-5/tests.stderr.bin',
    'runs/agentops-native-eligibility/protocol-preparation-v1-5/tests.stdout.bin',
    'runs/agentops-native-eligibility/protocol-runtime-source-inspection-v1.json',
    'runs/agentops-native-eligibility/socket-resume-parent-check-v8.json',
    'scripts/check_agentops_protocol_export_v1.py',
    'scripts/check_agentops_socket_resume_v8.py',
    'scripts/inspect_agentops_protocol_sources_v1.py',
    'tests/test_agentops_protocol_v1.py',
    'tests/test_agentops_protocol_resume_v9.py',
]


def runtime_rows(prior_result):
    inspection = load(INSPECTION)
    require(inspection['schema_version'] == 'agentops-protocol-runtime-sources/1'
            and inspection['replica'] == prior_result['linux_workspace'], 'Runtime-source inspection binding')
    site = PurePosixPath(prior_result['linux_workspace']) / MODULE_PREFIX
    require(inspection['python'] == str(PurePosixPath(prior_result['linux_workspace']) /
                'external/runtime-agentops-linux-v7/venv/bin/python')
            and inspection['site_packages'] == str(site)
            and inspection['source_trees'] == list(source_inspector.SOURCE_TREES)
            and inspection['source_files'] == list(source_inspector.SOURCE_FILES), 'Runtime-source inspection scope')
    rows = inspection['modules']
    require(rows == sorted(rows, key=lambda row: row['module'])
            and len(rows) == len({row['module'] for row in rows}), 'Ordered unique runtime sources')
    require(all(set(row) == {'module', 'bytes', 'sha256'} and type(row['bytes']) is int
                and row['bytes'] >= 0 and len(row['sha256']) == 64 for row in rows), 'Runtime-source row shape')
    return rows


def verify_distribution_records(exported, inventory, rows):
    wanted = {MODULE_PREFIX + row['module']: row for row in rows}
    owners = {name: [] for name in wanted}
    for package in inventory['packages']:
        records = [row for row in package['metadata_files'] if PurePosixPath(row['path']).name == 'RECORD']
        for record_row in records:
            entries = list(csv.reader(io.StringIO(
                relative_file(exported, record_row['path']).read_text(encoding='utf-8'))))
            for name, source in wanted.items():
                try:
                    relative = PurePosixPath(name).relative_to(package['location']).as_posix()
                except ValueError:
                    continue
                matches = [entry for entry in entries if entry and entry[0] == relative]
                if not matches:
                    continue
                require(len(matches) == 1 and len(matches[0]) == 3, 'Ambiguous runtime RECORD entry')
                expected_hash = 'sha256=' + base64.urlsafe_b64encode(
                    bytes.fromhex(source['sha256'])).decode().rstrip('=')
                require(matches[0][1:] == [expected_hash, str(source['bytes'])],
                        'Runtime source differs from installed RECORD: ' + name)
                owners[name].append(package['name'])
    require(all(len(value) == 1 for value in owners.values()), 'Runtime source lacks one RECORD owner')


def check():
    seal = load(resume.SEAL)
    require(seal.get('schema_version') == 'agentops-protocol-control-preparation/2', 'Preparation schema')
    require([row['path'] for row in seal['launch_inputs']] == LAUNCH_PATHS, 'Exact launch-input order/set')
    require([row['path'] for row in seal['prerequisites']] == PREREQUISITE_PATHS, 'Exact prerequisite order/set')
    verify_rows(ROOT, seal['launch_inputs'] + seal['prerequisites'])

    prior_result = load(resume.PRIOR / 'result.json')
    require(prior_result['status'] == 'native_and_http_controls_passed'
            and prior_result['export_reference_failures'] == [], 'Passed v8 prerequisite')
    require(seal['prior_result'] == record(resume.PRIOR / 'result.json', ROOT)
            and seal['prior_export'] == record(resume.PRIOR / 'export-manifest.json', ROOT)
            and seal['prior_parent_check'] == record(
                ROOT / 'runs/agentops-native-eligibility/socket-resume-parent-check-v8.json', ROOT),
            'Prior evidence bindings')
    require(seal['preflight_manifest'] == record(
                ROOT / 'docs/research/source-evidence/agentops-protocol-control-v1/manifest.json', ROOT)
            and seal['runtime_source_inspection'] == record(INSPECTION, ROOT), 'Preserved preflight bindings')
    require(prior.check(resume.PRIOR)['status'] == 'artifact_integrity_and_semantics_verified',
            'Read-only v8 prerequisite recheck')

    preparation = load(PREPARATION / 'result.json')
    stderr = (PREPARATION / 'tests.stderr.bin').read_text(encoding='utf-8')
    require(preparation['returncode'] == 0 and 'Ran 18 tests' in stderr
            and stderr.rstrip().endswith('OK'), 'Constructed protocol tests')

    export_manifest = load(resume.PRIOR / 'export-manifest.json')
    expected_runtime = runtime_rows(prior_result)
    require(seal['runtime_sources'] == expected_runtime, 'Exact installed protocol-module pins')
    inventory = load(resume.PRIOR / 'workspace' / prior.NATIVE / 'prepared-runtime.stdout.bin')
    verify_distribution_records(resume.PRIOR / 'workspace', inventory, expected_runtime)
    retained = {row['path']: row for row in export_manifest['files']}
    retained_rows = [retained[MODULE_PREFIX + row['module']] for row in expected_runtime
                     if MODULE_PREFIX + row['module'] in retained]
    verify_rows(resume.PRIOR / 'workspace', retained_rows)

    require(seal.get('application_execution_performed') is False
            and seal.get('live_model_calls') == 0
            and seal.get('research_gate_credit_added') == 0, 'Preparation scope')
    require(not resume.OUTPUT.exists(), 'Protocol-v9 attempt already exists')
    return {
        'status': 'preparation_and_prior_integrity_verified',
        'launch_inputs': len(seal['launch_inputs']),
        'prerequisites': len(seal['prerequisites']),
        'runtime_sources': len(seal['runtime_sources']),
        'constructed_tests': 18,
        'prior_export_files': len(export_manifest['files']),
        'runtime_sources_already_exported': len(retained_rows),
        'v9_attempt_exists': False,
        'application_execution_performed': False,
        'scientific_gate_credit_added': 0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve the earlier preparation check')
    report = {'schema_version': 'agentops-protocol-preparation-check/1', 'status': 'failed'}
    try:
        report.update(check())
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'preparation_and_prior_integrity_verified' else 1)
