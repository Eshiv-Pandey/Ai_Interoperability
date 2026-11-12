"""Independent V5 archive/provider/runtime/lifecycle review; standard library only.

No captured source, application, SDK, model, solver or provider is executed.
Run/head and the reviewed frozen plan are explicit caller inputs. Every raw
archive member is checked before interpreting any retained observation.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CASE = 'ap2-native-shopper-provider-v5-correct-human'
LOOPBACK = {'127.0.0.1', 'localhost', '::1'}
DENIAL_SCHEMA = 'ap2-native-shopper-network-denial/5'
CLASSIFIER_SCHEMA = 'ap2-native-shopper-network-classification/5'
SEPARATION_SCHEMA = 'ap2-native-shopper-actor-separation/5'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate_JSON_key:' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non_JSON_constant:' + value)


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def same(first, second, message):
    need(canonical(first) == canonical(second), message)


def timestamp(value):
    result = datetime.fromisoformat(value)
    need(result.tzinfo is not None, 'timezone_required')
    return result


def literal_function(tree, name):
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    statements = [item for item in node.body if not (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant))]
    need(len(statements) == 1 and isinstance(statements[0], ast.Return), 'literal_public_facts_function_required')
    return ast.literal_eval(statements[0].value)


def source_constant(tree, name):
    node = next(node for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
    value = node.value
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'frozenset':
        need(len(value.args) == 1 and not value.keywords, 'literal_frozenset_constant_required')
        return frozenset(ast.literal_eval(value.args[0]))
    return ast.literal_eval(value)


def function_parts(event, key):
    content = event.get('content') or {}
    return [part[key] for part in content.get('parts', []) if type(part) is dict and part.get(key) is not None]


def usage_observation(body, http_status):
    if type(body) is not dict:
        return None
    usage = body.get('usageMetadata')
    value = usage.get('totalTokenCount') if type(usage) is dict else None
    return value if type(value) is int and value >= 0 and (value > 0 or http_status != 200) else None


def guard_review(separation, raw, guard_plan):
    need(separation.get('schema_version') == SEPARATION_SCHEMA
         and separation.get('network_classifier_schema') == CLASSIFIER_SCHEMA
         and separation.get('network_diagnostic_schema') == DENIAL_SCHEMA
         and separation.get('public_user_replies_use_visible_final_text_only') is True
         and separation.get('provider_credential_is_synthetic_downstream_only') is True,
         'actor_separation_schema_or_flags_differs')
    bounds = {'records': guard_plan['maximum_diagnostic_records'],
              'total_bytes': guard_plan['maximum_diagnostic_bytes'],
              'single_record_bytes': guard_plan['maximum_single_diagnostic_bytes']}
    same(separation['network_diagnostic_bounds'], bounds, 'actor_diagnostic_bounds_differs')
    need(separation['network_diagnostic_stream'] == 'actor-network-denials.jsonl', 'actor_diagnostic_stream_differs')
    lines = raw.splitlines(keepends=True)
    need(len(lines) <= bounds['records'] and len(raw) <= bounds['total_bytes']
         and all(len(line) <= bounds['single_record_bytes'] for line in lines), 'actor_diagnostic_limit_exceeded')
    counters = separation['denials']
    keys = {'private_reads', 'external_network', 'descendants', 'diagnostic_write_failures',
            'network_diagnostics_logged', 'network_diagnostics_dropped', 'network_diagnostic_bytes'}
    need(set(counters) == keys and all(type(value) is int and value >= 0 for value in counters.values()),
         'actor_denial_counters_invalid')
    need(counters['network_diagnostics_logged'] == len(lines) and counters['network_diagnostic_bytes'] == len(raw)
         and counters['external_network'] == counters['network_diagnostics_logged']
             + counters['network_diagnostics_dropped'] + counters['diagnostic_write_failures'],
         'actor_diagnostic_raw_counter_join_differs')
    records = []
    for line in lines:
        item = decode(line)
        need(type(item) is dict and set(item) == {'schema_version', 'time', 'event', 'classification',
             'sanitized_arguments', 'socket_object_or_send_payload_retained', 'external_host_or_unrestricted_argument_retained'},
             'actor_diagnostic_fields_differ')
        timestamp(item['time'])
        event = item['event']
        need(item['schema_version'] == DENIAL_SCHEMA
             and event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'}
             and item['socket_object_or_send_payload_retained'] is False
             and item['external_host_or_unrestricted_argument_retained'] is False, 'actor_diagnostic_schema_event_or_separation_differs')
        classification = item['classification']
        need(type(classification) is dict and classification.get('schema_version') == CLASSIFIER_SCHEMA
             and classification.get('allowed') is False
             and classification.get('normalized_host') in LOOPBACK | {None}
             and (classification.get('normalized_port') is None or type(classification.get('normalized_port')) is int
                  and 1 <= classification['normalized_port'] <= 65535), 'actor_diagnostic_classification_invalid')
        args = item['sanitized_arguments']
        need(type(args) is dict and set(args) <= {'audit_values_type', 'audit_values_count', 'address_type',
             'address_length', 'host', 'port', 'ipv6_flowinfo', 'ipv6_scope_id'}, 'actor_diagnostic_unsafe_argument_fields')
        for key in ('host', 'port', 'ipv6_flowinfo', 'ipv6_scope_id'):
            if key not in args:
                continue
            atom = args[key]
            need(type(atom) is dict and set(atom) <= {'type', 'length', 'safe_value', 'value_redacted'},
                 'actor_diagnostic_unsafe_scalar_fields')
            if 'safe_value' in atom:
                value = atom['safe_value']
                if key == 'host':
                    need(atom['type'] in {'str', 'bytes'} and value in LOOPBACK, 'unrestricted_host_in_diagnostic')
                elif key == 'port':
                    numeric = (int(value) if type(value) is str and 1 <= len(value) <= 5
                               and all(char in '0123456789' for char in value) else value)
                    need(type(numeric) is int and 1 <= numeric <= 65535
                         and atom['type'] in {'str', 'bytes', 'int'}, 'unrestricted_port_in_diagnostic')
                else:
                    need(type(value) is int and 0 <= value <= 65535, 'unrestricted_ipv6_field_in_diagnostic')
            else:
                need(atom.get('value_redacted') is True, 'unredacted_unknown_diagnostic_scalar')
        records.append(item)
    return {'counters': counters, 'diagnostic_records': records, 'diagnostic_bytes': len(raw),
            'diagnostic_coverage_complete': counters['network_diagnostics_dropped'] == counters['diagnostic_write_failures'] == 0,
            'allowed_socket_argument_values_retained': False,
            'historical_V4_rejected_argument_cause_inferred': False,
            'claim_limit': 'Only denied values have sanitized witnesses. No denied records does not identify the allowed host representation. Python audit controls are not an OS hostile-code sandbox.'}


def review(base, run_id, head_sha, frozen_plan, frozen_plan_sha256):
    evidence = {}
    def raw(name, optional=False):
        relative = PurePosixPath(name)
        need(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name, 'unsafe_retained_path')
        path = base / name
        if not path.exists() and optional:
            return None
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(base), 'regular_retained_file_required:' + name)
        value = path.read_bytes()
        evidence[name] = digest(value)
        return value
    def obj(name, optional=False):
        value = raw(name, optional=optional)
        return decode(value) if value is not None else None
    def rows(name, optional=False):
        value = raw(name, optional=optional)
        return [decode(line) for line in value.splitlines()] if value is not None else []

    frozen_raw = frozen_plan.read_bytes()
    need(digest(frozen_raw)['sha256'] == frozen_plan_sha256, 'explicit_frozen_plan_identity_differs')
    expected = decode(frozen_raw)
    retention, run = obj('retention.json'), obj('github-run.json')
    need(retention['run_id'] == run['id'] == run_id and retention['head_sha'] == run['head_sha'] == head_sha,
         'actual_run_head_binding_differs')
    need(run['run_attempt'] == 1 and run['status'] == 'completed', 'terminal_first_run_attempt_required')
    archive_raw = raw('artifact.zip')
    archive_identity = digest(archive_raw)
    need(archive_identity == {'bytes': retention['archive_bytes'], 'sha256': retention['archive_sha256']}, 'retention_archive_identity_differs')
    selected = [item for item in obj('github-artifacts.json')['artifacts'] if item['id'] == retention['artifact_id']]
    need(len(selected) == 1, 'one_API_artifact_required')
    artifact = selected[0]
    need(artifact['digest'] == retention['api_digest'] == 'sha256:' + archive_identity['sha256']
         and artifact['size_in_bytes'] == archive_identity['bytes']
         and artifact['workflow_run']['id'] == run_id and artifact['workflow_run']['head_sha'] == head_sha
         and artifact['name'] == retention['artifact_name'] == 'ap2-native-shopper-provider-development-v5', 'API_artifact_binding_differs')
    manifest = obj('extracted-manifest.json')['files']
    names = {item['path'] for item in manifest}
    need(len(names) == len(manifest) == retention['extracted_files'], 'unique_manifest_count_differs')
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        need({item.filename for item in members} == names and len(members) == len(names), 'ZIP_manifest_membership_differs')
        for item in manifest:
            value = archive.read(item['path'])
            need(digest(value) == {'bytes': item['bytes'], 'sha256': item['sha256']}
                 and raw('extracted/' + item['path']) == value, 'ZIP_extracted_manifest_identity_differs:' + item['path'])
    actual_files = {path.relative_to(base / 'extracted').as_posix() for path in (base / 'extracted').rglob('*') if path.is_file()}
    same(sorted(actual_files), sorted(names), 'unmanifested_extracted_files_present')
    retention_plan = obj('plan.json')
    need(retention_plan['run_id'] == run_id and retention_plan['artifact_name'] == retention['artifact_name']
         and retention_plan['application_rerun'] is False, 'retention_plan_scope_differs')
    plan_raw = raw('extracted/plan/plan.json')
    plan = decode(plan_raw)
    same({k: v for k, v in plan.items() if k != 'prepared_at'},
         {k: v for k, v in expected.items() if k != 'prepared_at'}, 'reviewed_frozen_plan_fields_differs')
    need(plan['schema_version'] == 'ap2-native-shopper-provider-plan/5' and type(plan['allocated_task_count']) is int
         and plan['allocated_task_count'] == 1 and plan['public_human_facts']['case_id'] == CASE, 'V5_single_case_plan_required')
    opening = obj('extracted/execution/opening.json')
    need({k: opening['plan'][k] for k in ('bytes', 'sha256')} == digest(plan_raw), 'opening_plan_identity_differs')
    for name, identity in plan['owned_sources'].items():
        same(digest(raw('extracted/plan/owned-source/' + name)), identity, 'owned_source_snapshot_differs:' + name)
    prefix = 'extracted/execution/cases/' + CASE + '/'
    shopper = prefix + 'shopper/'
    worker_name = plan['selected_worker_relative_path']
    worker_raw = raw('extracted/plan/owned-source/' + worker_name)
    worker_tree = ast.parse(worker_raw)
    facts = obj(prefix + 'public-human-facts.json')
    same(literal_function(worker_tree, 'public_facts'), facts, 'worker_and_executed_public_facts_differs')
    same(facts, plan['public_human_facts'], 'plan_and_executed_public_facts_differs')
    preflight = obj('extracted/execution/worker-public-facts-preflight.json')
    need(preflight['selected_worker'] == worker_name and preflight['selected_worker_source_identity'] == digest(worker_raw)
         and preflight['exact_public_field_agreement'] is True and preflight['before_provider_smoke'] is True, 'worker_public_facts_preflight_differs')
    old_raw = raw('extracted/plan/owned-source/scripts/ap2_native_shopper_provider_worker_v2.py')
    old_tree = ast.parse(old_raw)
    adjusted_tree = ast.parse(worker_raw.replace(b'ap2-native-shopper-provider-worker/3', b'ap2-native-shopper-provider-worker/2'))
    for name in ('public_price_check', 'public_reply', 'visible_final_text', 'application'):
        find = lambda tree: next(item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name)
        need(ast.dump(find(old_tree), include_attributes=False) == ast.dump(find(adjusted_tree), include_attributes=False), 'original_actor_or_application_function_changed:' + name)
    guard_path = plan['actor_network_guard']['guard_relative_path']
    guard_tree = ast.parse(raw('extracted/plan/owned-source/' + guard_path))
    for name, value in [('CLASSIFIER_SCHEMA', CLASSIFIER_SCHEMA), ('DIAGNOSTIC_SCHEMA', DENIAL_SCHEMA),
                        ('SEPARATION_SCHEMA', SEPARATION_SCHEMA), ('MAX_DIAGNOSTICS', 160),
                        ('MAX_DIAGNOSTIC_BYTES', 262144), ('MAX_SINGLE_DIAGNOSTIC_BYTES', 4096)]:
        need(source_constant(guard_tree, name) == value, 'guard_literal_policy_differs:' + name)
    need(source_constant(guard_tree, 'NATIVE_PORTS') == {8001, 8002, 8003}
         and source_constant(guard_tree, 'LOOPBACK_NAMES') == LOOPBACK, 'guard_endpoint_policy_differs')
    result = obj('extracted/execution/result.json')
    need(result['schema_version'] == 'ap2-native-shopper-provider-result/5' and result['allocated_task_count'] == 1
         and len(result['cases']) == 1 and result['cases'][0]['case_id'] == CASE, 'V5_result_case_denominator_differs')
    runtime_raw = raw('extracted/execution/portable-runtime.json')
    runtime = decode(runtime_raw)
    need(result['portable_runtime_sha256'] == digest(runtime_raw)['sha256'], 'runtime_result_binding_differs')
    same(runtime['required_original_versions'], plan['versions'], 'runtime_plan_version_requirement_differs')
    need(all(runtime['distributions'].get(name) == version for name, version in plan['versions'].items()), 'required_distribution_version_differs')
    for key in ('source_stage_sha256', 'original_windows_environment_sha256'):
        same(runtime[key], plan[key], 'runtime_original_reference_differs:' + key)
    pip_raw = raw('extracted/pip-install-report.json')
    need({k: runtime['pip_report'][k] for k in ('bytes', 'sha256')} == digest(pip_raw), 'pip_report_runtime_identity_differs')
    pip = decode(pip_raw)
    normalize = lambda name: re.sub('[-_.]+', '-', name).lower()
    installed = {normalize(row['metadata']['name']): row['metadata']['version'] for row in pip['install']}
    need(all(runtime['distributions'].get(name) == version for name, version in installed.items()), 'pip_distribution_version_differs')
    binding, launch = obj(shopper + 'original-root-binding.json'), obj(prefix + 'native-launch.json')
    root_relative = 'code/samples/python/src/roles/shopping_agent/agent.py'
    need(binding['original_root_source_sha256'] == plan['sources'][root_relative]['sha256']
         and binding['original_root_import_file'] == launch['original_source_copy_roots']['ap2'] + '/' + root_relative,
         'original_root_source_or_private_import_differs')
    need(binding['root_model'] == plan['model'] and binding['official_ADK_runner'] is True
         and binding['genai_Client_replaced'] is False and binding['deterministic_BaseLlm_replacement'] is False,
         'original_root_model_or_runtime_binding_differs')
    ledger = rows('extracted/execution/provider/ledger.jsonl')
    starts, finishes = {}, {}
    for offset, item in enumerate(ledger):
        allocation = item['allocation']
        need(type(allocation) is int and allocation >= 0 and item['phase'] in {'started', 'finished'}, 'provider_ledger_phase_or_ID_invalid')
        target = starts if item['phase'] == 'started' else finishes
        need(allocation not in target and (item['phase'] == 'started' or allocation in starts), 'provider_duplicate_or_reordered_allocation')
        target[allocation] = item
    need(set(starts) == set(range(len(starts))) and set(finishes) <= set(starts), 'provider_allocation_sequence_differs')
    observations, provider_calls, known, request_bytes, models = [], [], 0, 0, Counter()
    for number, start in sorted(starts.items()):
        request_raw = raw(f'extracted/execution/provider/{number:03d}.request.json')
        need(digest(request_raw) == start['request'] and start['upstream_call_consumed'] is True, 'provider_opening_request_binding_differs')
        request = decode(request_raw)
        need(type(request) is dict and 'contents' in request, 'provider_request_shape_differs')
        request_bytes += len(request_raw)
        finish = finishes.get(number)
        if finish is None:
            observations.append({'allocation': number, 'http_status': None, 'request_bytes': len(request_raw), 'known_reported_tokens': None, 'unknown_usage_reason': 'unclosed_allocation'})
            continue
        response_raw = raw(f'extracted/execution/provider/{number:03d}.response.json')
        need(digest(response_raw) == finish['response'] and finish['upstream_call_consumed'] is True
             and timestamp(finish['time']) >= timestamp(start['time']), 'provider_terminal_payload_or_order_differs')
        try:
            body = decode(response_raw)
        except (ValueError, UnicodeError):
            body = None
        status = finish['http_status']
        need(type(status) is int and 100 <= status <= 599, 'provider_HTTP_status_invalid')
        usage = usage_observation(body, status)
        if usage is not None:
            known += usage
        need(finish['observed_cumulative_usage_tokens'] == known, 'provider_partial_known_usage_cumulative_differs')
        if type(body) is dict:
            if body.get('modelVersion'):
                models[body['modelVersion']] += 1
            for candidate in body.get('candidates', []):
                for call in function_parts(candidate, 'functionCall'):
                    provider_calls.append({'allocation': number, 'call': call, 'model_version': body.get('modelVersion'), 'reported_tokens': usage})
        observations.append({'allocation': number, 'http_status': status, 'request_bytes': len(request_raw),
                             'known_reported_tokens': usage, 'unknown_usage_reason': None if usage is not None else 'missing_or_invalid_usage',
                             'model_version': body.get('modelVersion') if type(body) is dict else None,
                             'upstream_error': body.get('error') if type(body) is dict else None})
    unclosed = sorted(set(starts) - set(finishes))
    closed = [item for item in observations if item['http_status'] is not None]
    unknown = [item for item in closed if item['known_reported_tokens'] is None]
    measured = {'upstream_allocations': len(starts), 'terminal_responses': len(finishes), 'known_reported_tokens': known,
                'successful_responses_missing_or_invalid_usage': sum(item['http_status'] == 200 for item in unknown),
                'failed_responses_missing_or_invalid_usage': sum(item['http_status'] != 200 for item in unknown),
                'responses_missing_or_invalid_usage': len(unknown), 'unclosed_allocation_ids': unclosed,
                'allocations_with_unmeasured_usage': len(unknown) + len(unclosed), 'fully_measured': not unknown and not unclosed}
    summary = result['provider']
    for key, value in measured.items():
        same(summary['all_response_usage'][key], value, 'provider_all_outcome_summary_differs:' + key)
    need(summary['all_response_usage']['unknown_usage_is_zero'] is False and summary['upstream_allocations'] == len(starts)
         and summary['cumulative_request_bytes'] == request_bytes and summary['observed_usage_tokens'] == known
         and summary['successful_provider_responses'] == sum(item['http_status'] == 200 for item in closed), 'provider_closing_summary_differs')
    limits = plan['limits']
    need(len(starts) <= limits['upstream_calls_including_smoke'] and request_bytes <= limits['maximum_total_request_bytes'], 'provider_call_or_byte_limit_exceeded')
    drain = obj('extracted/execution/provider-drain.json')
    same(drain, result['provider_drain'], 'provider_standalone_parent_drain_differs')
    need(drain['schema_version'] == 'ap2-provider-drain/2' and drain['admission_closed'] is True
         and drain['capture_frozen'] is True and drain['late_sender_outcomes_retained'] is False
         and drain['unfinished_allocations_require_unknown_usage'] is True, 'provider_drain_scope_differs')
    for key, value in [('allocated_upstream_calls_at_capture_freeze', len(starts)), ('request_bytes_at_capture_freeze', request_bytes),
                       ('unclosed_allocation_ids', unclosed), ('allocations_with_unmeasured_usage', len(unknown) + len(unclosed))]:
        same(drain[key], value, 'provider_drain_raw_census_differs:' + key)
    need(type(drain['active_handlers_at_capture_freeze']) is int and drain['active_handlers_at_capture_freeze'] >= len(unclosed)
         and drain['all_handlers_completed'] is (drain['active_handlers_at_capture_freeze'] == 0)
         and all(timestamp(item['time']) <= timestamp(drain['time']) for item in ledger), 'provider_drain_handler_or_timestamp_differs')
    case = result['cases'][0]
    cleanup = case['process_cleanup']
    need(len(cleanup) == 4 and len({item['pid'] for item in cleanup}) == 4
         and all(type(item['pid']) is int and item['pid'] > 0 and item['reaped'] is True
                 and item['cleanup_error_type'] is None for item in cleanup), 'four_unique_children_not_cleanly_reaped')
    services = []
    for service in ('merchant', 'credentials', 'processor'):
        text = raw(prefix + service + '.stdout.log').decode('utf-8')
        started = [int(value) for value in re.findall(r'Started server process \[(\d+)\]', text)]
        stopped = [int(value) for value in re.findall(r'Finished server process \[(\d+)\]', text)]
        need(len(started) == 1 and started == stopped and started[0] in {item['pid'] for item in cleanup}, 'native_service_start_finish_reap_PID_differs')
        need(digest(raw(prefix + service + '.agent-card.json')) == launch['public_cards'][service], 'native_card_digest_differs')
        services.append({'service': service, 'started_PID': started[0], 'finished_PID': stopped[0],
                         'card_GET_200_count': len(re.findall(r'GET .*agent-card\.json HTTP/1\.1" 200 OK', text)),
                         'POST_count': len(re.findall(r'"POST ', text))})
    worker = obj(shopper + 'worker-result.json')
    need(worker['schema_version'] == 'ap2-native-shopper-provider-worker/3' and worker['case_id'] == CASE
         and type(worker['original_remote_http_clients_closed']) is list and len(worker['original_remote_http_clients_closed']) == 2
         and all(item is True for item in worker['original_remote_http_clients_closed']), 'worker_schema_or_remote_client_cleanup_differs')
    guard = guard_review(obj(shopper + 'actor-input-separation.json'), raw(shopper + 'actor-network-denials.jsonl'), plan['actor_network_guard'])
    events = rows(shopper + 'ADK-events.jsonl')
    need(type(worker['ADK_event_count']) is int and worker['ADK_event_count'] == len(events), 'worker_raw_ADK_count_differs')
    event_ids = [item['event']['id'] for item in events]
    need(all(type(value) is str and value for value in event_ids) and len(event_ids) == len(set(event_ids)), 'ADK_event_IDs_invalid_or_reused')
    calls, responses, pending, joins = [], [], {}, []
    for offset, item in enumerate(events):
        event = item['event']
        for call in function_parts(event, 'functionCall'):
            need(type(call.get('id')) is str and call['id'] not in pending, 'ADK_call_ID_invalid_or_pending_duplicate')
            record = {'event_index': offset, 'author': event['author'], **call}
            pending[call['id']] = record
            calls.append(record)
            matches = [row for row in provider_calls if canonical(row['call']) == canonical(call)]
            need(len(matches) == 1, 'ADK_function_call_provider_match_not_unique')
            match = matches[0]
            need(event.get('modelVersion') == match['model_version']
                 and (event.get('usageMetadata') or {}).get('totalTokenCount') == match['reported_tokens'], 'ADK_provider_model_or_usage_differs')
            joins.append({'call_id': call['id'], 'name': call['name'], 'allocation': match['allocation']})
        for response in function_parts(event, 'functionResponse'):
            need(response.get('id') in pending and pending[response['id']]['name'] == response.get('name'), 'ADK_function_response_unmatched_or_reordered')
            del pending[response['id']]
            responses.append({'event_index': offset, 'author': event['author'], **response})
    conversation, decisions = rows(shopper + 'public-conversation.jsonl'), rows(shopper + 'public-actor-decisions.jsonl')
    users = [item for item in conversation if item['role'] == 'user']
    need(users and users[0]['turn'] == 0 and users[0]['text'] == facts['initial_request'], 'initial_public_user_fact_differs')
    visible = []
    for item in events:
        content = item['event'].get('content') or {}
        texts = [part['text'] for part in content.get('parts', []) if part.get('text') and not part.get('thought')]
        if content.get('role') == 'model' and texts:
            visible.append({'turn': item['turn'], 'author': item['event']['author'], 'text': '\n'.join(texts)})
    same(visible, [{k: item[k] for k in ('turn', 'author', 'text')} for item in conversation if item['role'] == 'model'], 'visible_public_text_and_ADK_differs')
    for decision in decisions:
        texts = [item['text'] for item in visible if item['turn'] == decision['turn']]
        prompt = texts[-1] if texts else ''
        need(decision['visible_prompt_sha256'] == hashlib.sha256(prompt.encode('utf-8')).hexdigest()
             and decision['session_or_tool_state_used'] is False, 'public_actor_prompt_or_separation_differs')
    snapshots = []
    for name in sorted(names):
        if re.fullmatch(re.escape(prefix.removeprefix('extracted/')) + r'shopper/turn-\d+-session\.json', name):
            snapshot = obj('extracted/' + name)
            turn = int(name.split('turn-')[-1].split('-')[0])
            same([item for item in snapshot['events'] if item.get('author') != 'user'],
                 [item['event'] for item in events if item['turn'] <= turn], 'session_snapshot_raw_ADK_events_differs')
            need(snapshot['id'] == binding['session_id'], 'session_snapshot_identity_differs')
            snapshots.append({'member': name, 'event_count': len(snapshot['events']),
                              'state_keys': sorted(snapshot.get('state', {})),
                              'payment_receipt_present': (snapshot.get('state') or {}).get('payment_receipt') is not None})
    smoke = obj('extracted/execution/provider-access-smoke.json')
    need(smoke['forced_tool_observed'] is True and 0 in starts, 'access_smoke_or_allocation_missing')
    refusals = rows('extracted/execution/provider/local-refusals.jsonl', optional=True)
    start_times = [timestamp(item['time']) for _, item in sorted(starts.items())]
    gaps = [(later - earlier).total_seconds() for earlier, later in zip(start_times, start_times[1:])]
    return {'schema_version': 'ap2-native-shopper-v5-provider-lifecycle-independent-review/1',
            'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'retained_provider_runtime_lifecycle_consistent_at_stated_scope',
            'run_id': run_id, 'head_sha': head_sha, 'archive_identity': archive_identity,
            'API_digest_matches_reconstructed_archive': True, 'archive_and_extracted_files_verified': len(manifest),
            'frozen_plan_identity': digest(frozen_raw),
            'provider': {**measured, 'access_smoke_allocation_included': 0, 'non_smoke_generation_allocations': len(starts) - 1,
                         'request_bytes': request_bytes, 'HTTP_status_counts': dict(Counter(item['http_status'] for item in closed)),
                         'observations': observations, 'returned_model_version_counts': dict(models),
                         'local_refusals': refusals, 'unknown_usage_is_zero': False,
                         'minimum_recorded_allocation_timestamp_gap_seconds': min(gaps) if gaps else None,
                         'actual_network_send_timestamps_retained': False, 'drain': drain},
            'runtime': {'python_version': runtime['python_version'], 'actual_distribution_count': len(runtime['distributions']),
                        'required_versions_checked': len(plan['versions']), 'pip_install_count': len(pip['install']),
                        'runtime_inventory_file_count': len(runtime['files']), 'actual_required_versions_match': True,
                        'hosted_runtime_physical_files_independently_rehashed': False},
            'source_binding': {'owned_source_snapshots_checked': len(plan['owned_sources']),
                        'selected_worker': worker_name, 'selected_worker_identity': digest(worker_raw),
                        'exact_typed_public_facts_match': True, 'original_actor_and_application_functions_preserved': True,
                        'original_root_matches_private_copy_path_and_plan_hash': True,
                        'full_original_or_installed_source_physical_bytes_independently_rehashed': False},
            'lifecycle': {'recorded_children': cleanup, 'all_recorded_children_reaped': True,
                         'native_services': services, 'remote_HTTP_clients_closed': [True, True],
                         'explicit_official_Runner_close_recorded': False,
                         'native_port_preflight': rows(prefix + 'native-port-preflight.jsonl'),
                         'native_listener_ownership_scope': 'Bound declared PID ownership check plus card/stdout/reap joins; no retained raw /proc FD/socket-inode witness.'},
            'owned_actor_guard': guard,
            'ADK_observations': {'events': len(events), 'function_call_count': len(calls), 'terminal_response_count': len(responses),
                         'business_call_count': sum(item['name'] != 'transfer_to_agent' for item in calls),
                         'business_terminal_count': sum(item['name'] != 'transfer_to_agent' for item in responses),
                         'unmatched_calls': list(pending.values()), 'provider_call_joins': joins,
                         'public_user_turns': len(users), 'visible_model_messages': len(visible),
                         'actor_decisions': decisions, 'session_snapshots': snapshots,
                         'worker_status': worker['status']},
            'material_consistency_questions': [], 'whole_task_grade': None, 'human_gold_qualified': False,
            'workflow_success_implies_purchase': False, 'V4_denial_cause_inferred': False,
            'original_application_SDK_provider_execution_by_reviewer': 0, 'Git_actions_by_reviewer': 0,
            'evidence_identities': evidence,
            'reviewer_source': {'path': Path(__file__).relative_to(ROOT).as_posix(), **digest(Path(__file__).read_bytes())},
            'scope_limits': ['One adaptive development allocation; V4 and earlier failures keep separate denominators.',
                             'Recorded provider usage and source/event consistency do not prove human task success or settlement.',
                             'Hosted physical runtime and original run.sh provisioning remain unqualified.',
                             'No denied V5 socket records identify the allowed representation or historical V4 cause.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--head-sha', required=True)
    parser.add_argument('--frozen-plan', type=Path, required=True)
    parser.add_argument('--frozen-plan-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base, output = args.base.resolve(), args.output.resolve()
    need(base.is_relative_to(ROOT / 'runs') and output.is_relative_to(ROOT / 'runs') and not output.exists(), 'workspace_retention_and_fresh_review_output_required')
    need(re.fullmatch('[0-9a-f]{40}', args.head_sha) is not None, 'explicit_full_head_SHA_required')
    report = review(base, args.run_id, args.head_sha, args.frozen_plan.resolve(), args.frozen_plan_sha256)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'output': output.relative_to(ROOT).as_posix(),
                      'provider_allocations': report['provider']['upstream_allocations'],
                      'known_tokens': report['provider']['known_reported_tokens'],
                      'unknown_allocations': report['provider']['allocations_with_unmeasured_usage'],
                      'denials': report['owned_actor_guard']['counters']['external_network'],
                      'source_identity': report['reviewer_source']}))


if __name__ == '__main__':
    main()
