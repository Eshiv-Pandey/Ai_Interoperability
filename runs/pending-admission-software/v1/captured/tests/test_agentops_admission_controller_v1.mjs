// Constructed transports; no bridge, network, service or model is executed.
import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { runPublicEpisode } from '../scripts/agentops_bridge_client_v1.mjs';
import { createAdmissionController, runAdmittedEpisode, snapshotDigest } from '../scripts/agentops_admission_controller_v1.mjs';
import { SCHEMA as CLIENT_SCHEMA, executeAdmittedClient } from '../scripts/agentops_admission_client_v1.mjs';

const copy = value => JSON.parse(JSON.stringify(value));
const origin = 'http://127.0.0.1:18764';
const taskId = 'public-task', contextId = 'public-context';
const call = { id: 'public-confirmation-id', name: 'adk_request_confirmation', args: {
  originalFunctionCall: { id: 'public-restart-id', name: 'restart_service', args: { name: 'inventory' } },
  toolConfirmation: { confirmed: false } } };
const encoded = value => ({ content: [{ type: 'text', text: JSON.stringify(value) }] });
const tools = [{ name: 'a2a_send_message' }, { name: 'a2a_get_task' }, { name: 'a2a_request',
  inputSchema: { type: 'object', properties: { url: { type: 'string' },
    method: { type: 'string', enum: ['GetTask', 'SendMessage'] }, params: { type: 'object' } },
    required: ['url', 'method', 'params'] } }];
const config = () => ({ arm: 'B7', agent_alias: 'agentops', agent_base_url: origin,
  rationale: 'Inventory is down and INC-002 matches the service-down runbook.',
  admission: { deployment: { origin, header_mode: 'version-header', serializer: 'mgcrea-raw-jsonrpc/1',
    service_contract: 'agentops-inventory-confirmation-fixture/1' } },
  limits: { poll_attempts: 2, poll_interval_ms: 1 } });
function transportFixture() {
  let seq = 0;
  const fixture = { sent: [], working: false, completed: false, missingCall: false,
    changedTools: false, changedDiscovery: false, changedCall: false, sendError: false,
    async pause() {},
    async rpc(phase, method, params) {
      fixture.sent.push({ phase, method, params: copy(params) });
      let body;
      if (method === 'tools/list') {
        const advertised = copy(tools);
        if (phase.startsWith('admission_recheck') && fixture.changedTools) advertised[2].inputSchema.properties.params = { type: 'string' };
        body = { tools: advertised };
      } else if (params.name === 'a2a_discover_agent') body = encoded({ url: origin,
        card: { interfaces: [{ url: fixture.changedDiscovery ? 'http://127.0.0.1:18766/' : origin + '/', protocol: 'JSONRPC' }] } });
      else if (phase === 'initial_typed_send') body = encoded({ task: { id: taskId, context_id: contextId, state: 'submitted' } });
      else if (params.name === 'a2a_get_task') body = encoded({ id: taskId, context_id: contextId,
        state: fixture.completed ? 'completed' : fixture.working ? 'working' : 'input_required', history: [], artifacts: [] });
      else if (params.name === 'a2a_request' && params.arguments.method === 'GetTask') {
        body = encoded({ jsonrpc: '2.0', id: 'rpc-' + seq, result: { id: taskId, contextId,
          status: { state: fixture.working ? 'TASK_STATE_WORKING' : 'TASK_STATE_INPUT_REQUIRED', message: {
            parts: fixture.missingCall ? [] : [{ data: { ...call, ...(fixture.changedCall ? { id: 'different-call' } : {}) },
              metadata: { adk_type: 'function_call' } }] } } } });
      } else if (phase === 'raw_answer') {
        if (fixture.sendError) throw new Error('simulated transport failure');
        fixture.completed = true; body = encoded({ acknowledged: true });
      } else throw new Error('Unexpected mock phase: ' + phase);
      return { body, seq: ++seq, json: { jsonrpc: '2.0', id: seq, result: body } };
    } };
  return fixture;
}
const accepted = snapshot => ({ schema_version: 'pending-admission-result/1', status: 'recorded',
  decision: 'supported', certificate_valid: true, dispatch_permitted: true,
  snapshot_sha256: snapshotDigest(snapshot), request: copy(snapshot.proposed_call), profile: {}, result: {} });
