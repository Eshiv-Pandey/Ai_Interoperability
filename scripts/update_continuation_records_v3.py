"""Snapshot exact current records, then integrate the closure screen once."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / 'docs/research/snapshots/continuation-v3'
PRE = ROOT / 'paper/continuation-pre-edit-integrity-v3.json'
PRIOR = ROOT / 'paper/continuation-integrity-v2.json'
RECORDS = [
    'RESEARCH_WORKFLOW.md', 'docs/research/execution-handoff.md',
    'docs/research/implementation-novelty-gate.md',
    'docs/research/cp2-review-packet-v1.md',
    'docs/research/checkpoint-status.json', 'paper/draft-status-v0.json',
]
if PRE.exists() or SNAPSHOTS.exists():
    raise SystemExit('Refusing to repeat or replace the v3 context update.')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def receipt(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), str(path)
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


prior = read(PRIOR)
assert prior['status'] == 'passed'
checks = []
for item in prior['checked_inputs']:
    actual = receipt(ROOT / item['checked_path'])
    assert actual['sha256'] == item['sha256'], item['checked_path']
    checks.append(actual)
for item in prior['current_records']:
    actual = receipt(ROOT / item['path'])
    assert actual == item, item['path']
    checks.append(actual)

screen_base = 'docs/research/source-evidence/action-observation-closure-screen-v1'
screen_report = read(ROOT / f'{screen_base}-verification.json')
assert screen_report['status'] == 'passed' and screen_report['files_checked'] == 27
assert screen_report['application_execution'] is False
assert receipt(ROOT / screen_report['manifest']['path']) == screen_report['manifest']
screen_manifest = read(ROOT / screen_report['manifest']['path'])
for item in screen_manifest['files']:
    assert receipt(ROOT / item['path']) == item, item['path']

texts = {
    'RESEARCH_WORKFLOW.md': (
        '## 1. Research direction and what changes',
        '\n\n**Action/observation compiler screen (25 October):** the\n'
        '[bounded method review](docs/research/source-evidence/action-observation-closure-screen-v1/decision.md)\n'
        'specifies field/recipe saturation and correlated history closure, but finds\n'
        'no additional C1 step beyond established knowledge, symbolic and synthesis\n'
        'methods. Legal string guessing and interactive observations must survive\n'
        'the abstraction. Eleven source-fidelity obligations remain unresolved;\n'
        'eight retained query/result pairs pass a 27-file integrity check. No\n'
        'compiler, application experiment, inference or gate credit is added.\n'
        'The original may-completion method objective remains at 5%.',
    ),
    'docs/research/implementation-novelty-gate.md': (
        '## What the fresh source audit changes',
        '\n\nThe [action/observation closure screen](source-evidence/action-observation-closure-screen-v1/decision.md)\n'
        'adds YAPA recipe/static-knowledge, DeepSec interactive-equivalence,\n'
        'register-bounded hidden-input synthesis and RESTler/APIphany comparator\n'
        'obligations. Monotone pooling loses correlations; correlated closure\n'
        'reduces to standard symbolic/contingent reasoning. Concrete legal guesses\n'
        'cannot be removed by an unproved private-atom abstraction. No additional\n'
        'compiler step or performance trial is selected, and eleven source-fidelity\n'
        'obligations remain open. The 27-file integrity check is not G1/G4/G5\n'
        'evidence; may completion remains the approved target, with caller\n'
        'guarantee only a separately labelled diagnostic. Credit stays 5%.',
    ),
    'docs/research/cp2-review-packet-v1.md': (
        '## Claims currently rejected',
        '\n\n**Action/observation compiler addendum (25 October):**\n'
        '[the precise method screen](source-evidence/action-observation-closure-screen-v1/decision.md)\n'
        'rejects generic recipe saturation or correlated symbolic/game closure as\n'
        'a demonstrated extra C1 step. The reviewed primary knowledge/synthesis/API\n'
        'mechanisms strengthen fair-comparator obligations, with their actual\n'
        'quantifiers and restrictions retained. Legal guessing may permit a lucky\n'
        'completion while no bounded uniform guarantee exists; neither nondeduction\n'
        'nor identical pending replies proves whole-interface impossibility.\n'
        '[Eleven coverage obligations](source-evidence/action-observation-closure-screen-v1/closure-obligations.json)\n'
        'remain open. Eight query/result pairs and a 27-file integrity check are\n'
        'source/maintenance evidence only. No compiler, solver, experiment,\n'
        'inference, domain qualification or human review occurred. CP2/CP7 remain\n'
        'incomplete at 5%; the original contribution route is unchanged.',
    ),
    'docs/research/execution-handoff.md': (
        '**Latest continuation update (25 October 2026):**',
        '\n\n- [Action/observation closure screen v1](source-evidence/action-observation-closure-screen-v1/decision.md)\n'
        '  specifies two compiler constructions and retains an adverse C1 result:\n'
        '  pooled knowledge loses correlations, while correlated histories reduce\n'
        '  to established symbolic/contingent methods. YAPA, the inspected 2018\n'
        '  DeepSec body, CSL 2026 hidden-input register synthesis, RESTler and an\n'
        '  APIphany abstract add precise strong-comparator obligations. No new\n'
        '  compiler/representation step or advantage threshold is selected.\n'
        '  [Eleven closure obligations](source-evidence/action-observation-closure-screen-v1/closure-obligations.json)\n'
        '  preserve actual legal string guesses, all public alternatives, task\n'
        '  bindings, safety, expiry and external approval distinctions. May\n'
        '  completion remains the main target; caller guarantee is diagnostic.\n'
        '  Eight query/result pairs pass a 27-file integrity check. The DeepSec\n'
        '  HTML 404, query 7 RESTler finds misresolved by the tool to YAPA, and\n'
        '  two rejected local patch preparations are retained; corrected exact\n'
        '  URL retrieval/context edits do not replace those records. No application\n'
        '  acquisition, installation, tests, archive replays, services or study\n'
        '  inference ran. AgentOps checkout path remains pending; do not retry\n'
        '  unchanged proxy-blocked acquisition. The next work requires an actual\n'
        '  extra source transformation/representation and fair discrimination\n'
        '  condition, rather than another renamed baseline.\n'
        '- Six mutable records were snapshotted under continuation-v3 after\n'
        '  verifying the prior v2 integrity inputs. New pre-edit/current audit\n'
        '  reports use v3/v0.4 paths; old reports/helpers are not overwritten.\n'
        '  CP7 evidence now includes the existing draft v0.3/integrity v2 audits.\n'
        '  Manuscript/reference/claim bytes remain unchanged; CP2 open, CP7\n'
        '  pending, goal active and checkpoint credit 5%.',
    ),
}
prepared = {}
for relative, (anchor, addition) in texts.items():
    original = (ROOT / relative).read_text(encoding='utf-8')
    assert original.count(anchor) == 1, relative
    prepared[relative] = original.replace(anchor, anchor + addition, 1)

checkpoint = read(ROOT / 'docs/research/checkpoint-status.json')
cp2 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP2')
cp7 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP7')
assert cp2['status'] == 'in_progress' and cp7['status'] == 'pending'
assert checkpoint['progress_percent'] == 5
assert checkpoint['novelty_demonstrated'] is checkpoint['human_review_completed'] is False
new_evidence = [
    'source-evidence/action-observation-closure-screen-v1/decision.md',
    'source-evidence/action-observation-closure-screen-v1/closure-obligations.json',
    'source-evidence/action-observation-closure-screen-v1/source-claim-ledger.json',
    'source-evidence/action-observation-closure-screen-v1/manifest.json',
    'source-evidence/action-observation-closure-screen-v1-verification.json',
]
for relative in new_evidence:
    assert relative not in cp2['evidence']
    receipt(ROOT / 'docs/research' / relative)
cp2['evidence'].extend(new_evidence)
cp2['source_leads']['action_observation_compiler'] = (
    'Screen v1: standard recipe/symbolic/synthesis overlap; eleven coverage obligations; no extra C1 step'
)
for relative in ['../../paper/draft-audit-v0.3.json', '../../paper/continuation-integrity-v2.json']:
    assert relative not in cp7['evidence']
    receipt(ROOT / 'docs/research' / relative)
    cp7['evidence'].append(relative)
prepared['docs/research/checkpoint-status.json'] = json.dumps(checkpoint, indent=2, ensure_ascii=False) + '\n'
draft_status = read(ROOT / 'paper/draft-status-v0.json')
assert draft_status['complete_paper'] is False and draft_status['checkpoint_progress_percent'] == 5
draft_status['development_source_screens']['action_observation_closure'] = (
    '../docs/research/source-evidence/action-observation-closure-screen-v1/decision.md'
)
prepared['paper/draft-status-v0.json'] = json.dumps(draft_status, indent=2, ensure_ascii=False) + '\n'
assert set(prepared) == set(RECORDS)

snapshots = []
for relative in RECORDS:
    original = ROOT / relative
    snapshot = SNAPSHOTS / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open('xb') as stream:
        stream.write(original.read_bytes())
    assert snapshot.read_bytes() == original.read_bytes()
    item = receipt(snapshot)
    snapshots.append({'original': relative, 'snapshot': item['path'],
                      'bytes': item['bytes'], 'sha256': item['sha256']})
stable = [
    receipt(ROOT / relative) for relative in [
        'paper/working-draft-v0.md', 'paper/claim-ledger-v0.json',
        'paper/references-v1.json', 'paper/references-v1.bib', 'paper/references-v1.md',
    ]
]
write_new(PRE, {
    'schema_version': 'continuation-pre-edit-integrity/3',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'prior_integrity_report': receipt(PRIOR),
    'prior_input_entries_checked': len(prior['checked_inputs']),
    'prior_current_records_checked': len(prior['current_records']),
    'distinct_prior_paths_checked': len({item['path'] for item in checks}),
    'verified_inputs': checks, 'mutable_record_snapshots': snapshots,
    'stable_paper_files': stable, 'new_screen_manifest': receipt(ROOT / screen_report['manifest']['path']),
    'changed_files_before_edit': [],
    'scope': 'Retained hashes and exact pre-edit snapshots; no tests, replay, application or inference.',
})
for relative, content in prepared.items():
    (ROOT / relative).write_text(content, encoding='utf-8', newline='\n')
for item in stable:
    assert receipt(ROOT / item['path']) == item
print(json.dumps({
    'status': 'updated', 'mutable_records_snapshotted': len(snapshots),
    'prior_input_entries_checked': len(prior['checked_inputs']),
    'prior_current_records_checked': len(prior['current_records']),
    'new_cp2_evidence_paths': len(new_evidence), 'new_cp7_existing_audit_paths': 2,
    'stable_paper_files_unchanged': len(stable), 'progress_percent': 5,
    'new_application_requests': 0, 'new_model_calls': 0,
}, indent=2))
