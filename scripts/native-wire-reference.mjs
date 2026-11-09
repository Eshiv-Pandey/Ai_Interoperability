// Native A2A reference DEVELOPMENT smoke, using pinned SDK and upstream fixture.
// Records actual HTTP; no fabricated bridge defects, LLMs or hidden evaluator gold.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomUUID, createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const upstream = path.join(root, 'external', 'a2a-to-mcp');
const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--output')) {
  throw new Error('Usage: node scripts/native-wire-reference.mjs [--output new-file.json]');
}
const output = args.length ? path.resolve(args[1]) : path.join(root, 'runs', 'wire-native', `${Date.now()}-${process.pid}.json`);
if (existsSync(output)) throw new Error(`Refusing to overwrite existing evidence: ${output}`);
mkdirSync(path.dirname(output), { recursive: true });
const sdkPath = path.join(upstream, 'node_modules', '@a2a-js', 'sdk', 'dist');
const { Role, TaskState } = await import(pathToFileURL(path.join(sdkPath, 'index.js')));
const { ClientFactory, JsonRpcTransportFactory } = await import(pathToFileURL(path.join(sdkPath, 'client', 'index.js')));
const hashes = {};
for (const relative of ['package-lock.json', 'fixtures/agent/index.ts', 'fixtures/agent/executor.ts', 'fixtures/agent/card.ts']) {
  hashes[relative] = createHash('sha256').update(readFileSync(path.join(upstream, relative))).digest('hex');
}
const report = {
  kind: 'native-reference-development-wire-smoke', started_at: new Date().toISOString(),
  fixture_commit: '58eff9da469bccdc432bf164662727947de646b4', node: process.version,
  fixture_label: 'Upstream deterministic fixture; no application holdout or independent gold',
  sdk_version: JSON.parse(readFileSync(path.join(upstream, 'node_modules', '@a2a-js', 'sdk', 'package.json'))).version,
  source_sha256: hashes, model_calls: 0, command: process.argv,
  http_exchanges: [], fixture_stdout: '', fixture_stderr: '',
  claim_limit: 'Native reference startup and observed continuation only; no admission/novelty result',
};
const fixtureArgs = ['--import', 'tsx', 'fixtures/agent/cli.ts', '--port', '0'];
const fixture = spawn(process.execPath, fixtureArgs, {
  cwd: upstream, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
});
report.fixture_command = [process.execPath, ...fixtureArgs];
report.fixture_pid = fixture.pid;
fixture.stdout.on('data', data => { report.fixture_stdout += data.toString(); });
fixture.stderr.on('data', data => { report.fixture_stderr += data.toString(); });

async function deadline(promise, milliseconds, label) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label} timed out`)), milliseconds);
    })]);
  } finally { clearTimeout(timer); }
}

const nativeFetch = globalThis.fetch;
async function loggedFetch(input, init) {
  const url = String(input);
  assert.equal(new URL(url).hostname, '127.0.0.1', 'Reference smoke uses loopback only');
  const signal = init?.signal ? AbortSignal.any([init.signal, AbortSignal.timeout(10000)]) : AbortSignal.timeout(10000);
  const response = await nativeFetch(input, { ...init, signal });
  const raw = await response.clone().text();
  report.http_exchanges.push({
    recorded_at: new Date().toISOString(), url, method: init?.method ?? 'GET',
    request_headers: Object.fromEntries(new Headers(init?.headers)), request_body: init?.body ?? null,
    response_status: response.status, response_headers: Object.fromEntries(response.headers), response_body: raw,
  });
  return response;
}

function userMessage(text, task = undefined) {
  // SDK protobuf representation inspected in pinned src/a2a-client.ts.
  return { messageId: randomUUID(), role: Role.ROLE_USER, contextId: task?.contextId ?? '',
    taskId: task?.id ?? '', parts: [{ content: { $case: 'text', value: text }, mediaType: 'text/plain', filename: '' }],
    extensions: [], referenceTaskIds: [] };
}

try {
  const url = await deadline(new Promise((resolve, reject) => {
    fixture.once('error', reject);
    fixture.once('exit', code => reject(new Error(`Fixture exited before startup: ${code}`)));
    fixture.stdout.on('data', () => {
      const match = report.fixture_stdout.match(/listening on (http:\/\/[^\s]+)/);
      if (match) resolve(match[1]);
    });
  }), 10000, 'fixture startup');
  report.fixture_url = url;
  const card = await (await loggedFetch(`${url}/.well-known/agent-card.json`)).json();
  report.card = card;
  const factory = new ClientFactory({
    transports: [new JsonRpcTransportFactory({ fetchImpl: loggedFetch })], preferredTransports: ['JSONRPC'],
  });
  const client = await factory.createFromAgentCard(card);
  const send = (text, task) => deadline(client.sendMessage({ tenant: '', message: userMessage(text, task) }), 10000, 'native send');
  const get = id => deadline(client.getTask({ tenant: '', id, historyLength: 0 }), 10000, 'native get');
  async function observe(id, wanted) {
    const end = Date.now() + 5000;
    let snapshot;
    do {
      snapshot = await get(id);
      if (snapshot.status?.state === wanted) return snapshot;
      await new Promise(resolve => setTimeout(resolve, 50));
    } while (Date.now() < end);
    throw new Error(`Native task did not reach ${wanted}: ${JSON.stringify(snapshot)}`);
  }
  const terminal = await send('task: native-reference');
  report.send_result = terminal;
  assert(terminal.id, 'Expected native Task response');
  const reread = await observe(terminal.id, TaskState.TASK_STATE_COMPLETED);
  report.get_result = reread;
  assert.equal(reread.id, terminal.id);
  assert(JSON.stringify(reread.artifacts).includes('ecnerefer-evitan'));
  const request = await send('ask: approval');
  const pending = await observe(request.id, TaskState.TASK_STATE_INPUT_REQUIRED);
  report.input_required_result = pending;
  const answer = await send('yes', pending);
  report.resume_acknowledgement = answer;
  assert.equal(answer.id, pending.id);
  const completed = await observe(pending.id, TaskState.TASK_STATE_COMPLETED);
  report.resumed_get_result = completed;
  assert.equal(completed.contextId, pending.contextId);
  assert(JSON.stringify(completed.artifacts).includes('approval = yes'));
  const parked = await send('ask: native-cancel');
  await observe(parked.id, TaskState.TASK_STATE_INPUT_REQUIRED);
  const cancelled = await deadline(client.cancelTask({ tenant: '', id: parked.id }), 10000, 'native cancel');
  report.cancel_result = cancelled;
  assert.equal(cancelled.id, parked.id);
  assert.equal(cancelled.status.state, TaskState.TASK_STATE_CANCELED);
  report.outcome = 'passed'; report.exit_code = 0;
} catch (error) {
  report.outcome = 'failed'; report.exit_code = 1;
  report.error = error.stack ?? String(error);
  process.exitCode = 1;
} finally {
  fixture.kill();
  try {
    await deadline(new Promise(resolve => fixture.exitCode !== null ? resolve() : fixture.once('exit', resolve)), 5000, 'fixture cleanup');
    report.fixture_exit_code = fixture.exitCode; report.fixture_exit_signal = fixture.signalCode;
    report.cleanup = 'child exited';
  } catch (error) {
    report.cleanup = String(error); process.exitCode = 1;
  }
  report.finished_at = new Date().toISOString();
  writeFileSync(output, JSON.stringify(report, null, 2) + '\n', { encoding: 'utf8', flag: 'wx' });
  console.log(JSON.stringify({ outcome: report.outcome, exit_code: process.exitCode ?? 0, output, error: report.error }));
}
