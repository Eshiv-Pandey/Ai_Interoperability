// Authored public-SDK policy tests. These do not import third-party SDKs or open a socket.
import assert from 'node:assert/strict';
import test from 'node:test';
import { nativeMessage, nativePart, runNativeEpisode, sdkConfirmation } from '../scripts/agentops_native_profile_client_v1.mjs';
import { confirmationPayload, INITIAL_TEXT, LITERAL_ANSWER } from '../scripts/agentops_bridge_client_v1.mjs';

const call = { id: 'public-call', name: 'adk_request_confirmation' };
const rationale = 'Inventory is down and INC-002 matches the service-down runbook.';
const pending = { id: 'public-task', contextId: 'public-context', status: { state: 'input_required', message: {
  parts: [{ content: { $case: 'data', value: call }, metadata: { adk_type: 'function_call' } }] } } };
const matrix = ['amir-sync', 'amir-stream', 'mg-poll'].flatMap(profile => ['literal', 'json-text', 'data'].map(representation => ({ profile, representation })))
  .concat([{ profile: 'mg-raw-no-header', representation: 'data' }, { profile: 'mg-raw-header', representation: 'data' }]);

for (const row of matrix) test(`${row.profile}/${row.representation} retains the frozen representation and public IDs`, async () => {
  const commands = []; let resumed = false, msg = 0, seq = 0;
  const adapter = {
    userRole: 1, messageId: () => 'native-message-' + (++msg), stateName: value => value, async pause() {},
    async send(message) { commands.push({ action: 'send', message });
      if (commands.length > 1) resumed = true;
      return pending; },
    async get(id) { commands.push({ action: 'get', id }); return resumed
      ? { ...pending, status: { state: 'completed' } } : pending; },
    async rawSend(args) { commands.push({ action: 'rawSend', args }); resumed = args.version === '1.0';
      return { status: 200, body: resumed ? { result: {} } : { error: { code: -32009 } } }; }
  };
  const events = [];
  const config = { ...row, rationale, limits: { poll_attempts: 2, poll_interval_ms: 1 } };
  const result = await runNativeEpisode(config, adapter, (kind, value) => {
    const event = { seq: ++seq, kind, ...value }; events.push(event); return event;
  });
  assert.equal(commands[0].message.parts[0].content.value, INITIAL_TEXT);
  assert.equal(result.answer_attempts, 1);
  assert.equal(result.strict_success, null);
  assert.equal(result.final_public_association_preserved, true);
  const response = commands.find((item, index) => index > 0 && ['send', 'rawSend'].includes(item.action));
  if (row.profile.startsWith('mg-raw')) {
    assert.equal(response.args.version, row.profile === 'mg-raw-header' ? '1.0' : null);
    assert.deepEqual(response.args.params.message.parts, [{ data: confirmationPayload(call, rationale), metadata: { adk_type: 'function_response' } }]);
    assert.equal(response.args.params.message.taskId, pending.id);
    assert.equal(response.args.params.message.contextId, pending.contextId);
  } else {
    assert.equal(response.message.taskId, pending.id);
    assert.equal(response.message.contextId, pending.contextId);
    assert.deepEqual(response.message.referenceTaskIds, []);
    const part = response.message.parts[0];
    if (row.representation === 'literal') assert.equal(part.content.value, LITERAL_ANSWER);
    else if (row.representation === 'json-text') assert.equal(part.content.value, JSON.stringify(confirmationPayload(call, rationale)));
    else { assert.deepEqual(part.content.value, confirmationPayload(call, rationale)); assert.equal(part.metadata.adk_type, 'function_response'); }
  }
  for (const binding of result.bindings) {
    const source = events.find(item => item.seq === binding.source.seq);
    assert(source && source.kind === 'sdk-result');
    assert.equal(binding.source.path.reduce((value, key) => value[key], source), binding.value);
  }
});

test('SDK confirmation extraction rejects untagged, missing and ambiguous calls', () => {
  assert.throws(() => sdkConfirmation({ ...pending, status: { message: { parts: [] } } }), /one public/);
  const repeated = structuredClone(pending);
  repeated.status.message.parts.push(repeated.status.message.parts[0]);
  assert.throws(() => sdkConfirmation(repeated), /one public/);
  const untagged = structuredClone(pending);
  delete untagged.status.message.parts[0].metadata;
  assert.throws(() => sdkConfirmation(untagged), /one public/);
});

test('native text and data have distinct actual part kinds with matching message invariants', () => {
  assert.equal(nativePart('json-text', call, rationale).content.$case, 'text');
  assert.equal(nativePart('data', call, rationale).content.$case, 'data');
  const message = nativeMessage(1, nativePart('literal', call, rationale), null, 'new-message');
  assert.equal(message.parts[0].mediaType, 'text/plain');
  assert.equal(message.taskId, '');
  assert.equal(message.contextId, '');
  assert.deepEqual(message.extensions, []);
  assert.deepEqual(message.referenceTaskIds, []);
});
