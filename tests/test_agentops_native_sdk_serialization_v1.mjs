// Real pinned SDK codecs/configuration with an inert transport: no fetch,
// sockets, servers, bridge processes, package installation or application run.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { nativeClientConfig, nativeMessage, nativePart, nativeSendRequest, sdkConfirmation } from '../scripts/agentops_native_profile_client_v1.mjs';

const runtimeRoot = process.env.AGENTOPS_RUNTIME_ROOT ?? path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fixtureCall = { id: 'codec-fixture-call', name: 'adk_request_confirmation' };
const fixtureOriginal = { task_id: 'codec-fixture-task', context_id: 'codec-fixture-context' };
const rationale = 'Inventory is down and INC-002 matches the service-down runbook.';
const expectedPayload = { id: fixtureCall.id, name: 'adk_request_confirmation', response: { confirmed: true, payload: { rationale } } };
const expectedLiteral = 'Yes, confirm the inventory restart. Rationale: Inventory is down and INC-002 matches the service-down runbook.';
const pins = { 'a2a-to-mcp': '1.1.0', 'mcp-a2a': '1.3.0' };
const loaded = new Map();

async function pinnedSdk(packageName) {
  if (!loaded.has(packageName)) loaded.set(packageName, (async () => {
    const root = path.join(runtimeRoot, 'external', packageName, 'node_modules/@a2a-js/sdk');
    assert.equal(JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8')).version, pins[packageName]);
    const sdk = await import(pathToFileURL(path.join(root, 'dist/index.js')).href);
    const clientSdk = await import(pathToFileURL(path.join(root, 'dist/client/index.js')).href);
    return { sdk, clientSdk };
  })());
  return loaded.get(packageName);
}

const matrix = ['amir-sync', 'amir-stream', 'mg-poll'].flatMap(profile => ['literal', 'json-text', 'data'].map(representation => ({ profile, representation })));
for (const { profile, representation } of matrix) test(`pinned SDK ${profile}/${representation}: wire part, role, IDs and configuration`, async () => {
  const { sdk, clientSdk } = await pinnedSdk(profile.startsWith('amir-') ? 'a2a-to-mcp' : 'mcp-a2a');
  const part = nativePart(representation, fixtureCall, rationale);
  const expectedPart = representation === 'data'
    ? { data: expectedPayload, metadata: { adk_type: 'function_response' } }
    : { text: representation === 'literal' ? expectedLiteral : JSON.stringify(expectedPayload), mediaType: 'text/plain' };
  assert.deepEqual(sdk.Part.toJSON(part), expectedPart);
  assert.deepEqual(sdk.Part.fromJSON(expectedPart), part);
  const message = nativeMessage(sdk.Role.ROLE_USER, part, fixtureOriginal, 'codec-fixture-message');
  const expectedMessage = { messageId: 'codec-fixture-message', contextId: fixtureOriginal.context_id,
    taskId: fixtureOriginal.task_id, role: 'ROLE_USER', parts: [expectedPart] };
  assert.deepEqual(sdk.Message.toJSON(message), expectedMessage);
  assert.deepEqual(sdk.Message.fromJSON(expectedMessage), message);
  // A numeric protobuf role matters: the wire enum string is invalid in a decoded Message.
  assert.equal(sdk.Message.toJSON({ ...message, role: 'ROLE_USER' }).role, 'UNRECOGNIZED');

  const captured = [];
  const inertTransport = { protocolVersion: '1.0',
    async sendMessage(params, options) { captured.push({ action: 'sendMessage', params, options }); return { id: fixtureOriginal.task_id }; },
    async *sendMessageStream(params, options) { captured.push({ action: 'sendMessageStream', params, options }); yield { payload: { $case: 'task', value: { id: fixtureOriginal.task_id } } }; }
  };
  const client = new clientSdk.Client(inertTransport, { capabilities: { streaming: true } }, nativeClientConfig(profile));
  const request = nativeSendRequest(message);
  if (profile === 'amir-stream') for await (const ignored of client.sendMessageStream(request)) { void ignored; }
  else await client.sendMessage(request);
  assert.equal(captured.length, 1);
  assert.equal(captured[0].action, profile === 'amir-stream' ? 'sendMessageStream' : 'sendMessage');
  assert.equal(captured[0].options.serviceParameters['A2A-Version'], '1.0');
  const expectedConfig = profile === 'mg-poll'
    ? { acceptedOutputModes: ['text/plain', 'application/json'], returnImmediately: true } : {};
  const actualWire = sdk.SendMessageRequest.toJSON(captured[0].params);
  assert.deepEqual(actualWire, { message: expectedMessage, configuration: expectedConfig });
  const decoded = sdk.SendMessageRequest.fromJSON(actualWire);
  assert.equal(decoded.configuration.returnImmediately, profile === 'mg-poll');
  assert.deepEqual(decoded.configuration.acceptedOutputModes, profile === 'mg-poll' ? ['text/plain', 'application/json'] : []);
  assert.equal(decoded.configuration.historyLength, undefined);
  assert.equal(decoded.configuration.taskPushNotificationConfig, undefined);
  assert.deepEqual(decoded.message, message);
});

for (const profile of ['mg-raw-no-header', 'mg-raw-header']) test(`pinned SDK ${profile}: polling prefix and raw omitted configuration`, async () => {
  const { sdk, clientSdk } = await pinnedSdk('mcp-a2a');
  const message = nativeMessage(sdk.Role.ROLE_USER, nativePart('data', fixtureCall, rationale), fixtureOriginal, 'codec-fixture-message');
  const rawWire = { message: { messageId: 'codec-fixture-message', role: 'ROLE_USER', taskId: fixtureOriginal.task_id,
    contextId: fixtureOriginal.context_id, parts: [{ data: expectedPayload, metadata: { adk_type: 'function_response' } }] } };
  assert.deepEqual(sdk.SendMessageRequest.fromJSON(rawWire), nativeSendRequest(message));
  assert.deepEqual(sdk.SendMessageRequest.toJSON(nativeSendRequest(message)), rawWire);
  const captured = [];
  const client = new clientSdk.Client({ protocolVersion: '1.0', async sendMessage(params) { captured.push(params); return {}; } }, {}, nativeClientConfig(profile));
  await client.sendMessage(nativeSendRequest(message));
  assert.deepEqual(sdk.SendMessageRequest.toJSON(captured[0]).configuration,
    { acceptedOutputModes: ['text/plain', 'application/json'], returnImmediately: true });
});

for (const packageName of Object.keys(pins)) test(`pinned ${packageName} SDK decodes public pending confirmation with source path intact`, async () => {
  const { sdk } = await pinnedSdk(packageName);
  const wire = { id: fixtureOriginal.task_id, contextId: fixtureOriginal.context_id, status: { state: 'TASK_STATE_INPUT_REQUIRED', message: {
    messageId: 'codec-confirmation-message', role: 'ROLE_AGENT', taskId: fixtureOriginal.task_id, contextId: fixtureOriginal.context_id,
    parts: [{ data: { ...fixtureCall, args: { hint: 'fixture' } }, metadata: { adk_type: 'function_call' } }] } } };
  const task = sdk.Task.fromJSON(wire);
  assert.equal(sdk.taskStateToJSON(task.status.state), 'TASK_STATE_INPUT_REQUIRED');
  assert.deepEqual(sdkConfirmation(task), { ...fixtureCall, part_index: 0 });
  assert.deepEqual(sdk.Task.toJSON(task), wire);
});
