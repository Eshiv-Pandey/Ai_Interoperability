"""Check retained native protocol-profile bytes and effects; no application imports."""
import argparse
import copy
import json
from pathlib import Path

from agentops_http_bytes_v1 import decode_response, rpc_results, strict_json
from check_agentops_effect_v2 import at_utc, db_value, require, same, seed_snapshot
from check_agentops_socket_policy_v1 import check_policy

LABELS = ('card-default', 'card-v1', 'start', 'get-pending', 'get-default',
          'resume-default', 'resume', 'get-completed')
RATIONALE = 'Inventory is down and INC-002 matches the service-down runbook.'


def parse_request(raw, port, label):
    head, separator, body = raw.partition(b'\r\n\r\n')
    require(bool(separator), 'complete request')
    method = 'GET' if label.startswith('card-') else 'POST'
    target = '/.well-known/agent-card.json' if method == 'GET' else '/'
    lines = head.decode('ascii').split('\r\n')
    require(lines[0] == f'{method} {target} HTTP/1.1', 'request method/target')
    headers = {}
    for line in lines[1:]:
        key, sep, value = line.partition(':')
        require(bool(sep) and key.lower() not in headers, 'unique request headers')
        headers[key.lower()] = value.strip()
    version = None if label in ('card-default', 'get-default', 'resume-default') else '1.0'
    expected = {'host': f'127.0.0.1:{port}', 'connection': 'close',
                'accept-encoding': 'identity', 'accept': 'application/json, text/event-stream',
                'content-length': str(len(body))}
    if method == 'POST':
        expected['content-type'] = 'application/json'
    if version is not None:
        expected['a2a-version'] = version
    require(headers == expected, 'exact frozen version and credential-free headers')
    if method == 'GET':
        require(body == b'', 'bodyless card request')
        return None
    return strict_json(body)


