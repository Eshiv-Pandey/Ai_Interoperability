"""Expanded zero-application peer controls for prospective V8 sender validation."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('_ap2_sender_peer_fixture',
    ROOT / 'scripts/review_ap2_v8_native_sender_peer_control_v1.py')
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
tag, identity, write = FIXTURE.tag, FIXTURE.identity, FIXTURE.write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_control_output_required')
    source = ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v8.py'
    raw = source.read_bytes()
    module = types.ModuleType('_ap2_v8_native_sender_expanded_constructed_peer')
    module.__file__ = str(source)
    exec(compile(raw, str(source), 'exec'), module.__dict__)
    cases = {}
    with tempfile.TemporaryDirectory(prefix='ap2-v8-native-sender-expanded-peer-') as temporary:
        output = Path(temporary)
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
        write(output / 'plan.json', {'policy': {'id': 'conventional', 'bridge_route': None}, 'provider_requests_allowed': 0})
        body = b'{"constructed_no_application_effect":true}'
        headers = [['host', '127.0.0.1:8001'], ['content-type', 'application/json'],
                   ['x-a2a-extensions', 'https://github.com/google-agentic-commerce/ap2/v1'], ['content-length', str(len(body))]]
        scope = {'type': 'http', 'server': ('127.0.0.1', 8001), 'client': ('127.0.0.1', 45001),
                 'method': 'POST', 'scheme': 'http', 'path': '/a2a/merchant_agent',
                 'raw_path': b'/a2a/merchant_agent', 'query_string': b'',
                 'headers': [(key.encode(), value.encode()) for key, value in headers], 'http_version': '1.1'}

        def exchange(index, current_body=body):
            return [{'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'scope', 'value': scope})},
                    {'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'receive_returned',
                        'value': {'type': 'http.request', 'body': current_body}})},
                    {'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'send_completed',
                        'value': {'type': 'http.response.start', 'status': 200, 'headers': []}})},
                    {'stream': 'merchant_raw', 'payload': tag({'exchange': index, 'boundary': 'send_completed',
                        'value': {'type': 'http.response.body', 'body': b'{}'}})}]

        events = exchange(0)
        witness = {'index': 0, 'role': 'merchant', 'method': 'POST', 'url': 'http://127.0.0.1:8001/a2a/merchant_agent',
                   'request_entity': identity(body), 'request_headers': headers, 'request_path': '/a2a/merchant_agent',
                   'request_raw_path': '/a2a/merchant_agent', 'request_query': '',
                   'transport': 'owned_httpx_AsyncHTTPTransport_over_actual_TCP',
                   'original_request_mutated_by_native_transport': False, 'provider_request': False,
                   'native_tcp_application_dispatch_attempted': True,
                   'owned_bridge_initiation_intercepted_before_native_dispatch': False}
        interventions = [{'index': 0, 'method': 'POST', 'url': witness['url'],
                          'transport': 'owned_httpx_native_TCP', 'provider_request': False}]
        specs = [('matching_sender_witness', [witness], events, interventions),
                 ('empty_sender_log', [], events, interventions),
                 ('arbitrary_false_dispatch_row', [dict(witness, native_tcp_application_dispatch_attempted=False)], events, interventions),
                 ('wrong_body_byte_count', [dict(witness, request_entity=dict(witness['request_entity'], bytes=len(body) + 1))], events, interventions),
                 ('wrong_query', [dict(witness, request_query='unexpected=true')], events, interventions),
                 ('wrong_explicit_headers', [dict(witness, request_headers=[['content-type', 'invalid/fixture']])], events, interventions),
                 ('unaccounted_native_received_exchange', [witness], events + exchange(1, b'{"unaccounted_fixture":true}'), interventions)]
        for label, rows, current_events, current_interventions in specs:
            (output / 'native-wire-attempts.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
            write(output / 'transport-interventions.json', current_interventions)
            try:
                value = module.verify_native_capture(output, deepcopy(current_events))
                cases[label] = {'accepted': True, 'native_tcp_capture_verified': value.get('native_tcp_capture_verified')}
            except Exception as error:
                cases[label] = {'accepted': False, 'error_type': type(error).__name__, 'reason': str(error)[:1000]}
    controls = {label + ('_accepted' if label == 'matching_sender_witness' else '_rejected'):
                row['accepted'] if label == 'matching_sender_witness' else not row['accepted']
                for label, row in cases.items()}
    report = {'schema_version': 'ap2-v8-native-sender-evidence-constructed-peer-control/2',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'evaluator_sha256': hashlib.sha256(raw).hexdigest(),
              'constructed_fixture_only': True, 'actual_application_or_provider_calls': 0,
              'actual_actor_or_bridge_processes_executed': 0, 'controls': controls, 'cases': cases,
              'passed': all(controls.values()),
              'scope': 'Independent evaluator only, with synthetic metadata/events. No actual socket or original application was executed. Baseline v1 failure evidence is preserved separately. These checks do not prove hosted outcomes or a hostile-code sandbox.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, report)
    print(json.dumps({'passed': report['passed'], 'failed_controls': [key for key, value in controls.items() if not value]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
