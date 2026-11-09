"""Unexecuted constructed ownership checks; no original SDK/source imports."""
from __future__ import annotations

import contextlib
import functools
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
PACKAGE = "_constructed_ap2_server_owner_suite"
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


load("ap2_hp_reference_execution_v1")
load("ap2_hp_passive_capture_v1")
binding = load("ap2_hp_original_binding_v1")
final = load("ap2_hp_final_asgi_binding_v1")
owner = load("ap2_hp_original_server_owner_v1")


class OwnerChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="constructed-ap2-server-owner-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.leases = []
        self.addCleanup(self.retain_artifacts)

    def retain_artifacts(self):
        configured = os.environ.get("AP2_HP_SERVER_OWNER_ARTIFACTS")
        if configured:
            destination = Path(configured) / self._testMethodName
            if destination.resolve().is_relative_to(self.directory) or self.directory.is_relative_to(destination.resolve()):
                raise ValueError("Constructed retained output overlaps its fixture")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.directory, destination)
            with (destination / "constructed-owner-reports.json").open("x", encoding="utf-8") as out:
                json.dump({"synthetic_only": True, "reports": [lease.report() for lease in self.leases]},
                          out, sort_keys=True, indent=2, allow_nan=False)
                out.write("\n")

    def module(self, text, name="_constructed_runtime_class", supplied=None):
        path = self.directory / (name + ".py")
        raw = text.encode()
        path.write_bytes(raw)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        prior = sys.modules.get(name)
        sys.modules[name] = module
        def restore():
            if prior is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prior
        self.addCleanup(restore)
        module.__dict__.update(supplied or {})
        # This explicitly executes authored fixture strings, never staged code.
        exec(compile(raw, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
        return module, path, raw

    def descriptor_fixture(self):
        return self.module(
            "class Runtime:\n"
            "    def __init__(self, value=(True,)):\n        self.value = value\n"
            "    @property\n    def readonly(self):\n        return True\n"
            "    @functools.cached_property\n    def cached(self):\n        return None\n"
            "    @contextlib.contextmanager\n    def signals(self):\n        yield None\n",
            supplied={"functools": functools, "contextlib": contextlib})

    def test_compile_only_property_cached_property_and_contextmanager_are_accepted(self):
        module, path, raw = self.descriptor_fixture()
        self.assertIs(owner.verify_class(module, module.__name__, path, raw, "Runtime"), module.Runtime)

    def test_descriptor_replacements_and_wrapped_closure_drift_are_refused(self):
        for kind in ("property", "cached", "wrapped", "default"):
            module, path, raw = self.descriptor_fixture()
            if kind == "property":
                module.Runtime.readonly = property(lambda instance: True)
            elif kind == "cached":
                module.Runtime.__dict__["cached"].func = lambda instance: None
            elif kind == "wrapped":
                actual = module.Runtime.__dict__["signals"]
                original = actual.__wrapped__
                actual.__wrapped__ = types.FunctionType(original.__code__, module.__dict__)
            else:
                module.Runtime.__init__.__defaults__ = ((1,),)
            with self.assertRaises(binding.BindingError):
                owner.verify_class(module, module.__name__, path, raw, "Runtime")

    def test_unreviewed_decorators_and_class_hooks_are_refused(self):
        module, path, raw = self.module("class Runtime:\n    @staticmethod\n    def operation():\n        return True\n")
        with self.assertRaises(binding.BindingError):
            owner.verify_class(module, module.__name__, path, raw, "Runtime")
        module, path, raw = self.descriptor_fixture()
        module.Runtime.__getattribute__ = lambda instance, key: object.__getattribute__(instance, key)
        with self.assertRaises(binding.BindingError):
            owner.verify_class(module, module.__name__, path, raw, "Runtime")

    def fixture(self, callback, *, constructor_error=None, malformed_flags=None, altered_config=None, install=True):
        """Ownership behavior only: original source/class checks are mocked."""
        class Config:
            def __init__(self, app, **kwargs):
                self.app = app
                self.__dict__.update({"reload": False, "workers": 1, "uds": None, "fd": None, "factory": False})
                self.__dict__.update(kwargs)
                if altered_config:
                    self.__dict__.update(altered_config)
        class ServerState:
            pass
        class Server:
            def __init__(self, *, config):
                if constructor_error is not None:
                    raise constructor_error
                self.config, self.started, self.should_exit, self.force_exit = config, False, False, False
                if malformed_flags:
                    self.__dict__.update(malformed_flags)
            @functools.cached_property
            def limit_max_requests(self):
                return None
            def run(self):
                self.started = True
                self.limit_max_requests
                return callback(self)
        main, _, _ = self.module(
            "def run(app, **kwargs):\n    config = Config(app, **kwargs)\n    server = Server(config=config)\n    return server.run()\n",
            name="_constructed_uvicorn_run", supplied={"Config": Config, "Server": Server})
        config_module, server_module, uvicorn = (types.ModuleType(name) for name in
                                               ("_constructed_config", "_constructed_server", "_constructed_uvicorn"))
        config_module.Config = Config
        server_module.Config, server_module.Server, server_module.ServerState = Config, Server, ServerState
        uvicorn.run, uvicorn.Config, uvicorn.Server = main.run, Config, Server
        caller, _, _ = self.module(
            "def run_agent_blocking(port, supplied):\n    app = supplied\n    return uvicorn.run(app, host='127.0.0.1', port=port, log_level='info', timeout_keep_alive=120)\n",
            name="_constructed_final_caller", supplied={"uvicorn": uvicorn})
        source = binding.SourceBinding(self.directory, self.directory, self.directory / "stage", self.directory / "environment",
                                       b"", b"", {}, {})
        proxy = final.FinalAppUvicornProxy(uvicorn, main.run, caller.run_agent_blocking.__code__, caller.__dict__, 8001, None)
        final_lease = final.FinalAppBindingLease(source, caller, uvicorn, main, proxy, installed=True)
        caller.uvicorn = proxy
        classes = {"Config": Config, "Server": Server, "ServerState": ServerState}
        self.enterContext(patch.object(owner, "runtime_classes", return_value=classes))
        lease = owner.make_original_server_owner(source, final_lease, main, config_module, server_module)
        self.leases.append(lease)
        if install:
            lease.install()
            self.assertTrue(lease.installed)
            self.assertIsNone(lease.error)
        return caller, main, lease

    def test_original_instance_config_and_return_identity_are_retained(self):
        returned, observed = object(), []
        def callback(server):
            observed.append(server)
            self.assertIs(lease.server, server)
            self.assertIs(server.config, lease.config)
            self.assertIs(lease.capture.app, app)
            self.assertFalse(lease.restore())
            self.assertTrue(lease.request_graceful_stop())
            self.assertTrue(server.should_exit)
            self.assertFalse(server.force_exit)
            return returned
        caller, main, lease = self.fixture(callback)
        app = object()
        self.assertIs(caller.run_agent_blocking(8001, app), returned)
        self.assertIs(lease.server, observed[0])
        self.assertTrue(lease.report()["delegated_run_inactive_observed"])
        self.assertTrue(lease.restore())
        self.assertIs(main.Server, lease.classes["Server"])
        self.assertTrue(lease.final.restore())

    def test_original_run_error_is_preserved_and_inactive_restore_is_allowed(self):
        failure = RuntimeError("constructed original run failure")
        def callback(server):
            raise failure
        caller, main, lease = self.fixture(callback)
        with self.assertRaises(RuntimeError) as caught:
            caller.run_agent_blocking(8001, object())
        self.assertIs(caught.exception, failure)
        self.assertFalse(lease.server.should_exit)
        self.assertTrue(lease.restore())
        self.assertFalse(lease.report()["graceful_shutdown_proven"])

    def test_original_constructor_error_is_preserved_without_replacement_server(self):
        failure = RuntimeError("constructed original constructor failure")
        caller, main, lease = self.fixture(lambda server: None, constructor_error=failure)
        with self.assertRaises(RuntimeError) as caught:
            caller.run_agent_blocking(8001, object())
        self.assertIs(caught.exception, failure)
        self.assertIs(lease.construction_error, failure)
        self.assertIsNone(lease.server)
        self.assertEqual(lease.attempts, 1)
        self.assertFalse(lease.constructing)
        self.assertTrue(lease.restore())

    def test_direct_factory_and_counterfeit_run_globals_are_refused(self):
        caller, main, lease = self.fixture(lambda server: None)
        config = lease.classes["Config"](object())
        with self.assertRaises(binding.BindingError):
            lease.factory(config=config)
        counterfeit = types.FunctionType(main.run.__code__, dict(main.__dict__))
        with self.assertRaises(binding.BindingError):
            counterfeit(object())
        self.assertEqual(lease.attempts, 0)
        self.assertTrue(lease.restore())

    def test_malformed_returned_original_server_is_retained_without_run_or_stop(self):
        runs = []
        caller, main, lease = self.fixture(lambda server: runs.append(server), malformed_flags={"started": True})
        with self.assertRaises(binding.BindingError) as caught:
            caller.run_agent_blocking(8001, object())
        self.assertIs(lease.construction_error, caught.exception)
        self.assertIs(lease.error, caught.exception)
        self.assertIs(type(lease.server), lease.classes["Server"])
        self.assertIs(lease.server.config, lease.config)
        self.assertIs(lease.config.app, lease.capture)
        self.assertEqual(runs, [])
        self.assertFalse(lease.server.should_exit)
        # Even an apparently active final run cannot promote contrary state.
        lease.final.proxy.active_runs = 1
        self.assertFalse(lease.request_graceful_stop())
        self.assertFalse(lease.server.should_exit)
        self.assertFalse(lease.restore())
        lease.final.proxy.active_runs = 0
        self.assertTrue(lease.restore())
        report = lease.report()
        self.assertTrue(report["original_server_retained"])
        for flag in ("alternate_server_constructed", "force_exit_requested", "graceful_shutdown_proven", "native_qualification_established"):
            self.assertFalse(report[flag])

    def test_typed_config_and_preinstall_alias_drift_are_refused(self):
        caller, main, lease = self.fixture(lambda server: None, altered_config={"workers": True})
        with self.assertRaises(binding.BindingError):
            caller.run_agent_blocking(8001, object())
        self.assertEqual(lease.attempts, 0)
        self.assertTrue(lease.restore())
        caller, main, lease = self.fixture(lambda server: None, install=False)
        main.Config = object()
        lease.install()
        self.assertFalse(lease.installed)
        self.assertIsNotNone(lease.error)

    def test_unstarted_force_exit_and_inactive_stop_do_not_change_flags(self):
        def callback(server):
            server.started = False
            self.assertFalse(lease.request_graceful_stop())
            self.assertFalse(server.should_exit)
            server.started, server.force_exit = True, True
            self.assertFalse(lease.request_graceful_stop())
            self.assertFalse(server.should_exit)
        caller, main, lease = self.fixture(callback)
        self.assertFalse(lease.request_graceful_stop())
        caller.run_agent_blocking(8001, object())
        self.assertFalse(lease.request_graceful_stop())
        self.assertTrue(lease.restore())

    def test_app_and_instance_method_interference_prevent_stop(self):
        def callback(server):
            captured = server.config.app
            server.config.app = object()
            self.assertFalse(lease.request_graceful_stop())
            server.config.app = captured
            server.config.workers = True
            self.assertFalse(lease.request_graceful_stop())
            server.config.workers = 1
            original_app = lease.capture.app
            lease.capture.app = object()
            self.assertFalse(lease.request_graceful_stop())
            lease.capture.app = original_app
            server.run = lambda: None
            self.assertFalse(lease.request_graceful_stop())
            self.assertFalse(server.should_exit)
        caller, main, lease = self.fixture(callback)
        caller.run_agent_blocking(8001, object())
        self.assertTrue(lease.restore())

    def test_factory_alias_interference_is_preserved_until_repaired(self):
        interference = object()
        def callback(server):
            main.Server = interference
            self.assertFalse(lease.request_graceful_stop())
            self.assertFalse(server.should_exit)
        caller, main, lease = self.fixture(callback)
        caller.run_agent_blocking(8001, object())
        self.assertFalse(lease.restore())
        self.assertIs(main.Server, interference)
        self.assertTrue(lease.report()["restoration_authority_retained"])
        main.Server = lease.factory
        self.assertTrue(lease.restore())
        self.assertTrue(lease.restore())

    def test_once_only_lease_refuses_reinstall_and_new_original_run(self):
        caller, main, lease = self.fixture(lambda server: None)
        caller.run_agent_blocking(8001, object())
        with self.assertRaises(binding.BindingError):
            caller.run_agent_blocking(8001, object())
        self.assertTrue(lease.restore())
        with self.assertRaises(binding.BindingError):
            lease.install()


if __name__ == "__main__":
    unittest.main(verbosity=2)
