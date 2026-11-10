// Bounded public MCP initiation client for the unchanged original AP2 card.
// No tool result is converted into a fabricated SDK Task or inverse mapping.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, fsyncSync, openSync, readFileSync, writeSync, writeFileSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

const hash = raw => createHash('sha256').update(raw).digest('hex');
const entity = raw => ({ bytes: raw.length, sha256: hash(raw), base64: raw.toString('base64') });
const errorText = error => String(error?.stack ?? error).slice(0, 3000);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);

export function mapOutgoing(route, packet, peer, alias) {
  assert(packet.jsonrpc === '2.0' && packet.method === 'message/send' && object(packet.params));
  const message = packet.params.message;
  assert(object(message) && Array.isArray(message.parts));
  const texts = message.parts.filter(part => part.kind === 'text').map(part => part.text);
  assert(texts.length === 1 && texts[0] === 'Initiate a payment' && !message.taskId,
    'This source-bound study maps initiation only');
  if (route === 'amir_typed') {
    // The original public schema exposes opaque handles, not A2A raw IDs.
    // This fresh bridge has returned no handle. Do not invent one from contextId.
    return { name: 'a2a_send_message', arguments: { agent: alias, text: texts[0] } };
  }
  if (route === 'mg_typed') {
    return { name: 'a2a_send_message', arguments: { url: peer, text: texts[0],
      ...(message.contextId ? { context_id: message.contextId } : {}) } };
  }
  assert(route === 'mg_raw', 'Unknown legal outgoing bridge route');
  // Arbitrary params are legal in the original raw tool. Its method enum is
  // modern; do not send message/send outside that enum or add header arguments.
  return { name: 'a2a_request', arguments: { url: peer, method: 'SendMessage', params: structuredClone(packet.params) } };
}

export function validate(config) {
  assert(config.schema_version === 'ap2-native-bridge-client/12');
  assert(['amir_typed', 'mg_typed', 'mg_raw'].includes(config.route));
  assert(process.version === config.node_version && config.node_version === 'v22.23.2');
  assert(path.isAbsolute(config.output) && path.isAbsolute(config.sender_wire));
  assert(config.bridge.command === process.execPath && path.isAbsolute(config.bridge.cwd));
  assert(Array.isArray(config.bridge.args) && config.bridge.args.every(value => typeof value === 'string'));
  assert(object(config.bridge.env) && Object.values(config.bridge.env).every(value => typeof value === 'string'));
  const peer = new URL(config.peer);
  assert(peer.protocol === 'http:' && peer.hostname === '127.0.0.1' && peer.port === '8001'
    && peer.pathname === '/' && !peer.username && !peer.password && !peer.search && !peer.hash);
  const endpoint = new URL(config.mcp_endpoint);
  assert(endpoint.protocol === 'http:' && endpoint.hostname === '127.0.0.1' && endpoint.pathname === '/mcp'
    && Number(endpoint.port) === config.bridge_port && !endpoint.username && !endpoint.password && !endpoint.search && !endpoint.hash);
  for (const [key, upper] of Object.entries({ request_ms: 15000, total_ms: 60000, max_bytes: 8388608 })) {
    assert(Number.isInteger(config.limits[key]) && config.limits[key] > 0 && config.limits[key] <= upper);
  }
  return config;
}

function journal(output) {
  const fd = openSync(path.join(output, 'events.jsonl'), 'wx');
  let sequence = 0;
  return { emit(kind, value = {}) {
    const record = { seq: ++sequence, kind, utc: new Date().toISOString(), ...value };
    writeSync(fd, JSON.stringify(record) + '\n');
    fsyncSync(fd);
    return record;
  }, close() { closeSync(fd); }, get sequence() { return sequence; } };
}

