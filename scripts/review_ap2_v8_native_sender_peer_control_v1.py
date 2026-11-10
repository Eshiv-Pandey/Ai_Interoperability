"""Zero-application constructed control for AP2 V8 native sender evidence."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def tag(value):
    if value is None:
        return {'type': 'none'}
    if type(value) is bool:
        return {'type': 'bool', 'value': value}
    if type(value) is int:
        return {'type': 'int', 'value': str(value)}
    if type(value) is str:
        return {'type': 'str', 'value': value}
    if type(value) is bytes:
        return dict(type='bytes', value=base64.b64encode(value).decode(), **identity(value))
    if type(value) in (list, tuple):
        return {'type': 'tuple' if type(value) is tuple else 'list', 'items': [tag(row) for row in value]}
    if type(value) is dict:
        return {'type': 'dict', 'entries': [[tag(key), tag(row)] for key, row in value.items()]}
    raise TypeError('bounded_fixture_type')


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_control_output_required')
    source = ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v8.py'
    raw = source.read_bytes()
    module = types.ModuleType('_ap2_v8_native_sender_constructed_peer')
    module.__file__ = str(source)
    exec(compile(raw, str(source), 'exec'), module.__dict__)
    cases = {}
    with tempfile.TemporaryDirectory(prefix='ap2-v8-native-sender-peer-') as temporary:
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
        body = b'{"constructed_no_application_effect":true}'
        scope = {'type': 'http', 'server': ('127.0.0.1', 8001), 'client': ('127.0.0.1', 45001),
                 'method': 'POST', 'scheme': 'http', 'path': '/a2a/merchant_agent',
                 'raw_path': b'/a2a/merchant_agent', 'query_string': b'', 'headers': [], 'http_version': '1.1'}
        events = [{'stream': 'merchant_raw', 'payload': tag({'exchange': 0, 'boundary': 'scope', 'value': scope})},
                  {'stream': 'merchant_raw', 'payload': tag({'exchange': 0, 'boundary': 'receive_returned',
                                                           'value': {'type': 'http.request', 'body': body}})}]
        witness = {'index': 0, 'role': 'merchant', 'method': 'POST', 'url': 'http://127.0.0.1:8001/a2a/merchant_agent',
                   'request_entity': identity(body), 'request_headers': [],
                   'transport': 'owned_httpx_AsyncHTTPTransport_over_actual_TCP',
                   'original_request_mutated_by_native_transport': False, 'provider_request': False,
                   'native_tcp_application_dispatch_attempted': True,
                   'owned_bridge_initiation_intercepted_before_native_dispatch': False}
        for label, rows in (('matching_sender_witness', [witness]), ('empty_sender_log', []),
                            ('arbitrary_false_dispatch_row', [dict(witness,
                                native_tcp_application_dispatch_attempted=False,
                                owned_bridge_initiation_intercepted_before_native_dispatch=False)])):
            (output / 'native-wire-attempts.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
            try:
                value = module.verify_native_capture(output, events)
                cases[label] = {'accepted': True, 'native_tcp_capture_verified': value.get('native_tcp_capture_verified')}
            except Exception as error:
                cases[label] = {'accepted': False, 'error_type': type(error).__name__, 'reason': str(error)[:1000]}
    controls = {'matching_constructed_sender_witness_accepted': cases['matching_sender_witness']['accepted'],
                'empty_sender_log_rejected': not cases['empty_sender_log']['accepted'],
                'arbitrary_false_dispatch_row_rejected': not cases['arbitrary_false_dispatch_row']['accepted']}
    report = {'schema_version': 'ap2-v8-native-sender-evidence-constructed-peer-control/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'evaluator_sha256': identity(raw)['sha256'],
              'constructed_fixture_only': True, 'actual_application_or_provider_calls': 0,
              'actual_actor_or_bridge_processes_executed': 0, 'controls': controls, 'cases': cases,
              'passed': all(controls.values()),
              'scope': 'Calls only independent evaluator on minimal supplied synthetic receipts/events. No genuine native listener, process or original application was executed. This checks validation coverage, not observed traffic mutation.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, report)
    print(json.dumps({'passed': report['passed'], 'failed_controls': [key for key, value in controls.items() if not value]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
