// Constructed public-MCP policy tests; no server/process/socket/application launches.
import assert from 'node:assert/strict';
import test from 'node:test';
import { confirmationPayload, decodeTool, findAmirConfirmation, findRawConfirmation,
  formAnswer, LITERAL_ANSWER, runPublicEpisode } from '../scripts/agentops_bridge_client_v1.mjs';
import { createVersionFetch } from '../scripts/agentops_mgcrea_embed_v1.mjs';

const call = { id: 'public-confirmation-id', name: 'adk_request_confirmation' };
const taskId = 'public-task', contextId = 'public-context';
const taskHandle = 'tk_public', contextHandle = 'cx_public';
const rationale = 'Inventory is down and INC-002 matches the service-down runbook.';
const form = { answer: { method: 'elicitation/create', params: { mode: 'form', message: '',
  requestedSchema: { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] } } } };
const task = { id: taskId, contextId, status: { state: 'TASK_STATE_INPUT_REQUIRED', message: {
  parts: [{ data: call, metadata: { adk_type: 'function_call' } }] } } };
const envelope = (state = 'INPUT_REQUIRED') => ({ content: [{ type: 'text', text: JSON.stringify(call),
  _meta: { 'io.github.amirk-s/a2a': { partKind: 'data', metadata: { adk_type: 'function_call' } } } }],
  structuredContent: { kind: 'task', taskHandle, contextHandle, status: state.toLowerCase(), a2aState: 'TASK_STATE_' + state } });
const encoded = value => ({ content: [{ type: 'text', text: JSON.stringify(value) }] });
const tools = [{ name: 'a2a_send_message' }, { name: 'a2a_get_task' }, { name: 'a2a_request',
  inputSchema: { properties: { method: { enum: ['GetTask', 'SendMessage'] } } } }];

function mockTransport(arm, { rawIdVisible = arm === 'B7', amirIdVisible = true } = {}) {
  let seq = 0, answered = false;
  const sent = [];
  return { sent, async pause() {}, async rpc(phase, method, params) {
    sent.push({ phase, method, params });
    let body;
    if (method === 'tools/list') body = { tools };
    else if (params.name === 'a2a_discover_agent') body = encoded({ card: {} });
    else if (phase === 'initial_typed_send') body = arm === 'B3'
      ? { resultType: 'input_required', requestState: 'opaque-never-decoded', inputRequests: form }
      : arm === 'B2' ? { taskId: taskHandle } : arm === 'B1' ? envelope()
        : encoded({ task: { id: taskId, context_id: contextId, state: 'submitted' } });
    else if (phase === 'pending_origin_get' || phase === 'final_origin_get') {
      const state = answered ? 'COMPLETED' : 'INPUT_REQUIRED';
      if (['B1', 'B2', 'B3'].includes(arm)) { body = envelope(state); if (!amirIdVisible) body.content = []; }
      else body = encoded({ id: taskId, context_id: contextId, state: state.toLowerCase(), history: [], artifacts: [] });
    } else if (phase === 'public_raw_get') body = rawIdVisible ? encoded({ jsonrpc: '2.0', id: 'native-rpc', result: task })
      : { ...encoded({ error: 'VersionNotSupported', status: 500 }), isError: true };
    else if (phase === 'pending_tasks_form') body = { taskId: taskHandle, status: 'input_required', inputRequests: form };
    else if (phase === 'post_answer_tasks_get') body = { taskId: taskHandle, status: 'completed' };
    else if (['typed_answer', 'raw_answer', 'tasks_answer', 'mrtr_answer'].includes(phase)) {
      answered = true; body = ['B1', 'B3'].includes(arm) ? envelope('COMPLETED') : encoded({ acknowledged: true });
    } else throw new Error('Unexpected mock phase ' + phase);
    return { body, seq: ++seq, json: { jsonrpc: '2.0', id: seq, result: body } };
  } };
}
const configFor = arm => ({ arm, agent_alias: 'agentops', agent_base_url: 'http://127.0.0.1:18764', rationale,
  limits: { poll_attempts: 2, poll_interval_ms: 1 } });

