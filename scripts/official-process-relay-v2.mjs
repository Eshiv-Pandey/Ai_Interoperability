// Harness I/O relay only; all MCP bytes reach the actual Python-spawned bridge.
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { createInterface } from 'node:readline';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { deadline, workspace, node22, relative, exclusiveJson, hash, stamp, logLifecycle } from './log-reference-http.mjs';

const input = createInterface({ input: process.stdin, terminal: false });
let bridge;
let started;
let startRejected;
let operation = 0;
const writes = new Map();
const emitControl = value => process.stdout.write(JSON.stringify(value) + '\n');
input.on('line', line => {
  try {
    const value = JSON.parse(line);
    if (value.type === 'bridge-started') {
      bridge.pid = value.pid; bridge.connected = true;
      started(value);
    } else if (value.type === 'bridge-start-error') startRejected(new Error(value.error));
    else if (value.type === 'bridge-stdout') bridge.stdout.emit('data', Buffer.from(value.base64, 'base64'));
    else if (value.type === 'bridge-stderr') bridge.stderr.emit('data', Buffer.from(value.base64, 'base64'));
    else if (value.type === 'bridge-stdin-written') {
      const callback = writes.get(value.operation_id); writes.delete(value.operation_id);
      callback?.(value.error ? new Error(value.error) : null);
    } else if (value.type === 'bridge-exit') {
      bridge.connected = false; bridge.emit('exit', value.code, value.signal ?? null);
    } else throw new Error('Unexpected supervisor packet: ' + value.type);
  } catch (error) { bridge?.emit('error', error); }
});
export function closeSupervisorInput() { input.close(); process.stdin.destroy(); }
export async function launchRelayedBridge(capture, base) {
  const amir = capture.report.route_id === 'amirk_a2a_to_mcp';
  const bridgeDir = path.join(workspace, 'external', amir ? 'a2a-to-mcp' : 'mcp-a2a');
  const args = [];
  const control = path.join(capture.runDir, 'bridge-close-control.json');
  const extra = { REFERENCE_HTTP_LOG: capture.nativeLog, REFERENCE_RUN_ID: capture.report.run_id,
    REFERENCE_ROUTE_ID: capture.report.route_id, REFERENCE_PORT_ORIGIN: base, REFERENCE_CLOSE_CONTROL: control };
  if (amir) {
    const config = path.join(capture.runDir, 'bridge-config.json');
    exclusiveJson(config, { agents: { carol: { url: base } }, host: '127.0.0.1' });
    args.push('--config', config, '--port', '0');
  } else {
    Object.assign(extra, { A2A_CONFIG: path.join(capture.runDir, 'absent-config.json'),
      A2A_STATE_DIR: path.join(capture.runDir, 'state'), A2A_DAEMON_URL: base, A2A_PEERS: base,
      A2A_ALLOW_WRITES: '1', A2A_CHANNEL: '0', A2A_MAX_RETRIES: '0' });
    capture.report.configuration.state_directory = relative(extra.A2A_STATE_DIR);
  }
  const preload = pathToFileURL(path.join(workspace, 'scripts/official-bridge-preload-v2.mjs')).href;
  const command = [node22, '--import', preload, path.join(bridgeDir, 'dist/cli.js'), ...args];
  const dynamic = { captured: stamp(), fixture_url: base, bridge_args: args,
    supplied_environment: extra, bridge_profile: capture.report.configuration, process_launcher: 'Python subprocess.Popen with real pipes' };
  const configLedger = path.join(capture.runDir, 'pre-bridge-runtime-config.json');
  exclusiveJson(configLedger, dynamic);
  capture.report.pre_bridge_runtime_config = { path: relative(configLedger), sha256: hash(JSON.stringify(dynamic, null, 2) + '\n'), captured: dynamic.captured };
  logLifecycle(capture, { type: 'runtime-config-frozen-before-bridge-spawn', ...capture.report.pre_bridge_runtime_config });
  bridge = new EventEmitter();
  bridge.stdout = new EventEmitter(); bridge.stderr = new EventEmitter(); bridge.connected = false;
  bridge.stdin = { write(bytes, callback) {
    const operation_id = ++operation;
    writes.set(operation_id, callback);
    emitControl({ type: 'write-bridge-stdin', operation_id, base64: Buffer.from(bytes).toString('base64') });
  }};
  bridge.send = () => emitControl({ type: 'close-bridge', pid: bridge.pid, control, run_id: capture.report.run_id });
  bridge.kill = () => emitControl({ type: 'kill-bridge', pid: bridge.pid });
  const tracked = { child: bridge, role: 'bridge', command, pid: null, exit: null };
  capture.diagnostics.children.bridge = { stdout: '', stderr: '', ipc: [] };
  bridge.stdout.on('data', bytes => { capture.diagnostics.children.bridge.stdout += bytes.toString('utf8'); });
  bridge.stderr.on('data', bytes => { capture.diagnostics.children.bridge.stderr += bytes.toString('utf8'); });
  tracked.exited = new Promise(resolve => bridge.once('exit', (code, signal) => {
    tracked.exit = { code, signal, observed: stamp() };
    logLifecycle(capture, { type: 'exit', role: 'bridge', pid: bridge.pid, ...tracked.exit });
    resolve(tracked.exit);
  }));
  const ready = new Promise((resolve, reject) => { started = resolve; startRejected = reject; });
  emitControl({ type: 'start-bridge', command, cwd: bridgeDir, environment: extra,
    run_dir: capture.runDir, run_id: capture.report.run_id, route_id: capture.report.route_id });
  const actual = await deadline(ready, 10000, 'Python supervisor bridge spawn');
  assert(Number.isInteger(actual.pid) && actual.pid > 0);
  tracked.pid = actual.pid; capture.children.push(tracked);
  capture.report.provenance.bridge_command = command; capture.report.provenance.bridge_pid = actual.pid;
  capture.report.supervisor = { pid: actual.supervisor_pid, source: 'scripts/supervise_official_bridge_v2.py',
    attempt: path.posix.dirname(capture.report.source_check_receipt.path),
    relay_log: relative(path.join(capture.runDir, 'supervisor-relay.jsonl')), stdout_stdin_policy: 'byte-preserving real process pipes; no PTY' };
  logLifecycle(capture, { type: 'spawn', role: 'bridge', pid: actual.pid, command, externally_observed: actual.started });
  return bridge;
}