const sentAnswers = transport => transport.sent.filter(item => item.phase === 'raw_answer');
const run = (transport, admit, extra = {}, cfg = config()) => runAdmittedEpisode(cfg, transport,
  () => ({}), { clock: () => 100, admit, ...extra });

test('supported independent witness sends exactly its request after four public rechecks', async () => {
  const transport = transportFixture(); let captured, witness;
  const result = await run(transport, async snapshot => {
    captured = snapshot; witness = accepted(snapshot); return witness;
  });
  assert.deepEqual(Object.keys(captured.observations).sort(), ['discovery', 'initial', 'pending', 'raw', 'tools']);
  for (const value of Object.values(captured.observations)) {
    assert.equal(value.observed_at, 100); assert(Number.isInteger(value.seq)); assert.equal(typeof value.request.method, 'string');
  }
  assert(Object.isFrozen(captured)); assert.equal(captured.valid_until, 115);
  assert.equal(result.admission.status, 'dispatched'); assert.equal(result.answer_attempts, 1);
  assert.equal(result.answer_replies, 1); assert.equal(result.answer_sent, true);
  assert.equal(result.strict_success, null); assert.equal(result.admission.claimed_live_effect, false);
  assert.equal(sentAnswers(transport).length, 1);
  assert.deepEqual(sentAnswers(transport)[0].params, witness.request.params);
  assert.equal(transport.sent.filter(item => item.phase.startsWith('admission_recheck')).length, 4);
  assert(transport.sent.findIndex(item => item.phase === 'admission_recheck_raw') < transport.sent.findIndex(item => item.phase === 'raw_answer'));
});

for (const [name, change] of [
  ['unknown', result => { result.decision = 'unknown'; result.certificate_valid = null; result.dispatch_permitted = false; result.request = null; }],
  ['unsupported', result => { result.decision = 'unsupported'; result.dispatch_permitted = false; result.request = null; }],
  ['invalid certificate', result => { result.certificate_valid = false; }],
  ['failed runner receipt', result => { result.status = 'failed'; }],
  ['dispatch forbidden', result => { result.dispatch_permitted = false; }],
  ['different snapshot', result => { result.snapshot_sha256 = '0'.repeat(64); }],
  ['different witness binding', result => { result.request.params.arguments.params.message.taskId = 'other-task'; }],
]) {
  test(`${name} causes zero continuation dispatch and overrides optimistic legacy flags`, async () => {
    const transport = transportFixture();
    const result = await run(transport, async snapshot => { const answer = accepted(snapshot); change(answer); return answer; });
    assert.equal(result.admission.status, 'blocked'); assert.equal(result.answer_attempts, 0);
    assert.equal(result.answer_sent, false); assert.equal(result.legacy_answer_attempts, 1);
    assert.equal(result.legacy_answer_sent, true); assert.equal(sentAnswers(transport).length, 0);
  });
}

for (const [name, property] of [['working state', 'working'], ['confirmation binding', 'changedCall'],
  ['raw tool schema', 'changedTools'], ['discovered endpoint', 'changedDiscovery']]) {
  test(`a changed ${name} after admission blocks the certified request`, async () => {
    const transport = transportFixture();
    const result = await run(transport, async snapshot => { transport[property] = true; return accepted(snapshot); });
    assert.equal(result.admission.status, 'blocked'); assert.equal(sentAnswers(transport).length, 0);
    assert.equal(result.answer_attempts, 0);
  });
}

test('configured route mutation during runner blocks before recheck or send', async () => {
  const cfg = config(), transport = transportFixture();
  const result = await run(transport, async snapshot => { cfg.admission.deployment.header_mode = 'passthrough'; return accepted(snapshot); }, {}, cfg);
  assert.equal(result.answer_attempts, 0); assert.equal(sentAnswers(transport).length, 0);
  assert(result.admission.blocks.some(item => item.reason.includes('configured route')));
});

