"""Unexecuted constructed adapter checks, not original AP2/SDK evidence.

Only authored modules are loaded. Fixture source is explicitly constructed and
executed in synthetic namespaces; no staged original source is ever executed.
"""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).absolute().parents[1]
PACKAGE = "_constructed_ap2_binding_suite"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "src/interoperability")]
sys.modules[PACKAGE] = package


def load(suffix):
    name = PACKAGE + "." + suffix
    spec = importlib.util.spec_from_file_location(name, ROOT / "src/interoperability" / (suffix + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


execution = load("ap2_hp_reference_execution_v1")
capture = load("ap2_hp_passive_capture_v1")
binding = load("ap2_hp_original_binding_v1")
final = load("ap2_hp_final_asgi_binding_v1")


def run_immediate(coroutine):
    """Drive only constructed coroutines that complete on their first send.

    No event loop, socket, thread or executor is created. Any suspension is a
    fixture error rather than an instruction to schedule external work.
    """
    if type(coroutine) is not types.CoroutineType:
        raise TypeError("A constructed native coroutine is required")
    try:
        try:
            coroutine.send(None)
        except StopIteration as completed:
            return completed.value
        raise AssertionError("Constructed coroutine unexpectedly suspended")
    finally:
        coroutine.close()


class AdapterChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="constructed-ap2-binding-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()

    def constructed_module(self, text, name="_constructed_origin_check"):
        path = self.directory / (name.replace(".", "_") + ".py")
        raw = text.encode("utf-8")
        path.write_bytes(raw)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        previous = sys.modules.get(name)
        sys.modules[name] = module
        def restore_module():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        self.addCleanup(restore_module)
        # Disclosed constructed source only. This is not staged AP2 code.
        exec(compile(raw, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
        return module, path, raw

    def test_compile_only_module_check_accepts_constructed_functions_and_class_closure(self):
        module, path, raw = self.constructed_module(
            "def operation(value=True, *, mode='explicit'):\n    return value, mode\n"
            "class Container:\n    def owner(self):\n        return __class__\n")
        binding.verify_module(module, module.__name__, path, raw)

    def test_changed_callable_code_is_refused(self):
        module, path, raw = self.constructed_module("def operation(value=True):\n    return value\n")
        changed = compile("def operation(value=True):\n    return False\n", str(path), "exec", dont_inherit=True)
        replacement = next(code for code in changed.co_consts if type(code) is types.CodeType)
        module.operation.__code__ = replacement
        with self.assertRaises(binding.BindingError):
            binding.verify_module(module, module.__name__, path, raw)

    def test_positional_and_keyword_defaults_keep_json_types(self):
        for field in ("positional", "keyword", "tuple", "set", "dict_key"):
            text = "def operation(value=True, *, mode=False):\n    return value\n"
            if field == "tuple":
                text = "def operation(value=(True,)):\n    return value\n"
            elif field == "set":
                text = "def operation(value={True}):\n    return value\n"
            elif field == "dict_key":
                text = "def operation(value={True: 'value'}):\n    return value\n"
            module, path, raw = self.constructed_module(text)
            if field == "positional":
                module.operation.__defaults__ = (1,)
            elif field == "keyword":
                module.operation.__kwdefaults__ = {"mode": 0}
            elif field == "tuple":
                module.operation.__defaults__ = ((1,),)
            elif field == "set":
                module.operation.__defaults__ = ({1},)
            else:
                module.operation.__defaults__ = ({1: "value"},)
            with self.assertRaises(binding.BindingError):
                binding.verify_module(module, module.__name__, path, raw)

    def test_module_registry_file_and_spec_origin_are_required(self):
        for field in ("registry", "file", "spec"):
            module, path, raw = self.constructed_module("def operation():\n    return True\n")
            wrong = self.directory / "wrong_origin.py"
            wrong.write_bytes(raw)
            if field == "registry":
                sys.modules[module.__name__] = types.ModuleType(module.__name__)
            elif field == "file":
                module.__file__ = str(wrong)
            else:
                module.__spec__.origin = str(wrong)
            with self.assertRaises(binding.BindingError):
                binding.verify_module(module, module.__name__, path, raw)

    def test_callable_globals_and_class_closure_cannot_be_substituted(self):
        module, path, raw = self.constructed_module(
            "def operation():\n    return True\n"
            "class Container:\n    def owner(self):\n        return __class__\n")
        original = module.operation
        module.operation = types.FunctionType(original.__code__, dict(module.__dict__))
        with self.assertRaises(binding.BindingError):
            binding.verify_module(module, module.__name__, path, raw)
        module.operation = original
        method = module.Container.owner
        other = object()
        cell = (lambda: other).__closure__[0]
        module.Container.owner = types.FunctionType(method.__code__, module.__dict__, closure=(cell,))
        with self.assertRaises(binding.BindingError):
            binding.verify_module(module, module.__name__, path, raw)

    def test_unreviewed_decorator_and_default_expression_are_refused(self):
        for text in (
            "def identity(value):\n    return value\n@identity\ndef operation():\n    return True\n",
            "def operation(value=object()):\n    return value\n",
        ):
            module, path, raw = self.constructed_module(text)
            with self.assertRaises(binding.BindingError):
                binding.verify_module(module, module.__name__, path, raw)

    def test_class_behavior_cannot_gain_an_undeclared_attribute_hook(self):
        module, path, raw = self.constructed_module("class Container:\n    def owner(self):\n        return True\n")
        module.Container.__getattribute__ = lambda self, key: object.__getattribute__(self, key)
        with self.assertRaises(binding.BindingError):
            binding.verify_module(module, module.__name__, path, raw)

    def test_required_callable_membership_is_explicit(self):
        module, path, raw = self.constructed_module("def operation():\n    return True\n")
        binding.verify_module(module, module.__name__, path, raw, symbols={"operation"})
        with self.assertRaises(binding.BindingError):
            binding.verify_module(module, module.__name__, path, raw, symbols={"absent"})

    def test_json_paths_and_complete_inventory_are_bounded(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(binding.BindingError):
                binding.strict(raw)
        for name in ("../escape", "folder\\file", "C:/escape", "/escape", "folder//file"):
            with self.assertRaises(binding.BindingError):
                binding.relative(name)
        (self.directory / "one").write_bytes(b"constructed")
        expected = {"one": binding.digest(b"constructed")}
        self.assertEqual(binding.inventory(self.directory), expected)
        (self.directory / "extra").write_bytes(b"unexpected")
        self.assertNotEqual(binding.inventory(self.directory), expected)
        with self.assertRaises(binding.BindingError):
            binding.regular(Path("relative-file"))

    def test_unfrozen_manifest_is_refused_without_original_execution(self):
        stage, environment = self.directory / "stage.json", self.directory / "environment.json"
        stage.write_bytes(b"{}")
        environment.write_bytes(b"{}")
        with self.assertRaises(binding.BindingError):
            binding.validate_inputs(self.directory, stage, environment)

    def caller_fixture(self):
        """Synthetic module/constructor bindings; native source checks mocked."""
        modules = {name: types.ModuleType(name) for name in binding.SOURCE_MODULES}
        class ConstructedClient:
            def __init__(self, name, endpoint):
                self._httpx_client, self._a2a_client_factory = object(), object()
                self._name, self._base_url, self._agent_card = name, endpoint, None
                self._client_required_extensions = {execution.EXTENSION}
        class ConstructedBuilder:
            pass
        client_module = modules["common.payment_remote_a2a_client"]
        client_module.PaymentRemoteA2aClient, client_module.DEFAULT_TIMEOUT = ConstructedClient, 600.0
        modules["common.a2a_message_builder"].A2aMessageBuilder = ConstructedBuilder
        modules["common.a2a_extension_utils"].EXTENSION_URI = execution.EXTENSION
        constants = modules["common.constants"]
        constants.__dict__.update({"TEMP_DB": self.directory,
            "AGENT_PROVIDER_KEY_PATH": self.directory / "agent_provider_signing_key.pem",
            "AGENT_PROVIDER_PUB_PATH": self.directory / "agent_provider_signing_key.pub",
            "PAYMENT_MANDATE_SD_JWT_KEY": execution.PAYMENT,
            "CHECKOUT_MANDATE_SD_JWT_KEY": execution.CHECKOUT,
            "PAYMENT_RECEIPT_DATA_KEY": "ap2.PaymentReceipt", "DEFAULT_MANDATE_TTL_SECONDS": 3600})
        artifact = modules["common.artifact_utils"]
        artifact.find_canonical_objects = object()
        merchant = ConstructedClient("merchant_agent", execution.MERCHANT)
        credentials = ConstructedClient("credentials_provider", execution.CREDENTIALS)
        clients = {"merchant_agent_client": merchant, "credentials_provider_client": credentials}
        for name, keys in binding.CLIENT_ALIASES.items():
            namespace = modules[name].__dict__
            namespace.update({key: clients[key] for key in keys})
            if name.endswith("remote_agents"):
                namespace.update({"PaymentRemoteA2aClient": ConstructedClient, "EXTENSION_URI": execution.EXTENSION})
            else:
                namespace["A2aMessageBuilder"] = ConstructedBuilder
                namespace["artifact_utils"] = artifact
                namespace["find_canonical_objects"] = artifact.find_canonical_objects
        tools = modules["roles.shopping_agent.tools"].__dict__
        tools.update({key: value for key, value in constants.__dict__.items() if key.isupper()})
        for module in modules.values():
            for key in ("find_products", "select_cart", "get_shipping_address", "get_payment_methods",
                        "get_payment_credential_token", "create_checkout", "create_checkout_mandate",
                        "create_payment_mandate", "send_signed_mandates_to_credentials_provider", "_store_receipt_if_present"):
                module.__dict__[key] = object()
        source = binding.SourceBinding(self.directory, self.directory, self.directory / "stage",
            self.directory / "environment", b"", b"", {}, {})
        return source, modules, clients

    def mocked_source_checks(self):
        stack = ExitStack()
        stack.enter_context(patch.object(binding.SourceBinding, "verify_unchanged", return_value=True))
        stack.enter_context(patch.object(binding.SourceBinding, "source_module", side_effect=lambda name, suffix, module: module))
        stack.enter_context(patch.object(binding.SourceBinding, "environment_module", side_effect=lambda name, suffix, module, **kwargs: module))
        return stack

    def test_exact_seven_aliases_restore_only_owned_proxies(self):
        source, modules, originals = self.caller_fixture()
        with self.mocked_source_checks():
            lease = binding.make_caller_binding(source, modules, temporary_root=self.directory).install()
        self.assertTrue(lease.installed)
        self.assertIsNone(lease.error)
        self.assertEqual(len(lease.slots), 7)
        for namespace, key, original, proxy in lease.slots:
            self.assertIs(original, originals[key])
            self.assertIs(namespace[key], proxy)
        self.assertTrue(lease.restore())
        self.assertTrue(lease.restore())
        for namespace, key, original, proxy in lease.slots:
            self.assertIs(namespace[key], original)
        with self.assertRaises(binding.BindingError):
            lease.install()

    def test_same_alias_count_with_wrong_placement_is_refused(self):
        source, modules, originals = self.caller_fixture()
        del modules["roles.shopping_agent.subagents.shopper.tools"].merchant_agent_client
        modules["common.constants"].merchant_agent_client = originals["merchant_agent_client"]
        with self.mocked_source_checks(), self.assertRaises(binding.BindingError):
            binding.make_caller_binding(source, modules, temporary_root=self.directory)

    def test_client_type_is_checked_before_arbitrary_attribute_behavior(self):
        source, modules, originals = self.caller_fixture()
        class Opaque:
            def __getattribute__(self, key):
                raise AssertionError("Unexpected constructed attribute read")
        modules["roles.shopping_agent.remote_agents"].merchant_agent_client = Opaque()
        with self.mocked_source_checks(), self.assertRaises(binding.BindingError):
            binding.make_caller_binding(source, modules, temporary_root=self.directory)

    def test_signing_root_and_required_builder_alias_are_explicit(self):
        for field in ("root", "builder"):
            source, modules, originals = self.caller_fixture()
            if field == "root":
                modules["common.constants"].AGENT_PROVIDER_KEY_PATH = self.directory / "other.pem"
            else:
                del modules["roles.shopping_agent.subagents.shopper.tools"].A2aMessageBuilder
            with self.mocked_source_checks(), self.assertRaises((binding.BindingError, KeyError)):
                binding.make_caller_binding(source, modules, temporary_root=self.directory)

    def test_preinstall_revalidates_original_constants_and_callables(self):
        for field in ("constant", "callable", "client"):
            source, modules, originals = self.caller_fixture()
            with self.mocked_source_checks():
                lease = binding.make_caller_binding(source, modules, temporary_root=self.directory)
                if field == "constant":
                    modules["common.constants"].DEFAULT_MANDATE_TTL_SECONDS = 1
                elif field == "callable":
                    modules["roles.shopping_agent.tools"].create_checkout = object()
                else:
                    originals["merchant_agent_client"]._agent_card = object()
                lease.install()
            self.assertFalse(lease.installed)
            self.assertIsNotNone(lease.error)
            self.assertTrue(lease.restored)

    def test_active_calls_and_alias_interference_retain_restoration_authority(self):
        source, modules, originals = self.caller_fixture()
        with self.mocked_source_checks():
            lease = binding.make_caller_binding(source, modules, temporary_root=self.directory).install()
        lease.bindings.merchant.active_calls = 1
        self.assertFalse(lease.restore())
        self.assertTrue(all(namespace[key] is proxy for namespace, key, original, proxy in lease.slots))
        lease.bindings.merchant.active_calls = 0
        namespace, key, original, proxy = lease.slots[0]
        interference = object()
        namespace[key] = interference
        self.assertFalse(lease.restore())
        self.assertIs(namespace[key], interference)
        self.assertTrue(lease.report()["restoration_authority_retained"])
        namespace[key] = proxy
        self.assertTrue(lease.restore())

    def test_observed_client_return_error_identity_and_active_lifetime(self):
        returned, failure = {"constructed": True}, RuntimeError("constructed original client failure")
        class Client:
            async def send_a2a_message(self, message):
                self.assert_active()
                if message.get("fail"):
                    raise failure
                return returned
        client = Client()
        observer = binding.OwnedPublicObserver(client, execution.MERCHANT)
        client.assert_active = lambda: self.assertEqual(observer.active_calls, 1)
        self.assertIs(run_immediate(observer.send_a2a_message({"fail": False})), returned)
        self.assertEqual(observer.active_calls, 0)
        with self.assertRaises(RuntimeError) as caught:
            run_immediate(observer.send_a2a_message({"fail": True}))
        self.assertIs(caught.exception, failure)
        self.assertEqual(observer.active_calls, 0)

    def final_fixture(self, original_run):
        server, path, raw = self.constructed_module(
            "def run_agent_blocking(port, supplied):\n"
            "    app = build(supplied)\n"
            "    add_middlewares(app)\n"
            "    return uvicorn.run(app, host='127.0.0.1', port=port, log_level='info', timeout_keep_alive=120)\n",
            name="_constructed_final_app")
        server.build = lambda supplied: supplied
        server.add_middlewares = lambda app: app.middlewares.append("constructed_original_middleware")
        uvicorn, main = types.ModuleType("_constructed_uvicorn"), types.ModuleType("_constructed_uvicorn_main")
        uvicorn.run, main.run = original_run, original_run
        uvicorn.marker = object()
        server.uvicorn = uvicorn
        source = binding.SourceBinding(self.directory, self.directory, self.directory / "stage",
            self.directory / "environment", b"", b"", {}, {})
        with self.mocked_source_checks():
            lease = final.make_final_app_binding(source, server, uvicorn, main, role="merchant").install()
        self.assertTrue(lease.installed)
        self.assertIsNone(lease.error)
        return server, uvicorn, main, lease

    def test_final_placement_preserves_original_result_after_middleware(self):
        returned, observed = object(), []
        def run(app, **kwargs):
            observed.append(app)
            self.assertEqual(app.app.middlewares, ["constructed_original_middleware"])
            self.assertEqual(kwargs, {"host": "127.0.0.1", "port": 8001, "log_level": "info", "timeout_keep_alive": 120})
            self.assertEqual(lease.proxy.active_runs, 1)
            self.assertFalse(lease.restore())
            return returned
        server, uvicorn, main, lease = self.final_fixture(run)
        app = types.SimpleNamespace(middlewares=[])
        self.assertIs(server.run_agent_blocking(8001, app), returned)
        self.assertIs(observed[0].app, app)
        self.assertIs(lease.proxy.marker, uvicorn.marker)
        self.assertEqual(lease.proxy.active_runs, 0)
        self.assertTrue(lease.restore())
        self.assertIs(server.uvicorn, uvicorn)

    def test_final_original_exception_and_failed_observation_preserve_identity(self):
        failure = RuntimeError("constructed original Uvicorn failure")
        def fail(app, **kwargs):
            raise failure
        server, uvicorn, main, lease = self.final_fixture(fail)
        with self.assertRaises(RuntimeError) as caught:
            server.run_agent_blocking(8001, types.SimpleNamespace(middlewares=[]))
        self.assertIs(caught.exception, failure)
        self.assertEqual(lease.proxy.active_runs, 0)
        self.assertTrue(lease.restore())
        returned, received = object(), []
        def run(app, **kwargs):
            received.append(app)
            return returned
        server, uvicorn, main, lease = self.final_fixture(run)
        app = types.SimpleNamespace(middlewares=[])
        with patch.object(final, "PassiveAsgiCapture", side_effect=OSError("constructed observer failure")):
            self.assertIs(server.run_agent_blocking(8001, app), returned)
        self.assertIs(received[0], app)
        self.assertEqual(lease.report()["placement_observation_errors"], [{"error_type": "OSError"}])
        self.assertTrue(lease.restore())

    def test_final_wrong_frame_globals_port_and_repeat_are_refused(self):
        for case in ("direct", "globals", "port", "repeat"):
            server, uvicorn, main, lease = self.final_fixture(lambda app, **kwargs: None)
            app = types.SimpleNamespace(middlewares=[])
            with self.assertRaises(binding.BindingError):
                if case == "direct":
                    lease.proxy.run(app, host="127.0.0.1", port=8001, log_level="info", timeout_keep_alive=120)
                elif case == "globals":
                    counterfeit = types.FunctionType(server.run_agent_blocking.__code__, dict(server.__dict__))
                    counterfeit(8001, app)
                elif case == "port":
                    server.run_agent_blocking(True, app)
                else:
                    server.run_agent_blocking(8001, app)
                    server.run_agent_blocking(8001, app)
            self.assertTrue(lease.restore())

    def test_final_source_guard_run_alias_and_restore_interference_are_explicit(self):
        with self.assertRaises(binding.BindingError):
            final.make_final_app_binding(object(), object(), object(), object(), role="merchant")
        server, uvicorn, main, lease = self.final_fixture(lambda app, **kwargs: None)
        interference = object()
        server.uvicorn = interference
        self.assertFalse(lease.restore())
        self.assertIs(server.uvicorn, interference)
        self.assertTrue(lease.report()["restoration_authority_retained"])
        server.uvicorn = lease.proxy
        self.assertTrue(lease.restore())
        with self.mocked_source_checks():
            replacement = final.make_final_app_binding(lease.source, server, uvicorn, main, role="merchant")
            main.run = object()
            replacement.install()
        self.assertFalse(replacement.installed)
        self.assertIsNotNone(replacement.error)

    def test_final_wrapper_forwards_lifespan_and_http_event_objects(self):
        scope, request, response, delivered = {"type": "http"}, {"type": "http.request", "body": b"raw"}, {"type": "http.response.body", "body": b"done"}, []
        async def app(actual_scope, receive, send):
            self.assertIs(actual_scope, scope)
            self.assertIs(await receive(), request)
            await send(response)
        async def receive():
            return request
        async def send(event):
            delivered.append(event)
        wrapper = capture.PassiveAsgiCapture(app)
        run_immediate(wrapper(scope, receive, send))
        self.assertIs(delivered[0], response)
        forwarded = []
        async def lifespan(actual_scope, actual_receive, actual_send):
            forwarded.append((actual_scope, actual_receive, actual_send))
        life_scope = {"type": "lifespan"}
        wrapper = capture.PassiveAsgiCapture(lifespan)
        run_immediate(wrapper(life_scope, receive, send))
        self.assertIs(forwarded[0][0], life_scope)
        self.assertIs(forwarded[0][1], receive)
        self.assertIs(forwarded[0][2], send)
        self.assertEqual(wrapper.records, [])
        class Suspension:
            def __await__(self):
                yield "constructed suspension"
        async def suspended():
            await Suspension()
        coroutine = suspended()
        with self.assertRaises(AssertionError):
            run_immediate(coroutine)
        self.assertIsNone(coroutine.cr_frame)


if __name__ == "__main__":
    unittest.main(verbosity=2)
