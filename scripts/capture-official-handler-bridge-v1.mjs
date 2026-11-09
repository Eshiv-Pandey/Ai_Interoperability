// New once-only official-handler bridge control. Historical captures unchanged.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createCapture, freezeBeforeStartup, launchBridge, stopChildren, finishCapture, hash,
  stamp, exclusiveJson, relative, workspace, errorText, initialText, answerText } from './log-reference-http.mjs';
import { runMgcrea } from './reference-mgcrea-v1.mjs';
import { runAmir } from './official-handler-amir-v1.mjs';

const variant = process.argv[2];
assert(['B1', 'B2', 'B3', 'B4'].includes(variant), 'Usage: node capture-official-handler-bridge-v1.mjs B1|B2|B3|B4');
const inherited = 'R' + variant.slice(1);
const specification = 'docs/research/official-handler-bridge-probe-v1.md';
const capture = createCapture(inherited, specification, [
  'scripts/check_official_handler_bridge.py', 'scripts/official-handler-amir-v1.mjs', 'scripts/replay_official_handler_bridge.py',
  'external/sdk-http-control-v1/environment-lock.json', 'external/sdk-http-control-v1/package.json',
  'docs/research/source-evidence/reference-continuation/normative/v1.0.1/docs/specification.md',
]);
const report = capture.report;
report.experiment_id = 'official-handler-bridge-fidelity/1';
report.official_variant = variant;
report.claim_limit = 'Bounded official-handler bridge fidelity using disclosed authored executor; no C1 novelty, second domain, natural failure prevalence, inverse mapping or human scientific review.';
report.protocol.a2a = '1.0-only official SDK1.1.0 JSONRPC HTTP handler; default context builder; no legacy compatibility';
report.namespaces.scope = 'Isolated official-handler loopback service with unchanged disclosed authored executor';
report.provenance.kind = 'official-handler-bridge-fidelity-control';
report.provenance.instrumentation.inherited_preload_labels = 'Logger uses historical authored-port labels. Actual service is the official Express handler, not the earlier custom HTTP wrapper.';
report.official_service = { sdk_version: '1.1.0', default_context_builder: true, legacy_compatibility: false,
  custom_http_wrapper_started: false, handler_mount: '/a2a', card_mount: '/.well-known/agent-card.json' };
