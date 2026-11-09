// Bounded public-MCP caller. The coordinator owns application execution/effect grading.
// Importing this module does not spawn a bridge, import a third-party SDK or send requests.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, mkdirSync, openSync, readFileSync, writeFileSync, writeSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

export const SCHEMA = 'agentops-bridge-client-config/1';
export const INITIAL_TEXT = 'Restart inventory.';
export const LITERAL_ANSWER = 'Yes, confirm the inventory restart. Rationale: Inventory is down and INC-002 matches the service-down runbook.';
const META_KEY = 'io.github.amirk-s/a2a';
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.length > 0;
const errorText = error => String(error?.stack ?? error);
const entity = raw => ({ base64: raw.toString('base64'), bytes: raw.length,
  sha256: createHash('sha256').update(raw).digest('hex') });
const stateOf = value => typeof value === 'string' ? value.replace(/^TASK_STATE_/, '').replaceAll('-', '_').toLowerCase() : null;

export function validateConfig(config) {
  assert(isObject(config) && config.schema_version === SCHEMA);
  assert(/^B[1-7]$/.test(config.arm), 'Unknown arm');
  assert(path.isAbsolute(config.output_dir), 'output_dir must be absolute');
  const origin = new URL(config.agent_base_url);
  assert(origin.protocol === 'http:' && origin.hostname === '127.0.0.1' && origin.port
    && origin.pathname === '/' && !origin.username && !origin.password && !origin.search && !origin.hash);
  assert(nonempty(config.rationale) && nonempty(config.agent_alias));
  if (['B1', 'B2', 'B3'].includes(config.arm)) {
    const endpoint = new URL(config.amir_endpoint);
    assert(endpoint.protocol === 'http:' && endpoint.hostname === '127.0.0.1'
      && endpoint.pathname === '/mcp' && !endpoint.username && !endpoint.password && !endpoint.search && !endpoint.hash);
  }
  const bridge = config.bridge;
  assert(isObject(bridge) && path.isAbsolute(bridge.command) && path.isAbsolute(bridge.cwd));
  assert(Array.isArray(bridge.args) && bridge.args.every(value => typeof value === 'string'));
  assert(isObject(bridge.env) && Object.values(bridge.env).every(value => typeof value === 'string'));
  const limits = config.limits;
  for (const [key, upper] of Object.entries({ request_timeout_ms: 45000, poll_interval_ms: 2000,
    poll_attempts: 60, total_timeout_ms: 300000, max_response_bytes: 33554432 })) {
    assert(Number.isInteger(limits?.[key]) && limits[key] > 0 && limits[key] <= upper, `Invalid limit ${key}`);
  }
  return config;
}

export function publicSource(seq, sourcePath, decodedPath) {
  return { seq, path: sourcePath, ...(decodedPath ? { decode: 'json-text', decoded_path: decodedPath } : {}) };
}

export function decodeTool(reply) {
  assert(isObject(reply.body), 'Missing tool-result object');
  const body = reply.body;
  const error = body.isError === true || body.isToolError === true;
  if (isObject(body.structuredContent)) return { value: body.structuredContent, error,
    source: child => publicSource(reply.seq, ['result', 'structuredContent', ...child]) };
  assert(Array.isArray(body.content) && body.content[0]?.type === 'text' && nonempty(body.content[0].text), 'Missing tool JSON text');
  const value = JSON.parse(body.content[0].text);
  assert(isObject(value), 'Expected decoded tool object');
  return { value, error, source: child => publicSource(reply.seq, ['result', 'content', 0, 'text'], child) };
}

export function findAmirConfirmation(reply) {
  const found = [];
  for (const [index, block] of (reply.body?.content ?? []).entries()) {
    const meta = block?._meta?.[META_KEY];
    if (block.type !== 'text' || meta?.partKind !== 'data' || meta?.metadata?.adk_type !== 'function_call') continue;
    let call;
    try { call = JSON.parse(block.text); } catch { continue; }
    if (call?.name === 'adk_request_confirmation' && nonempty(call.id)) {
      found.push({ id: call.id, name: call.name, source: publicSource(reply.seq, ['result', 'content', index, 'text'], ['id']),
        name_source: publicSource(reply.seq, ['result', 'content', index, 'text'], ['name']) });
    }
  }
  const ids = new Set(found.map(item => item.id));
  assert(ids.size <= 1, 'Ambiguous public confirmation IDs');
  return found[0] ?? null;
}

