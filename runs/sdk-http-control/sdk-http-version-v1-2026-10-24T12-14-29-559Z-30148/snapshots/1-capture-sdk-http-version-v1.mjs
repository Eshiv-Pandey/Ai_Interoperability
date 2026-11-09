// Once-only SOFTWARE/SDK HTTP CONTROL with unchanged disclosed Carol executor.
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { createServer } from 'node:http';
import { appendFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const driver = fileURLToPath(import.meta.url);
const root = path.dirname(path.dirname(driver));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const relative = filename => path.relative(root, filename).replaceAll('\\', '/');
const stamp = () => ({ utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString() });
const json = (filename, value) => writeFileSync(filename, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
const sdkOriginal = path.join(root, 'external/a2a-to-mcp/node_modules/@a2a-js/sdk');
const modules = path.join(root, 'external/sdk-http-control-v1/node_modules');
const executorFile = path.join(root, 'scripts/fixtures/carol-reference-v1.mjs');
const sourceFiles = [driver, path.join(root, 'scripts/check_sdk_http_version.py'), executorFile,
  path.join(root, 'docs/research/sdk-http-version-probe-v1.md'),
  path.join(root, 'docs/research/source-evidence/reference-continuation/normative/v1.0.1/docs/specification.md'),
  path.join(root, 'external/sdk-http-control-v1/environment-lock.json'),
  path.join(root, 'external/sdk-http-control-v1/package.json'),
  path.join(root, 'runs/sdk-http-control/cache-copy-ledger-v1.json'),
  path.join(root, 'scripts/prepare_sdk_http_environment.py')];
const plan = [
  ['H1', 'SendMessage', null, null], ['H2', 'SendMessage', '', null],
  ['H3', 'SendMessage', '1.0', null], ['H4', 'SendMessage', '0.3', null],
  ['H5', 'SendMessage', null, '1.0'], ['H6', 'SendMessage', '1.0', '1.0'],
  ['H7', 'SendMessage', '1.0', null], ['H8', 'GetTask', '1.0', null],
  ['H9', 'GetTask', null, null], ['H10', 'GetTask', null, '1.0'],
].map(([case_id, method, version_header, version_query]) => ({ case_id, method, version_header, version_query }));
const runId = `sdk-http-version-v1-${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}-${process.pid}`;
const directory = path.join(root, 'runs/sdk-http-control', runId);
mkdirSync(directory, { recursive: true });
const eventsFile = path.join(directory, 'events.jsonl'); writeFileSync(eventsFile, '', { flag: 'wx' });
const event = value => appendFileSync(eventsFile, JSON.stringify({ observed: stamp(), ...value }) + '\n');
const report = { schema_version: 'sdk-http-version-control/1', kind: 'SOFTWARE/SDK HTTP CONTROL USING DISCLOSED CAROL EXECUTOR',
  run_id: runId, pid: process.pid, started: stamp(), case_plan: plan, cases: [], ingress: [],
  model_calls: 0, remote_network_requests: 0, child_processes_started: 0,
  default_context_builder: true, legacy_compatibility: false, source_hashes: [], dependency_trees: [],
  outcome: 'setup-started', claim_limit: 'Pinned official-handler control only; no third bridge, natural prevalence, novel method or human review' };
let server; let executor;
function tree(directory) {
  const entries = [];
  const visit = current => {
    for (const entry of readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const filename = path.join(current, entry.name);
      if (entry.isDirectory()) visit(filename);
      else if (entry.isFile()) { const bytes = readFileSync(filename); entries.push({ path: path.relative(directory, filename).replaceAll('\\', '/'), bytes: bytes.length, sha256: hash(bytes) }); }
      else throw new Error(`Unsupported installed entry: ${filename}`);
    }
  };
  visit(directory); return entries;
}
const entity = bytes => ({ raw: bytes.toString('utf8'), base64: bytes.toString('base64'), bytes: bytes.length, sha256: hash(bytes) });
try {
  assert.equal(process.version, 'v22.13.0');
  assert.equal(hash(readFileSync(executorFile)), 'b6b6492ee5c27cf5db0474054b0f18a8feafe0859d9faaa4fd67946c7768626d');
  assert.equal(hash(readFileSync(path.join(modules, '@a2a-js/sdk/dist/server/express/index.js'))), hash(readFileSync(path.join(sdkOriginal, 'dist/server/express/index.js'))));
  const snapshots = path.join(directory, 'snapshots'); mkdirSync(snapshots);
  for (const [index, filename] of sourceFiles.entries()) {
    const bytes = readFileSync(filename); const copy = path.join(snapshots, `${index + 1}-${path.basename(filename)}`);
    writeFileSync(copy, bytes, { flag: 'wx' });
    report.source_hashes.push({ path: relative(filename), snapshot: relative(copy), bytes: bytes.length, sha256: hash(bytes) });
  }
  for (const [index, source] of [modules, sdkOriginal, path.join(root, 'external/a2a-to-mcp/node_modules/jose')].entries()) {
    const entries = tree(source); const copy = path.join(snapshots, `tree-${index + 1}`); mkdirSync(copy);
    for (const item of entries) {
      const target = path.join(copy, item.path); mkdirSync(path.dirname(target), { recursive: true });
      const bytes = readFileSync(path.join(source, item.path)); assert.equal(hash(bytes), item.sha256);
      writeFileSync(target, bytes, { flag: 'wx' });
    }
    report.dependency_trees.push({ source: relative(source), snapshot: relative(copy), entries, entries_sha256: hash(JSON.stringify(entries)) });
  }
  report.node = { version: process.version, executable: process.execPath, sha256: hash(readFileSync(process.execPath)) };
  report.pre_execution = { frozen: stamp(), source_hashes: report.source_hashes, dependency_trees: report.dependency_trees, node: report.node, case_plan: plan };
  const ledgerFile = path.join(directory, 'pre-execution-ledger.json'); json(ledgerFile, report.pre_execution);
  event({ type: 'ledger-frozen-before-imports', sha256: hash(readFileSync(ledgerFile)) });
  const express = (await import(pathToFileURL(path.join(modules, 'express/index.js')).href)).default;
  const { jsonRpcHandler } = await import(pathToFileURL(path.join(modules, '@a2a-js/sdk/dist/server/express/index.js')).href);
  const { DefaultRequestHandler, InMemoryTaskStore, UnauthenticatedUser } = await import(pathToFileURL(path.join(modules, '@a2a-js/sdk/dist/server/index.js')).href);
  const { CarolReferenceExecutor } = await import(pathToFileURL(executorFile).href);
  executor = new CarolReferenceExecutor();
  const card = { name: 'Carol official-handler software control', description: 'Constructed1.0-only card with unchanged disclosed executor', version: 'sdk-control-v1',
    supportedInterfaces: [{ url: 'http://127.0.0.1:0/a2a', protocolVersion: '1.0', protocolBinding: 'JSONRPC', tenant: '' }],
    capabilities: { streaming: false, pushNotifications: false, extensions: [], extendedAgentCard: false },
    defaultInputModes: ['text/plain'], defaultOutputModes: ['text/plain'], skills: [], securitySchemes: {}, securityRequirements: [], signatures: [] };
  const handler = new DefaultRequestHandler(card, new InMemoryTaskStore(), executor);
  const app = express();
  app.use((request, response, next) => {
    const chunks = []; const started = stamp();
    request.on('data', chunk => chunks.push(Buffer.from(chunk)));
    response.on('finish', () => {
      const ingress = { method: request.method, url: request.originalUrl, headers: { ...request.headers }, body: entity(Buffer.concat(chunks)), started,
        completed: stamp(), response_status: response.statusCode };
      report.ingress.push(ingress); event({ type: 'server-ingress-completed', ingress });
    });
    next();
  });
  app.use('/a2a', jsonRpcHandler({ requestHandler: handler, userBuilder: () => new UnauthenticatedUser() }));
  server = createServer(app);
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const base = `http://127.0.0.1:${server.address().port}`; card.supportedInterfaces[0].url = `${base}/a2a`;
  report.endpoint = `${base}/a2a`; report.card = card; report.server_started = stamp();
  event({ type: 'server-ready', endpoint: report.endpoint });
  const initial = JSON.stringify({ action: 'shuffle', history: [{ guess: 25, response: 'Go higher' }] });
  let original;
  for (const control of plan) {
    if (Number(control.case_id.slice(1)) >= 7 && !original) {
      report.cases.push({ case_id: control.case_id, executed: false, reason: 'H3 public positive task/context unavailable' });
      continue;
    }
    const sequence = Number(control.case_id.slice(1));
    const record = { case_id: control.case_id, executed: true, attempt: 1, started: stamp() };
    report.cases.push(record);
    const url = new URL(report.endpoint); if (control.version_query !== null) url.searchParams.set('A2A-Version', control.version_query);
    const headers = { 'content-type': 'application/json' }; if (control.version_header !== null) headers['A2A-Version'] = control.version_header;
    const params = control.method === 'GetTask' ? { id: original.task_id, historyLength: 10 } : {
      message: { messageId: randomUUID(), role: 'ROLE_USER', parts: [{ text: sequence === 7 ? 'Well done' : initial, mediaType: 'text/plain' }],
        ...(sequence === 7 ? { taskId: original.task_id, contextId: original.context_id, referenceTaskIds: [original.task_id] } : {}) },
      configuration: { acceptedOutputModes: ['text/plain'] } };
    const body = { jsonrpc: '2.0', id: sequence, method: control.method, params };
    record.request = { url: url.href, method: 'POST', headers, json: body, ...entity(Buffer.from(JSON.stringify(body))) };
    event({ type: 'case-started', case_id: control.case_id, request: record.request });
    try {
      const response = await fetch(url, { method: 'POST', headers, body: record.request.raw, signal: AbortSignal.timeout(10000) });
      const bytes = Buffer.from(await response.arrayBuffer());
      record.response = { status: response.status, headers: Object.fromEntries(response.headers), ...entity(bytes), observed: stamp() };
      try { record.response.json = JSON.parse(bytes.toString('utf8')); } catch (error) { record.response.parse_error = String(error); }
      if (sequence === 3) {
        const task = record.response.json?.result?.task;
        if (typeof task?.id === 'string' && task.id && typeof task?.contextId === 'string' && task.contextId) {
          original = { task_id: task.id, context_id: task.contextId, public_source_case: 'H3' };
          report.original = original;
        }
      }
    } catch (error) { record.error = error?.stack ?? String(error); }
    record.executor_task_contexts = [...executor.taskContexts.entries()]; record.completed = stamp();
    event({ type: 'case-completed', case: record });
  }
  report.outcome = 'recorded-once'; report.exit_code = 0;
} catch (error) {
  report.error = error?.stack ?? String(error); report.outcome = 'failed-setup-or-execution'; report.exit_code = 1;
} finally {
  report.cleanup = { started: stamp() };
  if (server?.listening) {
    try { server.closeAllConnections(); await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())); }
    catch (error) { report.cleanup.error = String(error); report.exit_code = 1; }
  }
  report.cleanup.server_listening = server?.listening ?? false; report.cleanup.completed = stamp();
  report.post_sources = report.source_hashes.map(entry => {
    try { return { path: entry.path, sha256: hash(readFileSync(path.join(root, entry.path))) }; }
    catch (error) { return { path: entry.path, error: String(error) }; }
  });
  report.post_trees = report.dependency_trees.map(entry => {
    try { return { source: entry.source, entries_sha256: hash(JSON.stringify(tree(path.join(root, entry.source)))) }; }
    catch (error) { return { source: entry.source, error: String(error) }; }
  });
  report.post_node_sha256 = hash(readFileSync(process.execPath));
  report.costs = { http_requests: report.cases.filter(c => c.executed).length, server_ingress_requests: report.ingress.length,
    child_processes: 0, model_calls: 0, remote_network_requests: 0 };
  report.completed = stamp(); event({ type: 'server-closed', cleanup: report.cleanup });
  report.events = { path: relative(eventsFile), sha256: hash(readFileSync(eventsFile)) };
  json(path.join(directory, 'report.json'), report);
  console.log(JSON.stringify({ report: relative(path.join(directory, 'report.json')), outcome: report.outcome,
    requests: report.costs.http_requests, server_listening: report.cleanup.server_listening, exit_code: report.exit_code }));
  process.exitCode = report.exit_code;
}
