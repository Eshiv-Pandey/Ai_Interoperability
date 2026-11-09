"""Authored v5 revalidation gates; no installed application or Linux process runs."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agentops_native_probe_v5 as native


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class NativeRevalidationTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "tmp" / ("authored-native-v5-" + uuid.uuid4().hex)
        self.runs = self.base / "runs"
        self.directory = self.runs / "runtime-revalidation-v5"
        self.directory.mkdir(parents=True)
        self.old_setup = self.runs / "dependencies-linux-v4"
        self.old_setup.mkdir()
        self.inspector = self.base / "inspector.py"
        self.coordinator = self.base / "coordinator.py"
        self.inspector.write_text("# authored placeholder, never executed\n")
        self.coordinator.write_text("# authored placeholder, never executed\n")
        self.inventory = {"schema_version": "agentops-installed-runtime-inspection/5",
                          "status": "installed_versions_match_lock", "python": [3, 13, 1],
                          "platform": {"system": "Linux", "machine": "x86_64"}, "packages": [],
                          "fcntl_native": {"kind": "builtin", "provider_file": {"authored": True}}}
        write(self.directory / "plan.json", {"authored": True})
        write(self.directory / "runtime-inspection.stdout.bin", self.inventory)
        (self.directory / "runtime-inspection.stderr.bin").write_bytes(b"")
        write(self.directory / "runtime-inspection.json", {
            "returncode": 0, "timed_out": False,
            "stdout": native.original.digest(self.directory / "runtime-inspection.stdout.bin")})
        write(self.old_setup / "result.json", {"status": "failed", "stage": "runtime-inspection"})
        write(self.old_setup / "locked-sync.json", {"returncode": 0, "timed_out": False})
        self.seal()

    def seal(self, **changes):
        report = {"schema_version": "agentops-runtime-revalidation/5",
                  "status": "installed_runtime_revalidated", "source_unchanged_after": True,
                  "source_files": [], "runtime_inventory": native.original.digest(self.directory / "runtime-inspection.stdout.bin"),
                  "harness_files": [native.original.digest(path) for path in (self.inspector, self.coordinator)],
                  "original_setup_result": native.original.digest(self.old_setup / "result.json"),
                  "locked_sync_receipt": native.original.digest(self.old_setup / "locked-sync.json"),
                  "files": [native.original.digest(path) for path in sorted(self.directory.iterdir())
                            if path.is_file() and path.name != "result.json"]}
        report.update(changes)
        write(self.directory / "result.json", report)

    def validate(self):
        with patch.object(native, "RUNS", self.runs), patch.object(native, "INSPECTOR", self.inspector), \
                patch.object(native, "REVALIDATOR", self.coordinator), \
                patch.object(native.original, "source_inventory", return_value=[]):
            return native.validate_setup()

    def test_correct_revalidation_and_retained_failed_setup_are_accepted(self):
        self.assertEqual(self.validate(), native.original.digest(self.directory / "result.json"))
        self.assertEqual(json.loads((self.old_setup / "result.json").read_text())["status"], "failed")

    def test_prior_status_schema_or_source_cannot_substitute_for_revalidation(self):
        for changes in ({"status": "dependencies_ready"}, {"status": "failed"},
                        {"schema_version": "agentops-runtime-revalidation/4"},
                        {"source_unchanged_after": False}, {"source_files": [{"path": "wrong-source"}]}):
            self.seal(**changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.validate()

    def test_missing_or_duplicate_inventory_receipts_are_rejected(self):
        report = json.loads((self.directory / "result.json").read_text())
        inventory = report["runtime_inventory"]
        for files in ([row for row in report["files"] if row != inventory], report["files"] + [inventory]):
            self.seal(files=files)
            with self.assertRaisesRegex(ValueError, "unique receipts"):
                self.validate()

    def test_mutated_runtime_inventory_is_rejected(self):
        write(self.directory / "runtime-inspection.stdout.bin", {"changed": True})
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.validate()

    def test_failed_inspector_rejected_even_when_receipt_is_resealed(self):
        path = self.directory / "runtime-inspection.json"
        receipt = json.loads(path.read_text())
        for changes in ({"returncode": 1}, {"timed_out": True}, {"stdout": {"path": "wrong"}}):
            write(path, dict(receipt, **changes))
            self.seal()
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "successfully capture"):
                self.validate()

    def test_revalidation_requires_corrected_harness_and_successful_prior_sync(self):
        self.seal(harness_files=[])
        with self.assertRaisesRegex(ValueError, "corrected inspector"):
            self.validate()
        write(self.old_setup / "locked-sync.json", {"returncode": 1, "timed_out": False})
        self.seal()
        with self.assertRaisesRegex(ValueError, "sync did not succeed"):
            self.validate()

    def test_old_inventory_schema_is_rejected(self):
        old = dict(self.inventory, schema_version="agentops-installed-runtime-inspection/4")
        with self.assertRaisesRegex(ValueError, "corrected v5"):
            native.validate_inventory(old)

    def test_fresh_preparation_must_equal_revalidated_runtime(self):
        target = self.runs / "native-probe-v5"
        changed = copy.deepcopy(self.inventory)
        changed["python"][-1] = 2
        with patch.object(native, "RUNS", self.runs), patch.object(native, "require_linux"), \
                patch.object(native, "validate_setup", return_value={"authored": True}), \
                patch.object(native, "revalidated_inventory", return_value=self.inventory), \
                patch.object(native.original, "source_inventory", return_value=[]), \
                patch.object(native, "harness", return_value=[]), \
                patch.object(native, "runtime_inspection", return_value=changed), \
                patch.object(native.original, "capture") as subprocess_capture:
            with self.assertRaises(SystemExit):
                native.prepare(target)
            subprocess_capture.assert_not_called()
        result = json.loads((target / "preparation-result.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertIn("differs from the revalidated runtime", result["error"])
        self.assertFalse((target / "execution.json").exists())

    def test_old_native_plan_and_existing_attempt_never_execute(self):
        target = self.runs / "native-probe-v5"
        target.mkdir()
        write(target / "plan.json", {"schema_version": "agentops-native-plan/4"})
        with patch.object(native, "RUNS", self.runs), patch.object(native, "require_linux"), \
                patch.object(native.original, "capture") as capture:
            with self.assertRaisesRegex(ValueError, "native v5"):
                native.run(target)
            write(target / "execution.json", {"authored": True})
            with self.assertRaises(FileExistsError):
                native.run(target)
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
