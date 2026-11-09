// New exact pending-task DEVELOPMENT observation of the original licensed route.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { workspace, node22, hash, stamp, elapsed, rpcBody, deadline, pause, createCapture, launchFixture, bridgeEnvironment, stopChild, addReceipt, finishCapture } from './log-local-http.mjs';

const protocol = { mcp: '2026-07-28', mcp_transport: 'loopback HTTP modern per-request envelope', extension: 'io.modelcontextprotocol/tasks', a2a: '1.0 JSONRPC and streaming JSONRPC' };
const capture = createCapture('amirk_a2a_to_mcp', protocol, '58eff9da469bccdc432bf164662727947de646b4');
capture.report.namespaces.task = 'AmirK-S bridge opaque tk_ MCP task handle; native task ID is not revealed by this projection';
capture.report.namespaces.context = 'AmirK-S bridge opaque cx_ context handle; native context ID is private sidecar data';
const fixture = launchFixture(capture);
let bridge;
let sequence = 0;
let url;
async function post(phase, method, params = {}) {
  const id = ++sequence;
  const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method };
  if (method === 'tools/call') headers['Mcp-Name'] = params.name;
  if (method.startsWith('tasks/')) headers['Mcp-Name'] = params.taskId;
  const json = { jsonrpc: '2.0', id, method, params: { _meta: { 'io.modelcontextprotocol/protocolVersion': '2026-07-28', 'io.modelcontextprotocol/clientCapabilities': { extensions: { 'io.modelcontextprotocol/tasks': {} } }, 'io.modelcontextprotocol/clientInfo': { name: 'local-development-observer', version: '0.1.0' } }, ...params } };
  const raw = JSON.stringify(json);
  const start = stamp();
  const exchange = { exchange_id: `mcp-${id}`, phase, request: { raw, json, url, headers, started_at_utc: start.utc, monotonic_ns: start.monotonic_ns, sha256: hash(raw) }, response: null };
  capture.report.exchanges.push(exchange);
  try {
    const response = await fetch(url, { method: 'POST', headers, body: raw, signal: AbortSignal.timeout(10000) });
    const responseRaw = await response.text();
    const end = stamp();
    exchange.response = { raw: responseRaw, json: rpcBody(responseRaw, response.headers.get('content-type') ?? ''), status: response.status, headers: Object.fromEntries(response.headers), observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns, sha256: hash(responseRaw) };
    exchange.elapsed_ms = elapsed(start, end);
    assert.equal(exchange.response.json.id, id, 'MCP request/reply IDs match');
    assert(!exchange.response.json.error, responseRaw);
    assert(exchange.response.json.result, responseRaw);
    return { body: exchange.response.json.result, exchange };
  } catch (error) { exchange.error = error.stack ?? String(error); throw error; }
}
const tool = (phase, name, args) => post(phase, 'tools/call', { name, arguments: args });
async function getUntil(taskId, wanted, phase) {
  const until = Date.now() + 5000;
  do {
    const result = await post(phase, 'tasks/get', { taskId });
    addReceipt(capture, result.exchange, 'bridge_task_record', taskId, null, ['result.taskId', 'result.status', 'result.inputRequests', 'result.result', 'result.ttlMs', 'result.lastUpdatedAt']);
    if (result.body.status === wanted) return result;
    await pause(typeof result.body.pollIntervalMs === 'number' ? Math.min(result.body.pollIntervalMs, 500) : 50);
  } while (Date.now() < until);
  throw new Error(`Extension task not observed ${wanted}`);
}
try {
  const fixtureUrl = await fixture.ready;
  const config = path.join(capture.runDir, 'bridge-config.json');
  writeFileSync(config, JSON.stringify({ agents: { fixture: { url: fixtureUrl } }, host: '127.0.0.1' }), { flag: 'wx' });
  const args = ['--import', new URL('./log-local-http.mjs', import.meta.url).href, 'dist/cli.js', '--config', config, '--port', '0'];
  bridge = spawn(node22, args, { cwd: path.join(workspace, 'external', 'a2a-to-mcp'), env: bridgeEnvironment(capture), windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  bridge.stdout.on('data', chunk => { capture.diagnostics.bridge_stdout += chunk.toString(); });
  bridge.stderr.on('data', chunk => { capture.diagnostics.bridge_stderr += chunk.toString(); });
  url = await deadline(new Promise((resolve, reject) => {
    bridge.once('error', reject); bridge.once('exit', code => reject(new Error(`Bridge exited ${code} before startup`)));
    const check = () => { const match = capture.diagnostics.bridge_stdout.match(/a2a-to-mcp listening on (http:\/\/[^\s]+)/); if (match) resolve(match[1]); };
    bridge.stdout.on('data', check); check();
  }), 10000, 'bridge startup');
  capture.report.provenance.bridge_command = [node22, ...args];
  capture.report.endpoint = url;
  await post('discover_profile', 'server/discover');
  await post('discover_tools', 'tools/list');
  const created = await tool('create_ask', 'a2a_send_message', { agent: 'fixture', text: 'ask: development-destination' });
  const taskId = created.body.taskId;
  assert.equal(created.body.resultType, 'task'); assert.equal(typeof taskId, 'string');
  const waiting = await getUntil(taskId, 'input_required', 'get_input_required');
  assert.equal(waiting.body.taskId, taskId);
  const pendingGet = await tool('authoritative_get_pending', 'a2a_get_task', { agent: 'fixture', taskHandle: taskId });
  const pending = pendingGet.body.structuredContent;
  assert.equal(pending.taskHandle, taskId); assert.equal(pending.status, 'input_required');
  const contextHandle = pending.contextHandle;
  addReceipt(capture, pendingGet.exchange, 'explicit_peer_task_query', taskId, contextHandle, ['result.structuredContent.taskHandle', 'result.structuredContent.contextHandle', 'result.structuredContent.status', 'result.structuredContent.a2aState', 'result.content', 'result.structuredContent.artifacts']);
  const keys = Object.keys(waiting.body.inputRequests ?? {}); assert.equal(keys.length, 1);
  const key = keys[0];
  const input = waiting.body.inputRequests[key]; assert.equal(input.method, 'elicitation/create');
  const fields = Object.keys(input.params?.requestedSchema?.properties ?? {}); assert.equal(fields.length, 1);
  const field = fields[0]; assert.equal(input.params.requestedSchema.properties[field].type, 'string');
  const answer = 'Paris';
  capture.report.contract = { task_id: taskId, context_handle: contextHandle, input_request_key: key, requested_field: field, answer, expected_receiver_text: 'development-destination = Paris', horizon_meaning: 'One actual request and paired observed response per exchange; polling observes progression' };
  const ack = await post('same_task_answer', 'tasks/update', { taskId, inputResponses: { [key]: { action: 'accept', content: { [field]: answer } } } });
  assert.equal(ack.body.resultType, 'complete');
  capture.report.contract.answer_ack_is_completion = false;
  const completed = await getUntil(taskId, 'completed', 'get_completed_extension');
  assert.equal(completed.body.taskId, taskId);
  assert.equal(completed.body.result.structuredContent.contextHandle, contextHandle);
  assert(JSON.stringify(completed.body.result.content).includes('development-destination = Paris'));
  const refreshed = await tool('authoritative_get_completed', 'a2a_get_task', { agent: 'fixture', taskHandle: taskId });
  assert.equal(refreshed.body.structuredContent.taskHandle, taskId);
  assert.equal(refreshed.body.structuredContent.contextHandle, contextHandle);
  assert.equal(refreshed.body.structuredContent.status, 'completed');
  assert(JSON.stringify(refreshed.body.content).includes('development-destination = Paris'));
  addReceipt(capture, refreshed.exchange, 'explicit_peer_task_query', taskId, contextHandle, ['result.structuredContent.taskHandle', 'result.structuredContent.contextHandle', 'result.structuredContent.status', 'result.structuredContent.a2aState', 'result.content', 'result.structuredContent.artifacts']);
  capture.report.outcome = 'passed'; capture.report.exit_code = 0;
} catch (error) { capture.report.outcome = 'failed'; capture.report.exit_code = 1; capture.report.error = error.stack ?? String(error); process.exitCode = 1; }
finally {
  // Allow already-started asynchronous response-clone logging to finish.
  await pause(50);
  for (const child of [bridge, fixture.child]) { try { await stopChild(child); } catch (error) { capture.diagnostics.cleanup_error = error.stack ?? String(error); capture.report.exit_code = 1; process.exitCode = 1; } }
  finishCapture(capture);
}
