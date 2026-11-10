// Source-bound process guards, not a hostile-code operating-system sandbox.
// The original bridge source, arguments, card, request headers and payloads are
// unchanged. The guard refuses reads/writes/networking outside the owned study.
import fs from 'node:fs';
import net from 'node:net';
import tls from 'node:tls';
import dns from 'node:dns';
import dgram from 'node:dgram';
import childProcess from 'node:child_process';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { syncBuiltinESMExports } from 'node:module';

export const loopbackHost = value => ['127.0.0.1', '::1', 'localhost'].includes(String(value).toLowerCase());
export const inside = (value, root) => value === root || value.startsWith(root + path.sep);

export function socketEndpoint(args, listening = false) {
  let first = args[0];
  if (Array.isArray(first)) first = first[0];
  if (first && typeof first === 'object') {
    return { host: String(first.host ?? first.hostname ?? (listening ? '' : 'localhost')),
      port: Number(first.port), path: first.path ?? null };
  }
  return { port: Number(first), host: typeof args[1] === 'string' ? args[1] : (listening ? '' : 'localhost'), path: null };
}

export function installGuard(config) {
  const state = path.resolve(config.stateRoot), runtime = path.resolve(config.runtimeRoot);
  const readFiles = new Set(config.readFiles.map(value => path.resolve(value)));
  const ports = new Set(config.peerPorts), listenPorts = new Set(config.listenPorts);
  const originalAppend = fs.appendFileSync.bind(fs);
  let sequence = 0, childStarted = false, fetchSequence = 0;
  const emit = value => originalAppend(config.log, JSON.stringify({ seq: ++sequence, pid: process.pid,
    role: config.role, utc: new Date().toISOString(), ...value }) + '\n', { encoding: 'utf8', flag: 'a' });
  const refuse = (kind, reason) => { emit({ kind: 'denial', operation: kind, reason });
    const error = new Error('AP2 owned process guard: ' + reason); error.code = 'AP2_SCOPE_DENIED'; throw error; };
  const filename = value => {
    if (typeof value === 'number') return null;
    if (value instanceof URL) return value.protocol === 'file:' ? path.resolve(fileURLToPath(value)) : refuse('filesystem', 'non_file_url');
    if (Buffer.isBuffer(value)) return path.resolve(value.toString());
    return typeof value === 'string' ? path.resolve(value) : refuse('filesystem', 'unknown_path_type');
  };
  const read = value => {
    const resolved = filename(value); if (resolved === null) return;
    const base = path.basename(resolved).toLowerCase();
    if (base === '.env' || base.includes('evaluator') || base.includes('qualification-private')
        || base.startsWith('gemini-api-key') || base.endsWith('.pem')) refuse('read', 'private_evaluator_or_saved_credential');
    if (!inside(resolved, state) && !inside(resolved, runtime) && !readFiles.has(resolved)) refuse('read', 'outside_owned_public_inputs');
  };
  const write = value => { const resolved = filename(value); if (resolved !== null && !inside(resolved, state)) refuse('write', 'outside_owned_bridge_state'); };
  const checkOpen = (value, flags) => typeof flags === 'string' && /[wa+]/.test(flags)
    || typeof flags === 'number' && (flags & (3 | fs.constants.O_CREAT | fs.constants.O_TRUNC | fs.constants.O_APPEND)) !== 0 ? write(value) : read(value);
  const wrap = (object, name, check) => { const original = object[name]; if (typeof original !== 'function') return;
    object[name] = function (...args) { check(args); return Reflect.apply(original, this, args); }; };
  for (const name of ['readFileSync', 'readFile', 'createReadStream']) wrap(fs, name, args => read(args[0]));
  for (const name of ['writeFileSync', 'writeFile', 'appendFileSync', 'appendFile', 'mkdirSync', 'mkdir',
    'unlinkSync', 'unlink', 'rmSync', 'rm', 'rmdirSync', 'rmdir', 'createWriteStream']) wrap(fs, name, args => write(args[0]));
  for (const name of ['renameSync', 'rename']) wrap(fs, name, args => { write(args[0]); write(args[1]); });
  for (const name of ['copyFileSync', 'copyFile']) wrap(fs, name, args => { read(args[0]); write(args[1]); });
  wrap(fs, 'openSync', args => checkOpen(args[0], args[1])); wrap(fs, 'open', args => checkOpen(args[0], args[1]));
  for (const name of ['readFile']) wrap(fs.promises, name, args => read(args[0]));
  for (const name of ['writeFile', 'appendFile', 'mkdir', 'unlink', 'rm', 'rmdir']) wrap(fs.promises, name, args => write(args[0]));
  wrap(fs.promises, 'rename', args => { write(args[0]); write(args[1]); });
  wrap(fs.promises, 'copyFile', args => { read(args[0]); write(args[1]); });
  wrap(fs.promises, 'open', args => checkOpen(args[0], args[1]));
  wrap(net.Socket.prototype, 'connect', args => {
    const endpoint = socketEndpoint(args);
    if (endpoint.path || !loopbackHost(endpoint.host) || !ports.has(endpoint.port)) refuse('connect', 'not_an_owned_peer_or_mcp_loopback_endpoint');
  });
  wrap(net.Server.prototype, 'listen', args => {
    const endpoint = socketEndpoint(args, true);
    if (endpoint.path || endpoint.host !== '127.0.0.1' || !listenPorts.has(endpoint.port)) refuse('listen', 'not_the_owned_bridge_loopback_listener');
  });
  wrap(tls, 'connect', () => refuse('tls', 'no_owned_tls_endpoint'));
  wrap(dgram.Socket.prototype, 'send', () => refuse('datagram', 'no_owned_datagram_endpoint'));
  wrap(dns, 'lookup', args => { if (!loopbackHost(args[0])) refuse('dns', 'non_loopback_name'); });
  wrap(dns.promises, 'lookup', args => { if (!loopbackHost(args[0])) refuse('dns', 'non_loopback_name'); });
  for (const name of ['resolve', 'resolve4', 'resolve6', 'resolveAny', 'reverse']) {
    wrap(dns, name, () => refuse('dns', 'no_dns_queries_allowed'));
    wrap(dns.promises, name, () => refuse('dns', 'no_dns_queries_allowed'));
  }
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async function (input, init) {
    const value = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
    if (value.protocol !== 'http:' || !loopbackHost(value.hostname) || !ports.has(Number(value.port))
        || value.username || value.password) refuse('fetch', 'not_owned_loopback_http');
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    if (headers.has('authorization') || headers.has('x-goog-api-key')) refuse('fetch', 'credential_header_forbidden');
    let body = init?.body;
    if (body === undefined && input instanceof Request) body = new Uint8Array(await input.clone().arrayBuffer());
    if (body === undefined || body === null) body = Buffer.alloc(0);
    else if (typeof body === 'string') body = Buffer.from(body);
    else if (body instanceof Uint8Array || body instanceof ArrayBuffer) body = Buffer.from(body);
    else refuse('fetch_observation', 'unrecordable_request_body');
    if (body.length > 8388608) refuse('fetch_observation', 'request_entity_byte_bound');
    const entity = raw => ({ bytes: raw.length, sha256: createHash('sha256').update(raw).digest('hex'), base64: raw.toString('base64') });
    const id = ++fetchSequence;
    emit({ kind: 'fetch-attempt', fetch_id: id, url: value.href, method: init?.method ?? (input instanceof Request ? input.method : 'GET'),
      request_headers: [...headers.entries()], request_entity: entity(body), original_fetch_arguments_rewritten: false });
    try {
      const response = await originalFetch.call(this, input, init);
      const bytes = Buffer.from(await response.clone().arrayBuffer());
      if (bytes.length > 8388608) refuse('fetch_observation', 'response_entity_byte_bound');
      emit({ kind: 'fetch-response', fetch_id: id, url: value.href, status: response.status, response_entity: entity(bytes),
        original_response_replaced: false, observation: 'clone_consumed_for_public_HTTP_entity_capture' });
      return response;
    } catch (error) { emit({ kind: 'fetch-error', fetch_id: id, reason: String(error).slice(0, 1000) }); throw error; }
  };
  const originalSpawn = childProcess.spawn;
  childProcess.spawn = function (command, args, options) {
    if (config.role !== 'client' || childStarted || command !== process.execPath
        || !Array.isArray(args) || JSON.stringify(args) !== JSON.stringify(config.childArgs)
        || options?.shell !== false || options?.env?.AP2_GUARD_ROLE !== 'bridge') refuse('spawn', 'unallocated_descendant_process');
    childStarted = true;
    const child = originalSpawn.call(this, command, args, options);
    emit({ kind: 'allocated_bridge_child', child_pid: child.pid ?? null });
    return child;
  };
  for (const name of ['exec', 'execFile', 'execSync', 'execFileSync', 'spawnSync', 'fork']) wrap(childProcess, name, () => refuse('spawn', 'unallocated_descendant_process'));
  syncBuiltinESMExports();
  emit({ kind: 'guard_installed', version: process.version, source_guard_scope: 'source_bound_guard_not_OS_sandbox',
    request_payloads_cards_headers_or_tool_arguments_rewritten: false,
    owned_HTTP_fetch_request_and_cloned_response_observation: true });
  // Both probes are blocked synchronously before any network/file read.
  try { dns.lookup('ap2-scope-probe.invalid', () => {}); } catch (error) {
    if (error.code !== 'AP2_SCOPE_DENIED') throw error; emit({ kind: 'external_network_probe_blocked' });
  }
  try { fs.readFileSync(path.join(state, 'evaluator.json')); } catch (error) {
    if (error.code !== 'AP2_SCOPE_DENIED') throw error; emit({ kind: 'private_evaluator_probe_blocked' });
  }
  return { emit };
}

if (process.env.AP2_NATIVE_GUARD === '1') {
  installGuard({ role: process.env.AP2_GUARD_ROLE, stateRoot: process.env.AP2_GUARD_STATE,
    runtimeRoot: process.env.AP2_GUARD_RUNTIME, log: process.env.AP2_GUARD_LOG,
    readFiles: JSON.parse(process.env.AP2_GUARD_READ_FILES), peerPorts: JSON.parse(process.env.AP2_GUARD_PEER_PORTS),
    listenPorts: JSON.parse(process.env.AP2_GUARD_LISTEN_PORTS), childArgs: JSON.parse(process.env.AP2_GUARD_CHILD_ARGS) });
}