for (const arm of ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']) {
  test(`${arm} uses only its permitted public continuation`, async () => {
    const transport = mockTransport(arm);
    const events = [];
    const result = await runPublicEpisode(configFor(arm), transport, (kind, value) => events.push({ kind, ...value }));
    assert.equal(result.strict_success, null);
    assert.equal(result.final_public_association_preserved, true);
    if (['B5', 'B6'].includes(arm)) {
      assert.equal(result.status, 'public_binding_not_observed');
      assert.equal(result.answer_attempts, 0);
      assert(!transport.sent.some(item => item.phase === 'raw_answer'));
      assert(!result.bindings.some(item => item.name === 'confirmation_call_id'));
    } else {
      assert.equal(result.answer_attempts, 1);
      const answer = transport.sent.find(item => /^(typed|raw|tasks|mrtr)_answer$/.test(item.phase));
      if (arm === 'B7') {
        assert.deepEqual(answer.params.arguments.params.message.parts, [{ data: confirmationPayload(call, rationale), metadata: { adk_type: 'function_response' } }]);
        assert.equal(answer.params.arguments.params.message.taskId, taskId);
      } else if (arm === 'B2') assert.equal(answer.params.inputResponses.answer.content.answer, JSON.stringify(confirmationPayload(call, rationale)));
      else if (arm === 'B3') {
        assert.equal(answer.params.requestState, 'opaque-never-decoded');
        assert.equal(answer.params.inputResponses.answer.content.answer, LITERAL_ANSWER);
        assert(!result.bindings.some(item => item.name === 'confirmation_call_id'));
      } else assert.equal(answer.params.arguments.text, arm === 'B1' ? JSON.stringify(confirmationPayload(call, rationale)) : LITERAL_ANSWER);
    }
    assert(events.filter(item => item.kind === 'public-binding').every(item => Number.isInteger(item.source.seq)));
  });
}

test('Amir text fallback never invents a call ID', async () => {
  const transport = mockTransport('B1', { amirIdVisible: false });
  const result = await runPublicEpisode(configFor('B1'), transport);
  assert.equal(result.public_confirmation_observed, false);
  assert.equal(result.answer_representation, 'literal_fallback');
  assert.equal(transport.sent.find(item => item.phase === 'typed_answer').params.arguments.text, LITERAL_ANSWER);
});

test('raw public ID must belong to the previously received task and context', () => {
  const reply = { seq: 17, body: encoded({ result: { ...task, id: 'other-task' } }) };
  assert.throws(() => findRawConfirmation(decodeTool(reply), { task_id: taskId, context_id: contextId }), /association/);
  const valid = findRawConfirmation(decodeTool({ seq: 18, body: encoded({ result: task }) }), { task_id: taskId, context_id: contextId });
  assert.equal(valid.source.seq, 18);
  assert.deepEqual(valid.source.path, ['result', 'content', 0, 'text']);
  assert.deepEqual(valid.source.decoded_path, ['result', 'status', 'message', 'parts', 0, 'data', 'id']);
});

test('lookalike plain text and conflicting tagged call IDs are not trusted', () => {
  assert.equal(findAmirConfirmation({ seq: 1, body: { content: [{ type: 'text', text: JSON.stringify(call) }] } }), null);
  const value = envelope();
  value.content.push({ ...value.content[0], text: JSON.stringify({ ...call, id: 'other-id' }) });
  assert.throws(() => findAmirConfirmation({ seq: 2, body: value }), /Ambiguous/);
});

test('form response obeys public field and rejects an unexpected schema', () => {
  assert.deepEqual(formAnswer({ inputRequests: form }, 'yes').responses, { answer: { action: 'accept', content: { answer: 'yes' } } });
  assert.throws(() => formAnswer({ inputRequests: {} }, 'yes'), /one public form/);
});

test('B6 passes fetch arguments by identity and B7 changes only scoped version header', async () => {
  const calls = [];
  const implementation = (...args) => { calls.push(args); return Promise.resolve('reply'); };
  const init = { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"x":1}' };
  await createVersionFetch('http://127.0.0.1:18764', 'passthrough', implementation)('http://127.0.0.1:18764/', init);
  assert.equal(calls[0][1], init);
  const fixed = createVersionFetch('http://127.0.0.1:18764', 'version-header', implementation);
  await fixed('http://127.0.0.1:18764/', init);
  assert.equal(calls[1][1].body, init.body);
  assert.equal(calls[1][1].method, init.method);
  assert.equal(calls[1][1].headers.get('A2A-Version'), '1.0');
  assert.equal(calls[1][1].headers.get('content-type'), 'application/json');
  await fixed('http://127.0.0.1:18766/', init);
  assert.equal(calls[2][1], init);
  assert.deepEqual(init.headers, { 'content-type': 'application/json' });
});
