"""Injected ownership/gate controls; no original/native/key/model execution."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("_ap2_native_gate_test", ROOT / "src/interoperability/ap2_hp_native_gate_v1.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
START = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def ref(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    path.write_bytes(module.encoded(value))
    return ref(path)


class MockOwner:
    def __init__(self, role):
        self.role = role
        self.started = False


class MockRuntime:
    def __init__(self):
        self.clock = START
        self.events = []
        self.physical = 3 * 1024**3
        self.commit = 4 * 1024**3
        self.occupied = []
        self.fail_role = None
        self.fail_cleanup = None
        self.collapse_after_first = False

    def now(self):
        return self.clock

    def bind_plan(self, plan):
        self.events.append(("bind", plan["run_id"]))

    def sleep(self, value):
        self.clock += timedelta(seconds=value)

    def memory_sample(self):
        return {"observed_at_utc": self.clock.isoformat(), "monotonic_ns": int((self.clock - START).total_seconds() * 1e9),
                "physical_available_bytes": self.physical, "commit_available_bytes": self.commit}

    def occupied_ports(self, ports):
        self.events.append(("ports", ports))
        return [port for port in self.occupied if port in ports]

    def make_owner(self, service, root):
        self.events.append(("owner", service["role"]))
        return MockOwner(service["role"])

    def launch_bootstrap(self, owner, plan, service, root):
        value = module.strict_json((root / "prelaunch.json").read_bytes())
        module.immediate_check(value, module.launch_binding(plan, service["role"]), self.memory_sample(), self.now())
        owner.started = True
        self.events.append(("mock_launch", service["module"], service["port"]))
        if self.collapse_after_first:
            self.physical = 1

    def wait_original_readiness(self, owner, plan, service, root):
        if self.fail_role == service["role"]:
            raise ValueError("Constructed readiness failure")
        return {"owned_connected_original_card": True, "binding": module.launch_binding(plan, service["role"]),
                "scope": "constructed injected-runtime observation, not original readiness"}

    def stop_owned(self, owner):
        self.events.append(("stop", owner.role))
        failed = self.fail_cleanup == owner.role
        return {"launch_attempted": owner.started, "handles_closed": not failed, "job_empty_observed": not failed,
                "errors": ["ConstructedCleanupFailure"] if failed else [], "authority_retained": failed}


class NativeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained = os.environ.get("AP2_GATE_TEST_ARTIFACT_ROOT")
        cls.temp = None if retained else tempfile.TemporaryDirectory(prefix="ap2-native-gate-constructed-")
        cls.base = Path(retained) if retained else Path(cls.temp.name)
        if retained:
            module.need(cls.base.is_absolute(), "Retained constructed artifact root must be absolute.")
            cls.base.mkdir(exist_ok=False)
        cls.source = cls.base / "source"
        original = ROOT / "docs/research/source-evidence/ap2-procurement-screen-v1/source"
        shutil.copytree(original, cls.source)
        certificates = ROOT / "docs/research/source-evidence/ap2-hp-cert-assets-v1/source"
        for name in module.CERT_ASSETS:
            destination = cls.source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(certificates / name, destination)
        cls.environment = cls.base / "mock-environment"
        cls.environment.mkdir()
        (cls.environment / "site-packages").mkdir()
        (cls.environment / "mock-python.exe").write_bytes(b"constructed nonexecutable environment identity")
        cls.python = ref(cls.environment / "mock-python.exe")
        cls.ps = cls.base / "mock-powershell.exe"
        cls.ps.write_bytes(b"constructed nonexecutable PowerShell identity")
        cls.hook = cls.base / "mock-usage-hook.py"
        cls.hook.write_bytes(b"raise AssertionError('This constructed hook must never execute in mocked tests')\n")
        cls.hook_review = write(cls.base / "mock-hook-review.json", {"status": "source_review_closed", "hook_sha256": ref(cls.hook)["sha256"],
            "contract": "enforce_before_every_provider_request", "scope": "constructed review fields only, not actual approval"})
        cls.allowance = cls.base / "constructed-allowance.txt"
        cls.allowance.write_bytes(b"Constructed provider allowance evidence, not a real entitlement")
        cls.ledger = cls.base / "constructed-ledger.json"
        cls.ledger.write_bytes(b"{}\n")

    @classmethod
    def tearDownClass(cls):
        if cls.temp is not None:
            cls.temp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="case-", dir=self.base))
        self.runtime = MockRuntime()
        environment = {"schema_version": "ap2-hp-native-environment/1", "status": "installed_hash_verified", "platform": "win32",
            "root": str(self.environment), "site_packages": str(self.environment / "site-packages"), "interpreter": self.python,
            "packages": dict(module.PACKAGES), "files": {"mock-python.exe": {"bytes": (self.environment / "mock-python.exe").stat().st_size,
                "sha256": self.python["sha256"]}}, "scope": "constructed environment manifest, not installed runtime"}
        self.env_ref = write(self.work / "environment.json", environment)
        self.plan = {"schema_version": module.SCHEMA, "run_id": "a" * 32, "model": module.MODEL,
            "output_root": str(self.work / "native-allocation"), "source_root": str(self.source),
            "services": deepcopy(list(module.SERVICES)), "ownership_policy": "per_service_windows_job_no_breakaway",
            "source_receipt": ref(ROOT / "docs/research/source-evidence/ap2-procurement-screen-v1/source-result.json"),
            "supplementary_assets": ref(ROOT / "docs/research/source-evidence/ap2-hp-cert-assets-v1/manifest.json"),
            "environment_manifest": self.env_ref, "interpreter": self.python, "powershell": ref(self.ps),
            "credential_helper": ref(ROOT / "scripts/with_gemini_key.ps1"),
            "owned_job_helper": ref(ROOT / "src/interoperability/windows_owned_job_v1.py"),
            "tcp_helper": ref(ROOT / "src/interoperability/windows_tcp_ownership_v1.py"),
            "bootstrap_helper": ref(ROOT / "src/interoperability/ap2_hp_native_gate_v1.py"),
            "windows_runtime": ref(ROOT / "src/interoperability/ap2_hp_windows_runtime_v1.py"),
            "bootstrap_script": ref(ROOT / "scripts/boot_ap2_hp_service_v1.py"),
            "usage_hook": ref(self.hook), "usage_hook_review": self.hook_review}
        self.usage = {"schema_version": "ap2-hp-model-usage-reservation/1", "status": "reserved_prospective_allowance",
            "configuration_sha256": module.configuration_hash(self.plan), "model": module.MODEL, "run_id": self.plan["run_id"],
            "remaining_model_calls": 7, "reserved_model_calls": 5, "counting_rules_verified": True, "reset_rules_verified": True,
            "reserved_at_utc": (START - timedelta(minutes=1)).isoformat(), "expires_at_utc": (START + timedelta(hours=1)).isoformat(),
            "hook_sha256": self.plan["usage_hook"]["sha256"], "allowance_evidence": [ref(self.allowance)], "ledger": ref(self.ledger)}
        self.refresh_usage()

    def refresh_usage(self):
        self.plan["usage_receipt"] = write(self.work / "usage.json", self.usage)

    def gate(self):
        return module.collect_gate(self.runtime, module.launch_binding(self.plan, "merchant"))

    def test_complete_byte_bound_contract_has_no_authentication_upgrade(self):
        value = module.validate_plan(self.plan, self.runtime.now())
        self.assertEqual(value["source_files"], 136)
        self.assertEqual(value["reserved_model_calls"], 5)
        self.assertFalse(value["source_authentication_proven"])
        self.assertFalse(value["provider_entitlement_authenticated"])
        self.assertEqual(self.runtime.events, [])

    def test_original_ports_and_module_order_cannot_be_changed(self):
        self.plan["services"][0]["port"] = 18001
        result = module.start_group(self.plan, self.runtime)
        self.assertEqual(result.report["status"], "refused_or_partial_owned_start")
        self.assertEqual(self.runtime.events, [])
        self.assertFalse(Path(self.plan["output_root"]).exists())

    def test_frozen_job_digest_cannot_be_replaced(self):
        self.plan["owned_job_helper"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(module.GateError, "Frozen reviewed helper"):
            module.validate_plan(self.plan, self.runtime.now())

    def test_source_tree_extra_file_refuses_before_any_owner(self):
        path = self.source / "constructed-extra.txt"
        path.write_bytes(b"not in source receipt")
        try:
            result = module.start_group(self.plan, self.runtime)
            self.assertEqual(self.runtime.events, [])
            self.assertEqual(result.report["status"], "refused_or_partial_owned_start")
        finally:
            path.unlink()

    def test_missing_original_certificate_refuses_before_owner(self):
        path = self.source / "code/samples/certs/ds_cert_sdjwt.pem"
        raw = path.read_bytes()
        path.unlink()
        try:
            group = module.start_group(self.plan, self.runtime)
            self.assertEqual(self.runtime.events, [])
            self.assertEqual(group.owners, [])
            self.assertEqual(group.report["status"], "refused_or_partial_owned_start")
        finally:
            path.write_bytes(raw)

    def test_tampered_original_certificate_refuses_before_owner(self):
        path = self.source / "code/samples/certs/issuer_cert_sdjwt.pem"
        raw = path.read_bytes()
        path.write_bytes(raw + b"constructed tamper")
        try:
            group = module.start_group(self.plan, self.runtime)
            self.assertEqual(self.runtime.events, [])
            self.assertEqual(group.owners, [])
            self.assertIn("exact original asset", group.report["reason"])
        finally:
            path.write_bytes(raw)

    def test_uninstalled_environment_receipt_refused(self):
        value = module.strict_json(Path(self.env_ref["path"]).read_bytes())
        value["status"] = "resolved_not_installed"
        self.plan["environment_manifest"] = write(Path(self.env_ref["path"]), value)
        with self.assertRaisesRegex(module.GateError, "Installed AP2 environment"):
            module.validate_plan(self.plan, self.runtime.now())

    def test_expired_usage_reservation_refused(self):
        self.usage["expires_at_utc"] = (START - timedelta(seconds=1)).isoformat(); self.refresh_usage()
        with self.assertRaisesRegex(module.GateError, "future-dated or expired"):
            module.validate_plan(self.plan, self.runtime.now())

    def test_assumed_or_zero_provider_allowance_refused(self):
        self.usage["remaining_model_calls"] = 0; self.refresh_usage()
        with self.assertRaisesRegex(module.GateError, "allowance"):
            module.validate_plan(self.plan, self.runtime.now())

    def test_usage_reservation_cannot_be_borrowed_by_different_run(self):
        self.plan["run_id"] = "b" * 32
        with self.assertRaisesRegex(module.GateError, "not bound"):
            module.validate_plan(self.plan, self.runtime.now())

    def test_two_timed_samples_accept_fixed_minima(self):
        self.runtime.physical, self.runtime.commit = 1024**3, 2 * 1024**3
        gate = self.gate()
        value = module.validate_gate(gate, module.launch_binding(self.plan, "merchant"), self.runtime.now())
        self.assertEqual(value["age_seconds"], 0)

    def test_each_physical_observation_must_pass(self):
        for index in (0, 1):
            gate = self.gate(); gate["samples"][index]["physical_available_bytes"] = 1024**3 - 1
            with self.assertRaisesRegex(module.GateError, "fixed minima"):
                module.validate_gate(gate, module.launch_binding(self.plan, "merchant"), self.runtime.now())

    def test_commit_gate_and_boolean_counter_rejected(self):
        gate = self.gate(); gate["samples"][0]["commit_available_bytes"] = 2 * 1024**3 - 1
        with self.assertRaises(module.GateError):
            module.validate_gate(gate, module.launch_binding(self.plan, "merchant"), self.runtime.now())
        gate = self.gate(); gate["samples"][0]["monotonic_ns"] = True
        with self.assertRaisesRegex(module.GateError, "integer monotonic"):
            module.validate_gate(gate, module.launch_binding(self.plan, "merchant"), self.runtime.now())

    def test_utc_monotonic_gap_mismatch_refused(self):
        gate = self.gate(); gate["samples"][1]["monotonic_ns"] += 2_000_000_000
        with self.assertRaisesRegex(module.GateError, "consistent UTC/monotonic"):
            module.validate_gate(gate, module.launch_binding(self.plan, "merchant"), self.runtime.now())

    def test_stale_or_other_role_gate_refused(self):
        gate = self.gate()
        with self.assertRaisesRegex(module.GateError, "older than 60"):
            module.validate_gate(gate, module.launch_binding(self.plan, "merchant"), self.runtime.now() + timedelta(seconds=61))
        with self.assertRaisesRegex(module.GateError, "binding differs"):
            module.validate_gate(gate, module.launch_binding(self.plan, "processor"), self.runtime.now())

    def test_immediate_sample_below_gate_or_stale_refused(self):
        gate = self.gate(); sample = self.runtime.memory_sample(); sample["physical_available_bytes"] = 1
        with self.assertRaisesRegex(module.GateError, "fixed minima"):
            module.immediate_check(gate, module.launch_binding(self.plan, "merchant"), sample, self.runtime.now())
        sample = self.runtime.memory_sample()
        with self.assertRaisesRegex(module.GateError, "Immediate bootstrap"):
            module.immediate_check(gate, module.launch_binding(self.plan, "merchant"), sample, self.runtime.now() + timedelta(seconds=3))

    def test_valid_mocked_three_service_starts_retain_owner_authority(self):
        group = module.start_group(self.plan, self.runtime)
        self.assertEqual(group.report["status"], "owned_original_services_ready_without_case_execution")
        self.assertEqual([item for item in self.runtime.events if item[0] == "mock_launch"],
            [("mock_launch", service["module"], service["port"]) for service in module.SERVICES])
        self.assertTrue((Path(self.plan["output_root"]) / ".temp-db").is_dir())
        self.assertEqual(len(group.owners), 3)
        self.assertFalse(group.report["native_qualification_established"])
        self.assertTrue(group.stop())
        self.assertEqual([item for item in self.runtime.events if item[0] == "stop"], [("stop", "processor"), ("stop", "credentials"), ("stop", "merchant")])

    def test_occupied_port_refuses_without_owner_or_shared_state(self):
        self.runtime.occupied = [8002]
        group = module.start_group(self.plan, self.runtime)
        self.assertFalse(any(item[0] == "owner" for item in self.runtime.events))
        self.assertFalse((Path(self.plan["output_root"]) / ".temp-db").exists())
        self.assertIn("occupied", group.report["reason"])

    def test_headroom_loss_after_first_start_stops_only_owned_service(self):
        self.runtime.collapse_after_first = True
        group = module.start_group(self.plan, self.runtime)
        self.assertEqual([item[1] for item in self.runtime.events if item[0] == "owner"], ["merchant"])
        self.assertEqual([item for item in self.runtime.events if item[0] == "stop"], [("stop", "merchant")])
        self.assertEqual(group.owners, [])

    def test_second_readiness_failure_stops_created_jobs_without_third(self):
        self.runtime.fail_role = "credentials"
        group = module.start_group(self.plan, self.runtime)
        self.assertEqual([item[1] for item in self.runtime.events if item[0] == "owner"], ["merchant", "credentials"])
        self.assertEqual([item for item in self.runtime.events if item[0] == "stop"], [("stop", "credentials"), ("stop", "merchant")])
        self.assertEqual(group.owners, [])

    def test_cleanup_failure_retains_live_authority_explicitly(self):
        self.runtime.fail_role = "credentials"; self.runtime.fail_cleanup = "merchant"
        group = module.start_group(self.plan, self.runtime)
        self.assertEqual(group.report["status"], "cleanup_incomplete_authority_retained")
        self.assertEqual([role for role, owner in group.owners], ["merchant"])
        self.runtime.fail_cleanup = None
        self.assertTrue(group.stop())

    def test_start_result_publication_failure_settles_all_owners(self):
        original_publish = module.publish
        def fail_result(path, value):
            if Path(path).name == "start-result.json":
                raise OSError("Constructed final publication failure")
            return original_publish(path, value)
        with patch.object(module, "publish", side_effect=fail_result):
            group = module.start_group(self.plan, self.runtime)
        self.assertEqual(group.report["status"], "start_result_publication_failed")
        self.assertEqual(group.owners, [])
        self.assertEqual([item for item in self.runtime.events if item[0] == "stop"],
            [("stop", "processor"), ("stop", "credentials"), ("stop", "merchant")])

    def test_start_result_publication_failure_retains_failed_cleanup_authority(self):
        original_publish = module.publish
        self.runtime.fail_cleanup = "merchant"
        def fail_result(path, value):
            if Path(path).name == "start-result.json":
                raise OSError("Constructed final publication failure")
            return original_publish(path, value)
        with patch.object(module, "publish", side_effect=fail_result):
            group = module.start_group(self.plan, self.runtime)
        self.assertEqual(group.report["status"], "cleanup_incomplete_authority_retained")
        self.assertEqual([role for role, owner in group.owners], ["merchant"])
        self.runtime.fail_cleanup = None
        self.assertTrue(group.stop())

    def test_consumed_output_never_restarted(self):
        Path(self.plan["output_root"]).mkdir()
        group = module.start_group(self.plan, self.runtime)
        self.assertIn("consumed", group.report["reason"])
        self.assertFalse(any(item[0] == "owner" for item in self.runtime.events))

    def test_bootstrap_rejects_arbitrary_helper_before_execution(self):
        marker = self.work / "must-not-exist.txt"
        evil = self.work / "not-a-reviewed-helper.py"
        evil.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\n", encoding="utf-8")
        path = self.work / "untrusted-plan.json"
        write(path, {"bootstrap_helper": ref(evil)})
        result = subprocess.run([sys.executable, "-I", "-S", "-B", str(ROOT / "scripts/boot_ap2_hp_service_v1.py"),
            "--plan", str(path), "--role", "merchant", "--stage", "before-key", "--job-handle", "1"], capture_output=True, check=False, timeout=30)
        (self.work / "bootstrap-refusal.stdout.bin").write_bytes(result.stdout)
        (self.work / "bootstrap-refusal.stderr.bin").write_bytes(result.stderr)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(marker.exists())
        self.assertEqual(json.loads(result.stdout)["status"], "refused_or_original_stage_failed")

    def test_direct_readiness_rejects_arbitrary_helper_before_execution(self):
        runtime_path = ROOT / "src/interoperability/ap2_hp_windows_runtime_v1.py"
        spec = importlib.util.spec_from_file_location("_ap2_native_runtime_test", runtime_path)
        runtime_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime_module)
        runtime = runtime_module.WindowsRuntime.__new__(runtime_module.WindowsRuntime)
        marker = self.work / "readiness-must-not-exist.txt"
        evil = self.work / "arbitrary-readiness-helper.py"
        evil.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\n", encoding="utf-8")
        self.plan["bootstrap_helper"] = ref(evil)
        with self.assertRaisesRegex(ValueError, "arbitrary plan-selected"):
            runtime.wait_original_readiness(None, self.plan, module.SERVICES[0], self.work)
        self.assertFalse(marker.exists())

    def test_exclusive_publication_retains_pending_and_final_bytes(self):
        path = self.work / "exclusive-publication.json"
        first = {"scope": "constructed publication", "value": 1}
        module.publish(path, first)
        self.assertEqual(path.read_bytes(), module.encoded(first))
        self.assertEqual(path.with_name(path.name + ".pending").read_bytes(), path.read_bytes())
        with self.assertRaises(FileExistsError):
            module.publish(path, {"value": 2})
        self.assertEqual(path.read_bytes(), module.encoded(first))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(module.GateError, "Duplicate"):
            module.strict_json(b'{"samples":[],"samples":[]}')


if __name__ == "__main__":
    unittest.main()
