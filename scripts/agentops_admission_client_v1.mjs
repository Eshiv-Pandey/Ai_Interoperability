// Fresh-allocation stdio client. Importing never spawns a bridge or sends a request.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, mkdirSync, openSync, readFileSync, writeFileSync, writeSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';
import { SCHEMA as PUBLIC_SCHEMA, validateConfig } from './agentops_bridge_client_v1.mjs';
import { runAdmittedEpisode } from './agentops_admission_controller_v1.mjs';

export const SCHEMA = 'agentops-admitted-client-config/1';
const entity = bytes => ({ base64: bytes.toString('base64'), bytes: bytes.length,
  sha256: createHash('sha256').update(bytes).digest('hex') });
const errorText = error => String(error?.stack ?? error);
const writeNew = (file, value) => writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });

export function validateAdmittedConfig(config) {
  assert(config?.schema_version === SCHEMA, 'Expected admitted client config');
  validateConfig({ ...config, schema_version: PUBLIC_SCHEMA });
  assert(['B5', 'B6', 'B7'].includes(config.arm), 'Only raw stdio bridge arms are supported');
  const admission = config.admission;
  assert(admission && typeof admission === 'object' && !Array.isArray(admission), 'Explicit admission configuration required');
  assert(typeof admission.python === 'string' && admission.python.length, 'Explicit Python executable required');
  assert(admission.deployment && typeof admission.deployment === 'object', 'Explicit deployment declaration required');
  assert(['version-header', 'passthrough', 'unknown'].includes(admission.deployment.header_mode), 'Unknown header mode');
  assert(Number.isSafeInteger(admission.budget) && admission.budget > 0 && admission.budget <= 10000000, 'Invalid work budget');
  assert(Number.isSafeInteger(admission.timeout_ms) && admission.timeout_ms > 0 && admission.timeout_ms <= 30000, 'Invalid admission timeout');
  // Receipts are always inside this new client allocation, never a supplied prior path.
  assert(!Object.hasOwn(admission, 'output_dir'), 'admission output_dir is allocated by the client');
  return config;
}

function journalAt(directory) {
  const descriptor = openSync(path.join(directory, 'mcp.jsonl'), 'wx'); let seq = 0;
  return { emit(kind, value = {}) {
    const event = { schema_version: 'agentops-admitted-client-event/1', seq: ++seq,
      at_utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString(), kind, ...value };
    writeSync(descriptor, JSON.stringify(event) + '\n'); return event;
  }, close() { closeSync(descriptor); } };
}

