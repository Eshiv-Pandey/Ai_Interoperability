"""Record one fresh Windows stage/chain invocation; never retry or alter WSL settings."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mounted(path):
    value = str(path.resolve()).replace('\\', '/')
    if len(value) < 3 or value[1:3] != ':/':
        raise ValueError('Expected an absolute Windows drive path')
    return '/mnt/' + value[0].lower() + value[2:]


def memory():
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ('total_physical', 'available_physical',
            'total_commit', 'available_commit', 'total_virtual', 'available_virtual', 'available_extended')]
    value = Status()
    value.length = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise OSError('GlobalMemoryStatusEx failed')
    return {name: getattr(value, name) for name, _ in value._fields_}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-output', type=Path, required=True)
    parser.add_argument('--record-output', type=Path, required=True)
    parser.add_argument('--reuse-root', required=True)
    args = parser.parse_args()
    stage, output = args.stage_output.resolve(), args.record_output.resolve()
    for path in (stage, output):
        if path.exists() or not path.is_relative_to(ROOT / 'runs'):
            raise ValueError('Require new output directories inside workspace runs')
    if stage.is_relative_to(output) or output.is_relative_to(stage):
        raise ValueError('Keep stage and parent invocation directories disjoint')
    sources = [ROOT / 'scripts' / name for name in (
        'stage_agentops_admission_v3.py', 'extract_agentops_admission_stage_v1.py',
        'run_agentops_admission_chain_v3.py', 'execute_agentops_admission_phase_v3.py',
        'agentops_admission_live_plan_v3.py', 'agentops_admission_control_v3.py',
        'export_agentops_admission_v3.py', 'check_agentops_interpreter_exit_v2.py',
        'check_agentops_startup_v1.py', 'agentops_startup_diagnostics_v1.py',
        'serve_agentops_bridge_diagnostic_v4.py')]
    before = [{'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)} for path in sources]
    config = Path.home() / '.wslconfig'
    config_before = config.read_bytes()
    stage_argv = [sys.executable, '-B', str(sources[0]), '--output', str(stage), '--reuse-root', args.reuse_root]
    output.mkdir(parents=True, exist_ok=False)
    (output / 'record_attempt.py').write_bytes(Path(__file__).read_bytes())
    (output / 'wslconfig-before.bin').write_bytes(config_before)
    write_new(output / 'plan.json', {'created_at_utc': now(), 'stage_output': str(stage),
        'reuse_root': args.reuse_root, 'stage_argv': stage_argv, 'maximum_attempts': 1,
        'sources': before, 'recorder_sha256': digest(Path(__file__)), 'memory_before': memory(),
        'wslconfig_sha256': hashlib.sha256(config_before).hexdigest(), 'host_configuration_mutations': 0,
        'next_step': 'Invoke the staged v3 chain once only after successful stage/source validation; export to stage-output/export.'})
    results, errors = [], []

    def invoke(name, argv):
        record = {'name': name, 'argv': argv, 'started_at_utc': now(), 'returncode': None}
        write_new(output / (name + '.started.json'), record)
        print('Starting ' + name, flush=True)
        with (output / (name + '.stdout.bin')).open('xb') as stdout, (output / (name + '.stderr.bin')).open('xb') as stderr:
            child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            record['pid'] = child.pid
            record['returncode'] = child.wait()
        record['finished_at_utc'] = now()
        record['streams'] = [{'path': name + '.' + suffix + '.bin',
                              'sha256': digest(output / (name + '.' + suffix + '.bin'))}
                             for suffix in ('stdout', 'stderr')]
        write_new(output / (name + '.result.json'), record)
        results.append(record)
        print(name + ' returned ' + str(record['returncode']), flush=True)
        return record['returncode']

    try:
        if invoke('stage', stage_argv) != 0:
            raise ValueError('Stage did not pass; no phase chain was invoked')
        staged = json.loads((stage / 'result.json').read_bytes())
        manifest = json.loads((stage / 'stage-plan.json').read_bytes())
        linux_stage = json.loads((stage / 'linux-stage.json').read_bytes())
        if staged['status'] != 'passed' or staged['source_unchanged'] is not True:
            raise ValueError('Staging receipt did not validate unchanged sources')
        if manifest['reuse_root'] != args.reuse_root or not re.fullmatch(
                r'/var/tmp/agentops-admission-live-v1-[0-9a-f]{16}', manifest['linux_workspace']):
            raise ValueError('Unexpected stage/runtime identity')
        if (staged['linux_workspace'] != manifest['linux_workspace']
                or linux_stage['status'] != 'passed' or linux_stage['source_unchanged'] is not True
                or linux_stage['linux_workspace'] != manifest['linux_workspace']
                or linux_stage['runtime_inspection_returncode'] != 0):
            raise ValueError('Windows and Linux stage identities or inspections differ')
        for expected in before:
            matches = [row for row in manifest['files'] if row['path'] == expected['path']]
            if len(matches) != 1 or matches[0]['sha256'] != expected['sha256']:
                raise ValueError('Staged source differs from reviewed source: ' + expected['path'])
        if any(digest(ROOT / row['path']) != row['sha256'] for row in before):
            raise ValueError('Reviewed launcher inputs changed during staging')
        workspace = manifest['linux_workspace']
        chain_argv = ['wsl.exe', '-d', 'Ubuntu', '--',
            args.reuse_root + '/external/runtime-agentops-linux-v7/venv/bin/python', '-B',
            workspace + '/scripts/run_agentops_admission_chain_v3.py', '--workspace', workspace,
            '--export-output', mounted(stage / 'export')]
        invoke('chain', chain_argv)
    except Exception as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    finally:
        report = {'schema_version': 'agentops-admission-windows-invocation/3', 'finished_at_utc': now(),
            'status': 'recorded' if len(results) == 2 and all(r['returncode'] == 0 for r in results) and not errors else 'failed_or_incomplete',
            'invocations': results, 'errors': errors, 'memory_after': memory(),
            'host_configuration_mutations': 0, 'wslconfig_unchanged': config.read_bytes() == config_before,
            'reviewed_sources_unchanged': all(digest(ROOT / row['path']) == row['sha256'] for row in before),
            'application_success': 'Read exported attempt/result.json; parent or phase success is not admission acceptance.'}
        if not report['wslconfig_unchanged'] or not report['reviewed_sources_unchanged']:
            report['status'] = 'failed_or_incomplete'
            report['errors'].append('Configuration or reviewed source integrity changed during invocation')
        write_new(output / 'result.json', report)
    print(json.dumps(report), flush=True)
    return 0 if report['status'] == 'recorded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
