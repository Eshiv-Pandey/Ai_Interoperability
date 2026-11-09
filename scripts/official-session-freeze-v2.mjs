// v2 orchestration helper: copied source-freeze logic; externally observed Git receipt.
// The historical helper remains unchanged. No SDK/application is imported here.
import assert from 'node:assert/strict';
import { constants, copyFileSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { workspace, node22, portFile, portHash, relative, hash, stamp, elapsed, exclusiveJson, logLifecycle } from './log-reference-http.mjs';
const under = (filename, directory) => path.resolve(filename).startsWith(path.resolve(directory) + path.sep);
function treeManifest(directory) {
  const entries = [];
  const visit = current => {
    for (const entry of readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const filename = path.join(current, entry.name);
      if (entry.isDirectory()) visit(filename);
      else if (entry.isFile()) { const bytes = readFileSync(filename); entries.push({ path: path.relative(directory, filename).replaceAll('\\', '/'), bytes: bytes.length, sha256: hash(bytes) }); }
      else throw new Error(`Unsupported artifact within package/source tree: ${filename}`);
    }
  };
  visit(directory);
  return { root: relative(directory), entries, file_count: entries.length, entries_sha256: hash(JSON.stringify(entries)) };
}

export function freezeBeforeStartup(capture, receiptPath) {
  assert.equal(process.execPath.toLowerCase(), node22.toLowerCase()); assert.equal(process.version, 'v22.13.0');
  assert(under(capture.specification, path.join(workspace, 'docs', 'research')));
  const amir = capture.report.route_id === 'amirk_a2a_to_mcp';
  const bridgeDir = path.join(workspace, 'external', amir ? 'a2a-to-mcp' : 'mcp-a2a');
  const lockFile = path.join(bridgeDir, amir ? 'package-lock.json' : 'pnpm-lock.yaml');
  const packageFile = path.join(bridgeDir, 'package.json');
  const pkg = JSON.parse(readFileSync(packageFile, 'utf8'));
  const sourceLockFile = path.join(workspace, 'external', 'source-lock.json');
  const sourceLock = JSON.parse(readFileSync(sourceLockFile, 'utf8'));
  const source = sourceLock.sources.find(entry => entry.id === capture.report.route_id);
  const receipt = JSON.parse(readFileSync(receiptPath, 'utf8'));
  const selected = receipt.routes.find(item => item.route_id === capture.report.route_id);
  assert(selected && selected.directory === relative(bridgeDir));
  assert.equal(selected.status.exit_code, 0); assert.equal(selected.status.stdout, '');
  const head = { status: selected.head.exit_code, stdout: selected.head.stdout, stderr: selected.head.stderr };
  capture.report.source_check_receipt = { path: relative(receiptPath), sha256: hash(readFileSync(receiptPath)),
    method: 'Python subprocess Git commands; no Node child process', route_id: selected.route_id };
  assert.equal(head.status, 0, head.stderr); assert.equal(head.stdout.trim(), source.commit);
  assert.equal(hash(readFileSync(lockFile)), source.dependency_lock.sha256);
  assert.equal(hash(readFileSync(path.join(workspace, portFile))), portHash);
  const portSdkRoot = path.join(workspace, 'external', 'a2a-to-mcp', 'node_modules', '@a2a-js', 'sdk');
  const portSdkPackage = JSON.parse(readFileSync(path.join(portSdkRoot, 'package.json'), 'utf8'));
  assert.equal(portSdkPackage.version, '1.1.0');
  const portJoseRoot = path.join(workspace, 'external', 'a2a-to-mcp', 'node_modules', 'jose');
  const portJosePackage = JSON.parse(readFileSync(path.join(portJoseRoot, 'package.json'), 'utf8'));
  const portLock = path.join(workspace, 'external', 'a2a-to-mcp', 'package-lock.json');
  assert.equal(hash(readFileSync(portLock)), sourceLock.sources.find(entry => entry.id === 'amirk_a2a_to_mcp').dependency_lock.sha256);
  const snapshots = path.join(capture.runDir, 'pre-execution-snapshots'); mkdirSync(snapshots);
  const files = [process.argv[1], fileURLToPath(import.meta.url), path.join(workspace, 'scripts', 'reference-mgcrea-v1.mjs'), path.join(workspace, portFile), capture.specification, sourceLockFile, packageFile, lockFile, portLock, path.join(portSdkRoot, 'package.json'), path.join(portJoseRoot, 'package.json'), path.join(workspace, 'docs', 'research', 'source-evidence', 'reference-continuation', 'port', 'change-map.json'), path.join(workspace, 'docs', 'research', 'source-evidence', 'reference-continuation', 'port', 'ATTRIBUTION.md'), ...capture.extraSnapshots.map(filename => path.resolve(workspace, filename))];
  const sourceHashes = {};
  for (const [index, filename] of [...new Set(files)].entries()) {
    assert(under(filename, workspace));
    const bytes = readFileSync(filename);
    const snapshot = path.join(snapshots, `${String(index + 1).padStart(2, '0')}-${path.basename(filename)}`);
    copyFileSync(filename, snapshot, constants.COPYFILE_EXCL);
    sourceHashes[relative(filename)] = { bytes: bytes.length, sha256: hash(bytes), snapshot: relative(snapshot) };
  }
  const dependencies = [];
  for (const name of Object.keys(pkg.dependencies ?? {}).sort()) {
    const packageRoot = path.join(bridgeDir, 'node_modules', ...name.split('/'));
    const installed = JSON.parse(readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));
    dependencies.push({ name, version: installed.version, manifest: treeManifest(packageRoot) });
  }
  const sdk = dependencies.find(entry => entry.name === '@a2a-js/sdk');
  assert.equal(sdk.version, amir ? '1.1.0' : '1.3.0');
  const bridgeSourceManifest = treeManifest(path.join(bridgeDir, 'src'));
  const bridgeDistManifest = treeManifest(path.join(bridgeDir, 'dist'));
  for (const [kind, manifest] of [['bridge-source', bridgeSourceManifest], ['bridge-dist', bridgeDistManifest]]) {
    const archive = path.join(snapshots, kind);
    mkdirSync(archive);
    for (const entry of manifest.entries) {
      const destination = path.join(archive, entry.path);
      mkdirSync(path.dirname(destination), { recursive: true });
      copyFileSync(path.join(workspace, manifest.root, entry.path), destination, constants.COPYFILE_EXCL);
    }
    manifest.snapshot_root = relative(archive);
  }
  capture.report.pre_execution = { captured: stamp(), source_hashes: sourceHashes, source_checkout: head.stdout.trim(), dependency_lock_sha256: hash(readFileSync(lockFile)), installed_runtime_dependencies: dependencies, port_runtime_dependencies: [{ name: portSdkPackage.name, version: portSdkPackage.version, manifest: treeManifest(portSdkRoot) }, { name: portJosePackage.name, version: portJosePackage.version, manifest: treeManifest(portJoseRoot) }], port_dependency_lock_sha256: hash(readFileSync(portLock)), bridge_source_manifest: bridgeSourceManifest, bridge_dist_manifest: bridgeDistManifest, node: { path: process.execPath, version: process.version, sha256: hash(readFileSync(process.execPath)) }, specification: { path: relative(capture.specification), sha256: hash(readFileSync(capture.specification)) } };
  capture.report.pre_execution.setup_ms = elapsed(capture.started, stamp());
  exclusiveJson(path.join(capture.runDir, 'pre-execution-ledger.json'), capture.report.pre_execution);
  logLifecycle(capture, { type: 'pre-execution-ledger-frozen', sha256: hash(readFileSync(path.join(capture.runDir, 'pre-execution-ledger.json'))) });
}

