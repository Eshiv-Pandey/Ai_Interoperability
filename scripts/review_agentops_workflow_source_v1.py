"""Independent source/control review; no original application or SDK imports."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'scripts/agentops_workflow_reference_v1.py',
    'scripts/agentops_workflow_public_v1.py',
    'scripts/analyze_agentops_workflow_reference_v1.py',
    'scripts/check_agentops_workflow_reference_v1.py',
    'scripts/ci_agentops_workflow_reference_v1.py',
    'docs/research/agentops-workflow-reference-v1.md',
    '.github/workflows/agentops-workflow-reference-v1.yml',
    'external/agentops-c806b7f1/agents/python/src/agent/workflow.py',
    'external/agentops-c806b7f1/agents/python/src/agent/composition.py',
    'external/agentops-c806b7f1/agents/python/src/agent/governance.py',
    'external/agentops-c806b7f1/agents/python/src/agent/guardrails.py',
)


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sources = {name: identity(ROOT / name) for name in FILES}
    original = ast.parse((ROOT / FILES[7]).read_text(encoding='utf-8'))
    runner = ast.parse((ROOT / FILES[0]).read_text(encoding='utf-8'))
    instructions = []
    for stage in ('plan', 'investigate', 'evidence_review', 'recommend'):
        assignment = next(n for n in original.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == stage for t in n.targets))
        keyword = next(k for k in assignment.value.keywords if k.arg == 'instruction')
        instructions.append(hashlib.sha256(ast.literal_eval(keyword.value).encode()).hexdigest())
    declared = next(n for n in runner.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'INSTRUCTION_SHA256' for t in n.targets))
    if instructions != list(ast.literal_eval(declared.value)):
        raise ValueError('Original per-node instruction literals differ from runtime source guards')
    if sources[FILES[7]]['sha256'] != '68c3fefa9966ecddb69d96150423379433016be508f811df7638a30ba9bb9747':
        raise ValueError('Original Workflow source pin differs')
    controls = subprocess.run([sys.executable, '-B', str(ROOT / FILES[3])], cwd=ROOT, capture_output=True, timeout=30, check=True)
    (output / 'constructed-controls.stdout.json').write_bytes(controls.stdout)
    (output / 'constructed-controls.stderr.txt').write_bytes(controls.stderr)
    control_result = json.loads(controls.stdout)
    if control_result['checks'] != 18 or control_result['original_application_execution'] is not False:
        raise ValueError('Unexpected software control scope or count')
    checked = subprocess.run([sys.executable, '-B', str(ROOT / FILES[4]), '--check-inputs'], cwd=ROOT, capture_output=True, timeout=30, check=True)
    (output / 'input-binding-check.stdout.json').write_bytes(checked.stdout)
    (output / 'input-binding-check.stderr.txt').write_bytes(checked.stderr)
    checks = json.loads(checked.stdout)
    if checks['tasks'] != ['agentops-h09-workflow-select-target', 'agentops-h10-workflow-override-conflict']:
        raise ValueError('Two original candidate identities changed')
    if any(identity(ROOT / name) != expected for name, expected in sources.items()):
        raise ValueError('Reviewed source changed while controls ran')
    report = {
        'schema_version': 'agentops-workflow-independent-source-review/1',
        'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'source_and_constructed_controls_reviewed_runtime_qualification_separate',
        'reviewer': 'independent Codex subagent native_original_shopper',
        'source_review_passed': True, 'sources': sources,
        'original_workflow_instruction_hashes': instructions,
        'constructed_controls': control_result,
        'source_input_check': {'status': checks['status'], 'source_members': checks['source_files'], 'tasks': checks['tasks']},
        'verified_source_findings': [
            'Original composition.app/root/workflow object identities and four-node edge are checked before execution; conversational root is not substituted.',
            'Original instruction hashes, exact node read-only tool surfaces and absent node policy callbacks are guarded; only declared node models are replaced.',
            'Original AgentOpsPolicyPlugin remains first; added observational hooks return None and do not modify original callbacks or governed values.',
            'Corrected analyzer treats raw official SDK function-response events as post-policy terminal authority; optional appended after-tool observers may legitimately short circuit.',
            'Targets derive from observed exact incident/list results; h10 request claims remain separate and resolved-state conflict is preserved without an action or note.',
            'Each case receives fresh copied seed/state/process/session; before/after database rows, original data/source hashes and owned worker cleanup are retained.',
            'Hosted controller stages original source, uses uv0.12.0/Python3.13.1 with the unchanged lock, retains installed runtime census and actual plugin-manager source before application execution.',
            'Both h09/h10 remain separate allocated candidates; failed/missing workers or source/tool/stage/state discrepancies cannot pass correspondence analysis.'
        ],
        'resolved_issue': {
            'description': 'Appended after-tool observation can be skipped when original security policy returns a replacement dictionary.',
            'correction': 'Use raw post-policy SDK function-response events joined to actual node/call IDs; after-hook journal is optional and compared only when present.',
            'controls': ['first_non_none_policy_replacement_skips_later_after_observer', 'raw_sdk_terminals_remain_authority_when_all_after_hooks_short_circuit', 'missing_raw_sdk_terminal_remains_partial_despite_short_circuit']
        },
        'dispatch_source_evidence_precision': 'Comparison inspected AP2-installed ADK1.28 plugin-manager first-non-None semantics; it is not called AgentOps pinned runtime evidence. The original AgentOps governance/guardrails state the semantics, and the new controller retains the actual installed locked-runtime manager before its task.',
        'unresolved_source_findings': [],
        'runtime_execution_performed_by_this_review': False, 'original_SDK_imported_by_this_review': False,
        'provider_calls': 0, 'held_out_qualified': False, 'human_gold_qualified': False,
        'original_A2A_or_native_transport_qualified': False,
        'runtime_evidence_not_inspected_by_this_review': True,
        'limits': ['Source/control review cannot establish actual Workflow execution, task semantics, source-to-model fidelity, live model quality or original A2A support.',
                   'Deterministic contextual JSON outputs are an owned model intervention; original source instructions are not modified.',
                   'The separate retained actual allocation must verify stage order, raw SDK calls/terminals, runtime manager source, state invariants, all failures and cleanup.']
    }
    target = output / 'review.json'
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'controls': control_result['checks'], 'review': str(target), 'source_review_passed': True}))


if __name__ == '__main__':
    main()
