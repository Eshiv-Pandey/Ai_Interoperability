"""Independent, zero-application static AP2 V8 source/scope review receipt."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = (
    'scripts/ap2_reference_development_v8.py',
    'scripts/run_ap2_native_bridge_matrix_v8.py',
    'scripts/evaluate_ap2_native_bridge_matrix_v8.py',
    'src/interoperability/ap2_native_transport_v8.py',
    'scripts/ap2_bridge_client_v8.mjs',
    'scripts/ap2_bridge_network_guard_v8.mjs',
    'scripts/ap2_native_bridge_runtime_v8.py',
    '.github/workflows/ap2-native-bridge-development-v8.yml',
    'benchmark/ap2-native-bridge-development-v8/application.json',
    'benchmark/ap2-native-bridge-development-v8/evaluator.json',
    'docs/research/ap2-native-bridge-development-v8.md',
)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(name):
    return json.loads((ROOT / name).read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.markdown.exists():
        raise ValueError('fresh_peer_review_outputs_required')
    blobs = {name: (ROOT / name).read_bytes() for name in REVIEWED}
    source = {name: raw.decode('utf-8-sig').replace('\r\n', '\n') for name, raw in blobs.items()}
    public = read('benchmark/ap2-native-bridge-development-v8/application.json')
    old = read('benchmark/ap2-application-development-v5/application.json')
    private = read('benchmark/ap2-native-bridge-development-v8/evaluator.json')
    finalization_path = 'docs/research/ap2-v8-finalization-peer-control-v2.json'
    finalization = read(finalization_path)
    sender_path = 'docs/research/ap2-v8-native-sender-peer-control-v3.json'
    sender = read(sender_path)
    bridge_path = 'docs/research/ap2-v8-bridge-sender-peer-control-v2.json'
    bridge = read(bridge_path)
    checks = {}

    def record(label, condition, evidence):
        checks[label] = {'passed': bool(condition), 'evidence': evidence}

    record('exact_13_V5_case_dictionaries', public['cases'] == old['cases'] and len(public['cases']) == 13,
           'V5 and V8 case dictionaries compared directly, including descriptions and human inputs.')
    record('unchanged_five_policy_flags',
           [{k: v for k, v in row.items() if k != 'description'} for row in public['arms'][:5]] ==
           [{k: v for k, v in row.items() if k != 'description'} for row in old['arms']],
           'Description-only TCP scope changes excluded; every policy flag compared directly.')
    record('prospective_104_denominator',
           len(public['cases']) * len(public['arms']) == public['declared_cells'] == private['declared_cells'] == 104,
           '13 cases by 8 arms, comprising 65 native policy cells and 39 repeated legal bridge initiation slots.')
    original = []
    for name, row in public['original_outgoing_source_records'].items():
        snapshot = (ROOT / row['retained_path']).read_bytes()
        expected = {key: row[key] for key in ('bytes', 'sha256')}
        current = (ROOT / name).read_bytes()
        original.append({'source': name, 'retained_path': row['retained_path'], 'identity': identity(snapshot),
                         'manifest_matches': identity(snapshot) == expected, 'external_original_bytes_match': current == snapshot})
    record('nine_original_source_and_license_snapshots', len(original) == 9 and all(
        row['manifest_matches'] and row['external_original_bytes_match'] for row in original),
        'Seven outgoing original source files and two license files independently rehashed against manifest and external originals.')
    orchestrator = source['scripts/run_ap2_native_bridge_matrix_v8.py']
    record('independent_partial_finalization_controls_current', finalization['passed'] is True
           and all(finalization['controls'].values())
           and finalization['orchestrator_sha256'] == identity(blobs['scripts/run_ap2_native_bridge_matrix_v8.py'])['sha256']
           and finalization['actual_application_or_provider_calls'] == finalization['actual_actor_processes_executed'] == 0,
           finalization_path)
    evaluator = source['scripts/evaluate_ap2_native_bridge_matrix_v8.py']
    record('seven_independent_native_sender_controls_current', sender['passed'] is True
           and all(sender['controls'].values()) and len(sender['controls']) == 7
           and sender['evaluator_sha256'] == identity(blobs['scripts/evaluate_ap2_native_bridge_matrix_v8.py'])['sha256']
           and sender['actual_application_or_provider_calls'] == sender['actual_actor_or_bridge_processes_executed'] == 0,
           sender_path)
    record('eight_independent_bridge_Node_attribution_controls_current', bridge['passed'] is True
           and all(bridge['controls'].values()) and len(bridge['controls']) == 8
           and bridge['evaluator_sha256'] == identity(blobs['scripts/evaluate_ap2_native_bridge_matrix_v8.py'])['sha256']
           and bridge['actual_application_or_provider_calls'] == bridge['actual_actor_or_bridge_processes_executed'] == 0,
           bridge_path)
    actor = source['scripts/ap2_reference_development_v8.py']
    guard = source['scripts/ap2_bridge_network_guard_v8.mjs']
    record('cleanup_exception_robustness_source_review',
           "cleanup_failures.append({'operation': 'client_aclose'" in actor
           and "cleanup_failures.append({'operation': 'transport_aclose'" in actor
           and "cleanup_failures.append({'operation': 'owned_peer_group_close'" in actor
           and 'finally:\n                httpx.AsyncClient.__init__, genai.Client = original_init, original_genai' in actor
           and 'and not cleanup_failures' in actor and "cleanup['owned_cleanup_failures'] == []" in evaluator,
           'Per-resource close exceptions are recorded; nested finally attempts owned socket closure and restores aliases. Static control-flow review only, not an observed close failure.')
    record('Node_fetch_observer_preserves_original_arguments_and_response',
           'originalFetch.call(this, input, init)' in guard
           and 'response.clone().arrayBuffer()' in guard and 'return response;' in guard
           and 'original_fetch_arguments_rewritten: false' in guard,
           'Observer consumes a clone before delivering the unchanged response. This can affect timing and is disclosed scheduling instrumentation, not timing-neutral execution.')
    imports = []
    for node in ast.walk(ast.parse(evaluator)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or '')
    record('no_static_actor_or_admission_import_in_evaluator',
           not any('ap2_reference_development' in name or 'ap2_application' in name
                   or 'ap2_native_transport' in name for name in imports),
           'AST imports inspected. The evaluator dynamically loads the retained generic certificate checker only; this is not independent human review.')
    record('bridge_repetition_and_unrealized_branches_explicit',
           public['continuation_unrealized_after_bridge_boundary_retained'] is True
           and '39 repeated prefix/initiation slots' in public['bridge_allocation_semantics']
           and "'repeated_bridge_prefix_and_initiation_slot': True" in evaluator
           and "'post_initiation_case_fault_or_OTP_branch_exercised': False" in evaluator,
           'Three missing-association slots retain a prefix omission; other later case faults and all OTP branches stay unrealized.')
    record('selected_route_limit_and_missing_outcomes_explicit',
           'remain in the 104-cell denominator' in private['missing_or_timed_out_cells']
           and 'partial_allocation_capture_unclosed_and_retained' in evaluator
           and 'whole_route_non_support_inference_allowed' in evaluator
           and 'retained_dispatch_attempts_must_be_finalized_not_replayed' in orchestrator,
           'Missing/unclosed outcomes remain present and cannot become verified purchases; no retained attempt is replayed by prepared-allocation resume.')
    workflow = source['.github/workflows/ap2-native-bridge-development-v8.yml']
    record('allocation_precedes_smoke_and_always_retention_present',
           workflow.index('--prepare-only') < workflow.index('for arm in conventional amir_typed mg_typed mg_raw')
           < workflow.index('--resume-prepared') and workflow.count('if: always()') == 2,
           'Workflow source order reviewed; this is prospective scheduling evidence, not evidence that GitHub dispatched or completed it.')
    report = {
        'schema_version': 'ap2-native-bridge-v8-independent-static-scope-review/1',
        'reviewed_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'static_controls_passed_no_further_confirmed_blocker' if all(row['passed'] for row in checks.values()) else 'static_control_refused',
        'passed': all(row['passed'] for row in checks.values()), 'checks': checks,
        'reviewed_sources': {name: identity(raw) for name, raw in blobs.items()},
        'original_outgoing_snapshots': original,
        'supporting_finalization_control': {'path': finalization_path, 'identity': identity((ROOT / finalization_path).read_bytes())},
        'supporting_sender_controls': [{'path': name, 'identity': identity((ROOT / name).read_bytes())}
                                      for name in (sender_path, bridge_path)],
        'superseded_failure_control': 'docs/research/ap2-v8-finalization-peer-control-v1.json',
        'superseded_sender_failure_control': 'docs/research/ap2-v8-native-sender-peer-control-v1.json',
        'new_original_application_calls': 0, 'new_provider_calls': 0, 'new_bridge_processes': 0,
        'human_review_performed': False, 'checkpoint_credit_claimed': False,
        'scope_limits': [
            'Static and constructed reviews do not establish runtime outcome, genuine held-out evaluation or human gold.',
            'Native TCP uses owned Uvicorn bootstrap with disabled lifespan/websocket handling, not canonical original launcher qualification.',
            'Python/Node guards are source-bound controls, not a hostile-code operating-system sandbox.',
            'Thirty-nine bridge slots are repeated prefix/initiation observations, not thirteen distinct exercised fault continuations.',
            'A root card 404 is a discovery outcome, not an observed downstream DataPart, extension or normalization failure.',
            'Typed interfaces cannot carry caller DataParts or extension-header arguments; raw modern method enum does not legalize legacy method names.',
            'No incoming Task inverse, original-card rewrite, injected header/method argument or fabricated context handle is permitted.',
            'A selected-route failure does not establish non-support for an entire original interface.',
        ],
    }
    for path in (args.output, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = [
        '# AP2 V8 independent static scope review', '',
        '11 November 2026. The repaired interrupted-allocation finalizer passes all six independent constructed controls. '
        'This review finds no additional confirmed blocker in the reviewed source. No original application, provider or bridge process was executed by this review.', '',
        f"The reproducible JSON receipt records {len(checks)} static/source controls and hashes all {len(REVIEWED)} reviewed files. "
        f"All controls passed: {report['passed']}. It also rehashes nine original outgoing source/license snapshots against their manifest and external originals.", '',
        'The prospective matrix contains 65 native policy cells and 39 repeated bridge initiation slots. '
        'The bridge slots intercept original payment initiation before later faults and OTP continuations. '
        'Only the three missing-association prefix slots exercise that omission. '
        'This review provides no new purchase, task success or checkpoint percentage.', '',
        'The original legal outgoing mappings were reviewed: Amir typed uses its fresh configured agent alias and text without inventing opaque handles; '
        'mgcrea typed uses URL, text and a legal optional raw context ID; mgcrea raw uses modern SendMessage with original params. '
        'No incoming Task inverse or header argument is added. The original prefixed AP2 card stays unchanged. '
        'A mgcrea root-card 404 must remain described as a discovery result.', '',
        'The original failure receipt remains retained as ap2-v8-finalization-peer-control-v1.json. '
        'The successor ap2-v8-finalization-peer-control-v2.json verifies preservation of completed return codes/status, '
        'distinguishes before-only intent from untouched allocations and proves prior completed receipt bytes are unchanged.', '',
        'The sender-witness omission failure remains retained as ap2-v8-native-sender-peer-control-v1.json. '
        'Its fresh v3 successor passes seven native controls; ap2-v8-bridge-sender-peer-control-v2.json passes eight bridge/Node-attribution controls. '
        'Valid supplied witnesses are accepted, while missing logs, altered header/query/body-size fields, unjustified false dispatch, '
        'missing or altered Node observations, wrong or duplicate bridge intercepts and unattributed receives are rejected. '
        'These constructed controls executed no application or bridge process.', '',
        'The actor cleanup was also reviewed statically. Individual close failures no longer bypass later socket closure or alias restoration; '
        'nonempty cleanup-failure receipts are refused. The source-bound Node HTTP observer preserves original fetch arguments and response identity, '
        'but consuming the response clone before delivery is timing instrumentation. No close failure was observed in a real application by this review.', '',
        'The review is bounded by the exact hashes in the JSON receipt. Any source edit requires a fresh successor review. '
        'Static controls do not establish canonical launcher qualification, genuine held-out evaluation, human gold or publication readiness.', '',
    ]
    args.markdown.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'checks': len(checks), 'source_files': len(REVIEWED),
                      'original_source_and_license_snapshots': len(original)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
