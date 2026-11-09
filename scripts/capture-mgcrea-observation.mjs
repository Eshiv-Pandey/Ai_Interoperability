// New exact pending-task DEVELOPMENT observation over genuine MCP stdio.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { workspace, node22, hash, stamp, elapsed, deadline, pause, createCapture, launchFixture, bridgeEnvironment, stopChild, addReceipt, finishCapture } from './log-local-http.mjs';

const capture = createCapture('mgcrea_mcp_a2a', { mcp: '2025-11-25', mcp_transport: 'actual child-process stdio', extension: 'not used; ordinary tools', a2a: '1.0 JSONRPC over real loopback HTTP' }, 'c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5');
capture.report.namespaces.task = 'Native A2A task UUID returned visibly through MCP tool projection';
capture.report.namespaces.context = 'Native A2A context UUID returned visibly as context_id through MCP';
const fixture = launchFixture(capture);
let bridge;
let sequence = 0;
let incoming = '';
const pending = new Map();
function receive(chunk) {
  incoming += chunk.toString();
  for (;;) {
    const newline = incoming.indexOf('\n'); if (newline < 0) return;
    const raw = incoming.slice(0, newline + 1); incoming = incoming.slice(newline + 1);
    const end = stamp();
    let json;
    try { json = JSON.parse(raw); } catch (error) { capture.diagnostics.unparsed_stdout = (capture.diagnostics.unparsed_stdout ?? '') + raw; continue; }
    const waiting = pending.get(json.id);
    if (waiting) {
      pending.delete(json.id);
      waiting.exchange.response = { raw, json, observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns, sha256: hash(raw) };
      waiting.exchange.elapsed_ms = elapsed(waiting.start, end);
      waiting.resolve({ body: json.result, exchange: waiting.exchange, json });
    } else capture.report.exchanges.push({ exchange_id: `mcp-unsolicited-${capture.report.exchanges.length + 1}`, phase: 'unsolicited_notification_or_reply', request: null, response: { raw, json, observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns, sha256: hash(raw) } });
  }
}
async function rpc(phase, method, params, notification = false) {
  const id = notification ? undefined : ++sequence;
  const json = { jsonrpc: '2.0', ...(id === undefined ? {} : { id }), method, ...(params === undefined ? {} : { params }) };
  const raw = JSON.stringify(json) + '\n';
  const start = stamp();
  const exchange = { exchange_id: notification ? `mcp-notification-${capture.report.exchanges.length + 1}` : `mcp-${id}`, phase, request: { raw, json, started_at_utc: start.utc, monotonic_ns: start.monotonic_ns, sha256: hash(raw) }, response: null };
  capture.report.exchanges.push(exchange);
  const answer = notification ? null : new Promise((resolve, reject) => pending.set(id, { resolve, reject, exchange, start }));
  await new Promise((resolve, reject) => bridge.stdin.write(raw, error => error ? reject(error) : resolve()));
  if (notification) return { exchange };
  try {
    const result = await deadline(answer, 10000, `MCP ${method}`);
    assert.equal(result.json.id, id); assert(!result.json.error, JSON.stringify(result.json)); assert(result.body, JSON.stringify(result.json));
    return result;
  } catch (error) { exchange.error = error.stack ?? String(error); throw error; }
}
async function tool(phase, name, args) {
  const result = await rpc(phase, 'tools/call', { name, arguments: args });
  assert(!result.body.isError && !result.body.isToolError, JSON.stringify(result.body));
  const body = result.body.structuredContent ?? JSON.parse(result.body.content.find(block => block.type === 'text').text);
  return { ...result, object: body };
}
async function read(taskId, refresh, phase) {
  const result = await tool(phase, 'a2a_get_task', { task_id: taskId, refresh });
  addReceipt(capture, result.exchange, refresh ? 'explicit_peer_task_query' : 'local_mirror', taskId, result.object.context_id, result.body.structuredContent ? ['result.structuredContent'] : ['result.content[0].text']);
  const receipt = capture.report.receipts.at(-1);
  receipt.bundle_encoding = result.body.structuredContent ? 'structuredContent object' : 'JSON serialized inside MCP text content';
  receipt.decoded_bundle_fields = Object.keys(result.object);
  return result;
}
async function observe(taskId, wanted, phase) {
  const until = Date.now() + 5000;
  do { const result = await read(taskId, true, phase); if (result.object.state === wanted) return result; await pause(50); } while (Date.now() < until);
  throw new Error(`Refreshed task not observed ${wanted}`);
}
try {
  const fixtureUrl = await fixture.ready;
  const args = ['--import', new URL('./log-local-http.mjs', import.meta.url).href, 'dist/cli.js'];
  const stateDir = path.join(capture.runDir, 'state');
  const env = bridgeEnvironment(capture, { A2A_CONFIG: path.join(capture.runDir, 'absent-config.json'), A2A_STATE_DIR: stateDir, A2A_DAEMON_URL: fixtureUrl, A2A_PEERS: fixtureUrl, A2A_ALLOW_WRITES: '1', A2A_CHANNEL: '0', A2A_MAX_RETRIES: '0' });
  bridge = spawn(node22, args, { cwd: path.join(workspace, 'external', 'mcp-a2a'), env, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  bridge.stdout.on('data', receive);
  bridge.stderr.on('data', chunk => { capture.diagnostics.bridge_stderr += chunk.toString(); });
  bridge.on('error', error => { for (const item of pending.values()) item.reject(error); });
  bridge.on('exit', code => { for (const item of pending.values()) item.reject(new Error(`Bridge exited ${code}`)); });
  capture.report.provenance.bridge_command = [node22, ...args];
  capture.report.configuration = { writes: true, channel: false, retries: 0, token: 'unset; isolated environment', state_directory: path.relative(workspace, stateDir).replaceAll('\\', '/') };
  const initialized = await rpc('initialize', 'initialize', { protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'local-development-raw-observer', version: '0.1.0' } });
  assert.equal(initialized.body.protocolVersion, '2025-11-25');
  await rpc('initialized_notification', 'notifications/initialized', undefined, true);
  const tools = await rpc('discover_tools', 'tools/list', {});
  assert(tools.body.tools.some(item => item.name === 'a2a_send_message'));
  const created = await tool('create_ask', 'a2a_send_message', { url: fixtureUrl, text: 'ask: development-destination' });
  assert.equal(created.object.replied_with, 'task');
  const taskId = created.object.task.id;
  const contextId = created.object.task.context_id;
  assert.equal(typeof taskId, 'string');
  const initialMirror = await read(taskId, false, 'local_mirror_before_pending_refresh');
  const waiting = await observe(taskId, 'input_required', 'authoritative_get_input_required');
  assert.equal(waiting.object.id, taskId);
  const boundContext = waiting.object.context_id;
  assert.equal(typeof boundContext, 'string');
  if (contextId) assert.equal(boundContext, contextId);
  capture.report.contract = { task_id: taskId, context_id: boundContext, answer: 'Paris', expected_receiver_text: 'development-destination = Paris', horizon_meaning: 'One actual request and paired observed response per exchange; polling observes progression', initial_mirror_state: initialMirror.object.state };
  const answered = await tool('same_task_answer', 'a2a_send_message', { url: fixtureUrl, text: 'Paris', task_id: taskId, context_id: boundContext });
  assert.equal(answered.object.task.id, taskId);
  assert.equal(answered.object.task.context_id, boundContext);
  capture.report.contract.answer_ack_is_completion = answered.object.task.state === 'completed' && JSON.stringify(answered.object.task.artifacts).includes('development-destination = Paris');
  const mirrorAfterAnswer = await read(taskId, false, 'local_mirror_after_answer_before_refresh');
  const completed = await observe(taskId, 'completed', 'authoritative_get_completed');
  assert.equal(completed.object.id, taskId); assert.equal(completed.object.context_id, boundContext);
  assert(JSON.stringify(completed.object.artifacts).includes('development-destination = Paris'));
  const mirrorAfterRefresh = await read(taskId, false, 'local_mirror_after_completed_refresh');
  assert.equal(mirrorAfterRefresh.object.state, 'completed');
  assert(JSON.stringify(mirrorAfterRefresh.object.artifacts).includes('development-destination = Paris'));
  capture.report.observed_states = { create_ask: created.object.task.state, initial_mirror: initialMirror.object.state, refreshed_pending: waiting.object.state, answer_reply: answered.object.task.state, mirror_after_answer: mirrorAfterAnswer.object.state, refreshed_completed: completed.object.state, mirror_after_refresh: mirrorAfterRefresh.object.state };
  capture.report.outcome = 'passed'; capture.report.exit_code = 0;
} catch (error) { capture.report.outcome = 'failed'; capture.report.exit_code = 1; capture.report.error = error.stack ?? String(error); process.exitCode = 1; }
finally {
  await pause(50);
  for (const child of [bridge, fixture.child]) { try { await stopChild(child); } catch (error) { capture.diagnostics.cleanup_error = error.stack ?? String(error); capture.report.exit_code = 1; process.exitCode = 1; } }
  finishCapture(capture);
}
