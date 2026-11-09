"""Authored artifact-integrity controls; no Linux/application execution."""
import copy
import json
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_agentops_linux_workspace_v5 as checker


class ExportCheckTests(unittest.TestCase):
    def setUp(self):
        self.run = ROOT / "tmp" / ("export-check-" + uuid.uuid4().hex)
        self.export = self.run / "workspace"
        self.export.mkdir(parents=True)
        path = self.export / "input.txt"
        path.write_bytes(b"authored input")
        self.row = checker.record(path, self.export)
        self.result = {"schema_version": "agentops-linux-filesystem-attempt/5", "status": "failed",
                       "parent_inputs_unchanged": True, "export_reference_failures": [],
                       "linux_workspace": "/tmp/example", "exported_files": 1}
        self.manifest = {"files": [self.row], "bytes": self.row["bytes"], "reference_failures": [],
                         "original_linux_root": "/tmp/example", "inert_symlinks": []}
        self.write("execution.json", {"inputs": [self.row]})
        self.write("result.json", self.result)
        self.write("export-manifest.json", self.manifest)
        self.write("linux-workspace.json", {"path": "/tmp/example"})

    def write(self, name, data):
        (self.run / name).write_text(json.dumps(data), encoding="utf-8")

    def test_authored_failed_package_integrity_checks_without_claiming_success(self):
        _, result, _ = checker.package_integrity(self.run, [self.row])
        self.assertEqual(result["status"], "failed")

    def test_missing_mandatory_input_rejected_even_with_consistent_manifest(self):
        self.manifest.update(files=[], bytes=0)
        self.result["exported_files"] = 0
        (self.export / "input.txt").unlink()
        self.write("export-manifest.json", self.manifest)
        self.write("result.json", self.result)
        with self.assertRaisesRegex(ValueError, "Mandatory"):
            checker.package_integrity(self.run, [self.row])

    def test_changed_bytes_and_undeclared_files_rejected(self):
        (self.export / "input.txt").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Changed"):
            checker.package_integrity(self.run, [self.row])
        (self.export / "input.txt").write_bytes(b"authored input")
        (self.export / "extra.txt").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "undeclared"):
            checker.package_integrity(self.run, [self.row])

    def test_duplicate_records_and_boolean_sizes_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            checker.verify_rows(self.export, [self.row, self.row])
        with self.assertRaisesRegex(ValueError, "byte length"):
            checker.verify_rows(self.export, [{**self.row, "bytes": True}])
        self.assertFalse(checker.zero(False))

    def test_windows_case_collision_rejected_before_alias_read(self):
        with self.assertRaisesRegex(ValueError, "Windows-colliding"):
            checker.verify_rows(self.export, [self.row, {**self.row, "path": "INPUT.TXT"}])

    def test_linux_path_mapping_uses_components(self):
        self.assertEqual(checker.linux_relative("/tmp/example/runs/data", "/tmp/example"), "runs/data")
        for name in ("/tmp/example-other/secret", "/tmp/example/../secret", "relative/path"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                checker.linux_relative(name, "/tmp/example")

    def test_inconsistent_roots_and_export_failures_rejected(self):
        self.manifest["original_linux_root"] = "/tmp/other"
        self.write("export-manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "roots"):
            checker.package_integrity(self.run, [self.row])
        self.manifest["original_linux_root"] = "/tmp/example"
        self.manifest["reference_failures"] = ["missing"]
        self.write("export-manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "references failed"):
            checker.package_integrity(self.run, [self.row])

    def test_duplicate_json_keys_rejected(self):
        (self.run / "ambiguous.json").write_text('{"status":"failed","status":"passed"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            checker.load(self.run / "ambiguous.json")

    def test_controller_receipt_requires_matching_successful_process_and_streams(self):
        label = "native-pipeline"
        for suffix in ("stdout", "stderr"):
            (self.run / f"{label}.{suffix}.bin").write_bytes(b"")
        receipt = {"argv": ["/usr/bin/python3", "-B", "-X", "utf8", "scripts/runner.py"],
                   "cwd": "/tmp/example", "linux_pid": 123,
                   "started_at_utc": "2026-10-26T00:00:00+00:00", "timed_out": False}
        self.write(label + ".started.json", receipt)
        receipt.update(returncode=0, finished_at_utc="2026-10-26T00:00:01+00:00",
                       streams=[checker.record(self.run / f"{label}.{suffix}.bin", self.run) for suffix in ("stdout", "stderr")])
        self.write(label + ".json", receipt)
        checker.stage_receipt(self.run, label, ["scripts/runner.py"], "/tmp/example")
        for field, value in (("returncode", False), ("returncode", 1), ("timed_out", True), ("linux_pid", True), ("cwd", "/tmp/other")):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(receipt)
                changed[field] = value
                self.write(label + ".json", changed)
                with self.assertRaises(ValueError):
                    checker.stage_receipt(self.run, label, ["scripts/runner.py"], "/tmp/example")

    def test_reader_rebases_digest_without_loading_archived_code(self):
        # Exercise trusted code/data separation with the already verified small
        # replica. No runtime imports or native/HTTP semantics are invoked here.
        review = ROOT / "runs/agentops-native-eligibility/replica-input-review-v5"
        inputs = checker.load(review / "result.json")["files"]
        http, sources = checker.validators_for(review / "workspace", inputs)
        self.assertEqual(len(sources), 421)
        actual = http.evidence.digest(ROOT / "scripts/agentops_http_control_v2.py")
        expected = next(row for row in inputs if row["path"] == "scripts/agentops_http_control_v2.py")
        self.assertEqual(actual, expected)
        self.assertTrue(Path(http.__file__).resolve().is_relative_to(ROOT / "scripts"))


if __name__ == "__main__":
    unittest.main()
