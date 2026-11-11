"""Prospective retained-byte V5 analysis; no application or provider execution.

The frozen plan, run and head are caller inputs. Unmatched tool calls are
reported as incomplete outcomes rather than discarded or treated as receipts.
Prior analyzers and allocations remain unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CASE = 'ap2-native-shopper-provider-v5-correct-human'
DEPENDENCIES = {
    'scripts/analyze_ap2_native_shopper_provider_v1.py': 'fd07c3609400f951d8500ce97f1cc655fc4ed654b7836597c30d26262ef930ab',
    'scripts/analyze_ap2_native_shopper_provider_v2.py': 'c1211733a21dd8bc8ea1aee5135b471c43f53fe7459eb998daf678160375e07d',
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def load(name):
    path = ROOT / name
    need(hashlib.sha256(path.read_bytes()).hexdigest() == DEPENDENCIES[name], 'immutable_analysis_dependency_differs')
    spec = importlib.util.spec_from_file_location('_V5_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V1 = load('scripts/analyze_ap2_native_shopper_provider_v1.py')
V2 = load('scripts/analyze_ap2_native_shopper_provider_v2.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def check_plan(read, expected):
    plan = read.json('plan/plan.json')
    need(plan.get('schema_version') == 'ap2-native-shopper-provider-plan/5', 'explicit_V5_plan_required')
    need(set(plan) == set(expected) and all(canonical(plan[key]) == canonical(value)
         for key, value in expected.items() if key != 'prepared_at'), 'reviewed_frozen_plan_differs')
    need(type(plan.get('allocated_task_count')) is int and plan['allocated_task_count'] == 1
         and plan['public_human_facts']['case_id'] == CASE, 'one_declared_V5_case_required')
    for name, expected_identity in plan['owned_sources'].items():
        need(type(expected_identity) is dict and set(expected_identity) == {'bytes', 'sha256'}
             and type(expected_identity['bytes']) is int and expected_identity['bytes'] >= 0
             and type(expected_identity['sha256']) is str
             and re.fullmatch(r'[0-9a-f]{64}', expected_identity['sha256']) is not None,
             'frozen_owned_source_identity_schema_differs:' + name)
        need(V1.digest(read.raw('plan/owned-source/' + name)) == expected_identity,
             'frozen_owned_source_differs:' + name)
    return plan


def call_pairs(events):
    calls, responses, questions = [], [], []
    pending, ids = {}, set()
    for index, row in enumerate(events):
        for part in V1.parts(row['event']):
            call = V1.function(part, 'function_call')
            response = V1.function(part, 'function_response')
            if call:
                record = {'event_index': index, 'author': row['event'].get('author'), **call}
                identity = call.get('id')
                if not isinstance(identity, str) or not identity or identity in ids:
                    questions.append('missing_or_reused_function_call_ID')
                else:
                    ids.add(identity)
                    pending[identity] = record
                calls.append(record)
            if response:
                record = {'event_index': index, 'author': row['event'].get('author'), **response}
                previous = pending.get(response.get('id'))
                if previous is None or previous['name'] != response.get('name'):
                    questions.append('unmatched_reordered_or_duplicate_function_response')
                else:
                    del pending[response['id']]
                responses.append(record)
    return {'calls': calls, 'responses': responses, 'unmatched_calls': list(pending.values()),
            'business_call_attempts': sum(row['name'] != 'transfer_to_agent' for row in calls),
            'business_terminal_responses': sum(row['name'] != 'transfer_to_agent' for row in responses),
            'consistency_questions': questions}


def provider_call_join(read, events):
    candidates = []
    for name in sorted(read.manifest):
        if not re.fullmatch(r'execution/provider/\d+\.response\.json', name):
            continue
        raw = read.raw(name)
        try:
            value = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        for candidate in value.get('candidates', []):
            for part in candidate.get('content', {}).get('parts', []):
                if call := V1.function(part, 'function_call'):
                    candidates.append((name, call, value))
    joined, questions = [], []
    for index, row in enumerate(events):
        event = row['event']
        for part in V1.parts(event):
            if not (call := V1.function(part, 'function_call')):
                continue
            matches = [(name, value) for name, other, value in candidates if canonical(call) == canonical(other)]
            if len(matches) != 1:
                questions.append('ADK_call_lacks_unique_exact_provider_match')
                continue
            name, value = matches[0]
            usage = event.get('usageMetadata', event.get('usage_metadata', {}))
            if event.get('modelVersion', event.get('model_version')) != value.get('modelVersion') or (
                    usage.get('totalTokenCount', usage.get('total_token_count')) != value.get('usageMetadata', {}).get('totalTokenCount')):
                questions.append('ADK_provider_model_version_or_usage_differs')
            joined.append({'event_index': index, 'call_id': call.get('id'), 'name': call.get('name'), 'provider_member': name})
    return {'matches': joined, 'consistency_questions': questions}


def actor_separation_analysis(read, shopper, plan, separation):
    raw = read.raw(shopper + 'actor-network-denials.jsonl', optional=True)
    if separation is None:
        return {'record_present': False, 'diagnostic_records': [], 'diagnostic_bytes': len(raw or b''),
                'consistency_questions': ['actor_separation_schema_or_flags_differs'] if raw is not None else []}
    questions = []
    guard = plan['actor_network_guard']
    expected_bounds = {'records': guard['maximum_diagnostic_records'],
                       'total_bytes': guard['maximum_diagnostic_bytes'],
                       'single_record_bytes': guard['maximum_single_diagnostic_bytes']}
    if (separation.get('schema_version') != guard['separation_schema']
            or separation.get('network_classifier_schema') != guard['classifier_schema']
            or separation.get('network_diagnostic_schema') != guard['denial_schema']
            or separation.get('public_user_replies_use_visible_final_text_only') is not True
            or separation.get('provider_credential_is_synthetic_downstream_only') is not True):
        questions.append('actor_separation_schema_or_flags_differs')
    if (separation.get('network_diagnostic_stream') != 'actor-network-denials.jsonl'
            or separation.get('network_diagnostic_bounds') != expected_bounds or raw is None):
        questions.append('actor_network_diagnostic_membership_or_bounds_differs')
    lines = (raw or b'').splitlines(keepends=True)
    records = []
    for line in lines:
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError):
            questions.append('actor_network_diagnostic_counter_or_record_differs')
            continue
        records.append(record)
        if (not isinstance(record, dict) or record.get('schema_version') != guard['denial_schema']
                or record.get('event') not in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'}
                or not isinstance(record.get('classification'), dict)
                or record['classification'].get('schema_version') != guard['classifier_schema']
                or record['classification'].get('allowed') is not False
                or record.get('socket_object_or_send_payload_retained') is not False
                or record.get('external_host_or_unrestricted_argument_retained') is not False):
            questions.append('actor_network_diagnostic_counter_or_record_differs')
    if (len(raw or b'') > expected_bounds['total_bytes'] or len(lines) > expected_bounds['records']
            or any(len(line) > expected_bounds['single_record_bytes'] for line in lines)):
        questions.append('actor_network_diagnostic_membership_or_bounds_differs')
    counters = separation.get('denials') or {}
    required = ('private_reads', 'external_network', 'descendants', 'network_diagnostics_logged',
                'network_diagnostics_dropped', 'diagnostic_write_failures', 'network_diagnostic_bytes')
    if (any(type(counters.get(name)) is not int or counters[name] < 0 for name in required)
            or counters.get('network_diagnostics_logged') != len(lines)
            or counters.get('network_diagnostic_bytes') != len(raw or b'')):
        questions.append('actor_network_diagnostic_counter_or_record_differs')
    elif counters['external_network'] != (counters['network_diagnostics_logged']
            + counters['network_diagnostics_dropped'] + counters['diagnostic_write_failures']):
        questions.append('actor_network_diagnostic_counter_or_record_differs')
    return {'record_present': True, 'diagnostic_records': records, 'diagnostic_bytes': len(raw or b''),
            'counters': counters,
            'all_denied_network_arguments_retained': (not questions
                and counters.get('network_diagnostics_dropped') == 0
                and counters.get('diagnostic_write_failures') == 0),
            'unrecorded_denial_count': (sum(counters[name] for name in
                ('network_diagnostics_dropped', 'diagnostic_write_failures'))
                if all(type(counters.get(name)) is int and counters[name] >= 0 for name in
                ('network_diagnostics_dropped', 'diagnostic_write_failures')) else None),
            'historical_V4_denial_cause_inferred': False,
            'consistency_questions': list(dict.fromkeys(questions))}


def analyze(read, expected):
    plan = check_plan(read, expected)
    result = read.json('execution/result.json')
    need(result.get('schema_version') == 'ap2-native-shopper-provider-result/5'
         and type(result.get('allocated_task_count')) is int and result['allocated_task_count'] == 1
         and len(result.get('cases', [])) == 1 and result['cases'][0].get('case_id') == CASE,
         'result_schema_case_or_denominator_differs')
    case = result['cases'][0]
    root = 'execution/cases/' + CASE + '/'
    shopper = root + 'shopper/'
    events = read.rows(shopper + 'ADK-events.jsonl')
    conversation = read.rows(shopper + 'public-conversation.jsonl')
    decisions = read.rows(shopper + 'public-actor-decisions.jsonl')
    snapshots = [(name, read.json(name)) for name in sorted(read.manifest)
                 if re.fullmatch(re.escape(shopper) + r'turn-\d+-session\.json', name)]
    public = V1.public_analysis(events, conversation, decisions, snapshots, plan['public_human_facts'])
    # A model call followed by an exception is a retained outcome, not by itself
    # an integrity error. Reordered/duplicate responses remain integrity errors.
    public['incomplete_tool_observations'] = [item for item in public['consistency_questions']
                                            if item == 'raw_ADK_function_call_response_census_differs']
    public['consistency_questions'] = [item for item in public['consistency_questions']
                                       if item != 'raw_ADK_function_call_response_census_differs']
    pairs = call_pairs(events)
    joins = provider_call_join(read, events)
    provider = V1.provider_analysis(read, result)
    runtime = V1.runtime_analysis(read, plan, result)
    drain = V2.drain_analysis(read, plan, result, provider)
    binding = read.json(shopper + 'original-root-binding.json', optional=True)
    worker = read.json(shopper + 'worker-result.json', optional=True)
    separation = read.json(shopper + 'actor-input-separation.json', optional=True)
    facts = read.json(root + 'public-human-facts.json', optional=True)
    actor = actor_separation_analysis(read, shopper, plan, separation)
    questions = [question for area in (public, pairs, joins, provider, runtime, drain, actor)
                 for question in area['consistency_questions']]
    preflight = result.get('status') == 'runtime_preflight_failed_before_provider_or_application_calls'
    if preflight and (events or case.get('status') != 'unexecuted' or result.get('unexecuted_count') != 1
            or binding is not None or worker is not None or separation is not None or facts is not None
            or conversation or decisions or snapshots):
        questions.append('runtime_preflight_failure_has_application_observations')
    if not preflight and not runtime['record_present']:
        questions.append('post_preflight_runtime_manifest_absent')
    if facts is not None and canonical(facts) != canonical(plan['public_human_facts']):
        questions.append('executed_public_facts_differ_from_plan')
    if worker is not None and (worker.get('schema_version') != 'ap2-native-shopper-provider-worker/3'
            or worker.get('case_id') != CASE or type(worker.get('ADK_event_count')) is not int
            or worker.get('ADK_event_count') != len(events)):
        questions.append('worker_schema_case_or_ADK_count_differs')
    if worker is not None:
        closed_clients = worker.get('original_remote_http_clients_closed')
        if type(closed_clients) is not list or len(closed_clients) != 2 or any(value is not True for value in closed_clients):
            questions.append('worker_remote_clients_not_closed')
    if events and (binding is None or worker is None or facts is None or separation is None):
        questions.append('ADK_execution_binding_or_worker_or_separation_absent')
    if binding is not None:
        expected_root = plan['sources']['code/samples/python/src/roles/shopping_agent/agent.py']['sha256']
        if (binding.get('original_root_source_sha256') != expected_root or binding.get('root_model') != V1.MODEL
                or binding.get('official_ADK_runner') is not True or binding.get('genai_Client_replaced') is not False
                or binding.get('deterministic_BaseLlm_replacement') is not False):
            questions.append('original_root_model_or_runtime_binding_differs')
    if provider['upstream_allocations'] > plan['limits']['upstream_calls_including_smoke'] or (
            provider['recorded_cumulative_request_bytes'] > plan['limits']['maximum_total_request_bytes']):
        questions.append('provider_call_or_byte_bounds_exceeded')
    if provider['recorded_cumulative_request_bytes'] != result.get('provider', {}).get('cumulative_request_bytes', 0):
        questions.append('provider_request_byte_summary_differs')
    children = case.get('process_cleanup', [])
    if any(row.get('reaped') is not True for row in children):
        questions.append('recorded_child_not_reaped')
    if any(type(row.get('pid')) is not int or row['pid'] <= 0 for row in children) or (
            len(children) != len({row.get('pid') for row in children})):
        questions.append('recorded_child_PID_missing_invalid_or_reused')
    event_ids = [row['event'].get('id') for row in events]
    if any(type(value) is not str or not value for value in event_ids) or len(event_ids) != len(set(event_ids)):
        questions.append('raw_ADK_event_ID_missing_invalid_or_reused')
    for snapshot_name, snapshot in snapshots:
        snapshot_turn = int(snapshot_name.split('turn-')[-1].split('-')[0])
        captured = [row['event'] for row in events if row.get('turn', 0) <= snapshot_turn]
        if snapshot.get('id') != (binding or {}).get('session_id'):
            questions.append('snapshot_session_identity_differs')
        model_events = [event for event in snapshot.get('events', []) if event.get('author') != 'user']
        if canonical(model_events) != canonical(captured):
            questions.append('snapshot_and_raw_ADK_events_differ')
    return {'schema_version': 'ap2-native-shopper-provider-offline-analysis/5',
            'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
            'run_id': read.receipt['run_id'], 'head_sha': read.receipt['head_sha'],
            'archive_sha256': read.receipt['archive_sha256'], 'archive_bytes': read.receipt['archive_bytes'],
            'case_denominator': 1, 'case_id': CASE, 'parent_case_status': case.get('status'),
            'status': 'retained_V5_observations_consistent' if not questions else 'retained_V5_consistency_questions',
            'consistency_questions': list(dict.fromkeys(questions)), 'public_and_ADK': public,
            'call_response_outcomes': pairs, 'provider_ADK_joins': joins, 'provider': provider,
            'provider_drain': drain, 'runtime_manifest': runtime, 'worker_result': worker,
            'actor_separation': separation, 'actor_network_diagnostics': actor, 'parent_process_cleanup': children,
            'whole_task_grade': None, 'human_gold_qualified': False, 'untouched_holdout_qualified': False,
            'hidden_effect_or_real_settlement_proven': False, 'actual_provider_requests_by_analyzer': 0,
            'validated_read_members': read.reads, 'analysis_dependencies': DEPENDENCIES,
            'limits': ['One adaptive development case; all prior attempts retain separate denominators.',
                       'Retained source and event consistency does not authenticate hidden effects or full runtime files.',
                       'A demo Success receipt is reported only as a sample receipt shape, never a human whole-task grade.',
                       'Provider usage with absent metadata remains unknown rather than zero.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained', type=Path, required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--head-sha', required=True)
    parser.add_argument('--frozen-plan', type=Path, required=True)
    parser.add_argument('--frozen-plan-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.frozen_plan.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == args.frozen_plan_sha256, 'explicit_frozen_plan_identity_differs')
    base, output = args.retained.resolve(), args.output.resolve()
    need(base.is_relative_to(ROOT / 'runs') and output.is_relative_to(ROOT / 'runs') and not output.exists(),
         'retained_workspace_and_fresh_output_required')
    read = V1.Retained(base, args.run_id, args.head_sha)
    artifacts = json.loads((base / 'github-artifacts.json').read_bytes())['artifacts']
    matched = [row for row in artifacts if row['id'] == read.receipt['artifact_id']]
    need(len(matched) == 1 and matched[0]['name'] == read.receipt['artifact_name']
         and matched[0]['digest'] == read.receipt['api_digest'], 'API_artifact_identity_differs')
    report = analyze(read, json.loads(raw))
    report['frozen_plan_sha256'] = args.frozen_plan_sha256
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'ADK_events': report['public_and_ADK']['raw_ADK_events'],
                      'business_attempts': report['call_response_outcomes']['business_call_attempts'],
                      'business_terminals': report['call_response_outcomes']['business_terminal_responses'],
                      'sample_success_receipts': report['public_and_ADK']['unique_success_receipt_records'],
                      'questions': len(report['consistency_questions'])}))


if __name__ == '__main__':
    main()
