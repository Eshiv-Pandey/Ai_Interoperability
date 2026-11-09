// PREPARE-ONLY module for the separately frozen Carol bridge probe.
// No top-level service startup, SDK import, model call, or capture execution.
import { randomUUID } from 'node:crypto';
import { createStdioRpc, addReceipt, pause, stamp } from './log-reference-http.mjs';

const INITIAL_TEXT = '{"action":"shuffle","history":[{"guess":25,"response":"Go higher"}]}';
const ANSWER_TEXT = 'Well done!';
const errorText = error => error?.stack ?? String(error);

export async function runMgcrea(capture, variant, fixtureUrl, bridge) {
  if (!['R3', 'R4'].includes(variant)) throw new Error('runMgcrea variant must be R3 or R4');
  const rpc = createStdioRpc(capture, bridge);
  const report = capture.report;
  report.tool_interpretations ??= [];
  report.module_errors ??= [];
  report.module = { name: 'reference-mgcrea-v1', variant, started: stamp(), execution: 'MCP stdio client to unmodified pinned mgcrea bridge' };
  const recordError = (stage, error, kind) => {
    const entry = { stage, kind, error: errorText(error), observed: stamp() };
    report.module_errors.push(entry);
    return entry;
  };
  async function tool(phase, name, args, waitMs) {
    const reply = await rpc(phase, 'tools/call', { name, arguments: args }, false, waitMs ?? 10000);
    if (reply.json?.error) throw new Error(`${phase}: MCP JSONRPC error ${JSON.stringify(reply.json.error)}`);
    const body = reply.body;
    if (!body || typeof body !== 'object') throw new Error(`${phase}: missing MCP tool-result object`);
    let decoded;
    let encoding;
    if (body.structuredContent !== undefined) {
      decoded = body.structuredContent;
      encoding = 'structuredContent object';
    } else {
      if (body.content?.[0]?.type !== 'text' || typeof body.content[0].text !== 'string') throw new Error(`${phase}: expected JSON inside result.content[0].text`);
      decoded = JSON.parse(body.content[0].text);
      encoding = 'JSON serialized inside result.content[0].text';
    }
    if (decoded === null || typeof decoded !== 'object' || Array.isArray(decoded)) throw new Error(`${phase}: decoded tool bundle is not an object`);
    const interpretation = {
      exchange_id: reply.exchange.exchange_id, phase, tool: name, arguments: args,
      encoding, decoded, mcp_tool_error: body.isError === true || body.isToolError === true,
      native_rpc_error: name === 'a2a_request' && decoded.error !== undefined ? decoded.error : null,
    };
    report.tool_interpretations.push(interpretation);
    return { ...reply, decoded, encoding, interpretation };
  }
  function receipt(reply, role, taskId, contextId, decodedPaths) {
    const structured = reply.encoding === 'structuredContent object';
    const actualPaths = decodedPaths.filter(field => field.split('.').reduce((value, key) => value?.[key], reply.decoded) !== undefined);
    addReceipt(capture, reply.exchange, role, taskId, contextId, structured
      ? actualPaths.map(field => `result.structuredContent.${field}`)
      : ['result.content[0].text']);
    const entry = report.receipts.at(-1);
    entry.bundle_encoding = reply.encoding;
    entry.decoded_check_field_paths = decodedPaths;
    entry.decoded_field_paths = actualPaths;
    entry.decoded_bundle_fields = Object.keys(reply.decoded);
    entry.public_binding_only = true;
    return entry;
  }
  function finished(observation, outcome = 'recorded') {
    report.observation = observation;
    report.module.outcome = outcome;
    report.module.completed = stamp();
    return { contract: report.contract ?? null, observation, module_outcome: outcome };
  }
  const initialized = await rpc('initialize', 'initialize', {
    protocolVersion: '2025-11-25', capabilities: {},
    clientInfo: { name: 'Carol-reference-development-observer', version: '1.0.0' },
  });
  if (initialized.body?.protocolVersion !== '2025-11-25') throw new Error('Pinned mgcrea MCP protocol negotiation did not return 2025-11-25');
  await rpc('initialized_notification', 'notifications/initialized', undefined, true);
  const listed = await rpc('discover_full_tools', 'tools/list', {});
  if (!Array.isArray(listed.body?.tools)) throw new Error('tools/list did not return its tools array');
  const tools = listed.body.tools;
  report.discovery = {
    initialize_exchange_id: initialized.exchange.exchange_id,
    tools_exchange_id: listed.exchange.exchange_id,
    tool_count: tools.length, tools,
  };
  for (const name of ['a2a_send_message', 'a2a_get_task', ...(variant === 'R4' ? ['a2a_request'] : [])]) {
    if (!tools.some(tool => tool.name === name)) throw new Error(`Required pinned write-enabled tool is absent: ${name}`);
  }
  if (variant === 'R4') {
    const methods = tools.find(tool => tool.name === 'a2a_request').inputSchema?.properties?.method?.enum;
    if (!Array.isArray(methods) || !methods.includes('SendMessage') || !methods.includes('GetTask')) throw new Error('Raw request tool profile does not permit both SendMessage and GetTask');
  }
  report.contract = {
    variant, initial_text: INITIAL_TEXT, answer_text: ANSWER_TEXT,
    source_expected_original_state: variant === 'R3' ? 'input_required' : 'completed',
    goal_id: 'logical-completion-and-original-association',
    goal: 'Original native task and context completed after the fixed answer',
    terminal_artifact_required: false, completion_requires_authoritative_get: true,
    initial_read_history_length: 10, final_read_history_length: 10,
    initial_observation_bound_ms: 5000, initial_poll_interval_ms: 50,
    typed_send_eligibility: true, raw_send_eligibility: tools.some(tool => tool.name === 'a2a_request' && tool.inputSchema?.properties?.method?.enum?.includes('SendMessage')),
    selected_answer_action: variant === 'R3' ? 'a2a_send_message' : 'a2a_request(SendMessage)',
    final_read_action: variant === 'R3' ? 'a2a_get_task(refresh:true)' : 'a2a_request(GetTask)',
    native_parameters_from_private_sidecar: false, answer_attempts: 0,
  };
  const created = await tool('initial_typed_send', 'a2a_send_message', { url: fixtureUrl, text: INITIAL_TEXT });
  report.initial = { exchange_id: created.exchange.exchange_id, decoded: created.decoded, encoding: created.encoding };
  if (created.interpretation.mcp_tool_error) {
    return finished({ initial_required_observed: false, answer_sent: false, goal_achieved: false, application_error: created.decoded }, 'recorded-application-error');
  }
  const originalTaskId = created.decoded.task?.id;
  if (created.decoded.replied_with !== 'task' || typeof originalTaskId !== 'string' || !originalTaskId) throw new Error('Initial typed send did not supply a public native task receipt');
  receipt(created, 'typed_initial_public_task_receipt', originalTaskId, created.decoded.task.context_id ?? null, ['task.id', 'task.context_id', 'task.state']);
  report.contract.original_task_id = originalTaskId;
  report.contract.initial_context_id = created.decoded.task.context_id ?? null;
  report.contract.initial_binding = { exchange_id: created.exchange.exchange_id, encoding: created.encoding, decoded_paths: ['task.id', 'task.context_id'], public: true };

  const until = Date.now() + 5000;
  report.initial_reads = [];
  let waiting;
  while (Date.now() < until) {
    let observed;
    try {
      observed = await tool('initial_authoritative_pending_get', 'a2a_get_task', { task_id: originalTaskId, history_length: 10, refresh: true }, Math.max(1, until - Date.now()));
    } catch (error) {
      recordError('initial_authoritative_pending_get', error, 'observation-or-protocol-error');
      finished({ initial_required_observed: false, answer_sent: false, goal_achieved: false, initial_observation_error: errorText(error) }, 'recorded-protocol-error');
      throw error;
    }
    report.initial_reads.push({ exchange_id: observed.exchange.exchange_id, decoded: observed.decoded, encoding: observed.encoding });
    receipt(observed, 'explicit_peer_task_query_pending', observed.decoded.id ?? null, observed.decoded.context_id ?? null, ['id', 'context_id', 'state', 'artifacts', 'history']);
    if (observed.interpretation.mcp_tool_error) return finished({ initial_required_observed: false, answer_sent: false, goal_achieved: false, application_error: observed.decoded }, 'recorded-application-error');
    if (observed.decoded.id !== originalTaskId) return finished({ initial_required_observed: false, answer_sent: false, goal_achieved: false, public_task_binding_mismatch: { requested: originalTaskId, returned: observed.decoded.id ?? null } }, 'recorded-association-mismatch');
    if (observed.decoded.state === 'input_required') { waiting = observed; break; }
    const remaining = until - Date.now();
    if (remaining > 0) await pause(Math.min(50, remaining));
  }
  if (!waiting) return finished({ initial_required_observed: false, initial_observation_timeout: true, answer_sent: false, goal_achieved: false, observed_initial_states: report.initial_reads.map(read => read.decoded.state ?? null) }, 'recorded-bounded-initial-miss');
  const originalContextId = waiting.decoded.context_id;
  if (typeof originalContextId !== 'string' || !originalContextId) throw new Error('Required-state public receipt lacks a native context ID');
  if (report.contract.initial_context_id !== null && report.contract.initial_context_id !== originalContextId) return finished({ initial_required_observed: true, answer_sent: false, goal_achieved: false, public_context_binding_mismatch: { initial: report.contract.initial_context_id, refreshed: originalContextId } }, 'recorded-association-mismatch');
  report.contract.original_context_id = originalContextId;
  report.contract.pending_binding = { exchange_id: waiting.exchange.exchange_id, encoding: waiting.encoding, decoded_paths: ['id', 'context_id', 'state'], public: true };
  report.pending = { exchange_id: waiting.exchange.exchange_id, decoded: waiting.decoded, encoding: waiting.encoding };
  const initialArtifactTexts = Array.isArray(waiting.decoded.artifacts) ? waiting.decoded.artifacts.map(artifact => artifact?.text) : [];
  let decodedInitialHistory;
  let artifactParseError;
  if (initialArtifactTexts.length === 1 && typeof initialArtifactTexts[0] === 'string') {
    try { decodedInitialHistory = JSON.parse(initialArtifactTexts[0]); }
    catch (error) { artifactParseError = errorText(error); }
  }
  const initialArtifactMatches = Array.isArray(decodedInitialHistory)
    && decodedInitialHistory.length === 1
    && decodedInitialHistory[0] !== null
    && typeof decodedInitialHistory[0] === 'object'
    && !Array.isArray(decodedInitialHistory[0])
    && Object.keys(decodedInitialHistory[0]).length === 2
    && decodedInitialHistory[0].guess === 25
    && decodedInitialHistory[0].response === 'Go higher';
  report.initial_condition = {
    required_state_observed: true, task_id: originalTaskId, context_id: originalContextId,
    artifact_texts: initialArtifactTexts, decoded_history: decodedInitialHistory ?? null,
    expected_history: [{ guess: 25, response: 'Go higher' }],
    artifact_history_matches: initialArtifactMatches,
    artifact_parse_error: artifactParseError ?? null,
  };
  if (!initialArtifactMatches) return finished({
    initial_required_observed: true, initial_artifact_expected_history_observed: false,
    initial_artifact_mismatch: report.initial_condition, answer_sent: false, goal_achieved: false,
  }, 'recorded-initial-artifact-mismatch');

  const answerArgs = variant === 'R3'
    ? { url: fixtureUrl, text: ANSWER_TEXT, task_id: originalTaskId, context_id: originalContextId }
    : { url: fixtureUrl, method: 'SendMessage', params: {
      message: { messageId: randomUUID(), taskId: originalTaskId, contextId: originalContextId, role: 'ROLE_USER', parts: [{ text: ANSWER_TEXT, mediaType: 'text/plain' }], referenceTaskIds: [originalTaskId] },
      configuration: { returnImmediately: false, acceptedOutputModes: ['text/plain'] },
    } };
  report.contract.answer_arguments = answerArgs;
  report.contract.answer_attempts = 1;
  let answered;
  let answerProtocolError;
  try {
    answered = await tool('fixed_same_task_answer', variant === 'R3' ? 'a2a_send_message' : 'a2a_request', answerArgs);
    report.answer = { exchange_id: answered.exchange.exchange_id, decoded: answered.decoded, encoding: answered.encoding, mcp_tool_error: answered.interpretation.mcp_tool_error, native_rpc_error: answered.interpretation.native_rpc_error };
    if (variant === 'R3') receipt(answered, 'typed_answer_public_receipt', answered.decoded.task?.id ?? null, answered.decoded.task?.context_id ?? null, ['task.id', 'task.context_id', 'task.state']);
    else receipt(answered, 'raw_native_answer_public_receipt', answered.decoded.result?.task?.id ?? null, answered.decoded.result?.task?.contextId ?? null, ['jsonrpc', 'id', 'error', 'result.task.id', 'result.task.contextId', 'result.task.status.state']);
  } catch (error) {
    answerProtocolError = error;
    recordError('fixed_same_task_answer', error, 'protocol-or-transport-error');
  }

  // One final authoritative read follows even an application-error answer.
  let finalRead;
  let finalProtocolError;
  try {
    finalRead = variant === 'R3'
      ? await tool('final_authoritative_original_get', 'a2a_get_task', { task_id: originalTaskId, history_length: 10, refresh: true })
      : await tool('final_authoritative_original_raw_get', 'a2a_request', { url: fixtureUrl, method: 'GetTask', params: { id: originalTaskId, historyLength: 10 } });
    report.final = { exchange_id: finalRead.exchange.exchange_id, decoded: finalRead.decoded, encoding: finalRead.encoding, mcp_tool_error: finalRead.interpretation.mcp_tool_error, native_rpc_error: finalRead.interpretation.native_rpc_error };
    if (variant === 'R3') receipt(finalRead, 'explicit_peer_task_query_final', finalRead.decoded.id ?? null, finalRead.decoded.context_id ?? null, ['id', 'context_id', 'state', 'artifacts', 'history']);
    else receipt(finalRead, 'raw_native_peer_task_query_final', finalRead.decoded.result?.id ?? null, finalRead.decoded.result?.contextId ?? null, ['jsonrpc', 'id', 'error', 'result.id', 'result.contextId', 'result.status.state', 'result.artifacts', 'result.history']);
  } catch (error) {
    finalProtocolError = error;
    recordError('final_authoritative_original_get', error, 'protocol-or-transport-error');
  }
  const task = variant === 'R3' ? finalRead?.decoded : finalRead?.decoded.result;
  const finalTaskId = task?.id ?? null;
  const finalContextId = (variant === 'R3' ? task?.context_id : task?.contextId) ?? null;
  const rawFinalState = (variant === 'R3' ? task?.state : task?.status?.state) ?? null;
  const finalState = typeof rawFinalState === 'string' ? rawFinalState.replace(/^TASK_STATE_/, '').toLowerCase() : null;
  const finalApplicationError = finalRead?.interpretation.mcp_tool_error === true || finalRead?.interpretation.native_rpc_error !== null && finalRead?.interpretation.native_rpc_error !== undefined;
  const observation = {
    initial_required_observed: true, initial_artifact_expected_history_observed: true, answer_sent: true, answer_attempts: 1,
    answer_application_error: answered?.interpretation.mcp_tool_error === true || answered?.interpretation.native_rpc_error !== null && answered?.interpretation.native_rpc_error !== undefined,
    final_authoritative_read_received: Boolean(finalRead), final_application_error: finalApplicationError,
    final_task_id: finalTaskId, final_context_id: finalContextId, final_state: finalState, final_state_returned: rawFinalState,
    original_task_preserved: finalTaskId === originalTaskId,
    original_context_preserved: finalContextId === originalContextId,
    original_task_completed: finalState === 'completed',
    goal_achieved: !finalApplicationError && finalTaskId === originalTaskId && finalContextId === originalContextId && finalState === 'completed',
    source_expected_state_observed: finalState === report.contract.source_expected_original_state,
    answer_protocol_error: answerProtocolError ? errorText(answerProtocolError) : null,
    final_protocol_error: finalProtocolError ? errorText(finalProtocolError) : null,
    interpretation: 'Source waiting/completed expectations are data; final public native task association and state determine the goal. No terminal artifact projector is used.',
  };
  const result = finished(observation, answerProtocolError || finalProtocolError ? 'recorded-protocol-error' : 'recorded');
  if (answerProtocolError || finalProtocolError) throw new AggregateError([answerProtocolError, finalProtocolError].filter(Boolean), 'MCP/native protocol or transport failure retained after final read attempt');
  return result;
}
