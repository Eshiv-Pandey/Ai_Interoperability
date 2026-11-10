"""Fresh-cell original AP2 payment-tool development comparisons.

This separately declared successor executes original modules and SDK handlers
over owned TCP sockets. Three legal original bridge initiation routes retain
actual MCP replies without inventing an inverse. It establishes selected
development observations, not live-provider, human-gold or full task grades.
"""
from __future__ import annotations

import argparse
import asyncio
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from types import CodeType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
STAGE = ROOT / 'runs/ap2-environment-preparation/source-stage-v1/manifest.json'
STAGE_SHA = '78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463'
ENVIRONMENT = ROOT / 'runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json'
ENVIRONMENT_SHA = '4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5'
SOURCE = STAGE.parent / 'ap2'
MODEL = 'gemini-3.1-flash-lite-preview'
CONTRACT = {'catalog_search': 'unbranded walking shoes', 'user_email': 'bugsbunny@gmail.com',
            'currency': 'USD', 'max_amount_cents': 10000}
ROUTES = {
    "Find products that match the user's request.": 'find_items_workflow',
    "Get the user's shipping address.": 'handle_get_shipping_address',
    "Get a filtered list of the user's payment methods.": 'handle_search_payment_methods',
    "Get a payment credential token for the user's payment method.": 'handle_create_payment_credential_token',
    'Create a checkout for the selected cart.': 'create_checkout',
    'This is the signed payment mandate': 'handle_signed_payment_mandate',
    'Initiate a payment': 'initiate_payment',
    'Initiate a payment. Include the challenge response.': 'initiate_payment',
    'initiate_payment': 'initiate_payment',
    'Give me the payment method credentials for this mandate.': 'handle_get_payment_method_raw_credentials',
    'Here is the payment receipt. No action is required.': 'handle_payment_receipt',
}
PEERS = (
    ('merchant', 'roles.merchant_agent', 'MerchantAgentExecutor', 8001, '/a2a/merchant_agent'),
    ('credentials', 'roles.credentials_provider_agent', 'CredentialsProviderExecutor', 8002, '/a2a/credentials_provider'),
    ('processor', 'roles.merchant_payment_processor_agent', 'PaymentProcessorExecutor', 8003, '/a2a/merchant_payment_processor_agent'),
)
SECRET_NAMES = ('GOOGLE_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS',
                'AGENT_PROVIDER_SIGNING_KEY_PEM', 'MERCHANT_SIGNING_KEY_PEM')
CODE_FIELDS = (
    'co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals', 'co_stacksize',
    'co_flags', 'co_code', 'co_names', 'co_varnames', 'co_freevars', 'co_cellvars',
    'co_filename', 'co_name', 'co_qualname', 'co_firstlineno', 'co_linetable', 'co_exceptiontable',
)
OWNED_COMPONENTS = (
    'scripts/ap2_reference_development_v11.py',
    'scripts/ap2_public_certificate_guard_v11.py',
    'scripts/print_ap2_owned_cell_diagnostics_v1.py',
    'scripts/run_ap2_cell_with_safe_diagnostics_v1.py',
    'scripts/ap2_native_bridge_runtime_v11.py',
    'scripts/agentops_bridge_runtime_archive_v1.py',
    'scripts/ap2_bridge_client_v11.mjs',
    'scripts/ap2_bridge_network_guard_v11.mjs',
    'src/interoperability/ap2_native_transport_v11.py',
    'src/interoperability/__init__.py',
    'src/interoperability/ap2_hp_original_binding_v1.py',
    'src/interoperability/ap2_hp_reference_execution_v1.py',
    'src/interoperability/ap2_hp_reference_plan_v1.py',
    'src/interoperability/ap2_hp_durable_observer_v1.py',
    'src/interoperability/ap2_pending_admission_v4.py',
    'src/interoperability/ap2_application_profile_v5.py',
    'src/interoperability/ap2_application_coordinator_v5.py',
    'benchmark/ap2-native-bridge-development-v11/application.json',
    'src/interoperability/refinement_shared_lift_v2.py',
    'src/interoperability/refinement.py',
    'src/interoperability/refinement_oracle.py',
    'src/interoperability/manifest.py',
    'src/interoperability/oracle.py',
)
BRIDGE_SOURCES = (
    'external/a2a-to-mcp/src/agent-card.ts',
    'external/a2a-to-mcp/src/a2a-client.ts',
    'external/a2a-to-mcp/src/tools.ts',
    'external/mcp-a2a/src/client/peer.ts',
    'external/mcp-a2a/src/client/fetch.ts',
    'external/mcp-a2a/src/tools/writes.ts',
    'external/mcp-a2a/src/tools/request.ts',
)


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def need(condition, label):
    if not condition:
        raise ValueError(label)


def constant_fingerprint(value):
    """Typed structural constants; serialization reference memoization is excluded."""
    if type(value) is CodeType:
        return code_fingerprint(value)
    if value is None:
        return ('none',)
    if value is Ellipsis:
        return ('ellipsis',)
    if type(value) in (str, int, bool, bytes):
        return (type(value).__name__, value)
    if type(value) is float:
        return ('float', value.hex())
    if type(value) is complex:
        return ('complex', value.real.hex(), value.imag.hex())
    if type(value) is tuple:
        return ('tuple', tuple(constant_fingerprint(child) for child in value))
    if type(value) is frozenset:
        return ('frozenset', tuple(sorted((constant_fingerprint(child) for child in value), key=repr)))
    raise ValueError('unsupported_code_constant_type')


def code_fingerprint(code):
    """All code identity attributes plus recursively typed constants and positions."""
    need(type(code) is CodeType, 'exact_code_object_required')
    return ('code', tuple((name, constant_fingerprint(getattr(code, name))) for name in CODE_FIELDS),
            constant_fingerprint(code.co_consts),
            constant_fingerprint(tuple(code.co_lines())),
            constant_fingerprint(tuple(code.co_positions())))


