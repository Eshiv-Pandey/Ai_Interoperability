"""Synthetic evidence only: no applications, services or benchmarks execute."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_agentops_admission_v3 as exporter


class AdmissionExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "source"
        self.root.mkdir()
        self.output = self.base / "export"
        self.code = self.write("src/interoperability/admission.py", b"# exact input\r\n")
        self.plan = {"schema_version": "agentops-admission-live-preparation/3",
                     "workspace": str(self.root), "reuse_root": "/original/runtime/workspace",
                     "runtime_python": "/original/runtime/workspace/venv/bin/python",
                     "bridge_runtime": "/original/runtime/workspace/bridge",
                     "inputs": [self.record(self.code)],
                     "python_runtime_inputs": [{"path": "external/runtime/not-exported.py", "bytes": 1,
                                                "sha256": "0" * 64}]}
        self.save_plan()

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def write_json(self, name, value):
        return self.write(name, (json.dumps(value, indent=2) + "\r\n").encode())

    def save_plan(self):
        return self.write_json(exporter.PLAN, self.plan)

    def record(self, path):
        raw = path.read_bytes()
        return {"path": path.relative_to(self.root).as_posix(), "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}

    def terminal(self, status="strict_success", **extra):
        return self.write_json(exporter.TERMINAL, {
            "schema_version": "agentops-admission-live-group/1", "status": status,
            "started_at_utc": "2026-10-29T00:00:00+00:00", "finished_at_utc": "2026-10-29T00:00:01+00:00",
            "plan": self.record(self.root / exporter.PLAN),
            "cases": {"N11": {"status": "recorded", "strict_success": True},
                      "B7": {"status": "recorded", "strict_success": True}}, **extra})

    def export(self, output=None):
        output = output or self.output
        report = exporter.export_workspace(self.root, output)
        manifest = json.loads((output / "manifest.json").read_bytes())
        self.assertEqual(json.loads((output / "result.json").read_bytes()), report)
        self.assertEqual(report["manifest"]["sha256"], hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest())
        return report, manifest

    def test_exact_scope_includes_all_adverse_and_temporary_bytes_without_following_references(self):
        historical = self.write("runs/agentops-http-control/bridge-diagnostic-v1-B7/result.json", b"historical")
        runtime = self.write("external/runtime/not-exported.py", b"runtime source")
        other_code = self.write("scripts/not-staged.py", b"not staged")
        ignored = self.write_json("runs/unrelated.json", {"path": "unrelated"})
        self.write_json(exporter.TREES[2] + "/diagnostic.json", {
            "external": str(runtime), "nested": self.record(runtime), "prior": self.record(historical)})
        self.write(exporter.TREES[1] + "/temp/actual.sqlite-wal", b"\0\xffwal")
        self.write(exporter.TREES[1] + "/service.stderr.bin", b"failed output\r\n")
        self.write_json(exporter.GROUP + "/attempt/B7.skipped.json", {"status": "skipped"})
        self.terminal("attempts_recorded", cases={"N11": {"status": "failed"}, "B7": {"status": "skipped"}})
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        report, manifest = self.export()
        self.assertEqual(report["status"], "exported")
        self.assertEqual(report["group_execution"]["status"], "attempts_recorded")
        self.assertEqual(report["group_execution"]["cases"]["B7"]["status"], "skipped")
        self.assertEqual(report["reuse_root"], self.plan["reuse_root"])
        self.assertFalse(report["external_runtime_closure_copied"])
        excluded = {path.relative_to(self.root).as_posix() for path in (historical, runtime, other_code, ignored)}
        expected = set(before) - excluded
        self.assertEqual({row["path"] for row in manifest["copied"]["files"]}, expected)
        self.assertEqual(manifest["source_before"], manifest["source_after"])
        self.assertEqual(manifest["source_before"]["files"], manifest["copied"]["files"])
        self.assertTrue(report["sources_unchanged"])
        for name in expected:
            self.assertEqual((self.output / "workspace" / name).read_bytes(), before[name])
        self.assertEqual({path.relative_to(self.root).as_posix(): path.read_bytes()
                          for path in self.root.rglob("*") if path.is_file()}, before)

    def test_startup_failure_diagnostics_are_copied_without_changing_the_failed_case(self):
        prefix = exporter.TREES[1]
        samples = {
            prefix + '/service/startup-diagnostics/lifecycle.jsonl': b'{"phase":"startup_monitor_started"}\n',
            prefix + '/service/startup-diagnostics/startup-stacks.txt': b'Startup traceback retained\n',
            prefix + '/startup-check.json': b'{"valid":true,"complete":false}\n',
            prefix + '/interpreter-exit-check.json': b'{"valid":false,"complete":false}\n'}
        for name, raw in samples.items():
            self.write(name, raw)
        self.terminal('attempts_recorded', cases={'N11': {'status': 'failed', 'strict_success': False},
                                                'B7': {'status': 'skipped', 'strict_success': False}})
        report, manifest = self.export()
        self.assertEqual(report['status'], 'exported')
        self.assertEqual(report['group_execution']['cases']['N11']['status'], 'failed')
        self.assertEqual(manifest['scope']['preparation_schema'], 'agentops-admission-live-preparation/3')
        for name, raw in samples.items():
            self.assertEqual((self.output / 'workspace' / name).read_bytes(), raw)

    def test_all_terminal_statuses_are_retained_separately_from_export_status(self):
        for index, status in enumerate(sorted(exporter.TERMINAL_STATUSES)):
            with self.subTest(status=status):
                self.terminal(status)
                report, _ = self.export(self.base / ("export-" + str(index)))
                self.assertEqual(report["status"], "exported")
                self.assertEqual(report["group_execution"]["status"], status)
                self.assertEqual(report["group_execution"]["record_status"], "terminal")

    def test_prepared_only_or_incomplete_records_are_never_upgraded(self):
        report, manifest = self.export()
        self.assertEqual(report["status"], "exported")
        self.assertIsNone(report["group_execution"]["status"])
        self.assertEqual(report["group_execution"]["record_status"], "missing")
        self.assertEqual(manifest["source_before"]["missing_scope_directories"], list(exporter.TREES[1:]))
        for name in ("N11", "B7"):
            self.assertEqual(report["group_execution"]["cases"][name]["record_status"], "missing")
        self.terminal("failed", cases={"N11": {"status": "unexecuted"}}, finished_at_utc=None)
        report, _ = self.export(self.base / "partial")
        self.assertEqual(report["status"], "exported")
        self.assertEqual(report["group_execution"]["status"], "failed")
        self.assertEqual(report["group_execution"]["record_status"], "incomplete")
        self.assertEqual(report["group_execution"]["cases"]["N11"]["status"], "unexecuted")

    def test_invalid_terminal_bytes_remain_exact_and_explicit(self):
        raw = b'{"status":"failed",'
        self.write(exporter.TERMINAL, raw)
        report, _ = self.export()
        self.assertEqual(report["status"], "exported")
        self.assertEqual(report["group_execution"]["record_status"], "invalid")
        self.assertEqual((self.output / "workspace" / exporter.TERMINAL).read_bytes(), raw)

    def test_overwrite_is_refused_and_first_export_unchanged(self):
        self.export()
        original = {path.relative_to(self.output).as_posix(): path.read_bytes()
                    for path in self.output.rglob("*") if path.is_file()}
        with self.assertRaises(FileExistsError):
            self.export()
        self.assertEqual({path.relative_to(self.output).as_posix(): path.read_bytes()
                          for path in self.output.rglob("*") if path.is_file()}, original)

    def test_overlapping_output_is_refused(self):
        for destination in (self.root, self.root / "new-export", self.base):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                exporter.export_workspace(self.root, destination)

    def test_traversal_and_noncanonical_input_paths_create_failed_attempt_without_escape(self):
        for index, name in enumerate(("../secret", "/etc/passwd", "C:/secret", "src\\secret",
                                      "./src/secret", "src//secret", "src/../secret", "")):
            with self.subTest(name=name):
                self.plan["inputs"][0]["path"] = name
                self.save_plan()
                destination = self.base / ("invalid-" + str(index))
                report, manifest = self.export(destination)
                self.assertEqual(report["status"], "failed")
                self.assertTrue(manifest["failures"])
                self.assertEqual(report["copied_files"], 0)
                with self.assertRaises(FileExistsError):
                    self.export(destination)

    def test_staged_hash_mismatch_retains_actual_bytes_and_fails(self):
        self.code.write_bytes(b"modified before export")
        report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["sources_unchanged"])
        self.assertTrue(report["copies_match_source_before"])
        self.assertTrue(any("differs from preparation plan" in issue for issue in manifest["failures"]))
        self.assertEqual((self.output / "workspace" / self.code.relative_to(self.root)).read_bytes(), self.code.read_bytes())

    def test_missing_input_is_explicit_failure_with_partial_evidence_retained(self):
        self.code.unlink()
        self.terminal("failed")
        report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertFalse(manifest["source_before"]["complete"])
        self.assertIsNone(report["sources_unchanged"])
        self.assertTrue((self.output / "workspace" / exporter.TERMINAL).is_file())

    def test_source_mutation_during_copy_is_detected(self):
        original = exporter.read_file

        def mutate(root, name, destination=None):
            value = original(root, name, destination)
            if destination is not None and name == self.code.relative_to(self.root).as_posix():
                self.code.write_bytes(b"changed after copy")
            return value

        with patch.object(exporter, "read_file", mutate):
            report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["sources_unchanged"])
        self.assertTrue(report["copies_match_source_before"])
        self.assertNotEqual(manifest["source_before"]["files"], manifest["source_after"]["files"])

    def test_new_run_file_during_copy_changes_inventory(self):
        original = exporter.read_file

        def add_file(root, name, destination=None):
            value = original(root, name, destination)
            if destination is not None and root == self.root:
                self.write(exporter.GROUP + "/new-partial.bin", b"new evidence")
            return value

        with patch.object(exporter, "read_file", add_file):
            report, _ = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["sources_unchanged"])

    def make_symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            self.skipTest("Host does not permit test symlinks: " + str(error))

    def test_source_file_symlink_is_refused(self):
        target = self.base / "outside.py"
        target.write_bytes(self.code.read_bytes())
        self.code.unlink()
        self.make_symlink(self.code, target)
        report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("Symlink" in item for item in manifest["failures"]))
        self.assertFalse((self.output / "workspace" / self.code.relative_to(self.root)).exists())

    def test_source_parent_symlink_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "body.bin").write_bytes(b"outside")
        group = self.root / exporter.GROUP
        self.make_symlink(group / "linked", outside, directory=True)
        report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("Symlink" in item for item in manifest["failures"]))
        self.assertFalse((self.output / "workspace" / exporter.GROUP / "linked/body.bin").exists())

    def test_output_parent_and_workspace_symlinks_are_refused_before_writing(self):
        alias = self.base / "source-alias"
        self.make_symlink(alias, self.root, directory=True)
        with self.assertRaises(ValueError):
            exporter.export_workspace(alias, self.output)
        destination = self.base / "destination"
        destination.mkdir()
        link = self.base / "destination-alias"
        self.make_symlink(link, destination, directory=True)
        with self.assertRaises(ValueError):
            exporter.export_workspace(self.root, link / "new")
        self.assertFalse((destination / "new").exists())

    def test_import_has_no_filesystem_side_effects_and_cli_is_usable(self):
        code = "import sys; sys.path.insert(0, sys.argv[1]); import export_agentops_admission_v3"
        imported = subprocess.run([sys.executable, "-B", "-c", code, str(Path(exporter.__file__).parent)],
                                  cwd=self.base, capture_output=True, timeout=15)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(imported.stdout, b"")
        result = subprocess.run([sys.executable, "-B", exporter.__file__, "--workspace", str(self.root),
                                 "--output", str(self.output)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "exported")

    def test_only_preparation_schema_three_is_accepted(self):
        for index, schema in enumerate(("agentops-admission-live-preparation/1", "agentops-admission-live-preparation/2", None)):
            with self.subTest(schema=schema):
                self.plan["schema_version"] = schema
                self.save_plan()
                report, manifest = self.export(self.base / ("schema-" + str(index)))
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["copied_files"], 0)
                self.assertTrue(any("Malformed preparation plan" in issue for issue in manifest["failures"]))

    def test_exact_exporter_source_is_retained_outside_workspace(self):
        original = Path(exporter.__file__).read_bytes()
        report, manifest = self.export()
        copied = self.output / "exporter-source.py"
        self.assertEqual(report["schema_version"], "agentops-admission-export-result/3")
        self.assertEqual(manifest["schema_version"], "agentops-admission-export-manifest/3")
        self.assertEqual(copied.read_bytes(), original)
        self.assertEqual(report["exporter_source"], {"path": "exporter-source.py", "bytes": len(original),
                                                   "sha256": hashlib.sha256(original).hexdigest()})
        self.assertTrue(report["exporter_source_unchanged"])
        self.assertTrue(report["exporter_copy_matches_before"])
        self.assertEqual(manifest["exporter"]["before"], manifest["exporter"]["after"])
        self.assertEqual(manifest["exporter"]["copy_before"], manifest["exporter"]["copy_after"])
        self.assertNotIn("exporter-source.py", {row["path"] for row in manifest["copied"]["files"]})
        self.assertFalse((self.root / "exporter-source.py").exists())
        self.assertFalse((self.output / "workspace/exporter-source.py").exists())

    def test_exporter_mutation_is_detected_without_changing_retained_copy(self):
        simulated_source = self.base / "exporter.py"
        initial = b"# initial exporter source\n"
        simulated_source.write_bytes(initial)
        original = exporter.read_file

        def mutate(root, name, destination=None):
            value = original(root, name, destination)
            if destination is not None and name == self.code.relative_to(self.root).as_posix():
                simulated_source.write_bytes(b"# changed exporter source\n")
            return value

        with patch.object(exporter, "__file__", str(simulated_source)), patch.object(exporter, "read_file", mutate):
            report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["exporter_source_unchanged"])
        self.assertTrue(report["sources_unchanged"])
        self.assertTrue(report["exporter_copy_matches_before"])
        self.assertEqual((self.output / "exporter-source.py").read_bytes(), initial)
        self.assertTrue(any("Exporter source changed during export" in issue for issue in manifest["failures"]))

    def test_captured_exporter_corruption_is_detected(self):
        original = exporter.read_file

        def corrupt(root, name, destination=None):
            value = original(root, name, destination)
            if destination is not None and name == self.code.relative_to(self.root).as_posix():
                (self.output / "exporter-source.py").write_bytes(b"corrupted capture")
            return value

        with patch.object(exporter, "read_file", corrupt):
            report, manifest = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["exporter_source_unchanged"])
        self.assertFalse(report["exporter_copy_matches_before"])
        self.assertTrue(any("Captured exporter differs" in issue for issue in manifest["failures"]))

    def test_captured_source_runs_standalone_without_staging_it_into_workspace(self):
        first, _ = self.export()
        second = self.base / "second-export"
        executed = subprocess.run([sys.executable, "-B", str(self.output / "exporter-source.py"),
            "--workspace", str(self.root), "--output", str(second)], capture_output=True, timeout=15)
        self.assertEqual(executed.returncode, 0, executed.stderr)
        report = json.loads(executed.stdout)
        self.assertEqual(report["status"], "exported")
        self.assertEqual(report["exporter_source"]["sha256"], first["exporter_source"]["sha256"])
        self.assertEqual((second / "exporter-source.py").read_bytes(), (self.output / "exporter-source.py").read_bytes())
        self.assertFalse((self.root / "exporter-source.py").exists())


if __name__ == "__main__":
    unittest.main()
