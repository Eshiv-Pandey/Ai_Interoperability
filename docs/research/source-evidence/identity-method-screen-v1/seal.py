"""Seal or verify this source screen without network or service execution."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'manifest.json'
SOURCES = {
    'amirk-handles.ts': 'external/a2a-to-mcp/src/handles.ts',
    'amirk-task-store.ts': 'external/a2a-to-mcp/src/tasks/store.ts',
    'amirk-envelope.ts': 'external/a2a-to-mcp/src/envelope.ts',
    'amirk-config.ts': 'external/a2a-to-mcp/src/config.ts',
    'amirk-a2a-client.ts': 'external/a2a-to-mcp/src/a2a-client.ts',
    'amirk-LICENSE': 'external/a2a-to-mcp/LICENSE',
    'mgcrea-peer.ts': 'external/mcp-a2a/src/client/peer.ts',
    'mgcrea-tasks.ts': 'external/mcp-a2a/src/store/tasks.ts',
    'mgcrea-paths.ts': 'external/mcp-a2a/src/store/paths.ts',
    'mgcrea-LICENSE': 'external/mcp-a2a/LICENSE',
}
TERMS = {
    'amirk-handles.ts': ['#newHandle()', '#forget(', '#isExpired(', 'delete(handle', 'sweep()'],
    'amirk-task-store.ts': ['mintFor(alias', 'const key =', 'record.terminal', 'delete(handle'],
    'amirk-envelope.ts': ['mintContext(alias', '.mintFor('],
    'amirk-config.ts': ['ALIAS_PATTERN'],
    'amirk-a2a-client.ts': ['buildUserMessage', 'messageId: randomUUID'],
    'mgcrea-peer.ts': ['normalizeBase =', 'randomId =', 'messageId: randomId'],
    'mgcrea-tasks.ts': ['pathFor(taskId', 'isSafeId(taskId)'],
    'mgcrea-paths.ts': ['SAFE_ID =', 'assertSafeId =', 'isSafeId ='],
}

def entry(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}

def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

if '--seal' in sys.argv:
    if MANIFEST.exists() or (HERE / 'local-sources').exists():
        raise SystemExit('Refusing to replace a manifest or snapshots.')
    queries = sorted(HERE.glob('*.query.json'))
    results = sorted(HERE.glob('*.result.json'))
    assert len(queries) == len(results) == 4
    assert {p.name[:-11] for p in queries} == {p.name[:-12] for p in results}
    (HERE / 'local-sources').mkdir()
    index = []
    for name, source in SOURCES.items():
        data = (ROOT / source).read_bytes()
        destination = HERE / 'local-sources' / name
        with destination.open('xb') as stream:
            stream.write(data)
        lines = data.decode('utf-8').splitlines()
        index.append({'source': source, 'snapshot': entry(destination),
                      'selected_lines': [{'line': i, 'text': line}
                                         for i, line in enumerate(lines, 1)
                                         if any(term in line for term in TERMS.get(name, []))]})
    write_new(HERE / 'source-index.json', {'schema_version':'identity-screen-source-index/1',
                                         'files':index, 'claim_limit':'Original local bytes and line anchors; no runtime.'})
    files = sorted(p for p in HERE.rglob('*') if p.is_file())
    write_new(MANIFEST, {'schema_version':'identity-screen-local-manifest/1',
                        'sealed_at_utc':datetime.now(UTC).isoformat(), 'retrieval_pairs':4,
                        'web_records_are_original_source_bytes':False,
                        'local_snapshots_are_original_bytes':True,
                        'files':[entry(p) for p in files], 'source_mapping':SOURCES,
                        'claim_limit':'Local source-screen integrity; no algorithm/runtime/novelty verification.'})

manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
paths = [item['path'] for item in manifest['files']]
assert len(paths) == len(set(paths))
for item in manifest['files']:
    path = (ROOT / item['path']).resolve()
    assert path.is_relative_to(ROOT) and entry(path) == item, item['path']
    if path.suffix == '.json':
        json.loads(path.read_text(encoding='utf-8'))
for name, source in SOURCES.items():
    assert (HERE / 'local-sources' / name).read_bytes() == (ROOT / source).read_bytes()
report = {'schema_version':'identity-screen-integrity-check/1',
          'checked_at_utc':datetime.now(UTC).isoformat(), 'status':'passed',
          'manifest':entry(MANIFEST), 'files_checked':len(paths),
          'retrieval_pairs':4, 'source_snapshots_checked':len(SOURCES),
          'runtime_executed':False, 'scope':'file hashes, JSON syntax and original local byte equality'}
if '--output' in sys.argv:
    output = Path(sys.argv[sys.argv.index('--output') + 1]).resolve()
    assert output.is_relative_to(ROOT)
    write_new(output, report)
print(json.dumps(report, indent=2))
