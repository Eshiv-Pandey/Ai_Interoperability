"""Once-only retained isolated capture of constructed AP2 gate/owner tests.

The tests load adapter definitions and invoke an early readiness refusal. They
never perform native Windows operations, import original AP2 modules, open a
credential, install an environment, or make a model/server call. The one test
subprocess exercises an early bootstrap refusal.
"""
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
    "src/interoperability/ap2_hp_native_gate_v1.py",
    "src/interoperability/ap2_hp_windows_runtime_v1.py",
    "scripts/boot_ap2_hp_service_v1.py",
    "tests/test_ap2_hp_native_gate_v1.py",
    "scripts/capture_ap2_hp_native_gate_tests_v1.py",
)
FROZEN = (
    "src/interoperability/windows_owned_job_v1.py",
    "src/interoperability/windows_tcp_ownership_v1.py",
    "scripts/with_gemini_key.ps1",
    "docs/research/source-evidence/ap2-procurement-screen-v1/source-result.json",
    "docs/research/source-evidence/ap2-hp-cert-assets-v1/manifest.json",
    "docs/research/source-evidence/ap2-hp-cert-assets-v1/source-tree.json",
)
SOURCE = "docs/research/source-evidence/ap2-procurement-screen-v1/source"
CERTS = "docs/research/source-evidence/ap2-hp-cert-assets-v1/source"


def now():
    return datetime.now(timezone.utc).isoformat()


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(root):
    return {path.relative_to(root).as_posix(): identity(path) for path in sorted(root.rglob("*")) if path.is_file()}


def write(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def test_names(path):
    tree = ast.parse(path.read_bytes())
    return sorted(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))


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
        self.outcomes.append({"id": test.id(), "status": "skipped", "reason": reason})


def run_tests(root, artifact_root):
    os.environ["AP2_GATE_TEST_ARTIFACT_ROOT"] = str(artifact_root)
    namespace = runpy.run_path(str(root / "tests/test_ap2_hp_native_gate_v1.py"), run_name="_ap2_retained_constructed_tests")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(namespace["NativeGateTests"])
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=RetainedResult)
    result = runner.run(suite)
    write(artifact_root.parent / "test-outcomes.json", {
        "schema_version": "ap2-hp-native-gate-constructed-tests/1",
        "tests_run": result.testsRun, "outcomes": result.outcomes,
        "successful": result.wasSuccessful(), "failure_count": len(result.failures),
        "error_count": len(result.errors), "skipped_count": len(result.skipped),
        "scope": "Injected gate/owner software and early refusal branches only; no native readiness or provider enforcement."
    })
    return 0 if result.wasSuccessful() else 1


def capture(root, output):
    if output.exists() or not output.is_absolute() or not output.parent.is_dir():
        raise ValueError("A fresh absolute capture root with an existing parent is required")
    output.mkdir()
    checkout = output / "captured-checkout"
    checkout.mkdir()
    before = {name: identity(root / name) for name in (*OWN, *FROZEN)}
    source_before, certs_before = inventory(root / SOURCE), inventory(root / CERTS)
    if len(source_before) != 134 or len(certs_before) != 2:
        raise ValueError("Expected 134 retained source files and two supplementary certificates")
    for name in (*OWN, *FROZEN):
        destination = checkout / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    shutil.copytree(root / SOURCE, checkout / SOURCE)
    shutil.copytree(root / CERTS, checkout / CERTS)
    captured_inputs = inventory(checkout)
    expected_captured = {**before,
        **{SOURCE + "/" + name: value for name, value in source_before.items()},
        **{CERTS + "/" + name: value for name, value in certs_before.items()}}
    copied_inputs_matched = captured_inputs == expected_captured
    if not copied_inputs_matched:
        raise ValueError("Copied checkout membership/bytes differ from the pre-copy input identities")
    names = test_names(checkout / "tests/test_ap2_hp_native_gate_v1.py")
    command = [sys.executable, "-I", "-S", "-B", str(checkout / OWN[-1]), "--phase", "tests",
               "--root", str(checkout), "--artifact-root", str(output / "constructed-artifacts")]
    write(output / "capture-plan.json", {
        "schema_version": "ap2-hp-native-gate-software-capture-plan/1", "created_at_utc": now(),
        "command": command, "driver": identity(Path(__file__)), "interpreter": {"path": sys.executable, **identity(Path(sys.executable))},
        "inputs_before": before, "captured_inputs": captured_inputs,
        "copied_checkout_matches_precopy_inputs": copied_inputs_matched,
        "original_source_files": source_before, "supplementary_certificate_files": certs_before,
        "declared_test_names": names, "expected_test_count": 28,
        "scope": "One isolated captured-source run of injected controls; no native application or model execution."
    })
    started = now()
    returncode, timed_out = None, False
    with (output / "tests.stdout.bin").open("xb") as stdout, (output / "tests.stderr.bin").open("xb") as stderr:
        try:
            child = subprocess.run(command, cwd=checkout, stdout=stdout, stderr=stderr, check=False, timeout=180)
            returncode = child.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    outcomes_path = output / "test-outcomes.json"
    outcomes = json.loads(outcomes_path.read_bytes()) if outcomes_path.is_file() else None
    after = {name: identity(root / name) for name in (*OWN, *FROZEN)}
    source_after, certs_after = inventory(root / SOURCE), inventory(root / CERTS)
    captured_after = inventory(checkout)
    matched_tests = (outcomes is not None and outcomes.get("tests_run") == 28 and len(names) == 28
        and sorted(item["id"].rsplit(".", 1)[-1] for item in outcomes["outcomes"]) == names
        and all(item["status"] == "passed" for item in outcomes["outcomes"]))
    unchanged = before == after and source_before == source_after and certs_before == certs_after and captured_inputs == captured_after
    report = {
        "schema_version": "ap2-hp-native-gate-software-capture/1",
        "status": "passed_constructed_software_tests_only" if returncode == 0 and matched_tests and unchanged and copied_inputs_matched and not timed_out else "failed_or_incomplete_constructed_capture",
        "started_at_utc": started, "finished_at_utc": now(), "returncode": returncode, "timed_out": timed_out,
        "tests_run": outcomes.get("tests_run") if outcomes else None, "declared_test_membership_verified": matched_tests,
        "copied_checkout_matches_precopy_inputs": copied_inputs_matched,
        "inputs_after": after, "original_and_captured_inputs_unchanged": unchanged,
        "captured_file_count": len(captured_inputs), "retained_files_before_result": inventory(output),
        "original_source_imported": False, "credential_opened": False, "environment_installed": False,
        "native_windows_operations_executed": False, "native_adapter_startup_executed": False,
        "native_application_executed": False, "model_requests": 0,
        "claim_limit": "Source-bound injected behavior only. Zero-operation fields describe this driver/test path, not a system-wide observer or native qualification."
    }
    write(output / "result.json", report)
    print(json.dumps({"status": report["status"], "tests_run": report["tests_run"], "inputs_unchanged": unchanged}))
    return 0 if report["status"] == "passed_constructed_software_tests_only" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("capture", "tests"), default="capture")
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args(argv)
    if args.phase == "tests":
        if args.artifact_root is None:
            parser.error("--artifact-root is required for the isolated test phase")
        return run_tests(args.root, args.artifact_root)
    if args.output is None:
        parser.error("--output is required for a fresh capture")
    return capture(args.root, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
