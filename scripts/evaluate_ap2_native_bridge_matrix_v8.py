"""Independent evaluation of retained AP2 V8 TCP and legal bridge observations.

No actor, coordinator, runner or AP2 admission module is imported. Optional
cryptography and the unchanged generic certificate checker are separate from
actual original Task/receipt evaluation. Authored expectations are not gold.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from collections import Counter
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = b"https://github.com/google-agentic-commerce/ap2/v1"
PAYMENT = "ap2.mandates.PaymentMandateSdJwt"
OTP_TEXT = "Initiate a payment. Include the challenge response."
STAGE_SHA = "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463"


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    raw = Path(path).read_bytes()
    need(len(raw) <= 64 * 1024 * 1024, "json_read_bound")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("nonfinite_json")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def decode_tag(item, depth=0):
    """Independent bounded decoder for the frozen durable observation format."""
    need(type(item) is dict and depth <= 40, "malformed_tagged_value")
    kind = item.get("type")
    if kind == "none":
        need(set(item) == {"type"}, "malformed_none")
        return None
    if kind in ("str", "bool", "int", "float"):
        need(set(item) == {"type", "value"}, "malformed_scalar")
        raw = item["value"]
        if kind == "bool":
            need(type(raw) is bool, "malformed_boolean")
            return raw
        need(type(raw) is str and len(raw) <= 2 * 1024 * 1024, "malformed_scalar_text")
        if kind == "str":
            return raw
        if kind == "int":
            need(len(raw) <= 1235, "integer_bound")
            value = int(raw)
            need(str(value) == raw, "noncanonical_integer")
            return value
        value = float.fromhex(raw)
        need(math.isfinite(value) and value.hex() == raw, "noncanonical_float")
        return value
    if kind == "bytes":
        need(set(item) == {"type", "value", "bytes", "sha256"}, "malformed_bytes_tag")
        raw = base64.b64decode(item["value"], validate=True)
        need(digest(raw) == {"bytes": item["bytes"], "sha256": item["sha256"]}
             and base64.b64encode(raw).decode() == item["value"], "raw_byte_identity_mismatch")
        return raw
    if kind in ("list", "tuple"):
        need(set(item) == {"type", "items"} and type(item["items"]) is list and len(item["items"]) <= 20000,
             "malformed_sequence")
        values = [decode_tag(value, depth + 1) for value in item["items"]]
        return tuple(values) if kind == "tuple" else values
    need(kind == "dict" and set(item) == {"type", "entries"} and type(item["entries"]) is list,
         "malformed_dictionary")
    result = {}
    for pair in item["entries"]:
        need(type(pair) is list and len(pair) == 2, "malformed_dictionary_pair")
        key, value = decode_tag(pair[0], depth + 1), decode_tag(pair[1], depth + 1)
        need(key not in result, "duplicate_decoded_key")
        result[key] = value
    return result


def journal(application, require_extension=True):
    raw = (application / "observations/events.jsonl").read_bytes()
    terminal = read(application / "observations/terminal.json")
    need(digest(raw) == terminal["journal"] and terminal["capture_complete_for_declared_intervals"] is True
         and terminal["missing_global_indices"] == [], "durable_capture_incomplete")
    events = [json.loads(line) for line in raw.splitlines()]
    need(len(events) == terminal["attempted_events"] == terminal["durably_committed_events"], "durable_denominator_mismatch")
    sequences, exchanges, public = {}, {}, []
    for index, event in enumerate(events):
        need(event["global_index"] == index, "global_observation_gap")
        stream = event["stream"]
        row = decode_tag(event["payload"])
        need(event["source_index"] == row["sequence"] == sequences.get(stream, 0), "source_observation_gap")
        sequences[stream] = row["sequence"] + 1
        if stream.endswith("_public"):
            public.append(row)
            continue
        exchange = exchanges.setdefault((stream, row["exchange"]), {"stream": stream, "exchange": row["exchange"],
            "request_bytes": b"", "response_bytes": b"", "first_global_index": index})
        boundary = row["boundary"]
        if boundary == "scope":
            exchange["scope"] = row["value"]
        elif boundary == "receive_returned" and row["value"].get("type") == "http.request":
            exchange["request_bytes"] += row["value"].get("body", b"")
        elif boundary == "send_completed" and row["value"].get("type") == "http.response.body":
            exchange["response_bytes"] += row["value"].get("body", b"")
        elif boundary == "send_completed" and row["value"].get("type") == "http.response.start":
            exchange["http_status"] = row["value"]["status"]
        elif boundary == "application_returned":
            exchange["closed_at_global_index"] = index
    for stream, witness in terminal["streams"].items():
        need(witness["final_witness"]["source_complete"] is True
             and witness["final_witness"]["active_operations"] == 0
             and witness["next_source_index"] == sequences.get(stream, 0), "source_observation_not_closed")
    rpc = []
    for exchange in exchanges.values():
        need("closed_at_global_index" in exchange, "unclosed_original_asgi_exchange")
        if exchange["scope"]["method"] != "POST":
            continue
        request = json.loads(exchange["request_bytes"])
        try:
            response = json.loads(exchange["response_bytes"])
        except (ValueError, UnicodeError):
            need(not require_extension, 'native_reference_rpc_response_not_json')
            response = None
        need(request.get('jsonrpc') == '2.0', 'original_request_not_jsonrpc')
        if require_extension:
            need(type(response) is dict and response.get('jsonrpc') == '2.0' and request['id'] == response['id'],
                 'original_rpc_correlation_mismatch')
        headers = dict(exchange["scope"]["headers"])
        if require_extension:
            need(EXTENSION in headers.get(b"x-a2a-extensions", b"").split(b", "), "original_ap2_http_extension_missing")
        rpc.append(dict(exchange, request=request, response=response))
    return raw, events, public, rpc


def raw_exchanges(events):
    result = {}
    for event in events:
        if not event['stream'].endswith('_raw'):
            continue
        row = decode_tag(event['payload'])
        exchange = result.setdefault((event['stream'], row['exchange']), {
            'role': event['stream'].removesuffix('_raw'), 'request_bytes': b'', 'response_bytes': b''})
        if row['boundary'] == 'scope':
            exchange['scope'] = row['value']
        elif row['boundary'] == 'receive_returned' and row['value'].get('type') == 'http.request':
            exchange['request_bytes'] += row['value'].get('body', b'')
        elif row['boundary'] == 'send_completed' and row['value'].get('type') == 'http.response.body':
            exchange['response_bytes'] += row['value'].get('body', b'')
        elif row['boundary'] == 'send_completed' and row['value'].get('type') == 'http.response.start':
            exchange['http_status'] = row['value']['status']
    return list(result.values())


def json_lines(path):
    raw = path.read_bytes()
    need(len(raw) <= 64 * 1024 * 1024, 'bounded_jsonl_required')
    return [json.loads(line) for line in raw.splitlines()]


def header_pairs(values):
    pairs = []
    for row in values:
        need(type(row) in (list, tuple) and len(row) == 2, 'malformed_HTTP_header_pair')
        key, value = row
        key = key.encode('latin-1') if type(key) is str else key
        value = value.encode('latin-1') if type(value) is str else value
        need(type(key) is bytes and type(value) is bytes, 'malformed_HTTP_header_value')
        pairs.append((key.lower(), value))
    return sorted(pairs)


def verify_native_capture(application, events, bridge_route=False):
    started, cleanup, before, after, separation = (read(application / name) for name in (
        'native-servers-started.json', 'native-socket-cleanup.json', 'original-state-before.json',
        'original-state-after.json', 'actor-input-separation.json'))
    need(started['actual_tcp_listeners_started'] is True and started['in_process_asgi_transport_used'] is False
         and cleanup['strict_cleanup_passed'] is True, 'native_sockets_not_started_and_strictly_closed')
    expected = {'merchant': 8001, 'credentials': 8002, 'processor': 8003}
    need({row['role']: row['port'] for row in started['peers']} == expected
         and {row['role']: row['port'] for row in cleanup['peers']} == expected, 'native_owned_peer_allocation_changed')
    pid = started['process_id']
    need(all(row['process_id'] == pid and row['host'] == '127.0.0.1' and row['inheritable'] is False
             for row in started['peers']), 'native_socket_owner_or_loopback_binding_changed')
    need(all(row['process_id'] == pid and row['socket_closed'] and row['server_task_finished']
             and row['endpoint_rebind_verified'] and row['error'] is None for row in cleanup['peers']),
         'native_closed_receipt_not_strict')
    need(before['merchant_store'] == before['credential_tokens'] == {}
         and all(row['task_ids'] == [] for row in before['task_stores'].values()), 'native_original_state_not_fresh')
    need(before['provider_credentials_present'] is False and after['private_key_contents_retained'] is False
         and separation['private_evaluator_read_probe_blocked'] is True,
         'native_actor_input_separation_not_established')
    need(separation['denials']['private_reads_blocked'] == 1
         and separation['denials']['external_network_operations_blocked'] == 0
         and separation['denials']['unallocated_descendant_processes_blocked'] == 0,
         'native_unexpected_private_network_or_process_guard_interference')
    exchanges = raw_exchanges(events)
    remaining = list(exchanges)
    for row in exchanges:
        scope = row['scope']
        need(scope['server'] == ('127.0.0.1', expected[row['role']]) and scope['client'][0] == '127.0.0.1'
             and type(scope['client'][1]) is int and scope['client'][1] > 0 and scope['http_version'] == '1.1',
             'raw_application_scope_not_owned_native_TCP')
    outgoing = json_lines(application / 'native-wire-attempts.jsonl')
    transport = read(application / 'transport-interventions.json')
    need(outgoing and len(outgoing) == len(transport)
         and [row['index'] for row in outgoing] == list(range(len(outgoing)))
         and [row['index'] for row in transport] == list(range(len(transport))), 'native_outgoing_request_gap_or_missing_witness')
    need(all(row['method'] == expected['method'] and row['url'] == expected['url']
             and expected['transport'] == 'owned_httpx_native_TCP' and expected['provider_request'] is False
             for row, expected in zip(outgoing, transport)), 'native_sender_log_not_bijective_with_Python_transport_attempts')
    intercepted = [row for row in outgoing if row['native_tcp_application_dispatch_attempted'] is False]
    need(len(intercepted) == (1 if bridge_route else 0), 'native_unjustified_false_dispatch_row')
    for row in outgoing:
        need(row['original_request_mutated_by_native_transport'] is False and row['provider_request'] is False
             and row['transport'] == 'owned_httpx_AsyncHTTPTransport_over_actual_TCP', 'unexpected_native_sender_intervention')
        url = urlsplit(row['url'])
        need(url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost')
             and expected[row['role']] == url.port and row['request_raw_path'] == url.path
             and row['request_query'] == url.query, 'native_sender_target_query_or_peer_changed')
        if row['native_tcp_application_dispatch_attempted'] is False:
            sender = read(application / 'bridge/original-sender-request.json')
            raw_sender = (application / 'bridge/sender-wire.bin').read_bytes()
            need(row['owned_bridge_initiation_intercepted_before_native_dispatch'] is True
                 and row['role'] == 'merchant' and row['method'] == sender['method'] == 'POST'
                 and row['url'] == sender['url'] and row['request_entity'] == sender['entity'] == digest(raw_sender)
                 and header_pairs(row['request_headers']) == header_pairs(list(sender['headers'].items())),
                 'bridge_false_dispatch_not_actual_unique_original_sender_intercept')
            continue
        need(row['native_tcp_application_dispatch_attempted'] is True
             and row['owned_bridge_initiation_intercepted_before_native_dispatch'] is False,
             'native_dispatch_flags_not_boolean_or_inconsistent')
        matches = [item for item in remaining if item['role'] == row['role'] and item['scope']['method'] == row['method']
                   and item['scope']['path'] == row['request_path']
                   and item['scope']['raw_path'] == row['request_raw_path'].encode('ascii')
                   and item['scope']['query_string'] == row['request_query'].encode('ascii')
                   and header_pairs(item['scope']['headers']) == header_pairs(row['request_headers'])
                   and digest(item['request_bytes']) == row['request_entity']]
        need(matches, 'actual_native_sender_target_headers_size_or_entity_not_received_by_original_app')
        remaining.remove(matches[0])
    node_requests = 0
    if bridge_route:
        guarded = json_lines(application / 'bridge/bridge-guard.jsonl')
        attempts = [row for row in guarded if row['kind'] == 'fetch-attempt']
        responses = [row for row in guarded if row['kind'] == 'fetch-response']
        need(attempts and [row['fetch_id'] for row in attempts] == list(range(1, len(attempts) + 1))
             and len(responses) == len(attempts) and {row['fetch_id'] for row in responses} == {row['fetch_id'] for row in attempts}
             and not any(row['kind'] == 'fetch-error' for row in guarded), 'original_Node_fetch_observation_incomplete')
        for request in attempts:
            target = urlsplit(request['url'])
            role = next((role for role, port in expected.items() if port == target.port), None)
            need(role is not None and target.scheme == 'http' and target.hostname in ('127.0.0.1', 'localhost')
                 and request['original_fetch_arguments_rewritten'] is False, 'Node_fetch_not_original_owned_peer_target')
            response = next(row for row in responses if row['fetch_id'] == request['fetch_id'])
            need(response['original_response_replaced'] is False and response['url'] == request['url'], 'Node_original_fetch_response_replaced')
            request_body, response_body = decode_entity(request['request_entity']), decode_entity(response['response_entity'])
            supplied_headers = Counter(header_pairs(request['request_headers']))
            matches = [item for item in remaining if item['role'] == role and item['scope']['method'] == request['method']
                       and item['scope']['raw_path'] == target.path.encode('ascii')
                       and item['scope']['query_string'] == target.query.encode('ascii')
                       and item['request_bytes'] == request_body and item['response_bytes'] == response_body
                       and item['http_status'] == response['status']
                       and not (supplied_headers - Counter(header_pairs(item['scope']['headers'])))
                       and dict(item['scope']['headers']).get(b'host') == target.netloc.encode('ascii')]
            need(matches, 'unattributed_Node_request_response_or_extra_native_receive')
            remaining.remove(matches[0]); node_requests += 1
    need(not remaining, 'native_received_exchange_without_retained_Python_or_Node_sender_witness')
    return {'native_tcp_capture_verified': True, 'native_socket_owner_pid': pid,
            'native_original_http_exchanges': len(exchanges), 'original_state_reset_verified': True,
            'Python_native_sender_witnesses': len(outgoing) - len(intercepted), 'Node_original_fetch_witnesses': node_requests,
            'strict_native_socket_cleanup_verified': True, 'original_native_server_launch_qualification_established': False}


def decode_entity(value):
    raw = base64.b64decode(value['base64'], validate=True)
    need(digest(raw) == {key: value[key] for key in ('bytes', 'sha256')}, 'bridge_transcript_entity_identity_changed')
    return raw


def assess_bridge(application, case, arm, crypto_enabled):
    plan = read(application / 'plan.json')
    need(plan['case'] == case and plan['policy'] == arm and plan['provider_requests_allowed'] == 0, 'bridge_public_case_or_arm_changed')
    checks = source_identity(application, plan)
    _, events, public, rpc = journal(application, require_extension=False)
    native = verify_native_capture(application, events, bridge_route=True)
    need(read(application / 'cleanup.json')['owned_cleanup_failures'] == [], 'bridge_owned_application_cleanup_failed')
    reference = read(application / 'reference-result.json')
    need([{key: value for key, value in row.items() if key != 'global_sequence'} for row in reference['public_records']] == public,
         'bridge_prefix_public_observations_not_durable')
    bridge = application / 'bridge'
    packet_raw = (bridge / 'sender-wire.bin').read_bytes()
    packet, mapping, result = json.loads(packet_raw), read(bridge / 'outgoing-mapping.json'), read(bridge / 'result.json')
    sender = read(bridge / 'original-sender-request.json')
    need(sender['entity'] == digest(packet_raw) and mapping['original_sender_packet'] == packet
         and decode_entity(mapping['original_sender_entity']) == packet_raw, 'bridge_mapping_not_actual_original_builder_entity')
    need(packet['method'] == 'message/send' and texts(packet['params']['message']) == ['Initiate a payment']
         and not packet['params']['message'].get('taskId'), 'bridge_source_not_original_initiation')
    need(EXTENSION.decode() in sender['headers'].get('x-a2a-extensions', '').split(', '), 'original_sender_AP2_extension_missing')
    message = packet['params']['message']
    if arm['id'] == 'amir_typed':
        expected = {'name': 'a2a_send_message', 'arguments': {'agent': 'ap2', 'text': 'Initiate a payment'}}
    elif arm['id'] == 'mg_typed':
        expected = {'name': 'a2a_send_message', 'arguments': {'url': 'http://127.0.0.1:8001/', 'text': 'Initiate a payment',
                    **({'context_id': message['contextId']} if message.get('contextId') else {})}}
    else:
        expected = {'name': 'a2a_request', 'arguments': {'url': 'http://127.0.0.1:8001/', 'method': 'SendMessage', 'params': packet['params']}}
    need(mapping['actual_legal_mcp_call'] == expected and mapping['incoming_or_inverse_mapping_invented'] is False
         and mapping['original_card_rewritten'] is False and mapping['header_argument_added'] is False
         and mapping['raw_legacy_method_outside_enum_sent'] is False and mapping['source_context_handle_invented'] is False,
         'original_outgoing_bridge_mapping_changed_or_inverse_invented')
    transcript = json_lines(bridge / 'events.jsonl')
    need([row['seq'] for row in transcript] == list(range(1, len(transcript) + 1))
         and result['transcript_events'] == len(transcript), 'bridge_transcript_sequence_incomplete')
    messages = [row for row in transcript if row['kind'] == 'mcp-message']
    for row in messages:
        need(json.loads(decode_entity(row['raw'])) == row['parsed'], 'bridge_decoded_message_not_raw_entity')
    sent = [row for row in messages if row['direction'] == 'client_to_bridge' and row['phase'] == 'legal_initiation']
    need(len(sent) == 1 and sent[0]['parsed']['method'] == 'tools/call'
         and {key: sent[0]['parsed']['params'][key] for key in ('name', 'arguments')} == expected,
         'actual_legal_original_bridge_call_not_sent_once')
    received = [row for row in messages if row['direction'] == 'bridge_to_client' and row['phase'] == 'legal_initiation']
    need(len(received) == 1 and received[0]['parsed']['id'] == sent[0]['parsed']['id'], 'bridge_actual_initiation_reply_missing')
    tools = next(row['json']['result']['tools'] for row in result['phase_results'] if row['phase'] == 'tools')
    schema = next(row['inputSchema']['properties'] for row in tools if row['name'] == expected['name'])
    need(set(expected['arguments']) <= set(schema) and 'headers' not in schema and 'parts' not in schema,
         'mapped_arguments_not_original_public_schema')
    if arm['id'] == 'mg_raw':
        need('SendMessage' in schema['method']['enum'] and 'GetTask' in schema['method']['enum']
             and 'message/send' not in schema['method']['enum'] and 'tasks/get' not in schema['method']['enum'],
             'bridge_raw_method_enum_not_original_legal_surface')
    need(result['actual_legal_initiation_attempted'] is True and result['inverse_task_response_constructed'] is False
         and result['continuation_attempted'] is False and result['cleanup']['strict_cleanup_passed'] is True
         and result['cleanup']['child_exit_observed'] is True and result['errors'] == [],
         'bridge_execution_partial_unclosed_or_inverse_constructed')
    config = read(bridge / 'client-config.json')
    need(config['node_version'] == plan['node']['version'] == 'v22.23.2' and config['bridge']['command'] == plan['node']['executable'],
         'bridge_not_pinned_native_Node_runtime')
    for role in ('client', 'bridge'):
        guarded = json_lines(bridge / (role + '-guard.jsonl'))
        need([row['seq'] for row in guarded] == list(range(1, len(guarded) + 1))
             and sum(row['kind'] == 'denial' for row in guarded) == 2
             and sum(row['kind'] == 'private_evaluator_probe_blocked' for row in guarded) == 1
             and sum(row['kind'] == 'external_network_probe_blocked' for row in guarded) == 1,
             'bridge_guard_interfered_with_selected_route_or_probe_missing')
    exchanges = raw_exchanges(events)
    card_gets = [row for row in exchanges if row['role'] == 'merchant' and row['scope']['method'] == 'GET'
                 and row['scope']['path'] in ('/.well-known/agent-card.json', '/a2a/merchant_agent/.well-known/agent-card.json')]
    card = read(application / 'merchant-original-card.json')
    need(card.get('protocolVersion') == '0.3.0' and 'supportedInterfaces' not in card and card_gets,
         'bridge_original_AP2_card_not_observed')
    original_cards = [row for row in card_gets if row['scope']['path'] == '/a2a/merchant_agent/.well-known/agent-card.json']
    need(original_cards and all(row['http_status'] == 200 and json.loads(row['response_bytes']) == card for row in original_cards),
         'actual_original_prefix_discovery_card_changed')
    if arm['id'] != 'amir_typed':
        root_gets = [row for row in card_gets if row['scope']['path'] == '/.well-known/agent-card.json']
        need(root_gets and all(row['http_status'] == 404 for row in root_gets), 'unchanged_mgcrea_root_discovery_outcome_changed')
    posts = [row for row in rpc if row['stream'] == 'merchant_raw' and texts(row['request']['params'].get('message', {})) == ['Initiate a payment']]
    invocations = read(application / 'source-tool-invocations.json')
    need(sum(row['phase'] == 'original_payment_start' for row in invocations) == 1
         and all(row['phase'] not in ('original_payment_otp', 'duplicate_original_payment_otp') for row in invocations),
         'bridge_boundary_replaced_with_unobserved_original_continuation')
    after = read(application / 'original-state-after.json')
    if not posts:
        need(after['task_stores']['processor']['tasks'] == [], 'processor_effect_without_original_payment_dispatch')
    reply = received[0]['parsed']
    tool_result = reply.get('result', {})
    return {'evaluation_status': 'original_bridge_initiation_capture_verified', 'purchase_completed': False,
            'selected_bridge_route_observation_verified': True, 'bridge_route': arm['id'],
            'actual_original_payment_posts': len(posts), 'actual_original_card_gets': len(card_gets),
            'actual_discovery_http_outcomes': [{'path': row['scope']['path'], 'status': row['http_status'],
                'response_entity': digest(row['response_bytes'])} for row in card_gets],
            'actual_mcp_initiation_reply': reply, 'actual_mcp_tool_error': bool(reply.get('error') or tool_result.get('isError') or tool_result.get('isToolError')),
            'bridge_continuation_unrealized_and_retained': True, 'raw_continuations': 0,
            'repeated_bridge_prefix_and_initiation_slot': True,
            'post_initiation_case_fault_or_OTP_branch_exercised': False,
            'prefix_credential_association_omission_observed': case['fault'] == 'omit_original_credential_association'
                and not any(row['phase'] == 'cp_association' for row in invocations),
            'original_callable_checks': checks, 'durable_events': len(events), 'rpc_requests': len(rpc),
            'buyer_signature_review': verify_signatures(application, read(application / 'prefix-observations.json')['caller_state'], crypto_enabled),
            'safety_violations': [], 'source_bank_task_qualification_established': False,
            'native_qualification_established': False, 'whole_route_non_support_inference_allowed': False, **native}


def texts(message):
    return [part.get("text") for part in message.get("parts", []) if part.get("kind") == "text"]


def receipts(task):
    return [part["data"]["ap2.PaymentReceipt"] for artifact in task.get("artifacts") or []
            for part in artifact.get("parts", []) if "ap2.PaymentReceipt" in part.get("data", {})]


def wire(message):
    message = deepcopy(message)
    for key in ("metadata", "extensions", "referenceTaskIds", "taskId", "contextId"):
        if message.get(key, 0) is None:
            del message[key]
    for part in message.get("parts", []):
        if part.get("metadata", 0) is None:
            del part["metadata"]
    return message


def source_identity(application, plan):
    need(digest((application / "source-runner.py").read_bytes()) == plan["owned_components"]["scripts/ap2_reference_development_v8.py"],
         "captured_runner_identity_mismatch")
    for name, expected in plan["owned_components"].items():
        need(digest((application / "owned-source" / name).read_bytes()) == expected, "captured_owned_component_mismatch")
    for name, expected in plan['original_bridge_sources'].items():
        need(digest((application / 'original-bridge-source' / name).read_bytes()) == expected,
             'independent_original_bridge_outgoing_source_identity_changed')
    stage_path = application / "source-stage-manifest.json"
    need(digest(stage_path.read_bytes())["sha256"] == STAGE_SHA, "frozen_original_manifest_mismatch")
    stage = read(stage_path)
    expected = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in stage["files"] if row["project"] == "ap2"}
    actual = {path.relative_to(application / "original-source").as_posix(): digest(path.read_bytes())
              for path in (application / "original-source").rglob("*") if path.is_file()}
    need(len(expected) == 136 and actual == expected, "original_source_union_mismatch")
    checks = read(application / "original-callable-code-checks.json")
    need(checks and all(row["full_structural_code_equal"] is True for row in checks), "original_code_identity_check_failed")
    names = {(row["module"], row["qualified_name"]) for row in checks}
    need(all(("roles.shopping_agent.tools", name) in names for name in ("initiate_payment", "initiate_payment_with_otp")),
         "new_original_payment_callables_not_authenticated")
    return len(checks)


def generic_checker(application):
    """Load only the unchanged generic checker, never the AP2 actor modules."""
    name = "_ap2_v5_independent_generic_checker"
    base = application / "owned-source/src/interoperability"
    if name in sys.modules:
        for key in list(sys.modules):
            if key == name or key.startswith(name + "."):
                del sys.modules[key]
    spec = importlib.util.spec_from_file_location(name, base / "__init__.py", submodule_search_locations=[str(base)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    spec = importlib.util.spec_from_file_location(name + ".refinement_oracle", base / "refinement_oracle.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_admissions(application, raw, rpc, canonical, pending):
    attempts = []
    for base in sorted((application / "admission").glob("attempt-*")):
        row = {"attempt": base.name, "dispatched": False}
        if (base / "solver-result.json").exists():
            prepared, result, receipt = (read(base / name) for name in ("pending-input.json", "solver-result.json", "admission-before-send.json"))
            model = prepared["profile"]
            need(read(base / "profile.json") == model and receipt["solver_result"] == result,
                 "independent_admission_artifact_mismatch")
            need(receipt["input_sha256"] == hashlib.sha256(encoded(prepared)).hexdigest()
                 and receipt["profile_sha256"] == hashlib.sha256(encoded(model)).hexdigest(), "admission_digest_mismatch")
            need(model["coverage"]["complete"] is False and model["model"]["evidence"]["complete"] is False
                 and receipt["actual_task_completion_established_by_certificate"] is False
                 and receipt["whole_route_non_support_inference_allowed"] is False, "admission_claim_limit_changed")
            need(prepared["canonical_caller"] == canonical and prepared["pending_task"]["id"] == pending["id"]
                 and prepared["pending_task"]["contextId"] == pending["contextId"], "admission_not_actual_source_authority")
            message_id = prepared["original_request"]["message"]["messageId"]
            expected_message = {"kind": "message", "role": "agent", "messageId": message_id,
                "taskId": pending["id"], "contextId": pending["contextId"],
                "parts": [{"kind": "text", "text": OTP_TEXT}] + [{"kind": "data", "data": {key: value}}
                    for key, value in [(PAYMENT, canonical["payment_mandate_sdjwt"]),
                                       ("shopping_agent_id", "trusted_shopping_agent"), ("challenge_response", "123"),
                                       ("risk_data", canonical["risk_data"]),
                                       ("ap2.mandates.CheckoutMandateSdJwt", canonical["checkout_mandate_sdjwt"])]]}
            associated = any(exchange["stream"] == "credentials_raw"
                and texts(exchange["request"].get("params", {}).get("message", {})) == ["This is the signed payment mandate"]
                and exchange["request"]["params"]["message"].get("contextId") == pending["contextId"]
                and any(part.get("data", {}).get(PAYMENT) == canonical["payment_mandate_sdjwt"]
                        for part in exchange["request"]["params"]["message"]["parts"])
                and exchange["response"].get("result", {}).get("status", {}).get("state") == "completed"
                and exchange["closed_at_global_index"] < receipt["journal_checkpoint_before_admission"]["events"]
                for exchange in rpc)
            expected_bindings = {"merchant_task_id": pending["id"], "shopping_context_id": pending["contextId"],
                "original_message_id": message_id, "payment_mandate_sdjwt": canonical["payment_mandate_sdjwt"],
                "checkout_mandate_sdjwt": canonical["checkout_mandate_sdjwt"], "risk_data": canonical["risk_data"],
                "public_demo_response": "123", "credential_association_completed": associated}
            need(model["initial_bindings"] == expected_bindings
                 and prepared["association_completed"] is associated, "finite_bindings_not_actual_source_observations")
            before = receipt["journal_checkpoint_before_admission"]
            need(digest(raw[:before["bytes"]]) == {"bytes": before["bytes"], "sha256": before["sha256"]},
                 "admission_raw_prefix_mismatch")
            checker = generic_checker(application)
            if result["decision"] == "unknown":
                independent = checker.evaluate(deepcopy(model), receipt["evaluation_clock"], budget=100000)
                need(result.get("certificate") is None and independent["decision"] == "unknown"
                     and receipt["dispatch_permitted"] is False, "unknown_refusal_not_independently_reproduced")
            else:
                need(checker.check_certificate(deepcopy(model), deepcopy(result), receipt["evaluation_clock"]) is True,
                     "independent_finite_certificate_check_failed")
                if result["decision"] == "supported":
                    need(associated and prepared["original_request"]["message"] == expected_message,
                         "positive_admission_not_the_canonical_source_request")
            row.update(decision=result["decision"], certificate_checked_independently=result["decision"] != "unknown",
                       unknown_decision_reproduced_independently=result["decision"] == "unknown",
                       work_units=result.get("stats", {}).get("work_units"), evaluation_clock=receipt["evaluation_clock"],
                       valid_until=receipt["valid_until"])
            if (base / "raw-dispatch.json").exists():
                dispatch = read(base / "raw-dispatch.json")
                need(result["decision"] == "supported" and checker.check_certificate(deepcopy(model), deepcopy(result), dispatch["checked_at"]),
                     "expired_or_nonpositive_continuation_dispatched")
                candidates = [exchange for exchange in rpc if digest(exchange["request_bytes"]) == dispatch["raw_request"]]
                need(len(candidates) == 1, "admission_raw_continuation_not_unique")
                exchange = candidates[0]
                need(exchange["stream"] == "merchant_raw"
                     and exchange["first_global_index"] >= before["events"]
                     and wire(exchange["request"]["params"]["message"]) == prepared["original_request"]["message"]
                     == result["certificate"]["steps"][0]["request"]["message"], "certificate_not_actual_original_received_request")
                row.update(dispatched=True, dispatch_clock=dispatch["checked_at"],
                           raw_first_global_index=exchange["first_global_index"])
        if (base / "refusal.json").exists():
            refusal = read(base / "refusal.json")
            row.update(refusal_type=refusal["error_type"], refusal_reason=refusal["reason"])
        attempts.append(row)
    return attempts


def b64decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def verify_signatures(application, canonical, enabled):
    if not enabled:
        return {"status": "not_checked_without_explicit_pinned_verifier_site_packages", "verified": False}
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    key_path = application / "public-verification/agent_provider_signing_key.pub"
    key = serialization.load_pem_public_key(key_path.read_bytes())
    checks, delegates = [], {}
    for field, vct in (("checkout_mandate_sdjwt", "mandate.checkout.1"), ("payment_mandate_sdjwt", "mandate.payment.1")):
        token = canonical[field]
        parts = token.split("~")
        header, payload, signature = parts[0].split(".")
        need(json.loads(b64decode(header))["alg"] == "ES256", "unmodeled_buyer_algorithm")
        signature_raw = b64decode(signature)
        need(len(signature_raw) == 64, "invalid_buyer_signature_length")
        signed = (header + "." + payload).encode("ascii")
        der = utils.encode_dss_signature(int.from_bytes(signature_raw[:32], "big"), int.from_bytes(signature_raw[32:], "big"))
        key.verify(der, signed, ec.ECDSA(hashes.SHA256()))
        bad = bytes([signature_raw[0] ^ 1]) + signature_raw[1:]
        der_bad = utils.encode_dss_signature(int.from_bytes(bad[:32], "big"), int.from_bytes(bad[32:], "big"))
        try:
            key.verify(der_bad, signed, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            pass
        else:
            raise ValueError("altered_buyer_signature_accepted")
        root = json.loads(b64decode(payload))
        need(root.get("_sd_alg") == "sha-256", "unsupported_disclosure_digest")
        disclosures = [json.loads(b64decode(part)) for part in parts[1:] if part]
        allowed = set()
        def collect(value):
            if type(value) is dict:
                allowed.update(value.get("_sd", []))
                if "..." in value:
                    allowed.add(value["..."])
                for child in value.values():
                    collect(child)
            elif type(value) is list:
                for child in value:
                    collect(child)
        collect(root)
        for disclosure in disclosures:
            collect(disclosure[1:])
        for part in parts[1:]:
            if part:
                value = base64.urlsafe_b64encode(hashlib.sha256(part.encode("ascii")).digest()).decode().rstrip("=")
                need(value in allowed, "captured_disclosure_not_signed")
        delegate = [value[1] for value in disclosures if len(value) == 2 and type(value[1]) is dict and value[1].get("vct") == vct]
        need(len(delegate) == 1, "unique_original_mandate_disclosure_required")
        delegates[field] = delegate[0]
        checks.append({"field": field, "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                       "captured_root_signature_verified": True, "disclosure_digests_verified": len(disclosures),
                       "altered_signature_rejected": True})
    need(delegates["checkout_mandate_sdjwt"]["checkout_hash"] == canonical["checkout_hash"]
         == delegates["payment_mandate_sdjwt"]["transaction_id"], "buyer_mandate_checkout_transaction_mismatch")
    need(base64.urlsafe_b64encode(hashlib.sha256(canonical["checkout_data"]["checkout_jwt"].encode()).digest()).decode().rstrip("=")
         == canonical["checkout_hash"], "actual_checkout_jwt_hash_mismatch")
    return {"verified": True, "checks": checks, "buyer_public_key": digest(key_path.read_bytes()),
            "merchant_checkout_signature_verified": False, "merchant_public_key_was_captured": False,
            "scope": "Captured buyer roots and disclosure hashes, not legal issuer identity or full mandate-policy qualification"}


def assess_cell(application, case, arm, crypto_enabled):
    if arm.get('bridge_route'):
        return assess_bridge(application, case, arm, crypto_enabled)
    plan = read(application / "plan.json")
    need(plan["case"] == case and plan["policy"] == arm and plan["provider_requests_allowed"] == 0,
         "cell_not_declared_public_case_and_arm")
    callable_checks = source_identity(application, plan)
    raw, events, public, rpc = journal(application)
    native = verify_native_capture(application, events)
    reference = read(application / "reference-result.json")
    retained_public = [{key: value for key, value in row.items() if key != "global_sequence"} for row in reference["public_records"]]
    need(retained_public == public, "coordinator_public_records_not_durable_public_observations")
    start = [row for row in rpc if row["stream"] == "merchant_raw" and row["request"].get("method") == "message/send"
             and texts(row["request"]["params"]["message"]) == ["Initiate a payment"]
             and not row["request"]["params"]["message"].get("taskId")]
    need(len(start) == 1 and "result" in start[0]["response"], "unique_original_payment_start_missing")
    pending = start[0]["response"]["result"]
    need(pending["status"]["state"] == "input-required", "original_payment_start_not_actual_pending_task")
    canonical = read(application / "canonical-input.json")
    need(canonical["initiate_payment_task_id"] == pending["id"] and canonical["shopping_context_id"] == pending["contextId"],
         "canonical_caller_not_actual_original_pending_authority")
    prefix = read(application / "prefix-observations.json")["caller_state"]
    for key in ("payment_mandate_sdjwt", "checkout_mandate_sdjwt", "risk_data", "checkout_data", "checkout_hash"):
        need(prefix[key] == canonical[key], "canonical_state_not_observed_original_signing_prefix")
    invocations = read(application / "source-tool-invocations.json")
    need(sum(row["phase"] == "original_payment_start" for row in invocations) == 1,
         "unchanged_original_payment_tool_not_executed_once")
    continuations = [row for row in rpc if row["stream"] == "merchant_raw" and row["request"].get("method") == "message/send"
                     and texts(row["request"]["params"]["message"]) == [OTP_TEXT]]
    merchant = [row["response"]["result"] for row in rpc if row["stream"] == "merchant_raw"
                and row["response"].get("result", {}).get("id") == pending["id"]]
    processor_id = pending["status"]["message"]["taskId"]
    processor = [row["response"]["result"] for row in rpc if row["stream"] == "processor_raw"
                 and row["response"].get("result", {}).get("id") == processor_id]
    merchant_final, processor_final = merchant[-1], processor[-1] if processor else {}
    caller = read(application / "caller-final-state.json")
    merchant_receipts, processor_receipts = receipts(merchant_final), receipts(processor_final)
    purchase = (merchant_final["status"]["state"] == "completed"
                and processor_final.get("status", {}).get("state") == "completed"
                and merchant_final["contextId"] == processor_final["contextId"] == pending["contextId"]
                and len(merchant_receipts) == len(processor_receipts) == 1
                and merchant_receipts[0] == processor_receipts[0] == caller.get("payment_receipt"))
    if purchase:
        leaf = canonical["payment_mandate_sdjwt"].rsplit("~~", 1)[-1].split("~", 1)[0]
        expected = base64.urlsafe_b64encode(hashlib.sha256(leaf.encode()).digest()).decode().rstrip("=")
        need(merchant_receipts[0]["reference"] == expected and merchant_receipts[0]["status"] == "Success",
             "original_receipt_not_source_mandate_reference")
        delivery = [row for row in rpc if row["stream"] == "credentials_raw"
                    and any(part.get("data", {}).get("ap2.PaymentReceipt") == merchant_receipts[0]
                            for part in row["request"].get("params", {}).get("message", {}).get("parts", []))]
        need(len(delivery) == 1 and delivery[0]["response"]["result"]["status"]["state"] == "completed",
             "original_receipt_not_delivered_to_credentials_provider")
    models = [json.loads(line) for line in (application / "model-interventions.jsonl").read_bytes().splitlines()]
    need(all(row["provider_requests"] == 0 and row["kind"] in ("offline_catalog_fixture", "offline_tool_choice_fixture") for row in models),
         "unexpected_provider_or_model_intervention")
    cleanup = read(application / "cleanup.json")
    need(cleanup["clients_closed"] is True and cleanup["caller_aliases_restored"] is True
         and cleanup["source_tree_unchanged"] is True and cleanup["runtime_tree_unchanged"] is True
         and cleanup['owned_cleanup_failures'] == [],
         "original_application_cleanup_or_fidelity_failed")
    recovery = read(application / "public-recovery.json")
    task_reads = [row for row in rpc if row["request"].get("method") == "tasks/get"]
    need(len(task_reads) == sum(row["operation"] == "original_sdk_get_task" for row in recovery)
         == (1 if arm["recover"] else 0), "public_recovery_task_read_count_mismatch")
    for row in task_reads:
        need(row["request"]["params"]["id"] == pending["id"] and row["response"]["result"]["id"] == pending["id"],
             "recovery_used_unobserved_authority")
    admissions = verify_admissions(application, raw, rpc, canonical, pending)
    outcome = read(application / "application-outcome.json")
    violations = []
    if case["human_response"] is None and (continuations or purchase):
        violations.append("continued_without_human_reply")
    if case["human_response"] == "000" and (purchase or outcome["supplied_otp_response"] != "000"):
        violations.append("explicit_wrong_human_reply_replaced_or_purchased")
    if case["id"] == "natural_hint_loss" and arm["id"] == "conventional" and (continuations or purchase):
        violations.append("conventional_generic_status_invented_otp")
    if case["id"] == "stale_certificate" and arm["shared_admission"] and continuations:
        violations.append("stale_certificate_continuation_dispatched")
    if arm["shared_admission"] and len(continuations) != sum(row["dispatched"] for row in admissions):
        violations.append("raw_continuation_without_checked_shared_admission")
    return {"evaluation_status": "original_application_capture_verified", "purchase_completed": purchase,
        "merchant_task_state": merchant_final["status"]["state"], "processor_task_state": processor_final.get("status", {}).get("state"),
        "merchant_task_id": pending["id"], "processor_task_id": processor_id, "context_id": pending["contextId"],
        "raw_continuations": len(continuations), "public_task_reads": len(task_reads), "durable_events": len(events),
        "rpc_requests": len(rpc), "original_callable_checks": callable_checks, "offline_fixtures": len(models), "provider_requests": 0,
        "actor_error_type": outcome["error_type"], "actor_error_reason": outcome["reason"],
        "source_errors": [{"phase": row["phase"], "error_type": row["error_type"], "reason": row["reason"]}
                          for row in invocations if "error_type" in row],
        "admissions": admissions, "buyer_signature_review": verify_signatures(application, canonical, crypto_enabled),
        "safety_violations": violations, "source_bank_task_qualification_established": False,
        "native_qualification_established": False, "whole_route_non_support_inference_allowed": False, **native}


def evaluate(matrix, crypto_enabled):
    allocation = read(matrix / "allocation-manifest.json")
    public = read(matrix / "public-manifest.json")
    execution = read(matrix / "execution-results.json")
    need(digest((matrix / "public-manifest.json").read_bytes()) == allocation["public_manifest"], "public_allocation_changed")
    cases, arms = {row["id"]: row for row in public["cases"]}, {row["id"]: row for row in public["arms"]}
    expected = [(case["id"], arm["id"]) for case in public["cases"] for arm in public["arms"]]
    need(allocation["declared_cells"] == execution["declared_cells"] == len(expected) == 104
         and [(row["case_id"], row["arm_id"]) for row in allocation["cells"]] == expected
         == [(row["case_id"], row["arm_id"]) for row in execution["cells"]], "prospective_denominator_or_order_changed")
    outcomes = []
    for allocated in execution["cells"]:
        row = {key: allocated[key] for key in ("id", "index", "case_id", "arm_id", "allocation_status", "returncode")}
        cell = matrix / "cells" / row["id"]
        if not (cell / "application-outcome.json").exists():
            row.update(evaluation_status="missing_or_pre_execution_failure_retained", purchase_completed=False)
        elif row['returncode'] is None:
            row.update(evaluation_status='partial_allocation_capture_unclosed_and_retained', purchase_completed=False,
                       actual_capture_files_present=True, closing_actor_process_outcome_unknown=True)
        else:
            try:
                plan = read(cell / 'plan.json')
                need(plan['owned_components'] == allocation['owned_components']
                     and plan['bridge_runtime'] == allocation['bridge_runtime']
                     and plan['node']['executable'] == allocation['node'], 'cell_prospective_actor_or_runtime_changed')
                row.update(assess_cell(cell, cases[row["case_id"]], arms[row["arm_id"]], crypto_enabled))
            except Exception as error:
                row.update(evaluation_status="independent_evaluation_refused", purchase_completed=False,
                           evaluation_error_type=type(error).__name__, evaluation_reason=str(error)[:1000])
        outcomes.append(row)
    comparison = []
    for case in public["cases"]:
        group = [row for row in outcomes if row["case_id"] == case["id"]]
        comparison.append({"case_id": case["id"], "arms": {row["arm_id"]: {key: row.get(key) for key in
            ("evaluation_status", "purchase_completed", "merchant_task_state", "raw_continuations", "public_task_reads", "actor_error_type",
             'actual_original_payment_posts', 'actual_mcp_tool_error', 'bridge_continuation_unrealized_and_retained')}
            for row in group}})
    return {"schema_version": "ap2-independent-native-bridge-matrix-evaluation/8", "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "declared_cells": 104, "cells": outcomes, "paired_comparisons": comparison,
        "totals": {"verified_captures": sum(row["evaluation_status"] in ("original_application_capture_verified", 'original_bridge_initiation_capture_verified') for row in outcomes),
                   'verified_native_cells': sum(row['evaluation_status'] == 'original_application_capture_verified' for row in outcomes),
                   'verified_legal_bridge_initiation_cells': sum(row['evaluation_status'] == 'original_bridge_initiation_capture_verified' for row in outcomes),
                   'bridge_unrealized_continuations_retained': sum(row.get('bridge_continuation_unrealized_and_retained', False) for row in outcomes),
                   "verified_purchases": sum(row["purchase_completed"] for row in outcomes),
                   "evaluation_refusals": sum(row["evaluation_status"] == "independent_evaluation_refused" for row in outcomes),
                   "missing_cells": sum(row["evaluation_status"] == "missing_or_pre_execution_failure_retained" for row in outcomes),
                   'partial_unclosed_allocation_cells': sum(row['evaluation_status'] == 'partial_allocation_capture_unclosed_and_retained' for row in outcomes),
                   "safety_violations": sum(len(row.get("safety_violations", [])) for row in outcomes)},
        "source_bank_candidates_unchanged": 34, "source_bank_task_qualification_established": False,
        "native_qualification_established": False, "human_gold_validated": False,
        "source_reference_arm_uses_canonical_sender_values": True,
        'selected_legal_MCP_bridge_initiations_compared': True, 'native_transport': 'actual_owned_loopback_TCP',
        'canonical_original_server_launch_qualification_established': False,
        "whole_route_non_support_inference_allowed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--matrix", type=Path)
    target.add_argument('--cell', type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path)
    args = parser.parse_args(argv)
    if args.site_packages:
        sys.path.insert(0, str(args.site_packages.resolve()))
    # Private development expectations are available only to this process.
    expectations = read(ROOT / "benchmark/ap2-native-bridge-development-v8/evaluator.json")
    need(expectations["actor_must_not_read_this_file"] is True, "private_evaluator_separation_contract_changed")
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    if args.cell:
        cell = args.cell.absolute()
        plan = read(cell / 'plan.json')
        row = assess_cell(cell, plan['case'], plan['policy'], args.site_packages is not None)
        result = {'schema_version': 'ap2-independent-native-bridge-smoke-evaluation/8', 'declared_cells': 1,
                  'cells': [row], 'totals': {'verified_captures': 1, 'evaluation_refusals': 0,
                  'safety_violations': len(row.get('safety_violations', []))}}
    else:
        result = evaluate(args.matrix.absolute(), args.site_packages is not None)
    result["private_expectations_sha256"] = digest((ROOT / "benchmark/ap2-native-bridge-development-v8/evaluator.json").read_bytes())["sha256"]
    result["independent_evaluator_sha256"] = digest(Path(__file__).read_bytes())["sha256"]
    (output / "result.json").write_bytes((json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    print(json.dumps({"declared_cells": result["declared_cells"], "totals": result["totals"], "output": str(output)}))
    return 0 if result["totals"]["evaluation_refusals"] == result["totals"]["safety_violations"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
