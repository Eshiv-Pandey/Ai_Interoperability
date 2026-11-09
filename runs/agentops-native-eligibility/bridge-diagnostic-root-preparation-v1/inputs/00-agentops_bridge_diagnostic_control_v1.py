"""New diagnostic controller, adapted from frozen v10 with explicit changes.

Only allocation, fresh case paths, preparation schema and diagnostic service
launcher differ. Client policy, effect checks, timeouts and cleanup are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import agentops_bridge_diagnostic_plan_v1 as design
import agentops_http_control_v5 as previous
import agentops_protocol_wire_v1 as wire
from check_agentops_effect_v2 import seed_snapshot
from check_agentops_bridge_v1 import check_service, check_case, parse_asgi_exchange
from agentops_owned_process_v1 import finish_owned_group

evidence = previous.evidence
ROOT = design.ROOT


def boundary(service, name):
    evidence.write_json(service / (name + '.snapshot.json'), {
        'observed_at_utc': evidence.now(), 'monotonic_ns': time.monotonic_ns(),
        'database': evidence.database_snapshot(service / 'state/incidents.db', service, 'run')})


def task_from_result(result):
    if not isinstance(result, dict):
        return None
    value = result.get('task', result.get('statusUpdate', result))
    task_id = value.get('taskId', value.get('id'))
    context_id = value.get('contextId')
    if isinstance(task_id, str) and task_id and isinstance(context_id, str) and context_id:
        return {'task_id': task_id, 'context_id': context_id}
    return None


def evaluator_read(service, case):
    """After the caller has exited, inspect origin state without returning IDs to it."""
    for folder in sorted((service / 'wire').iterdir()):
        if not (folder / 'exchange.json').exists():
            continue
        exchange = parse_asgi_exchange(folder)
        request = exchange.get('request')
        if not isinstance(request, dict) or request.get('method') not in ('SendMessage', 'SendStreamingMessage'):
            continue
        for response in exchange.get('responses', []):
            original = task_from_result(response.get('result'))
            if original:
                target = case / 'evaluator'
                target.mkdir(exist_ok=False)
                wire.exchange(target, 'final', design.PORT, 'POST', {
                    'jsonrpc': '2.0', 'id': 'evaluator-final', 'method': 'GetTask',
                    'params': {'id': original['task_id']}}, '1.0')
                return {'executed': True, **original, 'grader_only': True,
                        'available_to_client': False, 'source_sequence': exchange['record']['sequence']}
        break
    return {'executed': False, 'reason': 'No captured initial origin task binding',
            'grader_only': True, 'available_to_client': False}


def capture_client(argv, case, config):
    receipt = {'argv': argv, 'cwd': str(ROOT), 'started_at_utc': evidence.now(),
               'timed_out': False, 'forced_kill': False, 'cleanup_errors': []}
    process = None
    with (case / 'client.stdout.bin').open('xb') as stdout, (case / 'client.stderr.bin').open('xb') as stderr:
        try:
            process = subprocess.Popen(argv, cwd=ROOT, env=design.bridge_environment(case),
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
            receipt['pid'] = process.pid
            evidence.write_json(case / 'client.started.json', receipt)
            receipt['returncode'] = process.wait(timeout=220)
        except BaseException as error:
            receipt['error'] = f'{type(error).__name__}: {error}'
            receipt['timed_out'] = isinstance(error, subprocess.TimeoutExpired)
        finally:
            if process is not None:
                allowed = [argv]
                if 'bridge' in config:
                    allowed.append([config['bridge']['command'], *config['bridge']['args']])
                # Always inspect the session, even when its leader exited normally.
                receipt['owned_group'] = finish_owned_group(process.pid, allowed)
                receipt['forced_kill'] = any(row['signal'] == 'SIGKILL'
                                             for row in receipt['owned_group']['signals'])
                receipt['cleanup_errors'].extend(receipt['owned_group']['errors'])
                try:
                    process.wait(timeout=10)
                except Exception as error:
                    receipt['cleanup_errors'].append(f'Final wait: {type(error).__name__}: {error}')
            receipt['returncode'] = None if process is None else process.returncode
            receipt['finished_at_utc'] = evidence.now()
    receipt['streams'] = [evidence.digest(case / f'client.{suffix}.bin') for suffix in ('stdout', 'stderr')]
    evidence.write_json(case / 'client-process.json', receipt)
    return receipt


def stop_service(process, argv, service, result):
    try:
        evidence.write_json(service / 'stop-requested.json', {'requested_at_utc': evidence.now()})
    except Exception as error:
        result['cleanup_errors'].append(f'Stop request: {type(error).__name__}: {error}')
    result['forced_service_stop'] = False
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        result['forced_service_stop'] = True
    except Exception as error:
        result['cleanup_errors'].append(f'Service wait: {type(error).__name__}: {error}')
    group = finish_owned_group(process.pid, [argv])
    result['service_group_cleanup'] = group
    result['forced_service_stop'] |= group['forced_cleanup']
    result['cleanup_errors'].extend(group['errors'])
    try:
        process.wait(timeout=10)
    except Exception as error:
        result['cleanup_errors'].append(f'Final service wait: {type(error).__name__}: {error}')
    result['service_returncode'] = process.returncode


def run(case_id, runtime_root, seal_path):
    if sys.platform != 'linux':
        raise ValueError('Use the pinned Linux runtime')
    definition = design.CASES[case_id]
    seal = evidence.load_json(seal_path)
    if seal['schema_version'] != 'agentops-bridge-diagnostic-preparation/1' or seal['cases'] != list(design.CASES.values()):
        raise ValueError('Frozen case specification mismatch')
    if str(runtime_root) != seal['runtime_root']:
        raise ValueError('Runtime root differs from the frozen deployment')
    for row in seal['launch_inputs'] + seal['reuse_inputs']:
        if evidence.digest(ROOT / row['path']) != row:
            raise ValueError('Changed launch input: ' + row['path'])
    if hashlib.sha256(Path('/usr/bin/node').read_bytes()).hexdigest() != seal['node']['sha256']:
        raise ValueError('Node executable differs from the prepared pin')
    case = ROOT / (design.CASE_PREFIX + case_id)
    if case.exists():
        raise FileExistsError('Preserve existing case without rerun')
    source = evidence.source_inventory()
    previous.validate_native(source)
    case.mkdir(parents=True, exist_ok=False)
    (case / 'temp').mkdir()
    service = case / 'service'
    service.mkdir()
    (service / 'temp').mkdir()
    config = design.client_config(definition, case, runtime_root)
    evidence.write_json(case / 'client-config.json', config)
    evidence.write_json(case / 'agents.json', {'agents': {'agentops': {
        'cardUrl': f'http://127.0.0.1:{design.PORT}/.well-known/agent-card.json'}}})
    evidence.write_json(case / 'plan.json', {
        'schema_version': 'agentops-bridge-case-plan/1', **definition,
        'port': design.PORT, 'bridge_port': design.BRIDGE_PORT,
        'client_config': evidence.digest(case / 'client-config.json'),
        'service_source': evidence.digest(ROOT / 'scripts/serve_agentops_bridge_diagnostic_v2.py'),
        'source_files': source, 'prepared_at_utc': evidence.now(),
        'seal': evidence.digest(seal_path)})
    result = {'schema_version': 'agentops-bridge-case-result/1', 'case_id': case_id,
        'kind': definition['kind'], 'status': 'failed', 'started_at_utc': evidence.now(),
        'cleanup_errors': [], 'live_model_calls': 0, 'research_gate_credit_added': 0}
    process = None
    streams = []
    try:
        environment = evidence.clean_environment(service)
        environment.update({'AGENT_MODEL_PROVIDER': 'openai-compatible', 'AGENT_MODEL': 'qwen3:4b-instruct',
            'AGENT_DATA_DIR': str(evidence.SOURCE / 'agents/data'), 'AGENT_STATE_DIR': str(service / 'state'),
            'AGENT_A2A_HOST': '127.0.0.1', 'AGENT_A2A_BIND_HOST': '127.0.0.1', 'AGENT_A2A_PORT': str(design.PORT)})
        argv = [str(previous.native.RUNTIME), '-B', str(ROOT / 'scripts/serve_agentops_bridge_diagnostic_v2.py'),
                '--output', str(service), '--port', str(design.PORT)]
        streams = [(case / ('service.' + suffix + '.bin')).open('xb') for suffix in ('stdout', 'stderr')]
        process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=streams[0], stderr=streams[1], start_new_session=True)
        evidence.write_json(case / 'service-process.json', {'argv': argv, 'pid': process.pid, 'started_at_utc': evidence.now()})
        deadline = time.monotonic() + 65
        while not (service / 'service-ready.json').exists():
            if process.poll() is not None:
                raise RuntimeError('Fixture exited before readiness')
            if time.monotonic() >= deadline:
                raise TimeoutError('Fixture readiness deadline')
            time.sleep(0.1)
        script = 'agentops_native_profile_client_v1.mjs' if definition['kind'] == 'native' else 'agentops_bridge_client_v1.mjs'
        receipt = capture_client(['/usr/bin/node', str(ROOT / 'scripts' / script),
                                  '--config', str(case / 'client-config.json')], case, config)
        result.update(client_returncode=receipt['returncode'], client_timed_out=receipt['timed_out'],
                      client_forced_kill=receipt['forced_kill'], client_group_cleanup=receipt.get('owned_group', {}))
        result['cleanup_errors'].extend(receipt['cleanup_errors'])
        if definition['kind'] == 'bridge':
            client_result_path = case / 'client/result.json'
            client_result = evidence.load_json(client_result_path) if client_result_path.exists() else {}
            child = client_result.get('child', {})
            result['bridge_clean_exit'] = child.get('clean_exit') is True
            result['bridge_forced_kill'] = child.get('forced_kill', False)
            result['bridge_exit'] = child.get('exit')
        if (receipt.get('owned_group', {}).get('final_empty') is not True
                or receipt['cleanup_errors']):
            raise ValueError('Caller group exit unconfirmed; evaluator query withheld')
        result['evaluator_query'] = evaluator_read(service, case)
        boundary(service, 'final')
        result['status'] = 'recorded' if receipt['returncode'] == 0 else 'failed'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        if process is not None:
            stop_service(process, argv, service, result)
        for stream in streams:
            stream.close()
        if (service / 'state/incidents.db').is_file() and result.get('service_group_cleanup', {}).get('final_empty'):
            try:
                boundary(service, 'terminal')
            except Exception as error:
                result['cleanup_errors'].append(f'Terminal snapshot: {type(error).__name__}: {error}')
        try:
            result['source_unchanged_after'] = evidence.source_inventory() == source
        except Exception as error:
            result['source_unchanged_after'] = False
            result['source_check_error'] = f'{type(error).__name__}: {error}'
        try:
            checked = check_service(service, seed_snapshot(evidence.SOURCE / 'agents/data/incidents.db'))
            evidence.write_json(case / 'check.json', checked)
            result['service_strict_success'] = checked['strict_success']
        except Exception as error:
            result['checker_error'] = f'{type(error).__name__}: {error}'
        if (result.get('forced_service_stop') or result.get('cleanup_errors') or not result['source_unchanged_after']
                or result.get('client_group_cleanup', {}).get('forced_cleanup')
                or result.get('client_group_cleanup', {}).get('initially_empty') is not True
                or result.get('client_group_cleanup', {}).get('final_empty') is not True
                or result.get('service_group_cleanup', {}).get('initially_empty') is not True
                or result.get('service_group_cleanup', {}).get('final_empty') is not True):
            result['status'] = 'failed'
        result['finished_at_utc'] = evidence.now()
        result['files'] = [evidence.digest(path) for path in sorted(case.rglob('*')) if path.is_file()]
        evidence.write_json(case / 'result.json', result)
        # Whole-case provenance/profile checks also gate native eligibility.
        # Keep their report separate from this capture receipt.
        try:
            case_checked = check_case(case, seed_snapshot(evidence.SOURCE / 'agents/data/incidents.db'))
            evidence.write_json(case / 'case-check.json', case_checked)
        except Exception as error:
            evidence.write_json(case / 'case-check-error.json', {'error': f'{type(error).__name__}: {error}'})
    print(json.dumps({key: value for key, value in result.items() if key != 'files'}, indent=2), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=design.CASES, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--seal', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.case, args.runtime_root, args.seal)
    raise SystemExit(0 if report['status'] == 'recorded' else 1)
