"""Retain every capture attempt and validate historical projections independently."""

import argparse
import hashlib
import json
import subprocess
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from interoperability import baseline, oracle
from interoperability.projection_checker import check_native_sidecar, check_projection
from interoperability.wire_projection import ProjectionError, _decode_json, project_trace

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=ROOT / "runs/wire-observation")
    parser.add_argument("--expected-artifact-text", default="development-destination = Paris")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite existing verification evidence")
    snapshot = args.output.with_suffix(".sources").resolve()
    if not snapshot.is_relative_to(ROOT) or snapshot.exists():
        raise SystemExit("Source snapshot must be a new path inside the workspace")
    files = sorted(args.inputs.glob("*/runtime.json"))
    if not files:
        raise SystemExit("No capture records; never substitute invented observations")
    # Save exact current code/data BEFORE verification so later fixes cannot
    # make a historical source hash impossible to reproduce.
    snapshot.mkdir(parents=True)
    for name in ("src", "tests", "scripts", "examples/development", "runs/wire-observation"):
        source = ROOT / name
        destination = snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    checks = []
    for path in files:
        raw = path.read_bytes()
        trace = _decode_json(raw.decode("utf-8"))
        row = {"input": str(path), "input_sha256": hashlib.sha256(raw).hexdigest(),
               "run_id": trace.get("run_id"), "route_id": trace.get("route_id"),
               "capture_outcome": trace.get("outcome"), "capture_exit_code": trace.get("exit_code")}
        if trace.get("outcome") != "passed":
            row.update(projection_status="capture-failed-not-projectable", capture_error=trace.get("error"))
            checks.append(row)
            continue
        try:
            projection = project_trace(trace, args.expected_artifact_text)
            projected_ok = check_projection(trace, projection)
            clock, manifest = projection["analysis_clock"], projection["manifest"]
            candidate = baseline.evaluate(manifest, clock)
            reference = oracle.evaluate(manifest, clock)
            certificates = {}
            for name, result in (("baseline", candidate), ("oracle", reference)):
                certificates[name] = oracle.check_certificate(manifest, result, clock) if result["decision"] != "unknown" else None
            private = path.parent / "private-native-http.jsonl"
            private_ok = None
            if private.exists():
                private_raw = private.read_bytes()
                records = [_decode_json(line) for line in private_raw.decode("utf-8").splitlines() if line]
                private_ok = check_native_sidecar(trace, records)
                row.update(private_sidecar_sha256=hashlib.sha256(private_raw).hexdigest(),
                           private_sidecar_path=str(private))
            row.update(projection_status="checked", projection=projection,
                       independent_projection_valid=projected_ok,
                       private_native_correlation_valid=private_ok,
                       baseline=candidate, independent_finite_oracle=reference,
                       certificate_validity=certificates,
                       decision_agreement=candidate["decision"] == reference["decision"])
        except (ValueError, OSError) as error:
            row.update(projection_status="rejected", projection_error=f"{type(error).__name__}: {error}")
        checks.append(row)
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    test = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
    hashes = {
        str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in (ROOT / "src", ROOT / "tests", ROOT / "scripts")
        for p in sorted(directory.rglob("*.py"))
    }
    valid = [c for c in checks if c["projection_status"] == "checked"]
    passed = all(c["independent_projection_valid"] and c["private_native_correlation_valid"] is True
                 and c["decision_agreement"] and all(v is not False for v in c["certificate_validity"].values())
                 for c in valid)
    report = {
        "schema_version": "historical-projection-verification/0",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "expected_artifact_text": args.expected_artifact_text,
        "claim_limit": "Historical development traces only; no prospective admission, model completeness, human review or novelty claim",
        "all_capture_attempts_retained": True, "capture_attempts": len(checks),
        "checked_projections": len(valid), "capture_failures": sum(c["capture_outcome"] != "passed" for c in checks),
        "checks": checks, "tests": {"command": command, "exit_code": test.returncode,
                                    "stdout": test.stdout, "stderr": test.stderr},
        "implementation_sha256": hashes,
        "source_and_input_snapshot": str(snapshot),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"capture_attempts": len(checks), "capture_failures": report["capture_failures"],
                      "checked_projections": len(valid), "independent_checks_passed": passed,
                      "test_exit_code": test.returncode, "output": str(args.output)}))
    rejected = any(c["projection_status"] == "rejected" for c in checks)
    return int(not valid or not passed or rejected or test.returncode != 0)


if __name__ == "__main__":
    raise SystemExit(main())
