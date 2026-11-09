// Separate native A2A 1.0 preservation probe. No bridge or model execution.
// Outputs are exclusive; frozen sources/SDK hashes precede dynamic imports.
import assert from 'node:assert/strict';
import { fork, spawnSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { appendFileSync, copyFileSync, constants, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const driver = fileURLToPath(import.meta.url);
const workspace = path.dirname(path.dirname(driver));
const node22 = 'C:\\Program Files\\nodejs\\node.exe';
const portRelative = 'scripts/fixtures/carol-reference-v1.mjs';
const portSha256 = 'b6b6492ee5c27cf5db0474054b0f18a8feafe0859d9faaa4fd67946c7768626d';
const sdkRelative = 'external/a2a-to-mcp/node_modules/@a2a-js/sdk';
const evidenceRelative = 'docs/research/source-evidence/reference-continuation';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const relative = filename => path.relative(workspace, filename).replaceAll('\\', '/');
const stamp = () => ({ utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString() });
const errorText = error => error?.stack ?? String(error);
const exclusiveJson = (filename, value) => writeFileSync(filename, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function deadline(promise, ms, label) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`${label} exceeded ${ms}ms`)), ms); })]); }
  finally { clearTimeout(timer); }
}
function treeManifest(directory) {
  const entries = [];
  const visit = current => {
    for (const entry of readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const filename = path.join(current, entry.name);
      if (entry.isDirectory()) visit(filename);
      else if (entry.isFile()) {
        const bytes = readFileSync(filename);
        entries.push({ path: path.relative(directory, filename).replaceAll('\\', '/'), bytes: bytes.length, sha256: sha256(bytes) });
      } else throw new Error(`Unsupported installed artifact: ${filename}`);
    }
  };
  visit(directory);
  return { root: relative(directory), file_count: entries.length, entries, entries_sha256: sha256(JSON.stringify(entries)) };
}

async function serverChild() {
  // Parent already captured source/dependency hashes and exact copies.
  const { startCarolReferenceAgent } = await import(pathToFileURL(path.join(workspace, portRelative)).href);
  const agent = await startCarolReferenceAgent({ port: 0 });
  let closing = false;
  process.send({ type: 'ready', pid: process.pid, url: agent.url, card_url: agent.cardUrl, observed: stamp() });
  process.on('message', message => {
    if (message?.type !== 'close' || closing) return;
    closing = true;
    const started = stamp();
    void agent.close().then(() => {
      process.send({ type: 'closed', pid: process.pid, started, completed: stamp(), server_listening: agent.server.listening }, () => process.disconnect());
    }, error => {
      process.exitCode = 1;
      process.send({ type: 'close_failed', pid: process.pid, started, completed: stamp(), error: errorText(error) }, () => process.disconnect());
    });
  });
}