export function findRawConfirmation(decoded, original) {
  if (decoded.error || decoded.value.error) return null;
  const task = decoded.value.result;
  assert(isObject(task) && task.id === original.task_id && task.contextId === original.context_id,
    'Raw task association differs from public typed task');
  if (stateOf(task.status?.state) !== 'input_required') return null;
  const parts = task.status?.message?.parts ?? [];
  const found = [];
  for (const [index, part] of parts.entries()) {
    if (part.metadata?.adk_type === 'function_call' && part.data?.name === 'adk_request_confirmation' && nonempty(part.data.id)) {
      found.push({ id: part.data.id, name: part.data.name,
        source: decoded.source(['result', 'status', 'message', 'parts', index, 'data', 'id']),
        name_source: decoded.source(['result', 'status', 'message', 'parts', index, 'data', 'name']) });
    }
  }
  assert(new Set(found.map(item => item.id)).size <= 1, 'Ambiguous public raw confirmation IDs');
  return found[0] ?? null;
}

export function formAnswer(body, answer) {
  const keys = Object.keys(body?.inputRequests ?? {});
  assert.equal(keys.length, 1, 'Expected one public form');
  const request = body.inputRequests[keys[0]];
  const fields = Object.keys(request?.params?.requestedSchema?.properties ?? {});
  assert(request?.method === 'elicitation/create' && request.params.mode === 'form'
    && fields.length === 1 && request.params.requestedSchema.properties[fields[0]].type === 'string', 'Unexpected public form schema');
  return { responses: { [keys[0]]: { action: 'accept', content: { [fields[0]]: answer } } },
    request_key: keys[0], field: fields[0] };
}

export function confirmationPayload(call, rationale) {
  assert(nonempty(call?.id) && call.name === 'adk_request_confirmation');
  return { id: call.id, name: call.name, response: { confirmed: true, payload: { rationale } } };
}

function createJournal(directory) {
  const fd = openSync(path.join(directory, 'mcp.jsonl'), 'wx');
  let seq = 0;
  return { emit(kind, value = {}) {
    const event = { schema_version: 'agentops-bridge-client-event/1', seq: ++seq,
      at_utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString(), kind, ...value };
    writeSync(fd, JSON.stringify(event) + '\n');
    return event;
  }, close() { closeSync(fd); } };
}

