"""Record one fresh staging phase without retrying any allocated phase."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def phase_status(report, expected_commands):
    complete = (len(report['commands']) == expected_commands
                and all(item['returncode'] == 0 for item in report['commands'])
                and report['staged_sources_unchanged'] is True)
    if report['phase'] == 'after':
        complete = complete and report.get('python_runtime_equal') is True
    return 'passed' if complete else 'failed'


def phase_commands(phase, root, reuse, python, plan):
    group = root / 'runs/agentops-admission-live-v1'
    commands = []
    if phase == 'software':
        for name in ['test_agentops_admitted_client_v1', 'test_agentops_admission_live_plan_v3',
                     'test_agentops_admission_chain_v3',
                     'test_export_agentops_admission_v3', 'test_pending_admission', 'test_refinement',
                     'test_agentops_owned_child_v1', 'test_agentops_interpreter_exit_diagnostics_v1',
                     'test_check_agentops_interpreter_exit_v2', 'test_agentops_startup_diagnostics_v1',
                     'test_check_agentops_startup_v1', 'test_refinement_scaling_generator_v1']:
            commands.append((name, [python, '-B', '-m', 'unittest', '-v', name], root))
        commands.append(('node-controller', ['/usr/bin/node', '--test', 'tests/test_agentops_admission_controller_v1.mjs'], root))
    elif phase == 'prepare':
        commands.append(('prepare', [python, '-B', 'scripts/agentops_admission_live_plan_v3.py',
            '--reuse-root', str(reuse), '--python-before', str(group / 'python-runtime-before.json'),
            '--output', str(plan.parent)], root))
    elif phase in ['preflight', 'launch']:
        commands.append((phase, [python, '-B', 'scripts/agentops_admission_control_v3.py', '--plan', str(plan)]
                         + (['--preflight-only'] if phase == 'preflight' else []), root))
    else:
        commands.append(('python-runtime-after', [python, '-I', '-B', str(reuse / 'scripts/inspect_agentops_runtime_v6.py')], reuse))
        commands.append(('verify-prepared-inputs', [python, '-B', 'scripts/agentops_admission_live_plan_v3.py', '--verify', str(plan)], root))
    return commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--phase', choices=['software', 'prepare', 'preflight', 'launch', 'after'], required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    group = root / 'runs/agentops-admission-live-v1'
    stage = json.loads((group / 'stage-manifest.json').read_bytes())
    if str(root) != stage['linux_workspace']:
        raise ValueError('Workspace does not match stage allocation')
    reuse = Path(stage['reuse_root'])
    python = str(reuse / 'external/runtime-agentops-linux-v7/venv/bin/python')
    plan = group / 'preparation/plan.json'
    output = group / ('phase-' + args.phase)
    output.mkdir(exist_ok=False)
    write(output / 'driver-source.json', {'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'source': str(Path(__file__))})
    (output / 'execute_phase.py').write_bytes(Path(__file__).read_bytes())
    environment = dict(os.environ)
    environment.update(PYTHONPATH=os.pathsep.join(str(root / folder) for folder in ['src', 'scripts', 'tests']),
                       PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
                       PATH=str(Path(python).parent) + ':/usr/bin:/bin')
    commands = phase_commands(args.phase, root, reuse, python, plan)
    report = {'phase': args.phase, 'started_at_utc': now(), 'commands': []}
    write(output / 'plan.json', {'phase': args.phase, 'created_at_utc': now(),
        'commands': [{'name': name, 'argv': argv, 'cwd': str(cwd)} for name, argv, cwd in commands]})
    for name, argv, cwd in commands:
        item = {'name': name, 'argv': argv, 'cwd': str(cwd), 'started_at_utc': now()}
        print('Running ' + name, flush=True)
        with (output / (name + '.stdout.bin')).open('xb') as stdout, (output / (name + '.stderr.bin')).open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            item['pid'] = process.pid
            item['returncode'] = process.wait()
        item['finished_at_utc'] = now()
        item['streams'] = [{'path': name + '.' + suffix + '.bin', 'sha256': hashlib.sha256((output / (name + '.' + suffix + '.bin')).read_bytes()).hexdigest()} for suffix in ['stdout', 'stderr']]
        write(output / (name + '.receipt.json'), item)
        report['commands'].append(item)
        print(name + ': ' + str(item['returncode']), flush=True)
        if item['returncode'] != 0:
            break
    changed = [row['path'] for row in stage['files'] if hashlib.sha256((root / row['path']).read_bytes()).hexdigest() != row['sha256']]
    report.update(finished_at_utc=now(), staged_sources_unchanged=not changed, changed_sources=changed)
    if args.phase == 'after' and report['commands'][0]['returncode'] == 0:
        before = json.loads((group / 'python-runtime-before.json').read_bytes())
        after = json.loads((output / 'python-runtime-after.stdout.bin').read_bytes())
        report['python_runtime_equal'] = before == after
        report['python_runtime_differing_keys'] = [key for key in set(before) | set(after) if before.get(key) != after.get(key)]
    report['status'] = phase_status(report, len(commands))
    write(output / 'result.json', report)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
