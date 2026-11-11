"""Offline V2 native shopper analysis with a stable frozen-capture join.

V1 analysis and frozen V2 execution sources remain unchanged. Expected actual
run/head are explicit caller inputs; constructed controls never stand in for
an actual retained archive. This imports only a hash-pinned stdlib analyzer.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
V1_PATH = ROOT / 'scripts/analyze_ap2_native_shopper_provider_v1.py'
V1_SHA256 = 'fd07c3609400f951d8500ce97f1cc655fc4ed654b7836597c30d26262ef930ab'
FROZEN_PLAN = ROOT / 'runs/ap2-native-shopper-provider-development/v2/preparation-2/plan.json'
FROZEN_PLAN_SHA256 = '3c47d565091c3ac1b0842df35c56ecc1c12c1965e99cfe564456b71a7b399cda'
CASE_ID = 'ap2-native-shopper-provider-v2-correct-human'

if __import__('hashlib').sha256(V1_PATH.read_bytes()).hexdigest() != V1_SHA256:
    raise ValueError('immutable_V1_analyzer_dependency_differs')
SPEC = importlib.util.spec_from_file_location('_native_shopper_V2_offline_V1_helpers', V1_PATH)
V1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V1)


def frozen_plan(path=FROZEN_PLAN):
    raw = path.read_bytes()
    if V1.digest(raw)['sha256'] != FROZEN_PLAN_SHA256:
        raise ValueError('root_reviewed_V2_frozen_analysis_plan_differs')
    return json.loads(raw)


def check_plan(read, expected):
    plan = read.json('plan/plan.json')
    if plan.get('schema_version') != 'ap2-native-shopper-provider-plan/2':
        raise ValueError('explicit_V2_plan_schema_required')
    if set(plan) != set(expected) or any(json.dumps(plan[key], sort_keys=True) != json.dumps(value, sort_keys=True) for key, value in expected.items() if key != 'prepared_at'):
        raise ValueError('actual_V2_plan_differs_from_root_reviewed_frozen_template')
    if plan['public_human_facts']['case_id'] != CASE_ID or plan['allocated_task_count'] != 1:
        raise ValueError('single_declared_V2_development_case_required')
    for name, identity in plan['owned_sources'].items():
        if V1.digest(read.raw('plan/owned-source/' + name)) != identity:
            raise ValueError('frozen_V2_owned_source_snapshot_differs:' + name)
    return plan


def finite_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def drain_analysis(read, plan, result, provider):
    recorded = read.json('execution/provider-drain.json', optional=True)
    result_record = result.get('provider_drain')
    ledger = read.rows('execution/provider/ledger.jsonl')
    summary = result.get('provider') or {}
    questions = []
    preflight = result.get('status') == 'runtime_preflight_failed_before_provider_or_application_calls'
    if preflight:
        if recorded is not None or result_record is not None or ledger or summary.get('upstream_allocations') != 0:
            questions.append('runtime_preflight_failure_contains_provider_drain_or_allocations')
        return {'record_present': recorded is not None, 'status': 'not_started_runtime_preflight',
                'consistency_questions': questions, 'fully_measured_provider_consumption_claimed': False}
    if recorded is None:
        return {'record_present': False, 'status': 'required_V2_capture_freeze_record_absent',
                'consistency_questions': ['required_V2_provider_drain_record_absent'],
                'fully_measured_provider_consumption_claimed': False}
    if recorded != result_record:
        questions.append('standalone_and_parent_V2_provider_drain_records_differ')
    if recorded.get('schema_version') != 'ap2-provider-drain/2':
        questions.append('explicit_V2_provider_drain_schema_differs')
    for key in ('admission_closed', 'capture_frozen', 'unfinished_allocations_require_unknown_usage'):
        if recorded.get(key) is not True:
            questions.append('V2_drain_' + key + '_not_true')
    if recorded.get('late_sender_outcomes_retained') is not False:
        questions.append('V2_drain_late_outcome_capture_record_differs')
    for key in ('admission_closed', 'capture_frozen'):
        if summary.get(key) is not True:
            questions.append('V2_parent_provider_' + key + '_not_true')
    if summary.get('request_transport_timeout_seconds') != plan['limits']['request_timeout_seconds'] or summary.get('request_timeout_is_independent_whole_request_wall_cap') is not False:
        questions.append('V2_parent_sender_timeout_or_wall_cap_record_differs')
    active = recorded.get('active_handlers_at_capture_freeze')
    active_summary = summary.get('active_handlers')
    active_valid = type(active) is int and active >= 0
    if not active_valid or type(active_summary) is not int or not 0 <= active_summary <= active:
        questions.append('V2_active_handler_census_absent_invalid_or_increases_after_freeze')
    if not active_valid or recorded.get('all_handlers_completed') is not (active == 0):
        questions.append('V2_all_handlers_completed_record_and_freeze_census_differ')
    maximum, elapsed = recorded.get('maximum_drain_seconds'), recorded.get('elapsed_drain_seconds')
    if not finite_nonnegative(maximum) or maximum > plan['limits']['maximum_provider_drain_seconds'] or not finite_nonnegative(elapsed):
        questions.append('V2_drain_wait_bounds_or_elapsed_record_invalid')
    joins = {'allocated_upstream_calls_at_capture_freeze': provider['upstream_allocations'],
             'request_bytes_at_capture_freeze': provider['recorded_cumulative_request_bytes'],
             'unclosed_allocation_ids': provider['unclosed_allocation_ids'],
             'allocations_with_unmeasured_usage': provider['allocations_with_unmeasured_usage']}
    for key, value in joins.items():
        if recorded.get(key) != value:
            questions.append('V2_drain_' + key + '_differs_from_retained_ledger_census')
    if active_valid and len(provider['unclosed_allocation_ids']) > active:
        questions.append('V2_unclosed_allocation_count_exceeds_active_handlers_at_freeze')
    if active == 0 and provider['unclosed_allocation_ids']:
        questions.append('V2_completed_drain_has_unclosed_consumed_allocations')
    if provider['unclosed_allocation_ids'] and provider['fully_measured']:
        questions.append('V2_unclosed_consumption_incorrectly_reported_fully_measured')
    if (summary.get('all_response_usage') or {}).get('unknown_usage_is_zero') is not False:
        questions.append('V2_parent_unknown_usage_zero_policy_record_differs')
    try:
        freeze_time = datetime.fromisoformat(recorded['time'])
        for row in ledger:
            timestamp = datetime.fromisoformat(row['time'])
            if timestamp > freeze_time:
                questions.append('V2_ledger_timestamp_after_recorded_capture_freeze')
    except (KeyError, TypeError, ValueError):
        questions.append('V2_ledger_or_capture_freeze_timestamp_missing_or_invalid')
    return {'record_present': True, 'status': 'frozen_handler_census_and_raw_ledger_consistent' if not questions else 'V2_frozen_capture_incomplete_or_inconsistent',
            'standalone_drain_record': recorded, 'parent_summary_active_handlers': active_summary,
            'handler_census_is_distinct_from_consumed_allocation_count': True,
            'handlers_can_finish_without_late_captured_terminal_observations': True,
            'unclosed_consumed_allocations': provider['unclosed_allocation_ids'],
            'unclosed_allocations_with_unmeasured_usage': len(provider['unclosed_allocation_ids']),
            'all_response_allocations_with_unmeasured_usage': provider['allocations_with_unmeasured_usage'],
            'elapsed_drain_exceeds_requested_wait': elapsed > maximum if finite_nonnegative(elapsed) and finite_nonnegative(maximum) else None,
            'elapsed_wait_is_not_an_independently_proven_socket_wall_cap': True,
            'fully_measured_provider_consumption_claimed': provider['fully_measured'] and not questions and not provider['consistency_questions'],
            'consistency_questions': list(dict.fromkeys(questions)),
            'freeze_enforcement_scope': 'Raw retained ledger/payload joins and frozen owned source policy; actual late upstream completion after capture freeze is not observed.'}


def analyze(read, expected_plan):
    plan = check_plan(read, expected_plan)
    result = read.json('execution/result.json')
    if (result.get('schema_version') != 'ap2-native-shopper-provider-result/2'
            or type(result.get('allocated_task_count')) is not int or result.get('allocated_task_count') != 1 or len(result.get('cases', [])) != 1):
        raise ValueError('single_declared_V2_result_schema_and_denominator_required')
    case = result['cases'][0]
    if case.get('case_id') != CASE_ID:
        raise ValueError('declared_V2_case_identity_differs')
    root, shopper = 'execution/cases/' + CASE_ID + '/', 'execution/cases/' + CASE_ID + '/shopper/'
    snapshots = [(name, read.json(name)) for name in sorted(read.manifest) if re.fullmatch(re.escape(shopper) + r'turn-\d+-session\.json', name)]
    public = V1.public_analysis(read.rows(shopper + 'ADK-events.jsonl'), read.rows(shopper + 'public-conversation.jsonl'), read.rows(shopper + 'public-actor-decisions.jsonl'), snapshots, plan['public_human_facts'])
    provider = V1.provider_analysis(read, result)
    runtime = V1.runtime_analysis(read, plan, result)
    drain = drain_analysis(read, plan, result, provider)
    launch = read.json(root + 'native-launch.json', optional=True)
    binding = read.json(shopper + 'original-root-binding.json', optional=True)
    worker = read.json(shopper + 'worker-result.json', optional=True)
    facts = read.json(root + 'public-human-facts.json', optional=True)
    questions = [*public['consistency_questions'], *provider['consistency_questions'], *runtime['consistency_questions'], *drain['consistency_questions']]
    preflight = result.get('status') == 'runtime_preflight_failed_before_provider_or_application_calls'
    if preflight and (case.get('status') != 'unexecuted' or result.get('unexecuted_count') != 1 or public['raw_ADK_events'] or launch is not None or binding is not None):
        questions.append('V2_runtime_preflight_failure_has_executed_case_or_application_observations')
    if not preflight and (not runtime['record_present'] or result.get('portable_runtime_sha256') is None):
        questions.append('V2_post_preflight_execution_lacks_bound_runtime_manifest')
    if facts is not None and facts != plan['public_human_facts']:
        questions.append('actual_V2_public_actor_facts_differ_from_frozen_plan')
    if worker is not None:
        if worker.get('schema_version') != 'ap2-native-shopper-provider-worker/1' or worker.get('case_id') != CASE_ID or worker.get('ADK_event_count') != public['raw_ADK_events']:
            questions.append('inherited_original_worker_schema_case_or_raw_ADK_count_differs')
    if binding is not None:
        expected = plan['sources']['code/samples/python/src/roles/shopping_agent/agent.py']['sha256']
        if (binding.get('original_root_source_sha256') != expected or binding.get('root_model') != V1.MODEL
                or binding.get('deterministic_BaseLlm_replacement') is not False or binding.get('genai_Client_replaced') is not False
                or binding.get('official_ADK_runner') is not True or binding.get('root_name') != 'root_agent'
                or binding.get('original_root_tool_names') != list(V1.BUSINESS_TOOLS['root_agent'])
                or [row.get('name') for row in binding.get('subagents', [])] != list(V1.STAGES[1:])
                or any(row.get('model') != V1.MODEL for row in binding.get('subagents', []))):
            questions.append('actual_V2_original_root_source_tool_model_or_subagent_binding_differs')
        if public['session_snapshot_ids'] and public['session_snapshot_ids'] != [binding.get('session_id')]:
            questions.append('V2_root_binding_and_recorded_session_identity_differ')
    if public['raw_ADK_events'] and (binding is None or facts is None):
        questions.append('V2_raw_ADK_execution_lacks_original_binding_or_public_fact_record')
    if provider['recorded_cumulative_request_bytes'] != (result.get('provider') or {}).get('cumulative_request_bytes', 0):
        questions.append('V2_retained_request_bytes_and_parent_summary_differ')
    if provider['upstream_allocations'] > plan['limits']['upstream_calls_including_smoke'] or provider['recorded_cumulative_request_bytes'] > plan['limits']['maximum_total_request_bytes']:
        questions.append('V2_recorded_provider_allocations_or_request_bytes_exceed_frozen_bounds')
    if provider['minimum_recorded_allocation_timestamp_gap_seconds'] is not None and provider['minimum_recorded_allocation_timestamp_gap_seconds'] < plan['limits']['minimum_interval_seconds']:
        questions.append('V2_recorded_allocation_timestamp_gap_below_frozen_minimum')
    if any(path != plan['provider_path'] for path in provider['recorded_provider_path_census']):
        questions.append('V2_recorded_provider_path_differs_from_frozen_plan')
    if launch is not None:
        for role, identity in launch.get('public_cards', {}).items():
            if V1.digest(read.raw(root + role + '.agent-card.json')) != identity:
                questions.append('V2_recorded_native_agent_card_digest_differs')
    read.raw(root + 'shopper.stdout.log', optional=True)
    cleanups, native_pids = case.get('process_cleanup', []), {}
    for role in ('merchant', 'credentials', 'processor'):
        raw = read.raw(root + role + '.stdout.log', optional=True)
        native_pids[role] = [int(value) for value in re.findall(rb'Started server process \[(\d+)\]', raw or b'')]
    cleanup_ids = {row['pid'] for row in cleanups if row.get('reaped')}
    if any(pid not in cleanup_ids for values in native_pids.values() for pid in values):
        questions.append('V2_recorded_native_PID_lacks_reaped_cleanup')
    if result.get('source_tree_unchanged_after_original_run') is False or case.get('private_original_source_bytes_unchanged') is False:
        questions.append('V2_parent_reports_original_or_private_source_change')
    questions = list(dict.fromkeys(questions))
    return {'schema_version': 'ap2-native-shopper-provider-offline-analysis/2',
            'run_id': read.receipt['run_id'], 'head_sha': read.receipt['head_sha'], 'archive_sha256': read.receipt['archive_sha256'],
            'case_denominator': 1, 'case_id': CASE_ID, 'adaptive_development_followup': True, 'held_out_study': False,
            'status': 'retained_V2_native_shopper_observations_consistent' if not questions else 'retained_V2_native_shopper_incomplete_or_inconsistent',
            'observed_case_outcome': ('runtime_preflight_failed_before_provider_or_application_calls' if preflight else 'original_ADK_error_before_any_business_tool_or_visible_reply' if public['raw_ADK_error_events'] and not public['business_call_count'] and not public['visible_model_messages'] else 'retained_development_observations_require_per_branch_reading'),
            'consistency_questions': questions, 'parent_case_status': case.get('status'), 'parent_result_status': result.get('status'),
            'parent_failure': result.get('failure'), 'parent_preflight_error': result.get('error'),
            'worker_result': worker, 'public_and_ADK': public, 'provider': provider, 'provider_drain': drain, 'runtime_manifest': runtime,
            'native_launch': launch, 'original_root_binding': binding, 'native_stdout_process_IDs': native_pids, 'parent_process_cleanup': cleanups,
            'all_recorded_children_reaped': all(row.get('reaped') for row in cleanups) if cleanups else None,
            'source_tree_unchanged_parent_record': result.get('source_tree_unchanged_after_original_run'),
            'copied_source_unchanged_parent_record': case.get('private_original_source_bytes_unchanged'),
            'native_listener_ownership_parent_record': launch.get('exact_native_PID_listener_ownership_verified_before_card_requests') if launch else None,
            'native_listener_inode_records_independently_captured': False, 'validated_read_members': read.reads,
            'immutable_V1_analyzer_source_sha256': V1_SHA256, 'root_reviewed_frozen_plan_template_sha256': FROZEN_PLAN_SHA256,
            'bound_V2_owned_sources': plan['owned_sources'], 'whole_task_grade': None, 'human_gold': False,
            'original_run_sh_provisioning_qualified': False, 'original_A2A_wire_capture_claimed': False, 'hidden_effects_or_real_settlement_proven': False,
            'limits': ['Retained development observations and their consistency do not replace human semantic task grading.',
                       'An owned actor stop, original tool failure, provider failure and unreached branch remain separate outcomes.',
                       'Handler completion at capture freeze is separate from consumed allocations; unclosed consumption remains unknown.',
                       'No retained late upstream response exists after capture freeze; frozen source policy and stable raw records constrain the claim.',
                       'Provider transport timeout and drain wait records do not prove a whole-request network wall-clock cap.',
                       'Runtime versions, parent cleanup/ownership and original source-copy assertions do not supply full original A2A wire, hidden effects or settlement proof.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-run', type=int, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--frozen-plan', type=Path, default=FROZEN_PLAN)
    args = parser.parse_args()
    if args.expected_run <= 0 or not re.fullmatch(r'[0-9a-f]{40}', args.expected_head):
        raise ValueError('explicit_positive_run_and_full_expected_head_required')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('fresh_additive_V2_analysis_output_required')
    result = analyze(V1.Retained(args.retained.resolve(), args.expected_run, args.expected_head), frozen_plan(args.frozen_plan.resolve()))
    output.mkdir(parents=True)
    result['analyzer_source_sha256'] = V1.file_hash(Path(__file__).resolve())
    with (output / 'analysis.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'case_denominator': 1, 'consistency_questions': len(result['consistency_questions']),
                      'observed_ADK_events': result['public_and_ADK']['raw_ADK_events'],
                      'sample_success_receipts': result['public_and_ADK']['unique_success_receipt_records'],
                      'allocations_with_unmeasured_usage': result['provider']['allocations_with_unmeasured_usage']}))


if __name__ == '__main__':
    main()
