// New reference-continuation capture utilities. Historical wire drivers unchanged.
// Native preload logs only this authored port's isolated loopback exchanges.
import assert from 'node:assert/strict';
import { fork, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { appendFileSync, constants, copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const workspace = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const node22 = 'C:\\Program Files\\nodejs\\node.exe';
export const portFile = 'scripts/fixtures/carol-reference-v1.mjs';
export const portHash = 'b6b6492ee5c27cf5db0474054b0f18a8feafe0859d9faaa4fd67946c7768626d';
export const initialText = '{"action":"shuffle","history":[{"guess":25,"response":"Go higher"}]}';
export const answerText = 'Well done!';
export const hash = value => createHash('sha256').update(value).digest('hex');
export const stamp = () => ({ utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString() });
export const elapsed = (start, end) => Number(BigInt(end.monotonic_ns) - BigInt(start.monotonic_ns)) / 1e6;
export const relative = filename => path.relative(workspace, filename).replaceAll('\\', '/');
export const errorText = error => error?.stack ?? String(error);
export const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
export const exclusiveJson = (filename, value) => writeFileSync(filename, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
export async function deadline(promise, milliseconds, label) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`${label} exceeded ${milliseconds}ms`)), milliseconds); })]); }
  finally { clearTimeout(timer); }
}
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

