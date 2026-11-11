"""Recheck retained implementation evidence without original apps/provider calls.

Writes only a new supplied audit directory. This supports a delivery audit, not
an award of scientific gates or a whole-project completion percentage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def identity(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(262144), b""):
            h.update(block)
            size += len(block)
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": size, "sha256": h.hexdigest()}


def bound_records(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value
        for item in value.values():
            yield from bound_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from bound_records(item)


def verify_records(label, records, base=None):
    seen = set()
    checks = []
    errors = []
    for record in records:
        original = record["path"]
        path = Path(original)
        if not path.is_absolute():
            path = (ROOT / base / path) if base else (ROOT / path)
        key = (str(path.resolve()), record["sha256"])
        if key in seen:
            continue
        seen.add(key)
        try:
            current = identity(path)
            digest_equal = current["sha256"] == record["sha256"]
            size_equal = "bytes" not in record or current["bytes"] == record["bytes"]
            checks.append({**current, "expected_sha256": record["sha256"],
                           "digest_equal": digest_equal, "size_equal": size_equal})
            if not digest_equal or not size_equal:
                errors.append({"path": original, "reason": "identity_mismatch"})
        except (OSError, ValueError) as exc:
            errors.append({"path": original, "reason": type(exc).__name__})
    return {"label": label, "files_checked": len(checks), "errors": errors,
            "status": "passed" if not errors else "failed", "checks": checks}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def command(directory, name, args):
    start = dt.datetime.now(dt.timezone.utc).isoformat()
    timer = time.monotonic()
    result = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=300,
                            check=False)
    out = directory / (name + ".stdout.txt")
    err = directory / (name + ".stderr.txt")
    out.write_bytes(result.stdout)
    err.write_bytes(result.stderr)
    return {"id": name, "argv": args, "cwd": str(ROOT), "started_at_utc": start,
            "elapsed_seconds": round(time.monotonic() - timer, 6),
            "exit_code": result.returncode, "stdout": identity(out),
            "stderr": identity(err),
            "original_application_or_sdk_execution": False,
            "provider_requests": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    directory = args.output_dir.resolve()
    directory.relative_to(ROOT)
    directory.mkdir(parents=True, exist_ok=False)
    groups = []
    implementation = read("runs/implementation-acceptance/audit-v1.json")
    groups.append(verify_records("historical_algorithm_comparison_current_bytes",
                                 bound_records(implementation)))
    analysis = read("runs/research-analysis/independent-review-v1.json")
    groups.append(verify_records("analysis_input_bytes", analysis["source_bindings"]))
    groups.append(verify_records("analysis_output_bytes", analysis["output_bindings"],
                                 analysis["analysis_directory"]))
    groups.append(verify_records("analysis_result_bytes", [analysis["analysis_result"]]))
    ci = read("runs/ci-research-core/download-42819352517/retained-manifest.json")
    groups.append(verify_records("linux_retained_inventory", ci["files"],
                                 "runs/ci-research-core/download-42819352517"))
    agent = read("runs/ci-agentops-native/download-42808110286/export/manifest.json")
    # The exporter records copied files relative to its exported workspace.
    groups.append(verify_records("agentops_export_inventory", agent["copied"]["files"],
                                 "runs/ci-agentops-native/download-42808110286/export/workspace"))
    ap2_base = "runs/ap2-original-native-provider-development/v2/retained-42995902326-1"
    ap2_manifest = read(ap2_base + "/extracted-manifest.json")
    groups.append(verify_records("ap2_v2_extracted_inventory", ap2_manifest["files"],
                                 ap2_base + "/extracted"))
    semantic = read("runs/ap2-original-native-provider-development/v2/independent-semantic-analysis-v1/analysis.json")
    groups.append(verify_records("ap2_v2_semantic_evidence", [
        {"path": path, **record} for path, record in semantic["evidence_bindings"].items()]))
    parts = read(ap2_base + "/archive-parts-v3/index.json")
    joined = hashlib.sha256()
    total = 0
    parts_checks = []
    for part in parts["parts"]:
        path = ROOT / ap2_base / "archive-parts-v3" / part["name"]
        current = identity(path)
        if current["sha256"] != part["sha256"] or current["bytes"] != part["bytes"]:
            raise ValueError("Archive part identity mismatch")
        parts_checks.append(current)
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(262144), b""):
                joined.update(block)
                total += len(block)
    archive = {"status": "passed" if joined.hexdigest() == parts["identity"]["sha256"]
               and total == parts["identity"]["bytes"] else "failed",
               "archive_sha256": joined.hexdigest(), "archive_bytes": total,
               "part_checks": parts_checks, "archive_restored_or_executed": False}
    write(directory / "evidence-integrity.json", {
        "schema_version": "overnight-acceptance-integrity/1",
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "groups": groups, "ap2_archive": archive,
        "reviewer": "AI retained-byte audit",
        "original_application_or_sdk_execution": False, "provider_requests": 0})
    python = sys.executable
    commands = []
    commands.append(command(directory, "complete-task-bank", [python, "-I", "-S", "-B",
        "scripts/validate_task_banks_v1.py", "--require-complete", "--output",
        str(directory / "task-bank-validation.json")]))
    focused = ("import sys,unittest;sys.path[:0]=['src','scripts','tests'];"
               "suite=unittest.defaultTestLoader.loadTestsFromNames(["
               "'test_refinement_shared_lift_v2','test_shared_admission_v1',"
               "'test_direct_goal_pruned_v2','test_shared_lifting_comparison_v3',"
               "'test_pending_admission','test_task_bank_validation_v1',"
               "'test_ap2_original_native_provider_semantics_v2']);"
               "result=unittest.TextTestRunner(verbosity=1).run(suite);"
               "raise SystemExit(not result.wasSuccessful())")
    commands.append(command(directory, "focused-tests", [python, "-I", "-S", "-B", "-c", focused]))
    verify = ("import sys;sys.path.insert(0,'src');"
              "from interoperability.shared_lifting_comparison_v3 import main;"
              "raise SystemExit(main(sys.argv[1:]))")
    for budget in (32, 256, 4096, 100000):
        commands.append(command(directory, "linux-bundle-" + str(budget),
            [python, "-I", "-S", "-B", "-c", verify, "verify",
             "runs/ci-research-core/download-42819352517/budget-" + str(budget)]))
    commands.append(command(directory, "ap2-v2-semantic-recheck", [python, "-I", "-S", "-B",
        "scripts/analyze_ap2_original_native_provider_v2.py", "--retained-root", ap2_base,
        "--archive-sha256", parts["identity"]["sha256"], "--output",
        str(directory / "ap2-v2-semantic-recheck.json")]))
    write(directory / "commands.json", {"schema_version": "overnight-acceptance-commands/1",
        "commands": commands, "audit_source": identity(__file__)})
    failures = [group["label"] for group in groups if group["status"] != "passed"]
    failures += [item["id"] for item in commands if item["exit_code"] != 0]
    if archive["status"] != "passed":
        failures.append("ap2_archive")
    print(json.dumps({"audit_directory": str(directory), "failures": failures,
                      "files_hashed": sum(g["files_checked"] for g in groups),
                      "commands": len(commands)}, indent=2))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
