"""One fresh isolated capture of constructed reference/capture software tests."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import unittest


OWN = (
    "src/interoperability/ap2_hp_reference_execution_v1.py",
    "src/interoperability/ap2_hp_passive_capture_v1.py",
    "tests/test_ap2_hp_reference_execution_v1.py",
    "scripts/capture_ap2_hp_reference_execution_tests_v1.py",
)
DEPENDENCY = "src/interoperability/ap2_hp_reference_plan_v1.py"
SOURCE_ROOT = "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/"
ORIGINALS = (
    "roles/shopping_agent/tools.py", "roles/shopping_agent/subagents/shopper/tools.py",
    "roles/shopping_agent/subagents/shipping_address_collector/tools.py",
    "roles/shopping_agent/subagents/payment_method_collector/tools.py",
    "common/a2a_message_builder.py", "common/payment_remote_a2a_client.py",
)
INPUTS = OWN + (DEPENDENCY,) + tuple(SOURCE_ROOT + name for name in ORIGINALS)
FROZEN_SHA256 = {
    DEPENDENCY: "4699f8aba9c8adfdc6c07ee8558b9ea356d64f1a80eb5d07f64e586f5aa0a8e0",
    SOURCE_ROOT + ORIGINALS[0]: "612525025661b608a662a8a09bc50ea527543b26c3bdbc78911bd95f6c3926a6",
    SOURCE_ROOT + ORIGINALS[1]: "7a577d4088dc9decb3bbe72d3162e356176a4f6b1b0c3cb87d496be4e6245bc4",
    SOURCE_ROOT + ORIGINALS[2]: "6c11b152344289c075fc66595c7ed344a37c2762c549532c8a9c275ecf8d542d",
    SOURCE_ROOT + ORIGINALS[3]: "be4b5fea7a4c0eef965694cde93205ce1b1652a36c0f121fa7ec6d820fbed8dd",
    SOURCE_ROOT + ORIGINALS[4]: "d92cccc6cb9478b160f95cee0c060f9c0dc41f25266d8220cf48a5bbeba95061",
    SOURCE_ROOT + ORIGINALS[5]: "88bd46d93eb7408912c254b4dc6a392a821d07eabc049c5a04a42b8627042efb",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(root):
    return {path.relative_to(root).as_posix(): identity(path) for path in sorted(root.rglob("*")) if path.is_file()}


def write(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


class RetainedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append({"id": test.id(), "status": "passed"})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.outcomes.append({"id": test.id(), "status": "failed", "error_type": error[0].__name__})

    def addError(self, test, error):
        super().addError(test, error)
        self.outcomes.append({"id": test.id(), "status": "error", "error_type": error[0].__name__})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes.append({"id": test.id(), "status": "skipped"})


def run_tests(root, artifact_root):
    os.environ["AP2_EXECUTION_TEST_ARTIFACT_ROOT"] = str(artifact_root)
    namespace = runpy.run_path(str(root / OWN[2]), run_name="_ap2_injected_execution_tests")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(namespace["ReferenceExecutionTests"])
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=RetainedResult).run(suite)
    write(artifact_root.parent / "test-outcomes.json", {
        "tests_run": result.testsRun, "outcomes": result.outcomes, "successful": result.wasSuccessful(),
        "failure_count": len(result.failures), "error_count": len(result.errors), "skipped_count": len(result.skipped)})
    return 0 if result.wasSuccessful() else 1


def capture(root, output):
    if not output.is_absolute() or output.exists() or not output.parent.is_dir():
        raise ValueError("A fresh absolute output with an existing parent is required")
    before = {name: identity(root / name) for name in INPUTS}
    if any(before[name]["sha256"] != digest for name, digest in FROZEN_SHA256.items()):
        raise ValueError("Frozen planner or original source identity differs before allocation")
    output.mkdir()
    checkout = output / "captured-checkout"
    checkout.mkdir()
    for name in INPUTS:
        destination = checkout / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    copied = inventory(checkout)
    if copied != before:
        raise ValueError("Copied inputs differ from prospective input identities")
    tree = ast.parse((checkout / OWN[2]).read_bytes())
    names = sorted(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    if len(names) != 15 or len(set(names)) != 15:
        raise ValueError("Exactly 15 unique new test methods are required")
    command = [sys.executable, "-I", "-S", "-B", str(checkout / OWN[3]), "--phase", "tests", "--root", str(checkout),
               "--artifact-root", str(output / "constructed-artifacts")]
    write(output / "capture-plan.json", {"schema_version": "ap2-hp-reference-execution-software-plan/1",
        "created_at_utc": now(), "command": command, "inputs_before": before, "captured_inputs": copied,
        "copied_inputs_match": True, "declared_test_names": names, "expected_test_count": 15,
        "interpreter": {"path": sys.executable, **identity(Path(sys.executable))},
        "scope": "One isolated injected suite. Frozen planner dependency is imported; its completed suite is not rerun. Original six files are copied but never imported."})
    started, returncode, timed_out = now(), None, False
    with (output / "tests.stdout.bin").open("xb") as stdout, (output / "tests.stderr.bin").open("xb") as stderr:
        try:
            returncode = subprocess.run(command, cwd=checkout, stdout=stdout, stderr=stderr, timeout=120, check=False).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    outcomes_path = output / "test-outcomes.json"
    outcomes = json.loads(outcomes_path.read_bytes()) if outcomes_path.is_file() else {}
    matched = (outcomes.get("tests_run") == 15 and len(outcomes.get("outcomes", [])) == 15
               and sorted(item["id"].rsplit(".", 1)[-1] for item in outcomes["outcomes"]) == names
               and all(item["status"] == "passed" for item in outcomes["outcomes"]))
    after = {name: identity(root / name) for name in INPUTS}
    unchanged = before == after and copied == inventory(checkout)
    result = {"schema_version": "ap2-hp-reference-execution-software-capture/1",
        "status": "passed_constructed_software_tests_only" if returncode == 0 and matched and unchanged and not timed_out else "failed_or_incomplete_constructed_capture",
        "started_at_utc": started, "finished_at_utc": now(), "returncode": returncode, "timed_out": timed_out,
        "tests_run": outcomes.get("tests_run"), "declared_test_membership_verified": matched,
        "original_and_captured_inputs_unchanged": unchanged, "inputs_after": after,
        "captured_file_count": len(copied), "retained_files_before_result": inventory(output),
        "original_source_imported": False, "native_application_executed": False,
        "credential_opened": False, "model_requests": 0, "native_qualification_established": False,
        "claim_limit": "Injected objects and original-file identity retention only; no original runtime compatibility, native hook, provider guard or research credit."}
    write(output / "result.json", result)
    print(json.dumps({"status": result["status"], "tests_run": result["tests_run"], "inputs_unchanged": unchanged}))
    return 0 if result["status"] == "passed_constructed_software_tests_only" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("capture", "tests"), default="capture")
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args(argv)
    if args.phase == "tests":
        if args.artifact_root is None:
            parser.error("--artifact-root required")
        return run_tests(args.root, args.artifact_root)
    if args.output is None:
        parser.error("--output required")
    return capture(args.root, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