function decodeHttp(bytes, contentType) {
  if (!contentType.includes('text/event-stream')) return bytes.length ? [{ parsed: JSON.parse(bytes), raw: entity(bytes), framing: 'http-body' }] : [];
  const raw = bytes.toString('utf8');
  assert(/\r?\n\r?\n$/.test(raw), 'MCP SSE response has no complete closing frame');
  return raw.split(/\r?\n\r?\n/).flatMap(frame => {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n');
    return data ? [{ parsed: JSON.parse(data), raw: entity(Buffer.from(data)), framing: 'sse-data-derived' }] : [];
  });
}

async function rebind(port) {
  const server = net.createServer();
  return new Promise(resolve => {
    server.once('error', () => resolve(false));
    server.listen(port, '127.0.0.1', () => server.close(error => resolve(!error)));
  });
}

export async function execute(config, log) {
  const amir = config.route === 'amir_typed';
  const deadline = Date.now() + config.limits.total_ms;
  const remaining = () => { const value = deadline - Date.now(); assert(value > 0, 'MCP client total deadline'); return value; };
  const rawSource = readFileSync(config.sender_wire);
  const packet = JSON.parse(rawSource);
  const mapped = mapOutgoing(config.route, packet, config.peer, config.alias);
  const mapping = { schema_version: 'ap2-original-outgoing-map/12', route: config.route,
    original_sender_entity: entity(rawSource), original_sender_packet: packet,
    actual_legal_mcp_call: mapped, original_bridge_source_pin: config.bridge_pin,
    incoming_or_inverse_mapping_invented: false, header_argument_added: false,
    original_card_rewritten: false, raw_legacy_method_outside_enum_sent: false,
    typed_data_parts_not_representable: config.route !== 'mg_raw',
    source_context_handle_invented: false };
  writeFileSync(path.join(config.output, 'outgoing-mapping.json'), JSON.stringify(mapping, null, 2) + '\n', { flag: 'wx' });
  const child = spawn(config.bridge.command, config.bridge.args, { cwd: config.bridge.cwd,
    env: config.bridge.env, shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  assert(Number.isInteger(child.pid), 'Original bridge child did not start');
  log.emit('child-start', { pid: child.pid, command: config.bridge.command, args: config.bridge.args,
    cwd: config.bridge.cwd, original_bridge_cli: true, credential_free_explicit_environment: true });
  let childError, exitRecord, buffer = Buffer.alloc(0), stdoutText = '', stdoutBytes = 0, stderrBytes = 0;
  let operation = 0;
  const pending = new Map(), operations = new Map();
  const exited = new Promise(resolve => child.once('close', (code, signal) => {
    exitRecord = { pid: child.pid, code, signal, utc: new Date().toISOString() };
    log.emit('child-exit', exitRecord);
    for (const receiver of pending.values()) receiver.reject(new Error('Original bridge exited'));
    pending.clear(); resolve(exitRecord);
  }));
  child.on('error', error => { childError = error; log.emit('child-error', { error: errorText(error) });
    for (const receiver of pending.values()) receiver.reject(error); pending.clear(); });
  child.stderr.on('data', bytes => {
    stderrBytes += bytes.length;
    if (stderrBytes > config.limits.max_bytes) { childError = new Error('Bridge stderr byte bound'); child.kill('SIGKILL'); return; }
    log.emit('stdio-chunk', { direction: 'bridge_stderr', raw: entity(bytes) });
  });
  child.stdout.on('data', bytes => {
    stdoutBytes += bytes.length;
    if (stdoutBytes > config.limits.max_bytes) { childError = new Error('Bridge stdout byte bound'); child.kill('SIGKILL'); return; }
    log.emit('stdio-chunk', { direction: 'bridge_to_client', raw: entity(bytes) });
    if (amir) { stdoutText += bytes.toString('utf8'); return; }
    buffer = Buffer.concat([buffer, bytes]);
    for (;;) {
      const end = buffer.indexOf(10); if (end < 0) break;
      const line = buffer.subarray(0, end + 1); buffer = buffer.subarray(end + 1);
      try {
        const parsed = JSON.parse(line.toString());
        const associated = operations.get(parsed.id);
        const observed = log.emit('mcp-message', { direction: 'bridge_to_client', framing: 'stdio-line',
          operation_id: associated?.id ?? null, phase: associated?.phase ?? null, raw: entity(line), parsed });
        const receiver = pending.get(parsed.id);
        if (receiver) { pending.delete(parsed.id); receiver.resolve({ json: parsed, seq: observed.seq }); }
      } catch (error) {
        childError = error; log.emit('parse-error', { error: errorText(error), raw: entity(line) });
        for (const receiver of pending.values()) receiver.reject(error); pending.clear();
      }
    }
  });
  async function rpc(phase, method, params = {}, notify = false) {
    if (childError) throw childError;
    assert(!exitRecord, 'Original bridge is no longer running');
    const id = ++operation;
    operations.set(id, { id, phase });
    const value = { jsonrpc: '2.0', ...(notify ? {} : { id }), method,
      ...(notify && params === undefined ? {} : { params: amir ? { _meta: {
        'io.modelcontextprotocol/protocolVersion': '2026-07-28',
        'io.modelcontextprotocol/clientCapabilities': {},
        'io.modelcontextprotocol/clientInfo': { name: 'AP2-public-native-study', version: '8.0.0' } }, ...params } : params }) };
    const timeout = Math.min(config.limits.request_ms, remaining());
    const raw = Buffer.from(JSON.stringify(value));
    log.emit('operation-start', { operation_id: id, phase, method, notification: notify });
    if (amir) {
      const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream',
        'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method };
      if (method === 'tools/call') headers['Mcp-Name'] = params.name;
      const request = log.emit('http-request', { operation_id: id, phase, method: 'POST', url: config.mcp_endpoint, headers, raw: entity(raw) });
      log.emit('mcp-message', { direction: 'client_to_bridge', framing: 'http-body', operation_id: id, phase,
        source_http_seq: request.seq, raw: entity(raw), parsed: value });
      const response = await fetch(config.mcp_endpoint, { method: 'POST', headers, body: raw,
        redirect: 'error', signal: AbortSignal.timeout(timeout) });
      const chunks = []; let count = 0;
      const reader = response.body?.getReader();
      if (reader) for (;;) {
        const next = await reader.read(); if (next.done) break;
        count += next.value.length; assert(count <= config.limits.max_bytes, 'MCP HTTP body byte bound');
        chunks.push(Buffer.from(next.value));
      }
      const bytes = Buffer.concat(chunks), contentType = response.headers.get('content-type') ?? '';
      const event = log.emit('http-response', { operation_id: id, phase, status: response.status, content_type: contentType,
        raw: entity(bytes), complete: true });
      const messages = decodeHttp(bytes, contentType);
      let matched;
      for (const message of messages) {
        const observed = log.emit('mcp-message', { direction: 'bridge_to_client', operation_id: id, phase,
          source_http_seq: event.seq, ...message });
        if (message.parsed.id === id) matched = { json: message.parsed, seq: observed.seq };
      }
      assert(response.ok && (notify || matched), 'MCP HTTP response did not return this operation');
      log.emit('operation-complete', { operation_id: id, phase });
      return matched ?? { json: null, seq: event.seq };
    }
    const reply = notify ? null : new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    log.emit('mcp-message', { direction: 'client_to_bridge', framing: 'stdio-line', operation_id: id, phase,
      raw: entity(Buffer.concat([raw, Buffer.from('\n')])), parsed: value });
    await new Promise((resolve, reject) => child.stdin.write(Buffer.concat([raw, Buffer.from('\n')]), error => error ? reject(error) : resolve()));
    if (notify) return { json: null, seq: log.sequence };
    let timer;
    try {
      const observed = await Promise.race([reply, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('MCP stdio operation deadline')), timeout); })]);
      log.emit('operation-complete', { operation_id: id, phase }); return observed;
    } finally { clearTimeout(timer); pending.delete(id); }
  }
  const result = { schema_version: 'ap2-native-bridge-initiation/12', route: config.route,
    provider_requests: 0, phase_results: [], errors: [], actual_legal_initiation_attempted: false,
    inverse_task_response_constructed: false, continuation_attempted: false,
    source_bank_task_qualification_established: false, whole_route_non_support_inference_allowed: false };
  try {
    if (amir) {
      const startupDeadline = Date.now() + Math.min(10000, remaining());
      while (!stdoutText.includes('a2a-to-mcp listening on')) {
        if (childError) throw childError; assert(!exitRecord && Date.now() < startupDeadline, 'Original bridge startup bound');
        await sleep(20);
      }
      result.phase_results.push({ phase: 'protocol_discovery', ...(await rpc('protocol_discovery', 'server/discover')) });
    } else {
      result.phase_results.push({ phase: 'initialize', ...(await rpc('initialize', 'initialize', {
        protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'AP2-public-native-study', version: '8.0.0' } })) });
      await rpc('initialized', 'notifications/initialized', undefined, true);
    }
    const tools = await rpc('tools', 'tools/list');
    result.phase_results.push({ phase: 'tools', ...tools });
    assert(Array.isArray(tools.json?.result?.tools), 'Original public tool schema unavailable');
    const exposed = tools.json.result.tools.find(tool => tool.name === mapped.name);
    assert(exposed, 'Mapped original tool not exposed');
    if (config.route === 'mg_raw') {
      const methods = exposed.inputSchema?.properties?.method?.enum;
      assert(Array.isArray(methods) && methods.includes('SendMessage') && methods.includes('GetTask')
        && !methods.includes('message/send') && !methods.includes('tasks/get'), 'Original legal raw method enum changed');
    }
    const discover = amir ? { name: 'a2a_discover', arguments: { agent: config.alias } }
      : { name: 'a2a_discover_agent', arguments: { url: config.peer } };
    result.phase_results.push({ phase: 'original_card_discovery', ...(await rpc('original_card_discovery', 'tools/call', discover)) });
    result.actual_legal_initiation_attempted = true;
    result.phase_results.push({ phase: 'legal_initiation', ...(await rpc('legal_initiation', 'tools/call', mapped)) });
    result.status = 'actual_mcp_initiation_reply_captured';
  } catch (error) {
    result.errors.push(errorText(error)); result.status = 'actual_failed_or_partial_bridge_attempt_retained';
    log.emit('client-error', { error: errorText(error) });
  } finally {
    child.stdin.end();
    if (!exitRecord) child.kill('SIGTERM');
    const graceful = await Promise.race([exited.then(() => true), sleep(3000).then(() => false)]);
    let forced = false;
    if (!graceful) { forced = true; child.kill('SIGKILL'); await Promise.race([exited, sleep(3000)]); }
    const endpointRebound = amir && exitRecord ? await rebind(config.bridge_port) : null;
    result.cleanup = { child_pid: child.pid, child_exit_observed: Boolean(exitRecord), actual_exit: exitRecord ?? null,
      graceful_exit_observed: graceful, forced_kill: forced, mcp_endpoint_rebind_verified: endpointRebound,
      strict_cleanup_passed: Boolean(exitRecord) && (amir ? endpointRebound === true : true) };
    log.emit('cleanup-complete', result.cleanup);
    result.transcript_events = log.sequence;
  }
  return result;
}

export async function main(argv = process.argv.slice(2)) {
  assert(argv.length === 2 && argv[0] === '--config', 'Use --config with the public allocated configuration');
  const config = validate(JSON.parse(readFileSync(argv[1])));
  const log = journal(config.output);
  try {
    const result = await execute(config, log);
    writeFileSync(path.join(config.output, 'result.json'), JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
    process.stdout.write(JSON.stringify({ status: result.status, route: result.route,
      strict_cleanup_passed: result.cleanup.strict_cleanup_passed }) + '\n');
    return result.cleanup.strict_cleanup_passed ? 0 : 2;
  } finally { log.close(); }
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  main().then(code => { process.exitCode = code; }).catch(error => { process.stderr.write(errorText(error) + '\n'); process.exitCode = 3; });
}