def check(run, seed):
    plan = strict_json((run / 'plan.json').read_bytes())
    require(plan['schema_version'] == 'agentops-protocol-plan/1', 'plan schema')
    require(plan['sequence'] == list(LABELS) and plan['case'] in ('sync', 'stream'), 'frozen cases/sequence')
    port = plan['port']
    require(port == (18762 if plan['case'] == 'sync' else 18763), 'fixed case port')
    streaming = plan['case'] == 'stream'
    requests, replies, receipts, negative = {}, {}, [], {}
    for label in LABELS:
        requests[label] = parse_request((run / f'{label}.request.bin').read_bytes(), port, label)
        receipt = strict_json((run / f'{label}.exchange.json').read_bytes())
        version = None if label in ('card-default', 'get-default', 'resume-default') else '1.0'
        require(receipt['status'] == 'captured' and receipt['label'] == label and receipt['port'] == port
                and receipt['version'] == version and receipt['method'] == ('GET' if label.startswith('card-') else 'POST')
                and receipt['request_fully_sent'] is True and receipt['response_eof'] is True, 'complete exchange')
        receipts.append(receipt)
        status, headers, body = decode_response((run / f'{label}.response.bin').read_bytes())
        content_type = headers.get('content-type', '').split(';', 1)[0]
        if streaming and label in ('start', 'resume'):
            require(status == 200 and content_type == 'text/event-stream', 'successful SSE')
            replies[label] = rpc_results(body, 'approval-' + label)
            continue
        require(content_type == 'application/json', 'JSON response')
        reply = strict_json(body)
        if label in ('get-default', 'resume-default'):
            rpc_id = 'get-pending' if label == 'get-default' else 'approval-resume'
            require(200 <= status <= 599 and reply.get('jsonrpc') == '2.0' and reply.get('id') == rpc_id
                    and 'result' not in reply and reply.get('error', {}).get('code') == -32009,
                    'omitted-header version rejection')
            negative[label] = {'http_status': status, 'error': reply['error']}
        else:
            require(status == 200, 'HTTP success')
            if not label.startswith('card-'):
                rpc_id = 'approval-' + label if label in ('start', 'resume') else label
                require(reply.get('jsonrpc') == '2.0' and reply.get('id') == rpc_id
                        and 'error' not in reply, 'successful matching RPC')
                reply = reply['result']
        replies[label] = reply
    for label in ('card-default', 'card-v1'):
        card = replies[label]
        require(card['name'] == 'AgentOps Agent' and card['version'] == '0.11.0'
                and card['capabilities']['streaming'] is True, 'original card')
        require(card['supportedInterfaces'] == [{'url': f'http://127.0.0.1:{port}/', 'protocolBinding': 'JSONRPC'}],
                'original advertised interface without invented version')
        require({r['id'] for r in card['skills']} == {'incident-triage', 'remediation'}, 'original skills')
        require(card['defaultInputModes'] == card['defaultOutputModes'] == ['text/plain'], 'declared modes')
    initial = replies['start'][-1]['statusUpdate'] if streaming else replies['start']['task']
    task_id = initial['taskId'] if streaming else initial['id']
    context_id = initial['contextId']
    require(all(type(v) is str and bool(v) for v in (task_id, context_id)), 'task/context strings')
    require(initial['status']['state'] == 'TASK_STATE_INPUT_REQUIRED', 'pending original task')
    calls = [p['data'] for p in initial['status']['message']['parts']
             if p.get('metadata', {}).get('adk_type') == 'function_call'
             and p.get('data', {}).get('name') == 'adk_request_confirmation']
    require(len(calls) == 1 and type(calls[0].get('id')) is str and bool(calls[0]['id']), 'public confirmation id')
    call = calls[0]
    require(same(call['args']['originalFunctionCall'], {'id': 'restart-inventory-call',
                'name': 'restart_service', 'args': {'name': 'inventory'}}), 'original guarded action')
    method = 'SendStreamingMessage' if streaming else 'SendMessage'
    require(same(requests['start'], {'jsonrpc': '2.0', 'id': 'approval-start', 'method': method, 'params': {
        'message': {'messageId': 'approval-message', 'role': 'ROLE_USER',
                    'parts': [{'text': 'Restart inventory.'}]}}}), 'original start input')
    require(same(requests['resume'], {'jsonrpc': '2.0', 'id': 'approval-resume', 'method': method, 'params': {
        'message': {'messageId': 'approval-response', 'role': 'ROLE_USER', 'taskId': task_id, 'contextId': context_id,
                    'parts': [{'data': {'id': call['id'], 'name': 'adk_request_confirmation',
                        'response': {'confirmed': True, 'payload': {'rationale': RATIONALE}}},
                        'metadata': {'adk_type': 'function_response'}}]}}}), 'bound DataPart confirmation')
    require(same(requests['resume-default'], requests['resume'])
            and same(requests['get-default'], requests['get-pending']), 'matched payloads across version headers')
    for a, b in (('resume-default', 'resume'), ('get-default', 'get-pending')):
        require((run / f'{a}.request.bin').read_bytes() ==
                (run / f'{b}.request.bin').read_bytes().replace(b'A2A-Version: 1.0\r\n', b'', 1), 'exact paired wire difference')
    completed = replies['resume'][-1]['statusUpdate'] if streaming else replies['resume']['task']
    require(completed.get('taskId' if streaming else 'id') == task_id and completed.get('contextId') == context_id
            and completed['status']['state'] == 'TASK_STATE_COMPLETED', 'same-task completion')
    if streaming:
        for event in replies['start'] + replies['resume']:
            require(len(event) == 1, 'one streaming response arm')
            kind, value = next(iter(event.items()))
            require(kind in ('task', 'statusUpdate', 'artifactUpdate'), 'known task stream arm')
            require(value.get('id' if kind == 'task' else 'taskId') == task_id
                    and value.get('contextId') == context_id, 'all streamed events bound to original task')
    for label, state in (('get-pending', 'TASK_STATE_INPUT_REQUIRED'), ('get-completed', 'TASK_STATE_COMPLETED')):
        require(same(requests[label], {'jsonrpc': '2.0', 'id': label, 'method': 'GetTask', 'params': {'id': task_id}}), 'query original task')
        task = replies[label]
        require(task['id'] == task_id and task['contextId'] == context_id and task['status']['state'] == state, 'persisted original task state')
    boundaries = strict_json((run / 'boundaries.json').read_bytes())
    require([r['label'] for r in boundaries] == ['before-card-default'] + ['after-' + label for label in LABELS], 'all boundaries')
    ticks = [r['monotonic_ns'] for r in boundaries]
    require(all(type(t) is int for t in ticks) and all(a < b for a, b in zip(ticks, ticks[1:])), 'monotonic boundaries')
    stamps = [at_utc(r['observed_at_utc']) for r in boundaries]
    for i, receipt in enumerate(receipts):
        require(stamps[i] <= at_utc(receipt['started_at_utc']) <= at_utc(receipt['finished_at_utc']) <= stamps[i + 1], 'bounded exchange time')
    for row in boundaries:
        require(row['database']['path'] == 'state/incidents.db' and row['database']['path_base'] == 'run', 'isolated domain database')
        require(same(row, strict_json((run / (row['label'] + '.snapshot.json')).read_bytes())), 'snapshot binding')
    databases = [db_value(r['database']) for r in boundaries]
    require(all(same(db, db_value(seed)) for db in databases[:7]), 'no pre-confirmation or rejected-probe effects')
    final = databases[7]
    require(same(final, databases[8]), 'final query has no domain effect')
    rows = final['tables']['audit_log']
    require(len(rows) == 1, 'exactly one audit row')
    audit = rows[0]
    expected_audit = {'id': 1, 'schema_version': 1, 'actor': 'agentops-agent', 'approved_by': 'A2A_USER_' + context_id,
        'rationale': RATIONALE, 'context_summary': 'service inventory was down; open incidents: INC-002',
        'session_id': context_id, 'action': 'restart_service', 'target': 'inventory',
        'detail': 'service restarted and marked operational (mock)'}
    require(all(same(audit[k], v) for k, v in expected_audit.items()), 'attributed original audit')
    require(type(audit['invocation_id']) is str and bool(audit['invocation_id']), 'invocation identity')
    require(stamps[6].replace(microsecond=0) <= at_utc(audit['ts']) <= stamps[7], 'effect during header-confirmation interval')
    expected = copy.deepcopy(db_value(seed))
    targets = [r for r in expected['tables']['services'] if r['name'] == 'inventory']
    require(len(targets) == 1 and targets[0]['status'] == 'down', 'original seed target')
    targets[0]['status'] = 'operational'
    expected['tables']['audit_log'] = [audit]
    expected['tables']['sqlite_sequence'] = [{'name': 'audit_log', 'seq': 1}]
    require(same(final, expected), 'only expected status and audit changes')
    service = strict_json((run / 'service-result.json').read_bytes())
    require(service['schema_version'] == 'agentops-http-service/1' and service['observer_version'] == 2
            and service['status'] == 'stopped' and not service.get('watchdog_expired') and service['network_errors'] == [], 'offline clean service')
    require(type(service['model_double_calls']) is int and service['model_double_calls'] == 2, 'two deterministic double calls')
    require(same(service['seen_contexts'], [['A2A_USER_' + context_id, context_id, audit['invocation_id'], flag]
                                           for flag in (False, True)]), 'same guarded invocation and approver')
    socket = check_policy(service['socket_policy'], listener_port=port)
    require(service['network_errors'] == service['socket_policy']['unexpected'], 'network observation consistency')
    return {'schema_version': 'agentops-protocol-check/1', 'status': 'passed', 'case': plan['case'],
        'task_id': task_id, 'context_id': context_id, 'new_audit_rows': 1,
        'cards_equal': same(replies['card-default'], replies['card-v1']),
        'card_protocol_versions': {k: replies[k].get('protocolVersion') for k in ('card-default', 'card-v1')},
        'omitted_header_results': negative, 'socket_policy': socket,
        'bridge_qualification': False, 'scientific_gate_credit_added': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve prior checks')
    report = {'schema_version': 'agentops-protocol-check/1', 'status': 'failed'}
    try:
        report.update(check(args.run, seed_snapshot(Path(__file__).resolve().parents[1] /
            'external/agentops-c806b7f1/agents/data/incidents.db')))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'passed' else 1)