report.native_controls = [];
report.ingress = [];
report.model_calls = 0;
report.remote_network_requests = 0;
report.native_control_plan = ['N1', 'N2', 'N3'];
report.origin_diagnostic_plan = 'E1';
report.native_eligible = false;
const modules = path.join(workspace, 'external/sdk-http-control-v1/node_modules');
const entity = bytes => ({ raw: bytes.toString('utf8'), base64: bytes.toString('base64'), bytes: bytes.length, sha256: hash(bytes) });
function entriesOf(directory) {
  const result = [];
  const visit = current => {
    for (const entry of readdirSync(current, { withFileTypes: true }).sort((a,b) => a.name.localeCompare(b.name))) {
      const file = path.join(current, entry.name);
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile()) { const bytes = readFileSync(file); result.push({ path: path.relative(directory, file).replaceAll('\\', '/'), bytes: bytes.length, sha256: hash(bytes) }); }
      else throw new Error('Unsupported preserved runtime entry: ' + file);
    }
  };
  visit(directory); return result;
}
function snapshotTree(source, index) {
  const entries = entriesOf(source);
  const target = path.join(capture.runDir, 'official-runtime-snapshots', String(index));
  mkdirSync(target, { recursive: true });
  for (const entry of entries) {
    const bytes = readFileSync(path.join(source, entry.path));
    assert.equal(hash(bytes), entry.sha256);
    const dest = path.join(target, entry.path); mkdirSync(path.dirname(dest), { recursive: true });
    writeFileSync(dest, bytes, { flag: 'wx' });
  }
  return { source: relative(source), snapshot: relative(target), entries, entries_sha256: hash(JSON.stringify(entries)) };
}
let server;
let executor;
let sequence = 0;
async function nativeRequest(caseId, method, params, target) {
  const requestBody = { jsonrpc: '2.0', id: caseId + '-' + (++sequence), method, params };
  const bytes = Buffer.from(JSON.stringify(requestBody));
  const record = { case_id: caseId, executed: true, attempt: 1, started: stamp(),
    request: { url: target, method: 'POST', headers: { 'content-type': 'application/json', 'A2A-Version': '1.0' }, json: requestBody, ...entity(bytes) } };
  if (caseId === 'E1') report.origin_diagnostic = record; else report.native_controls.push(record);
  try {
    const response = await fetch(target, { method: 'POST', headers: record.request.headers, body: record.request.raw, signal: AbortSignal.timeout(10000) });
    const reply = Buffer.from(await response.arrayBuffer());
    record.response = { status: response.status, headers: Object.fromEntries(response.headers), ...entity(reply) };
    try { record.response.json = JSON.parse(record.response.raw); } catch (error) { record.response.parse_error = errorText(error); }
  } catch (error) { record.error = errorText(error); }
  record.completed = stamp();
  return record;
}
function sendParams(text, original) {
  return { message: { messageId: randomUUID(), role: 'ROLE_USER', parts: [{ text, mediaType: 'text/plain' }],
    ...(original ? { taskId: original.task_id, contextId: original.context_id, referenceTaskIds: [original.task_id] } : {}) },
    configuration: { acceptedOutputModes: ['text/plain'] } };
}
try {
  freezeBeforeStartup(capture);
  const directories = [modules,
    ...report.pre_execution.installed_runtime_dependencies.map(item => path.join(workspace, item.manifest.root)),
    ...report.pre_execution.port_runtime_dependencies.map(item => path.join(workspace, item.manifest.root))];
  const trees = [...new Set(directories)].map(snapshotTree);
  report.official_pre_execution = { frozen: stamp(), native_control_plan: report.native_control_plan,
    origin_diagnostic_plan: report.origin_diagnostic_plan, official_variant: variant,
    inherited_variant: inherited, official_service: JSON.parse(JSON.stringify(report.official_service)), trees,
    standard_pre_execution_ledger_sha256: hash(readFileSync(path.join(capture.runDir, 'pre-execution-ledger.json'))) };
  exclusiveJson(path.join(capture.runDir, 'official-pre-execution-ledger.json'), report.official_pre_execution);

  const express = (await import(pathToFileURL(path.join(modules, 'express/index.js')).href)).default;
  const { jsonRpcHandler, agentCardHandler } = await import(pathToFileURL(path.join(modules, '@a2a-js/sdk/dist/server/express/index.js')).href);
  const { DefaultRequestHandler, InMemoryTaskStore, UnauthenticatedUser } = await import(pathToFileURL(path.join(modules, '@a2a-js/sdk/dist/server/index.js')).href);
  const { CarolReferenceExecutor } = await import(pathToFileURL(path.join(workspace, 'scripts/fixtures/carol-reference-v1.mjs')).href);
  executor = new CarolReferenceExecutor();
  const card = { name: 'Carol official-handler bridge fidelity control', description: 'Authored1.0-only card; unchanged disclosed executor',
    version: 'official-handler-bridge-v1', supportedInterfaces: [{ url: 'http://127.0.0.1:0/a2a', protocolVersion: '1.0', protocolBinding: 'JSONRPC', tenant: '' }],
    capabilities: { streaming: false, pushNotifications: false, extensions: [], extendedAgentCard: false },
    defaultInputModes: ['text/plain'], defaultOutputModes: ['text/plain'], skills: [], securitySchemes: {}, securityRequirements: [], signatures: [] };
  const requestHandler = new DefaultRequestHandler(card, new InMemoryTaskStore(), executor);
  const app = express();
  app.use((req, res, next) => {
    const chunks = []; const started = stamp();
    req.on('data', chunk => chunks.push(Buffer.from(chunk)));
    res.on('finish', () => report.ingress.push({ method: req.method, url: req.originalUrl, headers: { ...req.headers },
      body: entity(Buffer.concat(chunks)), started, completed: stamp(), response_status: res.statusCode }));
    next();
  });
  app.use('/.well-known/agent-card.json', agentCardHandler({ agentCardProvider: () => requestHandler.getAgentCard() }));
  app.use('/a2a', jsonRpcHandler({ requestHandler, userBuilder: () => new UnauthenticatedUser() }));
  server = createServer(app);
  await new Promise((resolve,reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const base = 'http://127.0.0.1:' + server.address().port;
  card.supportedInterfaces[0].url = base + '/a2a';
  report.card = card; report.fixture_endpoint = base; report.official_service.endpoint = card.supportedInterfaces[0].url;
  report.official_service.started = stamp();
  const n1 = await nativeRequest('N1', 'SendMessage', sendParams(initialText), report.official_service.endpoint);
  const originalTask = n1.response?.json?.result?.task;
  let nativeArtifactEligible = false;
  try {
    nativeArtifactEligible = originalTask.artifacts.length === 1 && originalTask.artifacts[0].parts.length === 1
      && JSON.stringify(JSON.parse(originalTask.artifacts[0].parts[0].text)) === JSON.stringify([{ guess: 25, response: 'Go higher' }]);
  } catch { /* Retain an invalid native artifact; dependent bridge actions remain unexecuted. */ }
  if (n1.response?.status === 200 && originalTask?.status?.state === 'TASK_STATE_INPUT_REQUIRED'
      && nativeArtifactEligible && typeof originalTask.id === 'string' && originalTask.id && typeof originalTask.contextId === 'string' && originalTask.contextId) {
    const original = { task_id: originalTask.id, context_id: originalTask.contextId, public_source_case: 'N1' };
    report.native_original = original;
    const n2 = await nativeRequest('N2', 'SendMessage', sendParams(answerText, original), report.official_service.endpoint);
    const n3 = await nativeRequest('N3', 'GetTask', { id: original.task_id, historyLength: 10 }, report.official_service.endpoint);
    report.native_eligible = n2.response?.status === 200 && n2.response?.json?.result?.task?.status?.state === 'TASK_STATE_COMPLETED'
      && n2.response?.json?.result?.task?.id === original.task_id && n2.response?.json?.result?.task?.contextId === original.context_id
      && n3.response?.status === 200 && n3.response?.json?.result?.id === original.task_id
      && n3.response?.json?.result?.contextId === original.context_id && n3.response?.json?.result?.status?.state === 'TASK_STATE_COMPLETED';
  } else {
    for (const case_id of ['N2', 'N3']) report.native_controls.push({ case_id, executed: false, reason: 'N1 source-valid public pending prefix unavailable' });
  }
  if (report.native_eligible) {
    const bridge = launchBridge(capture, base);
    try {
      if (variant === 'B1' || variant === 'B2') await runAmir(capture, inherited, bridge);
      else await runMgcrea(capture, inherited, base, bridge);
    } catch (error) { report.caller_error = errorText(error); }
    let events = [];
    try { events = readFileSync(capture.nativeLog, 'utf8').split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)); }
    catch (error) { report.native_correlation_error = errorText(error); }
    const initial = events.find(item => item.type === 'exchange-completed' && item.request?.json?.method === 'SendMessage'
      && item.request.json.params?.message?.parts?.[0]?.text === initialText && item.response?.json?.result?.task?.id);
    if (initial) {
      const task = initial.response.json.result.task;
      report.evaluator_binding = { source: 'evaluator-private captured native initial response', native_exchange_id: initial.exchange_id,
        response_sha256: initial.response.sha256, task_id: task.id, context_id: task.contextId, fed_to_bridge_caller: false, recovery_action: false };
      await nativeRequest('E1', 'GetTask', { id: task.id, historyLength: 10 }, report.official_service.endpoint);
    } else report.origin_diagnostic = { case_id: 'E1', executed: false, reason: 'No identifiable native task from initial bridge exchange' };
    report.outcome = report.caller_error || report.native_correlation_error ? 'failed' : 'recorded';
    report.exit_code = report.outcome === 'failed' ? 1 : 0;
  } else {
    report.bridge_unexecuted_reason = 'Native header-positive eligibility not established';
    report.origin_diagnostic = { case_id: 'E1', executed: false, reason: report.bridge_unexecuted_reason };
    report.outcome = 'recorded-native-ineligible'; report.exit_code = 0;
  }
} catch (error) {
  report.outcome = 'failed'; report.exit_code = 1; report.error = errorText(error);
} finally {
  for (const case_id of report.native_control_plan) {
    if (!report.native_controls.some(item => item.case_id === case_id)) {
      report.native_controls.push({ case_id, executed: false, reason: 'Prior setup/control exception retained: ' + (report.error ?? 'Unavailable eligibility') });
    }
  }
  report.origin_diagnostic ??= { case_id: 'E1', executed: false, reason: 'Prior setup/bridge exception retained: ' + (report.error ?? 'No identifiable initial bridge task') };
  await stopChildren(capture);
  report.official_service.cleanup_started = stamp();
  if (server?.listening) {
    try { server.closeAllConnections(); await new Promise((resolve,reject) => server.close(error => error ? reject(error) : resolve())); }
    catch (error) { report.official_service.cleanup_error = errorText(error); report.outcome = 'failed'; report.exit_code = 1; }
  }
  report.official_service.server_listening = server?.listening ?? false;
  report.official_service.closed = stamp();
  report.official_post_trees = (report.official_pre_execution?.trees ?? []).map(item => {
    try { return { source: item.source, entries_sha256: hash(JSON.stringify(entriesOf(path.join(workspace, item.source)))) }; }
    catch (error) { return { source: item.source, error: errorText(error) }; }
  });
  report.official_post_bridge_trees = [report.pre_execution?.bridge_source_manifest, report.pre_execution?.bridge_dist_manifest].filter(Boolean).map(item => {
    try { return { root: item.root, entries_sha256: hash(JSON.stringify(entriesOf(path.join(workspace, item.root)))) }; }
    catch (error) { return { root: item.root, error: errorText(error) }; }
  });
  report.executor_task_contexts = executor ? [...executor.taskContexts.entries()] : [];
  report.control_costs = { native_control_requests: report.native_controls.filter(item => item.executed).length,
    evaluator_only_requests: report.origin_diagnostic?.executed ? 1 : 0, server_ingress_requests: report.ingress.length,
    bridge_children_started: capture.children.length, model_calls: 0, remote_network_requests: 0 };
  finishCapture(capture);
  process.exitCode = report.exit_code ?? 1;
}

