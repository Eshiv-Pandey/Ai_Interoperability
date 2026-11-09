"""Archive and check actual Carol bridge evidence without executing services.

Expected task outcomes never determine validation. All attempts are retained.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from interoperability import baseline, oracle
from interoperability.status_projection import project_status_trace
from interoperability.status_projection_checker import check_status_projection, check_status_native_sidecar
from interoperability.wire_projection import _decode_json

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Evidence path escapes root")
    return path


def check_run(root, relative):
    """Reproduce public/native/source-ledger claims solely from archived inputs."""
    path = inside(root, relative)
    trace = _decode_json(path.read_bytes().decode("utf-8"))
    row = {"input": relative, "input_sha256": sha256(path), "run_id": trace.get("run_id"),
           "variant": trace.get("variant_id"), "capture_outcome": trace.get("outcome"),
           "capture_exit_code": trace.get("exit_code")}
    if trace.get("outcome") != "recorded" or trace.get("exit_code") != 0:
        row.update(classification="unsuccessful-attempt-retained", valid=False,
                   capture_error=trace.get("error"))
        return row
    try:
        projection = project_status_trace(trace)
        public_valid = check_status_projection(trace, projection)
        native_path = inside(root, trace["private_sidecars"]["native_http"])
        records = [_decode_json(line) for line in native_path.read_bytes().decode("utf-8").splitlines() if line]
        native_valid = check_status_native_sidecar(trace, records)
        model, clock = projection["manifest"], projection["analysis_clock"]
        ordinary, reference = baseline.evaluate(model, clock), oracle.evaluate(model, clock)
        certificates = {name: (oracle.check_certificate(model, result, clock)
                              if result["decision"] != "unknown" else None)
                        for name, result in (("baseline", ordinary), ("oracle", reference))}
        pre = trace["pre_execution"]
        snapshots_ok = all(sha256(inside(root, info["snapshot"])) == info["sha256"]
                           for info in pre["source_hashes"].values())
        specification_ok = sha256(inside(root, pre["specification"]["path"])) == pre["specification"]["sha256"]
        ledger_path = path.parent / "pre-execution-ledger.json"
        ledger_ok = _decode_json(ledger_path.read_bytes().decode("utf-8")) == pre
        source_ok = not trace.get("post_source_errors") and not trace.get("post_source_changes") and all(
            trace["post_source_sha256"].get(name) == info["sha256"] for name, info in pre["source_hashes"].items())
        tree_checks = {}
        for name in ("bridge_source_manifest", "bridge_dist_manifest"):
            manifest = pre[name]
            tree = inside(root, manifest["snapshot_root"])
            expected = {entry["path"]: entry["sha256"] for entry in manifest["entries"]}
            tree_checks[name] = inventory(tree) == expected and len(expected) == manifest["file_count"]
        runtime = trace["pre_bridge_runtime_config"]
        runtime_ok = sha256(inside(root, runtime["path"])) == runtime["sha256"]
        completed = [r for r in records if r.get("type") == "exchange-completed"]
        native_costs = {"http_requests": len(completed),
                        "rpc_requests": sum(type(r["request"].get("json")) is dict for r in completed),
                        "request_body_bytes": sum(r["request"]["bytes"] for r in completed),
                        "response_body_bytes": sum(r["response"]["bytes"] for r in completed)}
        requests = [e["request"] for e in trace["exchanges"] if e.get("request")]
        expected_costs = {"mcp_rpc_requests": sum("id" in r["json"] for r in requests),
                          "mcp_notifications_sent": sum("id" not in r["json"] for r in requests),
                          "request_bytes": sum(r["bytes"] for r in requests),
                          "response_bytes": sum(e["response"]["bytes"] for e in trace["exchanges"] if e.get("response"))}
        costs_ok = all(trace["costs"].get(k) == v for k, v in expected_costs.items())
        cleanup = trace.get("cleanup", [])
        cleanup_ok = len(cleanup) == 2 and {r["role"] for r in cleanup} == {"carol", "bridge"} and all(
            r.get("normal_exit") is True and r.get("exit", {}).get("code") == 0
            and r["exit"].get("signal") is None and not r.get("fallback_kill_requested") for r in cleanup)
        carol = next(r for r in cleanup if r["role"] == "carol")
        cleanup_ok &= carol.get("server_close", {}).get("server_listening") is False
        validity = {"independent_public_projection": public_valid, "independent_native_correlation": native_valid,
                    "snapshot_hashes": snapshots_ok, "prospective_specification": specification_ok,
                    "source_ledger_matches_report": ledger_ok, "sources_unchanged_during_capture": source_ok,
                    "runtime_configuration_hash": runtime_ok, "bridge_source_archive": all(tree_checks.values()),
                    "mcp_cost_ledger": costs_ok, "specific_children_closed_normally": cleanup_ok,
                    "finite_decision_agreement": ordinary["decision"] == reference["decision"],
                    "certificates": all(value is not False for value in certificates.values()),
                    "later_clock_abstains": baseline.evaluate(model, clock + 1)["decision"] == "unknown"
                    and oracle.evaluate(model, clock + 1)["decision"] == "unknown"}
        row.update(classification="checked-actual-authored-port-observation", projection=projection,
                   baseline=ordinary, independent_finite_oracle=reference, certificates=certificates,
                   checks=validity, native_sidecar_sha256=sha256(native_path), native_costs=native_costs,
                   mcp_costs=expected_costs, tree_checks=tree_checks, observed=trace.get("observation"),
                   source_based_expectation_is_validation_condition=False,
                   valid=all(value is True for value in validity.values()))
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as error:
        row.update(classification="retained-rejected-observation", valid=False,
                   validation_error=f"{type(error).__name__}: {error}")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    snapshot = output.with_suffix(".sources")
    if not output.is_relative_to(ROOT) or output.exists() or snapshot.exists():
        raise SystemExit("Verification and archive must be new workspace paths")
    inputs = sorted((ROOT / "runs/reference-bridge-observation").glob("*/runtime.json"))
    if not inputs:
        raise SystemExit("No actual captures; never substitute software controls")
    snapshot.mkdir(parents=True)
    directories = [ROOT / name for name in ("src", "tests", "scripts", "examples/development", "runs/wire-observation")]
    directories += [p.parent for p in inputs]
    directories += [p.parent for p in (ROOT / "runs/native-reference-continuation").glob("carol-*/report.json")]
    directories += [p.parent for p in (ROOT / "runs/reference-port-native").glob("*/report.json")]
    for source in directories:
        destination = snapshot / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("docs/research/reference-bridge-probe-v1.md", "docs/research/status-projection-independent-review.md", "external/source-lock.json"):
        source = ROOT / name
        destination = snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    before = inventory(snapshot)
    checks = [check_run(snapshot, path.relative_to(ROOT).as_posix()) for path in inputs]
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    test = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300)
    after = inventory(snapshot)
    inputs_stable = all(sha256(ROOT / row["input"]) == row["input_sha256"] for row in checks)
    implementation = {name: value for name, value in before.items() if name.startswith(("src/", "tests/", "scripts/"))}
    implementation_stable = all(sha256(ROOT / name) == value for name, value in implementation.items())
    variants = [row["variant"] for row in checks]
    all_four = len(variants) == 4 and set(variants) == {"R1", "R2", "R3", "R4"}
    valid = (all_four and all(row["valid"] for row in checks) and test.returncode == 0
             and before == after and inputs_stable and implementation_stable)
    report = {"schema_version": "reference-bridge-verification/1", "recorded_at": datetime.now(timezone.utc).isoformat(),
              "claim_limit": "Four authored Carol-port route observations and software/source/data checks only; no unchanged-application prevalence, prospective unsupported/admission, candidate advantage, novelty or human review",
              "attempt_count": len(checks), "all_four_single_attempts": all_four, "checks": checks,
              "archive": str(snapshot), "archive_sha256": before, "archive_unchanged": before == after,
              "input_hashes_stable": inputs_stable, "implementation_sha256": implementation,
              "implementation_matches_archive": implementation_stable,
              "tests": {"command": command, "exit_code": test.returncode, "stdout": test.stdout, "stderr": test.stderr},
              "valid": valid}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "attempts": len(checks), "all_four_single_attempts": all_four,
                      "checked": sum(row["valid"] for row in checks), "test_exit_code": test.returncode,
                      "output": str(output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
