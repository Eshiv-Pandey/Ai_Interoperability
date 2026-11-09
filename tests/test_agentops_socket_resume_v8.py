"""Authored resume refusal/order tests; no Linux process or app executes."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resume_agentops_socket_observer_v8 as resume


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "tmp" / ("authored-socket-resume-" + uuid.uuid4().hex)
        self.base.mkdir()

    def test_non_linux_cannot_reserve_attempt(self):
        with patch.object(resume.sys, "platform", "win32"), patch.object(resume, "OUTPUT", self.base / "out"), \
                patch.object(resume, "capture") as capture:
            with self.assertRaisesRegex(ValueError, "Ubuntu"):
                resume.main()
            capture.assert_not_called()
            self.assertFalse((self.base / "out").exists())

    def test_existing_output_is_refused_before_reading_prerequisites(self):
        with patch.object(resume.sys, "platform", "linux"), patch.object(resume, "OUTPUT", self.base), \
                patch.object(resume.evidence, "load_json") as read:
            with self.assertRaises(FileExistsError):
                resume.main()
            read.assert_not_called()

    def test_retained_failure_is_recognized_without_relabeling_it(self):
        actual = resume.evidence.load_json(resume.PRIOR / "result.json")
        resume.validate_prior(actual)
        self.assertEqual(actual["status"], "failed")
        for key, value in (("native_result", "not_run"), ("native_result", "upstream_and_boundary_effect_check_passed"),
                           ("http_result", "wire_and_effect_check_passed"), ("parent_inputs_unchanged", False)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                resume.validate_prior(dict(actual, **{key: value}))

    def test_other_native_failure_cannot_authorize_correction(self):
        actual = resume.evidence.load_json(resume.PRIOR / "result.json")
        with patch.object(resume.evidence, "load_json", side_effect=[
                {"pytest_returncode": 1, "independent_check": "failed", "source_unchanged_after": True},
                {"status": "failed", "error": "ValueError: offline observer boundaries"},
                {"network_attempts": [{"event": "socket.bind"}]}]):
            with self.assertRaisesRegex(ValueError, "diagnosis"):
                resume.validate_prior(actual)

    def exercise(self, *, failure=None, changed_seal=False):
        replica = self.base / "agentops-research-v7-authored"
        replica.mkdir()
        prior, output, seal = self.base / "prior", self.base / "output", self.base / "seal.json"
        write(prior / "result.json", {"linux_workspace": str(replica)})
        write(prior / "export-manifest.json", {"original_linux_root": str(replica), "files": []})
        write(prior / "execution.json", {"inputs": []})
        write(seal, {"replica_inputs": [{"authored": "wrong"}] if changed_seal else []})
        stages = []

        def capture(root, label, arguments, timeout):
            stages.append(label)
            if label == failure:
                raise ValueError("authored stage failure")
            if label == "native-control":
                write(root / "runs/agentops-native-eligibility/native-probe-v7/result.json",
                      {"status": "upstream_and_boundary_effect_check_passed"})
            if label == "http-control":
                write(root / "runs/agentops-http-control/native-http-linux-v5/result.json",
                      {"status": "wire_and_effect_check_passed"})

        with patch.multiple(resume, PRIOR=prior, OUTPUT=output, SEAL=seal, ADDITIONS=[]), \
                patch.object(resume.sys, "platform", "linux"), patch.object(resume, "validate_prior"), \
                patch.object(resume.previous, "require_native_filesystem"), \
                patch.object(resume, "capture", side_effect=capture), \
                patch.object(resume, "export_evidence", return_value={"files": [], "reference_failures": []}):
            if changed_seal:
                with self.assertRaisesRegex(ValueError, "seal"):
                    resume.main()
                self.assertFalse(output.exists())
                self.assertEqual(stages, [])
            elif failure:
                with self.assertRaises(SystemExit):
                    resume.main()
                result = json.loads((output / "result.json").read_text())
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["http_result"], "not_run")
                self.assertEqual(stages, ["native-prepare", "native-control"])
            else:
                resume.main()
                self.assertEqual(stages, ["native-prepare", "native-control", "http-prepare", "http-control"])
                result = json.loads((output / "result.json").read_text())
                self.assertEqual(result["status"], "native_and_http_controls_passed")
                self.assertEqual(result["installations"], 0)

    def test_native_failure_stops_http_and_keeps_terminal_result(self):
        self.exercise(failure="native-control")

    def test_success_requires_all_four_ordered_stages(self):
        self.exercise()

    def test_changed_seal_refuses_all_execution(self):
        self.exercise(changed_seal=True)


if __name__ == "__main__":
    unittest.main()
