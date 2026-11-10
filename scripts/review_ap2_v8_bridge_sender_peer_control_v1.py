"""Independent zero-application bridge-intercept/Node-attribution controls."""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('_ap2_bridge_peer_fixture',
    ROOT / 'scripts/review_ap2_v8_native_sender_peer_control_v1.py')
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
tag, identity, write = FIXTURE.tag, FIXTURE.identity, FIXTURE.write


def entity(raw):
    return dict(identity(raw), base64=base64.b64encode(raw).decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_control_output_required')
    source = ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v8.py'
    raw = source.read_bytes()
    module = types.ModuleType('_ap2_v8_bridge_sender_constructed_peer')
    module.__file__ = str(source)
    exec(compile(raw, str(source), 'exec'), module.__dict__)
    cases = {}
    with tempfile.TemporaryDirectory(prefix='ap2-v8-bridge-sender-peer-') as temporary:
        output = Path(temporary)
        (output / 'bridge').mkdir()
        peers = [{'role': role, 'port': port, 'process_id': 999999, 'host': '127.0.0.1', 'inheritable': False}
                 for role, port in (('merchant', 8001), ('credentials', 8002), ('processor', 8003))]
        write(output / 'native-servers-started.json', {'process_id': 999999, 'actual_tcp_listeners_started': True,
              'in_process_asgi_transport_used': False, 'peers': peers})
        write(output / 'native-socket-cleanup.json', {'strict_cleanup_passed': True, 'peers': [dict(row,
              socket_closed=True, server_task_finished=True, endpoint_rebind_verified=True, error=None) for row in peers]})
        write(output / 'original-state-before.json', {'merchant_store': {}, 'credential_tokens': {},
              'task_stores': {row['role']: {'task_ids': []} for row in peers}, 'provider_credentials_present': False})
        write(output / 'original-state-after.json', {'private_key_contents_retained': False})
        write(output / 'actor-input-separation.json', {'private_evaluator_read_probe_blocked': True,
              'denials': {'private_reads_blocked': 1, 'external_network_operations_blocked': 0,
                          'unallocated_descendant_processes_blocked': 0}})
        body = b'{"constructed_prefix_no_application_effect":true}'
        original = b'{"jsonrpc":"2.0","id":1,"method":"message/send","params":{"message":{"parts":[{"kind":"text","text":"Initiate a payment"}]}}}'
        url = 'http://127.0.0.1:8001/a2a/merchant_agent'

        def headers_for(payload):
            return [['host', '127.0.0.1:8001'], ['content-type', 'application/json'],
                    ['x-a2a-extensions', 'https://github.com/google-agentic-commerce/ap2/v1'], ['content-length', str(len(payload))]]

        def witness(index, payload, intercepted=False):
            return {'index': index, 'role': 'merchant', 'method': 'POST', 'url': url,
                    'request_entity': identity(payload), 'request_headers': headers_for(payload),
                    'request_path': '/a2a/merchant_agent', 'request_raw_path': '/a2a/merchant_agent', 'request_query': '',
                    'transport': 'owned_httpx_AsyncHTTPTransport_over_actual_TCP',
                    'original_request_mutated_by_native_transport': False, 'provider_request': False,
                    'native_tcp_application_dispatch_attempted': not intercepted,
                    'owned_bridge_initiation_intercepted_before_native_dispatch': intercepted}

        def exchange(index, path, payload, headers, response=b'{}', status=200, method='POST'):
            scope = {'type': 'http', 'server': ('127.0.0.1', 8001), 'client': ('127.0.0.1', 45001 + index),
                     'method': method, 'scheme': 'http', 'path': path, 'raw_path': path.encode(), 'query_string': b'',
                     'headers': [(key.encode(), value.encode()) for key, value in headers], 'http_version': '1.1'}
            return [{'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'scope', 'value': scope})},
                    {'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'receive_returned',
                        'value': {'type': 'http.request', 'body': payload}})},
                    {'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'send_completed',
                        'value': {'type': 'http.response.start', 'status': status, 'headers': []}})},
                    {'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'send_completed',
                        'value': {'type': 'http.response.body', 'body': response}})}]

        outgoing = [witness(0, body), witness(1, original, True)]
        sender = {'method': 'POST', 'url': url, 'entity': identity(original), 'headers': dict(headers_for(original))}
        write(output / 'bridge/original-sender-request.json', sender)
        (output / 'bridge/sender-wire.bin').write_bytes(original)
        card_path = '/.well-known/agent-card.json'
        card_url = 'http://127.0.0.1:8001' + card_path
        card_response = b'{"constructed_original_card_404":true}'
        node_headers = [['host', '127.0.0.1:8001'], ['accept', 'application/json'],
                        ['accept-encoding', 'gzip, deflate'], ['user-agent', 'node']]
        events = exchange(0, '/a2a/merchant_agent', body, headers_for(body)) + exchange(
            1, card_path, b'', node_headers, card_response, 404, 'GET')
        guarded = [{'kind': 'fetch-attempt', 'fetch_id': 1, 'url': card_url, 'method': 'GET',
                    'request_headers': [['accept', 'application/json']], 'request_entity': entity(b''),
                    'original_fetch_arguments_rewritten': False},
                   {'kind': 'fetch-response', 'fetch_id': 1, 'url': card_url, 'status': 404,
                    'response_entity': entity(card_response), 'original_response_replaced': False}]
        specs = [('matching_Node_header_subset_and_unique_intercept', outgoing, events, guarded),
                 ('missing_Node_fetch_witness', outgoing, events, []),
                 ('wrong_Node_explicit_header', outgoing, events, [dict(guarded[0], request_headers=[['accept', 'invalid/fixture']]), guarded[1]]),
                 ('wrong_Node_response_entity', outgoing, events, [guarded[0], dict(guarded[1], response_entity=entity(b'altered'))]),
                 ('wrong_Node_query_target', outgoing, events, [dict(row, url=card_url + '?unexpected=true') for row in guarded]),
                 ('wrong_intercept_entity', [outgoing[0], dict(outgoing[1], request_entity=identity(b'altered'))], events, guarded),
                 ('duplicate_false_intercept', outgoing + [dict(outgoing[1], index=2)], events, guarded),
                 ('unattributed_extra_native_receive', outgoing, events + exchange(2, '/unexpected', b'', node_headers, b'{}', 404, 'GET'), guarded)]
        for label, rows, current_events, current_guarded in specs:
            (output / 'native-wire-attempts.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
            write(output / 'transport-interventions.json', [{'index': row['index'], 'method': row['method'], 'url': row['url'],
                  'transport': 'owned_httpx_native_TCP', 'provider_request': False} for row in rows])
            (output / 'bridge/bridge-guard.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in current_guarded), encoding='utf-8')
            try:
                value = module.verify_native_capture(output, deepcopy(current_events), bridge_route=True)
                cases[label] = {'accepted': True, 'native_tcp_capture_verified': value.get('native_tcp_capture_verified'),
                               'Node_original_fetch_witnesses': value.get('Node_original_fetch_witnesses')}
            except Exception as error:
                cases[label] = {'accepted': False, 'error_type': type(error).__name__, 'reason': str(error)[:1000]}
    positive = 'matching_Node_header_subset_and_unique_intercept'
    controls = {label + ('_accepted' if label == positive else '_rejected'):
                row['accepted'] if label == positive else not row['accepted'] for label, row in cases.items()}
    report = {'schema_version': 'ap2-v8-bridge-sender-evidence-constructed-peer-control/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'evaluator_sha256': hashlib.sha256(raw).hexdigest(),
              'constructed_fixture_only': True, 'actual_application_or_provider_calls': 0,
              'actual_actor_or_bridge_processes_executed': 0, 'controls': controls, 'cases': cases,
              'passed': all(controls.values()),
              'scope': 'Synthetic independent evaluator fixtures only. Positive fixture attributes one original sender intercept and one supplied Node discovery exchange with extra generated wire headers; it is not an observed original application or bridge outcome.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, report)
    print(json.dumps({'passed': report['passed'], 'failed_controls': [key for key, value in controls.items() if not value]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
