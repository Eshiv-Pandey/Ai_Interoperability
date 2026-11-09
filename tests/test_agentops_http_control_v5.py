"""Authored Linux gate/HTTP compatibility checks; no AgentOps or Linux execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agentops_http_control_v5 as control
from check_agentops_effect_v3 import check_record, seed_snapshot
from check_agentops_http_v2 import check
from test_agentops_socket_policy_v1 import policy_fixture

spec = importlib.util.spec_from_file_location("authored_wire_v1_for_linux", ROOT / "tests/test_agentops_http_control.py")
wire_fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire_fixtures)


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class LinuxHttpControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = seed_snapshot(control.evidence.SOURCE / "agents/data/incidents.db")

    def setUp(self):
        # Authored fixtures retained under ordinary-mode directories; this does
        # not alter upstream pytest's Linux mode-0700 fixture behavior.
        self.base = ROOT / "tmp" / ("authored-agentops-http-linux-v5-" + uuid.uuid4().hex)
        self.base.mkdir(parents=True)
        self.native = self.base / "native"
        self.native.mkdir()
        self.revalidation_record = {"path": "authored-revalidation", "sha256": "authored"}

    def authored_native(self):
        profile = wire_fixtures.fixtures.authored_profile(self.seed)
        profile.update(schema_version="agentops-passive-upstream-observation/3", socket_policy=policy_fixture())
        runtime = {"schema_version": "agentops-installed-runtime-inspection/6",
                   "status": "installed_versions_match_lock", "python": [3, 13, 1],
                   "platform": {"system": "Linux", "machine": "x86_64"}, "packages": []}
        write(self.native / "prepared-runtime.stdout.bin", runtime)
        write(self.native / "execution-runtime.stdout.bin", runtime)
        write(self.native / "seed-before.json", self.seed)
        write(self.native / "isolated-seed-before.json", self.seed)
        write(self.native / "preparation-result.json", {"status": "prepared"})
        write(self.native / "passive-profile.json", profile)
        effect = check_record(profile, self.seed)
        effect.update(schema_version="agentops-independent-effect-check/3",
                      profile_sha256=control.evidence.digest(self.native / "passive-profile.json")["sha256"],
                      seed_sha256=control.evidence.digest(control.evidence.SOURCE / "agents/data/incidents.db")["sha256"])
        write(self.native / "effect-check.json", effect)
        write(self.native / "plan.json", {"schema_version": "agentops-native-plan/7",
              "source_files": [], "harness_files": [], "runtime_setup": self.revalidation_record,
              "directory_capability_in_preparation": True,
              "runtime_inventory": control.evidence.digest(self.native / "prepared-runtime.stdout.bin"),
              "seed_snapshot": control.evidence.digest(self.native / "seed-before.json")})
        write(self.native / "execution.json", {"plan": control.evidence.digest(self.native / "plan.json")})
        write(self.native / "pytest-reports.json", {"exitstatus": 0, "reports": [
            {"nodeid": control.evidence.NODEID, "when": when, "outcome": "passed"}
            for when in ("setup", "call", "teardown")]})
        self.seal_native()

    def seal_native(self, **changes):
        result = {"schema_version": "agentops-native-result/7", "status": "upstream_and_boundary_effect_check_passed",
                  "source_unchanged_after": True, "pytest_returncode": 0, "independent_check": "passed",
                  "application_test_started": True, "live_model_calls": 0,
                  "files": [control.evidence.digest(path) for path in sorted(self.native.iterdir())
                            if path.is_file() and path.name != "result.json"]}
        result.update(changes)
        write(self.native / "result.json", result)

    def validate(self):
        with patch.object(control, "PREREQUISITE", self.native), \
                patch.object(control.native, "harness", return_value=[]), \
                patch.object(control.native, "validate_setup", return_value=self.revalidation_record), \
                patch.object(control.native, "installed_inventory", return_value=json.loads((self.native / "prepared-runtime.stdout.bin").read_bytes())):
            return control.validate_native([])

    def test_authored_native_evidence_passes_all_readonly_gates(self):
        self.authored_native()
        self.assertEqual(self.validate(), control.evidence.digest(self.native / "result.json"))

    def test_failed_or_windows_native_result_is_rejected(self):
        self.authored_native()
        for changes in ({"status": "failed"}, {"schema_version": "agentops-native-result/3"}, {"schema_version": "agentops-native-result/4"},
                        {"independent_check": "not_run"}, {"application_test_started": False}):
            self.seal_native(**changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "Linux native"):
                self.validate()

    def test_missing_and_duplicate_native_receipts_are_rejected(self):
        self.authored_native()
        result = json.loads((self.native / "result.json").read_text())
        for files in (result["files"][:-1], result["files"] + result["files"][:1]):
            write(self.native / "result.json", dict(result, files=files))
            with self.assertRaisesRegex(ValueError, "unique receipts"):
                self.validate()

    def test_native_receipt_byte_mutation_is_rejected(self):
        self.authored_native()
        write(self.native / "pytest-reports.json", {})
        with self.assertRaisesRegex(ValueError, "retained result"):
            self.validate()

    def test_distinct_phase_and_runtime_mismatch_rejected_even_with_new_hashes(self):
        self.authored_native()
        reports = json.loads((self.native / "pytest-reports.json").read_text())
        reports["reports"][-1]["when"] = "call"
        write(self.native / "pytest-reports.json", reports)
        self.seal_native()
        with self.assertRaisesRegex(ValueError, "setup/call/teardown"):
            self.validate()
        runtime = json.loads((self.native / "execution-runtime.stdout.bin").read_text())
        runtime["python"][-1] = 2
        write(self.native / "execution-runtime.stdout.bin", runtime)
        self.seal_native()
        with self.assertRaisesRegex(ValueError, "runtimes differ"):
            self.validate()

    def test_isolated_seed_and_effect_receipt_must_match(self):
        self.authored_native()
        isolated = copy.deepcopy(self.seed)
        isolated["user_version"] += 1
        write(self.native / "isolated-seed-before.json", isolated)
        self.seal_native()
        with self.assertRaisesRegex(ValueError, "seed snapshots"):
            self.validate()
        write(self.native / "isolated-seed-before.json", self.seed)
        effect = json.loads((self.native / "effect-check.json").read_text())
        effect["profile_sha256"] = "other"
        write(self.native / "effect-check.json", effect)
        self.seal_native()
        with self.assertRaisesRegex(ValueError, "effect-check receipt"):
            self.validate()

    def test_effect_semantics_rechecked_after_resealing(self):
        self.authored_native()
        profile = json.loads((self.native / "passive-profile.json").read_text())
        profile["network_attempts"] = [{"event": "socket.connect"}]
        write(self.native / "passive-profile.json", profile)
        effect = json.loads((self.native / "effect-check.json").read_text())
        effect["profile_sha256"] = control.evidence.digest(self.native / "passive-profile.json")["sha256"]
        write(self.native / "effect-check.json", effect)
        self.seal_native()
        with self.assertRaises(ValueError):
            self.validate()

    def test_windows_and_missing_native_stop_before_output_or_process(self):
        target = self.base / "http"
        with patch.object(sys, "platform", "win32"), patch.object(control.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "Linux"):
                control.prepare(target, 18761)
            with self.assertRaisesRegex(ValueError, "Linux"):
                control.run(target)
            spawn.assert_not_called()
        with patch.object(control.native, "require_linux"), patch.object(control, "RUNS", self.base), \
                patch.object(control.evidence, "source_inventory", return_value=[]), \
                patch.object(control, "PREREQUISITE", self.base / "missing"), \
                patch.object(control.subprocess, "Popen") as spawn:
            with self.assertRaises(FileNotFoundError):
                control.prepare(target, 18761)
            spawn.assert_not_called()
        self.assertFalse(target.exists())

    def test_existing_attempt_cannot_spawn_again(self):
        target = self.base / "http"
        target.mkdir()
        write(target / "execution.json", {"authored": True})
        with patch.object(control.native, "require_linux"), patch.object(control, "RUNS", self.base), \
                patch.object(control.subprocess, "Popen") as spawn:
            with self.assertRaises(FileExistsError):
                control.run(target)
            spawn.assert_not_called()

    def test_runtime_package_locations_use_selected_venv(self):
        runtime_root = self.base / "external/runtime/venv"
        for site in ("lib/python3.13/site-packages", "Lib/site-packages"):
            location = (runtime_root / site).relative_to(self.base).as_posix()
            metadata = {"packages": [{"name": name, "location": location}
                                     for name in ("a2a-sdk", "google-adk", "uvicorn")]}
            with patch.object(control, "ROOT", self.base), \
                    patch.object(control.native, "RUNTIME", runtime_root / "bin/python"), \
                    patch.object(control.native, "harness", return_value=[]), \
                    patch.object(control.evidence, "digest", side_effect=lambda path: {"path": str(path)}):
                rows = control.harness(metadata)
                self.assertTrue(any(str(runtime_root / site / "uvicorn/server.py") == row["path"] for row in rows))
                metadata["packages"][0]["location"] = "outside/venv"
                with self.assertRaisesRegex(ValueError, "outside"):
                    control.harness(metadata)

    def test_cleanup_errors_retained_instead_of_interrupting_result(self):
        process = Mock(pid=123, returncode=None)
        process.wait.side_effect = [control.subprocess.TimeoutExpired("authored", 20), OSError("wait failed")]
        result = {}
        with patch.object(control.evidence, "write_json", side_effect=OSError("stop write failed")), \
                patch.object(control.os, "killpg", create=True, side_effect=OSError("kill failed")):
            control.stop_owned_service(process, self.base, result)
        self.assertTrue(result["forced_service_stop"])
        self.assertEqual(len(result["cleanup_errors"]), 3)
        self.assertIsNone(result["service_returncode"])

    def test_v5_provenance_keeps_unchanged_wire_checker_contract(self):
        target = self.base / "wire"
        target.mkdir()
        files = wire_fixtures.authored_files(self.seed)
        plan = json.loads(files["plan.json"])
        plan["controller_version"] = "agentops-http-control/5"
        files["plan.json"] = wire_fixtures.encoded(plan)
        service = json.loads(files["service-result.json"])
        service.update(observer_version=2, socket_policy=policy_fixture(port=plan["port"]))
        files["service-result.json"] = wire_fixtures.encoded(service)
        for name, raw in files.items():
            (target / name).write_bytes(raw)
        report = check(target, self.seed)
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["bridge_qualification"])
        self.assertIsNone(report["request_version_header"])


if __name__ == "__main__":
    unittest.main()
