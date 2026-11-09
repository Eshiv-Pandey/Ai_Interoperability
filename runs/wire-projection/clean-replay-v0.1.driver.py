"""Replay an immutable historical archive using an explicitly chosen interpreter.

No bridge/model/network operation is run. The worker imports archived source,
rechecks archived inputs and decisions, and runs the archived software suite.
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*")) if path.is_file()
    }


WORKER = r'''
import hashlib
import json
import platform
import sys
import unittest
from pathlib import Path

snapshot = Path(sys.argv[1]).resolve()
verification = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.path.insert(0, str(snapshot / "src"))
from interoperability import baseline, oracle, projection_checker, wire_projection

modules = {
    module.__name__: str(Path(module.__file__).resolve())
    for module in (baseline, oracle, projection_checker, wire_projection)
}
if not all(Path(path).is_relative_to(snapshot / "src") for path in modules.values()):
    raise SystemExit("Worker imported non-archived implementation")

checks = []
run_ids = set()
for saved in verification["checks"]:
    run_id = saved["run_id"]
    if not isinstance(run_id, str) or not run_id or run_id in run_ids:
        raise ValueError("Missing or repeated capture identity")
    if any(part in run_id for part in ("/", "\\", "..")):
        raise ValueError("Invalid capture path identity")
    run_ids.add(run_id)
    path = snapshot / "runs" / "wire-observation" / run_id / "runtime.json"
    raw = path.read_bytes()
    trace = wire_projection._decode_json(raw.decode("utf-8"))
    row = {
        "run_id": run_id,
        "input_sha256_matches": hashlib.sha256(raw).hexdigest() == saved["input_sha256"],
        "capture_outcome_matches": trace.get("outcome") == saved["capture_outcome"],
        "capture_identity_matches": trace.get("run_id") == run_id
            and trace.get("route_id") == saved["route_id"],
        "capture_exit_code_matches": trace.get("exit_code") == saved["capture_exit_code"],
    }
    if trace.get("outcome") != "passed":
        row["failed_attempt_retained"] = saved["projection_status"] == "capture-failed-not-projectable"
        row["valid"] = all(value is True for key, value in row.items() if key != "run_id")
        checks.append(row)
        continue
    projection = wire_projection.project_trace(trace, verification["expected_artifact_text"])
    clock, model = projection["analysis_clock"], projection["manifest"]
    result = baseline.evaluate(model, clock)
    reference = oracle.evaluate(model, clock)
    sidecar = path.parent / "private-native-http.jsonl"
    private_raw = sidecar.read_bytes()
    records = [wire_projection._decode_json(line) for line in private_raw.decode("utf-8").splitlines() if line]
    row.update(
        projection_equals_saved=projection == saved["projection"],
        independent_public_check=projection_checker.check_projection(trace, projection),
        private_sidecar_sha256_matches=hashlib.sha256(private_raw).hexdigest() == saved["private_sidecar_sha256"],
        independent_private_check=projection_checker.check_native_sidecar(trace, records),
        baseline_equals_saved=result == saved["baseline"],
        oracle_equals_saved=reference == saved["independent_finite_oracle"],
        decision_agreement=result["decision"] == reference["decision"],
        incomplete_historical_evidence=model["evidence"]["complete"] is False
            and model["evidence"]["observed_at"] == model["evidence"]["valid_until"] == clock,
        later_clock_abstention=baseline.evaluate(model, clock + 1)["decision"] == "unknown"
            and oracle.evaluate(model, clock + 1)["decision"] == "unknown",
        baseline_certificate=oracle.check_certificate(model, result, clock),
        oracle_certificate=oracle.check_certificate(model, reference, clock),
    )
    row["valid"] = all(value is True for key, value in row.items() if key != "run_id")
    checks.append(row)

suite = unittest.defaultTestLoader.discover(str(snapshot / "tests"))
tests = unittest.TextTestRunner(verbosity=2, stream=sys.stderr).run(suite)
successes = sum("projection_equals_saved" in row for row in checks)
failures = len(checks) - successes
count_match = (len(checks) == verification["capture_attempts"]
               and successes == verification["checked_projections"]
               and failures == verification["capture_failures"])
valid = count_match and all(row["valid"] for row in checks) and tests.wasSuccessful()
print(json.dumps({
    "python": sys.version, "platform": platform.platform(),
    "imported_modules": modules, "counts_match": count_match,
    "capture_attempts": len(checks), "checked_projections": successes,
    "capture_failures": failures, "checks": checks,
    "tests_run": tests.testsRun, "test_failures": len(tests.failures),
    "test_errors": len(tests.errors), "test_skips": len(tests.skipped),
    "worker_valid": valid,
}))
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
    if output.exists():
        raise SystemExit("Refusing to overwrite existing replay evidence")
    if output.is_relative_to(snapshot):
        raise SystemExit("Replay output must be outside the immutable archive")
    saved = json.loads(verification.read_text(encoding="utf-8"))
    if saved.get("schema_version") != "historical-projection-verification/0":
        raise SystemExit("Unsupported verification schema")
    before = inventory(snapshot)
    if not before:
        raise SystemExit("Missing or empty source archive")
    source_checks = {}
    for relative, expected in saved["implementation_sha256"].items():
        path = snapshot / relative
        if not path.resolve().is_relative_to(snapshot):
            raise SystemExit("Archived source path escapes snapshot")
        source_checks[relative] = path.is_file() and sha256(path) == expected
    command = [str(args.python.resolve()), "-I", "-B", "-c", WORKER,
               str(snapshot), str(verification)]
    worker = subprocess.run(command, cwd=snapshot, capture_output=True,
                            text=True, encoding="utf-8", timeout=300)
    try:
        result = json.loads(worker.stdout)
    except json.JSONDecodeError:
        result = {"worker_valid": False, "unparsed_stdout": worker.stdout}
    after = inventory(snapshot)
    valid = (all(source_checks.values()) and before == after
             and worker.returncode == 0 and result.get("worker_valid") is True)
    report = {
        "schema_version": "historical-archive-replay/1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_limit": "Fresh-interpreter replay of saved development evidence; no new wire execution, inference, prospective guarantee, novelty or human validation",
        "verification": str(verification), "verification_sha256": sha256(verification),
        "snapshot": str(snapshot), "archive_file_count": len(before),
        "archive_sha256": before, "archive_unchanged": before == after,
        "archived_implementation_matches_saved_hashes": source_checks,
        "replay_driver_sha256": sha256(Path(__file__)),
        "worker_command": [command[0], "-I", "-B", "-c", "WORKER (in hashed replay driver)",
                           str(snapshot), str(verification)],
        "worker_exit_code": worker.returncode, "worker_result": result,
        "test_and_error_output": worker.stderr, "valid": valid,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "archive_unchanged": before == after,
                      "tests_run": result.get("tests_run"),
                      "capture_attempts": result.get("capture_attempts"),
                      "checked_projections": result.get("checked_projections"),
                      "capture_failures": result.get("capture_failures"),
                      "output": str(output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
