"""Synthetic receipts and mocked bootstrap dependencies; no native launches."""

from copy import deepcopy
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "serve_upstream_agentops_cases_v1.py"
MODULE_NAME = "serve_upstream_agentops_cases_v1_under_test"
SPEC = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[MODULE_NAME] = bootstrap
SPEC.loader.exec_module(bootstrap)

NOW = datetime(2026, 10, 29, 12, 0, 20, tzinfo=timezone.utc)
MIN_PHYSICAL = 1_073_741_824
MIN_COMMIT = 2_147_483_648
HASH = "a" * 64
STOP_TOKEN = "fixture_stop_token_1234"


def stamp(value):
    return value.isoformat(timespec="microseconds")


def synthetic_receipt(binding, now=NOW):
    return {
        "schema_version": "upstream-agentops-resource-gate/1",
        "stage": "prelaunch",
        "eligible": True,
        "minimums": {
            "physical_available_bytes": MIN_PHYSICAL,
            "commit_available_bytes": MIN_COMMIT,
        },
        "binding": deepcopy(binding),
        "samples": [
            {"observed_at_utc": stamp(now - timedelta(seconds=20)), "monotonic_ns": 100_000_000_000,
             "physical_available_bytes": MIN_PHYSICAL, "commit_available_bytes": MIN_COMMIT},
            {"observed_at_utc": stamp(now - timedelta(seconds=10)), "monotonic_ns": 110_000_000_000,
             "physical_available_bytes": MIN_PHYSICAL, "commit_available_bytes": MIN_COMMIT},
        ],
    }


