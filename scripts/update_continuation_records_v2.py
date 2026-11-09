"""Preserve pre-edit context and update mutable research records without trials."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / 'docs/research/snapshots/continuation-v2'
PRE_AUDIT = ROOT / 'paper/continuation-pre-edit-integrity-v2.json'
RECORDS = [
    'RESEARCH_WORKFLOW.md',
    'docs/research/execution-handoff.md',
    'docs/research/implementation-novelty-gate.md',
    'docs/research/cp2-review-packet-v1.md',
    'docs/research/checkpoint-status.json',
    'paper/draft-status-v0.json',
]
MANIFESTS = [
    'docs/research/source-evidence/diagnostic-method-screen-v1/manifest.json',
    'docs/research/source-evidence/apcore-screen-v1/manifest.json',
    'paper/bibliography-audit-v1.1.json',
    'paper/draft-audit-v0.2.json',
]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


if PRE_AUDIT.exists() or SNAPSHOTS.exists():
    raise SystemExit('Refusing to repeat/replace this continuation update.')

entries = [entry for name in MANIFESTS for entry in read(name)['files']]
prior = read('paper/continuation-integrity-v1.json')
for entry in entries + prior['records']:
    assert digest(ROOT / entry['path']) == entry['sha256'], entry['path']
    if 'bytes' in entry:
        assert (ROOT / entry['path']).stat().st_size == entry['bytes']
snapshots = []
for relative in RECORDS:
    source = ROOT / relative
    destination = SNAPSHOTS / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())
    assert source.read_bytes() == destination.read_bytes()
    snapshots.append({'original': relative, 'snapshot': destination.relative_to(ROOT).as_posix(),
                      'bytes': destination.stat().st_size, 'sha256': digest(destination)})
write_new(PRE_AUDIT, {
    'schema_version': 'continuation-pre-edit-integrity/2',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'source_reports': MANIFESTS, 'prior_integrity_report': 'paper/continuation-integrity-v1.json',
    'file_entries_checked': len(entries),
    'distinct_files_checked': len({entry['path'] for entry in entries}),
    'prior_records_checked': len(prior['records']),
    'changed_files_before_edit': [], 'mutable_record_snapshots': snapshots,
    'scope': 'Exact retained hashes and pre-edit byte snapshots; no test, service, model or archive replay.'
})

updates = {
    'docs/research/execution-handoff.md': (
        '**New verified work in this continuation:**',
        '**Latest continuation update (25 October2026):**\n\n'
        '- [apcore approval screen v2](source-evidence/apcore-approval-screen-v2/decision.md)\n'
        '  pins the underlying core0.32.2 at234813b283913c58532cd5292d9058730b42dc67.\n'
        '  The gate recognizes/strips `_approval_token`; JSON TextPart/DataPart can\n'
        '  carry it. Real pending errors store approval ID in details, while the\n'
        '  selected A2A status branch emits only code/message text. This is a narrow\n'
        '  source projection lead, not whole-interface impossibility or native success.\n'
        '  CRM/email/cookbook examples lack a substantive persisted effect. A separate\n'
        '  AI assessment reduces observation-based winning to established belief/game\n'
        '  and relational symbolic methods; no extra C1 step or trial is selected.\n'
        '  Twelve new query/result pairs have a passing31-file integrity check.\n'
        '- [AgentOps source lead](source-evidence/agentops-screen-v1/decision.md)\n'
        '  identifies MIT Python application code with real local SQLite effects,\n'
        '  atomic approval/audit/idempotency and an upstream same-task DataPart\n'
        '  confirmation test using a deterministic model double. Infrastructure\n'
        '  actions are explicitly simulated; test/source were inspected, not run.\n'
        '  Main raw/blob/search views differ; no full commit or installation exists.\n'
        '  A once-only git ls-remote pin probe failed at configured127.0.0.1:9 proxy;\n'
        '  exact output is retained. Do not retry unchanged or alter proxy settings.\n'
        '  Seven query/result pairs and reused discovery have a passing22-file check.\n'
        '  [Native eligibility preparation](source-evidence/agentops-screen-v1/native-eligibility-preparation.md)\n'
        '  records the concrete next step; local checkout path is pending. No qualified\n'
        '  second domain, application request, inference or gate credit is added.\n'
        '- Six mutable pre-edit records are saved as exact snapshots under\n'
        '  `docs/research/snapshots/continuation-v2/`; the pre-edit integrity report\n'
        '  checks135 entries/117 distinct retained input files and seven prior records.\n\n'
        '**Earlier verified work in the preceding continuation:**'
    ),
    'RESEARCH_WORKFLOW.md': (
        '## 1. Research direction and what changes',
        '## 1. Research direction and what changes\n\n'
        '**Approval/domain continuation (25 October):** the\n'
        '[apcore approval screen v2](docs/research/source-evidence/apcore-approval-screen-v2/decision.md)\n'
        'adds a pinned underlying Phase B gate and a narrow pending-ID status\n'
        'projection lead; it establishes no native substantive domain or new C1\n'
        'procedure. The separately authored AI assessment preserves partial-observation\n'
        'game/symbolic comparator obligations and does not replace human review.\n'
        '[AgentOps](docs/research/source-evidence/agentops-screen-v1/decision.md) has\n'
        'source-level local SQLite effects and an upstream same-task confirmation\n'
        'test, but remains unqualified without a coherent pin, installed runtime,\n'
        'native wire evidence, unchanged bridge controls and independent task validity.\n'
        'Its once-only pin probe failed at the configured proxy; failure is retained\n'
        'and no network settings were changed. Source-screen integrity checks cover\n'
        '31 and22 files; CP2 stays open and verified credit remains5%.'
    ),
    'docs/research/implementation-novelty-gate.md': (
        '## What the fresh source audit changes',
        '## What the fresh source audit changes\n\n'
        'The [apcore approval v2 screen](source-evidence/apcore-approval-screen-v2/decision.md)\n'
        'traces real Phase B token dispatch/stripping and pending-ID details through\n'
        'the selected text status projection. It leaves public alternative recovery,\n'
        'native governed effect and whole-interface completeness open. A separate\n'
        'AI assessment finds observation-based winning is established belief/game\n'
        'and relational symbolic analysis; changed quantifiers supply no C1 step.\n'
        'The [AgentOps source lead](source-evidence/agentops-screen-v1/decision.md)\n'
        'has real local SQLite mutations/audit and an inspected same-task confirmation\n'
        'test. Simulated infrastructure scope, unpinned differing source views,\n'
        'blocked acquisition and unexecuted native/bridge validity keep the second\n'
        'domain unqualified. Neither31/22-file integrity check passes G1/G4/G5\n'
        'or human review. No candidate/performance trial or added credit.'
    ),
    'docs/research/cp2-review-packet-v1.md': (
        '## Claims currently rejected',
        '## Claims currently rejected\n\n'
        '**Approval/operations source addendum (25 October):**\n'
        '[apcore v2](source-evidence/apcore-approval-screen-v2/decision.md) pins\n'
        'core Phase B token handling and finds a narrow ID-details-to-text projection\n'
        'lead; input token submission and v0.3 compatibility remain source-valid\n'
        'alternatives, while full recovery/action closure and native effects are open.\n'
        'The [separate AI assessment](source-evidence/apcore-approval-screen-v2/independent-ai-assessment.md)\n'
        'rejects generic observation-based winning/probe planning as an additional\n'
        'C1 step. It is not human review.\n'
        '[AgentOps](source-evidence/agentops-screen-v1/decision.md) adds an inspected\n'
        'upstream same-task confirmation test with actual local SQLite mutation/audit;\n'
        'the effects simulate infrastructure, source views remain unpinned, and\n'
        'the configured proxy blocked the retained once-only pin probe. No test,\n'
        'native request, bridge case or inference ran. Passing31/22-file source\n'
        'integrity checks supply no domain or novelty credit. The working manuscript\n'
        'remains3,357 words/19 claims; earlier18-claim statements below describe its\n'
        'pre-bibliography version. CP2/CP7 remain incomplete at5%.'
    ),
}
for relative, (old, new) in updates.items():
    path = ROOT / relative
    content = path.read_text(encoding='utf-8')
    assert content.count(old) == 1, relative
    path.write_text(content.replace(old, new, 1), encoding='utf-8', newline='\n')

checkpoint = read('docs/research/checkpoint-status.json')
cp2 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP2')
new_evidence = [
    'source-evidence/apcore-approval-screen-v2/decision.md',
    'source-evidence/apcore-approval-screen-v2/source-claim-ledger.json',
    'source-evidence/apcore-approval-screen-v2/independent-ai-assessment.md',
    'source-evidence/apcore-approval-screen-v2/manifest.json',
    'source-evidence/apcore-approval-screen-v2-verification.json',
    'source-evidence/agentops-screen-v1/decision.md',
    'source-evidence/agentops-screen-v1/source-claim-ledger.json',
    'source-evidence/agentops-screen-v1/native-eligibility-preparation.md',
    'source-evidence/agentops-screen-v1/git-pin-probe-v1.json',
    'source-evidence/agentops-screen-v1/manifest.json',
    'source-evidence/agentops-screen-v1-verification.json',
    '../../paper/continuation-pre-edit-integrity-v2.json',
]
for relative in new_evidence:
    assert relative not in cp2['evidence']
    assert (ROOT / 'docs/research' / relative).resolve().is_file(), relative
cp2['evidence'].extend(new_evidence)
cp2['source_leads'] = {
    'apcore': 'Pinned Phase B/output projection source only; complete public recovery/native effect open',
    'agentops': 'Stateful local simulation candidate; full commit/checkout/runtime/native/bridge validity unestablished',
    'agentops_acquisition': 'Once-only metadata probe failed configured proxy; local checkout path pending',
    'observation_method': 'Separate AI screen found standard partial-observation/game/symbolic reduction; no C1 step',
}
assert checkpoint['progress_percent'] == 5
assert checkpoint['novelty_demonstrated'] is checkpoint['human_review_completed'] is False
(ROOT / 'docs/research/checkpoint-status.json').write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')

status = read('paper/draft-status-v0.json')
status['development_source_screens'] = {
    'apcore_approval': '../docs/research/source-evidence/apcore-approval-screen-v2/decision.md',
    'agentops_lead': '../docs/research/source-evidence/agentops-screen-v1/decision.md',
    'effect_on_manuscript': 'No manuscript/references/claims edit; method/evaluation/human gates remain open',
    'new_application_requests': 0,
    'new_model_calls': 0,
}
assert status['complete_paper'] is False and status['checkpoint_progress_percent'] == 5
(ROOT / 'paper/draft-status-v0.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'status': 'updated', 'pre_edit_integrity': PRE_AUDIT.relative_to(ROOT).as_posix(),
                  'mutable_snapshots': len(snapshots), 'prior_file_entries_checked': len(entries),
                  'new_cp2_evidence_paths': len(new_evidence), 'progress_percent': 5,
                  'application_requests': 0, 'model_calls': 0}, indent=2))