export async function runPublicEpisode(config, transport, emit = () => ({})) {
  const result = { arm: config.arm, bindings: [], initial_text: INITIAL_TEXT,
    answer_sent: false, answer_attempts: 0, public_confirmation_observed: false,
    strict_success: null, strict_success_requires_external_effect_check: true, errors: [] };
  const bind = (name, value, source) => {
    assert(nonempty(value), `Missing public ${name}`);
    const previous = result.bindings.find(item => item.name === name);
    assert(!previous || previous.value === value, `Changed public ${name}`);
    const record = { name, value, source };
    result.bindings.push(record); emit('public-binding', record); return value;
  };
  const rpc = (phase, method, params = {}, notify = false) => transport.rpc(phase, method, params, notify);
  const tool = (phase, name, args) => rpc(phase, 'tools/call', { name, arguments: args });
  const guarded = async (phase, action) => { try { return await action(); }
    catch (error) { result.errors.push({ phase, error: errorText(error) }); return null; } };
  const listed = await rpc('discover_full_tools', 'tools/list');
  assert(Array.isArray(listed.body?.tools), 'Missing tools/list result');
  result.tools = listed.body.tools;
  for (const name of ['a2a_send_message', 'a2a_get_task']) assert(result.tools.some(item => item.name === name), `Missing tool ${name}`);
  const amir = ['B1', 'B2', 'B3'].includes(config.arm);
  const originalArgs = amir ? { agent: config.agent_alias, text: INITIAL_TEXT }
    : { url: config.agent_base_url, text: INITIAL_TEXT };
  if (!amir) await tool('discover_agent', 'a2a_discover_agent', { url: config.agent_base_url });
  const started = await tool('initial_typed_send', 'a2a_send_message', originalArgs);
  result.initial_reply_seq = started.seq;
  let taskHandle, contextHandle, taskId, contextId, pending, call = null;

  if (config.arm === 'B3') {
    if (started.body?.resultType !== 'input_required' || !nonempty(started.body?.requestState)) {
      result.status = 'no_public_mrtr_continuation'; return result;
    }
    bind('request_state', started.body.requestState, publicSource(started.seq, ['result', 'requestState']));
    result.answer_representation = 'literal_fallback';
    result.public_binding_unavailable = 'MRTR exposes no typed confirmation ID; sealed requestState is echoed unchanged';
    const form = formAnswer(started.body, LITERAL_ANSWER);
    result.form = { request_key: form.request_key, field: form.field, source_seq: started.seq };
    result.answer_attempts = 1; result.answer_sent = true; result.answer_text = LITERAL_ANSWER;
    const answer = await guarded('mrtr_answer', () => rpc('mrtr_answer', 'tools/call', {
      name: 'a2a_send_message', arguments: originalArgs, requestState: started.body.requestState,
      inputResponses: form.responses }));
    result.answer_reply_seq = answer?.seq ?? null;
    const envelope = answer?.body?.structuredContent;
    if (nonempty(envelope?.taskHandle)) taskHandle = bind('task_handle', envelope.taskHandle,
      publicSource(answer.seq, ['result', 'structuredContent', 'taskHandle']));
    if (nonempty(envelope?.contextHandle)) contextHandle = bind('context_handle', envelope.contextHandle,
      publicSource(answer.seq, ['result', 'structuredContent', 'contextHandle']));
  } else {
    if (amir) {
      const envelope = started.body?.structuredContent;
      const handle = config.arm === 'B2' ? started.body?.taskId : envelope?.taskHandle;
      if (!nonempty(handle)) { result.status = 'public_task_binding_not_observed'; return result; }
      taskHandle = bind('task_handle', handle, publicSource(started.seq,
        config.arm === 'B2' ? ['result', 'taskId'] : ['result', 'structuredContent', 'taskHandle']));
    } else {
      const decoded = decodeTool(started), task = decoded.value.task;
      if (decoded.error || !nonempty(task?.id) || !nonempty(task?.context_id)) {
        result.status = 'public_task_binding_not_observed'; return result;
      }
      taskId = bind('task_id', task.id, decoded.source(['task', 'id']));
      contextId = bind('context_id', task.context_id, decoded.source(['task', 'context_id']));
    }
    for (let index = 0; index < config.limits.poll_attempts; index++) {
      const read = await tool('pending_origin_get', 'a2a_get_task', amir
        ? { agent: config.agent_alias, taskHandle, historyLength: 100 }
        : { task_id: taskId, history_length: 100, refresh: true });
      const decoded = amir ? { value: read.body?.structuredContent, error: read.body?.isError === true || read.body?.isToolError === true }
        : decodeTool(read);
      const value = decoded.value;
      if (decoded.error || !isObject(value)) { result.status = 'pending_read_error'; return result; }
      assert(amir ? value.taskHandle === taskHandle : value.id === taskId && value.context_id === contextId,
        'Pending query changed original public association');
      const state = stateOf(amir ? value.a2aState : value.state);
      if (state === 'input_required') { pending = read; break; }
      if (!['submitted', 'working'].includes(state)) { result.status = 'initial_state_not_pending'; result.initial_state = state; return result; }
      if (index + 1 < config.limits.poll_attempts) await transport.pause(config.limits.poll_interval_ms);
    }
    if (!pending) { result.status = 'pending_observation_bound_reached'; return result; }
    result.pending_reply_seq = pending.seq;
    if (amir) {
      contextHandle = bind('context_handle', pending.body.structuredContent.contextHandle,
        publicSource(pending.seq, ['result', 'structuredContent', 'contextHandle']));
      call = findAmirConfirmation(pending);
    } else if (['B5', 'B6', 'B7'].includes(config.arm)) {
      assert(result.tools.some(item => item.name === 'a2a_request'
        && item.inputSchema?.properties?.method?.enum?.includes('GetTask')
        && item.inputSchema?.properties?.method?.enum?.includes('SendMessage')), 'Missing permitted raw methods');
      const raw = await guarded('public_raw_get', () => tool('public_raw_get', 'a2a_request', {
        url: config.agent_base_url, method: 'GetTask', params: { id: taskId, historyLength: 100 } }));
      if (raw) { result.public_raw_get_seq = raw.seq; call = findRawConfirmation(decodeTool(raw), { task_id: taskId, context_id: contextId }); }
    }
    if (call) {
      bind('confirmation_call_id', call.id, call.source); bind('confirmation_call_name', call.name, call.name_source);
      result.public_confirmation_observed = true;
    }
    if (['B5', 'B6', 'B7'].includes(config.arm) && !call) {
      result.status = 'public_binding_not_observed';
      result.public_binding_unavailable = 'No usable confirmation ID from permitted public raw task query';
    } else {
      const answerObject = call ? confirmationPayload(call, config.rationale) : null;
      const answerText = answerObject ? JSON.stringify(answerObject) : LITERAL_ANSWER;
      result.answer_representation = answerObject ? (amir || config.arm === 'B4' ? 'canonical_json_as_text' : 'canonical_data_part') : 'literal_fallback';
      result.answer_text = (amir || config.arm === 'B4') ? answerText : null;
      if (!call) result.public_binding_unavailable = 'Typed public output did not expose a usable ADK confirmation call ID';
      let answerAction;
      if (config.arm === 'B2') {
        const formReply = await rpc('pending_tasks_form', 'tasks/get', { taskId: taskHandle });
        assert(formReply.body?.taskId === taskHandle && formReply.body?.status === 'input_required', 'Tasks form is not bound to pending original');
        const form = formAnswer(formReply.body, answerText);
        result.form = { request_key: form.request_key, field: form.field, source_seq: formReply.seq };
        answerAction = () => rpc('tasks_answer', 'tasks/update', { taskId: taskHandle, inputResponses: form.responses });
      } else if (config.arm === 'B1') answerAction = () => tool('typed_answer', 'a2a_send_message', {
        agent: config.agent_alias, text: answerText, taskHandle, contextHandle });
      else if (config.arm === 'B4') answerAction = () => tool('typed_answer', 'a2a_send_message', {
        url: config.agent_base_url, text: answerText, task_id: taskId, context_id: contextId });
      else answerAction = () => tool('raw_answer', 'a2a_request', { url: config.agent_base_url, method: 'SendMessage', params: {
        message: { messageId: 'agentops-public-confirmation', role: 'ROLE_USER', taskId, contextId,
          parts: [{ data: answerObject, metadata: { adk_type: 'function_response' } }] } } });
      result.answer_attempts = 1; result.answer_sent = true;
      const answer = await guarded('answer', answerAction);
      result.answer_reply_seq = answer?.seq ?? null;
      if (config.arm === 'B2') {
        for (let index = 0; index < config.limits.poll_attempts; index++) {
          const update = await guarded('post_answer_tasks_get', () => rpc('post_answer_tasks_get', 'tasks/get', { taskId: taskHandle }));
          if (!update) break;
          assert(update.body?.taskId === taskHandle, 'Tasks completion query changed public handle');
          result.final_tasks_reply_seq = update.seq;
          result.final_tasks_status = update.body.status;
          if (!['submitted', 'working'].includes(update.body.status)) break;
          if (index + 1 < config.limits.poll_attempts) await transport.pause(config.limits.poll_interval_ms);
        }
      }
    }
  }

  if (taskHandle || taskId) {
    for (let index = 0; index < config.limits.poll_attempts; index++) {
      const final = await guarded('final_origin_get', () => tool('final_origin_get', 'a2a_get_task', amir
        ? { agent: config.agent_alias, taskHandle, historyLength: 100 }
        : { task_id: taskId, history_length: 100, refresh: true }));
      if (!final) break;
      const decoded = amir ? { value: final.body?.structuredContent, error: final.body?.isError === true || final.body?.isToolError === true } : decodeTool(final);
      result.final_reply_seq = final.seq;
      result.final_tool_error = decoded.error;
      const value = decoded.value;
      result.final_state = stateOf(amir ? value?.a2aState : value?.state);
      result.final_public_association_preserved = amir ? value?.taskHandle === taskHandle && value?.contextHandle === contextHandle
        : value?.id === taskId && value?.context_id === contextId;
      if (!['submitted', 'working'].includes(result.final_state) || decoded.error) break;
      if (index + 1 < config.limits.poll_attempts) await transport.pause(config.limits.poll_interval_ms);
    }
  } else result.final_read_unavailable = 'No public task handle after opaque MRTR response; evaluator-only origin check is separate';
  result.status ??= result.errors.length ? 'recorded_with_client_errors' : 'recorded';
  return result;
}

