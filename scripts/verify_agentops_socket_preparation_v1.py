"""Verify the sealed preparation and retained failure; no runtime execution.

This does not verify any future v8 capture, prove novelty, or award a gate.
"""
import argparse
import json
from pathlib import Path

import resume_agentops_socket_observer_v8 as resume
from check_agentops_linux_workspace_v5 import load, require, verify_rows
from run_agentops_linux_workspace_v5 import record

ROOT = resume.ROOT


def check():
    seal = load(resume.SEAL)
    require(seal.get("schema_version") == "agentops-socket-resume-preparation/1", "Preparation seal schema")
    verify_rows(ROOT, seal["replica_inputs"])
    verify_rows(ROOT, seal["artifacts"])
    old = load(resume.PRIOR / "execution.json")["inputs"]
    additions = [record(ROOT / name, ROOT) for name in resume.ADDITIONS]
    require(sorted(old + additions, key=lambda row: row["path"]) == seal["replica_inputs"], "Exact launch input set")
    require(seal["prior_attempt"] == record(resume.PRIOR / "result.json", ROOT)
            and seal["prior_export"] == record(resume.PRIOR / "export-manifest.json", ROOT), "Prior failure bindings")
    manifest = load(resume.PRIOR / "export-manifest.json")
    names = verify_rows(resume.PRIOR / "workspace", manifest["files"])
    resume.validate_prior(load(resume.PRIOR / "result.json"))
    expected = [
        ("runs/agentops-native-eligibility/socket-policy-validation-v1", 5),
        ("runs/agentops-http-control/socket-policy-validation-v5", 12),
        ("runs/agentops-native-eligibility/socket-resume-validation-v8", 7),
    ]
    for name, count in expected:
        receipt = load(ROOT / name / "result.json")
        require(type(receipt["returncode"]) is int and receipt["returncode"] == 0, "Software validation failed")
        output = (ROOT / name / "stderr.bin").read_text(encoding="utf-8")
        require(f"Ran {count} tests" in output and output.rstrip().endswith("OK"), "Software test completion missing")
    return {"status": "preparation_and_prior_integrity_verified", "replica_inputs": len(seal["replica_inputs"]),
            "prior_export_files": len(names), "software_tests": sum(count for _, count in expected),
            "prior_native_outcome": "failed", "prior_http_outcome": "not_run",
            "v8_attempt_exists": resume.OUTPUT.exists(), "linux_runtime_revalidated": False,
            "v8_capture_verified": False, "scientific_gate_credit_added": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Retain the earlier verification")
    result = {"schema_version": "agentops-socket-preparation-check/1", "status": "failed"}
    try:
        result.update(check())
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["status"] == "failed" else 0)
