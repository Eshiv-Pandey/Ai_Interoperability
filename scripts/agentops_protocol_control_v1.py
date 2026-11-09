"""Two fresh native 1.0 controls with paired omitted-header probes; no bridges."""
import argparse
import json
from pathlib import Path
import subprocess
import time

import agentops_http_control_v5 as previous
import agentops_protocol_wire_v1 as wire

evidence = previous.evidence
ROOT = previous.ROOT
RUNS = previous.RUNS
SEAL = ROOT / 'docs/research/source-evidence/agentops-protocol-control-v1/manifest-v2.json'
LABELS = ['card-default', 'card-v1', 'start', 'get-pending', 'get-default',
          'resume-default', 'resume', 'get-completed']


def run(case):
    previous.native.require_linux()
    if case not in ('sync', 'stream'):
        raise ValueError('Unknown frozen case')
    output = RUNS / ('protocol-v1-' + case)
    if output.exists():
        raise FileExistsError('Case exists; preserve it without rerun')
    source = evidence.source_inventory()
    prerequisite = previous.validate_native(source)
    baseline = previous.runtime_inventory()
    seal = evidence.load_json(SEAL)
    for row in seal['launch_inputs']:
        if evidence.digest(ROOT / row['path']) != row:
            raise ValueError('Launch input changed: ' + row['path'])
    site = previous.native.RUNTIME.parents[1] / 'lib/python3.13/site-packages'
    modules = []
    for row in seal['runtime_sources']:
        path = evidence.within(site / row['module'], site)
        record = evidence.digest(path)
        if record['sha256'] != row['sha256'] or record['bytes'] != row['bytes']:
            raise ValueError('Installed protocol source changed: ' + row['module'])
        modules.append(record)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'temp').mkdir()
    port = 18762 if case == 'sync' else 18763
    plan = {'schema_version': 'agentops-protocol-plan/1', 'case': case, 'port': port,
            'sequence': LABELS, 'source_files': source, 'runtime_sources': modules,
            'native_prerequisite': prerequisite, 'launch_seal': evidence.digest(SEAL),
            'service': evidence.digest(previous.SERVICE), 'prepared_at_utc': evidence.now()}
    evidence.write_json(output / 'plan.json', plan)
    result = {'schema_version': 'agentops-protocol-result/1', 'status': 'failed',
              'case': case, 'started_at_utc': evidence.now(), 'live_model_calls': 0,
              'bridge_qualification': False, 'research_gate_credit_added': 0}
    process, streams, snapshots = None, [], []

    def snapshot(label):
        row = {'label': label, 'observed_at_utc': evidence.now(), 'monotonic_ns': time.monotonic_ns(),
               'database': evidence.database_snapshot(output / 'state/incidents.db', output, 'run')}
        evidence.write_json(output / f'{label}.snapshot.json', row)
        snapshots.append(row)

    def exchange(label, method='POST', payload=None, version='1.0'):
        response = wire.exchange(output, label, port, method, payload, version)
        snapshot('after-' + label)
        return response

    try:
        environment = evidence.clean_environment(output)
        current = previous.native.runtime_inspection(output, 'execution-runtime', environment)
        if current != baseline:
            raise ValueError('Runtime changed from passed native control')
        environment.update({'AGENT_MODEL_PROVIDER': 'openai-compatible', 'AGENT_MODEL': 'qwen3:4b-instruct',
                            'AGENT_DATA_DIR': str(evidence.SOURCE / 'agents/data'),
                            'AGENT_STATE_DIR': str(output / 'state'), 'AGENT_A2A_HOST': '127.0.0.1',
                            'AGENT_A2A_BIND_HOST': '127.0.0.1', 'AGENT_A2A_PORT': str(port)})
        for name in ('stdout', 'stderr'):
            streams.append((output / f'service.{name}.bin').open('xb'))
        argv = [str(previous.native.RUNTIME), '-B', str(previous.SERVICE), '--output', str(output), '--port', str(port)]
        process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=streams[0], stderr=streams[1], shell=False, start_new_session=True)
        evidence.write_json(output / 'service-process.json', {'pid': process.pid, 'argv': argv,
            'started_at_utc': evidence.now()})
        deadline = time.monotonic() + 65
        while not (output / 'service-ready.json').exists():
            if process.poll() is not None:
                raise RuntimeError('Service exited before readiness')
            if time.monotonic() >= deadline:
                raise TimeoutError('Service readiness deadline')
            time.sleep(0.1)
        snapshot('before-card-default')
        exchange('card-default', 'GET', version=None)
        exchange('card-v1', 'GET')
        streaming = case == 'stream'
        method = 'SendStreamingMessage' if streaming else 'SendMessage'
        start = {'jsonrpc': '2.0', 'id': 'approval-start', 'method': method, 'params': {
            'message': {'messageId': 'approval-message', 'role': 'ROLE_USER',
                        'parts': [{'text': 'Restart inventory.'}]}}}
        reply = wire.rpc_response(exchange('start', payload=start), 'approval-start', streaming)
        task_id, context_id, call = wire.pending_task(reply, streaming)
        query = {'jsonrpc': '2.0', 'id': 'get-pending', 'method': 'GetTask', 'params': {'id': task_id}}
        wire.rpc_response(exchange('get-pending', payload=query), 'get-pending')
        # Paired payloads are exactly identical across header choices, including
        # RPC/message identifiers. These are prospectively fixed contrast probes.
        exchange('get-default', payload=query, version=None)
        resume = {'jsonrpc': '2.0', 'id': 'approval-resume', 'method': method, 'params': {
            'message': {'messageId': 'approval-response', 'role': 'ROLE_USER',
                        'taskId': task_id, 'contextId': context_id,
                        'parts': [{'data': {'id': call['id'], 'name': call['name'],
                            'response': {'confirmed': True, 'payload': {'rationale': previous.RATIONALE}}},
                                   'metadata': {'adk_type': 'function_response'}}]}}}
        exchange('resume-default', payload=resume, version=None)
        # Stop if the no-header probe mutated the domain: preserve a contrary
        # observation instead of sending a second effect-producing confirmation.
        from check_agentops_effect_v2 import db_value, same
        if not same(db_value(snapshots[-1]['database']), db_value(snapshots[0]['database'])):
            raise ValueError('No-header probe changed domain state; preserve contrary result')
        wire.rpc_response(exchange('resume', payload=resume), 'approval-resume', streaming)
        query = {'jsonrpc': '2.0', 'id': 'get-completed', 'method': 'GetTask', 'params': {'id': task_id}}
        wire.rpc_response(exchange('get-completed', payload=query), 'get-completed')
        result['status'] = 'captured_check_pending'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        if process is not None:
            previous.stop_owned_service(process, output, result)
        for stream in streams:
            stream.close()
        evidence.write_json(output / 'boundaries.json', snapshots)
        result['source_unchanged_after'] = evidence.source_inventory() == source
        if result['status'] == 'captured_check_pending':
            try:
                if result.get('forced_service_stop') or result.get('cleanup_errors') or result.get('service_returncode') != 0:
                    raise ValueError('Unclean service shutdown')
                from check_agentops_protocol_v1 import check
                from check_agentops_effect_v2 import seed_snapshot
                checked = check(output, seed_snapshot(evidence.SOURCE / 'agents/data/incidents.db'))
                evidence.write_json(output / 'check.json', checked)
                result['status'] = 'protocol_and_effect_checks_passed'
            except Exception as error:
                result.update(status='failed', error=f'{type(error).__name__}: {error}')
        if not result['source_unchanged_after']:
            result['status'] = 'failed_source_integrity'
        result['finished_at_utc'] = evidence.now()
        result['files'] = [evidence.digest(path) for path in sorted(output.iterdir()) if path.is_file()]
        evidence.write_json(output / 'result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, indent=2), flush=True)
    return result['status'] == 'protocol_and_effect_checks_passed'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=('sync', 'stream'))
    args = parser.parse_args()
    raise SystemExit(0 if run(args.case) else 1)
