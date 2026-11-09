"""Fresh setup admission controls; no installer, Linux process or app runs."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agentops_native_probe_v6 as native
import inspect_agentops_runtime_v6 as inspector
import run_agentops_persistent_workspace_v7 as coordinator


class PersistentSetupTests(unittest.TestCase):
    def setUp(self):
        self.runs = ROOT / "tmp" / ("authored-persistent-v7-" + uuid.uuid4().hex)
        self.setup = self.runs / "dependencies-linux-v7"
        self.setup.mkdir(parents=True)

    def validate(self, value):
        (self.setup / "result.json").write_text(json.dumps(value), encoding="utf-8")
        with patch.object(native, "RUNS", self.runs), patch.object(native.original, "source_inventory", return_value=[]):
            return native.validate_setup()

    def test_failed_prior_setup_cannot_authorize_new_native_attempt(self):
        for value in ({"schema_version": "agentops-linux-setup/4", "status": "dependencies_ready"},
                      {"schema_version": "agentops-linux-setup/7", "status": "failed"}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Successful v7"):
                self.validate(value)

    def test_complete_status_requires_managed_capability(self):
        with self.assertRaisesRegex(ValueError, "managed capability"):
            self.validate({"schema_version": "agentops-linux-setup/7", "status": "dependencies_ready",
                "stage": "complete", "source_unchanged_after": True, "managed_capability_passed": False})

    def test_success_status_cannot_omit_capture_receipts(self):
        with self.assertRaisesRegex(ValueError, "complete capture receipts"):
            self.validate({"schema_version": "agentops-linux-setup/7", "status": "dependencies_ready",
                "stage": "complete", "source_unchanged_after": True, "managed_capability_passed": True,
                "source_files": [], "files": []})

    def test_old_inventory_schema_cannot_substitute_for_new_receipt_identity(self):
        with self.assertRaisesRegex(ValueError, "v6 inspection"):
            native.validate_inventory({"schema_version": "agentops-installed-runtime-inspection/5",
                "status": "installed_versions_match_lock", "python": [3, 13, 1],
                "platform": {"system": "Linux", "machine": "x86_64"}})

    def test_native_builtin_supported_without_python_shim(self):
        self.assertEqual(inspector.classify_native_module(sys), "builtin")
        with self.assertRaises(ValueError):
            inspector.classify_native_module(json)

    def test_windows_coordinator_cannot_reserve_linux_attempt(self):
        with patch.object(coordinator.sys, "platform", "win32"), self.assertRaisesRegex(ValueError, "Requires Linux"):
            coordinator.main()

    def test_old_plan_and_existing_reservation_never_execute(self):
        output = self.runs / "native-probe-v6"
        output.mkdir()
        (output / "plan.json").write_text('{"schema_version":"agentops-native-plan/5"}')
        with patch.object(native, "RUNS", self.runs), patch.object(native, "require_linux"), \
                patch.object(native.original, "capture") as capture:
            with self.assertRaisesRegex(ValueError, "native v6"):
                native.run(output)
            (output / "execution.json").write_text('{"authored":true}')
            with self.assertRaises(FileExistsError):
                native.run(output)
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