test('expired evidence and bounded runner timeout both dispatch nothing', async () => {
  let clock = 100;
  const expiredTransport = transportFixture();
  const expired = await run(expiredTransport, async snapshot => { clock = 116; return accepted(snapshot); }, { clock: () => clock });
  assert.equal(expired.answer_attempts, 0); assert.equal(sentAnswers(expiredTransport).length, 0);
  const stalledTransport = transportFixture();
  const stalled = await run(stalledTransport, () => new Promise(() => {}), { timeout_ms: 10 });
  assert.equal(stalled.answer_attempts, 0); assert.equal(sentAnswers(stalledTransport).length, 0);
  assert(stalled.admission.blocks.some(item => item.reason.includes('timeout')));
});

test('missing public call never reaches admission or sends a continuation', async () => {
  const transport = transportFixture(); transport.missingCall = true;
  const result = await run(transport, () => { throw new Error('must not run'); });
  assert.equal(result.admission.status, 'not_reached'); assert.equal(result.answer_attempts, 0);
  assert.equal(result.legacy_answer_attempts, 0); assert.equal(sentAnswers(transport).length, 0);
});

test('same controller refuses a second continuation even after a successful first dispatch', async () => {
  const cfg = config(), transport = transportFixture();
  const controller = createAdmissionController(cfg, transport, () => ({}), { clock: () => 100, admit: accepted });
  await runPublicEpisode(cfg, controller.transport);
  const first = sentAnswers(transport)[0];
  await assert.rejects(controller.transport.rpc(first.phase, first.method, first.params), /already reserved or consumed/);
  assert.equal(sentAnswers(transport).length, 1); assert.equal(controller.audit.continuation_forwarded_attempts, 1);
});

test('a forwarded transport error is one attempted dispatch and zero replies, with no retry', async () => {
  const transport = transportFixture(); transport.sendError = true;
  const result = await run(transport, accepted);
  assert.equal(result.answer_attempts, 1); assert.equal(result.answer_replies, 0);
  assert.equal(result.answer_sent, null);
  assert.equal(sentAnswers(transport).length, 1); assert.equal(result.strict_success, null);
});

test('non-raw episode arms are rejected before any application request', async () => {
  const cfg = config(); cfg.arm = 'B4'; const transport = transportFixture();
  await assert.rejects(run(transport, accepted, {}, cfg), /only raw/);
  assert.equal(transport.sent.length, 0);
});

test('unexpected typed continuation, alternative raw mutation and answer phases cannot bypass admission', async () => {
  const transport = transportFixture();
  const controller = createAdmissionController(config(), transport, () => ({}), { clock: () => 100, admit: accepted });
  for (const [phase, params] of [
    ['initial_typed_send', { name: 'a2a_send_message', arguments: { url: origin, text: 'Restart inventory.', task_id: taskId } }],
    ['surprise', { name: 'a2a_send_message', arguments: { url: origin, text: 'yes', context_id: contextId } }],
    ['other_raw_method', { name: 'a2a_request', arguments: { url: origin, method: 'SendStreamingMessage', params: {} } }],
    ['another_answer_path', { name: 'unmodeled_tool', arguments: {} }],
    ['unknown_write', { name: 'a2a_respond_to_task', arguments: { task_id: taskId } }],
    ['unknown_cancel', { name: 'a2a_cancel_task', arguments: { task_id: taskId } }],
  ]) await assert.rejects(controller.transport.rpc(phase, 'tools/call', params), /unpermitted/);
  assert.equal(transport.sent.length, 0);
});

