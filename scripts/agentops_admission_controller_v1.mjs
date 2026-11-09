// Opt-in admission around the preserved public episode. Importing sends no requests.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstatSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeTool, findRawConfirmation, runPublicEpisode } from './agentops_bridge_client_v1.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const clone = value => JSON.parse(JSON.stringify(value));
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const stateOf = value => typeof value === 'string'
  ? value.replace(/^TASK_STATE_/, '').replaceAll('-', '_').toLowerCase() : null;
const phases = { discover_full_tools: 'tools', discover_agent: 'discovery', initial_typed_send: 'initial',
  pending_origin_get: 'pending', public_raw_get: 'raw' };
const codepointOrder = (a, b) => {
  const aa = [...a], bb = [...b];
  for (let index = 0; index < Math.min(aa.length, bb.length); index++) {
    const difference = aa[index].codePointAt(0) - bb[index].codePointAt(0);
    if (difference) return difference;
  }
  return aa.length - bb.length;
};

export function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (object(value)) return '{' + Object.keys(value).sort(codepointOrder)
    .map(key => JSON.stringify(key) + ':' + canonicalJson(value[key])).join(',') + '}';
  assert(value === null || ['string', 'boolean', 'number'].includes(typeof value), 'Non-JSON admission data');
  assert(typeof value !== 'number' || Number.isFinite(value), 'Nonfinite admission data');
  return JSON.stringify(value);
}
export const snapshotDigest = value => createHash('sha256').update(canonicalJson(value), 'utf8').digest('hex');
function freeze(value) {
  if (object(value) || Array.isArray(value)) { for (const item of Object.values(value)) freeze(item); Object.freeze(value); }
  return value;
}
function writeNew(file, value) { writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' }); }
function boundedInteger(value, name, maximum) {
  assert(Number.isSafeInteger(value) && value > 0 && value <= maximum, `Invalid ${name}`); return value;
}

// This default performs both candidate evaluation and its independent check in
// the Python CLI. Injection is for a trusted alternative runner or unit tests.
export function createPythonAdmissionRunner(options) {
  assert(path.isAbsolute(options.output_dir), 'Admission output_dir must be absolute and new');
  const timeout = boundedInteger(options.timeout_ms ?? 30000, 'admission timeout', 30000);
  const budget = boundedInteger(options.budget ?? 100000, 'admission budget', 10000000);
  const maxBytes = boundedInteger(options.max_output_bytes ?? 2097152, 'admission output bound', 8388608);
  let used = false;
  return async (snapshot, now) => {
    assert(!used, 'Admission runner is single-use'); used = true;
    mkdirSync(options.output_dir, { recursive: false });
    const input = path.join(options.output_dir, 'snapshot.json');
    const output = path.join(options.output_dir, 'result.json');
    writeNew(input, snapshot);
    const executable = options.python ?? 'python';
    const args = ['-B', '-m', 'interoperability.pending_admission', '--input', input, '--output', output,
      '--now', String(now), '--budget', String(budget)];
    const record = { schema_version: 'agentops-admission-subprocess/1', executable, args,
      cwd: ROOT, started_at_utc: new Date().toISOString(), timeout_ms: timeout,
      budget, snapshot_sha256: snapshotDigest(snapshot), timed_out: false, output_limit_reached: false };
    writeNew(path.join(options.output_dir, 'execution.json'), record);
    const stdout = [], stderr = []; let bytes = 0;
    await new Promise(resolve => {
      let child, timer;
      try {
        child = spawn(executable, args, { cwd: ROOT, env: { ...process.env,
          PYTHONPATH: path.join(ROOT, 'src') }, shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
      } catch (error) { record.error = String(error); resolve(); return; }
      const collect = destination => chunk => {
        bytes += chunk.length;
        if (bytes <= maxBytes) destination.push(chunk);
        else { record.output_limit_reached = true; child.kill('SIGKILL'); }
      };
      child.stdout.on('data', collect(stdout)); child.stderr.on('data', collect(stderr));
      child.on('error', error => { record.error = String(error); });
      timer = setTimeout(() => { record.timed_out = true; child.kill('SIGKILL'); }, timeout);
      child.once('close', (code, signal) => { clearTimeout(timer); record.returncode = code; record.signal = signal; resolve(); });
    });
    record.finished_at_utc = new Date().toISOString();
    writeFileSync(path.join(options.output_dir, 'stdout.bin'), Buffer.concat(stdout), { flag: 'wx' });
    writeFileSync(path.join(options.output_dir, 'stderr.bin'), Buffer.concat(stderr), { flag: 'wx' });
    writeNew(path.join(options.output_dir, 'process.json'), record);
    assert(record.returncode === 0 && !record.timed_out && !record.output_limit_reached && !record.error,
      `Admission subprocess failed: ${record.error ?? record.returncode}${record.timed_out ? ' timeout' : ''}`);
    const resultFile = lstatSync(output);
    assert(resultFile.isFile() && resultFile.size <= maxBytes, 'Admission result file exceeds output bound or is not a file');
    const result = JSON.parse(readFileSync(output, 'utf8'));
    return { ...result, receipt_path: output };
  };
}

function publicSignature(observations) {
  const initial = decodeTool(observations.initial), pending = decodeTool(observations.pending);
  const discovery = decodeTool(observations.discovery), raw = decodeTool(observations.raw);
  assert(!initial.error && !pending.error && !discovery.error && !raw.error, 'Public observation error');
  const task = initial.value.task;
  assert(typeof task?.id === 'string' && typeof task?.context_id === 'string', 'Missing initial association');
  assert(pending.value.id === task.id && pending.value.context_id === task.context_id, 'Changed typed association');
  assert(stateOf(pending.value.state) === 'input_required', 'Original task is no longer input_required');
  const call = findRawConfirmation(raw, { task_id: task.id, context_id: task.context_id });
  assert(call, 'No current public confirmation');
  return canonicalJson({ tools: observations.tools.body.tools,
    discovery: { url: discovery.value.url, interfaces: discovery.value.card?.interfaces ?? null },
    task_id: task.id, context_id: task.context_id, pending_state: stateOf(pending.value.state),
    raw_task: raw.value.result });
}

export function createAdmissionController(config, transport, emit = () => ({}), options = {}) {
  assert(['B5', 'B6', 'B7'].includes(config.arm), 'Admission wrapper supports only raw B5/B6/B7 episodes');
  const clock = options.clock ?? (() => Math.floor(Date.now() / 1000));
  const now = () => { const value = clock(); assert(Number.isSafeInteger(value) && value >= 0, 'Explicit clock must be an integer'); return value; };
  const deployment = clone(options.deployment ?? config.admission?.deployment ?? {
    origin: config.agent_base_url, header_mode: 'unknown', serializer: 'unknown', service_contract: 'unknown' });
  const route = () => ({ route: { arm: config.arm, agent_base_url: config.agent_base_url },
    deployment: options.deployment ?? config.admission?.deployment ?? deployment });
  const initialRoute = canonicalJson(route());
  const ttl = boundedInteger(options.observation_ttl_seconds ?? 15, 'observation TTL', 15);
  const runnerTimeout = boundedInteger(options.timeout_ms ?? 30000, 'admission timeout', 30000);
  const runner = options.admit ?? createPythonAdmissionRunner({ ...config.admission, ...options });
  const observations = {};
  const audit = { schema_version: 'agentops-admission-controller/1', status: 'not_reached',
    initial_forwarded_attempts: 0,
    continuation_requests_intercepted: 0, continuation_forwarded_attempts: 0,
    continuation_forwarded_replies: 0, admissions: [], blocks: [], rechecks: [],
    atomic_server_state_lock: false, claimed_live_effect: false };
  let busy = false, consumed = false, initialConsumed = false;
  const observe = (name, request, reply) => {
    assert(Number.isSafeInteger(reply?.seq) && object(reply.body), 'Missing public reply');
    return { seq: reply.seq, body: clone(reply.body), observed_at: now(), request: clone(request) };
  };
  const block = reason => {
    audit.status = 'blocked'; const item = { reason, at: now() }; audit.blocks.push(item);
    emit('admission-blocked', item); throw new Error('Admission blocked: ' + reason);
  };
  const guardedAdmission = async (phase, method, params, notify) => {
    audit.continuation_requests_intercepted++;
    if (phase !== 'raw_answer' || method !== 'tools/call' || params?.name !== 'a2a_request'
        || params.arguments?.method !== 'SendMessage' || notify) return block('unpermitted continuation route');
    if (busy || consumed) return block('continuation already reserved or consumed');
    busy = true;
    try {
      if (canonicalJson(route()) !== initialRoute) return block('configured route changed');
      if (!Object.keys(phases).every(phaseName => observations[phases[phaseName]])) return block('missing public observations');
      const started = now();
      const snapshot = freeze({ schema_version: 'agentops-pending-admission/1',
        id: options.id ?? `agentops-${config.arm}-${observations.raw.seq}-${started}`,
        route: clone(route().route), deployment, observations: clone(observations),
        rationale: config.rationale, proposed_call: { method, params: clone(params) },
        valid_until: observations.raw.observed_at + ttl });
      const signature = publicSignature(snapshot.observations);
      let timer, admission;
      try {
        admission = await Promise.race([Promise.resolve().then(() => runner(snapshot, started)),
          new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('admission runner timeout')), runnerTimeout); })]);
      } finally { clearTimeout(timer); }
      admission = freeze(clone(admission));
      audit.admissions.push(clone(admission)); emit('admission-result', clone(admission));
      if (admission?.schema_version !== 'pending-admission-result/1' || admission.status !== 'recorded'
          || admission.decision !== 'supported' || admission.certificate_valid !== true
          || admission.dispatch_permitted !== true) return block('decision or independent certificate does not permit dispatch');
      if (admission.snapshot_sha256 !== snapshotDigest(snapshot)) return block('admission belongs to a different snapshot');
      if (canonicalJson(admission.request) !== canonicalJson(snapshot.proposed_call)) return block('witness request differs from public proposal');
      if (canonicalJson(route()) !== initialRoute || config.rationale !== snapshot.rationale) return block('configured route or rationale changed during admission');
      if (now() > snapshot.valid_until) return block('admission observation expired');
      const refreshed = clone(snapshot.observations);
      for (const name of ['tools', 'discovery', 'pending', 'raw']) {
        if (now() > snapshot.valid_until) return block('admission expired before public recheck');
        const request = snapshot.observations[name].request;
        const reply = await transport.rpc('admission_recheck_' + name, request.method, clone(request.params), false);
        refreshed[name] = observe(name, request, reply);
      }
      audit.rechecks.push(clone(refreshed));
      if (publicSignature(refreshed) !== signature) return block('public route, pending state or binding changed after admission');
      if (now() > snapshot.valid_until || canonicalJson(route()) !== initialRoute
          || config.rationale !== snapshot.rationale) return block('admission expired or route/rationale changed during recheck');
      consumed = true; audit.status = 'dispatch_reserved';
      const request = clone(admission.request);
      emit('admission-dispatch', { snapshot_sha256: admission.snapshot_sha256, request: clone(request), at: now(),
        scope: 'Intent immediately before transport invocation; not proof of bytes written or application effect' });
      if (now() > snapshot.valid_until || canonicalJson(route()) !== initialRoute
          || config.rationale !== snapshot.rationale) return block('admission expired or configuration changed before forwarding');
      audit.status = 'dispatched'; audit.continuation_forwarded_attempts++;
      const reply = await transport.rpc(phase, request.method, request.params, false);
      audit.continuation_forwarded_replies++;
      return reply;
    } catch (error) {
      if (!String(error.message).startsWith('Admission blocked:') && audit.continuation_forwarded_attempts === 0) {
        audit.status = 'blocked'; audit.blocks.push({ reason: String(error), at: now() });
        emit('admission-blocked', audit.blocks.at(-1));
      }
      throw error;
    } finally { busy = false; }
  };
  return { audit, transport: {
    pause: ms => transport.pause(ms),
    async rpc(phase, method, params = {}, notify = false) {
      if (phase === 'raw_answer') {
        return guardedAdmission(phase, method, params, notify);
      }
      if (notify || canonicalJson(route()) !== initialRoute) return block('unpermitted notification or changed route');
      let expected;
      if (phase === 'discover_full_tools') expected = { method: 'tools/list', params: {} };
      if (phase === 'discover_agent') expected = { method: 'tools/call', params: {
        name: 'a2a_discover_agent', arguments: { url: config.agent_base_url } } };
      if (phase === 'initial_typed_send') {
        if (initialConsumed) return block('initial send already consumed');
        expected = { method: 'tools/call', params: { name: 'a2a_send_message', arguments: {
          url: config.agent_base_url, text: 'Restart inventory.' } } };
      }
      if (['pending_origin_get', 'final_origin_get', 'public_raw_get'].includes(phase)) {
        if (!observations.initial) return block('read requested before public initial association');
        const taskId = decodeTool(observations.initial).value.task?.id;
        if (typeof taskId !== 'string' || !taskId) return block('read lacks public task binding');
        expected = phase === 'public_raw_get'
          ? { method: 'tools/call', params: { name: 'a2a_request', arguments: {
            url: config.agent_base_url, method: 'GetTask', params: { id: taskId, historyLength: 100 } } } }
          : { method: 'tools/call', params: { name: 'a2a_get_task', arguments: {
            task_id: taskId, history_length: 100, refresh: true } } };
      }
      if (!expected || canonicalJson({ method, params }) !== canonicalJson(expected)) return block('unpermitted public RPC');
      if (phase === 'initial_typed_send') { initialConsumed = true; audit.initial_forwarded_attempts++; }
      const request = { method, params: clone(params) };
      const reply = await transport.rpc(phase, method, params, notify);
      if (phases[phase]) observations[phases[phase]] = observe(phases[phase], request, reply);
      return reply;
    },
  } };
}

export async function runAdmittedEpisode(config, transport, emit = () => ({}), options = {}) {
  const controller = createAdmissionController(config, transport, emit, options);
  let result;
  try { result = await runPublicEpisode(config, controller.transport, emit); }
  catch (error) { result = { arm: config.arm, status: 'client_failed', errors: [{ error: String(error) }],
    strict_success: null, strict_success_requires_external_effect_check: true }; }
  if (controller.audit.status === 'not_reached') controller.audit.reason = 'No public raw continuation proposal was produced';
  return { ...result, legacy_answer_sent: result.answer_sent ?? false,
    legacy_answer_attempts: result.answer_attempts ?? 0,
    answer_sent: controller.audit.continuation_forwarded_attempts === 0 ? false
      : controller.audit.continuation_forwarded_replies > 0 ? true : null,
    answer_sent_basis: controller.audit.continuation_forwarded_attempts === 0 ? 'No transport invocation'
      : controller.audit.continuation_forwarded_replies > 0 ? 'Public transport reply observed'
        : 'Transport invoked but send unverified after failure',
    answer_attempts: controller.audit.continuation_forwarded_attempts,
    answer_replies: controller.audit.continuation_forwarded_replies,
    admission: clone(controller.audit) };
}
