"""Verify the v3 context update, historical snapshots and sealed screen."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'paper/continuation-integrity-v3.json'
if OUTPUT.exists():
    raise SystemExit('Refusing to replace the v3 continuation audit.')


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def receipt(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), relative
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


pre_path = 'paper/continuation-pre-edit-integrity-v3.json'
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
    actual_path = mapping.get(item['path'], item['path'])
    actual = receipt(actual_path)
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'], item['path']
    historical_checks.append({'original': item['path'], 'checked_path': actual_path,
                              'bytes': actual['bytes'], 'sha256': actual['sha256'],
                              'v3_snapshot_used': actual_path != item['path']})
assert len(historical_checks) == pre['prior_input_entries_checked'] + pre['prior_current_records_checked']
for item in pre['stable_paper_files']:
    assert receipt(item['path']) == item, item['path']

screen_report_path = 'docs/research/source-evidence/action-observation-closure-screen-v1-verification.json'
screen_report = read(screen_report_path)
assert screen_report['status'] == 'passed' and screen_report['files_checked'] == 27
assert screen_report['application_execution'] is False and screen_report['coverage_complete'] is False
assert screen_report['new_application_requests'] == screen_report['new_model_calls'] == 0
assert receipt(screen_report['manifest']['path']) == screen_report['manifest'] == pre['new_screen_manifest']
draft_path = 'paper/draft-audit-v0.4.json'
draft = read(draft_path)
assert draft['status'] == 'passed'
assert draft['draft_words'] == 3357 and draft['claims_with_evidence_paths'] == 19
assert draft['new_service_requests'] == draft['new_model_calls'] == 0
current_checks = []
for report_path in [screen_report['manifest']['path'], draft_path]:
    for item in read(report_path)['files']:
        assert receipt(item['path']) == item, item['path']
        current_checks.append({'report': report_path, **item})

checkpoint = read('docs/research/checkpoint-status.json')
cp2 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP2')
cp7 = next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP7')
assert checkpoint['progress_percent'] == 5
assert checkpoint['novelty_demonstrated'] is checkpoint['human_review_completed'] is False
assert cp2['status'] == 'in_progress' and cp7['status'] == 'pending'
evidence_paths_checked = []
for cp in [cp2, cp7]:
    assert len(cp['evidence']) == len(set(cp['evidence']))
    for relative in cp['evidence']:
        path = (ROOT / 'docs/research' / relative).resolve()
        actual = receipt(path.relative_to(ROOT).as_posix())
        evidence_paths_checked.append(actual['path'])
assert '../../paper/draft-audit-v0.3.json' in cp7['evidence']
assert '../../paper/continuation-integrity-v2.json' in cp7['evidence']

markdown_links_checked = []
for relative in mapping:
    if not relative.endswith('.md'):
        continue
    document = ROOT / relative
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        if target.startswith(('https://', 'http://', '#')):
            continue
        path = (document.parent / target.split('#', 1)[0]).resolve()
        actual = receipt(path.relative_to(ROOT).as_posix())
        markdown_links_checked.append({'document': relative, 'target': actual['path']})

draft_status = read('paper/draft-status-v0.json')
assert draft_status['complete_paper'] is False and draft_status['checkpoint_progress_percent'] == 5
assert draft_status['human_review_completed'] is False
lead = draft_status['development_source_screens']['action_observation_closure']
assert receipt((ROOT / 'paper' / lead).resolve().relative_to(ROOT).as_posix())['path'].endswith('/decision.md')
scripts = ['scripts/seal_action_observation_screen_v1.py',
           'scripts/update_continuation_records_v3.py', 'scripts/audit_continuation_integrity_v3.py']
record_paths = list(mapping) + scripts + [pre_path, pre['prior_integrity_report']['path'],
    screen_report_path, screen_report['manifest']['path'], draft_path]
report = {
    'schema_version': 'continuation-retained-integrity/3',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'prior_input_entries_checked': pre['prior_input_entries_checked'],
    'prior_current_records_checked': pre['prior_current_records_checked'],
    'historical_entries_checked': len(historical_checks),
    'historical_entries_using_v3_snapshots': sum(item['v3_snapshot_used'] for item in historical_checks),
    'distinct_historical_paths_checked': len({item['checked_path'] for item in historical_checks}),
    'current_file_entries_checked': len(current_checks),
    'current_screen_files_checked': screen_report['files_checked'],
    'mutable_snapshots': pre['mutable_record_snapshots'],
    'stable_paper_files_unchanged': len(pre['stable_paper_files']),
    'checkpoint_evidence_paths_checked': len(evidence_paths_checked),
    'edited_markdown_links_checked': len(markdown_links_checked),
    'historical_checks': historical_checks, 'current_checks': current_checks,
    'current_records': [receipt(relative) for relative in record_paths],
    'new_application_requests': 0, 'new_model_calls': 0, 'new_tests': 0,
    'new_archive_replays': 0, 'new_git_metadata_probes': 0,
    'novelty_demonstrated': False, 'human_review_completed': False,
    'checkpoint_progress_percent': 5, 'goal_complete': False,
    'scope': 'Retained hashes, explicit pre-edit snapshots, current document/status links and sealed-screen consistency. No tests, application execution, archive replay, inference or human scientific review.',
}
with OUTPUT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in report.items() if key not in
                  ['historical_checks', 'current_checks', 'current_records', 'mutable_snapshots']}, indent=2))
