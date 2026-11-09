"""Archive and independently check original-native continuation evidence.

Software/data verification only: no application, bridge or model is executed.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from interoperability.reference_checker import check_reference_trace


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/research/source-evidence/reference-continuation"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {path.relative_to(root).as_posix(): sha256(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    snapshot = output.with_suffix(".sources")
    if not output.is_relative_to(ROOT) or output.exists() or snapshot.exists():
        raise SystemExit("Output and archive must be new paths inside the workspace")
    inputs = sorted((ROOT / "runs/native-reference-continuation").glob("carol-*/report.json"))
    if not inputs:
        raise SystemExit("No actual native attempts found")
    input_hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs}
    source_records = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in inputs]
    snapshot.mkdir(parents=True)
    directories = [ROOT / name for name in (
        "src", "tests", "scripts", "examples/development", "runs/wire-observation")]
    directories += [path.parent for path in inputs]
    # Preserve original application source and dependency/source ledgers, without
    # copying an installed environment or creating a recursive run-directory copy.
    directories += [SOURCE / name for name in ("official-samples", "normative", "runtime/original-number-game")]
    for source in directories:
        destination = snapshot / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative in (
        "upstream-LICENSE.txt", "runtime/original-source-manifest.json",
        "runtime/resolved-requirements.txt", "runtime/installed-artifacts.json"):
        path = SOURCE / relative
        destination = snapshot / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    before = inventory(snapshot)
    checks = []
    original = SOURCE / "runtime/original-number-game"
    for path, record in source_records:
        row = {"input": path.relative_to(ROOT).as_posix(), "input_sha256": sha256(path),
               "mode": record.get("mode"), "outcome": record.get("outcome"),
               "exit_code": record.get("exit_code")}
        if record.get("mode") == "run" and record.get("outcome") == "observed":
            row["independent_raw_trace_check"] = check_reference_trace(record)
            row["original_source_hashes_match"] = all(
                (original / relative).is_file() and sha256(original / relative) == expected
                for relative, expected in record["original_source_sha256"].items())
            row["installed_ledger_hash_matches"] = sha256(SOURCE / "runtime/installed-artifacts.json") == record["installed_artifacts_sha256"]
            row["dependency_freeze_hash_matches"] = sha256(SOURCE / "runtime/resolved-requirements.txt") == record["resolved_requirements_sha256"]
            row["prospective_spec_hash_matches"] = sha256(ROOT / record["prospective_specification"]["path"]) == record["prospective_specification"]["sha256"]
            row["checked_control_count"] = len(record["controls"])
            row["valid"] = all(row[key] is True for key in (
                "independent_raw_trace_check", "original_source_hashes_match",
                "installed_ledger_hash_matches", "dependency_freeze_hash_matches",
                "prospective_spec_hash_matches"))
        else:
            # Setup evidence or unsuccessful attempts are retained, never counted
            # as a verified application execution.
            row["classification"] = "setup-or-unsuccessful-attempt-retained"
        checks.append(row)
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    tests = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", timeout=300)
    checked = [row for row in checks if "valid" in row]
    after = inventory(snapshot)
    input_stability = all(sha256(ROOT / relative) == expected for relative, expected in input_hashes.items())
    implementation = {path.relative_to(ROOT).as_posix(): sha256(path)
                      for directory in (ROOT / "src", ROOT / "tests", ROOT / "scripts")
                      for path in sorted(directory.rglob("*.py"))}
    implementation_stability = all(before.get(relative) == digest
                                   for relative, digest in implementation.items())
    valid = (bool(checked) and all(row["valid"] for row in checked)
             and tests.returncode == 0 and before == after and input_stability
             and implementation_stability)
    report = {
        "schema_version": "original-reference-verification/1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_limit": "Original A2A 0.3 application evidence and software validity only; no A2A 1.0 bridge compatibility, natural bridge defect, candidate efficacy, novelty or human review",
        "capture_and_setup_attempts": len(checks), "checked_native_runs": len(checked),
        "checked_native_controls": sum(row["checked_control_count"] for row in checked),
        "checks": checks, "source_and_input_snapshot": str(snapshot),
        "archive_sha256": before, "archive_unchanged": before == after,
        "input_hashes_stable": input_stability,
        "implementation_sha256": implementation,
        "implementation_matches_archive": implementation_stability,
        "tests": {"command": command, "exit_code": tests.returncode,
                  "stdout": tests.stdout, "stderr": tests.stderr}, "valid": valid,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "checked_native_runs": len(checked),
                      "checked_native_controls": report["checked_native_controls"],
                      "test_exit_code": tests.returncode, "output": str(output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