def recursive_public_json(value, *, model_base=None, explicitly_set_model=None):
    """Detach finite JSON and explicit public model dumps, with strict types/bounds."""
    active = set()
    nodes = 0

    def project(item, depth):
        nonlocal nodes
        nodes += 1
        need(nodes <= 20000 and depth <= 40, 'public_projection_bound')
        if item is None or type(item) in (str, int, bool):
            return item
        if type(item) is float:
            need(math.isfinite(item), 'nonfinite_public_number')
            return item
        is_model = model_base is not None and isinstance(item, model_base)
        need(type(item) in (list, dict) or is_model, 'unsupported_public_projection_type')
        identity = id(item)
        need(identity not in active, 'cyclic_public_projection')
        active.add(identity)
        try:
            if is_model:
                options = {'mode': 'json', 'by_alias': True}
                if type(item) is explicitly_set_model:
                    options['exclude_unset'] = True
                return project(item.model_dump(**options), depth + 1)
            if type(item) is list:
                return [project(child, depth + 1) for child in item]
            need(all(type(key) is str for key in item), 'public_object_string_keys_required')
            return {key: project(child, depth + 1) for key, child in item.items()}
        finally:
            active.remove(identity)

    return project(value, 0)


def make_wire_reference_plan(planner, input_required):
    """Adapt the owned comparison to SDK wire labels without rewriting Tasks."""
    need(type(input_required) is str and input_required == 'input-required', 'unsupported_task_state_wire_value')

    class WireReferencePlan(planner.ReferencePlan):
        def observe(self, phase, value):
            if phase not in {'payment_start', 'payment_resume'}:
                return super().observe(phase, value)
            original_task = planner._task

            def wire_task(task, context=None, states=('completed',)):
                allowed = tuple(input_required if state == 'input_required' else state for state in states)
                return original_task(task, context, allowed)

            # observe is synchronous and pure. Restore the owned helper slot even
            # when its context/task/phase guard refuses the actual public value.
            planner._task = wire_task
            try:
                result = super().observe(phase, value)
            finally:
                planner._task = original_task
            if phase == 'payment_resume':
                target = 'completed' if self.state['challenge_response'] == '123' else input_required
                self.state['source_branch_requested_target'] = target
                self.state['supplied_continuation_target_observed'] = (
                    self.state['supplied_merchant_after']['status']['state'] == target)
            return result

    return WireReferencePlan


def write(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    need(len(raw) <= 16 * 1024 * 1024, 'report_size_bound')
    with Path(path).open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def now():
    return datetime.now(timezone.utc).isoformat()


def append(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    need(len(raw) <= 64 * 1024, 'journal_entry_size_bound')
    with Path(path).open('ab') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def inventory(directory):
    directory = Path(directory).resolve()
    result = {}
    for path in sorted(directory.rglob('*')):
        need(not path.is_symlink(), 'linked_inventory_entry')
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            need(len(result) < 25000 and path.stat().st_size <= 64 * 1024 * 1024, 'inventory_bound')
            result[path.relative_to(directory).as_posix()] = digest(path.read_bytes())
    return result


def source_contract():
    raw = STAGE.read_bytes()
    need(digest(raw)['sha256'] == STAGE_SHA, 'frozen_stage_changed')
    stage = json.loads(raw)
    expected = {row['path']: {key: row[key] for key in ('bytes', 'sha256')}
                for row in stage['files'] if row['project'] == 'ap2'}
    need(stage['ap2_files'] == 136 and len(expected) == 136, 'complete_original_union_required')
    need(inventory(SOURCE) == expected, 'original_tree_changed')
    return raw, expected


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    stage_raw, files = source_contract()
    raw = ENVIRONMENT.read_bytes()
    need(digest(raw)['sha256'] == ENVIRONMENT_SHA, 'frozen_version_manifest_changed')
    environment = json.loads(raw)
    excluded = {'ap2', 'ap2-samples', 'x402-a2a', 'pywin32', 'pywin32-ctypes', 'wmi'}
    rows = environment['all_distributions']
    requirements = sorted(f"{name}=={row['version']}" for name, row in rows.items() if name.lower() not in excluded)
    (output / 'requirements.txt').write_text('\n'.join(requirements) + '\n', encoding='utf-8')
    write(output / 'contract.json', {
        'schema_version': 'ap2-native-bridge-development/11', 'status': 'offline_application_prepared',
        'source_manifest': digest(stage_raw), 'original_ap2_file_count': len(files),
        'version_source_manifest': digest(raw), 'requirements': requirements,
        'compiled_windows_wheel_hashes_apply_to_linux': False, 'provider_requests_allowed': 0,
        'scope': 'full original apps and caller; offline model fixtures and native TCP transport',
        'native_qualification_established': False, 'aggregate_task_grade': None,
    })
    if sys.platform == 'linux':
        from ap2_native_bridge_runtime_v11 import materialize
        materialize(output / 'bridge-runtime')


class OfflineModel:
    def __init__(self, output):
        self.output, self.rows = output, []

    def generate_content(self, *, model, contents, config):
        need(model == MODEL and len(self.rows) < 24, 'offline_model_budget_or_identity')
        if isinstance(config, dict) and config.get('response_mime_type') == 'application/json':
            need(isinstance(contents, str) and "unbranded walking shoes" in contents
                 and 'PaymentItem' in contents, 'unreviewed_catalog_prompt')
            PaymentItem = importlib.import_module('ap2.models.payment_request').PaymentItem
            values = [PaymentItem.model_validate({'label': label, 'amount': {'currency': 'USD', 'value': price}})
                      for label, price in [('Walking shoes', '12.50'), ('Trail shoes', '18.00'), ('Canvas shoes', '23.00')]]
            row = {'kind': 'offline_catalog_fixture', 'items': [item.model_dump(mode='json') for item in values]}
            response = SimpleNamespace(parsed=values)
        else:
            offered = [declaration.name for tool in config.tools for declaration in tool.function_declarations or []]
            choice = ROUTES.get(contents)
            need(choice is not None and choice in offered, 'unknown_or_unoffered_offline_tool_choice')
            row = {'kind': 'offline_tool_choice_fixture', 'prompt': contents, 'offered': offered, 'choice': choice}
            response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[
                SimpleNamespace(function_call=SimpleNamespace(name=choice))]))])
        row.update(index=len(self.rows), model=model, provider_requests=0)
        self.rows.append(row)
        with (self.output / 'model-interventions.jsonl').open('ab') as handle:
            handle.write((json.dumps(row, sort_keys=True) + '\n').encode())
            handle.flush()
            os.fsync(handle.fileno())
        return response


