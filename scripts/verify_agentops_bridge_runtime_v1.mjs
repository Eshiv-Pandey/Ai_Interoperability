// Verify relocated file/edge identity and passive imports. Never starts services.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, realpathSync, readdirSync, readlinkSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [runtimeArgument, output] = process.argv.slice(2);
assert(runtimeArgument && output, 'Supply runtime root and new output JSON path');
const root = realpathSync(runtimeArgument);
const rawGraph = readFileSync(path.join(root, 'graph.json'));
const graph = JSON.parse(rawGraph);
const materialization = JSON.parse(readFileSync(path.join(root, 'materialization.json')));
const hash = raw => createHash('sha256').update(raw).digest('hex');
const result = { schema_version: 'agentops-bridge-runtime-verification/1', status: 'failed',
  checked_at_utc: new Date().toISOString(), runtime_root: root,
  graph_sha256: hash(rawGraph), archive_sha256: materialization.archive_sha256,
  node: { path: realpathSync(process.execPath), version: process.version, platform: process.platform,
    sha256: hash(readFileSync(process.execPath)) },
  bridges: materialization.bridges, application_requests: 0, live_model_calls: 0, installations: 0 };
function resolvedPackage(name, packageRoot) {
  for (const candidateRoot of createRequire(path.join(packageRoot, 'package.json')).resolve.paths(name) ?? []) {
    const candidate = path.join(candidateRoot, ...name.split('/'));
    if (existsSync(path.join(candidate, 'package.json'))) return realpathSync(candidate);
  }
  return null;
}
try {
  assert.equal(process.platform, 'linux');
  assert.equal(graph.schema_version, 'agentops-bridge-runtime-graph/1');
  assert.equal(graph.status, 'graph_pinned_not_materialized');
  assert.equal(materialization.status, 'materialized_import_check_pending');
  assert.equal(materialization.graph_sha256, result.graph_sha256);
  const nodes = new Map(graph.nodes.map(row => [row.id, row]));
  const files = new Set(['graph.json', 'materialization.json', ...graph.files.map(row => row.path)]);
  const links = new Map(materialization.links.map(row => [row.path, row]));
  const actualFiles = new Set(), actualLinks = new Set();
  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const name = path.join(directory, entry.name), relative = path.relative(root, name).split(path.sep).join('/');
      const stat = lstatSync(name);
      if (stat.isSymbolicLink()) {
        const row = links.get(relative);
        assert(row, 'Unexpected runtime link ' + relative);
        assert.equal(readlinkSync(name), row.target);
        assert.equal(realpathSync(name), path.join(root, row.resolved));
        actualLinks.add(relative);
      } else if (stat.isDirectory()) visit(name);
      else { assert(stat.isFile()); actualFiles.add(relative); }
    }
  }
  visit(root);
  assert.deepEqual([...actualFiles].sort(), [...files].sort());
  assert.deepEqual([...actualLinks].sort(), [...links.keys()].sort());
  for (const row of graph.files) {
    const raw = readFileSync(path.join(root, row.path));
    assert.equal(raw.length, row.bytes, row.path); assert.equal(hash(raw), row.sha256, row.path);
  }
  for (const row of graph.edges) {
    assert.equal(resolvedPackage(row.name, path.join(root, nodes.get(row.from).destination)),
      path.join(root, nodes.get(row.to).destination), 'Changed dependency resolution ' + row.name);
  }
  for (const row of graph.missing_optional) {
    assert.equal(resolvedPackage(row.name, path.join(root, nodes.get(row.from).destination)), null,
      'Previously absent optional dependency now resolves: ' + row.name);
  }
  result.exports = {};
  for (const alias of ['a2a-to-mcp', 'mcp-a2a']) {
    const module = await import(pathToFileURL(path.join(root, 'external', alias, 'dist/index.js')));
    result.exports[alias] = Object.keys(module);
  }
  const stdio = await import(pathToFileURL(path.join(root, 'external/mcp-a2a/node_modules/@modelcontextprotocol/server/dist/stdio.mjs')));
  assert.equal(typeof stdio.StdioServerTransport, 'function');
  result.status = 'runtime_files_resolution_and_imports_verified';
  result.packages = nodes.size; result.files = graph.files.length; result.resolved_edges = graph.edges.length;
  result.absent_optional_dependencies = graph.missing_optional.length;
} catch (error) { result.error = error.stack ?? String(error); }
writeFileSync(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
process.exitCode = result.status === 'runtime_files_resolution_and_imports_verified' ? 0 : 1;
