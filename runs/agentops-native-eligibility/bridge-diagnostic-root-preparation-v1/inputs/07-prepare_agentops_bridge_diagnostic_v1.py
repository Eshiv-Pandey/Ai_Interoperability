"""Validate and freeze the new shutdown diagnostic before any application launch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import agentops_bridge_diagnostic_plan_v1 as design
from check_agentops_bridge_group_v1 import validate_preparation as validate_original

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'docs/research/source-evidence/agentops-bridge-diagnostic-v1'
PRIOR = 'runs/agentops-native-eligibility/linux-bridge-v10'
SOFTWARE = 'runs/agentops-native-eligibility/bridge-diagnostic-software-v1'
LAUNCH_FILES = [PACKAGE + '/protocol.md'] + ['scripts/' + name for name in (
    'agentops_shutdown_diagnostics_v2.py', 'serve_agentops_bridge_diagnostic_v2.py',
    'agentops_bridge_diagnostic_plan_v1.py', 'agentops_bridge_diagnostic_control_v1.py',
    'resume_agentops_bridge_diagnostic_v11.py', 'check_agentops_bridge_diagnostic_v1.py',
    'check_agentops_bridge_diagnostic_group_v1.py')]
TEST_FILES = ['tests/' + name for name in (
    'test_agentops_shutdown_diagnostics_v2.py', 'test_agentops_bridge_diagnostic_v1.py',
    'test_agentops_bridge_diagnostic_supervision_v1.py',
    'test_agentops_bridge_diagnostic_group_v1.py')]
SOFTWARE_FILES = LAUNCH_FILES + TEST_FILES + ['scripts/prepare_agentops_bridge_diagnostic_v1.py']
PATTERNS = ['test_agentops_shutdown_diagnostics_v2.py', 'test_agentops_bridge_diagnostic_v1.py',
            'test_agentops_bridge_diagnostic_supervision_v1.py',
            'test_agentops_bridge_diagnostic_group_v1.py']


def record(name):
    raw = (ROOT / name).read_bytes()
    return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def software(output):
    if sys.platform != 'linux' or sys.version_info[:2] != (3, 13):
        raise ValueError('Use the existing pinned Linux Python 3.13 runtime')
    output = (ROOT / output).resolve()
    if not output.is_relative_to(ROOT / 'runs/agentops-native-eligibility'):
        raise ValueError('Software output must stay within the research run directory')
    output.mkdir(exist_ok=False)
    (output / 'inputs').mkdir()
    inputs = [record(name) for name in SOFTWARE_FILES]
    for index, row in enumerate(inputs):
        (output / 'inputs' / f'{index:02d}-{Path(row["path"]).name}').write_bytes((ROOT / row['path']).read_bytes())
    result = {'schema_version': 'agentops-bridge-diagnostic-software/1', 'status': 'failed',
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'inputs': inputs,
              'application_requests': 0, 'live_model_calls': 0, 'commands': []}
    write(output / 'execution.json', result)
    for index, pattern in enumerate(PATTERNS, 1):
        label = f'stage-{index}'
        argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
        row = {'label': label, 'argv': argv, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
               'timed_out': False}
        with (output / (label + '.stdout.bin')).open('xb') as stdout, \
                (output / (label + '.stderr.bin')).open('xb') as stderr:
            try:
                process = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=120)
                row['returncode'] = process.returncode
            except subprocess.TimeoutExpired:
                row.update(returncode=None, timed_out=True)
        row['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        row['streams'] = [record((output / (label + '.' + suffix + '.bin')).relative_to(ROOT).as_posix())
                          for suffix in ('stdout', 'stderr')]
        result['commands'].append(row)
        print(f'{label}: exit {row["returncode"]}', flush=True)
    result['inputs_unchanged'] = inputs == [record(name) for name in SOFTWARE_FILES]
    result['status'] = 'passed' if result['inputs_unchanged'] and all(
        row['returncode'] == 0 and not row['timed_out'] for row in result['commands']) else 'failed'
    result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    write(output / 'result.json', result)
    return result['status'] == 'passed'


def seal(software_dir):
    target = ROOT / PACKAGE / 'manifest.json'
    if target.exists() or (ROOT / 'runs/agentops-native-eligibility/linux-bridge-diagnostic-v11').exists():
        raise FileExistsError('Cannot freeze after any prior seal or diagnostic attempt')
    original, runtime = validate_original(ROOT)
    tested_path = (ROOT / software_dir / 'result.json').resolve()
    if not tested_path.is_relative_to(ROOT / 'runs/agentops-native-eligibility'):
        raise ValueError('Unexpected software receipt location')
    tested = json.loads(tested_path.read_bytes())
    if (tested['status'] != 'passed' or not tested['inputs_unchanged']
            or tested['inputs'] != [record(name) for name in SOFTWARE_FILES]):
        raise ValueError('Exact diagnostic software must pass before freezing')
    reuse = json.loads((ROOT / PRIOR / 'execution.json').read_bytes())['inputs']
    for row in reuse:
        if record(row['path']) != row:
            raise ValueError('Reused v10 input changed: ' + row['path'])
    prerequisites = TEST_FILES + ['scripts/prepare_agentops_bridge_diagnostic_v1.py',
        tested_path.relative_to(ROOT).as_posix(), PRIOR + '/result.json',
        PRIOR + '/execution.json', PRIOR + '/export-manifest.json',
        'runs/agentops-native-eligibility/bridge-parent-check-v10.json',
        'runs/agentops-native-eligibility/bridge-resume-audit-v1/result.json']
    prerequisites += [row['path'] for command in tested['commands'] for row in command['streams']]
    value = {'schema_version': 'agentops-bridge-diagnostic-preparation/1',
             'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
             'cases': list(design.CASES.values()), 'case_prefix': design.CASE_PREFIX,
             'runtime_root': runtime['runtime_root'], 'node': runtime['node'],
             'launch_inputs': [record(name) for name in LAUNCH_FILES], 'reuse_inputs': reuse,
             'prerequisites': [record(name) for name in prerequisites],
             'software': record(tested_path.relative_to(ROOT).as_posix()),
             'application_requests': 0, 'live_model_calls': 0, 'research_gate_credit_added': 0,
             'scope': 'Three fresh diagnostic controls; no replacement of v10, new qualification or novelty claim'}
    write(target, value)
    print(json.dumps({'status': 'sealed_not_executed', 'cases': list(design.CASES),
                      'launch_files': len(value['launch_inputs']), 'reused_inputs': len(reuse)}))
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('software', 'seal'))
    parser.add_argument('--software', default=SOFTWARE)
    args = parser.parse_args()
    raise SystemExit(0 if {'software': software, 'seal': seal}[args.command](args.software) else 1)
