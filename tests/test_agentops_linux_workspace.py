"""Authored filesystem/export tests; no WSL, dependency install or app execution."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_agentops_linux_workspace_v5 as workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / "tmp" / ("linux-workspace-test-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.source = self.directory / "source"
        self.source.mkdir()

    def add(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else json.dumps(content).encode())
        return workspace.record(path, self.source)

    def test_longest_mount_and_escaped_paths(self):
        mounts = (
            "1 0 8:1 / / rw - ext4 /dev/sda rw\n"
            "2 1 0:10 / /mnt/p rw - 9p drvfs rw\n"
            "3 1 8:2 / /tmp/research\\040disk rw - xfs /dev/sdb rw\n")
        self.assertEqual(workspace.mount_for("/tmp/task", mounts)["fstype"], "ext4")
        self.assertEqual(workspace.mount_for("/mnt/p/project", mounts)["fstype"], "9p")
        self.assertEqual(workspace.mount_for("/tmp/research disk/task", mounts)["fstype"], "xfs")
        self.assertEqual(workspace.mount_for("/mnt/prefix", mounts)["fstype"], "ext4")

    def test_non_native_mount_rejected(self):
        for kind in ("9p", "drvfs", "ntfs3", "cifs", "tmpfs"):
            with self.subTest(kind=kind), patch.object(workspace, "mount_for", return_value={"fstype": kind}), patch.object(Path, "read_text", return_value="mounts"):
                with self.assertRaisesRegex(ValueError, "Linux disk"):
                    workspace.require_native_filesystem(self.source)

    def test_path_traversal_and_absolute_paths_rejected(self):
        for name in ("../outside", "/outside", "a/../../outside", "C:/outside", "a\\outside", "."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                workspace.relative_file(self.source, name)

    def test_exact_copy_and_no_overwrite(self):
        row = self.add("scripts/example.py", b"retained source")
        destination = self.directory / "copy"
        destination.mkdir()
        workspace.copy_exact(self.source, destination, [row])
        self.assertEqual(workspace.record(destination / row["path"], destination), row)
        with self.assertRaises(FileExistsError):
            workspace.copy_exact(self.source, destination, [row])
        (self.source / row["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed"):
            workspace.copy_exact(self.source, self.directory / "other", [row])

    def test_export_preserves_paths_and_runtime_references(self):
        source = self.add("scripts/example.py", b"unchanged input")
        metadata = self.add("external/runtime/site/package.dist-info/METADATA", b"Name: package")
        native_module = self.add("external/runtime/python/lib/fcntl.so", b"authored extension")
        inspection = {"packages": [{"metadata_files": [metadata]}], "fcntl_extension": {
            "path": str(self.source / native_module["path"]), "sha256": native_module["sha256"]},
            "agentops_direct_url": {"url": "file:///tmp/original-replica/source"}}
        stream = self.add("runs/native/prepared-runtime.stdout.bin", inspection)
        self.add("runs/native/plan.json", {"runtime_inventory": stream, "source_files": [source]})
        destination = self.directory / "export"
        result = workspace.export_evidence(self.source, destination, [source])
        self.assertEqual(result["reference_failures"], [])
        self.assertTrue((destination / metadata["path"]).is_file())
        self.assertTrue((destination / native_module["path"]).is_file())
        self.assertEqual((destination / stream["path"]).read_bytes(), (self.source / stream["path"]).read_bytes())
        for row in result["files"]:
            self.assertEqual(workspace.record(destination / row["path"], destination), row)

    def test_export_reports_missing_and_escaping_references(self):
        self.add("runs/native/result.json", {"files": [
            {"path": "../outside", "bytes": 1, "sha256": "a"},
            {"path": "missing", "bytes": 1, "sha256": "b"}]})
        result = workspace.export_evidence(self.source, self.directory / "export", [])
        self.assertEqual(len(result["reference_failures"]), 2)
        self.assertTrue((self.directory / "export/runs/native/result.json").exists())

    def test_runtime_sources_are_labeled_as_post_execution_snapshots(self):
        module = self.add("external/runtime/site/google/adk/a2a/converters/part_converter.py", b"authored converter")
        self.add("runs/native/prepared-runtime.stdout.bin", {
            "schema_version": "agentops-installed-runtime-inspection/4",
            "packages": [{"name": "google-adk", "location": "external/runtime/site"}]})
        result = workspace.export_evidence(self.source, self.directory / "export", [])
        self.assertEqual(result["post_execution_runtime_source_files"], [module["path"]])
        self.assertEqual((self.directory / "export" / module["path"]).read_bytes(), b"authored converter")

    def test_export_detects_conflicting_reference_hash(self):
        source = self.add("scripts/example.py", b"source")
        wrong = {**source, "sha256": "0" * 64}
        self.add("runs/native/result.json", {"files": [wrong]})
        result = workspace.export_evidence(self.source, self.directory / "export", [source])
        self.assertEqual(len(result["reference_failures"]), 1)

    def test_source_fixture_json_does_not_expand_export_scope(self):
        fixture = self.add("external/app/test-fixture.json", {"path": "unexecuted-example", "bytes": 1, "sha256": "example"})
        result = workspace.export_evidence(self.source, self.directory / "export", [fixture])
        self.assertEqual(result["reference_failures"], [])

    def test_export_size_limit_precedes_copy(self):
        source = self.add("scripts/example.py", b"source")
        with patch.object(workspace, "MAX_EXPORT_BYTES", 2), self.assertRaisesRegex(ValueError, "export exceeds"):
            workspace.export_evidence(self.source, self.directory / "export", [source])
        self.assertFalse((self.directory / "export").exists())

    def test_pytest_symlinks_are_preserved_as_inert_metadata(self):
        self.add("runs/native/current", b"authored symlink stand-in")
        self.add("runs/native/data.json", {"actual": "data"})
        original = Path.is_symlink
        # Model the filesystem's symlink answers; Windows may not permit link
        # creation here. This verifies export policy, not native symlink support.
        with patch.object(Path, "is_symlink", lambda path: path.name == "current" or original(path)), patch.object(workspace.os, "readlink", return_value="../data"):
            result = workspace.export_evidence(self.source, self.directory / "export", [])
        self.assertEqual(result["inert_symlinks"], [{"path": "runs/native/current", "target": "../data"}])
        self.assertEqual(result["reference_failures"], [])
        self.assertFalse((self.directory / "export/runs/native/current").exists())

    def test_hashed_reference_through_symlink_remains_rejected(self):
        link = self.add("runs/native/current", b"authored symlink stand-in")
        self.add("runs/native/result.json", {"file": link})
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path.name == "current" or original(path)), patch.object(workspace.os, "readlink", return_value="../../outside"):
            result = workspace.export_evidence(self.source, self.directory / "export", [])
        self.assertEqual(len(result["reference_failures"]), 1)
        self.assertIn("symlink", result["reference_failures"][0])

    def test_windows_rejected_without_attempt(self):
        with patch.object(sys, "platform", "win32"), patch.object(sys, "argv", ["runner"]), patch.object(workspace, "OUTPUT", self.directory / "attempt"):
            with self.assertRaisesRegex(ValueError, "Ubuntu Linux"):
                workspace.main()
        self.assertFalse((self.directory / "attempt").exists())


if __name__ == "__main__":
    unittest.main()
