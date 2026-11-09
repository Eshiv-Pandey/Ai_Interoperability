"""Shared exact seal contract for protocol-v9 preparation and rechecking."""
import hashlib
import json
from pathlib import Path

SCHEMA = 'agentops-protocol-control-preparation/2'
SEAL_RELATIVE = 'docs/research/source-evidence/agentops-protocol-control-v1/manifest-v2.json'
PREFLIGHT_RELATIVE = 'docs/research/source-evidence/agentops-protocol-control-v1/manifest.json'
INSPECTION_RELATIVE = 'runs/agentops-native-eligibility/protocol-runtime-source-inspection-v1.json'
PRIOR_RELATIVE = 'runs/agentops-native-eligibility/linux-socket-resume-v8'
PARENT_CHECK_RELATIVE = 'runs/agentops-native-eligibility/socket-resume-parent-check-v8.json'
PREPARATION_RELATIVE = 'runs/agentops-native-eligibility/protocol-preparation-v1-5'

SOURCE_TREES = ('a2a', 'google/adk/a2a')
SOURCE_FILES = ()
REQUIRED_MODULES = {
    'a2a/client/client.py',
    'a2a/client/client_factory.py',
    'a2a/server/request_handlers/request_handler.py',
    'a2a/server/routes/common.py',
    'a2a/server/routes/jsonrpc_dispatcher.py',
    'a2a/server/routes/jsonrpc_routes.py',
    'a2a/types/a2a_pb2.py',
    'a2a/utils/version_validator.py',
    'google/adk/a2a/converters/part_converter.py',
    'google/adk/a2a/utils/agent_to_a2a.py',
}

LAUNCH_PATHS = [
    'docs/research/source-evidence/agentops-protocol-control-v1/protocol.md',
    'scripts/agentops_protocol_control_v1.py',
    'scripts/agentops_protocol_preparation_v2.py',
    'scripts/agentops_protocol_wire_v1.py',
    'scripts/check_agentops_protocol_v1.py',
    'scripts/resume_agentops_protocol_v9.py',
    'scripts/run_agentops_protocol_wsl_v9.ps1',
]

PREREQUISITE_PATHS = [
    PREFLIGHT_RELATIVE,
    'docs/research/source-evidence/agentops-socket-export-check-v8/manifest.json',
    PRIOR_RELATIVE + '/execution.json',
    PRIOR_RELATIVE + '/export-manifest.json',
    PRIOR_RELATIVE + '/result.json',
    'runs/agentops-native-eligibility/protocol-preparation-check-v1.json',
    PREPARATION_RELATIVE + '/result.json',
    PREPARATION_RELATIVE + '/tests.stderr.bin',
    PREPARATION_RELATIVE + '/tests.stdout.bin',
    INSPECTION_RELATIVE,
    PARENT_CHECK_RELATIVE,
    'scripts/check_agentops_protocol_export_v1.py',
    'scripts/check_agentops_socket_resume_v8.py',
    'scripts/inspect_agentops_protocol_sources_v1.py',
    'scripts/run_agentops_protocol_preparation_v2.py',
    'tests/test_agentops_protocol_resume_v9.py',
    'tests/test_agentops_protocol_v1.py',
]

SOFTWARE_INPUT_PATHS = sorted(set(LAUNCH_PATHS + [
    'scripts/check_agentops_protocol_export_v1.py',
    'scripts/inspect_agentops_protocol_sources_v1.py',
    'scripts/run_agentops_protocol_preparation_v2.py',
    'scripts/verify_agentops_protocol_preparation_v1.py',
    'tests/test_agentops_protocol_resume_v9.py',
    'tests/test_agentops_protocol_v1.py',
]))

HISTORICAL_PREPARATION_PATHS = [
    f'runs/agentops-native-eligibility/{folder}/{name}'
    for folder, names in (
        ('protocol-preparation-v1', ('result.json', 'test_agentops_protocol_v1.failed.py',
                                     'tests.stderr.bin', 'tests.stdout.bin')),
        ('protocol-preparation-v1-2', ('result.json', 'test_agentops_protocol_v1.failed.py',
                                       'tests.stderr.bin', 'tests.stdout.bin')),
        ('protocol-preparation-v1-3', ('result.json', 'tests.stderr.bin', 'tests.stdout.bin')),
        ('protocol-preparation-v1-4', ('result.json', 'tests.stderr.bin', 'tests.stdout.bin')),
    ) for name in names
]
ARTIFACT_PATHS = sorted(set(LAUNCH_PATHS + PREREQUISITE_PATHS
                            + HISTORICAL_PREPARATION_PATHS
                            + ['scripts/verify_agentops_protocol_preparation_v1.py']))

