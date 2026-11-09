"""Record final software checks and seal the prospective eighteen-case matrix."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import agentops_bridge_plan_v1 as design

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'docs/research/source-evidence/agentops-bridge-control-v1'
RUNTIME_PREP = 'runs/agentops-native-eligibility/bridge-runtime-preparation-v1'
SOFTWARE = 'runs/agentops-native-eligibility/bridge-software-preparation-v1'
RUNTIME_FILES = ['graph.json', 'materialization.json', 'runtime.zip', 'archive.json',
                 'runtime-verification.json', 'runtime-bytes-verification.json', 'preparation-seal.json']
LAUNCH_FILES = [PACKAGE + '/protocol.md'] + ['scripts/' + name for name in (
    'agentops_asgi_capture_v1.py', 'serve_agentops_bridge_v1.py', 'agentops_bridge_plan_v1.py',
    'agentops_bridge_control_v1.py', 'resume_agentops_bridges_v10.py', 'check_agentops_bridge_v1.py',
    'check_agentops_bridge_group_v1.py',
    'agentops_owned_process_v1.py', 'agentops_bridge_runtime_archive_v1.py',
    'agentops_bridge_client_v1.mjs', 'agentops_mgcrea_embed_v1.mjs', 'agentops_native_profile_client_v1.mjs')]
LAUNCH_FILES += [PACKAGE + '/runtime/' + name for name in RUNTIME_FILES]
TEST_FILES = ['tests/' + name for name in (
    'test_agentops_asgi_capture_v1.py', 'test_agentops_bridge_v1.py',
    'test_agentops_bridge_runtime_v1.py', 'test_agentops_bridge_cleanup_v1.py',
    'test_agentops_bridge_supervision_v1.py', 'test_agentops_bridge_group_v1.py',
    'test_agentops_bridge_client_v1.mjs', 'test_agentops_native_profile_client_v1.mjs',
    'test_agentops_native_sdk_serialization_v1.mjs')]
SOFTWARE_FILES = sorted(set(LAUNCH_FILES + TEST_FILES + ['scripts/prepare_agentops_bridge_v1.py']))


def record(name):
    raw = (ROOT / name).read_bytes()
    return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def copy_runtime_evidence():
    target = ROOT / PACKAGE / 'runtime'
    target.mkdir(exist_ok=False)
    for name in RUNTIME_FILES:
        raw = (ROOT / RUNTIME_PREP / name).read_bytes()
        with (target / name).open('xb') as stream:
            stream.write(raw)


def software():
    if sys.platform != 'linux':
        raise ValueError('Run final tests on the selected Linux platform')
    output = ROOT / SOFTWARE
    output.mkdir(parents=True, exist_ok=False)
    inputs = [record(name) for name in SOFTWARE_FILES]
    runtime = json.loads((ROOT / RUNTIME_PREP / 'runtime-verification.json').read_bytes())
    environment = dict(os.environ, AGENTOPS_RUNTIME_ROOT=runtime['runtime_root'])
    commands = [
        ('python-bridge', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_agentops_bridge*.py', '-v']),
        ('python-observer', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_agentops_asgi_capture_v1.py', '-v']),
        ('node', ['/usr/bin/node', '--test', *[name for name in TEST_FILES if name.endswith('.mjs')]]),
    ]
    result = {'schema_version': 'agentops-bridge-software-preparation/1', 'inputs': inputs,
              'application_requests': 0, 'live_model_calls': 0, 'commands': []}
    for label, argv in commands:
        row = {'label': label, 'argv': argv, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
        try:
            process = subprocess.run(argv, cwd=ROOT, env=environment, capture_output=True, timeout=180)
            stdout, stderr = process.stdout, process.stderr
            row['returncode'] = process.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b'', error.stderr or b''
            row.update(returncode=None, timed_out=True)
        for suffix, raw in (('stdout', stdout), ('stderr', stderr)):
            with (output / f'{label}.{suffix}.bin').open('xb') as stream:
                stream.write(raw)
        row['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        row['streams'] = [record(SOFTWARE + '/' + f'{label}.{suffix}.bin') for suffix in ('stdout', 'stderr')]
        result['commands'].append(row)
        print(f'{label}: exit {row["returncode"]}', flush=True)
    result['inputs_unchanged'] = inputs == [record(name) for name in SOFTWARE_FILES]
    result['status'] = 'passed' if result['inputs_unchanged'] and all(row['returncode'] == 0 for row in result['commands']) else 'failed'
    write(output / 'result.json', result)
    raise SystemExit(0 if result['status'] == 'passed' else 1)


def seal():
    target = ROOT / PACKAGE / 'manifest.json'
    if target.exists() or (ROOT / 'runs/agentops-native-eligibility/linux-bridge-v10').exists():
        raise FileExistsError('Cannot reseal or freeze after an attempt')
    tested = json.loads((ROOT / SOFTWARE / 'result.json').read_bytes())
    if tested['status'] != 'passed' or tested['inputs'] != [record(name) for name in SOFTWARE_FILES] or not tested['inputs_unchanged']:
        raise ValueError('Exact current software preparation must pass')
    runtime = json.loads((ROOT / RUNTIME_PREP / 'runtime-verification.json').read_bytes())
    if runtime['status'] != 'runtime_files_resolution_and_imports_verified':
        raise ValueError('Verified runtime required')
    prior = json.loads((ROOT / 'runs/agentops-native-eligibility/protocol-parent-check-v9.json').read_bytes())
    if prior['status'] != 'artifact_integrity_and_semantics_verified':
        raise ValueError('Verified native v9 prerequisite required')
    prerequisites = TEST_FILES + ['scripts/prepare_agentops_bridge_v1.py', SOFTWARE + '/result.json',
        'runs/agentops-native-eligibility/linux-protocol-v9/result.json',
        'runs/agentops-native-eligibility/linux-protocol-v9/export-manifest.json',
        'runs/agentops-native-eligibility/linux-protocol-v9/execution.json',
        'runs/agentops-native-eligibility/protocol-parent-check-v9.json']
    prerequisites += [stream['path'] for row in tested['commands'] for stream in row['streams']]
    seal = {'schema_version': 'agentops-bridge-preparation/1',
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'cases': list(design.CASES.values()),
        'node': runtime['node'], 'runtime_root': runtime['runtime_root'],
        'launch_inputs': [record(name) for name in LAUNCH_FILES],
        'prerequisites': [record(name) for name in prerequisites],
        'application_requests': 0, 'live_model_calls': 0, 'research_gate_credit_added': 0,
        'scope': '18 bounded development controls; no full-interface or method-novelty claim'}
    write(target, seal)
    print(json.dumps({'status': 'sealed_not_executed', 'cases': len(seal['cases']),
                      'launch_inputs': len(seal['launch_inputs']), 'prerequisites': len(seal['prerequisites'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('copy-runtime-evidence', 'software', 'seal'))
    action = parser.parse_args().command
    {'copy-runtime-evidence': copy_runtime_evidence, 'software': software, 'seal': seal}[action]()