def process_identity(pid):
    try:
        raw = Path(f'/proc/{pid}/stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        return (int(fields[1]), fields[19])
    except (OSError, ValueError, IndexError):
        return None


def stop_owned_descendants(pid):
    """Kill only descendants whose observed PID/parent/start-time identity holds."""
    selected = {pid: process_identity(pid)}
    changed = True
    while changed:
        changed = False
        for path in Path('/proc').iterdir():
            if not path.name.isdecimal():
                continue
            candidate = int(path.name)
            identity = process_identity(candidate)
            if identity and identity[0] in selected and candidate not in selected:
                selected[candidate] = identity
                changed = True
    killed = []
    for candidate, identity in reversed(list(selected.items())):
        if identity is not None and process_identity(candidate) == identity:
            try:
                os.kill(candidate, signal.SIGKILL)
                killed.append(candidate)
            except ProcessLookupError:
                pass
    return killed


async def bridge_initiation(output, plan, request):
    """Map an actual unchanged shopper-builder request through a real original CLI."""
    bridge = output / 'bridge'
    bridge.mkdir(exist_ok=False)
    state = bridge / 'state'
    state.mkdir()
    wire = bridge / 'sender-wire.bin'
    wire.write_bytes(request.content)
    write(bridge / 'original-sender-request.json', {
        'method': request.method, 'url': str(request.url), 'entity': digest(request.content),
        'headers': {key: value for key, value in request.headers.items()},
        'original_builder_executed': True, 'native_application_forwarded_at_this_boundary': False,
        'owned_bridge_forward_mapping_declared': True, 'inverse_response_mapping_invented': False})
    route = plan['policy']['bridge_route']
    runtime = Path(plan['bridge_runtime'])
    node = plan['node']['executable']
    client, guard = (ROOT / 'scripts/ap2_bridge_client_v11.mjs', ROOT / 'scripts/ap2_bridge_network_guard_v11.mjs')
    config_path = bridge / 'client-config.json'
    port = 18791
    amir = route == 'amir_typed'
    package = runtime / 'external' / ('a2a-to-mcp' if amir else 'mcp-a2a')
    cli_args = ['--import', str(guard), str(package / 'dist/cli.js')]
    if amir:
        agents = state / 'agents.json'
        write(agents, {'agents': {'ap2': {'cardUrl': f'http://127.0.0.1:8001{PEERS[0][4]}/.well-known/agent-card.json'}}})
        cli_args.extend(['--config', str(agents), '--host', '127.0.0.1', '--port', str(port)])
    shared = {'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC',
              'TMPDIR': str(state), 'XDG_CONFIG_HOME': str(state), 'XDG_STATE_HOME': str(state),
              'A2A_ALLOW_WRITES': '1', 'A2A_CHANNEL': '0', 'A2A_MAX_RETRIES': '0',
              'A2A_CONFIG': str(state / 'absent-bridge-config.json'), 'A2A_STATE_DIR': str(state / 'mg-state'),
              'A2A_DAEMON_URL': 'http://127.0.0.1:8001', 'A2A_PEERS': 'http://127.0.0.1:8001',
              'AP2_NATIVE_GUARD': '1', 'AP2_GUARD_STATE': str(bridge), 'AP2_GUARD_RUNTIME': str(runtime),
              'AP2_GUARD_READ_FILES': json.dumps([str(client), str(guard), str(config_path), str(wire)]),
              'AP2_GUARD_CHILD_ARGS': json.dumps(cli_args)}
    child_env = dict(shared, AP2_GUARD_ROLE='bridge', AP2_GUARD_LOG=str(bridge / 'bridge-guard.jsonl'),
                     AP2_GUARD_PEER_PORTS=json.dumps([8001, 8002, 8003]), AP2_GUARD_LISTEN_PORTS=json.dumps([port] if amir else []))
    client_env = dict(shared, AP2_GUARD_ROLE='client', AP2_GUARD_LOG=str(bridge / 'client-guard.jsonl'),
                      AP2_GUARD_PEER_PORTS=json.dumps([8001, 8002, 8003, port]), AP2_GUARD_LISTEN_PORTS=json.dumps([port] if amir else []))
    write(config_path, {'schema_version': 'ap2-native-bridge-client/11', 'output': str(bridge), 'sender_wire': str(wire),
                       'node_version': 'v22.23.2', 'route': route, 'alias': 'ap2', 'peer': 'http://127.0.0.1:8001/',
                       'mcp_endpoint': f'http://127.0.0.1:{port}/mcp', 'bridge_port': port,
                       'bridge_pin': '58eff9da469bccdc432bf164662727947de646b4' if amir else 'c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5',
                       'bridge': {'command': node, 'args': cli_args, 'cwd': str(runtime), 'env': child_env},
                       'limits': {'request_ms': 15000, 'total_ms': 60000, 'max_bytes': 8388608}})
    argv = [node, '--import', str(guard), str(client), '--config', str(config_path)]
    write(bridge / 'client-before-dispatch.json', {'argv': argv, 'started_utc': datetime.now(timezone.utc).isoformat(),
                                                'credential_free_explicit_environment': True})
    child = await asyncio.create_subprocess_exec(*argv, cwd=runtime, env=client_env,
                                                 stdin=subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE)
    forced = []
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), timeout=70)
    except BaseException:
        forced = stop_owned_descendants(child.pid)
        await child.wait()
        raise
    finally:
        write(bridge / 'client-after-dispatch.json', {'pid': child.pid, 'returncode': child.returncode,
                                                    'forced_cleanup_pids': forced,
                                                    'ended_utc': datetime.now(timezone.utc).isoformat()})
    (bridge / 'client-stdout.txt').write_bytes(stdout[:2 * 1024 * 1024])
    (bridge / 'client-stderr.txt').write_bytes(stderr[:2 * 1024 * 1024])
    result = json.loads((bridge / 'result.json').read_bytes())
    need(child.returncode == 0 and result['cleanup']['strict_cleanup_passed'] is True,
         'original_bridge_process_not_strictly_closed')