if (process.argv[2] === '--server-child') {
  try { await serverChild(); }
  catch (error) { console.error(errorText(error)); process.exitCode = 1; process.disconnect?.(); }
} else {
  const started = stamp();
  const runId = `carol-port-native-v1-${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}-${process.pid}`;
  const runsRoot = path.join(workspace, 'runs', 'reference-port-native');
  mkdirSync(runsRoot, { recursive: true });
  const runDirectory = path.join(runsRoot, runId);
  mkdirSync(runDirectory);
  const reportFile = path.join(runDirectory, 'report.json');
  const httpLog = path.join(runDirectory, 'native-http.jsonl');
  const lifecycleLog = path.join(runDirectory, 'process-lifecycle.jsonl');
  writeFileSync(httpLog, '', { flag: 'wx' });
  writeFileSync(lifecycleLog, '', { flag: 'wx' });
  const lifecycle = record => appendFileSync(lifecycleLog, JSON.stringify({ observed: stamp(), ...record }) + '\n');
  const report = {
    schema_version: 'carol-port-native-preservation/1', run_id: runId,
    kind: 'authored-A2A-1.0-port-development-native-only', started,
    command: process.argv, parent_pid: process.pid, model_calls: 0,
    protocol: { family: 'A2A', version: '1.0', binding: 'JSONRPC', transport: 'genuine Node loopback HTTP' },
    instrumentation: { description: 'Read-only fetchImpl passed to official card resolver and JSONRPC transport; original Request/body/headers forwarded unchanged; cloned response entity bytes are logged before returning original response.', overhead: 'Clone and synchronous file logging delay client delivery; no latency or efficiency claim.', bytes: 'Fetch-visible application entity bytes; excludes TCP framing and implicit HTTP headers.' },
    namespace: { task: 'Public native A2A task ID returned by official client response', context: 'Public native A2A context ID returned by official client response', authority: 'Unauthenticated loopback caller, no credentials', lease: null },
    bounds: { startup_ms: 10000, request_ms: 10000, initial_observation_ms: 5000, polling_interval_ms: 50, attempts_per_control: 1 },
    controls: [], sdk_calls: [], exchanges: [], outcome: 'setup-started', cleanup: {},
    claim_limit: 'Tested port control preservation only; no bridge compatibility, natural defect, efficacy, novelty or human gate approval.'
  };
  let child;
  let childExit;
  let childExitPromise;
  let diagnostics = { stdout: '', stderr: '', ipc: [] };
  let phase = 'setup';
  const call = async (method, input, operation) => {
    const entry = { call_id: `sdk-${report.sdk_calls.length + 1}`, phase, method, input, started: stamp(), exchange_start: report.exchanges.length };
    report.sdk_calls.push(entry);
    try { entry.result = await operation(); return entry.result; }
    catch (error) { entry.error = errorText(error); throw error; }
    finally { entry.completed = stamp(); entry.exchange_end = report.exchanges.length; }
  };
  try {
    assert.equal(process.execPath.toLowerCase(), node22.toLowerCase(), 'Use explicit pinned Node executable');
    assert.equal(process.version, 'v22.13.0');
    const args = process.argv.slice(2);
    assert.equal(args.length, 2, 'Usage: --spec <frozen-native-spec-path>');
    assert.equal(args[0], '--spec');
    const specification = path.resolve(workspace, args[1]);
    assert(specification.startsWith(path.resolve(workspace, 'docs', 'research') + path.sep));
    const mapFile = path.join(workspace, evidenceRelative, 'port', 'change-map.json');
    const map = JSON.parse(readFileSync(mapFile, 'utf8'));
    const port = path.join(workspace, portRelative);
    assert.equal(sha256(readFileSync(port)), portSha256, 'Port must match prospectively fixed source');
    assert.equal(map.port_sha256, portSha256);
    const lock = path.join(workspace, 'external', 'a2a-to-mcp', 'package-lock.json');
    assert.equal(sha256(readFileSync(lock)), map.sdk.dependency_lock_sha256);
    const sdkRoot = path.join(workspace, sdkRelative);
    const sdkPackage = JSON.parse(readFileSync(path.join(sdkRoot, 'package.json'), 'utf8'));
    assert.equal(sdkPackage.version, '1.1.0');
    const checkout = spawnSync('git', ['-C', path.join(workspace, 'external', 'a2a-to-mcp'), 'rev-parse', 'HEAD'], { encoding: 'utf8', windowsHide: true });
    assert.equal(checkout.status, 0, checkout.stderr);
    assert.equal(checkout.stdout.trim(), map.sdk.source_checkout_commit);
    const original = path.join(workspace, evidenceRelative, 'runtime', 'original-number-game');
    for (const [name, expected] of Object.entries(map.original_source_sha256)) assert.equal(sha256(readFileSync(path.join(original, name))), expected, `Original source preserved: ${name}`);
    const snapshotDirectory = path.join(runDirectory, 'pre-execution-snapshots');
    mkdirSync(snapshotDirectory);
    const inputs = [driver, port, specification, mapFile, path.join(workspace, evidenceRelative, 'port', 'ATTRIBUTION.md'), path.join(workspace, 'external', 'source-lock.json'), lock, path.join(sdkRoot, 'package.json'), path.join(workspace, evidenceRelative, 'runtime', 'original-source-manifest.json')];
    const sourceHashes = {};
    for (let i = 0; i < inputs.length; i++) {
      const filename = inputs[i];
      const bytes = readFileSync(filename);
      const snapshot = path.join(snapshotDirectory, `${String(i + 1).padStart(2, '0')}-${path.basename(filename)}`);
      copyFileSync(filename, snapshot, constants.COPYFILE_EXCL);
      sourceHashes[relative(filename)] = { sha256: sha256(bytes), bytes: bytes.length, snapshot: relative(snapshot) };
    }
    const sdkManifest = treeManifest(sdkRoot);
    const joseRoot = path.join(workspace, 'external', 'a2a-to-mcp', 'node_modules', 'jose');
    const josePackage = JSON.parse(readFileSync(path.join(joseRoot, 'package.json'), 'utf8'));
    const dependencyManifest = treeManifest(joseRoot);
    report.pre_execution = {
      captured: stamp(), source_hashes: sourceHashes, node: { executable: process.execPath, version: process.version, executable_sha256: sha256(readFileSync(process.execPath)), platform: process.platform, architecture: process.arch },
      specification: { path: relative(specification), sha256: sha256(readFileSync(specification)) },
      port: { path: portRelative, sha256: portSha256 },
      original_source: { commit: map.original_source_commit, checked_hashes: map.original_source_sha256, modified: false },
      sdk: { package: sdkPackage.name, version: sdkPackage.version, manifest: sdkManifest, checkout: checkout.stdout.trim(), dependency_lock_sha256: sha256(readFileSync(lock)) },
      additional_runtime_dependency: { package: josePackage.name, version: josePackage.version, manifest: dependencyManifest },
      setup_ms: Number(BigInt(stamp().monotonic_ns) - BigInt(started.monotonic_ns)) / 1e6
    };
    exclusiveJson(path.join(runDirectory, 'pre-execution-ledger.json'), report.pre_execution);
    lifecycle({ type: 'pre-execution-ledger-frozen', path: relative(path.join(runDirectory, 'pre-execution-ledger.json')), sha256: sha256(readFileSync(path.join(runDirectory, 'pre-execution-ledger.json'))) });

    // First SDK/port dynamic imports and service start occur only after ledger.
    const { Role, TaskState, taskStateToJSON } = await import(pathToFileURL(path.join(sdkRoot, 'dist', 'index.js')).href);
    const { ClientFactory, JsonRpcTransportFactory, DefaultAgentCardResolver } = await import(pathToFileURL(path.join(sdkRoot, 'dist', 'client', 'index.js')).href);
    const childStarted = stamp();
    child = fork(driver, ['--server-child'], { execPath: node22, execArgv: [], cwd: workspace, windowsHide: true, silent: true, env: { PATH: process.env.PATH, SystemRoot: process.env.SystemRoot, TEMP: process.env.TEMP, TMP: process.env.TMP } });
    report.server_process = { pid: child.pid, command: [node22, driver, '--server-child'], started: childStarted };
    lifecycle({ type: 'spawn', ...report.server_process });
    child.stdout.on('data', bytes => { diagnostics.stdout += bytes.toString('utf8'); });
    child.stderr.on('data', bytes => { diagnostics.stderr += bytes.toString('utf8'); });
    child.on('message', message => { diagnostics.ipc.push(message); lifecycle({ type: 'ipc', child_pid: child.pid, message }); });
    childExitPromise = new Promise(resolve => child.once('exit', (code, signal) => { childExit = { code, signal, observed: stamp() }; lifecycle({ type: 'exit', pid: child.pid, ...childExit }); resolve(childExit); }));
    const ready = await deadline(new Promise((resolve, reject) => {
      child.once('error', reject);
      child.once('exit', (code, signal) => reject(new Error(`Server exited before ready: ${code}/${signal}`)));
      child.on('message', message => { if (message.type === 'ready') resolve(message); });
    }), 10000, 'port startup');
    assert.equal(ready.pid, child.pid);
    report.server_process.ready = ready;
    const endpoint = new URL(ready.url);
    assert.equal(endpoint.hostname, '127.0.0.1');
    report.endpoint = ready.url;
    const originalFetch = globalThis.fetch;
    const observedFetch = async (input, init) => {
      const url = input instanceof Request ? input.url : String(input);
      assert.equal(new URL(url).origin, endpoint.origin, 'Native requests restricted to isolated loopback port');
      let requestBytes;
      const body = init?.body;
      if (body == null && input instanceof Request) requestBytes = Buffer.from(await input.clone().arrayBuffer());
      else if (body == null) requestBytes = Buffer.alloc(0);
      else if (typeof body === 'string' || body instanceof Uint8Array) requestBytes = Buffer.from(body);
      else throw new Error(`Unsupported exact request-body capture type: ${typeof body}`);
      const requestRaw = requestBytes.toString('utf8');
      const requestJson = requestRaw ? JSON.parse(requestRaw) : null;
      const exchange = { exchange_id: `http-${report.exchanges.length + 1}`, phase, request: { url, method: init?.method ?? (input instanceof Request ? input.method : 'GET'), headers: Object.fromEntries(new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined))), raw: requestRaw, base64: requestBytes.toString('base64'), bytes: requestBytes.length, sha256: sha256(requestBytes), json: requestJson, started: stamp() } };
      report.exchanges.push(exchange);
      appendFileSync(httpLog, JSON.stringify({ type: 'request-started', ...exchange }) + '\n');
      try {
        const response = await originalFetch(input, init);
        const responseBytes = Buffer.from(await response.clone().arrayBuffer());
        const responseRaw = responseBytes.toString('utf8');
        exchange.response = { status: response.status, headers: Object.fromEntries(response.headers), raw: responseRaw, base64: responseBytes.toString('base64'), bytes: responseBytes.length, sha256: sha256(responseBytes), json: JSON.parse(responseRaw), observed: stamp() };
        if (requestJson) assert.equal(exchange.response.json.id, requestJson.id, 'Actual JSONRPC request/reply IDs match');
        return response;
      } catch (error) { exchange.error = errorText(error); throw error; }
      finally { exchange.completed = stamp(); appendFileSync(httpLog, JSON.stringify({ type: 'exchange-completed', ...exchange }) + '\n'); }
    };
    const factory = new ClientFactory({ transports: [new JsonRpcTransportFactory({ fetchImpl: observedFetch })], preferredTransports: ['JSONRPC'], clientConfig: { polling: false }, cardResolver: new DefaultAgentCardResolver({ fetchImpl: observedFetch }) });
    phase = 'discovery';
    const client = await call('ClientFactory.createFromUrl', { url: ready.url }, () => deadline(factory.createFromUrl(ready.url), 10000, 'agent card request'));
    // Client itself is not a serializable receipt; save only actual profile.
    report.sdk_calls.at(-1).result = { protocolVersion: client.protocolVersion, protocolName: client.transport.protocolName };
    report.card = await client.getAgentCard();
    assert.equal(client.protocolVersion, '1.0');
    assert.equal(client.transport.protocolName, 'JSONRPC');
    assert.equal(report.card.capabilities.streaming, false);
    assert.equal(report.card.supportedInterfaces.length, 1);
    assert.equal(report.card.supportedInterfaces[0].protocolVersion, '1.0');
    const initialText = '{"action":"shuffle","history":[{"guess":25,"response":"Go higher"}]}';
    const answerText = 'Well done!';
    report.contract = { initial_text: initialText, answer_text: answerText, goal: 'Original task and context in TASK_STATE_COMPLETED after fixed answer', completed_artifact_required: false, history_setting: 'GetTask historyLength unset' };
    const message = (text, taskId = '', contextId = '', refs = []) => ({ messageId: randomUUID(), role: Role.ROLE_USER, taskId, contextId, parts: [{ content: { $case: 'text', value: text }, mediaType: 'text/plain', filename: '', metadata: undefined }], extensions: [], referenceTaskIds: refs, metadata: undefined });
    const send = input => call('SendMessage', input, () => client.sendMessage(input, { signal: AbortSignal.timeout(10000) }));
    const get = (id, requestLimit = 10000) => call('GetTask', { tenant: '', id, historyLength: undefined }, () => client.getTask({ tenant: '', id, historyLength: undefined }, { signal: AbortSignal.timeout(requestLimit) }));
    const stateName = task => taskStateToJSON(task.status?.state);
    const checkTask = task => { assert.equal(typeof task.id, 'string'); assert(task.id); assert.equal(typeof task.contextId, 'string'); assert(task.contextId); assert(task.status); };
    for (const controlId of ['P1', 'P2', 'P3']) {
      const control = { control_id: controlId, attempt: 1, started: stamp() };
      report.controls.push(control);
      phase = `${controlId}:initial-send`;
      control.initial_input = { tenant: '', message: message(initialText), configuration: { returnImmediately: false, acceptedOutputModes: ['text/plain'] }, metadata: undefined };
      control.initial_send = await send(control.initial_input);
      checkTask(control.initial_send);
      control.original_task_id = control.initial_send.id;
      control.original_context_id = control.initial_send.contextId;
      control.binding_source = { sdk_call_id: report.sdk_calls.at(-1).call_id, paths: ['result.id', 'result.contextId'], public: true };
      const until = Date.now() + 5000;
      control.initial_reads = [];
      do {
        phase = `${controlId}:initial-get`;
        const waiting = await get(control.original_task_id, Math.max(1, until - Date.now()));
        control.initial_reads.push(waiting);
        checkTask(waiting);
        assert.equal(waiting.id, control.original_task_id);
        assert.equal(waiting.contextId, control.original_context_id);
        if (waiting.status.state === TaskState.TASK_STATE_INPUT_REQUIRED) break;
        if (Date.now() >= until) throw new Error(`${controlId} never observed input-required within 5000ms`);
        await pause(50);
      } while (true);
      control.initial_required_receipt = control.initial_reads.at(-1);
      const artifactText = control.initial_required_receipt.artifacts.flatMap(artifact => artifact.parts).filter(part => part.content?.$case === 'text').map(part => part.content.value);
      assert.equal(artifactText.length, 1);
      assert.deepEqual(JSON.parse(artifactText[0]), [{ guess: 25, response: 'Go higher' }]);
      control.followup_input = { tenant: '', message: message(answerText, controlId === 'P3' ? '' : control.original_task_id, control.original_context_id, controlId === 'P1' ? [control.original_task_id] : []), configuration: { returnImmediately: false, acceptedOutputModes: ['text/plain'] }, metadata: undefined };
      phase = `${controlId}:followup-send`;
      try {
        control.followup_send = await send(control.followup_input);
        checkTask(control.followup_send);
      } catch (error) {
        if (controlId !== 'P3') throw error;
        control.followup_rejection = errorText(error);
      }
      phase = `${controlId}:original-get-after-answer`;
      control.original_after = await get(control.original_task_id);
      assert.equal(control.original_after.id, control.original_task_id);
      assert.equal(control.original_after.contextId, control.original_context_id);
      if (controlId !== 'P3') {
        assert.equal(control.followup_send.id, control.original_task_id);
        assert.equal(control.followup_send.contextId, control.original_context_id);
        const expected = controlId === 'P1' ? TaskState.TASK_STATE_COMPLETED : TaskState.TASK_STATE_INPUT_REQUIRED;
        assert.equal(control.followup_send.status.state, expected);
        assert.equal(control.original_after.status.state, expected);
      } else if (control.followup_send?.id !== undefined && control.followup_send.id !== control.original_task_id) {
        phase = `${controlId}:returned-task-get-after-answer`;
        control.returned_task_after = await get(control.followup_send.id);
        assert.equal(control.returned_task_after.id, control.followup_send.id);
        assert.equal(control.returned_task_after.contextId, control.followup_send.contextId);
      }
      control.observation = { original_state: stateName(control.original_after), returned_task_id: control.followup_send?.id ?? null, returned_context_id: control.followup_send?.contextId ?? null, returned_state: control.followup_send ? stateName(control.followup_send) : null, original_task_preserved_by_answer: control.followup_send ? control.followup_send.id === control.original_task_id : null, original_context_preserved_by_answer: control.followup_send ? control.followup_send.contextId === control.original_context_id : null, rejected: Boolean(control.followup_rejection) };
      control.outcome = 'recorded-with-prospective-checks-passed';
      control.completed = stamp();
    }
    report.outcome = 'passed';
  } catch (error) {
    report.outcome = 'failed'; report.error = errorText(error); report.failure_phase = phase; process.exitCode = 1;
  } finally {
    if (child) {
      report.cleanup = { pid: child.pid, requested: stamp(), mode: 'Specific child IPC invokes port server.closeAllConnections/server.close then disconnects; parent awaits normal process exit' };
      try {
        if (!childExit) {
          const closed = new Promise((resolve, reject) => child.on('message', message => {
            if (message.type === 'closed') resolve(message);
            if (message.type === 'close_failed') reject(new Error(message.error));
          }));
          child.send({ type: 'close' });
          report.cleanup.server_close = await deadline(closed, 5000, 'specific server.close');
        }
        report.cleanup.exit = await deadline(childExitPromise, 5000, 'specific child exit');
        assert.equal(report.cleanup.exit.code, 0, 'Server child normal exit after close');
        assert.equal(report.cleanup.exit.signal, null);
      } catch (error) {
        report.cleanup.error = errorText(error);
        // Last-resort termination targets only the recorded isolated child.
        if (!childExit) { report.cleanup.fallback_kill_requested = stamp(); child.kill(); try { report.cleanup.exit = await deadline(childExitPromise, 5000, 'fallback specific child exit'); } catch (exitError) { report.cleanup.exit_error = errorText(exitError); } }
        report.outcome = 'failed'; process.exitCode = 1;
      }
    } else report.cleanup = { started_child: false };
    report.completed = stamp();
    report.costs = { http_attempts: report.exchanges.length, card_requests: report.exchanges.filter(exchange => !exchange.request.json).length, rpc_requests: report.exchanges.filter(exchange => exchange.request.json).length, send_requests: report.exchanges.filter(exchange => exchange.request.json?.method === 'SendMessage').length, get_requests: report.exchanges.filter(exchange => exchange.request.json?.method === 'GetTask').length, request_bytes: report.exchanges.reduce((sum, exchange) => sum + exchange.request.bytes, 0), response_bytes: report.exchanges.reduce((sum, exchange) => sum + (exchange.response?.bytes ?? 0), 0), failed_requests: report.exchanges.filter(exchange => exchange.error || exchange.response?.json?.error).length, setup_ms: report.pre_execution?.setup_ms ?? null };
    exclusiveJson(path.join(runDirectory, 'process-diagnostics.json'), diagnostics);
    report.sidecars = { native_http: relative(httpLog), process_lifecycle: relative(lifecycleLog), diagnostics: relative(path.join(runDirectory, 'process-diagnostics.json')) };
    report.driver_post_sha256 = sha256(readFileSync(driver));
    report.port_post_sha256 = sha256(readFileSync(path.join(workspace, portRelative)));
    exclusiveJson(reportFile, report);
    console.log(JSON.stringify({ outcome: report.outcome, report: relative(reportFile), report_sha256: sha256(readFileSync(reportFile)), pid: child?.pid ?? null, controls: report.controls.map(control => ({ id: control.control_id, observation: control.observation, outcome: control.outcome })), costs: report.costs, cleanup: report.cleanup, error: report.error }));
  }
}
