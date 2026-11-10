"""Fresh-cell original AP2 ADK shopper/root conversation development capture.

This executes original modules and SDK handlers. It is development integration,
not native TCP, live-provider, human-gold or aggregate task qualification.
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
import subprocess
import sys
import tempfile
import time
from types import CodeType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
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
OWNED_COMPONENTS = ('scripts/ap2_reference_development_v7.py', 'src/interoperability/__init__.py', 'src/interoperability/ap2_hp_original_binding_v1.py', 'src/interoperability/ap2_hp_reference_execution_v1.py', 'src/interoperability/ap2_hp_reference_plan_v1.py', 'src/interoperability/ap2_hp_durable_observer_v1.py', 'src/interoperability/ap2_original_shopper_fixture_v7.py', 'src/interoperability/ap2_original_shopper_conversation_v7.py', 'benchmark/ap2-shopper-development-v7/application.json', 'benchmark/tasks-v1/ap2/application.json')


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
        'schema_version': 'ap2-application-development/7', 'status': 'offline_application_prepared',
        'source_manifest': digest(stage_raw), 'original_ap2_file_count': len(files),
        'version_source_manifest': digest(raw), 'requirements': requirements,
        'compiled_windows_wheel_hashes_apply_to_linux': False, 'provider_requests_allowed': 0,
        'scope': 'full original apps and caller; offline model fixtures and ASGI in-process transport',
        'native_qualification_established': False, 'aggregate_task_grade': None,
    })


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
    sys.path[:0] = [str(ROOT / 'src'), str(SOURCE / 'code/samples/python/src'),
                    str(SOURCE / 'code/sdk/python'), str(STAGE.parent / 'a2a-x402/python/x402_a2a/src'),
                    str(site_packages)]
    mandate_module = importlib.import_module('ap2.sdk.mandate')
    original_log_path = mandate_module.LOG_FILE_PATH
    mandate_module.LOG_FILE_PATH = str(private / '.logs/mandate_operations.log')
    # Schema construction sees the original GenAI class; only subsequent model clients are fixtures.
    importlib.import_module('google.adk.tools.tool_context')
    import httpx
    from google import genai
    from interoperability import ap2_hp_durable_observer_v1 as durable
    from interoperability import ap2_hp_original_binding_v1 as binding
    from interoperability import ap2_hp_reference_execution_v1 as execution
    from interoperability.ap2_hp_reference_execution_v1 import ReferenceCoordinator
    from interoperability import ap2_hp_reference_plan_v1 as planner
    from interoperability.ap2_original_shopper_conversation_v7 import OriginalShopperConversation
    from a2a.types import TaskState
    from pydantic import BaseModel
    ContactAddress = importlib.import_module('ap2.models.contact_picker').ContactAddress
    original_public_json = execution.public_json

    def coordinator_public_json(value):
        # Compare the original returned address's explicit fields to the raw
        # DataPart. Defaults inserted by its original model are retained separately.
        return recursive_public_json(value, model_base=BaseModel, explicitly_set_model=ContactAddress)

    def retain_public_json(value):
        return recursive_public_json(value, model_base=BaseModel)

    stage_raw, source_files = source_contract()
    runtime_files = inventory(site_packages)
    runtime = {'schema_version': 'ap2-offline-application-runtime/7', 'root': str(site_packages),
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
    recorder = durable.DurableRecorder.allocate(output / 'observations', {
        'merchant_raw': 'raw_asgi', 'credentials_raw': 'raw_asgi', 'processor_raw': 'raw_asgi',
        'merchant_public': 'public', 'credentials_public': 'public',
    })
    lease = outcome = None
    transport_rows = []
    restored = True

    class LocalTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            need(request.url.scheme == 'http' and request.url.host in {'localhost', '127.0.0.1'}
                 and request.url.port in transports, 'external_transport_refused')
            need('authorization' not in request.headers and 'x-goog-api-key' not in request.headers,
                 'secret_transport_header_refused')
            transport_rows.append({'index': len(transport_rows), 'method': request.method,
                                   'url': str(request.url), 'transport': 'owned_httpx_ASGITransport',
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
            routes = [route for route in app.routes if getattr(route, 'path', None) == rpc]
            need(len(routes) == 1, 'one_original_rpc_route_required')
            original_application = routes[0].endpoint.__self__
            task_stores[role] = original_application.handler.request_handler.task_store
            need(type(task_stores[role]).__module__ == 'a2a.server.tasks.inmemory_task_store'
                 and type(task_stores[role]).__name__ == 'InMemoryTaskStore'
                 and task_stores[role].tasks == {}, 'actual_original_task_store_not_fresh')
            server._add_middlewares(app, logging.getLogger('ap2.offline.' + role))
            wrappers[role] = durable.RawAsgiCapture(app, recorder.sink(role + '_raw'))
            transports[port] = httpx.ASGITransport(app=wrappers[role])
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
            'private_signing_key_files': len(list(private.glob('*.pem'))),
            'provider_credentials_present': False})
        execution.public_json = coordinator_public_json
        wire_plan = make_wire_reference_plan(planner, TaskState.input_required.value)
        public_manifest = json.loads((output / 'public-matrix-manifest.json').read_bytes())
        coordinator = OriginalShopperConversation(lease.bindings, wire_plan, CONTRACT,
            output=output, case=case, manifest=public_manifest, writer=write, serializer=retain_public_json,
            source_binding=source_binding, fingerprint=code_fingerprint)
        outcome = await coordinator.run()
        write(output / 'original-state-after.json', {
            'merchant_store': retain_public_json(merchant_storage._store),
            'credential_tokens': retain_public_json(credential_storage._token),
            'task_stores': {role: {'class': type(store).__module__ + '.' + type(store).__qualname__,
                                 'tasks': [retain_public_json(task) for task in store.tasks.values()]}
                            for role, store in task_stores.items()},
            'private_signing_key_files': len(list(private.glob('*.pem'))),
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
            restored = lease.restore()
        for client in clients:
            await client.aclose()
        for transport in transports.values():
            await transport.aclose()
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
                                      'source_tree_unchanged': source_contract()[1] == source_files})
    return outcome is not None and recorder.report()['published_complete'] is True


def worker(output, site_packages):
    need(not any(os.environ.get(name) for name in SECRET_NAMES), 'credential_free_worker_required')
    plan = json.loads((output / 'plan.json').read_bytes())
    for name, expected in plan['owned_components'].items():
        need(digest((ROOT / name).read_bytes()) == expected, 'prospective_owned_source_component_changed')
        need(digest((output / 'owned-source' / name).read_bytes()) == expected, 'retained_owned_source_component_changed')
    denials = {'private_reads_blocked': 0, 'external_network_operations_blocked': 0,
               'descendant_processes_blocked': 0, 'windows_loop_constructor_loopback_events': 0}
    audit_state = {'original_application_started': False}
    def public_only_actor(event, values):
        if event == 'open' and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).absolute()
            name = path.name.lower()
            private_input = ((path.is_relative_to(ROOT / 'benchmark') and
                              (name == 'evaluator.json' or name.startswith('qualification-private')))
                             or (path.is_relative_to(ROOT / 'scripts') and
                                 ('evaluator' in name or name.startswith('evaluate_ap2')))
                             or name == '.env' or name.startswith('gemini-api-key'))
            if private_input:
                denials['private_reads_blocked'] += 1
                raise PermissionError('actor_private_evaluator_or_saved_credential_read_denied')
        if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'}:
            if os.name == 'nt' and not audit_state['original_application_started'] and event == 'socket.connect':
                address = values[1] if len(values) > 1 else None
                if type(address) is tuple and address[0] == '127.0.0.1':
                    denials['windows_loop_constructor_loopback_events'] += 1
                    return
            denials['external_network_operations_blocked'] += 1
            raise PermissionError('original_adk_offline_actor_external_network_denied')
        if event == 'subprocess.Popen' or event == 'os.system' or event.startswith('os.spawn'):
            denials['descendant_processes_blocked'] += 1
            raise PermissionError('original_adk_actor_descendant_process_denied')
    sys.addaudithook(public_only_actor)
    try:
        (ROOT / 'benchmark/tasks-v1/ap2/evaluator.json').read_bytes()
    except PermissionError:
        evaluator_probe_blocked = True
    else:
        raise ValueError('actor_private_evaluator_probe_not_denied')
    with tempfile.TemporaryDirectory(prefix='ap2-offline-v7-private-') as temporary:
        private = Path(temporary).resolve()
        os.environ['TEMP_DB_DIR'] = str(private)
        os.environ['AGENT_PROVIDER_PUBLIC_KEY_PATH'] = str(private / 'agent_provider_signing_key.pub')
        os.environ['MERCHANT_SIGNING_KEY_PATH'] = str(private / 'merchant_signing_key.pem')
        previous = Path.cwd()
        (private / '.logs').mkdir()
        os.chdir(private)
        try:
            async def run_original():
                audit_state['original_application_started'] = True
                return await application(output, site_packages, private, plan['case'], plan['policy'])
            return 0 if asyncio.run(asyncio.wait_for(run_original(), timeout=150)) else 2
        finally:
            os.chdir(previous)
            write(output / 'actor-input-separation.json', {'private_evaluator_read_probe_blocked': evaluator_probe_blocked,
                  'denials': denials, 'provider_credentials_present': False,
                  'scope': 'Python audit and source-bound process controls, not a hostile-code OS sandbox'})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'execute', '_worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--site-packages', type=Path)
    parser.add_argument('--case')
    parser.add_argument('--arm')
    parser.add_argument('--matrix-manifest', type=Path, default=ROOT / 'benchmark/ap2-shopper-development-v7/application.json')
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
            write(output / 'worker-failure.json', {'error_type': type(error).__name__, 'reason': str(error)[:1000],
                                                 'provider_requests': 0, 'native_qualification_established': False})
            return 3
    matrix_raw = args.matrix_manifest.read_bytes()
    need(matrix_raw == (ROOT / 'benchmark/ap2-shopper-development-v7/application.json').read_bytes(),
         'only_frozen_public_actor_manifest_allowed')
    matrix = json.loads(matrix_raw)
    need(matrix['schema_version'] == 'ap2-original-adk-bank-feasibility/7'
         and matrix['provider_requests_allowed'] == 0, 'public_matrix_contract_required')
    case = next((row for row in matrix['records'] if row['id'] == args.case), None)
    policy = {'id': 'original_adk', 'declared_provider_requests': 0}
    need(case is not None and case['execution_mode'] == 'original_adk_conversation', 'declared_original_adk_candidate_required')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'public-matrix-manifest.json').write_bytes(matrix_raw)
    stage_raw, source_files = source_contract()
    resources = resource_check()
    write(output / 'resource-check.json', resources)
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
    for name, expected in source_files.items():
        raw = (SOURCE / name).read_bytes()
        need(digest(raw) == expected, 'original_source_snapshot_changed')
        retained = output / 'original-source' / name
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_bytes(raw)
    (output / 'source-stage-manifest.json').write_bytes(stage_raw)
    write(output / 'plan.json', {'schema_version': 'ap2-application-development/7', 'created_utc': datetime.now(timezone.utc).isoformat(),
                                'provider_requests_allowed': 0, 'contract': CONTRACT, 'offline_model_call_bound': 24,
                                'public_matrix_manifest': digest(matrix_raw), 'case': case, 'policy': policy,
                                'owned_components': component_hashes,
                                'scope': 'official original ADK root/subagents, original tools and task stores; deterministic registered model/human fixtures and offline/ASGI interventions',
                                'native_qualification_established': False, 'aggregate_task_grade': None,
                                'source_manifest_sha256': STAGE_SHA, 'worker_timeout_seconds': 180,
                                'original_adk': {'original_root_and_subagents': True,
                                                 'registered_model_fixture': 'deterministic BaseLlm',
                                                 'human_fixture': 'replies only to actual ADK user-facing questions',
                                                 'candidate_denominator': 34,
                                                 'model_call_bound': matrix['actor_model_call_bound']}})
    if resources['status'] == 'local_memory_gate_refused':
        write(output / 'result.json', {'schema_version': 'ap2-application-development/7',
                                      'status': 'local_memory_gate_refused', 'returncode': 4,
                                      'provider_requests': 0, 'original_imports': 0,
                                      'native_qualification_established': False})
        print(json.dumps({'status': 'local_memory_gate_refused', 'output': str(output)}))
        return 4
    command = [sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), '_worker',
               '--output', str(output), '--site-packages', str(site_packages)]
    try:
        completed = subprocess.run(command, env=environment, capture_output=True, timeout=180, check=False)
        (output / 'stdout.txt').write_bytes(completed.stdout[:2 * 1024 * 1024])
        (output / 'stderr.txt').write_bytes(completed.stderr[:2 * 1024 * 1024])
        code = completed.returncode
    except subprocess.TimeoutExpired:
        code = 124
    write(output / 'result.json', {'schema_version': 'ap2-application-development/7', 'returncode': code,
                                 'status': 'original_application_cell_captured' if code == 0 else 'retained_failed_or_partial_application_attempt',
                                 'provider_requests': 0, 'native_qualification_established': False, 'aggregate_task_grade': None})
    print(json.dumps({'status': 'original_application_cell_captured' if code == 0 else 'retained_failed_or_partial_application_attempt',
                      'returncode': code, 'output': str(output)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