def imported_inventory(site_packages):
    result = {}
    for name, module in sorted(sys.modules.copy().items()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_file() and (path.is_relative_to(site_packages) or path.is_relative_to(SOURCE)
                                   or path.is_relative_to(ROOT / 'src')):
                result[name] = {'path': str(path), **digest(path.read_bytes())}
    return result


def resource_check():
    if os.name != 'nt':
        return {'status': 'hosted_or_nonwindows_execution', 'windows_memory_gate_applies': False}
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in
            ('total_physical', 'available_physical', 'total_commit', 'available_commit',
             'total_virtual', 'available_virtual', 'available_extended')]
    value = Memory()
    value.length = ctypes.sizeof(value)
    need(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)), 'memory_observation_failed')
    okay = value.available_physical >= 1024 ** 3 and value.available_commit >= 2 * 1024 ** 3
    return {'status': 'memory_gate_passed' if okay else 'local_memory_gate_refused',
            'available_physical_bytes': value.available_physical,
            'available_commit_bytes': value.available_commit,
            'minimum_physical_bytes': 1024 ** 3, 'minimum_commit_bytes': 2 * 1024 ** 3}


async def application(output, site_packages, private, case, policy):
    append(output / 'worker-stages.jsonl', {'stage': 'application_entry', 'utc': now()})
    sys.path[:0] = [str(ROOT / 'src'), str(SOURCE / 'code/samples/python/src'),
                    str(SOURCE / 'code/sdk/python'), str(STAGE.parent / 'a2a-x402/python/x402_a2a/src'),
                    str(site_packages)]
    mandate_module = importlib.import_module('ap2.sdk.mandate')
    append(output / 'worker-stages.jsonl', {'stage': 'original_mandate_import_completed', 'utc': now()})
    original_log_path = mandate_module.LOG_FILE_PATH
    mandate_module.LOG_FILE_PATH = str(private / '.logs/mandate_operations.log')
    # Schema construction sees the original GenAI class; only subsequent model clients are fixtures.
    importlib.import_module('google.adk.tools.tool_context')
    append(output / 'worker-stages.jsonl', {'stage': 'ADK_tool_context_import_completed', 'utc': now()})
    import httpx
    from google import genai
    from interoperability import ap2_hp_durable_observer_v1 as durable
    from interoperability import ap2_hp_original_binding_v1 as binding
    from interoperability import ap2_hp_reference_execution_v1 as execution
    from interoperability.ap2_hp_reference_execution_v1 import ReferenceCoordinator
    from interoperability import ap2_hp_reference_plan_v1 as planner
    from interoperability import ap2_application_profile_v5 as admission
    from interoperability.ap2_application_coordinator_v5 import ApplicationCoordinator, ReceivedAdmissionBoundary
    from a2a.types import TaskState, TaskQueryParams
    from pydantic import BaseModel
    from interoperability.ap2_native_transport_v11 import OwnedPeerGroup
    ContactAddress = importlib.import_module('ap2.models.contact_picker').ContactAddress
    original_public_json = execution.public_json

    def coordinator_public_json(value):
        # Compare the original returned address's explicit fields to the raw
        # DataPart. Defaults inserted by its original model are retained separately.
        return recursive_public_json(value, model_base=BaseModel, explicitly_set_model=ContactAddress)

    def retain_public_json(value):
        return recursive_public_json(value, model_base=BaseModel)

    append(output / 'worker-stages.jsonl', {'stage': 'before_original_source_inventory', 'utc': now()})
    stage_raw, source_files = source_contract()
    append(output / 'worker-stages.jsonl', {'stage': 'original_source_inventory_completed', 'utc': now()})
    runtime_files = inventory(site_packages)
    append(output / 'worker-stages.jsonl', {'stage': 'installed_runtime_inventory_completed', 'utc': now()})
    runtime = {'schema_version': 'ap2-offline-native-application-runtime/11', 'root': str(site_packages),
               'files': runtime_files, 'python': sys.version, 'platform': platform.platform(),
               'versions': {name: importlib.metadata.version(name) for name in
                            ('a2a-sdk', 'google-adk', 'google-genai', 'pydantic', 'cryptography', 'jwcrypto', 'httpx', 'starlette')}}
    write(output / 'runtime-manifest.json', runtime)
    runtime_path = output / 'runtime-manifest.json'
    runtime_raw = runtime_path.read_bytes()
    source_binding = binding.SourceBinding(SOURCE.resolve(), site_packages, STAGE.resolve(), runtime_path.resolve(),
                                          stage_raw, runtime_raw, source_files, runtime_files)
    original_validator = binding.SourceBinding.verify_unchanged
    original_marshal = binding.marshal
    original_function_check = binding._verify_function
    callable_checks = []

    def observed_function_check(function, node, expected, namespace, enclosing=None):
        legacy_equal = original_marshal.dumps(function.__code__) == original_marshal.dumps(expected)
        actual_fingerprint, expected_fingerprint = code_fingerprint(function.__code__), code_fingerprint(expected)
        row = {
            'index': len(callable_checks), 'module': function.__module__, 'qualified_name': function.__qualname__,
            'full_structural_code_equal': actual_fingerprint == expected_fingerprint,
            'legacy_marshal_bytes_equal': legacy_equal,
            'actual_fingerprint_sha256': digest(repr(actual_fingerprint).encode())['sha256'],
            'expected_fingerprint_sha256': digest(repr(expected_fingerprint).encode())['sha256'],
            'identity_fields': list(CODE_FIELDS) + ['co_consts_recursive_types', 'co_lines', 'co_positions'],
        }
        callable_checks.append(row)
        need(len(callable_checks) <= 1000, 'callable_observation_bound')
        need(row['full_structural_code_equal'], 'original_callable_structural_code_differs:' + function.__qualname__)
        # The unchanged owned helper still checks globals, defaults and closure identity.
        return original_function_check(function, node, expected, namespace, enclosing)

    def portable_validator(self):
        need(self is source_binding and self.stage_path.read_bytes() == stage_raw
             and self.environment_path.read_bytes() == runtime_raw, 'portable_binding_manifest_changed')
        need(source_contract()[1] == self.source_files, 'portable_binding_source_changed')
        return True

    binding.SourceBinding.verify_unchanged = portable_validator
    binding.marshal = SimpleNamespace(dumps=code_fingerprint)
    binding._verify_function = observed_function_check
    model = OfflineModel(output)
    original_genai, original_init = genai.Client, httpx.AsyncClient.__init__
    clients, transports, wrappers, task_stores = [], {}, {}, {}
    plan = json.loads((output / 'plan.json').read_bytes())
    group = OwnedPeerGroup(output, write, (lambda request: bridge_initiation(output, plan, request))
                           if policy.get('bridge_route') else None)
    recorder = durable.DurableRecorder.allocate(output / 'observations', {
        'merchant_raw': 'raw_asgi', 'credentials_raw': 'raw_asgi', 'processor_raw': 'raw_asgi',
        'merchant_public': 'public', 'credentials_public': 'public',
    })
    lease = outcome = None
    admission_boundary = ReceivedAdmissionBoundary(output, recorder, durable, case, policy, write)
    transport_rows = []
    restored = True
    cleanup_failures = []

    class LocalTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            need(request.url.scheme == 'http' and request.url.host in {'localhost', '127.0.0.1'}
                 and request.url.port in transports, 'external_transport_refused')
            need('authorization' not in request.headers and 'x-goog-api-key' not in request.headers,
                 'secret_transport_header_refused')
            if request.url.port == 8001 and request.method == 'POST':
                payload = admission.decode_json(request.content)
                message = payload.get('params', {}).get('message', {})
                texts = [part.get('text') for part in message.get('parts', []) if part.get('kind') == 'text']
                if texts == [admission.TEXT]:
                    need(str(request.url) == admission.MERCHANT
                         and admission.EXTENSION in request.headers.get('x-a2a-extensions', '').split(', '),
                         'received_raw_merchant_endpoint_or_extension_changed')
                    need(lease is not None and lease.bindings.merchant.records[-1]['boundary'] == 'attempt',
                         'actual_original_public_send_attempt_required')
                    sender = lease.bindings.merchant.records[-1]['public_value']
                    if case['fault'] == 'drop_received_payment_datapart' and policy['apply_received_fault']:
                        incoming = request.content
                        message['parts'] = [part for part in message['parts']
                                            if admission.PAYMENT not in part.get('data', {})]
                        mutated = admission.encoded(payload)
                        write(output / 'recipient-loss-intervention.json', {
                            'kind': 'owned_transport_drops_payment_datapart_after_unchanged_original_builder',
                            'original_sender_message': sender, 'original_sdk_raw_request': json.loads(incoming),
                            'received_raw_request': payload,
                            'original_sdk_raw_identity': digest(incoming), 'received_raw_identity': digest(mutated),
                            'original_source_or_sdk_message_mutated': False})
                        headers = [(key, value) for key, value in request.headers.multi_items() if key.lower() != 'content-length']
                        request = httpx.Request(request.method, request.url, headers=headers, content=mutated,
                                                extensions=request.extensions)
                    await admission_boundary.authorize(request.content, sender)
            transport_rows.append({'index': len(transport_rows), 'method': request.method,
                                   'url': str(request.url), 'transport': 'owned_httpx_native_TCP',
                                   'provider_request': False})
            need(len(transport_rows) <= 64, 'peer_transport_request_bound')
            return await transports[request.url.port].handle_async_request(request)

    def leased_init(self, *args, **kwargs):
        need('transport' not in kwargs, 'unexpected_existing_transport')
        kwargs.update(transport=LocalTransport(), trust_env=False)
        original_init(self, *args, **kwargs)
        clients.append(self)

    def offline_client(*args, **kwargs):
        need(not args and not kwargs, 'unexpected_model_client_options')
        return SimpleNamespace(models=model)

    httpx.AsyncClient.__init__, genai.Client = leased_init, offline_client
    try:
        from common import server
        for role, package, executor_name, port, rpc in PEERS:
            main = importlib.import_module(package + '.__main__')
            executor_module = importlib.import_module(package + '.agent_executor')
            card = server.load_local_agent_card(main.__file__)
            executor = getattr(executor_module, executor_name)(card.capabilities.extensions)
            app = server._build_starlette_app(card, executor=executor, rpc_url=rpc)
            original_routes = [route for route in app.routes if getattr(route, 'path', None) == rpc]
            need(len(original_routes) == 1, 'unique_original_sdk_rpc_application_required')
            task_stores[role] = original_routes[0].endpoint.__self__.handler.request_handler.task_store
            need(type(task_stores[role]).__module__ == 'a2a.server.tasks.inmemory_task_store'
                 and type(task_stores[role]).__name__ == 'InMemoryTaskStore' and task_stores[role].tasks == {},
                 'actual_original_native_task_store_not_fresh')
            write(output / (role + '-original-card.json'), card.model_dump(mode='json', by_alias=True, exclude_none=True))
            server._add_middlewares(app, logging.getLogger('ap2.offline.' + role))
            wrappers[role] = durable.RawAsgiCapture(app, recorder.sink(role + '_raw'))
            transports[port] = group.allocate(role, wrappers[role], port)
        modules = {name: importlib.import_module(name) for name in binding.SOURCE_MODULES}
        need(modules['roles.shopping_agent.subagents.shipping_address_collector.tools'].ContactAddress is ContactAddress,
             'original_contact_address_alias_changed')
        lease = binding.make_caller_binding(source_binding, modules, temporary_root=private,
                                           merchant_sink=recorder.sink('merchant_public'),
                                           credentials_sink=recorder.sink('credentials_public'))
        lease.install()
        need(lease.installed and lease.error is None, 'original_caller_lease_incomplete')
        merchant_storage = importlib.import_module('roles.merchant_agent.storage')
        credential_storage = importlib.import_module('roles.credentials_provider_agent.account_manager')
        write(output / 'original-state-before.json', {
            'merchant_store': retain_public_json(merchant_storage._store),
            'credential_tokens': retain_public_json(credential_storage._token),
            'task_stores': {role: {'class': type(store).__module__ + '.' + type(store).__qualname__,
                                 'task_ids': list(store.tasks)} for role, store in task_stores.items()},
            'provider_credentials_present': False, 'private_key_contents_retained': False})
        execution.public_json = coordinator_public_json
        wire_plan = make_wire_reference_plan(planner, TaskState.input_required.value)
        coordinator = ApplicationCoordinator(lease.bindings, wire_plan, CONTRACT,
            original_tools=modules['roles.shopping_agent.tools'], output=output, case=case, policy=policy,
            boundary=admission_boundary, writer=write, serializer=retain_public_json, task_query_class=TaskQueryParams)
        outcome = await coordinator.run()
        write(output / 'original-state-after.json', {
            'merchant_store': retain_public_json(merchant_storage._store),
            'credential_tokens': retain_public_json(credential_storage._token),
            'task_stores': {role: {'class': type(store).__module__ + '.' + type(store).__qualname__,
                                 'tasks': [retain_public_json(task) for task in store.tasks.values()]}
                            for role, store in task_stores.items()},
            'private_key_contents_retained': False})
        write(output / 'reference-result.json', outcome.report())
        write(output / 'caller-final-state.json', retain_public_json(coordinator.context.state))
        write(output / 'original-tool-returns.json', [{'phase': phase, 'value': retain_public_json(value)}
                                                     for phase, value in outcome.tool_returns])
        # Copy public verification keys only. The original apps generated their private keys.
        public = output / 'public-verification'
        public.mkdir()
        for path in private.glob('*.pub'):
            shutil.copyfile(path, public / path.name)
    finally:
        if lease is not None:
            try:
                restored = lease.restore()
            except BaseException as error:
                restored = False
                cleanup_failures.append({'operation': 'caller_lease_restore', 'error_type': type(error).__name__})
        try:
            for index, client in enumerate(clients):
                try:
                    await client.aclose()
                except BaseException as error:
                    cleanup_failures.append({'operation': 'client_aclose', 'index': index, 'error_type': type(error).__name__})
            for index, transport in enumerate(transports.values()):
                try:
                    await transport.aclose()
                except BaseException as error:
                    cleanup_failures.append({'operation': 'transport_aclose', 'index': index, 'error_type': type(error).__name__})
        finally:
            try:
                await group.close()
            except BaseException as error:
                cleanup_failures.append({'operation': 'owned_peer_group_close', 'error_type': type(error).__name__})
            finally:
                httpx.AsyncClient.__init__, genai.Client = original_init, original_genai
                binding.SourceBinding.verify_unchanged = original_validator
                binding.marshal = original_marshal
                binding._verify_function = original_function_check
                execution.public_json = original_public_json
                mandate_module.LOG_FILE_PATH = original_log_path
        for role, _, _, _, _ in PEERS:
            if role in wrappers:
                wrappers[role].finish()
            else:
                recorder.finish_stream(role + '_raw', {'source_complete': True, 'active_operations': 0,
                                                       'attempted_records': 0})
        for role in ('merchant', 'credentials'):
            observer = getattr(lease.bindings, role) if lease is not None else None
            recorder.finish_stream(role + '_public', {
                'source_complete': observer.capture_complete if observer is not None else True,
                'active_operations': observer.active_calls if observer is not None else 0,
                'attempted_records': len(observer.records) if observer is not None else 0,
            })
        recorder.publish(allow_incomplete=True)
        recorder.close()
        write(output / 'transport-interventions.json', transport_rows)
        write(output / 'original-callable-code-checks.json', callable_checks)
        write(output / 'imported-modules.json', imported_inventory(site_packages))
        write(output / 'cleanup.json', {'client_count': len(clients), 'clients_closed': all(c.is_closed for c in clients),
                                      'caller_aliases_restored': restored, 'raw': {key: value.report() for key, value in wrappers.items()},
                                      'owned_validator_intervention': 'portable source and fresh site-packages inventory; legacy native environment claim not used',
                                      'owned_code_comparison_intervention': 'full recursive structural code identity, typed constants, filename/line/position/exception metadata; legacy globals/default/closure/alias guards retained',
                                      'owned_public_projection_intervention': 'bounded recursive explicit BaseModel dumps; shipping comparison uses explicit original model fields and retains full original return separately',
                                      'owned_task_state_comparison_intervention': {
                                          'input_required_wire_value': TaskState.input_required.value,
                                          'raw_task_status_values_unchanged': True,
                                          'task_context_identity_guards_preserved': True},
                                      'public_observer_serializer_unchanged': lease is None or all(
                                          observer.serializer is original_public_json for observer in
                                          (lease.bindings.merchant, lease.bindings.credentials)),
                                      'original_sdk_log_destination_intervention': 'owned private temporary profile; no source-tree log writes',
                                      'runtime_tree_unchanged': inventory(site_packages) == runtime_files,
                                      'source_tree_unchanged': source_contract()[1] == source_files,
                                      'strict_native_socket_cleanup_passed': group.cleanup_complete,
                                      'owned_cleanup_failures': cleanup_failures,
                                      'in_process_ASGITransport_used': False,
                                      'original_native_server_launch_qualification_established': False})
        admission_boundary.finish()
    return outcome is not None and recorder.report()['published_complete'] is True and group.cleanup_complete and not cleanup_failures


