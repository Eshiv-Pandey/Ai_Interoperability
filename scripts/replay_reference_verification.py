"""Replay archived original-reference checks and tests in a clean interpreter."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {path.relative_to(root).as_posix(): sha256(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


WORKER = r'''
import json
import sys
import unittest
from pathlib import Path
snapshot = Path(sys.argv[1]).resolve()
verification = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.path.insert(0, str(snapshot / "src"))
from interoperability import reference_checker
module_path = Path(reference_checker.__file__).resolve()
if not module_path.is_relative_to(snapshot / "src"):
    raise SystemExit("Non-archived checker import")
checks = []
for row in verification["checks"]:
    if "valid" not in row:
        continue
    path = (snapshot / row["input"]).resolve()
    if not path.is_relative_to(snapshot):
        raise SystemExit("Capture path escapes archive")
    record = json.loads(path.read_text(encoding="utf-8"))
    checks.append({"input": row["input"], "valid": reference_checker.check_reference_trace(record),
                   "controls": len(record["controls"])})
suite = unittest.defaultTestLoader.discover(str(snapshot / "tests"))
tests = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
valid = (bool(checks) and all(row["valid"] for row in checks)
         and len(checks) == verification["checked_native_runs"]
         and sum(row["controls"] for row in checks) == verification["checked_native_controls"]
         and tests.wasSuccessful())
print(json.dumps({"checker_module": str(module_path), "python": sys.version,
                  "checks": checks, "tests_run": tests.testsRun,
                  "test_failures": len(tests.failures), "test_errors": len(tests.errors),
                  "test_skips": len(tests.skipped), "valid": valid}))
raise SystemExit(0 if valid else 1)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verification = args.verification.resolve()
    snapshot = (args.snapshot or verification.with_suffix(".sources")).resolve()
    output = args.output.resolve()
    driver_snapshot = output.with_suffix(".driver.py")
    if output.exists() or driver_snapshot.exists() or output.is_relative_to(snapshot):
        raise SystemExit("Replay output/driver must be new paths outside the archive")
    saved = json.loads(verification.read_text(encoding="utf-8"))
    if saved.get("schema_version") != "original-reference-verification/1" or saved.get("valid") is not True:
        raise SystemExit("Expected a successful original-reference verification")
    before = inventory(snapshot)
    archive_matches = bool(before) and before == saved["archive_sha256"]
    source_matches = bool(saved["implementation_sha256"]) and all(
        before.get(relative) == digest for relative, digest in saved["implementation_sha256"].items())
    output.parent.mkdir(parents=True, exist_ok=True)
    with driver_snapshot.open("xb") as handle:
        handle.write(Path(__file__).read_bytes())
    command = [str(args.python.resolve()), "-I", "-B", "-c", WORKER,
               str(snapshot), str(verification)]
    worker = subprocess.run(command, cwd=snapshot, capture_output=True,
                            text=True, encoding="utf-8", timeout=300)
    try:
        result = json.loads(worker.stdout)
    except json.JSONDecodeError:
        result = {"valid": False, "unparsed_stdout": worker.stdout}
    after = inventory(snapshot)
    valid = (archive_matches and source_matches and before == after
             and worker.returncode == 0 and result.get("valid") is True)
    report = {
        "schema_version": "original-reference-archive-replay/1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_limit": "Clean-interpreter software/data replay only; no native application rerun, A2A 1.0 bridge compatibility, novelty or human review",
        "verification": str(verification), "verification_sha256": sha256(verification),
        "archive": str(snapshot), "archive_file_count": len(before),
        "archive_matches_verification": archive_matches,
        "source_matches_verification": source_matches, "archive_unchanged": before == after,
        "driver_snapshot": str(driver_snapshot), "driver_sha256": sha256(driver_snapshot),
        "worker_command": [command[0], "-I", "-B", "-c", "WORKER (in hashed driver)",
                           str(snapshot), str(verification)],
        "worker_exit_code": worker.returncode, "worker_result": result,
        "test_and_error_output": worker.stderr, "valid": valid,
    }
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "archive_unchanged": before == after,
                      "tests_run": result.get("tests_run"), "output": str(output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
