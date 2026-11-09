"""Execute the frozen native/bridge matrix once, then export every attempt."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import agentops_native_probe_v2 as evidence
import agentops_bridge_plan_v1 as design
import run_agentops_linux_workspace_v5 as previous
from export_agentops_workspace_v7 import export_evidence
from agentops_bridge_runtime_archive_v1 import verify_runtime
from agentops_owned_process_v1 import finish_owned_group

ROOT = evidence.WORKSPACE
OUTPUT = ROOT / 'runs/agentops-native-eligibility/linux-bridge-v10'
PRIOR = ROOT / 'runs/agentops-native-eligibility/linux-protocol-v9'
SEAL = ROOT / 'docs/research/source-evidence/agentops-bridge-control-v1/manifest.json'
RUNTIME_INPUTS = ROOT / 'docs/research/source-evidence/agentops-bridge-control-v1/runtime'


def groups_clean(groups):
    return set(groups) == {'controller', 'client', 'service'} and all(
        group.get('initially_empty') is True and group.get('final_empty') is True
        and group.get('forced_cleanup') is False and not group.get('errors')
        for group in groups.values())


def cleanup_case_groups(replica, case_id, runtime_root, process, argv):
    """Check all receipt-owned sessions after every controller termination."""
    groups = {'controller': finish_owned_group(process.pid, [argv])}
    errors = list(groups['controller']['errors'])
    case = replica / 'runs/agentops-http-control' / ('bridge-v1-' + case_id)
    definition = design.CASES[case_id]
    # Build allowed identities from frozen launch design, not untrusted receipts.
    script = 'agentops_native_profile_client_v1.mjs' if definition['kind'] == 'native' else 'agentops_bridge_client_v1.mjs'
    client_argv = ['/usr/bin/node', str(replica / 'scripts' / script), '--config', str(case / 'client-config.json')]
    service_argv = [str(replica / 'external/runtime-agentops-linux-v7/venv/bin/python'), '-B',
                    str(replica / 'scripts/serve_agentops_bridge_v1.py'), '--output', str(case / 'service'),
                    '--port', str(design.PORT)]
    for label, name, expected in (('client', 'client.started.json', client_argv),
                                  ('service', 'service-process.json', service_argv)):
        try:
            owned = evidence.load_json(case / name)
            if owned['argv'] != expected:
                raise ValueError('Owned launch argv differs from frozen design')
            allowed = [expected]
            if label == 'client' and definition['kind'] == 'bridge':
                config = evidence.load_json(case / 'client-config.json')
                bridge = config['bridge']
                # The parent design module is in the Windows-mounted workspace;
                # derive the embedded script location from the actual replica.
                expected_config = design.client_config(definition, case, runtime_root)
                if definition['arm'] in ('B6', 'B7'):
                    expected_config['bridge']['args'][0] = str(replica / 'scripts/agentops_mgcrea_embed_v1.mjs')
                if config != expected_config:
                    raise ValueError('Bridge launch configuration differs from frozen design')
                allowed.append([bridge['command'], *bridge['args']])
            groups[label] = finish_owned_group(owned['pid'], allowed)
            errors.extend(f'{label}: {value}' for value in groups[label]['errors'])
        except FileNotFoundError:
            groups[label] = {'status': 'receipt_absent'}
            errors.append(f'{label}: owned process receipt absent')
        except Exception as error:
            groups[label] = {'status': 'identity_unconfirmed'}
            errors.append(f'{label}: {type(error).__name__}: {error}')
    return groups, errors


def capture(replica, case_id, runtime_root, seal):
    argv = [sys.executable, '-B', str(replica / 'scripts/agentops_bridge_control_v1.py'),
            '--case', case_id, '--runtime-root', str(runtime_root), '--seal', str(seal)]
    row = {'argv': argv, 'cwd': str(replica), 'started_at_utc': evidence.now(),
           'timed_out': False, 'cleanup_errors': []}
    process = None
    with (OUTPUT / f'{case_id}.stdout.bin').open('xb') as stdout, \
            (OUTPUT / f'{case_id}.stderr.bin').open('xb') as stderr:
        try:
            env = evidence.clean_environment(OUTPUT)
            env['PYTHONPATH'] = str(replica / 'scripts')
            process = subprocess.Popen(argv, cwd=replica, env=env, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True)
            row['pid'] = process.pid
            evidence.write_json(OUTPUT / f'{case_id}.started.json', row)
            row['returncode'] = process.wait(timeout=480)
        except BaseException as error:
            row['error'] = f'{type(error).__name__}: {error}'
            row['timed_out'] = isinstance(error, subprocess.TimeoutExpired)
        finally:
            if process is not None:
                row['owned_groups'], errors = cleanup_case_groups(replica, case_id, runtime_root, process, argv)
                row['cleanup_errors'].extend(errors)
                try:
                    process.wait(timeout=10)
                except Exception as error:
                    row['cleanup_errors'].append(f'Controller wait: {type(error).__name__}: {error}')
            row['returncode'] = None if process is None else process.returncode
            row['finished_at_utc'] = evidence.now()
    row['streams'] = [previous.record(OUTPUT / f'{case_id}.{suffix}.bin', OUTPUT)
                      for suffix in ('stdout', 'stderr')]
    evidence.write_json(OUTPUT / f'{case_id}.json', row)
    return row


def main(runtime_root):
    if sys.platform != 'linux':
        raise ValueError('Use the explicit Linux launcher')
    if OUTPUT.exists():
        raise FileExistsError('Preserve the existing group attempt; never repeat it')
    seal = evidence.load_json(SEAL)
    if seal['schema_version'] != 'agentops-bridge-preparation/1' or seal['cases'] != list(design.CASES.values()):
        raise ValueError('Invalid frozen group')
    prior = evidence.load_json(PRIOR / 'result.json')
    if prior['status'] != 'native_protocol_controls_passed' or prior['export_reference_failures']:
        raise ValueError('Verified native protocol prerequisite required')
    replica = Path(prior['linux_workspace'])
    previous.require_native_filesystem(replica)
    # Reuse the installed Python fixture; each new case has fresh state.
    for row in evidence.load_json(PRIOR / 'export-manifest.json')['files']:
        if previous.record(previous.relative_file(replica, row['path']), replica) != row:
            raise ValueError('Prior live evidence changed: ' + row['path'])
    for row in seal['launch_inputs'] + seal['prerequisites']:
        if previous.record(previous.relative_file(ROOT, row['path']), ROOT) != row:
            raise ValueError('Changed prepared input: ' + row['path'])
    for row in seal['launch_inputs']:
        if (replica / row['path']).exists():
            raise FileExistsError('New launch path already exists: ' + row['path'])
    if str(runtime_root) != seal['runtime_root'] or not runtime_root.is_dir():
        raise ValueError('Prepared bridge runtime location differs')
    graph = evidence.load_json(RUNTIME_INPUTS / 'graph.json')
    materialization = evidence.load_json(RUNTIME_INPUTS / 'materialization.json')
    runtime_before = verify_runtime(runtime_root, graph, materialization)
    for case_id in design.CASES:
        if (replica / 'runs/agentops-http-control' / ('bridge-v1-' + case_id)).exists():
            raise FileExistsError('A planned case already exists: ' + case_id)
    inputs = evidence.load_json(PRIOR / 'execution.json')['inputs'] + seal['launch_inputs'] + [previous.record(SEAL, ROOT)]
    OUTPUT.mkdir(parents=True, exist_ok=False)
    (OUTPUT / 'temp').mkdir()
    result = {'schema_version': 'agentops-bridge-group/1', 'status': 'failed',
        'started_at_utc': evidence.now(), 'linux_workspace': str(replica),
        'cases': {}, 'installations': 0, 'live_model_calls': 0, 'research_gate_credit_added': 0,
        'qualified_second_domain': False, 'runtime_before': runtime_before}
    evidence.write_json(OUTPUT / 'execution.json', {**result, 'inputs': inputs,
        'seal': previous.record(SEAL, ROOT), 'runtime_root': str(runtime_root)})
    try:
        previous.copy_exact(ROOT, replica, seal['launch_inputs'] + [previous.record(SEAL, ROOT)])
        for case_id, definition in design.CASES.items():
            failed_prerequisites = [name for name in definition['native_prerequisites']
                                   if not result['cases'].get(name, {}).get('strict_success')]
            if failed_prerequisites:
                result['cases'][case_id] = {'status': 'skipped', 'reason': 'Native positive control did not qualify',
                                            'failed_prerequisites': failed_prerequisites}
                evidence.write_json(OUTPUT / f'{case_id}.skipped.json', result['cases'][case_id])
                continue
            print(f'Starting {case_id}; one fresh bounded attempt.', flush=True)
            receipt = capture(replica, case_id, runtime_root, replica / SEAL.relative_to(ROOT))
            path = replica / 'runs/agentops-http-control' / ('bridge-v1-' + case_id) / 'result.json'
            outcome = evidence.load_json(path) if path.exists() else {'status': 'missing_result'}
            result['cases'][case_id] = {key: outcome.get(key) for key in
                ('status', 'service_strict_success', 'service_returncode', 'client_returncode')}
            case_check_path = path.parent / 'case-check.json'
            case_check = evidence.load_json(case_check_path) if case_check_path.exists() else {}
            result['cases'][case_id]['strict_success'] = case_check.get('strict_success') is True
            if (receipt['timed_out'] or receipt.get('error') or receipt['cleanup_errors']
                    or not groups_clean(receipt.get('owned_groups', {}))
                    or outcome.get('client_timed_out') or outcome.get('client_forced_kill')
                    or outcome.get('client_group_cleanup', {}).get('forced_cleanup')
                    or outcome.get('client_group_cleanup', {}).get('initially_empty') is not True
                    or outcome.get('client_group_cleanup', {}).get('final_empty') is not True
                    or outcome.get('service_group_cleanup', {}).get('initially_empty') is not True
                    or outcome.get('service_group_cleanup', {}).get('final_empty') is not True
                    or (definition['kind'] == 'bridge' and (outcome.get('bridge_clean_exit') is not True
                                                           or outcome.get('bridge_forced_kill')))
                    or outcome.get('forced_service_stop') or outcome.get('cleanup_errors')
                    or outcome.get('service_returncode') != 0 or not outcome.get('source_unchanged_after')):
                raise ValueError('Unclean/unknown cleanup; no later case may launch')
        result['status'] = 'matrix_attempts_recorded'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        try:
            result['runtime_after'] = verify_runtime(runtime_root, graph, materialization)
        except Exception as error:
            result['runtime_after_error'] = f'{type(error).__name__}: {error}'
            result['status'] = 'failed_runtime_integrity'
        for case_id in design.CASES:
            if case_id not in result['cases']:
                result['cases'][case_id] = {'status': 'unexecuted',
                    'reason': 'Group stopped before this planned case',
                    'group_error': result.get('error')}
                evidence.write_json(OUTPUT / f'{case_id}.unexecuted.json', result['cases'][case_id])
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
            result['parent_inputs_unchanged'] = all(previous.record(ROOT / row['path'], ROOT) == row
                                                    for row in seal['launch_inputs'] + seal['prerequisites'])
        except Exception as error:
            result['parent_inputs_unchanged'] = False
            result['parent_check_error'] = f'{type(error).__name__}: {error}'
        if not result['parent_inputs_unchanged']:
            result['status'] = 'failed_parent_integrity'
        result['finished_at_utc'] = evidence.now()
        evidence.write_json(OUTPUT / 'result.json', result)
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    report = main(parser.parse_args().runtime_root)
    raise SystemExit(0 if report['status'] == 'matrix_attempts_recorded' else 1)
