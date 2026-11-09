"""Authored control/packaging checks; no Linux or AgentOps application executes."""
import copy
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agentops_native_probe_v4 as native
import inspect_agentops_runtime_v4 as inspector
import run_agentops_linux_v4 as setup


class LinuxControlTests(unittest.TestCase):
    def setUp(self):
        # Retain authored fixtures. Default-mode directories avoid the known
        # Windows sandbox mode-0700 limitation; this is not an upstream fixture.
        self.output = ROOT / "tmp" / ("linux-control-test-" + uuid.uuid4().hex)
        self.output.mkdir(parents=True)

    def archive(self, members):
        target = self.output / "tool.tar.gz"
        with tarfile.open(target, "w:gz") as stream:
            for name, kind in members:
                member = tarfile.TarInfo(name)
                if kind == "file":
                    member.size = 5
                    stream.addfile(member, io.BytesIO(b"dummy"))
                else:
                    member.type = tarfile.SYMTYPE
                    member.linkname = "../../outside"
                    stream.addfile(member)
        return target, hashlib.sha256(target.read_bytes()).hexdigest()

    def test_windows_rejected_before_reservation_or_download(self):
        with patch.object(sys, "platform", "win32"), patch.object(setup.urllib.request, "urlopen") as download:
            for action in (setup.setup, inspector.inspect,
                           lambda: native.prepare(self.output / "native"),
                           lambda: native.run(self.output / "native")):
                with self.assertRaisesRegex(ValueError, "Linux"):
                    action()
            download.assert_not_called()
        self.assertFalse((self.output / "native").exists())

    def test_unsupported_architecture_and_libc_rejected(self):
        with patch.object(sys, "platform", "linux"), patch.object(setup.platform, "machine", return_value="aarch64"):
            with self.assertRaisesRegex(ValueError, "x86_64"):
                setup.require_linux()
        with patch.object(sys, "platform", "linux"), patch.object(setup.platform, "machine", return_value="x86_64"), patch.object(setup.platform, "libc_ver", return_value=("musl", "1")):
            with self.assertRaisesRegex(ValueError, "glibc"):
                setup.require_linux()

    def test_tool_pin_matches_preserved_linux_source(self):
        self.assertEqual(setup.tool_pin(), {
            "url": "https://github.com/astral-sh/uv/releases/download/0.12.0/uv-x86_64-unknown-linux-gnu.tar.gz",
            "sha256": "eaf842262aa1c418d8ecc5605f02ee1ebfd369124fa48548e85f9481a47831a9"})

    def test_extracts_only_exact_verified_member(self):
        archive, sha = self.archive([("uv-x86_64-unknown-linux-gnu/uv", "file"), ("../../ignored", "file")])
        target = self.output / "uv"
        setup.unpack_uv(archive, target, sha)
        self.assertEqual(target.read_bytes(), b"dummy")
        self.assertEqual({path.name for path in self.output.iterdir()}, {"tool.tar.gz", "uv"})
        with self.assertRaises(FileExistsError):
            setup.unpack_uv(archive, target, sha)

    def test_checksum_rejection_precedes_extraction(self):
        archive, _ = self.archive([("uv-x86_64-unknown-linux-gnu/uv", "file")])
        with self.assertRaisesRegex(ValueError, "checksum"):
            setup.unpack_uv(archive, self.output / "uv", "0" * 64)
        self.assertFalse((self.output / "uv").exists())

    def test_symlink_member_rejected(self):
        archive, sha = self.archive([("uv-x86_64-unknown-linux-gnu/uv", "symlink")])
        with self.assertRaisesRegex(ValueError, "regular"):
            setup.unpack_uv(archive, self.output / "uv", sha)

    def test_duplicate_member_rejected(self):
        archive, sha = self.archive([("uv-x86_64-unknown-linux-gnu/uv", "file")] * 2)
        with self.assertRaisesRegex(ValueError, "regular"):
            setup.unpack_uv(archive, self.output / "uv", sha)

    def test_existing_setup_stops_before_source_or_network(self):
        with patch.object(setup, "require_linux"), patch.object(setup, "RUNTIME", self.output), patch.object(setup.evidence, "source_inventory") as source:
            with self.assertRaises(FileExistsError):
                setup.setup()
            source.assert_not_called()

    def test_failed_dependency_receipt_rejected(self):
        with patch.object(native.original, "load_json", return_value={"status": "failed", "source_unchanged_after": True}):
            with self.assertRaisesRegex(ValueError, "Successful Linux"):
                native.validate_setup()

    def test_setup_evidence_mutation_rejected(self):
        row = {"path": "runs/agentops-native-eligibility/dependencies-linux-v4/installed-runtime.stdout.bin", "sha256": "original"}
        receipt = {"status": "dependencies_ready", "source_unchanged_after": True, "source_files": [], "files": [row]}
        with patch.object(native.original, "load_json", return_value=receipt), patch.object(native.original, "source_inventory", return_value=[]), patch.object(native.original, "digest", return_value={"sha256": "changed"}):
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                native.validate_setup()

    def test_pytest_requires_all_three_distinct_phases(self):
        report = {"exitstatus": 0, "reports": [
            {"nodeid": native.original.NODEID, "when": when, "outcome": "passed"}
            for when in ("setup", "call", "teardown")]}
        native.validate_pytest_reports(report)
        mutations = []
        duplicate = copy.deepcopy(report)
        duplicate["reports"][2]["when"] = "call"
        mutations.append(duplicate)
        other = copy.deepcopy(report)
        other["reports"][1]["nodeid"] = "another-test"
        mutations.append(other)
        failed = copy.deepcopy(report)
        failed["reports"][1]["outcome"] = "failed"
        mutations.append(failed)
        mutations.extend([{"exitstatus": 4, "reports": []}, {"exitstatus": 0, "reports": []}])
        for mutated in mutations:
            with self.subTest(mutated=mutated), self.assertRaises(ValueError):
                native.validate_pytest_reports(mutated)


if __name__ == "__main__":
    unittest.main()