test('the transport seam permits only one exact initial send', async () => {
  const transport = transportFixture(), controller = createAdmissionController(config(), transport, () => ({}),
    { clock: () => 100, admit: accepted });
  const args = { name: 'a2a_send_message', arguments: { url: origin, text: 'Restart inventory.' } };
  await controller.transport.rpc('initial_typed_send', 'tools/call', args);
  await assert.rejects(controller.transport.rpc('initial_typed_send', 'tools/call', args), /already consumed/);
  await assert.rejects(controller.transport.rpc('direct', 'SendMessage', args), /unpermitted/);
  assert.equal(transport.sent.length, 1);
});

test('dispatch event failure does not claim an unforwarded transport attempt', async () => {
  const transport = transportFixture();
  const result = await runAdmittedEpisode(config(), transport, kind => {
    if (kind === 'admission-dispatch') throw new Error('simulated journal failure');
  }, { clock: () => 100, admit: accepted });
  assert.equal(result.answer_attempts, 0); assert.equal(result.answer_sent, false);
  assert.equal(sentAnswers(transport).length, 0); assert.equal(result.admission.status, 'blocked');
});

test('rationale mutation during public rechecks blocks dispatch', async () => {
  const cfg = config(), transport = transportFixture(), original = transport.rpc;
  transport.rpc = async (...args) => { const reply = await original(...args);
    if (args[0] === 'admission_recheck_raw') cfg.rationale = 'changed after certification'; return reply; };
  const result = await run(transport, accepted, {}, cfg);
  assert.equal(result.answer_attempts, 0); assert.equal(sentAnswers(transport).length, 0);
});

test('runner result mutation during rechecks cannot replace the frozen certified request', async () => {
  const transport = transportFixture(), original = transport.rpc; let returned;
  transport.rpc = async (...args) => {
    if (args[0] === 'admission_recheck_tools') returned.request.params.arguments.params.message.taskId = 'injected-other-task';
    return original(...args);
  };
  const result = await run(transport, snapshot => { returned = accepted(snapshot); return returned; });
  assert.equal(result.answer_attempts, 1);
  assert.equal(sentAnswers(transport)[0].params.arguments.params.message.taskId, taskId);
});

test('default Python candidate and independent checker gate mocked transport and retain new receipts', async t => {
  const directory = mkdtempSync(path.join(tmpdir(), 'agentops-admission-controller-'));
  t.after(() => { assert.equal(path.dirname(path.resolve(directory)), path.resolve(tmpdir())); rmSync(directory, { recursive: true }); });
  for (const mode of ['version-header', 'passthrough']) {
    const cfg = config(); cfg.admission.deployment.header_mode = mode;
    const transport = transportFixture(), output = path.join(directory, mode);
    const result = await runAdmittedEpisode(cfg, transport, () => ({}), { clock: () => 100,
      output_dir: output, timeout_ms: 30000, budget: 100000 });
    const receipt = JSON.parse(readFileSync(path.join(output, 'result.json'), 'utf8'));
    const snapshot = JSON.parse(readFileSync(path.join(output, 'snapshot.json'), 'utf8'));
    assert.equal(receipt.snapshot_sha256, snapshotDigest(snapshot));
    assert.equal(receipt.status, 'recorded');
    assert.equal(receipt.application_requests, 0);
    if (mode === 'version-header') {
      assert.equal(receipt.decision, 'supported'); assert.equal(receipt.certificate_valid, true);
      assert.equal(receipt.result.certificate.kind, 'recipe-path');
      assert.equal(result.answer_attempts, 1); assert.equal(sentAnswers(transport).length, 1);
      assert.equal(receipt.profile.model.provenance.kind, 'wire-derived');
    } else {
      assert.equal(receipt.decision, 'unknown'); assert.equal(receipt.certificate_valid, null);
      assert.equal(result.answer_attempts, 0); assert.equal(sentAnswers(transport).length, 0);
    }
  }
});

