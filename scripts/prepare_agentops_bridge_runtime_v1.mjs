// Freeze installed runtime dependency resolution without installing or building.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const digest = raw => createHash('sha256').update(raw).digest('hex');
const relative = value => path.relative(root, value).split(path.sep).join('/');
const readJson = name => JSON.parse(readFileSync(name, 'utf8'));
const fileRecord = (name, base=root) => {
  const raw = readFileSync(name);
  return { path: path.relative(base, name).split(path.sep).join('/'), bytes: raw.length, sha256: digest(raw) };
};
const allowedName = name => /^(?:@[a-zA-Z0-9._-]+\/)?[a-zA-Z0-9._-]+$/.test(name) && !name.split('/').some(p => p === '.' || p === '..');

export function resolveInstalled(name, packageRoot) {
  assert(allowedName(name), 'Invalid dependency name ' + name);
  const require = createRequire(path.join(packageRoot, 'package.json'));
  for (const directory of require.resolve.paths(name) ?? []) {
    const candidate = path.join(directory, ...name.split('/'));
    if (existsSync(path.join(candidate, 'package.json'))) return realpathSync(candidate);
  }
  return null;
}

export function declaredEdges(metadata) {
  const names = [...new Set(['dependencies', 'optionalDependencies', 'peerDependencies']
    .flatMap(field => Object.keys(metadata[field] ?? {})))].sort();
  return names.map(name => ({ name,
    declarations: Object.fromEntries(['dependencies', 'optionalDependencies', 'peerDependencies']
      .filter(field => Object.hasOwn(metadata[field] ?? {}, name))
      .map(field => [field, metadata[field][name]])),
    optional: Object.hasOwn(metadata.optionalDependencies ?? {}, name) ||
      (!Object.hasOwn(metadata.dependencies ?? {}, name) && metadata.peerDependenciesMeta?.[name]?.optional === true),
  }));
}

function entries(directory) {
  const rows = [];
  function visit(current, atRoot) {
    for (const item of readdirSync(current, { withFileTypes: true }).sort((a,b) => a.name.localeCompare(b.name))) {
      if (atRoot && ['node_modules', '.git'].includes(item.name)) continue;
      const filename = path.join(current, item.name);
      const stat = lstatSync(filename);
      assert(!stat.isSymbolicLink(), 'Unexpected package content link ' + filename);
      if (stat.isDirectory()) {
        assert(item.name !== 'node_modules', 'Nested undeclared node_modules content requires explicit handling: ' + filename);
        visit(filename, false);
      } else {
        assert(stat.isFile(), 'Unexpected package content entry ' + filename);
        rows.push(fileRecord(filename, directory));
      }
    }
  }
  visit(directory, true);
  return rows;
}

export function prepare(output) {
  assert(!existsSync(output), 'Preserve existing runtime preparation');
  mkdirSync(output, { recursive: false });
  const result = { schema_version: 'agentops-bridge-runtime-graph/1', status: 'failed',
    prepared_at_utc: new Date().toISOString(), original_workspace: root,
    preparation_node: { path: process.execPath, version: process.version, platform: process.platform,
      sha256: digest(readFileSync(process.execPath)) },
    scope: 'Declared installed runtime/optional/peer dependency closure with exact package contents; not an authentication or execution claim',
    application_requests: 0, live_model_calls: 0, installations: 0,
    source_lock: fileRecord(path.join(root, 'external/source-lock.json')),
    preparer: fileRecord(fileURLToPath(import.meta.url)), roots: [], nodes: [], edges: [], missing_optional: [], files: [] };
  const registry = new Map();
  function nodeFor(directory) {
    const physical = realpathSync(directory);
    const key = process.platform === 'win32' ? physical.toLowerCase() : physical;
    if (registry.has(key)) return registry.get(key);
    assert(physical.startsWith(root + path.sep), 'Resolved dependency outside workspace: ' + physical);
    const metadata = readJson(path.join(physical, 'package.json'));
    assert(typeof metadata.name === 'string' && typeof metadata.version === 'string', 'Package identity required');
    const node = { id: 'p' + String(result.nodes.length).padStart(3, '0'),
      name: metadata.name, version: metadata.version, original_root: relative(physical),
      original_realpath: physical, destination: '', package_json: fileRecord(path.join(physical, 'package.json'), physical),
      license: metadata.license ?? null, declared_dependencies: declaredEdges(metadata), files: [] };
    node.destination = 'nodes/' + node.id + '/package';
    registry.set(key, node);
    result.nodes.push(node);
    return node;
  }
  try {
    const sourceLock = readJson(path.join(root, 'external/source-lock.json'));
    for (const [alias, sourceId] of [['a2a-to-mcp', 'amirk_a2a_to_mcp'], ['mcp-a2a', 'mgcrea_mcp_a2a']]) {
      const source = sourceLock.sources.find(row => row.id === sourceId);
      assert(source, 'Missing locked source');
      const directory = path.join(root, source.path);
      const head = spawnSync('git', ['-C', directory, 'rev-parse', 'HEAD'], { encoding: 'utf8', windowsHide: true });
      const status = spawnSync('git', ['-C', directory, 'status', '--porcelain', '--untracked-files=no'], { encoding: 'utf8', windowsHide: true });
      assert.equal(head.status, 0, head.stderr); assert.equal(status.status, 0, status.stderr);
      assert.equal(head.stdout.trim(), source.commit); assert.equal(status.stdout, '');
      assert.equal(fileRecord(path.join(root, source.dependency_lock.path)).sha256, source.dependency_lock.sha256);
      const node = nodeFor(directory);
      result.roots.push({ alias, source_id: sourceId, node: node.id, commit: source.commit,
        tracked_status: status.stdout, lock: fileRecord(path.join(root, source.dependency_lock.path)) });
    }
    for (let i = 0; i < result.nodes.length; i++) {
      const node = result.nodes[i];
      for (const declared of node.declared_dependencies) {
        const resolved = resolveInstalled(declared.name, node.original_realpath);
        if (resolved === null) {
          assert(declared.optional, 'Missing required dependency: ' + node.name + ' -> ' + declared.name);
          result.missing_optional.push({ from: node.id, ...declared });
        } else {
          const target = nodeFor(resolved);
          result.edges.push({ from: node.id, to: target.id, ...declared });
        }
      }
      node.files = entries(node.original_realpath);
      for (const row of node.files) result.files.push({
        path: node.destination + '/' + row.path, source: node.original_root + '/' + row.path,
        bytes: row.bytes, sha256: row.sha256 });
    }
    result.total_bytes = result.files.reduce((n, row) => n + row.bytes, 0);
    assert(result.total_bytes < 256 * 1024 * 1024, 'Runtime snapshot exceeds bounded size');
    result.status = 'graph_pinned_not_materialized';
  } catch (error) {
    result.error = error.stack ?? String(error);
  }
  writeFileSync(path.join(output, 'graph.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  process.stdout.write(JSON.stringify({ status: result.status, packages: result.nodes.length,
    files: result.files.length, bytes: result.total_bytes, missing_optional: result.missing_optional.length,
    error: result.error }, null, 2) + '\n');
  return result.status === 'graph_pinned_not_materialized';
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  assert(process.argv[2], 'Supply an exclusive output directory');
  process.exitCode = prepare(path.resolve(process.argv[2])) ? 0 : 1;
}
