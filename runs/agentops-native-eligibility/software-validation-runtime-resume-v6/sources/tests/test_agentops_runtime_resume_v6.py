"""Resume orchestration controls with authored receipts and no Linux execution."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resume_agentops_linux_workspace_v6 as resume


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class RuntimeResumeTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "tmp" / ("authored-resume-v6-" + uuid.uuid4().hex)
        self.prior = self.root / "prior"
        self.replica = self.root / "agentops-research-v5-authored"
        self.output = self.root / "new-attempt"
        self.replica.mkdir(parents=True)
        old = self.root / "scripts/old.py"
        old.parent.mkdir()
        old.write_bytes(b"# retained old input\n")
        self.inputs = [resume.previous.record(old, self.root)]
        resume.previous.copy_exact(self.root, self.replica, self.inputs)
        (self.prior / "workspace").mkdir(parents=True)
        resume.previous.copy_exact(self.root, self.prior / "workspace", self.inputs)
        (self.root / "scripts/new.py").write_bytes(b"# new versioned input\n")
        write(self.prior / "result.json", {
            "status": "failed", "native_result": "not_run", "http_result": "not_run",
            "parent_inputs_unchanged": True, "export_reference_failures": [],
            "linux_workspace": str(self.replica)})
        write(self.prior / "export-manifest.json", {
            "original_linux_root": str(self.replica), "files": self.inputs})
        write(self.prior / "execution.json", {"inputs": self.inputs})
        self.stages = []

    def stage(self, replica, label, arguments, timeout):
        self.assertEqual(replica, self.replica)
        self.stages.append(label)
        if label == "native-control":
            write(replica / "runs/agentops-native-eligibility/native-probe-v5/result.json",
                  {"status": "upstream_and_boundary_effect_check_passed"})
        if label == "http-control":
            write(replica / "runs/agentops-http-control/native-http-linux-v3/result.json",
                  {"status": "wire_and_effect_check_passed"})

    def invoke(self, stage=None):
        with ExitStack() as stack:
            for name, value in (("ROOT", self.root), ("PRIOR", self.prior),
                                ("OUTPUT", self.output), ("ADDITIONS", ["scripts/new.py"])):
                stack.enter_context(patch.object(resume, name, value))
            stack.enter_context(patch.object(resume.sys, "platform", "linux"))
            stack.enter_context(patch.object(resume.previous, "require_native_filesystem"))
            stack.enter_context(patch.object(resume, "capture", side_effect=stage or self.stage))
            stack.enter_context(redirect_stdout(io.StringIO()))
            resume.main()

    def result(self):
        return json.loads((self.output / "result.json").read_bytes())

    def test_success_requires_ordered_revalidation_native_and_http_stages(self):
        before = (self.prior / "result.json").read_bytes()
        self.invoke()
        self.assertEqual(self.stages, ["runtime-revalidation", "native-prepare",
                                     "native-control", "http-prepare", "http-control"])
        self.assertEqual(self.result()["status"], "native_and_http_controls_passed")
        self.assertEqual(self.result()["installations"], 0)
        self.assertEqual(self.result()["export_reference_failures"], [])
        self.assertEqual((self.prior / "result.json").read_bytes(), before)
        self.assertEqual((self.output / "workspace/scripts/new.py").read_bytes(),
                         (self.root / "scripts/new.py").read_bytes())

    def test_revalidation_failure_prevents_native_and_http_but_exports_evidence(self):
        def fail(replica, label, arguments, timeout):
            self.stages.append(label)
            raise ValueError("authored revalidation failure")
        with self.assertRaises(SystemExit):
            self.invoke(fail)
        self.assertEqual(self.stages, ["runtime-revalidation"])
        self.assertEqual(self.result()["native_result"], "not_run")
        self.assertEqual(self.result()["http_result"], "not_run")
        self.assertTrue((self.output / "export-manifest.json").is_file())

    def test_failed_native_result_blocks_http_even_if_stage_exits_cleanly(self):
        def stage(replica, label, arguments, timeout):
            self.stage(replica, label, arguments, timeout)
            if label == "native-control":
                write(replica / "runs/agentops-native-eligibility/native-probe-v5/result.json",
                      {"status": "failed"})
        with self.assertRaises(SystemExit):
            self.invoke(stage)
        self.assertEqual(self.stages, ["runtime-revalidation", "native-prepare", "native-control"])
        self.assertEqual(self.result()["native_result"], "failed")
        self.assertEqual(self.result()["http_result"], "not_run")

    def test_existing_replica_attempt_is_never_repeated(self):
        reservation = self.replica / "runs/agentops-native-eligibility/native-probe-v5"
        reservation.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            self.invoke()
        self.assertEqual(self.stages, [])
        self.assertFalse(self.output.exists())

    def test_changed_original_input_is_rejected_before_any_stage(self):
        (self.root / "scripts/old.py").write_bytes(b"changed parent input")
        with self.assertRaisesRegex(ValueError, "parent-side input changed"):
            self.invoke()
        self.assertEqual(self.stages, [])
        self.assertFalse(self.output.exists())

    def test_changed_linux_copy_is_rejected_before_any_stage(self):
        (self.replica / "scripts/old.py").write_bytes(b"changed Linux copy")
        with self.assertRaisesRegex(ValueError, "live Linux bytes changed"):
            self.invoke()
        self.assertEqual(self.stages, [])

    def test_missing_replica_does_not_trigger_reinstall(self):
        result = json.loads((self.prior / "result.json").read_bytes())
        result["linux_workspace"] = str(self.root / "agentops-research-v5-missing")
        write(self.prior / "result.json", result)
        with self.assertRaisesRegex(ValueError, "no reinstall attempted"):
            self.invoke()
        self.assertEqual(self.stages, [])

    def test_second_invocation_preserves_finished_result(self):
        self.invoke()
        before = (self.output / "result.json").read_bytes()
        self.stages.clear()
        with self.assertRaises(FileExistsError):
            self.invoke()
        self.assertEqual(self.stages, [])
        self.assertEqual((self.output / "result.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
