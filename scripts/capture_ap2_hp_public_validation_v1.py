"""Capture isolated stdlib tests for the AP2 public observer in a new namespace."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


FILES = (
    "src/interoperability/ap2_hp_public_assessment_v1.py",
    "tests/test_ap2_hp_public_assessment_v1.py",
    "scripts/capture_ap2_hp_public_validation_v1.py",
    "docs/research/ap2-human-present-public-assessor-design-v1.md",
    "docs/research/ap2-human-present-source-reassessment-v1.md",
    "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/sdk/python/ap2/sdk/mandate.py",
    "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/sdk/python/ap2/sdk/utils.py",
    "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/sdk/python/ap2/sdk/generated/payment_receipt.py",
    "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/merchant_payment_processor_agent/tools.py",
    "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/merchant_agent/tools.py",
)


def descriptor(value):
    return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def publish(path, value):
    pending = path.with_suffix(path.suffix + ".pending")
    with pending.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, path)  # Exclusive final name; no overwrite of prior evidence.
    pending.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (root / args.output).resolve()
    output.relative_to(root / "runs/ap2-hp-public-software")
    values = {name: (root / name).read_bytes() for name in FILES}
    tree = ast.parse(values[FILES[1]])
    primary = sorted(node.name for owner in tree.body if isinstance(owner, ast.ClassDef)
                     and owner.name == "PublicPaymentAssessmentTests" for node in owner.body
                     if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    if not primary or len(primary) != len(set(primary)):
        raise ValueError("Unique primary tests are required.")
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    for name, value in values.items():
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(value)
    command = [sys.executable, "-I", "-S", "-B", "-m", "unittest", "discover", "-s", "tests",
               "-p", "test_ap2_hp_public_assessment_v1.py", "-v"]
    plan = {"schema_version": "ap2-hp-public-validation-plan/1", "source_files": {k: descriptor(v) for k, v in values.items()},
            "primary_tests": primary, "argv": command, "scope": "constructed_public_observer_tests_only",
            "application_imports_authorized": False, "native_application_launches_authorized": False}
    publish(output / "plan.json", plan)
    started = datetime.now(timezone.utc).isoformat()
    try:
        process = subprocess.run(command, cwd=workspace, capture_output=True, timeout=60, check=False)
        stdout, stderr, returncode = process.stdout, process.stderr, process.returncode
        error = None
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, returncode = exc.stdout or b"", exc.stderr or b"", None
        error = "test_timeout"
    for name, value in (("stdout.txt", stdout), ("stderr.txt", stderr)):
        with (output / name).open("xb") as stream:
            stream.write(value)
    lines = stderr.decode("utf-8", errors="replace").splitlines()
    observed = []
    for line in lines:
        match = re.fullmatch(r"(test_\w+) \(test_ap2_hp_public_assessment_v1\.PublicPaymentAssessmentTests\.(test_\w+)\) \.\.\. ok", line)
        if match and match[1] == match[2]:
            observed.append(match[1])
    summary = next((re.fullmatch(r"Ran (\d+) tests? in .+", line) for line in lines if line.startswith("Ran ")), None)
    count = int(summary[1]) if summary else None
    unchanged = all((root / name).read_bytes() == value and (workspace / name).read_bytes() == value
                    for name, value in values.items())
    passed = returncode == 0 and error is None and count == len(primary) and sorted(observed) == primary and unchanged
    manifest = {p.relative_to(output).as_posix(): descriptor(p.read_bytes())
                for p in sorted(output.rglob("*")) if p.is_file()}
    result = {"schema_version": "ap2-hp-public-validation-result/1", "status": "passed" if passed else "failed",
              "started_at_utc": started, "ended_at_utc": datetime.now(timezone.utc).isoformat(),
              "returncode": returncode, "error": error, "tests_passed": len(observed), "tests_reported": count,
              "exact_primary_membership_verified": sorted(observed) == primary, "inputs_unchanged": unchanged,
              "files": manifest, "original_application_processes_launched": 0, "provider_calls": 0,
              "native_qualification_established": False, "scope": "constructed_public_observer_tests_only"}
    publish(output / "result.json", result)
    print(json.dumps({"status": result["status"], "tests_passed": result["tests_passed"],
                      "result": str(output / "result.json"), "native_qualification_established": False}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
