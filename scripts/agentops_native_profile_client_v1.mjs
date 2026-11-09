// Eleven prospectively selectable native profile/representation controls.
// No startup, SDK import or request occurs when this module is imported.
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { closeSync, mkdirSync, openSync, readFileSync, writeFileSync, writeSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';
import { confirmationPayload, INITIAL_TEXT, LITERAL_ANSWER } from './agentops_bridge_client_v1.mjs';

export const NATIVE_SCHEMA = 'agentops-native-profile-client-config/1';
const profiles = ['amir-sync', 'amir-stream', 'mg-poll', 'mg-raw-no-header', 'mg-raw-header'];
const representations = ['literal', 'json-text', 'data'];
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.length > 0;
const errorText = error => String(error?.stack ?? error);
const entity = raw => ({ base64: raw.toString('base64'), bytes: raw.length,
  sha256: createHash('sha256').update(raw).digest('hex') });

export function validateNativeConfig(config) {
  assert(isObject(config) && config.schema_version === NATIVE_SCHEMA);
  assert(profiles.includes(config.profile) && representations.includes(config.representation));
  assert(!config.profile.startsWith('mg-raw') || config.representation === 'data');
  assert(path.isAbsolute(config.runtime_root) && path.isAbsolute(config.output_dir));
  const origin = new URL(config.agent_base_url);
  assert(origin.protocol === 'http:' && origin.hostname === '127.0.0.1' && origin.port
    && origin.pathname === '/' && !origin.username && !origin.password && !origin.search && !origin.hash);
  assert(nonempty(config.rationale));
  for (const [key, upper] of Object.entries({ request_timeout_ms: 45000, poll_interval_ms: 2000,
    poll_attempts: 60, total_timeout_ms: 300000, max_response_bytes: 33554432 })) {
    assert(Number.isInteger(config.limits?.[key]) && config.limits[key] > 0 && config.limits[key] <= upper, `Invalid limit ${key}`);
  }
  return config;
}

export function nativePart(representation, call, rationale) {
  if (representation === 'literal') return { content: { $case: 'text', value: LITERAL_ANSWER },
    metadata: undefined, filename: '', mediaType: 'text/plain' };
  const value = confirmationPayload(call, rationale);
  if (representation === 'json-text') return { content: { $case: 'text', value: JSON.stringify(value) },
    metadata: undefined, filename: '', mediaType: 'text/plain' };
  assert.equal(representation, 'data');
  return { content: { $case: 'data', value }, metadata: { adk_type: 'function_response' }, filename: '', mediaType: '' };
}

export function nativeMessage(role, part, original, messageId) {
  return { messageId, contextId: original?.context_id ?? '', taskId: original?.task_id ?? '',
    role, parts: [part], metadata: undefined, extensions: [], referenceTaskIds: [] };
}

export function nativeClientConfig(profile) {
  assert(profiles.includes(profile), 'Unknown native profile');
  return profile.startsWith('amir-') ? undefined
    : { polling: true, acceptedOutputModes: ['text/plain', 'application/json'] };
}

export function nativeSendRequest(message) {
  return { tenant: '', message, configuration: undefined, metadata: undefined };
}

export function sdkConfirmation(task) {
  assert(nonempty(task?.id) && nonempty(task?.contextId), 'Missing native public task/context');
  const candidates = [];
  for (const [index, part] of (task.status?.message?.parts ?? []).entries()) {
    const data = part.content?.$case === 'data' ? part.content.value : undefined;
    if (part.metadata?.adk_type === 'function_call' && data?.name === 'adk_request_confirmation' && nonempty(data.id)) {
      candidates.push({ id: data.id, name: data.name, part_index: index });
    }
  }
  assert.equal(candidates.length, 1, 'Expected one public native confirmation request');
  return candidates[0];
}

export async function runNativeEpisode(config, adapter, emit) {
  const result = { profile: config.profile, representation: config.representation, answer_attempts: 0,
    strict_success: null, strict_success_requires_external_effect_check: true, bindings: [], errors: [] };
  const invoke = async (phase, action, args) => {
    emit('sdk-call', { phase, action, arguments: args });
    try { const value = await adapter[action](args); const event = emit('sdk-result', { phase, action, value });
      return { value, seq: event.seq }; }
    catch (error) { emit('sdk-error', { phase, action, error: errorText(error) }); throw error; }
  };
  const bind = (name, value, seq, sourcePath) => {
    assert(nonempty(value), 'Missing binding ' + name);
    const binding = { name, value, source: { seq, path: ['value', ...sourcePath] } };
    result.bindings.push(binding); emit('public-binding', binding); return value;
  };
  const originalPart = { content: { $case: 'text', value: INITIAL_TEXT }, metadata: undefined, filename: '', mediaType: 'text/plain' };
  const startMessage = nativeMessage(adapter.userRole, originalPart, null, adapter.messageId());
  const sent = await invoke('start', 'send', startMessage);
  let task = sent.value;
  if (!nonempty(task?.id) || !nonempty(task?.contextId)) { result.status = 'no_public_native_task'; return result; }
  const original = { task_id: bind('task_id', task.id, sent.seq, ['id']),
    context_id: bind('context_id', task.contextId, sent.seq, ['contextId']) };
  let pending;
  for (let index = 0; index < config.limits.poll_attempts; index++) {
    const read = await invoke('get-pending', 'get', original.task_id);
    task = read.value;
    assert(task.id === original.task_id && task.contextId === original.context_id, 'Native task/context changed');
    const state = adapter.stateName(task.status?.state);
    if (state === 'input_required') { pending = read; break; }
    if (!['working', 'submitted'].includes(state)) { result.status = 'initial_state_not_pending'; result.initial_state = state; return result; }
    if (index + 1 < config.limits.poll_attempts) await adapter.pause(config.limits.poll_interval_ms);
  }
  if (!pending) { result.status = 'pending_observation_bound_reached'; return result; }
  const call = sdkConfirmation(pending.value);
  bind('confirmation_call_id', call.id, pending.seq, ['status', 'message', 'parts', call.part_index, 'content', 'value', 'id']);
  bind('confirmation_call_name', call.name, pending.seq, ['status', 'message', 'parts', call.part_index, 'content', 'value', 'name']);
  result.public_original = original;
  const message = nativeMessage(adapter.userRole, nativePart(config.representation, call, config.rationale), original, adapter.messageId());
  result.answer_attempts = 1;
  try {
    if (config.profile.startsWith('mg-raw')) {
      const params = { message: { messageId: message.messageId, role: 'ROLE_USER', taskId: original.task_id,
        contextId: original.context_id, parts: [{ data: confirmationPayload(call, config.rationale), metadata: { adk_type: 'function_response' } }] } };
      const answer = await invoke('resume-raw', 'rawSend', { params, version: config.profile === 'mg-raw-header' ? '1.0' : null });
      result.answer_reply_seq = answer.seq;
    } else {
      const answer = await invoke('resume', 'send', message);
      result.answer_reply_seq = answer.seq;
    }
  } catch (error) { result.errors.push({ phase: 'resume', error: errorText(error) }); }
  for (let index = 0; index < config.limits.poll_attempts; index++) {
    let final;
    try { final = await invoke('get-completed', 'get', original.task_id); }
    catch (error) { result.errors.push({ phase: 'get-completed', error: errorText(error) }); break; }
    result.final_reply_seq = final.seq;
    result.final_state = adapter.stateName(final.value.status?.state);
    result.final_public_association_preserved = final.value.id === original.task_id && final.value.contextId === original.context_id;
    if (!['working', 'submitted'].includes(result.final_state)) break;
    if (index + 1 < config.limits.poll_attempts) await adapter.pause(config.limits.poll_interval_ms);
  }
  result.status = result.errors.length ? 'recorded_with_client_errors' : 'recorded';
  return result;
}

function createJournal(directory) {
  const fd = openSync(path.join(directory, 'sdk.jsonl'), 'wx'); let seq = 0;
  return { emit(kind, value = {}) { const event = { schema_version: 'agentops-native-profile-event/1', seq: ++seq,
    at_utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString(), kind, ...value };
    writeSync(fd, JSON.stringify(event) + '\n'); return event; }, close() { closeSync(fd); } };
}

async function buildAdapter(config, journal) {
  const amir = config.profile.startsWith('amir-');
  const packageRoot = path.join(config.runtime_root, 'external', amir ? 'a2a-to-mcp' : 'mcp-a2a');
  const sdkRoot = path.join(packageRoot, 'node_modules/@a2a-js/sdk/dist');
  const sdk = await import(pathToFileURL(path.join(sdkRoot, 'index.js')).href);
  const clientSdk = await import(pathToFileURL(path.join(sdkRoot, 'client/index.js')).href);
  const deadline = Date.now() + config.limits.total_timeout_ms;
  const left = () => { const value = deadline - Date.now(); assert(value > 0, 'Native total deadline reached'); return value; };
  let requestSignal;
  const boundedFetch = (input, init = {}) => {
    const target = new URL(input instanceof Request ? input.url : String(input));
    assert.equal(target.origin, new URL(config.agent_base_url).origin, 'Native request escaped frozen original origin');
    const signal = requestSignal ?? AbortSignal.timeout(Math.min(config.limits.request_timeout_ms, left()));
    return fetch(input, { ...init, signal: init.signal ? AbortSignal.any([init.signal, signal]) : signal, redirect: 'error' });
  };
  const bounded = async operation => {
    requestSignal = AbortSignal.timeout(Math.min(config.limits.request_timeout_ms, left()));
    try { return await operation(); } finally { requestSignal = undefined; }
  };
  let card, client, fetchImpl = boundedFetch;
  if (amir) {
    const { AgentCardResolver } = await import(pathToFileURL(path.join(packageRoot, 'dist/agent-card.js')).href);
    const resolver = new AgentCardResolver({ agents: { agentops: { cardUrl: new URL('/.well-known/agent-card.json', config.agent_base_url).href } }, fetchImpl });
    const resolved = await bounded(() => resolver.get('agentops'));
    card = resolved.card;
    client = await new clientSdk.ClientFactory({ transports: [new clientSdk.JsonRpcTransportFactory({ fetchImpl })],
      preferredTransports: ['JSONRPC'], clientConfig: nativeClientConfig(config.profile) }).createFromAgentCard(card);
  } else {
    const { createA2AFetch, USER_AGENT } = await import(pathToFileURL(path.join(packageRoot, 'dist/index.js')).href);
    fetchImpl = createA2AFetch({ maxRetries: 0, userAgent: USER_AGENT, token: undefined, fetch: boundedFetch });
    const resolver = new clientSdk.DefaultAgentCardResolver({ fetchImpl });
    card = await bounded(() => resolver.resolve(config.agent_base_url));
    client = await new clientSdk.ClientFactory(clientSdk.ClientFactoryOptions.createFrom(clientSdk.ClientFactoryOptions.default, {
      transports: [new clientSdk.JsonRpcTransportFactory({ fetchImpl }), new clientSdk.RestTransportFactory({ fetchImpl })],
      clientConfig: nativeClientConfig(config.profile), cardResolver: resolver
    })).createFromAgentCard(card);
  }
  journal.emit('discovered-card', { package_root: packageRoot, sdk_version: JSON.parse(readFileSync(path.join(sdkRoot, '../package.json'))).version,
    profile: config.profile, card });
  if (config.profile === 'amir-stream') assert(card.capabilities?.streaming === true, 'Original card does not advertise required streaming profile');
  let rawSequence = 0;
  return {
    userRole: sdk.Role.ROLE_USER,
    stateName: state => sdk.taskStateToJSON(state).replace(/^TASK_STATE_/, '').toLowerCase(),
    messageId: () => amir ? randomUUID() : `msg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`,
    async pause(ms) { await sleep(Math.min(ms, left())); },
    async get(id) { return bounded(() => client.getTask({ tenant: '', id, historyLength: 100 })); },
    async send(message) {
      return bounded(async () => {
        const params = nativeSendRequest(message);
        if (config.profile !== 'amir-stream') return client.sendMessage(params);
        let task, eventBytes = 0;
        for await (const event of client.sendMessageStream(params)) {
          eventBytes += Buffer.byteLength(JSON.stringify(event));
          assert(eventBytes <= config.limits.max_response_bytes, 'Native decoded stream byte limit');
          journal.emit('sdk-stream-event', { value: event });
          if (event.payload?.$case === 'task') task = event.payload.value;
          else if (event.payload?.$case === 'statusUpdate') {
            const update = event.payload.value;
            if (task) assert(update.taskId === task.id && update.contextId === task.contextId, 'Native stream task association changed');
            task = { ...(task ?? {}), id: update.taskId, contextId: update.contextId, status: update.status };
          }
        }
        assert(task, 'Native stream closed without a public task'); return task;
      });
    },
    async rawSend({ params, version }) {
      return bounded(async () => {
        const iface = card.supportedInterfaces.find(item => item.protocolBinding === 'JSONRPC');
        assert(iface, 'Original card advertises no JSONRPC binding');
        const payload = { jsonrpc: '2.0', id: 'native-raw-' + (++rawSequence), method: 'SendMessage', params };
        const bytes = Buffer.from(JSON.stringify(payload));
        const headers = { 'content-type': 'application/json', ...(version ? { 'A2A-Version': version } : {}) };
        journal.emit('raw-http-request', { url: iface.url, method: 'POST', headers, raw: entity(bytes), parsed: payload });
        const chunks = []; let response, complete = false, total = 0;
        try {
          response = await fetchImpl(iface.url, { method: 'POST', headers, body: bytes });
          const reader = response.body?.getReader();
          if (reader) for (;;) { const item = await reader.read(); if (item.done) break;
            const chunk = Buffer.from(item.value); chunks.push(chunk); total += chunk.length;
            if (total > config.limits.max_response_bytes) { await reader.cancel(); throw new Error('Raw native response byte limit'); } }
          complete = true;
          return { status: response.status, body: JSON.parse(Buffer.concat(chunks).toString('utf8')) };
        } finally { journal.emit('raw-http-response', { status: response?.status ?? null,
          headers: response ? Object.fromEntries(response.headers) : {}, complete, raw: entity(Buffer.concat(chunks)) }); }
      });
    }
  };
}

export async function main(argv = process.argv.slice(2)) {
  assert(argv.length === 2 && argv[0] === '--config', 'Use --config <JSON path>');
  const bytes = readFileSync(path.resolve(argv[1]));
  const config = validateNativeConfig(JSON.parse(bytes));
  mkdirSync(config.output_dir, { recursive: false });
  writeFileSync(path.join(config.output_dir, 'config.json'), bytes, { flag: 'wx' });
  const journal = createJournal(config.output_dir); let result;
  try {
    const adapter = await buildAdapter(config, journal);
    result = await runNativeEpisode(config, adapter, journal.emit);
  } catch (error) { result = { profile: config.profile, representation: config.representation,
    status: 'client_failed', error: errorText(error), strict_success: null }; }
  finally { journal.close(); }
  result.schema_version = 'agentops-native-profile-client-result/1';
  result.finished_at_utc = new Date().toISOString();
  result.source_scope = 'Direct SDK/native observations; no evaluator or prior evidence files read';
  writeFileSync(path.join(config.output_dir, 'result.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  process.stdout.write(JSON.stringify({ profile: config.profile, representation: config.representation, status: result.status }) + '\n');
  process.exitCode = result.status === 'client_failed' ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { process.stderr.write(errorText(error) + '\n'); process.exitCode = 1; });
}
