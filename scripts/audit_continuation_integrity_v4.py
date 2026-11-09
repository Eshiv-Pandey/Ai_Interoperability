"""Verify v4 retention, current follow-up and updated checkpoint links."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'paper/continuation-integrity-v4.json'
if OUTPUT.exists():
    raise SystemExit('Refusing to replace the v4 continuation audit.')


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def receipt(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), relative
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


pre_path = 'paper/continuation-pre-edit-integrity-v4.json'
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
    historical_checks.append({
        'original': item['path'], 'checked_path': checked_path,
        'bytes': actual['bytes'], 'sha256': actual['sha256'],
        'v4_snapshot_used': checked_path != item['path'],
    })
assert len(historical_checks) == pre['prior_input_entries_checked'] + pre['prior_current_records_checked']
for item in pre['stable_paper_files']:
    assert receipt(item['path']) == item, item['path']

screen_report_path = 'docs/research/source-evidence/agentops-por-followup-v1-verification.json'
screen = read(screen_report_path)
assert screen['status'] == 'passed' and screen['files_checked'] == 39
assert screen['retrieval_pairs'] == 11 and screen['application_execution'] is False
assert screen['original_source_bytes_acquired'] is False
assert screen['new_application_requests'] == screen['new_model_calls'] == screen['new_installations'] == 0
assert receipt(screen['manifest']['path']) == screen['manifest'] == pre['new_screen_manifest']
draft_path = 'paper/draft-audit-v0.5.json'
draft = read(draft_path)
assert draft['status'] == 'passed' and draft['draft_words'] == 3357
assert draft['claims_with_evidence_paths'] == 19
assert draft['new_service_requests'] == draft['new_model_calls'] == 0
current_checks = []
for report_path in [screen['manifest']['path'], draft_path]:
    for item in read(report_path)['files']:
        assert receipt(item['path']) == item, item['path']
        current_checks.append({'report': report_path, **item})

checkpoint = read('docs/research/checkpoint-status.json')
cp2 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP2')
cp7 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP7')
assert checkpoint['progress_percent'] == 5
assert checkpoint['novelty_demonstrated'] is checkpoint['human_review_completed'] is False
assert cp2['status'] == 'in_progress' and cp7['status'] == 'pending'
assert 'web full-commit' in cp2['source_leads']['agentops']
evidence_paths_checked = []
for cp in [cp2, cp7]:
    assert len(cp['evidence']) == len(set(cp['evidence']))
    for relative in cp['evidence']:
        path = (ROOT / 'docs/research' / relative).resolve()
        evidence_paths_checked.append(receipt(path.relative_to(ROOT).as_posix())['path'])
assert '../../paper/draft-audit-v0.4.json' in cp7['evidence']
assert '../../paper/continuation-integrity-v3.json' in cp7['evidence']
markdown_links_checked = []
for relative in mapping:
    if not relative.endswith('.md'):
        continue
    document = ROOT / relative
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        if target.startswith(('https://', 'http://', '#')):
            continue
        path = (document.parent / target.split('#', 1)[0]).resolve()
        markdown_links_checked.append({
            'document': relative, 'target': receipt(path.relative_to(ROOT).as_posix())['path'],
        })
draft_status = read('paper/draft-status-v0.json')
assert draft_status['complete_paper'] is False and draft_status['checkpoint_progress_percent'] == 5
assert draft_status['human_review_completed'] is False
lead = draft_status['development_source_screens']['agentops_pin_por_followup']
assert receipt((ROOT / 'paper' / lead).resolve().relative_to(ROOT).as_posix())['path'].endswith('/decision.md')
scripts = [
    'scripts/seal_agentops_por_followup_v1.py',
    'scripts/update_continuation_records_v4.py', 'scripts/audit_continuation_integrity_v4.py',
]
record_paths = list(mapping) + scripts + [
    pre_path, pre['prior_integrity_report']['path'], screen_report_path, screen['manifest']['path'], draft_path,
]
report = {
    'schema_version': 'continuation-retained-integrity/4',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'prior_input_entries_checked': pre['prior_input_entries_checked'],
    'prior_current_records_checked': pre['prior_current_records_checked'],
    'historical_entries_checked': len(historical_checks),
    'historical_entries_using_v4_snapshots': sum(item['v4_snapshot_used'] for item in historical_checks),
    'distinct_historical_paths_checked': len({item['checked_path'] for item in historical_checks}),
    'current_file_entries_checked': len(current_checks),
    'current_screen_files_checked': screen['files_checked'],
    'mutable_snapshots': pre['mutable_record_snapshots'],
    'stable_paper_files_unchanged': len(pre['stable_paper_files']),
    'checkpoint_evidence_paths_checked': len(evidence_paths_checked),
    'edited_markdown_links_checked': len(markdown_links_checked),
    'historical_checks': historical_checks, 'current_checks': current_checks,
    'current_records': [receipt(relative) for relative in record_paths],
    'new_application_requests': 0, 'new_model_calls': 0, 'new_tests': 0,
    'new_archive_replays': 0, 'new_git_metadata_probes': 0, 'new_installations': 0,
    'novelty_demonstrated': False, 'human_review_completed': False,
    'checkpoint_progress_percent': 5, 'goal_complete': False,
    'scope': 'Retained hashes, exact pre-edit snapshots, current links and source-screen consistency; no application execution, tests, inference, novelty or human review.',
}
with OUTPUT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in report.items() if key not in [
    'historical_checks', 'current_checks', 'current_records', 'mutable_snapshots',
]}, indent=2))
