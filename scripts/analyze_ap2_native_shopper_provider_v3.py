"""Additive retained V3 analysis with explicit frozen schema/source binding.

The hash-pinned V2 drain policy and V1 public/SDK/provider helpers stay unchanged.
Actual run/head are caller inputs. Constructed controls supply no actual result.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
V2_PATH = ROOT / 'scripts/analyze_ap2_native_shopper_provider_v2.py'
V2_SHA256 = 'c1211733a21dd8bc8ea1aee5135b471c43f53fe7459eb998daf678160375e07d'
FROZEN_PLAN = ROOT / 'runs/ap2-native-shopper-provider-development/v3/preparation-1/plan.json'
FROZEN_PLAN_SHA256 = '49343a1fa5c7836b6acf851ce213a4699718026dd7ebaf305a2f9186c7a9d63f'
CASE_ID = 'ap2-native-shopper-provider-v3-correct-human'

if hashlib.sha256(V2_PATH.read_bytes()).hexdigest() != V2_SHA256:
    raise ValueError('immutable_V2_analyzer_dependency_differs')
SPEC = importlib.util.spec_from_file_location('_native_shopper_V3_offline_V2_helpers', V2_PATH)
V2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V2)
V1 = V2.V1


def frozen_plan(path=FROZEN_PLAN):
    raw = path.read_bytes()
    if V1.digest(raw)['sha256'] != FROZEN_PLAN_SHA256:
        raise ValueError('root_reviewed_V3_frozen_analysis_plan_differs')
    return json.loads(raw)


def check_plan(read, expected):
    plan = read.json('plan/plan.json')
    if plan.get('schema_version') != 'ap2-native-shopper-provider-plan/3':
        raise ValueError('explicit_V3_plan_schema_required')
    if set(plan) != set(expected) or any(json.dumps(plan[key], sort_keys=True) != json.dumps(value, sort_keys=True) for key, value in expected.items() if key != 'prepared_at'):
        raise ValueError('actual_V3_plan_differs_from_root_reviewed_frozen_template')
    if plan['public_human_facts']['case_id'] != CASE_ID or plan['allocated_task_count'] != 1:
        raise ValueError('single_declared_V3_development_case_required')
    for name, identity in plan['owned_sources'].items():
        if V1.digest(read.raw('plan/owned-source/' + name)) != identity:
            raise ValueError('frozen_V3_owned_source_snapshot_differs:' + name)
    return plan


def analyze(read, expected_plan):
    plan = check_plan(read, expected_plan)
    result = read.json('execution/result.json')
    if (result.get('schema_version') != 'ap2-native-shopper-provider-result/3'
            or type(result.get('allocated_task_count')) is not int or result.get('allocated_task_count') != 1 or len(result.get('cases', [])) != 1):
        raise ValueError('single_declared_V3_result_schema_and_denominator_required')
    case = result['cases'][0]
    if case.get('case_id') != CASE_ID:
        raise ValueError('declared_V3_case_identity_differs')
    root, shopper = 'execution/cases/' + CASE_ID + '/', 'execution/cases/' + CASE_ID + '/shopper/'
    snapshots = [(name, read.json(name)) for name in sorted(read.manifest) if re.fullmatch(re.escape(shopper) + r'turn-\d+-session\.json', name)]
    public = V1.public_analysis(read.rows(shopper + 'ADK-events.jsonl'), read.rows(shopper + 'public-conversation.jsonl'), read.rows(shopper + 'public-actor-decisions.jsonl'), snapshots, plan['public_human_facts'])
    provider = V1.provider_analysis(read, result)
    runtime = V1.runtime_analysis(read, plan, result)
    # V3 deliberately preserves the V2 execution boundary/drain schema and
    # policy. Reuse its analysis without rewriting retained result schemas.
    drain = V2.drain_analysis(read, plan, result, provider)
    launch = read.json(root + 'native-launch.json', optional=True)
    binding = read.json(shopper + 'original-root-binding.json', optional=True)
    worker = read.json(shopper + 'worker-result.json', optional=True)
    facts = read.json(root + 'public-human-facts.json', optional=True)
    questions = [*public['consistency_questions'], *provider['consistency_questions'], *runtime['consistency_questions'], *drain['consistency_questions']]
    preflight = result.get('status') == 'runtime_preflight_failed_before_provider_or_application_calls'
    if preflight and (case.get('status') != 'unexecuted' or result.get('unexecuted_count') != 1 or public['raw_ADK_events'] or launch is not None or binding is not None):
        questions.append('V3_runtime_preflight_failure_has_executed_case_or_application_observations')
    if not preflight and (not runtime['record_present'] or result.get('portable_runtime_sha256') is None):
        questions.append('V3_post_preflight_execution_lacks_bound_runtime_manifest')
    if facts is not None and facts != plan['public_human_facts']:
        questions.append('actual_V3_public_actor_facts_differ_from_frozen_plan')
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
            questions.append('actual_V3_original_root_source_tool_model_or_subagent_binding_differs')
        if public['session_snapshot_ids'] and public['session_snapshot_ids'] != [binding.get('session_id')]:
            questions.append('V3_root_binding_and_recorded_session_identity_differ')
    if public['raw_ADK_events'] and (binding is None or facts is None):
        questions.append('V3_raw_ADK_execution_lacks_original_binding_or_public_fact_record')
    if provider['recorded_cumulative_request_bytes'] != (result.get('provider') or {}).get('cumulative_request_bytes', 0):
        questions.append('V3_retained_request_bytes_and_parent_summary_differ')
    if provider['upstream_allocations'] > plan['limits']['upstream_calls_including_smoke'] or provider['recorded_cumulative_request_bytes'] > plan['limits']['maximum_total_request_bytes']:
        questions.append('V3_recorded_provider_allocations_or_request_bytes_exceed_frozen_bounds')
    if provider['minimum_recorded_allocation_timestamp_gap_seconds'] is not None and provider['minimum_recorded_allocation_timestamp_gap_seconds'] < plan['limits']['minimum_interval_seconds']:
        questions.append('V3_recorded_allocation_timestamp_gap_below_frozen_minimum')
    if any(path != plan['provider_path'] for path in provider['recorded_provider_path_census']):
        questions.append('V3_recorded_provider_path_differs_from_frozen_plan')
    if launch is not None:
        for role, identity in launch.get('public_cards', {}).items():
            if V1.digest(read.raw(root + role + '.agent-card.json')) != identity:
                questions.append('V3_recorded_native_agent_card_digest_differs')
    read.raw(root + 'shopper.stdout.log', optional=True)
    cleanups, native_pids = case.get('process_cleanup', []), {}
    for role in ('merchant', 'credentials', 'processor'):
        raw = read.raw(root + role + '.stdout.log', optional=True)
        native_pids[role] = [int(value) for value in re.findall(rb'Started server process \[(\d+)\]', raw or b'')]
    cleanup_ids = {row['pid'] for row in cleanups if row.get('reaped')}
    if any(pid not in cleanup_ids for values in native_pids.values() for pid in values):
        questions.append('V3_recorded_native_PID_lacks_reaped_cleanup')
    if result.get('source_tree_unchanged_after_original_run') is False or case.get('private_original_source_bytes_unchanged') is False:
        questions.append('V3_parent_reports_original_or_private_source_change')
    questions = list(dict.fromkeys(questions))
    return {'schema_version': 'ap2-native-shopper-provider-offline-analysis/3',
            'run_id': read.receipt['run_id'], 'head_sha': read.receipt['head_sha'], 'archive_sha256': read.receipt['archive_sha256'],
            'case_denominator': 1, 'case_id': CASE_ID, 'adaptive_development_followup': True, 'held_out_study': False,
            'status': 'retained_V3_native_shopper_observations_consistent' if not questions else 'retained_V3_native_shopper_incomplete_or_inconsistent',
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
            'immutable_V1_analyzer_source_sha256': V2.V1_SHA256, 'immutable_V2_analyzer_source_sha256': V2_SHA256,
            'root_reviewed_frozen_plan_template_sha256': FROZEN_PLAN_SHA256, 'bound_V3_owned_sources': plan['owned_sources'],
            'inherited_boundary_drain_schema': 'ap2-provider-drain/2', 'whole_task_grade': None, 'human_gold': False,
            'original_run_sh_provisioning_qualified': False, 'original_A2A_wire_capture_claimed': False, 'hidden_effects_or_real_settlement_proven': False,
            'limits': ['Retained development observations and their consistency do not replace human semantic task grading.',
                       'An owned actor stop, original tool failure, provider failure and unreached branch remain separate outcomes.',
                       'Handler completion at capture freeze is separate from consumed allocations; unclosed consumption remains unknown.',
                       'Frozen V3 sources preserve the V2 sender/drain and V1 worker; retained schemas are checked directly, not rewritten.',
                       'Provider transport timeout and drain wait records do not prove a whole-request network wall-clock cap.',
                       'Runtime versions, parent cleanup/ownership and source-copy assertions do not supply full original A2A wire, hidden effects or settlement proof.']}


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
        raise ValueError('fresh_additive_V3_analysis_output_required')
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