export async function executeAdmittedClient(config, journal) {
  validateAdmittedConfig(config);
  const deadline = Date.now() + config.limits.total_timeout_ms;
  const remaining = () => { const value = deadline - Date.now(); assert(value > 0, 'Client total deadline reached'); return value; };
  const child = spawn(config.bridge.command, config.bridge.args, { cwd: config.bridge.cwd, env: config.bridge.env,
    shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  const lifecycle = { pid: child.pid ?? null, command: config.bridge.command, args: config.bridge.args,
    cwd: config.bridge.cwd, started_at_utc: new Date().toISOString(), clean_exit: false };
  journal.emit('child-start', lifecycle);
  let childError, exitRecord, buffer = Buffer.alloc(0), bytesSeen = 0, operation = 0, continuationWrites = 0;
  const pending = new Map(), operations = new Map();
  const rejectPending = error => { for (const receiver of pending.values()) receiver.reject(error); pending.clear(); };
  const exited = new Promise(resolve => child.once('close', (code, signal) => {
    exitRecord = { code, signal, at_utc: new Date().toISOString() }; journal.emit('child-exit', exitRecord);
    rejectPending(new Error(`Bridge exited: ${code}/${signal}`)); resolve(exitRecord);
  }));
  child.on('error', error => { childError = error; journal.emit('child-error', { error: errorText(error) }); rejectPending(error); });
  child.stdin.on('error', error => { childError = error; journal.emit('stdin-error', { error: errorText(error) }); rejectPending(error); });
  const capture = (direction, bytes) => {
    bytesSeen += bytes.length;
    if (bytesSeen > config.limits.max_response_bytes) {
      childError = new Error('Bridge stdout/stderr byte limit'); rejectPending(childError);
      if (!lifecycle.output_limit_reached) {
        lifecycle.output_limit_reached = true; lifecycle.forced_kill = true; lifecycle.sigkill_sent = child.kill('SIGKILL');
        journal.emit('output-limit', { observed_bytes: bytesSeen, bound: config.limits.max_response_bytes });
      }
      return false;
    }
    journal.emit('stdio-chunk', { direction, raw: entity(bytes) }); return true;
  };
  child.stderr.on('data', bytes => capture('bridge_stderr', bytes));
  child.stdout.on('data', bytes => {
    if (!capture('bridge_to_client', bytes)) return;
    buffer = Buffer.concat([buffer, bytes]);
    for (;;) {
      const newline = buffer.indexOf(10); if (newline < 0) break;
      const line = buffer.subarray(0, newline + 1); buffer = buffer.subarray(newline + 1);
      try {
        const parsed = JSON.parse(line.toString('utf8')), associated = operations.get(parsed.id);
        const event = journal.emit('mcp-message', { direction: 'bridge_to_client', framing: 'stdio-line',
          operation_id: associated?.id ?? null, phase: associated?.phase ?? null, raw: entity(line), parsed });
        if (pending.has(parsed.id)) {
          const receiver = pending.get(parsed.id); pending.delete(parsed.id);
          receiver.resolve({ body: parsed.result, json: parsed, seq: event.seq });
        }
      } catch (error) { childError = error; journal.emit('mcp-parse-error', { error: errorText(error), raw: entity(line) }); rejectPending(error); }
    }
  });
  const transport = {
    pause: async ms => { await sleep(Math.min(ms, remaining())); },
    async rpc(phase, method, params = {}, notify = false) {
      if (childError) throw childError; assert(!exitRecord, 'Bridge is no longer running');
      const id = ++operation; operations.set(id, { id, phase });
      const json = { jsonrpc: '2.0', ...(notify ? {} : { id }), method,
        ...(notify && params === undefined ? {} : { params }) };
      const bytes = Buffer.from(JSON.stringify(json) + '\n');
      const timeout = Math.min(config.limits.request_timeout_ms, remaining());
      journal.emit('operation-start', { operation_id: id, phase, method, notification: notify });
      let timer;
      const response = notify ? Promise.resolve({ body: null, json: null, seq: null })
        : new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
      response.catch(() => {});
      const timed = new Promise((_, reject) => { timer = setTimeout(() => {
        pending.delete(id); reject(new Error('MCP request timeout: ' + phase));
      }, timeout); });
      const sent = journal.emit('mcp-message', { direction: 'client_to_bridge', framing: 'stdio-line',
        operation_id: id, phase, raw: entity(bytes), parsed: json });
      try {
        await Promise.race([new Promise((resolve, reject) => child.stdin.write(bytes, error => error ? reject(error) : resolve())), timed]);
        if (phase === 'raw_answer') continuationWrites++;
        journal.emit('stdio-written', { operation_id: id, source_seq: sent.seq, bytes: bytes.length });
        const reply = await Promise.race([response, timed]);
        if (!notify) assert(reply.json?.jsonrpc === '2.0' && reply.json.id === id && !reply.json.error, 'MCP error or mismatched response');
        journal.emit('operation-complete', { operation_id: id, phase, reply_seq: reply.seq }); return reply;
      } catch (error) { journal.emit('operation-error', { operation_id: id, phase, error: errorText(error) }); throw error; }
      finally { clearTimeout(timer); pending.delete(id); }
    },
  };
  let result;
  try {
    const initialized = await transport.rpc('initialize', 'initialize', { protocolVersion: '2025-11-25',
      capabilities: {}, clientInfo: { name: 'AgentOps-admitted-control', version: '1.0.0' } });
    assert(initialized.body?.protocolVersion === '2025-11-25', 'Unexpected MCP negotiated revision');
    await transport.rpc('initialized', 'notifications/initialized', undefined, true);
    result = await runAdmittedEpisode(config, transport, journal.emit, { ...config.admission,
      output_dir: path.join(config.output_dir, 'admission') });
  } catch (error) {
    result = { arm: config.arm, status: 'client_failed', error: errorText(error), strict_success: null,
      strict_success_requires_external_effect_check: true };
  } finally {
    lifecycle.cleanup_started_at_utc = new Date().toISOString();
    if (!exitRecord) {
      lifecycle.stdin_end_sent = true; child.stdin.end();
      let timer;
      try { await Promise.race([exited, new Promise(resolve => { timer = setTimeout(resolve, 2000); })]); }
      finally { clearTimeout(timer); }
    }
    for (const [signal, grace] of [['SIGTERM', 12000], ['SIGKILL', 5000]]) {
      if (exitRecord) break;
      lifecycle[signal === 'SIGTERM' ? 'sigterm_sent' : 'forced_kill'] = child.kill(signal);
      let timer;
      try { await Promise.race([exited, new Promise(resolve => { timer = setTimeout(resolve, grace); })]); }
      finally { clearTimeout(timer); }
    }
    lifecycle.exit = exitRecord ?? null;
    lifecycle.clean_exit = !lifecycle.forced_kill && exitRecord?.code === 0 && !exitRecord?.signal;
    lifecycle.finished_at_utc = new Date().toISOString();
    if (buffer.length) journal.emit('stdio-trailing-bytes', { direction: 'bridge_to_client', raw: entity(buffer) });
    journal.emit('child-cleanup', lifecycle);
  }
  return { ...result, answer_sent: continuationWrites > 0 ? true : result.answer_attempts > 0 ? null : false,
    answer_sent_basis: 'Completed raw_answer stdin-write callback; delivery and application effect remain separate',
    continuation_stdin_write_completions: continuationWrites, child: lifecycle, configured_limits: config.limits,
    source_scope: 'Current public MCP observations plus explicitly declared deployment and conditional fixture contract; no historical run inputs',
    live_effect_verified_by_client: false };
}

export async function main(argv = process.argv.slice(2)) {
  if (argv.length === 1 && argv[0] === '--help') {
    process.stdout.write('Usage: node scripts/agentops_admission_client_v1.mjs --config NEW_CONFIG.json\n'); return;
  }
  assert(argv.length === 2 && argv[0] === '--config', 'Use --config <new allocation JSON>');
  const bytes = readFileSync(path.resolve(argv[1])), config = validateAdmittedConfig(JSON.parse(bytes));
  mkdirSync(config.output_dir, { recursive: false });
  writeFileSync(path.join(config.output_dir, 'config.json'), bytes, { flag: 'wx' });
  const journal = journalAt(config.output_dir); let result;
  try { result = await executeAdmittedClient(config, journal); }
  catch (error) { result = { arm: config.arm, status: 'client_failed', error: errorText(error), strict_success: null }; }
  finally { journal.close(); }
  result.schema_version = 'agentops-admitted-client-result/1'; result.finished_at_utc = new Date().toISOString();
  writeNew(path.join(config.output_dir, 'result.json'), result);
  process.stdout.write(JSON.stringify({ arm: config.arm, status: result.status,
    admission: result.admission?.status ?? null, forwarded_attempts: result.answer_attempts ?? 0,
    clean_exit: result.child?.clean_exit ?? false }) + '\n');
  process.exitCode = result.status === 'client_failed' || !result.child?.clean_exit ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { process.stderr.write(errorText(error) + '\n'); process.exitCode = 1; });
}