function decodeHttpMessages(bytes, contentType) {
  const raw = bytes.toString('utf8');
  if (!contentType.includes('text/event-stream')) return [{ parsed: JSON.parse(raw), bytes, framing: 'http-body' }];
  assert(/\r?\n\r?\n$/.test(raw), 'SSE response lacks closing frame');
  const messages = [];
  for (const frame of raw.split(/\r?\n\r?\n/)) {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n');
    if (data) messages.push({ parsed: JSON.parse(data), bytes: Buffer.from(data), framing: 'sse-data-derived' });
  }
  return messages;
}

async function execute(config, journal) {
  const amir = ['B1', 'B2', 'B3'].includes(config.arm);
  const deadline = Date.now() + config.limits.total_timeout_ms;
  const remaining = () => { const value = deadline - Date.now(); assert(value > 0, 'Client total deadline reached'); return value; };
  const child = spawn(config.bridge.command, config.bridge.args, { cwd: config.bridge.cwd, env: config.bridge.env,
    shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  const lifecycle = { pid: child.pid ?? null, command: config.bridge.command, args: config.bridge.args,
    cwd: config.bridge.cwd, started_at_utc: new Date().toISOString(), clean_exit: false };
  journal.emit('child-start', lifecycle);
  let childError, buffer = Buffer.alloc(0), stdoutText = '', outputBytes = 0, exitRecord;
  const pending = new Map();
  const operations = new Map();
  let operation = 0;
  const exited = new Promise(resolve => child.once('close', (code, signal) => {
    exitRecord = { code, signal, at_utc: new Date().toISOString() };
    journal.emit('child-exit', exitRecord);
    for (const item of pending.values()) item.reject(new Error(`Bridge exited: ${code}/${signal}`));
    pending.clear(); resolve(exitRecord);
  }));
  child.on('error', error => { childError = error; journal.emit('child-error', { error: errorText(error) });
    for (const item of pending.values()) item.reject(error); pending.clear(); });
  child.stderr.on('data', bytes => journal.emit('stdio-chunk', { direction: 'bridge_stderr', raw: entity(bytes) }));
  child.stdout.on('data', bytes => {
    journal.emit('stdio-chunk', { direction: 'bridge_to_client', raw: entity(bytes) });
    outputBytes += bytes.length;
    if (outputBytes > config.limits.max_response_bytes) { childError = new Error('Bridge stdout byte limit');
      for (const item of pending.values()) item.reject(childError); pending.clear(); return; }
    if (amir) { stdoutText += bytes.toString('utf8'); return; }
    buffer = Buffer.concat([buffer, bytes]);
    for (;;) {
      const end = buffer.indexOf(10); if (end < 0) break;
      const line = buffer.subarray(0, end + 1); buffer = buffer.subarray(end + 1);
      try {
        const parsed = JSON.parse(line.toString('utf8'));
        const associated = operations.get(parsed.id);
        const event = journal.emit('mcp-message', { direction: 'bridge_to_client', framing: 'stdio-line',
          operation_id: associated?.id ?? null, phase: associated?.phase ?? null, raw: entity(line), parsed });
        if (pending.has(parsed.id)) { const receiver = pending.get(parsed.id); pending.delete(parsed.id);
          receiver.resolve({ body: parsed.result, json: parsed, seq: event.seq }); }
      } catch (error) { childError = error; journal.emit('mcp-parse-error', { error: errorText(error), raw: entity(line) });
        for (const item of pending.values()) item.reject(error); pending.clear(); }
    }
  });
  const capabilities = config.arm === 'B2' ? { extensions: { 'io.modelcontextprotocol/tasks': {} } }
    : config.arm === 'B3' ? { elicitation: {} } : {};
  const transport = {
    async pause(ms) { await sleep(Math.min(ms, remaining())); },
    async rpc(phase, method, params = {}, notify = false) {
      if (childError) throw childError;
      assert(!exitRecord, 'Bridge is no longer running');
      const id = ++operation;
      operations.set(id, { id, phase });
      const json = { jsonrpc: '2.0', ...(notify ? {} : { id }), method,
        ...(notify && params === undefined ? {} : { params: amir ? { _meta: {
          'io.modelcontextprotocol/protocolVersion': '2026-07-28',
          'io.modelcontextprotocol/clientCapabilities': capabilities,
          'io.modelcontextprotocol/clientInfo': { name: 'AgentOps-public-control', version: '1.0.0' } }, ...params } : params }) };
      const timeout = Math.min(config.limits.request_timeout_ms, remaining());
      journal.emit('operation-start', { operation_id: id, phase, method, notification: notify });
      let reply;
      try {
        if (amir) {
          const bytes = Buffer.from(JSON.stringify(json));
          const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream',
            'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method };
          if (method === 'tools/call') headers['Mcp-Name'] = params.name;
          if (method.startsWith('tasks/')) headers['Mcp-Name'] = params.taskId;
          const request = journal.emit('http-request', { operation_id: id, phase, url: config.amir_endpoint,
            method: 'POST', headers, raw: entity(bytes) });
          journal.emit('mcp-message', { direction: 'client_to_bridge', framing: 'http-body', operation_id: id,
            phase, source_http_seq: request.seq, raw: entity(bytes), parsed: json });
          const chunks = []; let total = 0, response, complete = false, responseEvent;
          try {
            response = await fetch(config.amir_endpoint, { method: 'POST', headers, body: bytes,
              redirect: 'error', signal: AbortSignal.timeout(timeout) });
            const reader = response.body?.getReader();
            if (reader) for (;;) { const part = await reader.read(); if (part.done) break;
              const chunk = Buffer.from(part.value); chunks.push(chunk); total += chunk.length;
              if (total > config.limits.max_response_bytes) { await reader.cancel(); throw new Error('HTTP response byte limit'); } }
            complete = true;
          } finally {
            responseEvent = journal.emit('http-response', { operation_id: id, phase, status: response?.status ?? null,
              headers: response ? Object.fromEntries(response.headers) : {}, complete, raw: entity(Buffer.concat(chunks)) });
          }
          for (const message of decodeHttpMessages(Buffer.concat(chunks), response.headers.get('content-type') ?? '')) {
            const event = journal.emit('mcp-message', { direction: 'bridge_to_client', operation_id: id, phase,
              framing: message.framing, source_http_seq: responseEvent.seq, raw: entity(message.bytes), parsed: message.parsed });
            if (message.parsed.id === id) { assert(!reply, 'Duplicate HTTP RPC reply'); reply = { body: message.parsed.result, json: message.parsed, seq: event.seq }; }
          }
          assert(reply, 'No matching HTTP MCP reply');
        } else {
          const bytes = Buffer.from(JSON.stringify(json) + '\n');
          const responsePromise = notify ? Promise.resolve({ body: null, json: null, seq: null })
            : new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
          // A fast process error may arrive while the write callback is pending.
          // Preserve that rejection for the awaited promise without an unhandled event.
          responsePromise.catch(() => {});
          let timer;
          const timed = new Promise((resolve, reject) => { timer = setTimeout(() => {
            pending.delete(id); reject(new Error(`MCP request timeout: ${phase}`)); }, timeout); });
          const event = journal.emit('mcp-message', { direction: 'client_to_bridge', framing: 'stdio-line',
            operation_id: id, phase, raw: entity(bytes), parsed: json });
          try {
            await Promise.race([new Promise((resolve, reject) => child.stdin.write(bytes, error => error ? reject(error) : resolve())), timed]);
            journal.emit('stdio-written', { operation_id: id, source_seq: event.seq, bytes: bytes.length });
            reply = await Promise.race([responsePromise, timed]);
          } finally { clearTimeout(timer); pending.delete(id); }
        }
        if (!notify) assert(reply.json?.jsonrpc === '2.0' && reply.json.id === id && !reply.json.error,
          `MCP JSON-RPC error or wrong response: ${JSON.stringify(reply.json)}`);
        journal.emit('operation-complete', { operation_id: id, phase, reply_seq: reply.seq });
        return reply;
      } catch (error) { journal.emit('operation-error', { operation_id: id, phase, error: errorText(error) }); throw error; }
    }
  };
  let result;
  try {
    if (amir) {
      const startupDeadline = Date.now() + Math.min(15000, remaining());
      while (!stdoutText.includes('a2a-to-mcp listening on ' + config.amir_endpoint)) {
        if (childError) throw childError; assert(!exitRecord, 'Bridge exited before ready');
        assert(Date.now() < startupDeadline, 'Amir startup timeout'); await sleep(25);
      }
      await transport.rpc('discover_profile', 'server/discover');
    } else {
      const initialized = await transport.rpc('initialize', 'initialize', { protocolVersion: '2025-11-25',
        capabilities: {}, clientInfo: { name: 'AgentOps-public-control', version: '1.0.0' } });
      assert(initialized.body?.protocolVersion === '2025-11-25', 'Unexpected MCP negotiated revision');
      await transport.rpc('initialized', 'notifications/initialized', undefined, true);
    }
    result = await runPublicEpisode(config, transport, journal.emit);
  } catch (error) { result = { arm: config.arm, status: 'client_failed', error: errorText(error),
    strict_success: null, strict_success_requires_external_effect_check: true }; }
  finally {
    lifecycle.cleanup_started_at_utc = new Date().toISOString();
    if (!exitRecord) {
      lifecycle.sigterm_sent = child.kill('SIGTERM');
      let timer;
      try { await Promise.race([exited, new Promise(resolve => { timer = setTimeout(resolve, 12000); })]); }
      finally { clearTimeout(timer); }
    }
    if (!exitRecord) {
      lifecycle.forced_kill = true; lifecycle.sigkill_sent = child.kill('SIGKILL');
      let timer;
      try { await Promise.race([exited, new Promise(resolve => { timer = setTimeout(resolve, 5000); })]); }
      finally { clearTimeout(timer); }
    }
    lifecycle.exit = exitRecord ?? null;
    if (!amir && buffer.length) journal.emit('stdio-trailing-bytes', { direction: 'bridge_to_client', raw: entity(buffer) });
    lifecycle.clean_exit = !lifecycle.forced_kill && exitRecord?.code === 0 && !exitRecord?.signal;
    lifecycle.finished_at_utc = new Date().toISOString();
    journal.emit('child-cleanup', lifecycle);
  }
  return { ...result, child: lifecycle, configured_limits: config.limits,
    source_scope: 'Public MCP observations only; no native evidence files read' };
}

export async function main(argv = process.argv.slice(2)) {
  assert(argv.length === 2 && argv[0] === '--config', 'Use --config <JSON path>');
  const bytes = readFileSync(path.resolve(argv[1]));
  const config = validateConfig(JSON.parse(bytes));
  mkdirSync(config.output_dir, { recursive: false });
  writeFileSync(path.join(config.output_dir, 'config.json'), bytes, { flag: 'wx' });
  const journal = createJournal(config.output_dir);
  let result;
  try { result = await execute(config, journal); }
  catch (error) { result = { arm: config.arm, status: 'client_failed', error: errorText(error), strict_success: null }; }
  finally { journal.close(); }
  result.schema_version = 'agentops-bridge-client-result/1';
  result.finished_at_utc = new Date().toISOString();
  writeFileSync(path.join(config.output_dir, 'result.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  process.stdout.write(JSON.stringify({ arm: config.arm, status: result.status, clean_exit: result.child?.clean_exit ?? false }) + '\n');
  process.exitCode = result.status === 'client_failed' || !result.child?.clean_exit ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { process.stderr.write(errorText(error) + '\n'); process.exitCode = 1; });
}
