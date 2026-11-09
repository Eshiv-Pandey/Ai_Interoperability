"""Seal a formatted-source method screen; never execute application code."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'docs/research/source-evidence/action-observation-closure-screen-v1'
OUTPUT = ROOT / 'docs/research/source-evidence/action-observation-closure-screen-v1-verification.json'
MANIFEST = SCREEN / 'manifest.json'
if MANIFEST.exists() or OUTPUT.exists():
    raise SystemExit('Refusing to replace or repeat the sealed screen.')


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
coverage = read(SCREEN / 'closure-obligations.json')
queries = sorted(SCREEN.glob('*-query.json'))
responses = sorted(SCREEN.glob('*-tool-response.json'))
assert len(queries) == len(responses) == ledger['retrieval_pairs'] == 8
assert len(ledger['claims']) == 8 and len(coverage['obligations']) == 11
assert coverage['public_surface_coverage_complete'] is False
assert coverage['can_certify_supported'] is coverage['can_certify_unsupported'] is False
assert coverage['practical_inputs_include_private_tokens'] is False
assert ledger['progress_percent'] == 5
assert ledger['novelty_demonstrated'] is ledger['human_review_completed'] is False
assert ledger['candidate_implementations_or_performance_trials'] == 0
assert all(value == 0 for value in coverage['execution'].values())

json_checked = []
for path in sorted(SCREEN.glob('*.json')):
    read(path)
    json_checked.append(path.relative_to(ROOT).as_posix())
for query, response in zip(queries, responses):
    assert query.name.removesuffix('-query.json') == response.name.removesuffix('-tool-response.json')
    assert isinstance(read(query), dict)
    assert isinstance(read(response)['content'], list)

# Preserve and classify tool failures rather than treating global isError=false
# as a successful retrieval of every requested source.
failed_html = responses[1].read_text(encoding='utf-8')
assert '2211.03225v2' in failed_html and '404' in failed_html
misresolved = responses[6].read_text(encoding='utf-8')
assert 'Algorithm 1' in misresolved and '1005.0737' in misresolved
assert 'No matching text found' in misresolved
corrected = responses[7].read_text(encoding='utf-8')
assert 'RESTler.pdf' in corrected and 'DEPENDENCIES' in corrected

evidence_checked = []
for item in ledger['claims'] + coverage['obligations']:
    assert item['id'] and item['evidence']
    for relative in item['evidence']:
        path = (SCREEN / relative).resolve()
        receipt(path)
        evidence_checked.append(path.relative_to(ROOT).as_posix())

links_checked = []
for target in re.findall(r'\]\(([^)]+)\)', (SCREEN / 'decision.md').read_text(encoding='utf-8')):
    if target.startswith(('https://', 'http://')):
        continue
    path = (SCREEN / target.split('#', 1)[0]).resolve()
    receipt(path)
    links_checked.append(path.relative_to(ROOT).as_posix())

files = set(SCREEN.iterdir()) | {Path(__file__).resolve()}
files |= {(ROOT / relative).resolve() for relative in ledger['retained_local_inputs']}
assert all(path.is_file() for path in files)
manifest = {
    'schema_version': 'formatted-source-screen-manifest/1',
    'sealed_at_utc': datetime.now(UTC).isoformat(), 'retrieval_pairs': 8,
    'representation': 'JSON serialization of formatted web-tool query/results',
    'web_records_are_original_source_bytes': False,
    'original_remote_source_snapshots': 0,
    'files': [receipt(path) for path in sorted(files)],
    'scope': 'Root analytical method screen and source-fidelity obligations; no compiler, solver, test, archive replay, service, model inference or human review.',
    'claims': {'candidate_implementations_or_performance_trials': 0,
               'application_requests': 0, 'model_calls': 0,
               'qualified_second_domain': False, 'novelty_demonstrated': False,
               'human_review_completed': False, 'progress_percent': 5},
}
write_new(MANIFEST, manifest)
for item in read(MANIFEST)['files']:
    assert receipt(ROOT / item['path']) == item
report = {
    'schema_version': 'formatted-source-screen-verification/1',
    'checked_at_utc': datetime.now(UTC).isoformat(), 'status': 'passed',
    'manifest': receipt(MANIFEST), 'files_checked': len(files),
    'json_records_checked': len(json_checked), 'retrieval_pairs': 8,
    'claim_evidence_links_checked': len(evidence_checked),
    'local_document_links_checked': len(links_checked),
    'closure_obligations': 11, 'coverage_complete': False,
    'failed_html_and_misresolved_finds_retained': True,
    'local_patch_preparation_failures_retained': True,
    'application_execution': False, 'new_application_requests': 0,
    'new_model_calls': 0, 'new_tests': 0, 'new_archive_replays': 0,
    'checkpoint_progress_percent': 5,
    'scope': 'File hashes, JSON, evidence paths and failure retention only; no validation of scientific novelty or source-to-runtime completeness.',
}
write_new(OUTPUT, report)
print(json.dumps(report, indent=2))
