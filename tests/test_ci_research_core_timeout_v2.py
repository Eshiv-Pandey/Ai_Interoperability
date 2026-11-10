"""Actual Linux stdlib subprocess cleanup; never an application or model run."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_research_core_v2 as driver


CHILD = "import signal,sys,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN) if sys.argv[2]=='ignore' else None;time.sleep(1.4);Path(sys.argv[1]).write_text('late child write')"
COORDINATOR = "import json,os,signal,subprocess,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN) if sys.argv[3]=='ignore' else None;p=subprocess.Popen([sys.executable,'-I','-S','-B','-c',sys.argv[1],sys.argv[2],sys.argv[3]]);print(json.dumps({'coordinator_pid':os.getpid(),'child_pid':p.pid}),flush=True);time.sleep(30)"


@unittest.skipUnless(sys.platform == "linux", "Actual owned process-group tests require Linux")
class LinuxTimeoutTests(unittest.TestCase):
    def setUp(self):
        retained = os.environ.get("CI_TIMEOUT_TEST_OUTPUT")
        if retained:
            self.base = Path(retained) / self._testMethodName
            self.base.mkdir(exist_ok=False)
        else:
            temporary = tempfile.TemporaryDirectory(prefix="core-owned-timeout-")
            self.addCleanup(temporary.cleanup)
            self.base = Path(temporary.name)
        (self.base / "checkout").mkdir()
        self.before_subreaper = driver.subreaper_state()

    def invoke_child(self, mode):
        marker = self.base / "late-marker.txt"
        argv = [sys.executable, "-I", "-S", "-B", "-c", COORDINATOR, CHILD, str(marker), mode]
        receipt = driver.invoke(self.base, "timeout", argv, .3)
        identities = json.loads((self.base / "commands/timeout/stdout.bin").read_bytes())
        group = receipt["owned_group"]
        self.assertTrue(receipt["timed_out"])
        self.assertEqual(receipt["pid"], identities["coordinator_pid"])
        self.assertIn(identities["child_pid"], [item["pid"] for item in group["initial_members"]])
        self.assertIn(identities["child_pid"], [item["pid"] for item in group["adopted_children_reaped"]])
        self.assertTrue(group["parent_reaped"])
        self.assertTrue(group["final_empty"])
        self.assertEqual(driver.group_members(receipt["pid"]), [])
        self.assertEqual(driver.subreaper_state(), self.before_subreaper)
        self.assertEqual(driver._OPEN_GROUPS, set())
        self.assertTrue(receipt["coordinator_source_unchanged"])
        self.assertEqual(len(receipt["coordinator_source_before"]), 2)
        time.sleep(1.5)  # Longer than the child's original write delay.
        self.assertFalse(marker.exists(), "Terminated child performed a late write")
        driver.guarded_write(self.base / "delayed-marker-check.json", {
            "coordinator_pid": identities["coordinator_pid"], "child_pid": identities["child_pid"],
            "checked_at": driver.core.now(), "wait_after_return_seconds": 1.5,
            "child_marker_delay_seconds": 1.4, "marker_exists": marker.exists(),
            "group_members_after_wait": driver.group_members(receipt["pid"]),
            "subreaper_state_restored": driver.subreaper_state() == self.before_subreaper,
            "open_groups": sorted(driver._OPEN_GROUPS)})
        return receipt

    def test_timeout_reaps_coordinator_and_delayed_child_before_return(self):
        receipt = self.invoke_child("term")
        self.assertIn("SIGTERM", receipt["owned_group"]["signals"])

    def test_sigterm_ignoring_group_is_killed_and_reaped(self):
        receipt = self.invoke_child("ignore")
        self.assertIn("SIGKILL", receipt["owned_group"]["signals"])

    def test_normal_output_and_return_code_are_preserved(self):
        argv = [sys.executable, "-I", "-S", "-B", "-c", "import sys;print('normal-output');print('normal-error',file=sys.stderr)"]
        result = driver.invoke(self.base, "normal", argv, 2)
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["timed_out"])
        self.assertEqual((self.base / "commands/normal/stdout.bin").read_bytes(), b"normal-output\n")
        self.assertEqual((self.base / "commands/normal/stderr.bin").read_bytes(), b"normal-error\n")
        self.assertTrue(result["owned_group"]["final_empty"])
        self.assertTrue(result["coordinator_source_unchanged"])
        self.assertEqual(result["owned_group"]["signals"], [])
        self.assertEqual(driver.subreaper_state(), self.before_subreaper)

    def test_unconfirmed_ownership_blocks_new_commands_and_manifest_sealing(self):
        with patch.object(driver, "_OPEN_GROUPS", {999999}):
            with self.assertRaisesRegex(ValueError, "blocked"):
                driver.invoke(self.base, "blocked", [sys.executable, "-c", "pass"], 1)
            with self.assertRaisesRegex(ValueError, "Cannot seal"):
                driver.guarded_write(self.base / "retained-manifest.json", {})
        self.assertFalse((self.base / "commands/blocked").exists())
        self.assertFalse((self.base / "retained-manifest.json").exists())


class PlatformGuardTests(unittest.TestCase):
    def test_windows_execution_is_rejected_before_allocation(self):
        with tempfile.TemporaryDirectory(prefix="core-platform-guard-") as tmp:
            output = Path(tmp) / "not-created"
            with patch.object(driver.sys, "platform", "win32"):
                with self.assertRaisesRegex(ValueError, "requires Linux"):
                    driver.execute(output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
