"""Seal source follow-up records; do not run imported application code."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'docs/research/source-evidence/agentops-por-followup-v1'
MANIFEST = SCREEN / 'manifest.json'
OUTPUT = ROOT / 'docs/research/source-evidence/agentops-por-followup-v1-verification.json'
if MANIFEST.exists() or OUTPUT.exists():
    raise SystemExit('Refusing to overwrite the sealed follow-up.')


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


ledger = read(SCREEN / 'source-claim-ledger.json')
assert ledger['retrieval_pairs'] == 11 and len(ledger['claims']) == 8
assert ledger['source']['resolved_web_commit'] == 'c806b7f1cd0042c9817c0a4c46d80a9a95a24293'
assert ledger['source']['a2a_sdk_lock'] == '1.1.5'
assert ledger['source']['google_adk_lock'] == '2.10.0'
assert ledger['source']['original_source_bytes_acquired'] is False
assert ledger['source']['local_git_pin_verified'] is False
assert ledger['progress_percent'] == 5 and ledger['may_completion_target_preserved'] is True
assert all(ledger[key] is False for key in [
    'novelty_demonstrated', 'qualified_second_domain',
    'human_review_completed', 'contribution_route_changed'])
assert all(value == 0 for value in ledger['execution'].values())

queries = sorted(SCREEN.glob('*-query.json'))
responses = sorted(SCREEN.glob('*-tool-response.json'))
assert len(queries) == len(responses) == 11
response_text = {}
for query, response in zip(queries, responses):
    assert query.name.removesuffix('-query.json') == response.name.removesuffix('-tool-response.json')
    assert isinstance(read(query), dict)
    result = read(response)
    if response.name.startswith('02-'):
        assert result['status'] == 'fulfilled'
        result = result['value']
    assert isinstance(result['content'], list)
    response_text[response.name[:2]] = '\n'.join(
        item['text'] for item in result['content'] if item['type'] == 'text')

assert 'non-retryable error' in response_text['02']
assert 'Internal Error' in response_text['04']
assert 'No matching text found' in response_text['06']
assert 'L757: name = "google-adk"\nL758: version = "2.10.0"' in response_text['08']
assert 'assert completed_task["taskId"] == task_id' in response_text['09']
assert 'assert service.status == "operational"' in response_text['09']
assert 'BEGIN IMMEDIATE' in response_text['09']
assert 'uq_audit_log_idempotency' in response_text['10']
assert 'Proposition 8.' in response_text['10'] and 'Proposition 7.' in response_text['11']
assert 'agents/python/AGENTS.md: (404) Not Found' in response_text['11']

browser = read(SCREEN / 'browser-acquisition-failure-receipt.json')
assert browser['original_tool_outputs_available_in_this_receipt'] is False
assert browser['archive_downloaded'] is browser['software_executed'] is False
assert browser['new_retry_performed_during_receipt'] is browser['settings_changed'] is False
assert browser['attempts'][-1]['outcome'] == 'Computer Use app approval timed out.'
assert len(read(SCREEN / 'retrieval-limitations.json')['failures']) == 6

evidence_links = []
for claim in ledger['claims']:
    assert claim['id'] and claim['claim'] and claim['limit'] and claim['evidence']
    for relative in claim['evidence']:
        evidence_links.append(receipt(SCREEN / relative)['path'])

document_links = []
for document in sorted(SCREEN.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        if target.startswith(('https://', 'http://', '#')):
            continue
        document_links.append(receipt(document.parent / target.split('#', 1)[0])['path'])

json_files = sorted(SCREEN.glob('*.json'))
for path in json_files:
    read(path)
files = set(SCREEN.iterdir()) | {Path(__file__).resolve()}
files |= {(ROOT / relative).resolve() for relative in ledger['retained_local_inputs']}
for report_name in ['agentops-screen-v1', 'action-observation-closure-screen-v1']:
    prior_report = read(ROOT / f'docs/research/source-evidence/{report_name}-verification.json')
    assert prior_report['status'] == 'passed'
    assert receipt(ROOT / prior_report['manifest']['path']) == prior_report['manifest']
    prior_manifest = read(ROOT / prior_report['manifest']['path'])
    for entry in prior_manifest['files']:
        assert receipt(ROOT / entry['path']) == entry, entry['path']

manifest = {
    'schema_version': 'formatted-source-screen-manifest/1',
    'sealed_at_utc': datetime.now(UTC).isoformat(), 'retrieval_pairs': 11,
    'representation': 'Complete JSON serializations of formatted web-tool query/results; pair02 retains settlement wrapper',
    'web_records_are_original_source_bytes': False, 'original_remote_source_snapshots': 0,
    'browser_receipt_is_recovered_narrative': True,
    'files': [receipt(path) for path in sorted(files)],
    'claims': {key: ledger[key] for key in [
        'progress_percent', 'novelty_demonstrated', 'qualified_second_domain',
        'human_review_completed', 'contribution_route_changed', 'may_completion_target_preserved']},
    'execution': ledger['execution'],
    'scope': 'Pinned formatted-source and analytical comparator screen; file/evidence integrity only.',
}
write_new(MANIFEST, manifest)
for entry in read(MANIFEST)['files']:
    assert receipt(ROOT / entry['path']) == entry, entry['path']
report = {
    'schema_version': 'formatted-source-screen-verification/1',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'manifest': receipt(MANIFEST), 'files_checked': len(files),
    'json_records_checked': len(json_files), 'retrieval_pairs': 11,
    'claim_evidence_links_checked': len(evidence_links),
    'local_document_links_checked': len(document_links),
    'prior_screens_verified_unchanged': 2,
    'settlement_wrapper_preserved': True, 'retrieval_failures_retained': True,
    'browser_failure_narrative_retained': True, 'original_source_bytes_acquired': False,
    'application_execution': False, 'new_application_requests': 0, 'new_model_calls': 0,
    'new_tests': 0, 'new_archive_replays': 0, 'new_installations': 0,
    'candidate_performance_trials': 0, 'checkpoint_progress_percent': 5,
    'scope': 'Hashes, JSON, exact source-excerpt checks, failure provenance and local links; no runtime, novelty or human scientific validation.',
}
write_new(OUTPUT, report)
print(json.dumps(report, indent=2))
