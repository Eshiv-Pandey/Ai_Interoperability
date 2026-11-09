"""Append native protocol cases to the existing Linux replica; export all evidence."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import agentops_native_probe_v2 as evidence
import agentops_protocol_preparation_v2 as preparation
import run_agentops_linux_workspace_v5 as previous
from export_agentops_workspace_v7 import export_evidence

ROOT = evidence.WORKSPACE
PRIOR = ROOT / 'runs/agentops-native-eligibility/linux-socket-resume-v8'
OUTPUT = ROOT / 'runs/agentops-native-eligibility/linux-protocol-v9'
SEAL = ROOT / 'docs/research/source-evidence/agentops-protocol-control-v1/manifest-v2.json'


def verify_unchanged(rows, base=ROOT):
    for row in rows:
        if previous.record(previous.relative_file(base, row['path']), base) != row:
            raise ValueError('Changed file: ' + row['path'])


def cleanup_owned_service(replica, case):
    record_path = replica / f'runs/agentops-http-control/protocol-v1-{case}/service-process.json'
    if not record_path.exists():
        return
    owned = evidence.load_json(record_path)
    if type(owned.get('pid')) is not int or owned['pid'] <= 0:
        raise ValueError('Invalid owned service PID')
    cmdline = Path(f'/proc/{owned["pid"]}/cmdline')
    if not cmdline.exists():
        return
    actual = cmdline.read_bytes().rstrip(b'\0').decode().split('\0')
    expected = [str(replica / 'external/runtime-agentops-linux-v7/venv/bin/python'), '-B',
        str(replica / 'scripts/serve_agentops_http_v2.py'), '--output',
        str(replica / f'runs/agentops-http-control/protocol-v1-{case}'), '--port',
        '18762' if case == 'sync' else '18763']
    if actual != owned.get('argv') or actual != expected:
        raise ValueError('Cannot verify owned service for cleanup')
    os.killpg(owned['pid'], signal.SIGKILL)


def capture(replica, case):
    environment = evidence.clean_environment(OUTPUT)
    environment['PYTHONPATH'] = str(replica / 'scripts')
    for name in ('TEMP', 'TMP', 'TMPDIR'):
        environment[name] = str(replica / 'protocol-temp-v9')
    argv = [sys.executable, '-B', '-X', 'utf8', 'scripts/agentops_protocol_control_v1.py', case]
    receipt = {'argv': argv, 'cwd': str(replica), 'started_at_utc': evidence.now(), 'timed_out': False}
    process = None
    cleanup_errors = []
    with (OUTPUT / f'{case}.stdout.bin').open('xb') as stdout, (OUTPUT / f'{case}.stderr.bin').open('xb') as stderr:
        try:
            process = subprocess.Popen(argv, cwd=replica, env=environment, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True)
            receipt['pid'] = process.pid
            evidence.write_json(OUTPUT / f'{case}.started.json', receipt)
            receipt['returncode'] = process.wait(timeout=600)
        except BaseException as error:
            receipt['capture_error'] = f'{type(error).__name__}: {error}'
            receipt['timed_out'] = isinstance(error, subprocess.TimeoutExpired)
            try:
                cleanup_owned_service(replica, case)
            except Exception as cleanup_error:
                cleanup_errors.append(f'service: {type(cleanup_error).__name__}: {cleanup_error}')
        finally:
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except Exception as cleanup_error:
                    cleanup_errors.append(f'controller-signal: {type(cleanup_error).__name__}: {cleanup_error}')
                try:
                    process.wait(timeout=15)
                except Exception as cleanup_error:
                    cleanup_errors.append(f'controller-wait: {type(cleanup_error).__name__}: {cleanup_error}')
            receipt['returncode'] = None if process is None else process.returncode
            receipt['finished_at_utc'] = evidence.now()
    if cleanup_errors:
        receipt['cleanup_errors'] = cleanup_errors
    receipt['streams'] = [previous.record(OUTPUT / f'{case}.{suffix}.bin', OUTPUT) for suffix in ('stdout', 'stderr')]
    evidence.write_json(OUTPUT / f'{case}.json', receipt)
    return receipt


def run_cases(replica, result):
    for case in ('sync', 'stream'):
        receipt = capture(replica, case)
        case_file = replica / f'runs/agentops-http-control/protocol-v1-{case}/result.json'
        outcome = evidence.load_json(case_file) if case_file.is_file() else {'status': 'no_result'}
        result['cases'][case] = {'returncode': receipt.get('returncode'), 'status': outcome['status']}
        if (receipt.get('timed_out') or receipt.get('capture_error') or receipt.get('cleanup_errors')
                or outcome.get('forced_service_stop') or outcome.get('cleanup_errors')):
            raise ValueError('Unclean/timed-out case; second launch not permitted')
        if not case_file.is_file():
            raise ValueError('Missing terminal case result; cleanup is unconfirmed')
        service_record = replica / f'runs/agentops-http-control/protocol-v1-{case}/service-process.json'
        if not service_record.is_file() or outcome.get('service_returncode') != 0:
            raise ValueError('No verified clean service exit')


def main():
    if sys.platform != 'linux':
        raise ValueError('Use the explicit Ubuntu launcher')
    if OUTPUT.exists():
        raise FileExistsError('Preserve the existing protocol attempt')
    prior = evidence.load_json(PRIOR / 'result.json')
    if prior['status'] != 'native_and_http_controls_passed' or prior['export_reference_failures']:
        raise ValueError('Passed v8 controls required')
    seal = evidence.load_json(SEAL)
    preparation.validate_seal(ROOT, seal, prior)
    replica = Path(prior['linux_workspace'])
    manifest = evidence.load_json(PRIOR / 'export-manifest.json')
    if (not replica.is_absolute() or replica.is_symlink() or not replica.is_dir()
            or not replica.name.startswith('agentops-research-v7-')
            or str(replica) != manifest['original_linux_root']):
        raise ValueError('Existing Linux replica unavailable; no reinstall')
    previous.require_native_filesystem(replica)
    for row in manifest['files']:
        for base in (PRIOR / 'workspace', replica):
            if previous.record(previous.relative_file(base, row['path']), base) != row:
                raise ValueError('Prior export/live bytes changed: ' + row['path'])
    old_inputs = evidence.load_json(PRIOR / 'execution.json')['inputs']
    inputs = old_inputs + seal['launch_inputs']
    if len({r['path'] for r in inputs}) != len(inputs):
        raise ValueError('New inputs must not replace old inputs')
    for row in seal['launch_inputs']:
        if previous.relative_file(replica, row['path']).exists():
            raise FileExistsError('Addition exists: ' + row['path'])
    for name in ('protocol-temp-v9', 'runs/agentops-http-control/protocol-v1-sync',
                 'runs/agentops-http-control/protocol-v1-stream', SEAL.relative_to(ROOT).as_posix()):
        if (replica / name).exists():
            raise FileExistsError('New path already exists: ' + name)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = {'schema_version': 'agentops-linux-protocol/9', 'status': 'failed',
        'started_at_utc': evidence.now(), 'linux_workspace': str(replica),
        'installations': 0, 'live_model_calls': 0, 'qualified_second_domain': False,
        'research_gate_credit_added': 0, 'cases': {}}
    # Manifest cannot include its own hash, but this execution binds it and
    # exports it as an additional exact input after the launch-input list.
    inputs.append(previous.record(SEAL, ROOT))
    evidence.write_json(OUTPUT / 'execution.json', {**result, 'inputs': inputs,
        'prior_result': previous.record(PRIOR / 'result.json', ROOT),
        'prior_export': previous.record(PRIOR / 'export-manifest.json', ROOT),
        'seal': previous.record(SEAL, ROOT)})
    try:
        previous.copy_exact(ROOT, replica, seal['launch_inputs'] + [previous.record(SEAL, ROOT)])
        (replica / 'protocol-temp-v9').mkdir()
        print(f'Reusing {replica}; no installation. Running sync, then stream.', flush=True)
        run_cases(replica, result)
        if all(row['returncode'] == 0 and row['status'] == 'protocol_and_effect_checks_passed'
               for row in result['cases'].values()) and len(result['cases']) == 2:
            result['status'] = 'native_protocol_controls_passed'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        try:
            exported = export_evidence(replica, OUTPUT / 'workspace', inputs)
            evidence.write_json(OUTPUT / 'export-manifest.json', exported)
            result['exported_files'] = len(exported['files'])
            result['export_reference_failures'] = exported['reference_failures']
            if exported['reference_failures']:
                result['status'] = 'failed_export_references'
        except Exception as error:
            result.update(status='failed_export', export_error=f'{type(error).__name__}: {error}')
        try:
            verify_unchanged(inputs + seal['prerequisites'])
            result['parent_inputs_unchanged'] = True
        except Exception as error:
            result['parent_inputs_unchanged'] = False
            result['parent_input_error'] = f'{type(error).__name__}: {error}'
            result['status'] = 'failed_parent_integrity'
        result['finished_at_utc'] = evidence.now()
        evidence.write_json(OUTPUT / 'result.json', result)
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(0 if result['status'] == 'native_protocol_controls_passed' else 1)


if __name__ == '__main__':
    main()
