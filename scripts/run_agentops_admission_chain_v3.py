"""Execute frozen phases in one WSL lifetime, then export stable evidence.

The preparation and coordinator own all application acceptance rules. This
driver never retries a phase and never equates process success with successful
admission. It records its plan before execution and captures every child stream.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--export-output', type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.workspace.resolve()
    group = root / 'runs/agentops-admission-live-v1'
    stage = json.loads((group / 'stage-manifest.json').read_bytes())
    if str(root) != stage['linux_workspace']:
        raise ValueError('Workspace differs from the recorded stage allocation')
    export_output = args.export_output.resolve()
    if export_output.is_relative_to(root) or root.is_relative_to(export_output):
        raise ValueError('Export must be disjoint from the staged workspace')
    if export_output.exists():
        raise FileExistsError('Export allocation already exists')
    source = Path(__file__).resolve()
    if source != root / 'scripts/run_agentops_admission_chain_v3.py':
        raise ValueError('Run the staged chain source from its recorded workspace')
    python = stage['reuse_root'] + '/external/runtime-agentops-linux-v7/venv/bin/python'
    driver = root / 'scripts/execute_agentops_admission_phase_v3.py'
    exporter = root / 'scripts/export_agentops_admission_v3.py'
    commands = [{'phase': phase, 'argv': [python, '-B', str(driver), '--workspace', str(root), '--phase', phase]}
                for phase in ('software', 'prepare', 'preflight', 'launch', 'after')]
    export_argv = [python, '-B', str(exporter), '--workspace', str(root), '--output', str(export_output)]
    output = group / 'phase-chain'
    output.mkdir(exist_ok=False)
    (output / 'run_chain.py').write_bytes(source.read_bytes())
    plan = {'schema_version': 'agentops-admission-phase-chain/3', 'created_at_utc': now(),
            'commands': commands, 'export_argv': export_argv, 'maximum_attempts_per_phase': 1,
            'sources': [{'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                        for path in (source, driver, exporter)],
            'gate': 'Software, preparation and preflight must succeed before launch. After-inspection follows every launch outcome.',
            'application_success': 'Read attempt/result.json; successful phases do not establish application success.'}
    write_new(output / 'plan.json', plan)
    results = []
    for command in commands:
        phase = command['phase']
        item = {**command, 'started_at_utc': now(), 'returncode': None}
        write_new(output / (phase + '.started.json'), item)
        print('Starting frozen phase ' + phase, flush=True)
        with (output / (phase + '.stdout.bin')).open('xb') as stdout, (output / (phase + '.stderr.bin')).open('xb') as stderr:
            try:
                child = subprocess.Popen(command['argv'], cwd=root, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
                item['pid'] = child.pid
                item['returncode'] = child.wait()
            except OSError as error:
                item['error'] = type(error).__name__ + ': ' + str(error)
        item['finished_at_utc'] = now()
        item['streams'] = [{'path': phase + '.' + suffix + '.bin',
                            'sha256': hashlib.sha256((output / (phase + '.' + suffix + '.bin')).read_bytes()).hexdigest()}
                           for suffix in ('stdout', 'stderr')]
        write_new(output / (phase + '.receipt.json'), item)
        results.append(item)
        print(phase + ' returned ' + str(item['returncode']), flush=True)
        if phase in ('software', 'prepare', 'preflight') and item['returncode'] != 0:
            break
    succeeded = len(results) == len(commands) and all(item['returncode'] == 0 for item in results)
    report = {'schema_version': 'agentops-admission-phase-chain-result/3',
              'status': 'phases_passed' if succeeded else 'phase_failed', 'finished_at_utc': now(),
              'commands': results, 'unexecuted_phases': [x['phase'] for x in commands[len(results):]],
              'application_success': 'Read attempt/result.json; phase status is not live admission acceptance.'}
    write_new(output / 'result.json', report)
    # All files in the exported workspace are now closed and final. Exporter
    # diagnostics go to the outer parent process, outside the selected trees.
    preparation = group / 'preparation/plan.json'
    export_returncode = None
    if preparation.exists():
        print('Exporting stable workspace evidence', flush=True)
        export_returncode = subprocess.run(export_argv, cwd=root, stdin=subprocess.DEVNULL).returncode
    else:
        print('No preparation plan: export was not invoked; retained phase evidence remains in the staged workspace.', flush=True)
    print(json.dumps({'phase_status': report['status'], 'export_returncode': export_returncode}), flush=True)
    return 0 if succeeded and export_returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
