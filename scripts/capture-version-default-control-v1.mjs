// SOFTWARE/SDK function control only; execute after frozen-contract verification.
// No application executor, server, HTTP request, child process or model call.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { appendFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { inspect } from 'node:util';

const driver = fileURLToPath(import.meta.url);
const workspace = path.dirname(path.dirname(driver));
const node22 = 'C:\\Program Files\\nodejs\\node.exe';
const sdkRoot = path.join(workspace, 'external', 'a2a-to-mcp', 'node_modules', '@a2a-js', 'sdk');
const sdkServer = path.join(sdkRoot, 'dist', 'server', 'index.js');
const serverHash = '57ab549afa0e2cb2bef0de37f88f1ea0192c918b360322232bbd6d30263cd643';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const relative = filename => path.relative(workspace, filename).replaceAll('\\', '/');
const stamp = () => ({ utc: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString() });
const errorText = error => error?.stack ?? String(error);
const exclusiveJson = (filename, value) => writeFileSync(filename, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
const describeReturn = value => ({ type: typeof value, representation: inspect(value, { depth: null, maxArrayLength: null, maxStringLength: null, breakLength: Infinity, compact: true, getters: false }) });
function treeManifest(directory) {
  const entries = [];
  const visit = current => {
    for (const entry of readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const filename = path.join(current, entry.name);
      if (entry.isDirectory()) visit(filename);
      else if (entry.isFile()) { const bytes = readFileSync(filename); entries.push({ path: path.relative(directory, filename).replaceAll('\\', '/'), bytes: bytes.length, sha256: hash(bytes) }); }
      else throw new Error(`Unsupported installed artifact: ${filename}`);
    }
  };
  visit(directory);
  return { root: relative(directory), entries, entries_sha256: hash(JSON.stringify(entries)), file_count: entries.length };
}
const args = process.argv.slice(2);
let specification; const extraSnapshots = [];
for (let index = 0; index < args.length; index += 2) {
  const flag = args[index]; const value = args[index + 1];
  if (!value) throw new Error(`Missing value for ${flag}`);
  if (flag === '--spec') specification = path.resolve(workspace, value);
  else if (flag === '--snapshot') extraSnapshots.push(path.resolve(workspace, value));
  else throw new Error(`Unknown argument ${flag}`);
}
if (!specification) throw new Error('Usage: --spec frozen-spec [--snapshot checker-file ...]');

const runId = `sdk-version-default-v1-${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}-${process.pid}`;
const runsRoot = path.join(workspace, 'runs', 'version-default-control');
mkdirSync(runsRoot, { recursive: true });
const runDir = path.join(runsRoot, runId); mkdirSync(runDir);
const eventLog = path.join(runDir, 'function-events.jsonl'); writeFileSync(eventLog, '', { flag: 'wx' });
const event = value => appendFileSync(eventLog, JSON.stringify({ observed: stamp(), ...value }) + '\n');
const card = {
  name: 'SDK function version control only', description: 'Constructed1.0-only software card; no application or network endpoint', version: 'software-control-v1',
  supportedInterfaces: [{ url: 'https://version-control.invalid/a2a', protocolBinding: 'JSONRPC', protocolVersion: '1.0', tenant: '' }],
  capabilities: { streaming: false, pushNotifications: false, extensions: [], extendedAgentCard: false },
  defaultInputModes: ['text/plain'], defaultOutputModes: ['text/plain'], skills: [], securitySchemes: {}, securityRequirements: [], signatures: []
};
const plan = [
  { case_id: 'D1', requested_version_property_present: false, headers: {}, expected_effective_version: '0.3', expected_acceptance: false },
  { case_id: 'D2', requested_version_property_present: true, requested_version: '', headers: { 'a2a-version': '' }, expected_effective_version: '0.3', expected_acceptance: false },
  { case_id: 'D3', requested_version_property_present: true, requested_version: '1.0', headers: { 'a2a-version': '1.0' }, expected_effective_version: '1.0', expected_acceptance: true },
  { case_id: 'D4', requested_version_property_present: true, requested_version: '0.3', headers: { 'a2a-version': '0.3' }, expected_effective_version: '0.3', expected_acceptance: false }
];
const report = {
  schema_version: 'sdk-version-default-function-control/1', run_id: runId, kind: 'SOFTWARE/SDK CONTROL', started: stamp(), pid: process.pid, command: process.argv,
  applications_executed: false, servers_started: 0, child_processes_started: 0, network_requests: 0, model_calls: 0,
  input_boundary: 'Direct complete builder options objects and clearly constructed JSONRPC1.0-only card, not HTTP header/query parsing or wire exchange',
  card, case_plan: plan, cases: [], function_calls: [], outcome: 'setup-started', exit_code: null,
  claim_limit: 'Installed SDK function behavior on four local inputs only; not application/bridge observation, wire conformance, natural defect, efficacy, efficiency, novelty or human approval.'
};
try {
  assert.equal(process.execPath.toLowerCase(), node22.toLowerCase()); assert.equal(process.version, 'v22.13.0');
  assert(specification.startsWith(path.join(workspace, 'docs', 'research') + path.sep));
  assert.equal(hash(readFileSync(sdkServer)), serverHash);
  const pkg = JSON.parse(readFileSync(path.join(sdkRoot, 'package.json'), 'utf8')); assert.equal(pkg.version, '1.1.0');
  const sourceLockFile = path.join(workspace, 'external', 'source-lock.json');
  const sourceLock = JSON.parse(readFileSync(sourceLockFile, 'utf8'));
  const lock = path.join(workspace, 'external', 'a2a-to-mcp', 'package-lock.json');
  assert.equal(hash(readFileSync(lock)), sourceLock.sources.find(source => source.id === 'amirk_a2a_to_mcp').dependency_lock.sha256);
  const snapshotRoot = path.join(runDir, 'pre-execution-snapshots'); mkdirSync(snapshotRoot);
  const files = [driver, specification, path.join(workspace, 'docs', 'research', 'port-version-default-audit-v1.md'), sourceLockFile, lock, ...extraSnapshots];
  const sources = {};
  for (const [index, filename] of [...new Set(files)].entries()) {
    assert(filename.startsWith(workspace + path.sep));
    const bytes = readFileSync(filename); const snapshot = path.join(snapshotRoot, `${String(index + 1).padStart(2, '0')}-${path.basename(filename)}`);
    writeFileSync(snapshot, bytes, { flag: 'wx' });
    sources[relative(filename)] = { bytes: bytes.length, sha256: hash(bytes), snapshot: relative(snapshot) };
  }
  const sdkManifest = treeManifest(sdkRoot);
  const sdkSnapshot = path.join(snapshotRoot, 'installed-sdk'); mkdirSync(sdkSnapshot);
  for (const entry of sdkManifest.entries) {
    const target = path.join(sdkSnapshot, entry.path); mkdirSync(path.dirname(target), { recursive: true });
    const bytes = readFileSync(path.join(sdkRoot, entry.path));
    assert.equal(bytes.length, entry.bytes, `SDK snapshot bytes match manifest: ${entry.path}`);
    assert.equal(hash(bytes), entry.sha256, `SDK snapshot hash matches manifest: ${entry.path}`);
    writeFileSync(target, bytes, { flag: 'wx' });
  }
  sdkManifest.snapshot_root = relative(sdkSnapshot);
  const joseRoot = path.join(workspace, 'external', 'a2a-to-mcp', 'node_modules', 'jose');
  const josePackage = JSON.parse(readFileSync(path.join(joseRoot, 'package.json'), 'utf8'));
  const joseManifest = treeManifest(joseRoot);
  const joseSnapshot = path.join(snapshotRoot, 'installed-jose'); mkdirSync(joseSnapshot);
  for (const entry of joseManifest.entries) {
    const target = path.join(joseSnapshot, entry.path); mkdirSync(path.dirname(target), { recursive: true });
    const bytes = readFileSync(path.join(joseRoot, entry.path));
    assert.equal(bytes.length, entry.bytes, `Dependency snapshot size: ${entry.path}`);
    assert.equal(hash(bytes), entry.sha256, `Dependency snapshot hash: ${entry.path}`);
    writeFileSync(target, bytes, { flag: 'wx' });
  }
  joseManifest.snapshot_root = relative(joseSnapshot);
  const cardFile = path.join(runDir, 'card.json'); const planFile = path.join(runDir, 'case-plan.json');
  exclusiveJson(cardFile, card); exclusiveJson(planFile, plan);
  report.pre_execution = {
    captured: stamp(), source_hashes: sources, node: { executable: process.execPath, version: process.version, executable_sha256: hash(readFileSync(process.execPath)), platform: process.platform, architecture: process.arch },
    sdk: { name: pkg.name, version: pkg.version, server_file: relative(sdkServer), server_sha256: serverHash, installed_manifest: sdkManifest, license: { path: relative(path.join(sdkRoot, 'LICENSE')), sha256: hash(readFileSync(path.join(sdkRoot, 'LICENSE'))) } },
    runtime_dependency: { name: josePackage.name, version: josePackage.version, manifest: joseManifest },
    specification: { path: relative(specification), sha256: hash(readFileSync(specification)) },
    exact_input_files: [{ path: relative(cardFile), sha256: hash(readFileSync(cardFile)) }, { path: relative(planFile), sha256: hash(readFileSync(planFile)) }]
  };
  exclusiveJson(path.join(runDir, 'pre-execution-ledger.json'), report.pre_execution);
  event({ type: 'pre-execution-ledger-frozen', path: relative(path.join(runDir, 'pre-execution-ledger.json')), sha256: hash(readFileSync(path.join(runDir, 'pre-execution-ledger.json'))) });

  // This is the first SDK import. No request handler, transport server or app.
  const { defaultServerCallContextBuilder, getSupportedVersions, validateVersion, UnauthenticatedUser, JsonRpcTransportHandler } = await import(pathToFileURL(sdkServer).href);
  const supportCall = { function: 'getSupportedVersions', started: stamp(), arguments: { card_path: relative(cardFile), protocol_binding: 'JSONRPC' } };
  report.function_calls.push(supportCall);
  try { supportCall.result = [...getSupportedVersions(card, 'JSONRPC')]; }
  catch (error) { supportCall.error = errorText(error); throw error; }
  finally { supportCall.completed = stamp(); }
  report.actual_supported_versions = supportCall.result;
  for (const control of plan) {
    const record = { case_id: control.case_id, attempt: 1, started: stamp(), input: control };
    report.cases.push(record); event({ type: 'case-started', case_id: control.case_id, input: control });
    const options = { extensions: undefined, user: new UnauthenticatedUser(), headers: control.headers, tenant: undefined };
    if (control.requested_version_property_present) options.requestedVersion = control.requested_version;
    record.actual_options_descriptor = { own_requested_version_property: Object.hasOwn(options, 'requestedVersion'), requested_version_value: Object.hasOwn(options, 'requestedVersion') ? options.requestedVersion : null, headers: options.headers, user: { class_name: options.user.constructor.name, is_authenticated: options.user.isAuthenticated, user_name: options.user.userName } };
    try {
      const builderCall = { function: 'defaultServerCallContextBuilder', case_id: control.case_id, started: stamp() }; report.function_calls.push(builderCall);
      let context;
      try { context = defaultServerCallContextBuilder(options); builderCall.result = { requestedVersion: context.requestedVersion, headers: context.state.get('headers') }; }
      catch (error) { builderCall.error = errorText(error); throw error; }
      finally { builderCall.completed = stamp(); }
      record.effective_requested_version = context.requestedVersion;
      record.headers_saved_by_builder = context.state.get('headers');
      const validationCall = { function: 'validateVersion', case_id: control.case_id, started: stamp(), arguments: { requested_version: context.requestedVersion, protocol_binding: 'JSONRPC', card_path: relative(cardFile) } }; report.function_calls.push(validationCall);
      try {
        const returned = validateVersion(context.requestedVersion, card, 'JSONRPC');
        validationCall.completed = stamp();
        record.validation = { accepted: true, returned_undefined: returned === undefined, actual_return: describeReturn(returned) };
        validationCall.result = record.validation;
      } catch (error) {
        validationCall.completed = stamp();
        record.validation = { accepted: false, semantic_exception: { name: error.name, constructor_name: error.constructor?.name, reason: error.reason ?? null, message: error.message, stack: errorText(error), has_code: 'code' in error, has_envelope_code: 'envelopeCode' in error, has_data: 'data' in error } };
        validationCall.error = record.validation.semantic_exception;
        const mappingCall = { function: 'JsonRpcTransportHandler.mapToJSONRPCError', case_id: control.case_id, started: stamp(), label: 'Local official SDK serialization of observed exception, not wire response' }; report.function_calls.push(mappingCall);
        try { mappingCall.result = JsonRpcTransportHandler.mapToJSONRPCError(error); record.optional_official_jsonrpc_mapping = mappingCall.result; }
        catch (mappingError) { mappingCall.error = errorText(mappingError); record.mapping_error = errorText(mappingError); }
        finally { mappingCall.completed = stamp(); }
      } finally { validationCall.completed ??= stamp(); }
      record.matches_prospective_expectation = record.effective_requested_version === control.expected_effective_version && record.validation.accepted === control.expected_acceptance && (control.expected_acceptance ? record.validation.returned_undefined === true : record.validation.semantic_exception.name === 'VersionNotSupportedError' && record.validation.semantic_exception.reason === 'VERSION_NOT_SUPPORTED' && record.optional_official_jsonrpc_mapping?.code === -32009);
    } catch (error) { record.unexpected_error = errorText(error); record.matches_prospective_expectation = false; }
    finally { record.completed = stamp(); event({ type: 'case-completed', ...record }); }
  }
  report.software_control_expectations_passed = report.actual_supported_versions.length === 1 && report.actual_supported_versions[0] === '1.0' && report.cases.length === 4 && report.cases.every(record => record.matches_prospective_expectation);
  report.outcome = report.software_control_expectations_passed ? 'passed-software-control' : 'failed-software-control'; report.exit_code = report.software_control_expectations_passed ? 0 : 1;
} catch (error) { report.outcome = 'failed-setup-or-import'; report.exit_code = 1; report.error = errorText(error); }
finally {
  report.post_source_sha256 = {}; report.post_source_errors = []; report.post_source_changes = [];
  const monitored = { ...Object.fromEntries(Object.entries(report.pre_execution?.source_hashes ?? {}).map(([filename, entry]) => [filename, entry.sha256])), ...Object.fromEntries((report.pre_execution?.sdk.installed_manifest.entries ?? []).map(entry => [relative(path.join(sdkRoot, entry.path)), entry.sha256])), ...Object.fromEntries((report.pre_execution?.runtime_dependency.manifest.entries ?? []).map(entry => [relative(path.join(workspace, report.pre_execution.runtime_dependency.manifest.root, entry.path)), entry.sha256])), ...Object.fromEntries((report.pre_execution?.exact_input_files ?? []).map(entry => [entry.path, entry.sha256])) };
  for (const [filename, expected] of Object.entries(monitored)) {
    try { const actual = hash(readFileSync(path.join(workspace, filename))); report.post_source_sha256[filename] = actual; if (actual !== expected) { report.post_source_changes.push({ path: filename, before: expected, after: actual }); report.outcome = 'failed-source-change'; report.exit_code = 1; } }
    catch (error) { report.post_source_errors.push({ path: filename, error: errorText(error) }); report.outcome = 'failed-source-read'; report.exit_code = 1; }
  }
  report.post_tree_changes = [];
  for (const baseline of [report.pre_execution?.sdk.installed_manifest, report.pre_execution?.runtime_dependency.manifest].filter(Boolean)) {
    try {
      const current = treeManifest(path.join(workspace, baseline.root));
      const expectedPaths = new Set(baseline.entries.map(entry => entry.path));
      const actualPaths = new Set(current.entries.map(entry => entry.path));
      const added = [...actualPaths].filter(filename => !expectedPaths.has(filename));
      const removed = [...expectedPaths].filter(filename => !actualPaths.has(filename));
      if (added.length || removed.length) { report.post_tree_changes.push({ root: baseline.root, added, removed }); report.outcome = 'failed-source-tree-change'; report.exit_code = 1; }
    } catch (error) { report.post_source_errors.push({ path: baseline.root, error: errorText(error) }); report.outcome = 'failed-source-tree-read'; report.exit_code = 1; }
  }
  if (report.pre_execution?.node.executable_sha256) {
    try {
      const current = hash(readFileSync(process.execPath));
      report.post_node_executable_sha256 = current;
      if (current !== report.pre_execution.node.executable_sha256) { report.post_source_changes.push({ path: process.execPath, before: report.pre_execution.node.executable_sha256, after: current }); report.outcome = 'failed-node-change'; report.exit_code = 1; }
    } catch (error) { report.post_source_errors.push({ path: process.execPath, error: errorText(error) }); report.outcome = 'failed-node-read'; report.exit_code = 1; }
  }
  report.completed = stamp(); report.cleanup = { process_id: process.pid, servers_started: 0, child_processes_started: 0, close_operation_required: false, completion: 'Same-process function calls ended; no owned service or child to close' };
  report.costs = { function_calls: report.function_calls.length, builder_calls: report.function_calls.filter(call => call.function === 'defaultServerCallContextBuilder').length, validator_calls: report.function_calls.filter(call => call.function === 'validateVersion').length, support_set_calls: report.function_calls.filter(call => call.function === 'getSupportedVersions').length, optional_mapping_calls: report.function_calls.filter(call => call.function === 'JsonRpcTransportHandler.mapToJSONRPCError').length, network_requests: 0, model_calls: 0 };
  report.event_log = { path: relative(eventLog), sha256: hash(readFileSync(eventLog)) };
  const reportFile = path.join(runDir, 'report.json'); exclusiveJson(reportFile, report);
  console.log(JSON.stringify({ outcome: report.outcome, report: relative(reportFile), report_sha256: hash(readFileSync(reportFile)), pid: process.pid, cases: report.cases.map(record => ({ case_id: record.case_id, effective_requested_version: record.effective_requested_version, validation: record.validation && { accepted: record.validation.accepted, semantic_name: record.validation.semantic_exception?.name }, optional_mapped_code: record.optional_official_jsonrpc_mapping?.code, matches_prospective_expectation: record.matches_prospective_expectation })), costs: report.costs, error: report.error }));
  process.exitCode = report.exit_code;
}