def worker(output, site_packages):
    need(not any(os.environ.get(name) for name in SECRET_NAMES), 'credential_free_worker_required')
    plan = json.loads((output / 'plan.json').read_bytes())
    for name, expected in plan['owned_components'].items():
        need(digest((ROOT / name).read_bytes()) == expected, 'prospective_owned_source_component_changed')
        need(digest((output / 'owned-source' / name).read_bytes()) == expected, 'retained_owned_source_component_changed')
    from ap2_native_bridge_runtime_v11 import verify as verify_bridge_runtime
    from ap2_public_certificate_guard_v11 import prepare_public_certificates, admitted_certificates_unchanged, record_denial
    verify_bridge_runtime(Path(plan['bridge_runtime']))
    denials = {'private_reads_blocked': 0, 'external_network_operations_blocked': 0,
               'unallocated_descendant_processes_blocked': 0, 'allowed_owned_loopback_operations': 0,
               'allowed_allocated_bridge_client_processes': 0}
    audit_state = {'private_root': None, 'bridge_client_dispatched': False, 'diagnostic_rows': 0,
                   'expected_private_evaluator_probe': False}
    append(output / 'worker-stages.jsonl', {'stage': 'before_declared_public_certificate_admission', 'utc': now()})
    public_CA_bundles = prepare_public_certificates(output, SOURCE, site_packages, write)
    append(output / 'worker-stages.jsonl', {'stage': 'declared_public_certificate_admission_completed', 'utc': now()})

    def guard_roots():
        return {'SOURCE': SOURCE, 'SITE_PACKAGES': site_packages, 'REPOSITORY': ROOT,
                'PRIVATE_PROFILE': audit_state['private_root']}

    def public_only_actor(event, values):
        if event == 'open' and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).absolute()
            name = path.name.lower()
            open_mode = values[1] if len(values) > 1 else None
            open_flags = values[2] if len(values) > 2 else 0
            public_certificate_read = (path in public_CA_bundles and open_mode in {None, 'r', 'rb'}
                                       and type(open_flags) is int and not open_flags &
                                       (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            private_input = ((path.is_relative_to(ROOT / 'benchmark') and
                              (name == 'evaluator.json' or name.startswith('qualification-private')))
                             or (path.is_relative_to(ROOT / 'scripts') and
                                 ('evaluator' in name or name.startswith('evaluate_ap2')))
                             or name == '.env' or name.startswith('gemini-api-key')
                             or (path.suffix.lower() in {'.pem', '.key'} and not public_certificate_read and
                                 (audit_state['private_root'] is None or not path.is_relative_to(audit_state['private_root']))))
            if private_input:
                denials['private_reads_blocked'] += 1
                record_denial(output, audit_state, event, 'actor_private_evaluator_or_saved_credential_read_denied',
                              guard_roots(), path)
                raise PermissionError('actor_private_evaluator_or_saved_credential_read_denied')
        if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.bind', 'socket.sendto'}:
            if event == 'socket.getaddrinfo':
                host, port = values[0], values[1]
            else:
                address = values[1] if len(values) > 1 else None
                host, port = address[:2] if type(address) is tuple and len(address) >= 2 else (None, None)
            if event != 'socket.sendto' and host in {'127.0.0.1', '::1', 'localhost'} and port in {8001, 8002, 8003, 18791}:
                denials['allowed_owned_loopback_operations'] += 1
                return
            denials['external_network_operations_blocked'] += 1
            sock = values[0] if event != 'socket.getaddrinfo' else None
            record_denial(output, audit_state, event, 'native_actor_unowned_network_operation_denied', guard_roots(),
                          network_endpoint=(host, port, getattr(sock, 'family', None), getattr(sock, 'type', None)))
            raise PermissionError('native_actor_unowned_network_operation_denied')
        if event == 'subprocess.Popen':
            argv = values[1]
            expected = [plan['node']['executable'], '--import', str(ROOT / 'scripts/ap2_bridge_network_guard_v11.mjs'),
                        str(ROOT / 'scripts/ap2_bridge_client_v11.mjs'), '--config', str(output / 'bridge/client-config.json')]
            if (plan['policy'].get('bridge_route') and not audit_state['bridge_client_dispatched']
                    and list(argv) == expected and values[0] == expected[0]):
                audit_state['bridge_client_dispatched'] = True
                denials['allowed_allocated_bridge_client_processes'] += 1
                return
            denials['unallocated_descendant_processes_blocked'] += 1
            record_denial(output, audit_state, event, 'native_actor_unallocated_descendant_process_denied', guard_roots())
            raise PermissionError('native_actor_unallocated_descendant_process_denied')
        if event == 'os.system' or event.startswith('os.spawn'):
            denials['unallocated_descendant_processes_blocked'] += 1
            record_denial(output, audit_state, event, 'native_actor_unallocated_descendant_process_denied', guard_roots())
            raise PermissionError('native_actor_unallocated_descendant_process_denied')

    sys.addaudithook(public_only_actor)
    audit_state['expected_private_evaluator_probe'] = True
    try:
        (ROOT / 'benchmark/ap2-native-bridge-development-v11/evaluator.json').read_bytes()
    except PermissionError:
        evaluator_probe_blocked = True
    else:
        raise ValueError('native_actor_private_evaluator_probe_not_denied')
    finally:
        audit_state['expected_private_evaluator_probe'] = False
    with tempfile.TemporaryDirectory(prefix='ap2-offline-v11-private-') as temporary:
        private = Path(temporary).resolve()
        audit_state['private_root'] = private
        os.environ['TEMP_DB_DIR'] = str(private)
        os.environ['AGENT_PROVIDER_PUBLIC_KEY_PATH'] = str(private / 'agent_provider_signing_key.pub')
        os.environ['MERCHANT_SIGNING_KEY_PATH'] = str(private / 'merchant_signing_key.pem')
        previous = Path.cwd()
        (private / '.logs').mkdir()
        os.chdir(private)
        try:
            append(output / 'worker-stages.jsonl', {'stage': 'before_guarded_application_event_loop', 'utc': now()})
            return 0 if asyncio.run(asyncio.wait_for(application(output, site_packages, private, plan['case'], plan['policy']), timeout=150)) else 2
        finally:
            os.chdir(previous)
            write(output / 'actor-input-separation.json', {'private_evaluator_read_probe_blocked': evaluator_probe_blocked,
                  'denials': denials, 'provider_credentials_present': False,
                  'public_certificate_admissions_unchanged': admitted_certificates_unchanged(output),
                  'guard_diagnostic_rows': audit_state['diagnostic_rows'],
                  'guard_diagnostic_bound_reached': audit_state.get('diagnostic_bound_reached', False),
                  'scope': 'source-bound Python and Node guards, not a hostile-code OS sandbox'})
            verify_bridge_runtime(Path(plan['bridge_runtime']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'execute', '_worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--site-packages', type=Path)
    parser.add_argument('--case')
    parser.add_argument('--arm')
    parser.add_argument('--bridge-runtime', type=Path)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--matrix-manifest', type=Path, default=ROOT / 'benchmark/ap2-native-bridge-development-v11/application.json')
    args = parser.parse_args(argv)
    output = args.output.absolute()
    if args.mode == 'prepare':
        prepare(output)
        print(json.dumps({'status': 'offline_application_prepared', 'output': str(output)}))
        return 0
    site_packages = (args.site_packages or Path(json.loads(ENVIRONMENT.read_bytes())['site_packages'])).resolve()
    if args.mode == '_worker':
        try:
            return worker(output, site_packages)
        except BaseException as error:
            from ap2_public_certificate_guard_v11 import exception_frame_metadata
            write(output / 'worker-failure.json', {'error_type': type(error).__name__, 'reason': str(error)[:1000],
                                                 'frames': exception_frame_metadata(error, {
                                                     'SOURCE': SOURCE, 'SITE_PACKAGES': site_packages, 'REPOSITORY': ROOT}),
                                                 'contents_arguments_locals_headers_and_environment_retained': False,
                                                 'provider_requests': 0, 'native_qualification_established': False})
            return 3
    matrix_raw = args.matrix_manifest.read_bytes()
    need(matrix_raw == (ROOT / 'benchmark/ap2-native-bridge-development-v11/application.json').read_bytes(),
         'only_frozen_public_actor_manifest_allowed')
    matrix = json.loads(matrix_raw)
    need(matrix['schema_version'] == 'ap2-native-bridge-development-matrix/11'
         and matrix['provider_requests_allowed'] == 0, 'public_matrix_contract_required')
    case = next((row for row in matrix['cases'] if row['id'] == args.case), None)
    policy = next((row for row in matrix['arms'] if row['id'] == args.arm), None)
    need(case is not None and policy is not None, 'declared_public_case_and_arm_required')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'public-matrix-manifest.json').write_bytes(matrix_raw)
    stage_raw, source_files = source_contract()
    resources = resource_check()
    write(output / 'resource-check.json', resources)
    need(sys.platform == 'linux' and args.bridge_runtime is not None and args.node is not None,
         'native_study_requires_explicit_linux_bridge_runtime_and_node')
    from ap2_native_bridge_runtime_v11 import verify as verify_bridge_runtime, verify_outgoing_sources, NODE_VERSION
    runtime_root, node = args.bridge_runtime.resolve(), args.node.resolve()
    runtime_verification = verify_bridge_runtime(runtime_root)
    write(output / 'original-outgoing-map-source-binding.json', verify_outgoing_sources(matrix['original_outgoing_source_records']))
    node_probe = subprocess.run([str(node), '--version'], capture_output=True, check=False, timeout=10,
                               env={'PATH': str(node.parent) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    need(node_probe.returncode == 0 and node_probe.stdout.decode().strip() == NODE_VERSION,
         'explicit_pinned_node_version_required')
    node_record = {'executable': str(node), 'version': NODE_VERSION, 'executable_identity': digest(node.read_bytes())}
    write(output / 'node-runtime.json', node_record)
    write(output / 'bridge-runtime-verification.json', runtime_verification)
    environment = {key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LANG') if key in os.environ}
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    shutil.copyfile(__file__, output / 'source-runner.py')
    component_hashes = {}
    for name in OWNED_COMPONENTS:
        raw = (ROOT / name).read_bytes()
        retained = output / 'owned-source' / name
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_bytes(raw)
        component_hashes[name] = digest(raw)
    bridge_sources = {}
    for name, source in matrix['original_outgoing_source_records'].items():
        raw = (ROOT / source['retained_path']).read_bytes()
        need(digest(raw) == {key: source[key] for key in ('bytes', 'sha256')}, 'original_outgoing_source_snapshot_changed')
        retained = output / 'original-bridge-source' / name
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_bytes(raw)
        bridge_sources[name] = digest(raw)
    for name, expected in source_files.items():
        raw = (SOURCE / name).read_bytes()
        need(digest(raw) == expected, 'original_source_snapshot_changed')
        retained = output / 'original-source' / name
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_bytes(raw)
    (output / 'source-stage-manifest.json').write_bytes(stage_raw)
    write(output / 'plan.json', {'schema_version': 'ap2-native-bridge-development/11', 'created_utc': datetime.now(timezone.utc).isoformat(),
                                'provider_requests_allowed': 0, 'contract': CONTRACT, 'offline_model_call_bound': 24,
                                'public_matrix_manifest': digest(matrix_raw), 'case': case, 'policy': policy,
                                'owned_components': component_hashes,
                                'original_bridge_sources': bridge_sources, 'bridge_runtime': str(runtime_root), 'node': node_record,
                                'bridge_graph_sha256': matrix['bridge_graph_sha256'],
                                'bridge_archive_sha256': matrix['bridge_archive_sha256'],
                                'original_cards_rewritten': False, 'incoming_inverse_mapping_invented': False,
                                'scope': 'unchanged original shopper payment and OTP tools, merchant/processor/credentials apps and SDK task stores; owned prefix and offline/native TCP interventions',
                                'native_qualification_established': False, 'aggregate_task_grade': None,
                                'source_manifest_sha256': STAGE_SHA, 'worker_timeout_seconds': 180,
                                'admission': {'method': 'witness-lift-refine-shared-v2',
                                              'independent_checker': 'unchanged refinement_oracle.check_certificate',
                                              'work_budget': 100000, 'freshness_seconds': case.get('certificate_valid_for_seconds', 15),
                                              'finite_coverage_complete': False,
                                              'whole_route_non_support_inference_allowed': False}})
    if resources['status'] == 'local_memory_gate_refused':
        write(output / 'result.json', {'schema_version': 'ap2-native-bridge-development/11',
                                      'status': 'local_memory_gate_refused', 'returncode': 4,
                                      'provider_requests': 0, 'original_imports': 0,
                                      'native_qualification_established': False})
        print(json.dumps({'status': 'local_memory_gate_refused', 'output': str(output)}))
        return 4
    command = [sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), '_worker',
               '--output', str(output), '--site-packages', str(site_packages)]
    child = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    forced = []
    try:
        stdout, stderr = child.communicate(timeout=180)
        code = child.returncode
    except subprocess.TimeoutExpired:
        forced = stop_owned_descendants(child.pid)
        stdout, stderr = child.communicate(timeout=10)
        code = 124
    (output / 'stdout.txt').write_bytes(stdout[:2 * 1024 * 1024])
    (output / 'stderr.txt').write_bytes(stderr[:2 * 1024 * 1024])
    write(output / 'result.json', {'schema_version': 'ap2-native-bridge-development/11', 'returncode': code,
                                 'status': 'original_application_cell_captured' if code == 0 else 'retained_failed_or_partial_application_attempt',
                                 'provider_requests': 0, 'native_qualification_established': False, 'aggregate_task_grade': None,
                                 'forced_cleanup_pids': forced, 'actual_worker_pid': child.pid})
    print(json.dumps({'status': 'original_application_cell_captured' if code == 0 else 'retained_failed_or_partial_application_attempt',
                      'returncode': code, 'output': str(output)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