class SecretReadGuard(dict):
    """Presence/iteration is allowed; obtaining the synthetic key value is not."""

    def __getitem__(self, key):
        if key == "GOOGLE_API_KEY":
            raise AssertionError("bootstrap read a key value")
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key == "GOOGLE_API_KEY":
            raise AssertionError("bootstrap read a key value")
        return super().get(key, default)

    def items(self):
        if "GOOGLE_API_KEY" in self:
            raise AssertionError("bootstrap obtained environment values")
        return super().items()

    def values(self):
        if "GOOGLE_API_KEY" in self:
            raise AssertionError("bootstrap obtained environment values")
        return super().values()

    def copy(self):
        if "GOOGLE_API_KEY" in self:
            raise AssertionError("bootstrap copied a key value")
        return super().copy()

    def pop(self, key, *args):
        if key == "GOOGLE_API_KEY":
            raise AssertionError("bootstrap removed and read a key value")
        return super().pop(key, *args)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        for relative in bootstrap._SOURCE_FILES:
            source_file = self.source / relative
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_bytes(b"synthetic source placeholder; never imported or opened as a database\n")
        self.service = self.root / "service"
        self.service.mkdir()
        (self.service / "state").mkdir()
        self.receipt_path = self.root / "gate.json"
        self.config = bootstrap.BootstrapConfig(
            source_root=self.source,
            service_dir=self.service,
            family="core",
            provider="gemini",
            model="gemini-3.1-flash-lite-preview",
            host="127.0.0.1",
            port=8123,
            resource_gate_receipt=self.receipt_path,
            stop_token=STOP_TOKEN,
        )
        self.binding = bootstrap.binding_for(self.config, bootstrap_sha256=HASH)
        self.receipt = synthetic_receipt(self.binding)
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")

    def assert_gate_rejected(self, receipt=None, binding=None, now=NOW):
        with self.assertRaises(ValueError):
            bootstrap.validate_resource_gate(
                self.receipt if receipt is None else receipt,
                self.binding if binding is None else binding,
                now,
            )

    def changed_config(self, **changes):
        return replace(self.config, **changes)

    def argv(self):
        return [
            "--source-root", str(self.source), "--service-dir", str(self.service),
            "--family", "core", "--provider", "gemini", "--model", self.config.model,
            "--host", "127.0.0.1", "--port", "8123",
            "--resource-gate-receipt", str(self.receipt_path),
            "--stop-token", STOP_TOKEN,
        ]

    def test_module_import_has_no_runtime_dependency_imports(self):
        imported = []
        original_import = __import__

        def guarded_import(name, *args, **kwargs):
            imported.append(name)
            if name.split(".")[0] in {"agent", "google", "uvicorn", "agentops_asgi_capture_v1"}:
                raise AssertionError("runtime import during bootstrap module import")
            return original_import(name, *args, **kwargs)

        name = "serve_upstream_agentops_cases_v1_import_probe"
        spec = importlib.util.spec_from_file_location(name, SCRIPT)
        module = importlib.util.module_from_spec(spec)
        self.addCleanup(sys.modules.pop, name, None)
        sys.modules[name] = module
        with patch("builtins.__import__", side_effect=guarded_import):
            spec.loader.exec_module(module)
        self.assertNotIn("uvicorn", imported)

    def test_binding_has_only_exact_nonsecret_launch_fields(self):
        self.assertEqual(set(self.binding), {
            "source_root", "service_dir", "family", "provider", "model", "host", "port",
            "interpreter", "bootstrap_sha256",
            "stop_token",
        })
        self.assertEqual(self.binding["source_root"], str(self.source.resolve()))
        self.assertEqual(self.binding["service_dir"], str(self.service.resolve()))
        self.assertEqual(self.binding["interpreter"], str(Path(sys.executable).resolve()))
        self.assertEqual(self.binding["bootstrap_sha256"], HASH)
        self.assertEqual(self.binding["family"], "core")
        self.assertEqual(self.binding["provider"], "gemini")
        self.assertEqual(self.binding["model"], self.config.model)
        self.assertEqual(self.binding["host"], "127.0.0.1")
        self.assertEqual(self.binding["port"], 8123)
        self.assertEqual(self.binding["stop_token"], STOP_TOKEN)

    def test_valid_receipt_at_exact_minima_is_accepted_without_mutation(self):
        original = deepcopy(self.receipt)
        result = bootstrap.validate_resource_gate(self.receipt, self.binding, NOW)
        self.assertIsInstance(result, dict)
        self.assertEqual(self.receipt, original)

    def test_gate_schema_stage_and_eligibility_are_typed_and_exact(self):
        for field, values in (
            ("schema_version", (None, "wrong/1")),
            ("stage", (None, "postlaunch")),
            ("eligible", (False, 1, "true", None)),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    receipt = deepcopy(self.receipt)
                    receipt[field] = value
                    self.assert_gate_rejected(receipt)

    def test_missing_required_receipt_fields_are_rejected(self):
        for field in ("schema_version", "stage", "eligible", "minimums", "binding", "samples"):
            with self.subTest(field=field):
                receipt = deepcopy(self.receipt)
                receipt.pop(field)
                self.assert_gate_rejected(receipt)

    def test_declared_minima_cannot_be_lowered_or_retyped(self):
        for field, required in (("physical_available_bytes", MIN_PHYSICAL), ("commit_available_bytes", MIN_COMMIT)):
            for invalid in (required - 1, required + 1, True, str(required), float(required), None):
                with self.subTest(field=field, value=invalid):
                    receipt = deepcopy(self.receipt)
                    receipt["minimums"][field] = invalid
                    self.assert_gate_rejected(receipt)

    def test_both_samples_must_meet_both_minima(self):
        for index in (0, 1):
            for field, required in (("physical_available_bytes", MIN_PHYSICAL), ("commit_available_bytes", MIN_COMMIT)):
                with self.subTest(sample=index, field=field):
                    receipt = deepcopy(self.receipt)
                    receipt["samples"][index][field] = required - 1
                    self.assert_gate_rejected(receipt)

    def test_sample_integer_fields_reject_boolean_float_string_and_null(self):
        for field in ("monotonic_ns", "physical_available_bytes", "commit_available_bytes"):
            for invalid in (True, False, 1.5, "100000000000", None):
                with self.subTest(field=field, value=invalid):
                    receipt = deepcopy(self.receipt)
                    receipt["samples"][1][field] = invalid
                    self.assert_gate_rejected(receipt)

    def test_samples_are_exactly_two_complete_objects(self):
        for samples in ([], self.receipt["samples"][:1], self.receipt["samples"] * 2, "partial", [None, None]):
            with self.subTest(samples=samples):
                receipt = deepcopy(self.receipt)
                receipt["samples"] = samples
                self.assert_gate_rejected(receipt)
        for field in self.receipt["samples"][0]:
            with self.subTest(missing_sample_field=field):
                receipt = deepcopy(self.receipt)
                receipt["samples"][0].pop(field)
                self.assert_gate_rejected(receipt)

    def test_wall_and_monotonic_gap_boundaries_are_accepted(self):
        for gap in (10, 30):
            with self.subTest(gap=gap):
                receipt = deepcopy(self.receipt)
                receipt["samples"][0]["observed_at_utc"] = stamp(NOW - timedelta(seconds=10 + gap))
                receipt["samples"][1]["monotonic_ns"] = receipt["samples"][0]["monotonic_ns"] + gap * 1_000_000_000
                self.assertIsInstance(bootstrap.validate_resource_gate(receipt, self.binding, NOW), dict)

    def test_wall_sample_gaps_outside_ten_to_thirty_seconds_are_rejected(self):
        for gap in (0, 9.999999, 30.000001, -10):
            with self.subTest(gap=gap):
                receipt = deepcopy(self.receipt)
                receipt["samples"][0]["observed_at_utc"] = stamp(NOW - timedelta(seconds=10 + gap))
                self.assert_gate_rejected(receipt)

    def test_monotonic_sample_gaps_outside_ten_to_thirty_seconds_are_rejected(self):
        for gap_ns in (0, 9_999_999_999, 30_000_000_001, -10_000_000_000):
            with self.subTest(gap_ns=gap_ns):
                receipt = deepcopy(self.receipt)
                receipt["samples"][1]["monotonic_ns"] = receipt["samples"][0]["monotonic_ns"] + gap_ns
                self.assert_gate_rejected(receipt)

    def test_second_sample_freshness_accepts_zero_and_sixty_seconds(self):
        for age in (0, 60):
            with self.subTest(age=age):
                receipt = deepcopy(self.receipt)
                receipt["samples"][1]["observed_at_utc"] = stamp(NOW - timedelta(seconds=age))
                receipt["samples"][0]["observed_at_utc"] = stamp(NOW - timedelta(seconds=age + 10))
                self.assertIsInstance(bootstrap.validate_resource_gate(receipt, self.binding, NOW), dict)

    def test_stale_and_future_second_sample_is_rejected(self):
        for age in (60.000001, 300, -0.000001):
            with self.subTest(age=age):
                receipt = deepcopy(self.receipt)
                receipt["samples"][1]["observed_at_utc"] = stamp(NOW - timedelta(seconds=age))
                receipt["samples"][0]["observed_at_utc"] = stamp(NOW - timedelta(seconds=age + 10))
                self.assert_gate_rejected(receipt)

    def test_sample_timestamps_require_parseable_utc_offsets(self):
        for invalid in (None, True, "not-a-time", "2026-10-29T12:00:10", "2026-10-29T17:30:10+05:30"):
            with self.subTest(timestamp=invalid):
                receipt = deepcopy(self.receipt)
                receipt["samples"][1]["observed_at_utc"] = invalid
                self.assert_gate_rejected(receipt)

    def test_utc_z_sample_timestamps_are_supported(self):
        receipt = deepcopy(self.receipt)
        for sample in receipt["samples"]:
            sample["observed_at_utc"] = sample["observed_at_utc"].replace("+00:00", "Z")
        self.assertIsInstance(bootstrap.validate_resource_gate(receipt, self.binding, NOW), dict)

    def test_every_binding_field_must_match(self):
        for field in self.binding:
            with self.subTest(field=field):
                receipt = deepcopy(self.receipt)
                receipt["binding"][field] = 8124 if field == "port" else "different"
                self.assert_gate_rejected(receipt)

    def test_binding_keys_cannot_be_missing_extra_or_retyped(self):
        for field in self.binding:
            with self.subTest(missing=field):
                receipt = deepcopy(self.receipt)
                receipt["binding"].pop(field)
                self.assert_gate_rejected(receipt)
        receipt = deepcopy(self.receipt)
        receipt["binding"]["extra"] = "unbound"
        self.assert_gate_rejected(receipt)
        for invalid in (True, "8123", 8123.0):
            receipt = deepcopy(self.receipt)
            receipt["binding"]["port"] = invalid
            self.assert_gate_rejected(receipt)

    def test_gate_binding_changes_when_launch_identity_changes(self):
        for field, value in (("family", "report"), ("model", "another-model"), ("port", 8124),
                             ("source_root", self.root / "other-source"), ("service_dir", self.root / "other-service")):
            with self.subTest(field=field):
                other_binding = bootstrap.binding_for(self.changed_config(**{field: value}), bootstrap_sha256=HASH)
                self.assert_gate_rejected(binding=other_binding)

    def test_gate_checks_do_not_import_apps_or_write_the_service_directory(self):
        before = sorted(path.relative_to(self.service) for path in self.service.rglob("*"))
        receipt = deepcopy(self.receipt)
        receipt["eligible"] = False
        with patch("importlib.import_module", side_effect=AssertionError("runtime import during gate check")):
            self.assert_gate_rejected(receipt)
        self.assertEqual(sorted(path.relative_to(self.service) for path in self.service.rglob("*")), before)

    def test_valid_arguments_are_parsed_without_runtime_imports_or_writes(self):
        before = sorted(self.service.rglob("*"))
        with patch("importlib.import_module", side_effect=AssertionError("runtime import during argument parse")):
            config = bootstrap.parse_args(self.argv())
        self.assertEqual(config, self.config)
        self.assertEqual(sorted(self.service.rglob("*")), before)

    def test_argument_parser_rejects_unsupported_family_invalid_port_and_stop_token(self):
        for option, value in (("--family", "substitute"), ("--port", "0"), ("--port", "65536"),
                              ("--stop-token", "short"), ("--stop-token", "!" * 20), ("--stop-token", "x" * 129)):
            with self.subTest(option=option, value=value):
                argv = self.argv()
                argv[argv.index(option) + 1] = value
                with self.assertRaises((SystemExit, ValueError)):
                    bootstrap.parse_args(argv)

    def test_stop_request_accepts_only_exact_schema_and_owned_token(self):
        request = {"schema_version": "upstream-agentops-stop/1", "stop_token": STOP_TOKEN}
        original = deepcopy(request)
        self.assertIsNone(bootstrap.validate_stop_request(request, STOP_TOKEN))
        self.assertEqual(request, original)
        for invalid in (None, [], "stop", {},
                        {"schema_version": "upstream-agentops-stop/1"},
                        {"schema_version": "wrong/1", "stop_token": STOP_TOKEN},
                        {"schema_version": "upstream-agentops-stop/1", "stop_token": True},
                        {"schema_version": "upstream-agentops-stop/1", "stop_token": "wrong_owned_token_1234"},
                        {**request, "unbound": "extra"}):
            with self.subTest(request=invalid):
                with self.assertRaises(ValueError):
                    bootstrap.validate_stop_request(invalid, STOP_TOKEN)

    def test_empty_preallocated_state_directory_is_valid_without_writes(self):
        before = sorted(self.service.rglob("*"))
        bootstrap.validate_paths(self.config)
        self.assertEqual(sorted(self.service.rglob("*")), before)

    def test_existing_state_data_wire_or_stop_marker_is_rejected(self):
        for existing in ("state/data.db", "wire", "stop.request.json", "bootstrap.created.json",
                         "bootstrap.stop-ack.json", "bootstrap.stop-error.json", "bootstrap.exit.json"):
            with self.subTest(existing=existing):
                target = self.service / existing
                if existing == "wire":
                    target.mkdir()
                else:
                    target.write_text("synthetic retained data", encoding="utf-8")
                try:
                    with self.assertRaises(ValueError):
                        bootstrap.validate_paths(self.config)
                finally:
                    if target.is_dir():
                        target.rmdir()
                    else:
                        target.unlink()

    def test_missing_or_non_directory_launch_paths_are_rejected(self):
        missing = self.root / "missing"
        file_path = self.root / "file"
        file_path.write_text("synthetic file", encoding="utf-8")
        for field in ("source_root", "service_dir"):
            for path in (missing, file_path):
                with self.subTest(field=field, path=path):
                    with self.assertRaises(ValueError):
                        bootstrap.validate_paths(self.changed_config(**{field: path}))

    def test_relative_launch_paths_are_rejected(self):
        for field in ("source_root", "service_dir"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    bootstrap.validate_paths(self.changed_config(**{field: Path("relative")}))

    def test_linked_or_reparse_state_is_rejected(self):
        original_lstat = Path.lstat
        state = self.service / "state"
        for mode, attributes in ((stat.S_IFLNK | 0o777, 0), (stat.S_IFDIR | 0o700, 0x400)):
            with self.subTest(mode=mode, attributes=attributes):
                def fake_lstat(path, *args, **kwargs):
                    if path == state:
                        return SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
                    return original_lstat(path, *args, **kwargs)
                with patch.object(Path, "lstat", new=fake_lstat):
                    with self.assertRaises(ValueError):
                        bootstrap.validate_paths(self.config)

    def test_source_and_service_must_be_disjoint(self):
        with self.assertRaises(ValueError):
            bootstrap.validate_paths(self.changed_config(source_root=self.service))

    def test_control_json_rejects_duplicate_keys_malformed_utf8_and_oversize(self):
        for contents in (b'{"stop_token":"first","stop_token":"second"}', b'{"partial":', b'\xff', b' ' * (1024 * 1024 + 1)):
            with self.subTest(size=len(contents)):
                path = self.root / "control.json"
                path.write_bytes(contents)
                with self.assertRaises(ValueError):
                    bootstrap.read_json_regular(path)

    def test_control_json_reads_a_regular_complete_object_without_mutation(self):
        contents = b'{"schema_version":"upstream-agentops-stop/1","stop_token":"fixture_stop_token_1234"}'
        path = self.root / "control.json"
        path.write_bytes(contents)
        self.assertEqual(bootstrap.read_json_regular(path), json.loads(contents))
        self.assertEqual(path.read_bytes(), contents)

    def test_runtime_flags_require_isolation_no_site_and_no_bytecode(self):
        bootstrap.validate_runtime_flags(SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1))
        for field in ("isolated", "no_site", "dont_write_bytecode"):
            flags = {"isolated": 1, "no_site": 1, "dont_write_bytecode": 1}
            flags[field] = 0
            with self.subTest(flag=field):
                with self.assertRaises(ValueError):
                    bootstrap.validate_runtime_flags(SimpleNamespace(**flags))

    def test_explicit_runtime_path_setup_does_not_execute_pth_files(self):
        library = self.root / "runtime-library"
        library.mkdir()
        (library / "unsafe.pth").write_text("import never_import_this_fixture\n", encoding="utf-8")
        trusted_stdlib = self.root / "stdlib"
        trusted_stdlib.mkdir()
        modules = {key: value for key, value in sys.modules.items() if key != "agent" and not key.startswith("agent.")}
        fake_site = SimpleNamespace(addsitedir=Mock(side_effect=AssertionError("pth execution")))
        modules["site"] = fake_site
        with patch.object(sys, "modules", modules), patch.object(sys, "path", [str(trusted_stdlib)]):
            result = bootstrap._install_source_path(self.config, runtime_library=library)
            self.assertEqual(sys.path, [str((self.source / "agents/python/src").resolve()), str(SCRIPT.parent.resolve()),
                                       str(trusted_stdlib), str(library.resolve())])
            self.assertIs(result["site_addsitedir_used"], False)
            self.assertIs(result["pth_executed"], False)
            fake_site.addsitedir.assert_not_called()
            self.assertNotIn("never_import_this_fixture", sys.modules)

    def test_runtime_library_is_derived_from_executable_not_prefix(self):
        runtime = self.root / "synthetic-venv"
        executable = runtime / "Scripts/python.exe"
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"synthetic executable placeholder; never executed")
        library = runtime / "Lib/site-packages"
        library.mkdir(parents=True)
        (runtime / "pyvenv.cfg").write_text("home = synthetic-base\n", encoding="utf-8")
        trusted_stdlib = self.root / "stdlib"
        trusted_stdlib.mkdir()
        modules = {key: value for key, value in sys.modules.items() if key != "agent" and not key.startswith("agent.")}
        with patch.object(sys, "executable", str(executable)), patch.object(sys, "prefix", str(self.root / "wrong-prefix")), \
                patch.object(sys, "path", [str(trusted_stdlib)]), patch.object(sys, "modules", modules):
            result = bootstrap._install_source_path(self.config)
            self.assertEqual(result["runtime_library"], str(library.resolve()))
            self.assertEqual(len(result["pyvenv_cfg_sha256"]), 64)
            self.assertIs(result["pth_executed"], False)

    def test_preimported_agent_or_untrusted_initial_path_is_rejected(self):
        library = self.root / "runtime-library"
        library.mkdir()
        modules = {key: value for key, value in sys.modules.items() if key != "agent" and not key.startswith("agent.")}
        with patch.object(sys, "modules", {**modules, "agent": object()}), patch.object(sys, "path", [str(self.root)]):
            with self.assertRaises(ValueError):
                bootstrap._install_source_path(self.config, runtime_library=library)
        for path in ("", str(self.root / "site-packages")):
            with self.subTest(initial_path=path):
                with patch.object(sys, "modules", modules), patch.object(sys, "path", [path]):
                    with self.assertRaises(ValueError):
                        bootstrap._install_source_path(self.config, runtime_library=library)

    def test_nonsecret_environment_contains_explicit_model_and_no_credentials(self):
        overrides = bootstrap.nonsecret_environment(self.config)
        self.assertEqual(overrides["AGENT_MODEL_PROVIDER"], "gemini")
        self.assertEqual(overrides["AGENT_MODEL"], self.config.model)
        self.assertEqual(overrides["AGENT_A2A_BIND_HOST"], self.config.host)
        self.assertEqual(overrides["AGENT_A2A_PORT"], str(self.config.port))
        self.assertEqual(overrides["AGENT_STATE_DIR"], str(self.service / "state"))
        for key in overrides:
            self.assertFalse(any(marker in key for marker in ("API_KEY", "TOKEN", "PASSWORD", "SECRET")))
        json.dumps(overrides)

    def test_environment_configuration_preserves_key_without_obtaining_its_value(self):
        environment = SecretReadGuard({"GOOGLE_API_KEY": "synthetic-key-value", "PATH": "preserved-path",
                                       "AGENT_MODEL_FALLBACK": "wrong-model", "AGENT_MCP_URL": "http://wrong.invalid",
                                       "AGENT_ARBITRARY_SWITCH": "remove-me"})
        bootstrap.configure_environment(self.config, environ=environment)
        self.assertEqual(dict.__getitem__(environment, "GOOGLE_API_KEY"), "synthetic-key-value")
        self.assertEqual(environment["PATH"], "preserved-path")
        self.assertNotIn("AGENT_MODEL_FALLBACK", environment)
        self.assertNotIn("AGENT_MCP_URL", environment)
        self.assertNotIn("AGENT_ARBITRARY_SWITCH", environment)
        for key, value in bootstrap.nonsecret_environment(self.config).items():
            self.assertEqual(environment[key], value)

    def test_environment_requires_key_name_presence(self):
        with self.assertRaises(ValueError):
            bootstrap.configure_environment(self.config, environ={"PATH": "synthetic-path"})

    def test_provider_proxy_and_telemetry_switches_cannot_survive_configuration(self):
        switching_keys = (
            "GOOGLE_GENAI_USE_ENTERPRISE", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS", "GEMINI_API_KEY",
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
            "http_proxy", "https_proxy", "all_proxy", "no_proxy", "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
            "MLFLOW_TRACKING_URI", "MCP_URL", "STATE_BACKUP_PATH", "PYTHONPATH", "PYTHONHOME", "DOTENV_FILE",
        )
        environment = SecretReadGuard({"GOOGLE_API_KEY": "synthetic-key-value", "PATH": "preserved-path",
                                       **{key: "synthetic-switch-value" for key in switching_keys}})
        bootstrap.configure_environment(self.config, environ=environment)
        overrides = bootstrap.nonsecret_environment(self.config)
        for key in switching_keys:
            with self.subTest(key=key):
                if key in overrides:
                    self.assertEqual(environment[key], overrides[key])
                else:
                    self.assertNotIn(key, environment)
        self.assertEqual(dict.__getitem__(environment, "GOOGLE_API_KEY"), "synthetic-key-value")

    def test_original_family_object_selection_and_external_capture(self):
        for family in ("core", "report", "workflow"):
            with self.subTest(family=family):
                config = self.changed_config(family=family)
                original_app = object()
                wrapped_app = object()
                original_core = SimpleNamespace(name="agentops_agent")
                original_report = SimpleNamespace(name="triage_report_agent")
                original_workflow = SimpleNamespace(name="triage_workflow")
                source_module = config.source_root / "agents/python/src/agent"
                server = SimpleNamespace(create_app=Mock(return_value=original_app), root_agent=original_core,
                                         __file__=str(source_module / "server.py"),
                                         settings=SimpleNamespace(**bootstrap.expected_settings(config)))
                capture = Mock(return_value=wrapped_app)
                modules = {
                    "agent.server": server,
                    "agent.report": SimpleNamespace(triage_report_agent=original_report, __file__=str(source_module / "report.py")),
                    "agent.workflow": SimpleNamespace(triage_workflow=original_workflow, __file__=str(source_module / "workflow.py")),
                    "agentops_asgi_capture_v1": SimpleNamespace(Capture=capture, __file__=str(SCRIPT.parent / "agentops_asgi_capture_v1.py")),
                }
                imported = []

                def importer(name):
                    imported.append(name)
                    return modules[name]

                observed, metadata = bootstrap.build_observed_app(config, importer=importer)
                self.assertIs(observed, wrapped_app)
                if family == "core":
                    server.create_app.assert_called_once_with()
                    self.assertNotIn("agent.report", imported)
                    self.assertNotIn("agent.workflow", imported)
                else:
                    expected = original_report if family == "report" else original_workflow
                    server.create_app.assert_called_once_with(agent=expected)
                    self.assertIn("agent." + family, imported)
                capture.assert_called_once_with(original_app, self.service)
                self.assertIsInstance(metadata, dict)
                self.assertEqual(metadata["configuration"], bootstrap.nonsecret_environment(config))
                self.assertIs(metadata["tool_restriction"], False)
                self.assertIs(metadata["autoapproval"], False)
                self.assertIs(metadata["model_replacement"], False)
                json.dumps(metadata)

    def test_original_app_creation_error_cannot_be_replaced_by_a_fixture(self):
        original_error = RuntimeError("synthetic original app creation error")
        server = SimpleNamespace(create_app=Mock(side_effect=original_error), root_agent=SimpleNamespace(name="agentops_agent"),
                                 __file__=str(self.source / "agents/python/src/agent/server.py"),
                                 settings=SimpleNamespace(**bootstrap.expected_settings(self.config)))
        capture = Mock()
        modules = {"agent.server": server, "agentops_asgi_capture_v1": SimpleNamespace(Capture=capture,
                   __file__=str(SCRIPT.parent / "agentops_asgi_capture_v1.py"))}
        with self.assertRaises(RuntimeError) as caught:
            bootstrap.build_observed_app(self.config, importer=modules.__getitem__)
        self.assertIs(caught.exception, original_error)
        capture.assert_not_called()

    def test_unbound_source_origin_settings_or_object_name_is_rejected(self):
        for change in ("origin", "settings", "name"):
            with self.subTest(change=change):
                server = SimpleNamespace(create_app=Mock(), root_agent=SimpleNamespace(name="agentops_agent"),
                                         __file__=str(self.source / "agents/python/src/agent/server.py"),
                                         settings=SimpleNamespace(**bootstrap.expected_settings(self.config)))
                if change == "origin":
                    server.__file__ = str(self.root / "unbound/server.py")
                elif change == "settings":
                    server.settings.model_fallback = "substitute-model"
                else:
                    server.root_agent.name = "fixture_agent"
                with self.assertRaises(ValueError):
                    bootstrap.build_observed_app(self.config, importer=lambda name: server)
                server.create_app.assert_not_called()

    def run_mocked_main(self, *, receipt=None, current=None, result=None, factory_error=None):
        receipt = self.receipt if receipt is None else receipt
        self.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        events = []
        configuration = Mock(side_effect=lambda *args: events.append("configure"))
        setup = Mock(side_effect=lambda *args: events.append("install") or {"pth_executed": False})
        memory = Mock(side_effect=lambda: events.append("headroom") or (
            {"physical_available_bytes": MIN_PHYSICAL, "commit_available_bytes": MIN_COMMIT} if current is None else current))
        original_gate = bootstrap.validate_resource_gate

        def check_gate(value, binding, entered):
            events.append("gate")
            self.assertIs(type(entered), datetime)
            return original_gate(value, binding, NOW)

        created_configs = []
        server = SimpleNamespace(started=True, should_exit=False)

        def uvicorn_config(app, **kwargs):
            # Real Uvicorn names its positional argument app; factory is a
            # separate bool keyword. Naming both factory masks the runtime
            # factory path with a duplicate-argument TypeError in this mock.
            config = SimpleNamespace(factory=app, kwargs=kwargs)
            created_configs.append(config)
            return config

        def uvicorn_server(config):
            server.config = config
            return server

        uvicorn = SimpleNamespace(Config=Mock(side_effect=uvicorn_config), Server=Mock(side_effect=uvicorn_server))

        def importer(name):
            events.append("import:" + name)
            self.assertEqual(name, "uvicorn")
            return uvicorn

        def factory(*args, **kwargs):
            events.append("factory")
            if factory_error is not None:
                raise factory_error
            return object(), {"configuration": bootstrap.nonsecret_environment(self.config), "autoapproval": False}

        completed = {
            "status": "stopped", "owned_stop_accepted": True, "uvicorn_started": True,
            "original_serve_returned": True, "process_exit_proven": False, "database_retention_completed": False,
        } if result is None else result

        async def run_fake_serve(server_argument, config_argument):
            self.assertIs(server_argument, server)
            self.assertEqual(config_argument, self.config)
            events.append("serve")
            server.config.factory()
            return deepcopy(completed)

        stderr = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(bootstrap, "validate_runtime_flags"))
            stack.enter_context(patch.object(bootstrap, "binding_for", return_value=self.binding))
            stack.enter_context(patch.object(bootstrap, "validate_resource_gate", side_effect=check_gate))
            stack.enter_context(patch.object(bootstrap, "global_memory_status", memory))
            stack.enter_context(patch.object(bootstrap, "configure_environment", configuration))
            stack.enter_context(patch.object(bootstrap, "_install_source_path", setup))
            runtime_import = stack.enter_context(patch.object(bootstrap, "import_module", side_effect=importer))
            app_factory = stack.enter_context(patch.object(bootstrap, "build_observed_app", side_effect=factory))
            # Drive only this synthetic async seam through the real stdlib
            # event-loop entrypoint; no AsyncMock coroutine is leaked.
            stack.enter_context(patch.object(bootstrap, "serve_with_stop", new=run_fake_serve))
            stack.enter_context(patch.object(sys, "stderr", stderr))
            code = bootstrap.main(self.argv())
        return SimpleNamespace(code=code, events=events, memory=memory, configuration=configuration,
                               setup=setup, runtime_import=runtime_import, app_factory=app_factory,
                               uvicorn=uvicorn, created_configs=created_configs, stderr=stderr.getvalue())

    def test_main_rejected_gate_precedes_headroom_environment_imports_and_writes(self):
        receipt = deepcopy(self.receipt)
        receipt["eligible"] = False
        before = sorted(self.service.rglob("*"))
        outcome = self.run_mocked_main(receipt=receipt)
        self.assertEqual(outcome.code, 1)
        self.assertEqual(outcome.events, ["gate"])
        outcome.memory.assert_not_called()
        outcome.configuration.assert_not_called()
        outcome.setup.assert_not_called()
        outcome.runtime_import.assert_not_called()
        outcome.app_factory.assert_not_called()
        self.assertEqual(sorted(self.service.rglob("*")), before)

    def test_main_rechecks_typed_current_headroom_before_any_runtime_side_effect(self):
        for field, invalid in (("physical_available_bytes", MIN_PHYSICAL - 1),
                               ("commit_available_bytes", MIN_COMMIT - 1),
                               ("physical_available_bytes", True), ("commit_available_bytes", "2147483648")):
            with self.subTest(field=field, value=invalid):
                current = {"physical_available_bytes": MIN_PHYSICAL, "commit_available_bytes": MIN_COMMIT}
                current[field] = invalid
                outcome = self.run_mocked_main(current=current)
                self.assertEqual(outcome.code, 1)
                self.assertEqual(outcome.events, ["gate", "headroom"])
                outcome.configuration.assert_not_called()
                outcome.runtime_import.assert_not_called()
                self.assertFalse((self.service / "bootstrap.exit.json").exists())

    def test_mocked_main_uses_original_factory_lifespan_and_records_limited_exit(self):
        outcome = self.run_mocked_main()
        self.assertEqual(outcome.code, 0)
        self.assertEqual(outcome.events, ["gate", "headroom", "configure", "install", "import:uvicorn", "serve", "factory"])
        kwargs = outcome.created_configs[0].kwargs
        self.assertIs(kwargs["factory"], True)
        self.assertEqual(kwargs["host"], "127.0.0.1")
        self.assertEqual(kwargs["port"], 8123)
        self.assertEqual(kwargs["lifespan"], "on")
        self.assertEqual(kwargs["timeout_graceful_shutdown"], 10)
        self.assertIs(kwargs["access_log"], False)
        created = json.loads((self.service / "bootstrap.created.json").read_text(encoding="utf-8"))
        exited = json.loads((self.service / "bootstrap.exit.json").read_text(encoding="utf-8"))
        self.assertEqual(created["status"], "constructed_not_ready")
        self.assertEqual(created["binding"], self.binding)
        self.assertEqual(created["configuration"], bootstrap.nonsecret_environment(self.config))
        self.assertEqual(exited["status"], "stopped")
        self.assertIs(exited["process_exit_proven"], False)
        self.assertIs(exited["database_retention_completed"], False)
        self.assertIs(exited["native_case_pass_proven"], False)
        self.assertIs(exited["qualification_established"], False)
        self.assertNotIn("synthetic-key-value", json.dumps(created) + json.dumps(exited))

    def test_main_does_not_upgrade_return_without_owned_ready_stop(self):
        outcome = self.run_mocked_main(result={"status": "returned_without_owned_ready_stop", "original_serve_returned": True})
        self.assertEqual(outcome.code, 1)
        exited = json.loads((self.service / "bootstrap.exit.json").read_text(encoding="utf-8"))
        self.assertEqual(exited["status"], "returned_without_owned_ready_stop")
        self.assertIs(exited["native_case_pass_proven"], False)

    def test_main_sanitizes_original_construction_errors(self):
        outcome = self.run_mocked_main(factory_error=RuntimeError("synthetic-secret-value from failed provider"))
        self.assertEqual(outcome.code, 1)
        exited = (self.service / "bootstrap.exit.json").read_text(encoding="utf-8")
        self.assertNotIn("synthetic-secret-value", exited + outcome.stderr)
        self.assertEqual(json.loads(exited)["error_type"], "RuntimeError")
        self.assertFalse((self.service / "bootstrap.created.json").exists())

    def stop_marker(self, token=STOP_TOKEN):
        path = self.service / "stop.request.json"
        path.write_text(json.dumps({"schema_version": "upstream-agentops-stop/1", "stop_token": token}), encoding="utf-8")
        return path

    def test_valid_stop_ack_requests_owned_server_drain_without_close_proof(self):
        marker = self.stop_marker()
        server = SimpleNamespace(started=True, should_exit=False)

        async def observe():
            return await asyncio.wait_for(bootstrap._watch_stop(server, self.config, poll_seconds=0), timeout=1)

        acknowledgment = asyncio.run(observe())
        self.assertTrue(server.should_exit)
        self.assertEqual(acknowledgment["schema_version"], "upstream-agentops-stop-ack/1")
        self.assertEqual(acknowledgment["status"], "accepted")
        self.assertIs(acknowledgment["lifespan_close_completed"], False)
        self.assertEqual(acknowledgment["request_sha256"], hashlib.sha256(marker.read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.service / "bootstrap.stop-ack.json").read_text(encoding="utf-8")), acknowledgment)

    def test_valid_stop_waits_for_original_server_startup_before_drain(self):
        self.stop_marker()
        server = SimpleNamespace(started=False, should_exit=False)

        async def observe():
            watching = asyncio.create_task(bootstrap._watch_stop(server, self.config, poll_seconds=0))
            await asyncio.sleep(0)
            self.assertFalse(server.should_exit)
            self.assertFalse((self.service / "bootstrap.stop-ack.json").exists())
            server.started = True
            return await asyncio.wait_for(watching, timeout=1)

        acknowledgment = asyncio.run(observe())
        self.assertTrue(server.should_exit)
        self.assertEqual(acknowledgment["status"], "accepted")

    def test_rejected_stop_does_not_acknowledge_or_set_exit_in_watcher(self):
        self.stop_marker("wrong_owned_token_1234")
        server = SimpleNamespace(started=True, should_exit=False)

        async def observe():
            return await asyncio.wait_for(bootstrap._watch_stop(server, self.config, poll_seconds=0), timeout=1)

        with self.assertRaises(ValueError):
            asyncio.run(observe())
        self.assertFalse(server.should_exit)
        self.assertFalse((self.service / "bootstrap.stop-ack.json").exists())
        rejected = json.loads((self.service / "bootstrap.stop-error.json").read_text(encoding="utf-8"))
        self.assertEqual(rejected["status"], "rejected")

    def test_serve_with_owned_stop_awaits_original_serve_return_without_process_proof(self):
        marker_path = self.service / "stop.request.json"

        class FakeServer:
            started = False
            should_exit = False

            async def serve(self):
                self.started = True
                marker_path.write_text(json.dumps({"schema_version": "upstream-agentops-stop/1", "stop_token": STOP_TOKEN}), encoding="utf-8")
                while not self.should_exit:
                    await asyncio.sleep(0)
                self.returned = True

        server = FakeServer()

        async def observe():
            return await asyncio.wait_for(bootstrap.serve_with_stop(server, self.config), timeout=1)

        result = asyncio.run(observe())
        self.assertTrue(server.returned)
        self.assertEqual(result["status"], "stopped")
        self.assertIs(result["original_serve_returned"], True)
        self.assertIs(result["process_exit_proven"], False)
        self.assertIs(result["database_retention_completed"], False)


if __name__ == "__main__":
    unittest.main()
