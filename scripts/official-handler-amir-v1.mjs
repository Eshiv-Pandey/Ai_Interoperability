// Exact copy of the earlier authored Amir caller routine; historical file unchanged.
import assert from 'node:assert/strict';
import { deadline, stamp, hash, elapsed, addReceipt, pause, initialText, answerText, errorText } from './log-reference-http.mjs';
function rpcBody(raw, contentType) {
  if (contentType.includes('text/event-stream')) {
    const events = raw.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).filter(Boolean);
    return JSON.parse(events.at(-1) ?? 'null');
  }
  return JSON.parse(raw);
}
export async function runAmir(capture, variant, bridge) {
  const report = capture.report;
  const modernTasks = variant === 'R2';
  const diagnostics = capture.diagnostics.children.bridge;
  const url = await deadline(new Promise((resolve, reject) => {
    bridge.once('error', reject); bridge.once('exit', code => reject(new Error(`Amir bridge exited ${code} before ready`)));
    const check = () => { const match = diagnostics.stdout.match(/a2a-to-mcp listening on (http:\/\/[^\s]+)/); if (match) resolve(match[1]); };
    bridge.stdout.on('data', check); check();
  }), 10000, 'Amir bridge startup');
  assert.equal(new URL(url).hostname, '127.0.0.1');
  report.endpoint = url;
  let sequence = 0;
  async function rpc(phase, method, params = {}, requestLimit = 10000) {
    const id = ++sequence;
    const capabilities = modernTasks ? { extensions: { 'io.modelcontextprotocol/tasks': {} } } : {};
    const json = { jsonrpc: '2.0', id, method, params: { _meta: { 'io.modelcontextprotocol/protocolVersion': '2026-07-28', 'io.modelcontextprotocol/clientCapabilities': capabilities, 'io.modelcontextprotocol/clientInfo': { name: 'Carol-reference-development-observer', version: '1.0.0' } }, ...params } };
    const raw = JSON.stringify(json); const bytes = Buffer.from(raw); const start = stamp();
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method };
    if (method === 'tools/call') headers['Mcp-Name'] = params.name;
    if (method.startsWith('tasks/')) headers['Mcp-Name'] = params.taskId;
    const exchange = { exchange_id: `mcp-${id}`, phase, request: { raw, base64: bytes.toString('base64'), bytes: bytes.length, json, url, headers, started_at_utc: start.utc, monotonic_ns: start.monotonic_ns, sha256: hash(bytes) }, response: null };
    report.exchanges.push(exchange);
    try {
      const response = await fetch(url, { method: 'POST', headers, body: raw, signal: AbortSignal.timeout(requestLimit) });
      const body = Buffer.from(await response.arrayBuffer()); const responseRaw = body.toString('utf8'); const end = stamp();
      exchange.response = { raw: responseRaw, base64: body.toString('base64'), bytes: body.length, json: null, status: response.status, headers: Object.fromEntries(response.headers), observed_at_utc: end.utc, monotonic_ns: end.monotonic_ns, sha256: hash(body) };
      exchange.response.json = rpcBody(responseRaw, response.headers.get('content-type') ?? '');
      exchange.elapsed_ms = elapsed(start, end);
      assert.equal(exchange.response.json.id, id); assert(!exchange.response.json.error, responseRaw); assert(exchange.response.json.result, responseRaw);
      return { body: exchange.response.json.result, exchange };
    } catch (error) { exchange.error = errorText(error); throw error; }
  }
  const tool = (phase, name, args, requestLimit) => rpc(phase, 'tools/call', { name, arguments: args }, requestLimit);
  const receiveEnvelope = result => result.body?.structuredContent;
  const isToolError = result => result.body?.isError === true || result.body?.isToolError === true;
  const record = (key, result) => { report[key] = { exchange_id: result.exchange.exchange_id, body: result.body }; };
  const receipt = (result, role) => {
    const envelope = receiveEnvelope(result);
    const fields = ['taskHandle', 'contextHandle', 'status', 'a2aState', 'artifacts', 'history'].filter(field => envelope?.[field] !== undefined).map(field => `result.structuredContent.${field}`);
    if (result.body.content !== undefined) fields.push('result.content');
    return addReceipt(capture, result.exchange, role, envelope?.taskHandle, envelope?.contextHandle, fields);
  };
  const discovered = await rpc('discover_profile', 'server/discover');
  const listed = await rpc('discover_full_tools', 'tools/list');
  report.discovery = { profile_exchange_id: discovered.exchange.exchange_id, profile: discovered.body, tools_exchange_id: listed.exchange.exchange_id, tools: listed.body.tools };
  assert(Array.isArray(listed.body.tools));
  assert(listed.body.tools.some(item => item.name === 'a2a_send_message'));
  assert(listed.body.tools.some(item => item.name === 'a2a_get_task'));
  report.contract = { variant, initial_text: initialText, answer_text: answerText, source_expected_original_state: 'input_required', goal_id: 'logical-completion-and-original-association', goal: 'Original task and context completed after fixed answer, measured by final authoritative tool envelope', terminal_artifact_required: false, history_length: 10, native_parameters_from_private_sidecar: false, selected_answer_action: modernTasks ? 'tasks/update accept actual string form' : 'a2a_send_message', answer_attempts: 0, initial_observation_bound_ms: 5000, initial_poll_interval_ms: 50 };
  const created = await tool('initial_typed_send', 'a2a_send_message', { agent: 'carol', text: initialText });
  record('initial', created);
  const originalTaskHandle = modernTasks ? created.body.taskId : receiveEnvelope(created)?.taskHandle;
  if (typeof originalTaskHandle !== 'string' || !originalTaskHandle) {
    report.observation = { initial_required_observed: false, answer_sent: false, goal_achieved: false, initial_application_error: isToolError(created), missing_public_task_handle: true };
    return;
  }
  report.contract.original_task_handle = originalTaskHandle;
  report.contract.initial_context_handle = receiveEnvelope(created)?.contextHandle ?? null;
  report.contract.initial_binding = { exchange_id: created.exchange.exchange_id, field: modernTasks ? 'result.taskId' : 'result.structuredContent.taskHandle', public: true };
  if (!modernTasks) receipt(created, 'typed_initial_public_task_receipt');
  const until = Date.now() + 5000;
  report.initial_reads = [];
  let pending;
  while (Date.now() < until) {
    const read = await tool('initial_authoritative_pending_get', 'a2a_get_task', { agent: 'carol', taskHandle: originalTaskHandle, historyLength: 10 }, Math.max(1, until - Date.now()));
    report.initial_reads.push({ exchange_id: read.exchange.exchange_id, body: read.body });
    receipt(read, 'explicit_peer_task_query_pending');
    const envelope = receiveEnvelope(read);
    if (isToolError(read)) { report.observation = { initial_required_observed: false, answer_sent: false, goal_achieved: false, initial_application_error: true }; return; }
    if (envelope?.taskHandle !== originalTaskHandle) { report.observation = { initial_required_observed: false, answer_sent: false, goal_achieved: false, initial_task_binding_mismatch: true }; return; }
    if (envelope.status === 'input_required' && envelope.a2aState === 'TASK_STATE_INPUT_REQUIRED') { pending = read; break; }
    const remaining = until - Date.now(); if (remaining > 0) await pause(Math.min(50, remaining));
  }
  if (!pending) { report.observation = { initial_required_observed: false, answer_sent: false, goal_achieved: false, initial_observation_timeout: true, observed_states: report.initial_reads.map(read => read.body.structuredContent?.a2aState ?? null) }; return; }
  record('pending', pending);
  const artifactTexts = (pending.body.content ?? []).filter(block => block.type === 'text').map(block => block.text);
  let initialPayloadValid = false;
  try { initialPayloadValid = artifactTexts.length === 1 && JSON.stringify(JSON.parse(artifactTexts[0])) === JSON.stringify([{ guess: 25, response: 'Go higher' }]); } catch { /* Actual invalid payload remains recorded. */ }
  report.contract.initial_artifact_control_valid = initialPayloadValid;
  if (!initialPayloadValid) { report.observation = { initial_required_observed: true, answer_sent: false, goal_achieved: false, initial_artifact_control_valid: false }; return; }
  const originalContextHandle = receiveEnvelope(pending).contextHandle;
  assert.equal(typeof originalContextHandle, 'string'); assert(originalContextHandle);
  if (report.contract.initial_context_handle !== null && report.contract.initial_context_handle !== originalContextHandle) { report.observation = { initial_required_observed: true, answer_sent: false, goal_achieved: false, initial_context_binding_mismatch: { initial: report.contract.initial_context_handle, refreshed: originalContextHandle } }; return; }
  report.contract.original_context_handle = originalContextHandle;
  report.contract.pending_binding = { exchange_id: pending.exchange.exchange_id, fields: ['result.structuredContent.taskHandle', 'result.structuredContent.contextHandle', 'result.structuredContent.a2aState'], public: true };
  let answer;
  let answerError;
  let extensionAfter;
  let extensionError;
  if (modernTasks) {
    const waiting = await rpc('pending_extension_get_form', 'tasks/get', { taskId: originalTaskHandle });
    record('pending_extension', waiting);
    addReceipt(capture, waiting.exchange, 'bridge_task_record', waiting.body.taskId, null, ['result.taskId', 'result.status', 'result.inputRequests']);
    const keys = Object.keys(waiting.body.inputRequests ?? {});
    const request = keys.length === 1 ? waiting.body.inputRequests[keys[0]] : undefined;
    const properties = request?.params?.requestedSchema?.properties ?? {};
    const fields = Object.keys(properties);
    if (waiting.body.taskId !== originalTaskHandle || waiting.body.status !== 'input_required' || request?.method !== 'elicitation/create' || fields.length !== 1 || properties[fields[0]].type !== 'string') {
      report.observation = { initial_required_observed: true, answer_sent: false, goal_achieved: false, modern_answer_form_eligible: false, actual_input_requests: waiting.body.inputRequests ?? null };
      return;
    }
    report.contract.input_request_key = keys[0]; report.contract.requested_field = fields[0]; report.contract.requested_form = request;
    const args = { taskId: originalTaskHandle, inputResponses: { [keys[0]]: { action: 'accept', content: { [fields[0]]: answerText } } } };
    report.contract.answer_arguments = args; report.contract.answer_attempts = 1;
    try { answer = await rpc('fixed_same_task_answer_update', 'tasks/update', args); record('answer', answer); }
    catch (error) { answerError = errorText(error); }
    try { extensionAfter = await rpc('extension_get_after_answer', 'tasks/get', { taskId: originalTaskHandle }); record('final_extension', extensionAfter); }
    catch (error) { extensionError = errorText(error); }
  } else {
    const args = { agent: 'carol', text: answerText, taskHandle: originalTaskHandle, contextHandle: originalContextHandle };
    report.contract.answer_arguments = args; report.contract.answer_attempts = 1;
    try { answer = await tool('fixed_same_task_answer_send', 'a2a_send_message', args); record('answer', answer); receipt(answer, 'typed_answer_public_receipt'); }
    catch (error) { answerError = errorText(error); }
  }
  let final;
  let finalError;
  try { final = await tool('final_authoritative_original_get', 'a2a_get_task', { agent: 'carol', taskHandle: originalTaskHandle, historyLength: 10 }); record('final', final); receipt(final, 'explicit_peer_task_query_final'); }
  catch (error) { finalError = errorText(error); }
  const envelope = final ? receiveEnvelope(final) : undefined;
  report.observation = { initial_required_observed: true, answer_sent: true, answer_attempts: 1, final_authoritative_read_received: Boolean(final), final_application_error: final ? isToolError(final) : null, final_task_handle: envelope?.taskHandle ?? null, final_context_handle: envelope?.contextHandle ?? null, final_state: envelope?.a2aState ?? null, final_status: envelope?.status ?? null, original_task_preserved: envelope?.taskHandle === originalTaskHandle, original_context_preserved: envelope?.contextHandle === originalContextHandle, goal_achieved: Boolean(final && !isToolError(final) && envelope?.taskHandle === originalTaskHandle && envelope?.contextHandle === originalContextHandle && envelope?.a2aState === 'TASK_STATE_COMPLETED'), outer_answer_result_type: answer?.body?.resultType ?? null, outer_answer_is_goal_evidence: false, extension_status_after_answer: extensionAfter?.body?.status ?? null, source_expected_state_observed: envelope?.a2aState === 'TASK_STATE_INPUT_REQUIRED', answer_protocol_error: answerError ?? null, extension_protocol_error: extensionError ?? null, final_protocol_error: finalError ?? null };
  if (answerError || extensionError || finalError) throw new Error(`Protocol/capture failure retained after final read: ${JSON.stringify({ answerError, extensionError, finalError })}`);
}


