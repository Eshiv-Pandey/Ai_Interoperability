// Development observation utilities and read-only native fetch instrumentation.
// Preload only in isolated local bridge children with WIRE_HTTP_LOG set.
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, openSync, readFileSync, writeFileSync, writeSync, closeSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const workspace = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const node22 = 'C:\\Program Files\\nodejs\\node.exe';
export const hash = value => createHash('sha256').update(value).digest('hex');
export const stamp = () => ({ utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString() });
export const elapsed = (before, after) => Number(BigInt(after.monotonic_ns) - BigInt(before.monotonic_ns)) / 1e6;
export const jsonOrNull = raw => { try { return JSON.parse(raw); } catch { return null; } };
export function rpcBody(raw, contentType = '') {
  if (contentType.includes('text/event-stream')) {
    const lines = raw.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).filter(Boolean);
    return JSON.parse(lines.at(-1) ?? 'null');
  }
  return JSON.parse(raw);
}
export async function deadline(promise, milliseconds, label) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`${label} timed out after ${milliseconds}ms`)), milliseconds); })]); }
  finally { clearTimeout(timer); }
}
export const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

export function createCapture(routeId, protocol, sourceCommit) {
  if (process.execPath.toLowerCase() !== node22.toLowerCase() || process.versions.node.split('.')[0] !== '22') throw new Error(`Use explicit Node 22: ${node22}`);
  const args = process.argv.slice(2);
  if (args.length && (args.length !== 2 || args[0] !== '--output')) throw new Error('Usage: node capture script [--output <new-file.json>]');
  const runId = `${routeId}-${new Date().toISOString().replace(/[:.]/g, '-')}-${process.pid}`;
  mkdirSync(path.join(workspace, 'runs', 'wire-observation'), { recursive: true });
  const runDir = path.join(workspace, 'runs', 'wire-observation', runId);
  mkdirSync(runDir, { recursive: false });
  const output = args.length ? path.resolve(workspace, args[1]) : path.join(runDir, 'runtime.json');
  const allowedRoot = path.resolve(workspace, 'runs', 'wire-observation') + path.sep;
  if (!output.startsWith(allowedRoot)) throw new Error('Output must remain under runs/wire-observation/');
  if (existsSync(output)) throw new Error(`Refusing to overwrite ${output}`);
  mkdirSync(path.dirname(output), { recursive: true });
  const nativeLog = path.join(runDir, 'private-native-http.jsonl');
  const diagnostics = { fixture_stdout: '', fixture_stderr: '', bridge_stdout: '', bridge_stderr: '' };
  const report = {
    schema_version: 'runtime-wire-observation/1', run_id: runId, route_id: routeId,
    protocol, source_commit: sourceCommit, started_at_utc: new Date().toISOString(),
    command: process.argv, node: process.version, exchanges: [], receipts: [],
    provenance: {
      kind: 'wire-derived-development', fixture: { repository: 'AmirK-S/a2a-to-mcp', commit: '58eff9da469bccdc432bf164662727947de646b4', label: 'Original upstream deterministic fixture; shared between routes, no model inference or independent gold' },
      instrumentation: { native_http: 'Read-only global fetch wrapper in original bridge child; no replacement transport, request mutation, correlation header, injected faults or delays', overhead: 'Wrapper stamps and hashes, clones response bodies asynchronously, and appends native records synchronously. Scheduling, memory and file-I/O overhead is measured as part of elapsed time; no uninstrumented latency claim.', raw_mcp: 'Exact application JSON-RPC bytes on genuine loopback HTTP or child-process stdio, with paired matching IDs', native_bytes: 'Fetch-visible request input and response entity body, not TLS/TCP framing or implicit HTTP request headers' },
      model_calls: 0, held_out: false, evidence_complete: false,
    },
    namespaces: { task: null, context: null, principal: 'unidentified unauthenticated local development caller; no authority grant inferred', scope: 'loopback fixture', credential_epoch: 'not applicable; no credentials supplied', policy_epoch: 'not observed', validity_interval: 'not established; no service freshness lease inferred' },
  };
  return { report, runDir, output, nativeLog, diagnostics };
}
export function launchFixture(capture) {
  const fixtureDir = path.join(workspace, 'external', 'a2a-to-mcp');
  const args = ['node_modules/tsx/dist/cli.mjs', 'fixtures/agent/cli.ts', '--port', '0'];
  const child = spawn(node22, args, { cwd: fixtureDir, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout.on('data', chunk => { capture.diagnostics.fixture_stdout += chunk.toString(); });
  child.stderr.on('data', chunk => { capture.diagnostics.fixture_stderr += chunk.toString(); });
  capture.report.provenance.fixture.command = [node22, ...args];
  const ready = deadline(new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', code => reject(new Error(`Fixture exited ${code} before startup`)));
    const check = () => { const match = capture.diagnostics.fixture_stdout.match(/listening on (http:\/\/[^\s]+)/); if (match) resolve(match[1]); };
    child.stdout.on('data', check); check();
  }), 10000, 'fixture startup');
  return { child, ready };
}
export function bridgeEnvironment(capture, extra = {}) {
  return { PATH: `${path.dirname(node22)};${process.env.PATH ?? ''}`, SystemRoot: process.env.SystemRoot ?? 'C:\\Windows', TEMP: process.env.TEMP ?? capture.runDir, TMP: process.env.TMP ?? capture.runDir,
    WIRE_HTTP_LOG: capture.nativeLog, WIRE_RUN_ID: capture.report.run_id, WIRE_ROUTE_ID: capture.report.route_id, ...extra };
}
export async function stopChild(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise(resolve => child.once('exit', resolve));
  child.stdin?.end();
  child.kill();
  await deadline(exited, 5000, 'child cleanup');
}
export function addReceipt(capture, exchange, role, taskId, contextId, fields) {
  capture.report.receipts.push({ receipt_id: `${exchange.exchange_id}-receipt`, exchange_id: exchange.exchange_id, role,
    protocol: capture.report.protocol, task_namespace: capture.report.namespaces.task, task_id: taskId ?? null,
    context_namespace: capture.report.namespaces.context, context_id: contextId ?? null,
    source: { endpoint: exchange.request.url ?? 'original bridge child stdio', method: exchange.request.json?.method, tool: exchange.request.json?.params?.name ?? null, source_commit: capture.report.source_commit, response_sha256: exchange.response.sha256 },
    observed_at_utc: exchange.response.observed_at_utc, returned_field_paths: fields, request_cost: exchange.request.json?.id === undefined ? 0 : 1,
    freshness_basis: role === 'local_mirror' ? 'Local mirror response only; its returned updated_at is a store timestamp, not a peer lease' : role === 'bridge_task_record' ? 'Returned extension task record; may be fed by active stream or frozen after terminal state; native evidence determines any refresh' : 'Explicit supported task read; only captured peer GetTask establishes refreshed origin',
    validity_interval: null, recipient_authority: null });
}
export function finishCapture(capture) {
  capture.report.completed_at_utc = new Date().toISOString();
  capture.report.costs = { mcp_rpc_requests: capture.report.exchanges.filter(exchange => exchange.request?.json?.id !== undefined).length,
    mcp_notifications_sent: capture.report.exchanges.filter(exchange => exchange.request?.json && exchange.request.json.id === undefined).length,
    request_bytes: capture.report.exchanges.reduce((sum, exchange) => sum + Buffer.byteLength(exchange.request?.raw ?? ''), 0),
    response_bytes: capture.report.exchanges.reduce((sum, exchange) => sum + Buffer.byteLength(exchange.response?.raw ?? ''), 0) };
  writeFileSync(path.join(capture.runDir, 'private-process-diagnostics.json'), JSON.stringify(capture.diagnostics, null, 2) + '\n', { flag: 'wx' });
  capture.report.private_sidecars = { native_http: existsSync(capture.nativeLog) ? path.relative(workspace, capture.nativeLog).replaceAll('\\', '/') : null, native_capture_available: existsSync(capture.nativeLog), diagnostics: path.relative(workspace, path.join(capture.runDir, 'private-process-diagnostics.json')).replaceAll('\\', '/') };
  const sourceFiles = [path.join(workspace, 'external', 'source-lock.json'), fileURLToPath(import.meta.url), process.argv[1]];
  for (const file of sourceFiles.slice(1)) writeFileSync(path.join(capture.runDir, `driver-${path.basename(file)}.txt`), readFileSync(file), { flag: 'wx' });
  capture.report.provenance.source_sha256 = Object.fromEntries(sourceFiles.map(file => [path.relative(workspace, file).replaceAll('\\', '/'), hash(readFileSync(file))]));
  writeFileSync(capture.output, JSON.stringify(capture.report, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ outcome: capture.report.outcome, exit_code: capture.report.exit_code, output: capture.output, private_native_sidecar: capture.nativeLog, error: capture.report.error }));
}