EXPECTED_KEYS = {
    'schema_version', 'prepared_at_utc', 'launch_inputs', 'prerequisites',
    'runtime_sources', 'artifacts', 'prior_result', 'prior_export',
    'prior_parent_check', 'preflight_manifest', 'runtime_source_inspection',
    'application_execution_performed', 'live_model_calls',
    'research_gate_credit_added', 'scope',
}


def file_record(root, name):
    root = root.resolve()
    path = (root / name).resolve()
    relative = path.relative_to(root).as_posix()
    raw = path.read_bytes()
    return {'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def verify_records(root, rows, expected_paths):
    if [row.get('path') for row in rows] != expected_paths:
        raise ValueError('Unexpected sealed path set/order')
    for row in rows:
        if file_record(root, row['path']) != row:
            raise ValueError('Changed sealed file: ' + row['path'])


def validate_runtime_rows(rows):
    if rows != sorted(rows, key=lambda row: row.get('module', '')):
        raise ValueError('Runtime sources are not sorted')
    modules = [row.get('module') for row in rows]
    if len(modules) != len(set(modules)):
        raise ValueError('Duplicate runtime source')
    if not REQUIRED_MODULES.issubset(modules):
        raise ValueError('Required runtime source omitted')
    for row in rows:
        if (set(row) != {'module', 'bytes', 'sha256'} or type(row['module']) is not str
                or not (row['module'].startswith('a2a/') or row['module'].startswith('google/adk/a2a/'))
                or type(row['bytes']) is not int or row['bytes'] < 0
                or type(row['sha256']) is not str or len(row['sha256']) != 64):
            raise ValueError('Invalid runtime-source row')


def validate_seal(root, seal, prior):
    if set(seal) != EXPECTED_KEYS or seal.get('schema_version') != SCHEMA:
        raise ValueError('Invalid protocol preparation schema')
    if (type(seal.get('prepared_at_utc')) is not str or not seal['prepared_at_utc']
            or seal.get('application_execution_performed') is not False
            or seal.get('live_model_calls') != 0
            or seal.get('research_gate_credit_added') != 0):
        raise ValueError('Invalid protocol preparation scope')
    verify_records(root, seal['launch_inputs'], LAUNCH_PATHS)
    verify_records(root, seal['prerequisites'], PREREQUISITE_PATHS)
    verify_records(root, seal['artifacts'], ARTIFACT_PATHS)
    expected_bindings = {
        'prior_result': file_record(root, PRIOR_RELATIVE + '/result.json'),
        'prior_export': file_record(root, PRIOR_RELATIVE + '/export-manifest.json'),
        'prior_parent_check': file_record(root, PARENT_CHECK_RELATIVE),
        'preflight_manifest': file_record(root, PREFLIGHT_RELATIVE),
        'runtime_source_inspection': file_record(root, INSPECTION_RELATIVE),
    }
    for key, value in expected_bindings.items():
        if seal.get(key) != value:
            raise ValueError('Wrong preparation binding: ' + key)
    inspection = json.loads((root / INSPECTION_RELATIVE).read_bytes())
    expected_python = str(Path(prior['linux_workspace']) /
        'external/runtime-agentops-linux-v7/venv/bin/python').replace('\\', '/')
    expected_site = str(Path(prior['linux_workspace']) /
        'external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages').replace('\\', '/')
    if (inspection.get('schema_version') != 'agentops-protocol-runtime-sources/1'
            or inspection.get('replica') != prior['linux_workspace']
            or inspection.get('python') != expected_python
            or inspection.get('site_packages') != expected_site
            or inspection.get('source_trees') != list(SOURCE_TREES)
            or inspection.get('source_files') != list(SOURCE_FILES)
            or inspection.get('application_imports') != 0
            or inspection.get('application_requests') != 0
            or inspection.get('live_model_calls') != 0):
        raise ValueError('Invalid runtime-source inspection')
    validate_runtime_rows(inspection.get('modules'))
    if seal.get('runtime_sources') != inspection['modules']:
        raise ValueError('Runtime sources differ from inspection')
    return inspection