test('new stdio client completes a constructed MCP-process lifecycle through Python admission', async t => {
  const directory = mkdtempSync(path.join(tmpdir(), 'agentops-admitted-stdio-'));
  t.after(() => { assert.equal(path.dirname(path.resolve(directory)), path.resolve(tmpdir())); rmSync(directory, { recursive: true }); });
  // This local JSON-lines shim is an authored test worker, never a real bridge,
  // service, model client or network endpoint. It records no real restart effect.
  const worker = `
    const readline = require('node:readline');
    const tools = ${JSON.stringify(tools)}, call = ${JSON.stringify(call)};
    const origin = ${JSON.stringify(origin)}, taskId = ${JSON.stringify(taskId)}, contextId = ${JSON.stringify(contextId)};
    const encoded = value => ({content:[{type:'text',text:JSON.stringify(value)}]});
    let answered = false;
    process.on('SIGTERM', () => process.exit(0));
    readline.createInterface({input:process.stdin}).on('line', line => {
      const request = JSON.parse(line); if (!Object.hasOwn(request,'id')) return;
      const params = request.params, name = params?.name; let result;
      if (request.method === 'initialize') result = {protocolVersion:'2025-11-25'};
      else if (request.method === 'tools/list') result = {tools};
      else if (name === 'a2a_discover_agent') result = encoded({url:origin,card:{interfaces:[{url:origin+'/',protocol:'JSONRPC'}]}});
      else if (name === 'a2a_send_message') result = encoded({task:{id:taskId,context_id:contextId,state:'submitted'}});
      else if (name === 'a2a_get_task') result = encoded({id:taskId,context_id:contextId,state:answered?'completed':'input_required'});
      else if (name === 'a2a_request' && params.arguments.method === 'GetTask') result = encoded({jsonrpc:'2.0',id:request.id,
        result:{id:taskId,contextId,status:{state:'TASK_STATE_INPUT_REQUIRED',message:{parts:[{data:call,metadata:{adk_type:'function_call'}}]}}}});
      else if (name === 'a2a_request' && params.arguments.method === 'SendMessage') {answered=true;result=encoded({acknowledged:true});}
      else throw new Error('Unexpected test request');
      process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:request.id,result})+'\\n');
    });`;
  const output = path.join(directory, 'client'); mkdirSync(output);
  const cfg = { ...config(), schema_version: CLIENT_SCHEMA, output_dir: output,
    bridge: { command: process.execPath, args: ['-e', worker], cwd: directory, env: { ...process.env } },
    limits: { request_timeout_ms: 10000, poll_interval_ms: 1, poll_attempts: 2,
      total_timeout_ms: 30000, max_response_bytes: 1048576 } };
  cfg.admission = { ...cfg.admission, python: 'python', budget: 100000, timeout_ms: 10000 };
  const events = []; let seq = 0;
  const result = await executeAdmittedClient(cfg, { emit: (kind, value) => {
    const event = { seq: ++seq, kind, ...value }; events.push(event); return event;
  } });
  assert.equal(result.admission.status, 'dispatched'); assert.equal(result.answer_attempts, 1);
  assert.equal(result.answer_replies, 1); assert.equal(result.final_state, 'completed');
  assert.equal(result.child.clean_exit, true); assert.equal(result.live_effect_verified_by_client, false);
  assert.equal(result.continuation_stdin_write_completions, 1); assert.equal(result.answer_sent, true);
  assert.equal(events.filter(event => event.kind === 'admission-dispatch').length, 1);
});

test('a Python receipt larger than the configured bound is retained but cannot dispatch', async t => {
  const directory = mkdtempSync(path.join(tmpdir(), 'agentops-admission-result-bound-'));
  t.after(() => { assert.equal(path.dirname(path.resolve(directory)), path.resolve(tmpdir())); rmSync(directory, { recursive: true }); });
  const transport = transportFixture(), output = path.join(directory, 'admission');
  const result = await runAdmittedEpisode(config(), transport, () => ({}), { clock: () => 100,
    output_dir: output, timeout_ms: 30000, budget: 100000, max_output_bytes: 1024 });
  assert.equal(result.answer_attempts, 0); assert.equal(sentAnswers(transport).length, 0);
  assert(result.admission.blocks.some(item => item.reason.includes('result file exceeds')));
  assert(readFileSync(path.join(output, 'result.json')).length > 1024);
});