if (process.env.WIRE_HTTP_LOG) {
  const destination = path.resolve(process.env.WIRE_HTTP_LOG);
  const permitted = path.resolve(workspace, 'runs', 'wire-observation') + path.sep;
  if (!destination.startsWith(permitted)) throw new Error('Native log must remain under runs/wire-observation/');
  const fd = openSync(destination, 'wx');
  const write = record => writeSync(fd, JSON.stringify(record) + '\n');
  write({ schema_version: 'private-native-http/1', run_id: process.env.WIRE_RUN_ID, route_id: process.env.WIRE_ROUTE_ID, pid: process.pid, created_at_utc: new Date().toISOString(), role: 'evaluator-private native grading evidence', correlation: 'No added header; serial MCP request intervals plus exact native IDs; overlapping intervals remain ambiguous' });
  const originalFetch = globalThis.fetch;
  let sequence = 0;
  globalThis.fetch = async function observedFetch(input, init) {
    const start = stamp();
    const exchangeId = `native-${++sequence}`;
    const url = input instanceof Request ? input.url : String(input);
    const suppliedHeaders = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    const requestRaw = typeof init?.body === 'string' ? init.body : init?.body == null ? null : Buffer.isBuffer(init.body) || init.body instanceof Uint8Array ? Buffer.from(init.body).toString('utf8') : null;
    const request = { url, method: init?.method ?? (input instanceof Request ? input.method : 'GET'), headers: Object.fromEntries(suppliedHeaders), raw: requestRaw, json: requestRaw === null ? null : jsonOrNull(requestRaw), sha256: requestRaw === null ? null : hash(requestRaw), started_at_utc: start.utc, monotonic_ns: start.monotonic_ns, request_body_capture: requestRaw === null && init?.body != null ? 'unsupported input body type; not fabricated' : 'exact supplied fetch body' };
    const nativeProvenance = { task_namespace: request.json ? 'Native A2A fixture task ID; raw correlation is evaluator-private unless MCP itself revealed it' : 'not applicable to agent card read', context_namespace: request.json ? 'Native A2A fixture context ID; raw correlation is evaluator-private unless MCP itself revealed it' : 'not applicable to agent card read', source: { endpoint: url, method: request.json?.method ?? request.method, route_id: process.env.WIRE_ROUTE_ID, run_id: process.env.WIRE_RUN_ID }, validity_interval: null, recipient_authority: null };
    try {
      const response = await originalFetch.call(globalThis, input, init);
      const headersAt = stamp();
      const observedResponse = { status: response.status, headers: Object.fromEntries(response.headers), headers_observed_at_utc: headersAt.utc, headers_monotonic_ns: headersAt.monotonic_ns };
      // Do not delay delivery of the original response or drain its stream.
      response.clone().text().then(raw => {
        const end = stamp();
        write({ exchange_id: exchangeId, role: 'native_peer_response', ...nativeProvenance, protocol: { family: 'A2A', binding: request.json ? 'JSONRPC' : 'agent-card HTTP discovery', wire_version_request_header: suppliedHeaders.get('A2A-Version') }, request,
          response: { ...observedResponse, raw, json: jsonOrNull(raw), sha256: hash(raw), observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns }, elapsed_ms: elapsed(start, end), headers_elapsed_ms: elapsed(start, headersAt) });
      }).catch(error => write({ exchange_id: exchangeId, role: 'native_observation_failure', ...nativeProvenance, request, response: observedResponse, observation_error: error.stack ?? String(error) }));
      return response;
    } catch (error) { const end = stamp(); write({ exchange_id: exchangeId, role: 'native_request_failure', ...nativeProvenance, request, response: null, observed_at_utc: end.utc, elapsed_ms: elapsed(start, end), error: error.stack ?? String(error) }); throw error; }
  };
  process.once('exit', () => { write({ type: 'logger-exit', observed_at_utc: new Date().toISOString() }); closeSync(fd); });
}
