"""Audit current and historical evidence with explicit mutable-record snapshots."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'paper/continuation-integrity-v2.json'
if OUTPUT.exists():
    raise SystemExit('Refusing to replace the continuation integrity report.')


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def receipt(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), relative
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


pre = read('paper/continuation-pre-edit-integrity-v2.json')
assert pre['status'] == 'passed' and pre['changed_files_before_edit'] == []
mapping = {item['original']: item['snapshot'] for item in pre['mutable_record_snapshots']}
assert len(mapping) == 6
for item in pre['mutable_record_snapshots']:
    actual = receipt(item['snapshot'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']

historical = pre['source_reports']
current = [
    'docs/research/source-evidence/apcore-approval-screen-v2/manifest.json',
    'docs/research/source-evidence/agentops-screen-v1/manifest.json',
    'paper/draft-audit-v0.3.json',
]
checked = []
for report_path in historical + current:
    report = read(report_path)
    for entry in report['files']:
        actual_path = mapping.get(entry['path'], entry['path']) if report_path in historical else entry['path']
        actual = receipt(actual_path)
        assert actual['bytes'] == entry['bytes'] and actual['sha256'] == entry['sha256'], entry['path']
        checked.append({'report': report_path, 'original': entry['path'],
                        'checked_path': actual_path, 'sha256': actual['sha256'],
                        'historical_snapshot_used': actual_path != entry['path']})
prior = read(pre['prior_integrity_report'])
for entry in prior['records']:
    actual = receipt(mapping.get(entry['path'], entry['path']))
    assert actual['sha256'] == entry['sha256'], entry['path']

links_checked = []
documents = [
    'docs/research/source-evidence/apcore-approval-screen-v2/decision.md',
    'docs/research/source-evidence/agentops-screen-v1/decision.md',
    'docs/research/source-evidence/agentops-screen-v1/native-eligibility-preparation.md',
]
for relative in documents:
    path = ROOT / relative
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if target.startswith(('https://', 'http://')):
            continue
        linked = (path.parent / target.split('#', 1)[0]).resolve()
        assert linked.is_relative_to(ROOT) and linked.is_file(), (relative, target)
        links_checked.append(linked.relative_to(ROOT).as_posix())

for relative in ['docs/research/source-evidence/apcore-approval-screen-v2-verification.json',
                 'docs/research/source-evidence/agentops-screen-v1-verification.json']:
    value = read(relative)
    assert value['status'] == 'passed' and value['application_execution'] is False
    assert receipt(value['manifest']['path']) == value['manifest']
checkpoint = read('docs/research/checkpoint-status.json')
assert checkpoint['progress_percent'] == 5
assert checkpoint['novelty_demonstrated'] is checkpoint['human_review_completed'] is False
assert next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP2')['status'] == 'in_progress'
assert next(item for item in checkpoint['checkpoints'] if item['id'] == 'CP7')['status'] == 'pending'
probe = read('docs/research/source-evidence/agentops-screen-v1/git-pin-probe-v1.json')
assert probe['returncode'] == 128 and '127.0.0.1 port 9' in probe['stderr_utf8']
draft = read('paper/draft-audit-v0.3.json')
assert draft['status'] == 'passed' and draft['draft_words'] == 3357
assert draft['claims_with_evidence_paths'] == 19 and draft['new_model_calls'] == draft['new_service_requests'] == 0

report_paths = historical + current + [pre['prior_integrity_report'],
    'paper/continuation-pre-edit-integrity-v2.json',
    'docs/research/source-evidence/apcore-approval-screen-v2-verification.json',
    'docs/research/source-evidence/agentops-screen-v1-verification.json']
report = {
    'schema_version': 'continuation-retained-integrity/2',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'historical_file_entries_checked': sum(item['report'] in historical for item in checked),
    'current_file_entries_checked': sum(item['report'] in current for item in checked),
    'distinct_checked_paths': len({item['checked_path'] for item in checked}),
    'historical_entries_using_exact_mutable_snapshots': sum(item['historical_snapshot_used'] for item in checked),
    'mutable_snapshots': pre['mutable_record_snapshots'],
    'prior_report_records_checked': len(prior['records']),
    'local_screen_links_checked': len(links_checked),
    'checked_inputs': checked,
    'current_records': [receipt(name) for name in report_paths + list(mapping) +
                        ['scripts/audit_continuation_integrity_v2.py', 'scripts/update_continuation_records_v2.py']],
    'new_application_requests': 0, 'new_model_calls': 0,
    'new_git_metadata_probes': 1, 'git_probe_result': 'failed configured proxy; not application failure',
    'checkpoint_progress_percent': 5, 'goal_complete': False,
    'scope': 'Retained file hashes, explicit pre-edit snapshots, current draft/status and local link consistency. No new test, archive replay, native/bridge request, inference or human scientific review.'
}
with OUTPUT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in report.items() if key not in
                  ['checked_inputs', 'current_records', 'mutable_snapshots']}, indent=2))
