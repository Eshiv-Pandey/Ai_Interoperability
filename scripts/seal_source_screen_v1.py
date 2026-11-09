"""Seal/check formatted source-screen evidence; no downloads or service imports."""
import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/research/source-evidence'


def receipt(path):
    data = path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(), 'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_new(path, data):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--seal', action='store_true')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
screen = args.directory.resolve()
output = args.output.resolve()
if not screen.is_relative_to(BASE) or not screen.is_dir():
    raise SystemExit('Screen must be within the workspace source-evidence directory.')
if not output.is_relative_to(ROOT) or output.exists() or output.is_relative_to(screen):
    raise SystemExit('Verification output must be new, in the workspace and outside the sealed directory.')
manifest_path = screen / 'manifest.json'
if args.seal:
    if manifest_path.exists():
        raise SystemExit('Refusing to replace an existing screen manifest.')
    ledger = read(screen / 'source-claim-ledger.json')
    queries = sorted(screen.glob('*-query.json'))
    results = sorted(screen.glob('*-tool-response.json'))
    assert len(queries) == len(results) == ledger['retrieval_pairs']
    assert {p.name.removesuffix('-query.json') for p in queries} == {
        p.name.removesuffix('-tool-response.json') for p in results}
    assert ledger['scope']['model_calls'] == ledger['scope']['application_requests'] == 0
    assert ledger['scope']['novelty_demonstrated'] is False
    assert ledger['scope']['human_review_completed'] is False
    assert ledger['scope']['progress_percent'] == 5
    files = {p for p in screen.rglob('*') if p.is_file()} | {Path(__file__).resolve()}
    for relative in ledger['retained_local_inputs']:
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT) and path.is_file()
        files.add(path)
    for claim in ledger['claims']:
        assert claim['kind'] and claim['limit'] and claim['evidence']
        for relative in claim['evidence']:
            assert (screen / relative).resolve() in files
    write_new(manifest_path, {
        'schema_version':'formatted-source-screen-manifest/1',
        'sealed_at_utc':datetime.now(UTC).isoformat(), 'retrieval_pairs':len(queries),
        'representation':'JSON serialization of formatted web-tool query/results; some responses retain Promise settlement wrappers',
        'web_records_are_original_source_bytes':False,
        'original_remote_source_snapshots':0, 'claims':ledger['scope'],
        'files':[receipt(path) for path in sorted(files)],
        'limit':'Local retained-file integrity and claim-path closure only; no authenticity, complete source, runtime, novelty or human-validation claim.'})
manifest = read(manifest_path)
assert len({item['path'] for item in manifest['files']}) == len(manifest['files'])
for item in manifest['files']:
    path = (ROOT / item['path']).resolve()
    assert path.is_relative_to(ROOT) and receipt(path) == item, item['path']
    if path.suffix == '.json':
        read(path)
expected_local = {item['path'] for item in manifest['files'] if (ROOT / item['path']).is_relative_to(screen)}
actual_local = {path.relative_to(ROOT).as_posix() for path in screen.rglob('*') if path.is_file() and path != manifest_path}
assert expected_local == actual_local
report = {'schema_version':'formatted-source-screen-integrity/1',
          'checked_at_utc':datetime.now(UTC).isoformat(), 'status':'passed',
          'manifest':receipt(manifest_path), 'files_checked':len(manifest['files']),
          'retrieval_pairs':manifest['retrieval_pairs'], 'web_records_are_original_source_bytes':False,
          'application_execution':False, 'check_scope':'File hashes, JSON syntax and claim/evidence path closure'}
write_new(output, report)
print(json.dumps(report, indent=2))
