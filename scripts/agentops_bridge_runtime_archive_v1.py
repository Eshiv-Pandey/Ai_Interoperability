"""Archive and materialize an exact installed Node dependency graph; no install."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

MAX_BYTES = 256 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if (not isinstance(name, str) or not name or path.is_absolute() or '\\' in name
            or ':' in name or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Unsafe archive path: ' + str(name))
    return path


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def check_graph(graph):
    if graph.get('schema_version') != 'agentops-bridge-runtime-graph/1' or graph.get('status') != 'graph_pinned_not_materialized':
        raise ValueError('Passed runtime graph required')
    nodes = {n['id']: n for n in graph['nodes']}
    if len(nodes) != len(graph['nodes']) or not nodes:
        raise ValueError('Unique graph nodes required')
    if any(row['from'] not in nodes for row in graph['edges'] + graph['missing_optional']):
        raise ValueError('Unknown dependency source node')
    expected = []
    for node in graph['nodes']:
        if not re.fullmatch(r'p[0-9]{3}', node['id']) or node['destination'] != 'nodes/' + node['id'] + '/package':
            raise ValueError('Invalid node destination')
        for row in node['files']:
            safe_name(row['path'])
            expected.append({'path': node['destination'] + '/' + row['path'],
                'source': node['original_root'] + '/' + row['path'], 'bytes': row['bytes'], 'sha256': row['sha256']})
        declarations = {r['name']: r for r in node['declared_dependencies']}
        selected = [r for r in graph['edges'] if r['from'] == node['id']]
        absent = [r for r in graph['missing_optional'] if r['from'] == node['id']]
        if len(selected) + len(absent) != len(declarations) or {r['name'] for r in selected + absent} != set(declarations):
            raise ValueError('Omitted or duplicate dependency resolution')
        for edge in selected + absent:
            if {k: edge[k] for k in ('name', 'declarations', 'optional')} != declarations[edge['name']]:
                raise ValueError('Changed dependency declaration')
            name = edge['name']
            safe_name(name)
            if not re.fullmatch(r'(?:@[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+', name):
                raise ValueError('Invalid package name')
        if any(r.get('to') not in nodes for r in selected) or any(r['optional'] is not True for r in absent):
            raise ValueError('Invalid resolved/absent edge')
    if graph['files'] != expected or len({r['path'] for r in expected}) != len(expected):
        raise ValueError('Complete unique graph file list required')
    if graph['total_bytes'] != sum(r['bytes'] for r in expected) or not 0 < graph['total_bytes'] <= MAX_BYTES:
        raise ValueError('Invalid bounded runtime size')
    if {r['alias'] for r in graph['roots']} != {'a2a-to-mcp', 'mcp-a2a'} or len(graph['roots']) != 2:
        raise ValueError('Exactly the two bridge roots required')
    if any(r['node'] not in nodes for r in graph['roots']):
        raise ValueError('Unknown root node')
    return nodes


def pack(directory):
    raw_graph = (directory / 'graph.json').read_bytes()
    graph = json.loads(raw_graph)
    check_graph(graph)
    root = Path(graph['original_workspace']).resolve()
    target = directory / 'runtime.zip'
    report = {'schema_version': 'agentops-bridge-runtime-archive/1', 'status': 'failed', 'started_at_utc': now(),
              'graph_sha256': sha(raw_graph), 'application_requests': 0, 'live_model_calls': 0, 'installations': 0}
    try:
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr('graph.json', raw_graph)
            for row in graph['files']:
                safe_name(row['source'])
                source = (root / row['source']).resolve()
                if not source.is_relative_to(root) or not source.is_file():
                    raise ValueError('Source outside workspace or missing')
                raw = source.read_bytes()
                if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                    raise ValueError('Changed pinned source: ' + row['source'])
                archive.writestr(row['path'], raw)
        report.update(status='archive_verified', archive='runtime.zip', bytes=target.stat().st_size,
                      archive_sha256=sha(target.read_bytes()), package_count=len(graph['nodes']), files=len(graph['files']))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['finished_at_utc'] = now()
    write_new(directory / 'archive.json', report)
    return report


def materialize(directory, replica, target):
    if sys.platform != 'linux':
        raise ValueError('Materialize inside Linux')
    if (not replica.is_absolute() or replica.is_symlink() or not replica.is_dir()
            or not replica.name.startswith('agentops-research-v7-')):
        raise ValueError('Expected existing original Linux replica')
    if target != replica / 'external/runtime-agentops-bridges-v1' or target.exists() or target.is_symlink():
        raise ValueError('New exact runtime destination required')
    if (target.parent.is_symlink() or target.parent.resolve() != replica.resolve() / 'external'):
        raise ValueError('Runtime parent must remain within replica')
    archive_row = json.loads((directory / 'archive.json').read_bytes())
    archive_path = directory / 'runtime.zip'
    raw_graph = (directory / 'graph.json').read_bytes()
    if (archive_row['status'] != 'archive_verified' or archive_row['graph_sha256'] != sha(raw_graph)
            or archive_row['archive_sha256'] != sha(archive_path.read_bytes()) or archive_row['bytes'] != archive_path.stat().st_size):
        raise ValueError('Archive/graph seal mismatch')
    graph = json.loads(raw_graph)
    nodes = check_graph(graph)
    expected = {r['path']: r for r in graph['files']}
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len({r.filename for r in infos}) != len(infos) or {r.filename for r in infos} != set(expected) | {'graph.json'}:
            raise ValueError('Archive entry set differs')
        for info in infos:
            safe_name(info.filename)
            if info.is_dir() or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Only regular archive files allowed')
            expected_size = len(raw_graph) if info.filename == 'graph.json' else expected[info.filename]['bytes']
            if info.file_size != expected_size or info.flag_bits & 1:
                raise ValueError('Archive declared size/encryption mismatch')
        if archive.read('graph.json') != raw_graph:
            raise ValueError('Archived graph differs')
        target.mkdir(exist_ok=False)
        report = {'schema_version': 'agentops-bridge-runtime-materialization/1', 'status': 'failed',
            'started_at_utc': now(), 'runtime_root': str(target), 'archive_sha256': archive_row['archive_sha256'],
            'graph_sha256': archive_row['graph_sha256'], 'application_requests': 0, 'live_model_calls': 0,
            'installations': 0, 'links': [], 'bridges': {}}
        try:
            for name, row in expected.items():
                raw = archive.read(name)
                if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                    raise ValueError('Archive content differs: ' + name)
                dest = target / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as stream:
                    stream.write(raw)
            with (target / 'graph.json').open('xb') as stream:
                stream.write(raw_graph)
            def link(name, destination):
                path = target / name
                resolved_target = target / destination
                path.parent.mkdir(parents=True, exist_ok=True)
                rel = os.path.relpath(resolved_target, path.parent)
                if not (path.parent / rel).resolve().is_relative_to(target.resolve()):
                    raise ValueError('Dependency link escapes runtime')
                path.symlink_to(rel, target_is_directory=True)
                report['links'].append({'path': name, 'target': rel, 'resolved': destination})
            for edge in graph['edges']:
                link(nodes[edge['from']]['destination'] + '/node_modules/' + edge['name'], nodes[edge['to']]['destination'])
            for item in graph['roots']:
                alias = 'external/' + item['alias']
                link(alias, nodes[item['node']]['destination'])
                report['bridges'][item['alias']] = {'package_root': str(target / alias),
                    'cli': str(target / alias / 'dist/cli.js'), 'entry': str(target / alias / 'dist/index.js')}
            report.update(status='materialized_import_check_pending', packages=len(nodes),
                          files=len(expected), bytes=graph['total_bytes'])
        except Exception as error:
            report['error'] = f'{type(error).__name__}: {error}'
        report['finished_at_utc'] = now()
        write_new(target / 'materialization.json', report)
    return report


def verify_runtime(runtime_root, graph, materialization):
    """Check live runtime against externally sealed graph and materialization objects.

    Callers must load these two objects from pinned inputs, not trust live copies.
    Does not import packages, start services, or follow package dependency links.
    """
    nodes = check_graph(graph)
    if runtime_root.is_symlink() or not runtime_root.is_dir():
        raise ValueError('Regular runtime root required')
    if (materialization['status'] != 'materialized_import_check_pending'
            or materialization['runtime_root'] != str(runtime_root)
            or json.loads((runtime_root / 'graph.json').read_bytes()) != graph
            or json.loads((runtime_root / 'materialization.json').read_bytes()) != materialization):
        raise ValueError('Live runtime metadata differs from pinned inputs')
    if sha((runtime_root / 'graph.json').read_bytes()) != materialization['graph_sha256']:
        raise ValueError('Live graph byte hash differs')
    expected_materialization_bytes = (json.dumps(materialization, indent=2) + '\n').encode('utf-8')
    if (runtime_root / 'materialization.json').read_bytes() != expected_materialization_bytes:
        raise ValueError('Live materialization receipt bytes differ')
    expected_links = {}
    for edge in graph['edges']:
        name = nodes[edge['from']]['destination'] + '/node_modules/' + edge['name']
        expected_links[name] = nodes[edge['to']]['destination']
    for row in graph['roots']:
        expected_links['external/' + row['alias']] = nodes[row['node']]['destination']
    if (len(materialization['links']) != len(expected_links)
            or {r['path']: r['resolved'] for r in materialization['links']} != expected_links):
        raise ValueError('Materialization link set differs from graph')
    expected_files = {r['path'] for r in graph['files']} | {'graph.json', 'materialization.json'}
    actual_files, actual_links = set(), set()
    for folder, directories, files in os.walk(runtime_root, followlinks=False):
        for name in directories + files:
            path = Path(folder) / name
            relative = path.relative_to(runtime_root).as_posix()
            if path.is_symlink():
                if relative not in expected_links:
                    raise ValueError('Unexpected runtime symlink: ' + relative)
                expected = (runtime_root / expected_links[relative]).resolve()
                if path.resolve() != expected or not expected.is_relative_to(runtime_root.resolve()):
                    raise ValueError('Changed runtime link target: ' + relative)
                link_row = next(r for r in materialization['links'] if r['path'] == relative)
                if os.readlink(path) != link_row['target']:
                    raise ValueError('Changed literal runtime link: ' + relative)
                actual_links.add(relative)
            elif path.is_file():
                actual_files.add(relative)
            elif not path.is_dir():
                raise ValueError('Nonregular runtime entry: ' + relative)
    if actual_files != expected_files or actual_links != set(expected_links):
        raise ValueError('Runtime file/link enumeration differs')
    for row in graph['files']:
        raw = (runtime_root / row['path']).read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('Changed runtime file: ' + row['path'])
    return {'status': 'runtime_bytes_and_links_verified', 'files': len(graph['files']),
            'packages': len(nodes), 'links': len(actual_links), 'graph_sha256': materialization['graph_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('pack')
    p.add_argument('--directory', required=True, type=Path)
    p = subs.add_parser('materialize')
    p.add_argument('--directory', required=True, type=Path)
    p.add_argument('--replica', required=True, type=Path)
    p.add_argument('--target', required=True, type=Path)
    p = subs.add_parser('verify')
    p.add_argument('--runtime', required=True, type=Path)
    p.add_argument('--graph', required=True, type=Path)
    p.add_argument('--materialization', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'pack':
        report = pack(args.directory)
    elif args.command == 'materialize':
        report = materialize(args.directory, args.replica, args.target)
    else:
        report = verify_runtime(args.runtime, json.loads(args.graph.read_bytes()), json.loads(args.materialization.read_bytes()))
        write_new(args.output, report)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] in ('archive_verified', 'materialized_import_check_pending', 'runtime_bytes_and_links_verified') else 1)