export function createCapture(variant, specification, extraSnapshots = []) {
  const amir = variant === 'R1' || variant === 'R2';
  const bridgeId = amir ? 'amirk_a2a_to_mcp' : 'mgcrea_mcp_a2a';
  const protocol = { mcp: amir ? '2026-07-28' : '2025-11-25', mcp_transport: amir ? 'loopback HTTP modern per-request envelope' : 'actual child-process stdio', extension: variant === 'R2' ? 'io.modelcontextprotocol/tasks' : 'not declared by this route', a2a: '1.0 JSONRPC on authored Carol port, streaming=false' };
  const runId = `${variant}-${bridgeId}-reference-v1-${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}-${process.pid}`;
  const root = path.join(workspace, 'runs', 'reference-bridge-observation');
  mkdirSync(root, { recursive: true });
  const runDir = path.join(root, runId);
  mkdirSync(runDir);
  const lifecycle = path.join(runDir, 'process-lifecycle.jsonl');
  writeFileSync(lifecycle, '', { flag: 'wx' });
  const capture = { runDir, output: path.join(runDir, 'runtime.json'), nativeLog: path.join(runDir, 'private-native-http.jsonl'), lifecycle, children: [], diagnostics: { children: {} }, specification: path.resolve(workspace, specification), extraSnapshots, started: stamp() };
  capture.report = {
    schema_version: 'runtime-wire-observation/1', run_id: runId, route_id: bridgeId, variant_id: variant, protocol,
    source_commit: amir ? '58eff9da469bccdc432bf164662727947de646b4' : 'c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5',
    started_at_utc: new Date().toISOString(), command: process.argv, node: process.version, parent_pid: process.pid,
    exchanges: [], receipts: [], outcome: 'setup-started', exit_code: null,
    namespaces: { task: amir ? 'Amir opaque tk_ handle; native IDs are public only if a captured MCP content metadata/history path reveals them' : 'Native A2A task ID visibly returned in MCP JSON-in-text', context: amir ? 'Amir opaque cx_ handle; public native metadata/history paths separately recorded' : 'Native A2A context ID visibly returned as context_id in MCP JSON-in-text', principal: 'Unauthenticated local development caller', scope: 'Isolated authored Carol loopback port', credential_epoch: 'No credentials', policy_epoch: null, validity_interval: null },
    provenance: { kind: 'wire-derived-authored-port-development', fixture: { kind: 'Separate authored A2A1.0 port of official Carol application', repository: 'a2aproject/a2a-samples', commit: '6603ba3f2c31a7ef33e70b9d8b5b5f8be42ac9a3', file: portFile, sha256: portHash }, model_calls: 0, held_out: false, evidence_complete: false,
      instrumentation: { native_http: 'Read-only preload wraps original bridge fetch; captures exact supplied request/body and cloned response entity bytes; does not alter headers, parameters or transport.', overhead: 'Cloned response body is logged before original response is delivered; capture file I/O and scheduling overhead included, no latency or efficiency claim.', native_bytes: 'Fetch-visible application entity bytes, excludes TCP framing and implicit HTTP headers.', cleanup: 'Specific recorded children only; preload IPC emits unchanged original CLI SIGTERM shutdown handler and awaits actual exit; Carol IPC invokes server.close.' } },
    configuration: amir ? { tasks_extension: variant === 'R2', elicitation: false, agent_alias: 'carol', mcp_revision: '2026-07-28' } : { writes: true, channel: false, retries: 0, token: 'unset; isolated environment', mcp_revision: '2025-11-25' },
    bounds: { startup_ms: 10000, request_ms: 10000, initial_observation_ms: 5000, polling_interval_ms: 50, answer_attempts: 1, final_authoritative_reads: 1 },
    claim_limit: 'Observed authored-port route behavior only. No bridge conformance, natural defect, universal impossibility, model efficacy, efficiency, novelty or human gate approval.'
  };
  return capture;
}
export function logLifecycle(capture, record) { appendFileSync(capture.lifecycle, JSON.stringify({ observed: stamp(), ...record }) + '\n'); }
export function freezeBeforeStartup(capture) {
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
  const head = spawnSync('git', ['-C', bridgeDir, 'rev-parse', 'HEAD'], { encoding: 'utf8', windowsHide: true });
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
function isolatedEnvironment(extra = {}) { return { PATH: process.env.PATH, SystemRoot: process.env.SystemRoot, TEMP: process.env.TEMP, TMP: process.env.TMP, ...extra }; }
function trackChild(capture, child, role, command) {
  const tracked = { child, role, command, pid: child.pid, exit: null };
  capture.children.push(tracked);
  capture.diagnostics.children[role] = { stdout: '', stderr: '', ipc: [] };
  const diagnostics = capture.diagnostics.children[role];
  child.stdout.on('data', bytes => { diagnostics.stdout += bytes.toString('utf8'); });
  child.stderr.on('data', bytes => { diagnostics.stderr += bytes.toString('utf8'); });
  child.on('message', message => { diagnostics.ipc.push(message); logLifecycle(capture, { type: 'ipc', role, pid: child.pid, message }); });
  tracked.exited = new Promise(resolve => child.once('exit', (code, signal) => { tracked.exit = { code, signal, observed: stamp() }; logLifecycle(capture, { type: 'exit', role, pid: child.pid, ...tracked.exit }); resolve(tracked.exit); }));
  logLifecycle(capture, { type: 'spawn', role, pid: child.pid, command });
  return tracked;
}
export async function launchCarol(capture) {
  const helper = fileURLToPath(import.meta.url);
  const child = fork(helper, ['--carol-child'], { execPath: node22, execArgv: [], cwd: workspace, windowsHide: true, silent: true, env: isolatedEnvironment() });
  const tracked = trackChild(capture, child, 'carol', [node22, helper, '--carol-child']);
  const ready = await deadline(new Promise((resolve, reject) => { child.once('error', reject); child.once('exit', code => reject(new Error(`Carol exited ${code} before ready`))); child.on('message', message => { if (message.type === 'carol-ready') resolve(message); }); }), 10000, 'Carol startup');
  assert.equal(ready.pid, child.pid);
  tracked.ready = ready;
  capture.report.provenance.fixture.pid = child.pid;
  capture.report.provenance.fixture.command = tracked.command;
  capture.report.fixture_endpoint = ready.url;
  return ready.url;
}
export function launchBridge(capture, fixtureUrl) {
  const amir = capture.report.route_id === 'amirk_a2a_to_mcp';
  const bridgeDir = path.join(workspace, 'external', amir ? 'a2a-to-mcp' : 'mcp-a2a');
  const args = [];
  const extra = { REFERENCE_HTTP_LOG: capture.nativeLog, REFERENCE_RUN_ID: capture.report.run_id, REFERENCE_ROUTE_ID: capture.report.route_id, REFERENCE_PORT_ORIGIN: fixtureUrl };
  if (amir) {
    const config = path.join(capture.runDir, 'bridge-config.json');
    exclusiveJson(config, { agents: { carol: { url: fixtureUrl } }, host: '127.0.0.1' });
    args.push('--config', config, '--port', '0');
  } else {
    Object.assign(extra, { A2A_CONFIG: path.join(capture.runDir, 'absent-config.json'), A2A_STATE_DIR: path.join(capture.runDir, 'state'), A2A_DAEMON_URL: fixtureUrl, A2A_PEERS: fixtureUrl, A2A_ALLOW_WRITES: '1', A2A_CHANNEL: '0', A2A_MAX_RETRIES: '0' });
    capture.report.configuration.state_directory = relative(extra.A2A_STATE_DIR);
  }
  const main = path.join(bridgeDir, 'dist', 'cli.js');
  const preload = pathToFileURL(fileURLToPath(import.meta.url)).href;
  const dynamicConfiguration = { captured: stamp(), fixture_url: fixtureUrl, bridge_args: args, supplied_environment: extra, bridge_profile: capture.report.configuration };
  const configLedger = path.join(capture.runDir, 'pre-bridge-runtime-config.json');
  exclusiveJson(configLedger, dynamicConfiguration);
  capture.report.pre_bridge_runtime_config = { path: relative(configLedger), sha256: hash(readFileSync(configLedger)), captured: dynamicConfiguration.captured };
  logLifecycle(capture, { type: 'runtime-config-frozen-before-bridge-spawn', ...capture.report.pre_bridge_runtime_config });
  const child = fork(main, args, { execPath: node22, execArgv: ['--import', preload], cwd: bridgeDir, windowsHide: true, silent: true, env: isolatedEnvironment(extra) });
  trackChild(capture, child, 'bridge', [node22, '--import', preload, main, ...args]);
  capture.report.provenance.bridge_command = [node22, '--import', preload, main, ...args];
  capture.report.provenance.bridge_pid = child.pid;
  return child;
}
export async function stopChildren(capture) {
  capture.report.cleanup = [];
  for (const tracked of [...capture.children].reverse()) {
    const record = { role: tracked.role, pid: tracked.pid, requested: stamp(), already_exited: Boolean(tracked.exit) };
    capture.report.cleanup.push(record);
    try {
      if (!tracked.exit && tracked.child.connected) {
        record.method = tracked.role === 'carol' ? 'Carol server.close IPC' : 'Preload IPC emits existing original CLI SIGTERM shutdown handler';
        tracked.child.send({ type: tracked.role === 'carol' ? 'carol-close' : 'reference-bridge-close' });
      }
      record.exit = await deadline(tracked.exited, 5000, `${tracked.role} normal cleanup`);
      if (tracked.role === 'carol') record.server_close = capture.diagnostics.children.carol.ipc.find(message => message.type === 'carol-closed') ?? null;
      record.normal_exit = record.exit.code === 0 && record.exit.signal === null;
      if (!record.normal_exit) throw new Error(`${tracked.role} cleanup exited ${record.exit.code}/${record.exit.signal}`);
    } catch (error) {
      record.error = errorText(error);
      if (!tracked.exit) { record.fallback_kill_requested = stamp(); tracked.child.kill(); try { record.exit = await deadline(tracked.exited, 5000, `${tracked.role} exact-PID fallback`); } catch (failure) { record.fallback_error = errorText(failure); } }
      capture.report.outcome = 'failed'; capture.report.exit_code = 1;
    }
  }
}
export function addReceipt(capture, exchange, role, taskId, contextId, fields) {
  assert(exchange.response);
  const receipt = { receipt_id: `${exchange.exchange_id}-receipt-${capture.report.receipts.length + 1}`, exchange_id: exchange.exchange_id, role, protocol: capture.report.protocol, task_namespace: capture.report.namespaces.task, task_id: taskId ?? null, context_namespace: capture.report.namespaces.context, context_id: contextId ?? null, source: { endpoint: exchange.request?.url ?? 'original bridge child stdio', method: exchange.request?.json?.method, tool: exchange.request?.json?.params?.name ?? null, source_commit: capture.report.source_commit, response_sha256: exchange.response.sha256 }, observed_at_utc: exchange.response.observed_at_utc, returned_field_paths: fields, request_cost: exchange.request?.json?.id === undefined ? 0 : 1, freshness_basis: role === 'bridge_task_record' ? 'Captured extension task record; not automatically authoritative origin refresh' : 'Actual supported task query; native sidecar separately identifies genuine GetTask', validity_interval: null, recipient_authority: null };
  capture.report.receipts.push(receipt);
  return receipt;
}
export function createStdioRpc(capture, bridge) {
  let incoming = Buffer.alloc(0);
  let sequence = 0;
  const pending = new Map();
  const rejectPending = error => { for (const item of pending.values()) item.reject(error); pending.clear(); };
  bridge.on('error', rejectPending); bridge.on('exit', code => rejectPending(new Error(`Bridge exited ${code}`)));
  bridge.stdout.on('data', chunk => {
    incoming = Buffer.concat([incoming, chunk]);
    for (;;) {
      const newline = incoming.indexOf(10); if (newline < 0) return;
      const bytes = incoming.subarray(0, newline + 1); incoming = incoming.subarray(newline + 1);
      const raw = bytes.toString('utf8'); const end = stamp();
      let json;
      try { json = JSON.parse(raw); } catch (error) {
        capture.diagnostics.unparsed_stdout ??= [];
        capture.diagnostics.unparsed_stdout.push({ raw, base64: bytes.toString('base64'), bytes: bytes.length, sha256: hash(bytes), observed: end, parse_error: errorText(error) });
        continue;
      }
      const waiting = pending.get(json.id);
      const response = { raw, base64: bytes.toString('base64'), bytes: bytes.length, json, observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns, sha256: hash(bytes) };
      if (waiting) { pending.delete(json.id); waiting.exchange.response = response; waiting.exchange.elapsed_ms = elapsed(waiting.start, end); waiting.resolve({ body: json.result, exchange: waiting.exchange, json }); }
      else capture.report.exchanges.push({ exchange_id: `mcp-unsolicited-${capture.report.exchanges.length + 1}`, phase: 'unsolicited_notification_or_reply', request: null, response });
    }
  });
  return async (phase, method, params, notification = false, requestLimit = 10000) => {
    const id = notification ? undefined : ++sequence;
    const json = { jsonrpc: '2.0', ...(id === undefined ? {} : { id }), method, ...(params === undefined ? {} : { params }) };
    const raw = JSON.stringify(json) + '\n'; const bytes = Buffer.from(raw); const start = stamp();
    const exchange = { exchange_id: notification ? `mcp-notification-${capture.report.exchanges.length + 1}` : `mcp-${id}`, phase, request: { raw, base64: bytes.toString('base64'), bytes: bytes.length, json, started_at_utc: start.utc, monotonic_ns: start.monotonic_ns, sha256: hash(bytes) }, response: null };
    capture.report.exchanges.push(exchange);
    const answer = notification ? null : new Promise((resolve, reject) => pending.set(id, { resolve, reject, exchange, start }));
    // Register rejection handling immediately: a child can exit while its
    // stdin.write callback is pending. The original rejection still propagates
    // through the bounded exchange below and is retained in exchange.error.
    answer?.catch(() => {});
    try {
      const writeAndResponse = (async () => {
        await new Promise((resolve, reject) => bridge.stdin.write(bytes, error => error ? reject(error) : resolve()));
        return notification ? { exchange } : await answer;
      })();
      const result = await deadline(writeAndResponse, requestLimit, `MCP ${method} write plus response`);
      if (notification) return result;
      assert.equal(result.json.id, id); assert(!result.json.error, JSON.stringify(result.json)); assert(result.body, JSON.stringify(result.json));
      return result;
    } catch (error) { exchange.error = errorText(error); pending.delete(id); throw error; }
  };
}
export function finishCapture(capture) {
  capture.report.completed_at_utc = new Date().toISOString();
  const requests = capture.report.exchanges.filter(exchange => exchange.request);
  capture.report.costs = { mcp_rpc_requests: requests.filter(exchange => exchange.request.json.id !== undefined).length, mcp_notifications_sent: requests.filter(exchange => exchange.request.json.id === undefined).length, request_bytes: requests.reduce((sum, exchange) => sum + exchange.request.bytes, 0), response_bytes: capture.report.exchanges.reduce((sum, exchange) => sum + (exchange.response?.bytes ?? 0), 0), setup_ms: capture.report.pre_execution?.setup_ms ?? null, native_cost_source: 'Every native request/reply entity retained separately in private-native-http.jsonl; independent sidecar check may derive aggregate counts/bytes' };
  const diagnostics = path.join(capture.runDir, 'private-process-diagnostics.json');
  exclusiveJson(diagnostics, capture.diagnostics);
  capture.report.private_sidecars = { native_http: existsSync(capture.nativeLog) ? relative(capture.nativeLog) : null, native_capture_available: existsSync(capture.nativeLog), diagnostics: relative(diagnostics), process_lifecycle: relative(capture.lifecycle) };
  capture.report.post_source_sha256 = {};
  capture.report.post_source_errors = [];
  capture.report.post_source_changes = [];
  for (const [filename, before] of Object.entries(capture.report.pre_execution?.source_hashes ?? {})) {
    try {
      const after = hash(readFileSync(path.join(workspace, filename)));
      capture.report.post_source_sha256[filename] = after;
      if (after !== before.sha256) {
        capture.report.post_source_changes.push({ path: filename, pre_sha256: before.sha256, post_sha256: after, observed: stamp() });
        capture.report.outcome = 'failed'; capture.report.exit_code = 1;
      }
    } catch (error) {
      capture.report.post_source_errors.push({ path: filename, error: errorText(error), observed: stamp() });
      capture.report.outcome = 'failed'; capture.report.exit_code = 1;
    }
  }
  exclusiveJson(capture.output, capture.report);
  console.log(JSON.stringify({ outcome: capture.report.outcome, exit_code: capture.report.exit_code, variant: capture.report.variant_id, output: relative(capture.output), report_sha256: hash(readFileSync(capture.output)), observation: capture.report.observation, cleanup: capture.report.cleanup, error: capture.report.error }));
}

// This branch is entered only when the authorized capture driver forks Carol.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url) && process.argv[2] === '--carol-child') {
  try {
    const { startCarolReferenceAgent } = await import(pathToFileURL(path.join(workspace, portFile)).href);
    const agent = await startCarolReferenceAgent({ port: 0 });
    process.send({ type: 'carol-ready', pid: process.pid, url: agent.url, card_url: agent.cardUrl, observed: stamp() });
    let closing = false;
    process.on('message', message => {
      if (message?.type !== 'carol-close' || closing) return;
      closing = true;
      void agent.close().then(() => process.send({ type: 'carol-closed', pid: process.pid, observed: stamp(), server_listening: agent.server.listening }, () => process.disconnect()), error => { process.exitCode = 1; process.send({ type: 'carol-close-failed', pid: process.pid, error: errorText(error), observed: stamp() }, () => process.disconnect()); });
    });
  } catch (error) { console.error(errorText(error)); process.exitCode = 1; process.disconnect?.(); }
}

