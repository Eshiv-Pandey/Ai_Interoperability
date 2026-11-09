"""Snapshot current records and integrate the pinned-source follow-up once."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / 'docs/research/snapshots/continuation-v4'
PRE = ROOT / 'paper/continuation-pre-edit-integrity-v4.json'
PRIOR = ROOT / 'paper/continuation-integrity-v3.json'
RECORDS = [
    'RESEARCH_WORKFLOW.md', 'docs/research/execution-handoff.md',
    'docs/research/implementation-novelty-gate.md', 'docs/research/cp2-review-packet-v1.md',
    'docs/research/checkpoint-status.json', 'paper/draft-status-v0.json',
]
if PRE.exists() or SNAPSHOTS.exists():
    raise SystemExit('Refusing to repeat or replace the v4 context update.')


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
for item in prior['historical_checks']:
    actual = receipt(ROOT / item['checked_path'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'], item['checked_path']
    checks.append(actual)
for item in prior['current_checks'] + prior['current_records']:
    actual = receipt(ROOT / item['path'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'], item['path']
    checks.append(actual)

screen_base = 'docs/research/source-evidence/agentops-por-followup-v1'
screen_report = read(ROOT / f'{screen_base}-verification.json')
assert screen_report['status'] == 'passed' and screen_report['files_checked'] == 39
assert screen_report['application_execution'] is False
assert receipt(ROOT / screen_report['manifest']['path']) == screen_report['manifest']
for item in read(ROOT / screen_report['manifest']['path'])['files']:
    assert receipt(ROOT / item['path']) == item, item['path']

additions = {
    'RESEARCH_WORKFLOW.md': (
        '## 1. Research direction and what changes',
        '\n\n**Pinned-source/POR follow-up (25 October):** the\n'
        '[versioned follow-up](docs/research/source-evidence/agentops-por-followup-v1/decision.md)\n'
        'web-resolves AgentOps v0.11.0 to a full commit and revalidates its\n'
        'upstream same-task confirmation/effect test, transaction and exact\n'
        'ADK2.10.0/A2A1.1.5 lock blocks. No checkout, install or native wire\n'
        'control exists here. The primary POR body already provides symbolic\n'
        'dependency, persistent/sleep and conditional-collapse methods; no extra\n'
        'C1 step is selected. Eleven query/result pairs pass a 39-file source\n'
        'integrity check. Retrieval failures and a handoff-derived unsuccessful\n'
        'browser acquisition receipt are retained. Original may target, human\n'
        'review requirements and 5% credit remain unchanged.',
    ),
    'docs/research/implementation-novelty-gate.md': (
        '## What the fresh source audit changes',
        '\n\nThe [AgentOps/POR follow-up](source-evidence/agentops-por-followup-v1/decision.md)\n'
        'resolves the former web release-pin uncertainty and inspects the\n'
        'same-task local-effect confirmation control at that pin. Local bytes,\n'
        'installation, actual card/wire profile, unchanged bridges and human\n'
        'task validity remain open. The primary POR v2 Definitions7-9 and\n'
        'Propositions5-8 already cover symbolic independence, persistent/sleep\n'
        'sets and conservative conditional collapsing. Their equivalence/final\n'
        'witness result is not automatically bounded safe may-completion; an\n'
        'ordinary monitor/product extension supplies no extra C1 step. No\n'
        'implementation or performance trial is selected. Eleven retained pairs\n'
        'and a 39-file audit add source integrity, not G1/G4/G5 credit.',
    ),
    'docs/research/cp2-review-packet-v1.md': (
        '## Claims currently rejected',
        '\n\n**Pinned-source/POR addendum (25 October):**\n'
        '[AgentOps release/source update](source-evidence/agentops-por-followup-v1/agentops-source-update.md)\n'
        'now resolves a full web commit and revalidates the upstream original-task\n'
        'confirmation, service and attributed-audit assertions. The test has not\n'
        'run here and does not alone assert exactly one new audit/no unrelated\n'
        'change. Acquisition, actual wire/profile, unchanged bridge and human\n'
        'task validity are still missing. The\n'
        '[POR comparator screen](source-evidence/agentops-por-followup-v1/por-comparator-screen.md)\n'
        'rejects generic symbolic/POR/conditional-collapse novelty. Eleven pairs\n'
        'pass a 39-file integrity check; access/lookup failures and recovered\n'
        'browser acquisition failure are retained. No additional C1 step,\n'
        'performance experiment, domain qualification or human review follows.',
    ),
    'docs/research/execution-handoff.md': (
        '**Latest continuation update (25 October 2026):**',
        '\n\n- [AgentOps/POR follow-up v1](source-evidence/agentops-por-followup-v1/decision.md)\n'
        '  web-resolves AgentOps v0.11.0 to\n'
        '  c806b7f1cd0042c9817c0a4c46d80a9a95a24293. Pinned MIT application,\n'
        '  upstream same-task DataPart confirmation test, guarded local SQLite\n'
        '  transaction/audit/idempotency and ADK2.10.0/A2A1.1.5 lock blocks are\n'
        '  inspected. Release notes explain the former Go/Python discrepancy\n'
        '  and disclose an Eval waiver. All are formatted excerpts, not a\n'
        '  checkout/original source bytes or installation. The test is unrun;\n'
        '  latest-audit assertions do not alone prove exactly one row/no unrelated\n'
        '  changes. Synthetic test identity is not authenticated human identity.\n'
        '- The primary POR v2 Sections3-6/Definitions7-9/Propositions5-8\n'
        '  already give symbolic dependency, persistent/sleep and conditional\n'
        '  collapse mechanisms. Generic POR or an ordinary task-monitor product\n'
        '  supplies no additional C1 step. Equivalence/final-witness correctness\n'
        '  is not automatically bounded safe may-completion or uniform policy\n'
        '  preservation. No candidate or advantage threshold is selected.\n'
        '- Eleven complete query/result JSON serializations pass a 39-file\n'
        '  integrity check; pair02 keeps the original settlement wrapper. All\n'
        '  HTML/DOI/click/find/subtree-URL failures remain retained. The browser\n'
        '  acquisition attempt from the recovered handoff opened a release tab\n'
        '  but lost its binding, then encountered focus timeouts and native app\n'
        '  approval timeout. Its task-specific receipt is recovered narrative,\n'
        '  not raw tool bytes. No archive downloaded, software executed or\n'
        '  settings changed. Stop unchanged browser/Git acquisition retries;\n'
        '  local checkout path remains pending. No application requests, tests,\n'
        '  installs, archive replays, solvers or study inference occurred.\n'
        '- Six mutable records are snapshotted under continuation-v4 before\n'
        '  this additive update. New pre-edit/current audit paths use v4/v0.5;\n'
        '  earlier reports/helpers/screens remain unchanged. CP7 now links\n'
        '  existing v0.4/v3 audits. The next useful step needs an actual extra\n'
        '  representation/transformation and fair discrimination condition,\n'
        '  alongside accessible pinned acquisition/native validity. CP2 open,\n'
        '  CP7 pending, original method route, goal active and credit 5%.',
    ),
}
prepared = {}
for relative, (anchor, addition) in additions.items():
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
    f'source-evidence/agentops-por-followup-v1/{name}' for name in [
        'decision.md', 'agentops-source-update.md', 'por-comparator-screen.md',
        'source-claim-ledger.json', 'retrieval-limitations.json',
        'browser-acquisition-failure-receipt.json', 'manifest.json',
    ]
] + ['source-evidence/agentops-por-followup-v1-verification.json']
for relative in new_evidence:
    assert relative not in cp2['evidence']
    receipt(ROOT / 'docs/research' / relative)
cp2['evidence'].extend(new_evidence)
cp2['source_leads']['agentops'] = (
    'v0.11.0 web full-commit pin; native-effect source/control revalidated; local bytes/install/wire/bridge and human validity open'
)
cp2['source_leads']['agentops_acquisition'] = (
    'Historical proxy Git failure and recovered browser binding/approval failures retained; no archive; local path pending'
)
cp2['source_leads']['partial_order_method'] = (
    'Primary symbolic POR/persistent/sleep/conditional-collapse overlap; augmented may semantics/cost obligations; no C1 step'
)
for relative in ['../../paper/draft-audit-v0.4.json', '../../paper/continuation-integrity-v3.json']:
    assert relative not in cp7['evidence']
    receipt(ROOT / 'docs/research' / relative)
    cp7['evidence'].append(relative)
prepared['docs/research/checkpoint-status.json'] = json.dumps(checkpoint, indent=2, ensure_ascii=False) + '\n'
draft_status = read(ROOT / 'paper/draft-status-v0.json')
assert draft_status['complete_paper'] is False and draft_status['checkpoint_progress_percent'] == 5
draft_status['development_source_screens']['agentops_pin_por_followup'] = (
    '../docs/research/source-evidence/agentops-por-followup-v1/decision.md'
)
prepared['paper/draft-status-v0.json'] = json.dumps(draft_status, indent=2, ensure_ascii=False) + '\n'
assert set(prepared) == set(RECORDS)

snapshots = []
for relative in RECORDS:
    snapshot = SNAPSHOTS / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open('xb') as stream:
        stream.write((ROOT / relative).read_bytes())
    assert snapshot.read_bytes() == (ROOT / relative).read_bytes()
    item = receipt(snapshot)
    snapshots.append({'original': relative, 'snapshot': item['path'],
                      'bytes': item['bytes'], 'sha256': item['sha256']})
stable = [receipt(ROOT / relative) for relative in [
    'paper/working-draft-v0.md', 'paper/claim-ledger-v0.json',
    'paper/references-v1.json', 'paper/references-v1.bib', 'paper/references-v1.md',
]]
write_new(PRE, {
    'schema_version': 'continuation-pre-edit-integrity/4',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'prior_integrity_report': receipt(PRIOR),
    'prior_input_entries_checked': len(prior['historical_checks']) + len(prior['current_checks']),
    'prior_current_records_checked': len(prior['current_records']),
    'distinct_prior_paths_checked': len({item['path'] for item in checks}),
    'verified_inputs': checks, 'mutable_record_snapshots': snapshots,
    'stable_paper_files': stable,
    'new_screen_manifest': receipt(ROOT / screen_report['manifest']['path']),
    'changed_files_before_edit': [],
    'scope': 'Retained hashes and exact pre-edit snapshots; no software tests, application or inference.',
})
for relative, content in prepared.items():
    (ROOT / relative).write_text(content, encoding='utf-8', newline='\n')
for item in stable:
    assert receipt(ROOT / item['path']) == item
print(json.dumps({
    'status': 'updated', 'mutable_records_snapshotted': len(snapshots),
    'prior_input_entries_checked': len(prior['historical_checks']) + len(prior['current_checks']),
    'prior_current_records_checked': len(prior['current_records']),
    'new_cp2_evidence_paths': len(new_evidence), 'new_cp7_existing_audit_paths': 2,
    'stable_paper_files_unchanged': len(stable), 'progress_percent': 5,
    'new_application_requests': 0, 'new_model_calls': 0,
}, indent=2))
