"""Constructed paper-restoration safety controls; no SDK/provider execution."""
from __future__ import annotations
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / "scripts/verify_v15_paper_package_v2.py"
SPEC = importlib.util.spec_from_file_location("paper_restore_v2_controls", SOURCE)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Controls(unittest.TestCase):
    def test_portable_names_reject_traversal_aliases_and_reserved_targets(self):
        for name in ("../escape", "/absolute", "C:/escape", "a\\b", "a/./b", "a//b", "a/CON.txt", "a/name.", "a/name ", "a/name?", "a/name\x00"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                HELPER.portable_name(name)

    def zip_check(self, names, modes=None):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as zipped:
            for index, name in enumerate(names):
                info = zipfile.ZipInfo(name)
                if modes:
                    info.create_system = 3
                    info.external_attr = modes[index] << 16
                zipped.writestr(info, b"x")
        stream.seek(0)
        inventory = {name: identity(b"x") for name in names}
        with zipfile.ZipFile(stream) as zipped:
            return HELPER.validate_zip(zipped, inventory)

    def test_case_duplicate_and_file_directory_conflict_are_refused(self):
        for names in (("item", "ITEM"), ("dir", "dir/item"), ("Dir/a", "dir/b")):
            with self.subTest(names=names), self.assertRaises(ValueError):
                self.zip_check(names)

    def test_symlink_in_unused_member_is_refused(self):
        with self.assertRaises(ValueError):
            self.zip_check(("needed", "unused-link"), (stat.S_IFREG | 0o600, stat.S_IFLNK | 0o777))

    def fixture(self, root, bad_member=False, existing_drift=False, bad_parts=False):
        base = root / "runs/fixture/retained-1-1"
        base.mkdir(parents=True)
        payloads = {"a.txt": b"GOOD", "b.txt": b"EVIL" if bad_member else b"GOOD", "sdk/unneeded.py": b"unneeded SDK payload"}
        archive = base / "artifact.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for name, raw in payloads.items():
                zipped.writestr(name, raw)
        whole = identity(archive.read_bytes())
        digest = "sha256:" + whole["sha256"]
        head = "a" * 40
        receipt = {"archive_bytes": whole["bytes"], "archive_sha256": whole["sha256"], "status": "retained",
                   "api_digest": digest, "digest_matches_api": True, "run_id": 1, "head_sha": head,
                   "workflow_conclusion": "success", "artifact_id": 2, "artifact_name": "fixture", "extracted_files": 3}
        write_json(base / "retention.json", receipt)
        write_json(base / "github-run.json", {"status": "completed", "id": 1, "run_attempt": 1, "head_sha": head,
                                               "conclusion": "success", "html_url": "https://github.com/test/repo/actions/runs/1"})
        write_json(base / "plan.json", {"run_id": 1, "application_rerun": False, "repository": "test/repo"})
        write_json(base / "github-artifacts.json", {"artifacts": [{"id": 2, "digest": digest, "size_in_bytes": whole["bytes"],
                    "name": "fixture", "expired": False, "workflow_run": {"id": 1, "head_sha": head}}]})
        rows = [{"path": name, **identity(b"GOOD" if name == "b.txt" and bad_member else raw)} for name, raw in payloads.items()]
        write_json(base / "extracted-manifest.json", {"files": rows})
        targets = [{"path": "runs/fixture/retained-1-1/extracted/" + name, **identity(b"GOOD")} for name in ("a.txt", "b.txt")]
        (base / "extracted").mkdir()
        (base / "extracted/a.txt").write_bytes(b"DRFT" if existing_drift else b"GOOD")
        write_json(root / HELPER.PROVENANCE, {"inputs": targets})
        source_rows = []
        if bad_parts:
            index = base / "archive-parts-v1/index.json"
            index.parent.mkdir()
            raw = archive.read_bytes()
            (index.parent / "part-0000.bin").write_bytes(raw)
            write_json(index, {"schema_version": "public-retained-archive-parts/1", "archive": "artifact.zip",
                "run_id": 1, "api_digest": digest, "identity": whole, "part_byte_limit": HELPER.PART_BYTES,
                "original_archive_modified": False, "parts": [{"name": "part-0000.bin", "bytes": len(raw), "sha256": "0" * 64}]})
            archive.unlink()
            source_rows = [{"archive": "runs/fixture/retained-1-1/artifact.zip",
                            "index": "runs/fixture/retained-1-1/archive-parts-v1/index.json"}]
        write_json(root / HELPER.CENSUS, {"inputs": targets, "archive_recovery_sources": source_rows})
        for name in ("scripts/verify_v15_paper_package_v1.py", "docs/research/paper-v15-offline-restoration-guide-v1.md",
                     "scripts/verify_v15_paper_package_v2.py", "docs/research/paper-v15-offline-restoration-guide-v2.md"):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"constructed control source")
        return base

    def run_fixture(self, root, output, fake_audit=False):
        def audit(argv, allocation, timeout, workspace):
            write_json(Path(argv[-1]), {"passed": True, "checks_passed": 19, "constructed_control_only": True})
            return {"returncode": 0, "timed_out": False, "constructed_control_only": True}
        with mock.patch.object(HELPER, "ROOT", root), mock.patch.object(HELPER, "PINNED", {}), mock.patch.object(HELPER, "INPUT_COUNT", 2):
            if fake_audit:
                with mock.patch.object(HELPER, "run_bounded", side_effect=audit):
                    return HELPER.run(output)
            with mock.patch.object(HELPER, "run_bounded", side_effect=AssertionError("preflight failure must not run auditor")):
                return HELPER.run(output)

    def test_late_needed_payload_hash_failure_prevents_all_evidence_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            base = self.fixture(root, bad_member=True)
            result = self.run_fixture(root, root / "runs/control")
            self.assertEqual(result["status"], "failed")
            self.assertFalse((base / "extracted/b.txt").exists())
            self.assertEqual((base / "extracted/a.txt").read_bytes(), b"GOOD")
            self.assertEqual(result["restored_required_input_count"], 0)

    def test_existing_needed_input_drift_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            base = self.fixture(root, existing_drift=True)
            result = self.run_fixture(root, root / "runs/control")
            self.assertEqual(result["status"], "failed")
            self.assertEqual((base / "extracted/a.txt").read_bytes(), b"DRFT")
            self.assertFalse((base / "extracted/b.txt").exists())

    def test_bad_part_hash_never_publishes_archive_or_missing_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            base = self.fixture(root, bad_parts=True)
            result = self.run_fixture(root, root / "runs/control")
            self.assertEqual(result["status"], "failed")
            self.assertFalse((base / "artifact.zip").exists())
            self.assertFalse((base / "extracted/b.txt").exists())
            self.assertEqual(result["restored_required_input_count"], 0)

    def test_selective_restore_preserves_exact_subset_and_does_not_extract_sdk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            base = self.fixture(root)
            result = self.run_fixture(root, root / "runs/control", fake_audit=True)
            self.assertEqual(result["status"], "passed_exact_V15_paper_inputs_and_read_audit")
            self.assertEqual((base / "extracted/a.txt").read_bytes(), b"GOOD")
            self.assertEqual((base / "extracted/b.txt").read_bytes(), b"GOOD")
            self.assertFalse((base / "extracted/sdk").exists())
            self.assertEqual(result["restored_member_count"], 1)

    def test_publication_is_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / "existing"
            target.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                HELPER.publish(io.BytesIO(b"new"), target, identity(b"new"), root)
            self.assertEqual(target.read_bytes(), b"existing")

    def test_existing_final_case_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "Original").write_bytes(b"existing")
            with self.assertRaises(ValueError):
                HELPER.verify_existing_spelling(root / "original", root)

    def test_auditor_log_capture_is_bounded_and_drained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root / "logs"
            output.mkdir()
            argv = [sys.executable, "-I", "-S", "-B", "-c",
                    "import sys;sys.stdout.buffer.write(b'o'*(3*1024*1024));sys.stderr.buffer.write(b'e'*(2*1024*1024))"]
            result = HELPER.run_bounded(argv, output, 15, root)
            self.assertEqual(result["returncode"], 0)
            self.assertFalse(result["timed_out"])
            self.assertEqual([row["retained_bytes"] for row in result["logs"]], [HELPER.MAX_LOG_BYTES] * 2)
            self.assertEqual([row["discarded_bytes"] for row in result["logs"]], [2 * HELPER.MAX_LOG_BYTES, HELPER.MAX_LOG_BYTES])
            self.assertEqual((output / "paper-read-audit.stdout.bin").stat().st_size, HELPER.MAX_LOG_BYTES)


if __name__ == "__main__":
    unittest.main()