// Preload runs in unchanged bridge CLI children only, with explicit local log.
if (process.env.REFERENCE_HTTP_LOG) {
  const destination = path.resolve(process.env.REFERENCE_HTTP_LOG);
  assert(under(destination, path.join(workspace, 'runs', 'reference-bridge-observation')));
  const allowedOrigin = new URL(process.env.REFERENCE_PORT_ORIGIN).origin;
  assert.equal(new URL(allowedOrigin).hostname, '127.0.0.1');
  writeFileSync(destination, '', { flag: 'wx' });
  const write = record => appendFileSync(destination, JSON.stringify(record) + '\n');
  write({ schema_version: 'private-native-http/1', run_id: process.env.REFERENCE_RUN_ID, route_id: process.env.REFERENCE_ROUTE_ID, pid: process.pid, created_at_utc: new Date().toISOString(), role: 'Evaluator-private raw authored-Carol-port correlation; IDs become arm-public only when separately present in MCP response', fixture: { file: portFile, sha256: portHash } });
  const originalFetch = globalThis.fetch;
  let sequence = 0;
  globalThis.fetch = async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    assert.equal(new URL(url).origin, allowedOrigin, 'Capture restricted to authorized local Carol origin');
    let bytes;
    if (init?.body == null && input instanceof Request) bytes = Buffer.from(await input.clone().arrayBuffer());
    else if (init?.body == null) bytes = Buffer.alloc(0);
    else if (typeof init.body === 'string' || init.body instanceof Uint8Array) bytes = Buffer.from(init.body);
    else throw new Error(`Unsupported exact native request body: ${typeof init.body}`);
    const raw = bytes.toString('utf8'); const start = stamp();
    const request = { url, method: init?.method ?? (input instanceof Request ? input.method : 'GET'), headers: Object.fromEntries(new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined))), raw, base64: bytes.toString('base64'), bytes: bytes.length, json: null, sha256: hash(bytes), started_at_utc: start.utc, monotonic_ns: start.monotonic_ns };
    if (raw) { try { request.json = JSON.parse(raw); } catch (error) { request.json_parse_error = errorText(error); } }
    const exchange = { exchange_id: `native-${++sequence}`, role: 'native_peer_response', request, response: null };
    write({ type: 'request-started', ...exchange });
    try {
      const response = await originalFetch(input, init);
      const body = Buffer.from(await response.clone().arrayBuffer()); const responseRaw = body.toString('utf8'); const end = stamp();
      exchange.response = { raw: responseRaw, base64: body.toString('base64'), bytes: body.length, json: null, sha256: hash(body), status: response.status, headers: Object.fromEntries(response.headers), observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns };
      try { exchange.response.json = JSON.parse(responseRaw); } catch (error) { exchange.response.json_parse_error = errorText(error); }
      exchange.elapsed_ms = elapsed(start, end);
      return response;
    } catch (error) { exchange.error = errorText(error); throw error; }
    finally { write({ type: 'exchange-completed', ...exchange }); }
  };
  process.on('message', message => {
    if (message?.type !== 'reference-bridge-close') return;
    write({ type: 'shutdown-request', pid: process.pid, observed: stamp(), original_sigterm_listeners: process.listenerCount('SIGTERM') });
    process.emit('SIGTERM');
  });
  process.once('exit', code => write({ type: 'logger-exit', code, pid: process.pid, observed: stamp() }));
}
