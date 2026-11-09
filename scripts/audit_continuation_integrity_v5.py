"""Verify retained v5 inputs, new manuscript and unchanged historical drafts."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'paper/continuation-integrity-v5.json'
if OUTPUT.exists():
    raise SystemExit('Refusing to replace the v5 continuation audit.')


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def receipt(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), relative
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


pre_path = 'paper/continuation-pre-edit-integrity-v5.json'
pre = read(pre_path)
assert pre['status'] == 'passed' and pre['changed_files_before_edit'] == []
mapping = {item['original']: item['snapshot'] for item in pre['mutable_record_snapshots']}
assert len(mapping) == 6
for item in pre['mutable_record_snapshots']:
    actual = receipt(item['snapshot'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']
assert receipt(pre['prior_integrity_report']['path']) == pre['prior_integrity_report']
historical_checks = []
for item in pre['verified_inputs']:
    checked_path = mapping.get(item['path'], item['path'])
    actual = receipt(checked_path)
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'], item['path']
    historical_checks.append({'original': item['path'], 'checked_path': checked_path,
                              'bytes': actual['bytes'], 'sha256': actual['sha256'],
                              'v5_snapshot_used': checked_path != item['path']})
assert len(historical_checks) == pre['prior_input_entries_checked'] + pre['prior_current_records_checked']
for item in pre['stable_paper_files']:
    assert receipt(item['path']) == item, item['path']
assert len(pre['stable_paper_files']) == 6

draft_path = 'paper/draft-audit-v1.json'
draft = read(draft_path)
assert draft['status'] == 'passed'
assert draft['draft'] == 'paper/working-draft-v1.md' and draft['draft_words'] == 4216
assert draft['claims_with_evidence_paths'] == 23 and draft['references'] == 18
assert draft['prior_reference_entries_preserved'] == 15
assert draft['new_service_requests'] == draft['new_model_calls'] == 0
assert draft['initial_v1_metadata_audit_failure_preserved'] == 'paper/draft-audit-initial-failure-v1.json'
current_checks = []
for item in draft['files']:
    assert receipt(item['path']) == item, item['path']
    current_checks.append({'report': draft_path, **item})
for name in ['action-observation-closure-screen-v1', 'agentops-por-followup-v1']:
    report_path = 'docs/research/source-evidence/' + name + '-verification.json'
    screen = read(report_path)
    assert screen['status'] == 'passed' and screen['application_execution'] is False
    assert receipt(screen['manifest']['path']) == screen['manifest']
    for item in read(screen['manifest']['path'])['files']:
        assert receipt(item['path']) == item, item['path']
        current_checks.append({'report': screen['manifest']['path'], **item})

checkpoint = read('docs/research/checkpoint-status.json')
cp2 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP2')
cp7 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP7')
assert cp2['status'] == 'in_progress' and cp7['status'] == 'pending'
assert checkpoint['progress_percent'] == 5
assert checkpoint['novelty_demonstrated'] is checkpoint['human_review_completed'] is False
assert cp7['latest_working_draft'] == '../../paper/working-draft-v1.md'
assert cp7['latest_draft_status'] == '../../paper/draft-status-v1.json'
assert '../../paper/draft-audit-v0.5.json' in cp7['evidence']
assert '../../paper/continuation-integrity-v4.json' in cp7['evidence']
evidence_paths = []
for cp in [cp2, cp7]:
    assert len(cp['evidence']) == len(set(cp['evidence']))
    for relative in cp['evidence']:
        path = (ROOT / 'docs/research' / relative).resolve().relative_to(ROOT).as_posix()
        evidence_paths.append(receipt(path)['path'])
links = []
documents = [path for path in mapping if path.endswith('.md')] + [
    'paper/working-draft-v1.md', 'paper/references-v2.md',
    'docs/research/source-evidence/paper-semantics-refresh-v1/change-note.md',
]
for relative in documents:
    document = ROOT / relative
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        if target.startswith(('https://', 'http://', '#')):
            continue
        path = (document.parent / target.split('#', 1)[0]).resolve().relative_to(ROOT).as_posix()
        links.append({'document': relative, 'target': receipt(path)['path']})
status = read('paper/draft-status-v1.json')
assert status['complete_paper'] is status['human_review_completed'] is False
assert status['checkpoint_progress_percent'] == 5 and status['bibliography']['entries'] == 18
failure = read('paper/draft-audit-initial-failure-v1.json')
assert failure['exit_code'] == 1 and failure['output_report_written'] is False
assert (ROOT / failure['preserved_source']).is_file()
assert 'AssertionError: cheval2018deepsec' in failure['error_text']
assert len(read('paper/claim-ledger-v1.json')['claims']) == 23
record_paths = list(mapping) + [
    'scripts/build_working_draft_v1.py', 'scripts/audit_paper_draft_v1.py',
    'scripts/audit_continuation_integrity_v5.py', pre_path,
    pre['prior_integrity_report']['path'], draft_path,
    'paper/working-draft-v1.md', 'paper/claim-ledger-v1.json',
    'paper/draft-status-v1.json', 'paper/references-v2.json',
    'paper/references-v2.bib', 'paper/references-v2.md',
    'paper/draft-audit-initial-source-v1.txt', 'paper/draft-audit-initial-failure-v1.json',
    'docs/research/source-evidence/paper-semantics-refresh-v1/change-note.md',
]
report = {
    'schema_version': 'continuation-retained-integrity/5',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'prior_input_entries_checked': pre['prior_input_entries_checked'],
    'prior_current_records_checked': pre['prior_current_records_checked'],
    'historical_entries_checked': len(historical_checks),
    'historical_entries_using_v5_snapshots': sum(item['v5_snapshot_used'] for item in historical_checks),
    'distinct_historical_paths_checked': len({item['checked_path'] for item in historical_checks}),
    'current_file_entries_checked': len(current_checks), 'current_source_screens_checked': 2,
    'mutable_snapshots': pre['mutable_record_snapshots'],
    'v0_paper_files_unchanged': len(pre['stable_paper_files']),
    'draft_words': draft['draft_words'], 'claims': 23, 'references': 18,
    'checkpoint_evidence_paths_checked': len(evidence_paths),
    'document_links_checked': len(links), 'metadata_audit_failure_preserved': True,
    'historical_checks': historical_checks, 'current_checks': current_checks,
    'current_records': [receipt(path) for path in record_paths],
    'new_application_requests': 0, 'new_model_calls': 0, 'new_tests': 0,
    'new_archive_replays': 0, 'new_installations': 0, 'candidate_performance_trials': 0,
    'novelty_demonstrated': False, 'human_review_completed': False,
    'checkpoint_progress_percent': 5, 'goal_complete': False,
    'scope': 'New manuscript/citations/claim links, exact pre-edit retention and unchanged historical sources; no compiler/theorem, tests, application, inference or scientific/human acceptance.',
}
with OUTPUT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in report.items() if key not in [
    'historical_checks', 'current_checks', 'current_records', 'mutable_snapshots',
]}, indent=2))
