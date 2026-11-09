"""Replay retained SDK control evidence without importing or running the SDK.

Use the checker captured before the original function calls in an isolated
Python process. Mutation checks exercise evidence rejection, not new services.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


WORKER = r'''
import copy, importlib.util, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
report_path = sys.argv[2]
checker = root / sys.argv[3]
spec = importlib.util.spec_from_file_location("frozen_sdk_control_checker", checker)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.check_archive(root, report_path)
original = module.decode((root / report_path).read_text(encoding="utf-8"))
mutations = [
    ("missing-case", lambda r: r["cases"].pop()),
    ("reordered-cases", lambda r: r["cases"].reverse()),
    ("wrong-effective-default", lambda r: r["cases"][0].update(effective_requested_version="1.0")),
    ("wrong-property-presence", lambda r: r["cases"][0]["actual_options_descriptor"].update(own_requested_version_property=True)),
    ("fabricated-wire-error", lambda r: r["cases"][0]["validation"]["semantic_exception"].update(has_code=True)),
    ("wrong-error-code", lambda r: r["cases"][0]["optional_official_jsonrpc_mapping"].update(code=-32603)),
    ("successful-call-turned-error", lambda r: r["cases"][2]["validation"].update(accepted=False)),
    ("duplicate-call", lambda r: r["function_calls"].append(r["function_calls"][0])),
    ("wrong-call-order", lambda r: r["function_calls"].reverse()),
    ("wrong-direct-call-cost", lambda r: r["costs"].update(function_calls=0)),
    ("invented-application-observation", lambda r: r.update(applications_executed=True)),
    ("nonterminal-process", lambda r: r.update(exit_code=None)),
    ("changed-source-outcome", lambda r: r["post_source_changes"].append({"source": "changed"})),
    ("wrong-binding", lambda r: r["card"]["supportedInterfaces"][0].update(protocolBinding="HTTP+JSON")),
]
checks = []
for name, mutate in mutations:
    candidate = copy.deepcopy(original)
    mutate(candidate)
    try:
        module.check_semantics(candidate)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        checks.append({"name": name, "rejected": True, "reason": str(error)})
    else:
        checks.append({"name": name, "rejected": False})
# Claimed pass flags have no authority; changing them must not affect replay.
candidate = copy.deepcopy(original)
candidate["software_control_expectations_passed"] = False
for case in candidate["cases"]:
    case["matches_prospective_expectation"] = False
module.check_semantics(candidate)
for name, raw in [("duplicate-json-key", '{"x":1,"x":2}'),
                  ("non-finite-json", '{"x":NaN}')]:
    try:
        module.decode(raw)
    except ValueError as error:
        checks.append({"name": name, "rejected": True, "reason": str(error)})
    else:
        checks.append({"name": name, "rejected": False})
for name, relative in [("escaping-evidence-path", "../outside.json"),
                       ("absolute-evidence-path", str(root.resolve() / "report.json"))]:
    try:
        module.inside(root, relative)
    except ValueError as error:
        checks.append({"name": name, "rejected": True, "reason": str(error)})
    else:
        checks.append({"name": name, "rejected": False})
result.update(mutation_checks=checks, mutation_checks_passed=all(c["rejected"] for c in checks),
              claimed_pass_flags_ignored=True, sdk_imported=False, network_requests=0, model_calls=0)
print(json.dumps(result))
sys.exit(0 if result["mutation_checks_passed"] else 1)
'''


def sha(filename):
    return hashlib.sha256(filename.read_bytes()).hexdigest()


def inventory(directory):
    return [{"path": p.relative_to(directory).as_posix(), "bytes": p.stat().st_size,
             "sha256": sha(p)} for p in sorted(directory.rglob("*")) if p.is_file()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    report = (workspace / args.report).resolve()
    output = (workspace / args.output).resolve()
    if not report.is_relative_to(workspace) or not output.is_relative_to(workspace):
        raise ValueError("Paths must stay in the workspace")
    if output.exists():
        raise FileExistsError(output)
    raw = json.loads(report.read_text(encoding="utf-8"))
    entry = raw["pre_execution"]["source_hashes"]["scripts/check_version_default_control.py"]
    checker = workspace / entry["snapshot"]
    if sha(checker) != entry["sha256"]:
        raise ValueError("Original pre-execution checker bytes changed")
    archive = output.with_suffix(".sources")
    archive.mkdir(parents=True, exist_ok=False)
    attempt = report.parent.relative_to(workspace)
    shutil.copytree(report.parent, archive / attempt)
    driver = Path(__file__).resolve()
    archived_driver = archive / "scripts" / driver.name
    archived_driver.parent.mkdir(parents=True)
    shutil.copyfile(driver, archived_driver)
    before = inventory(archive)
    manifest = {"schema_version": "sdk-control-archive/1", "created_at": datetime.now(timezone.utc).isoformat(),
                "files": before, "original_report": args.report,
                "original_report_sha256": sha(report), "checker_sha256": entry["sha256"]}
    with output.with_suffix(".manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    process = subprocess.run([sys.executable, "-I", "-B", "-c", WORKER, str(archive), args.report,
                              entry["snapshot"]], cwd=archive, capture_output=True, text=True, timeout=60)
    after = inventory(archive)
    result = json.loads(process.stdout) if process.returncode == 0 else None
    checked = {"schema_version": "sdk-control-clean-replay/1", "checked_at": datetime.now(timezone.utc).isoformat(),
               "archive": archive.relative_to(workspace).as_posix(), "archive_files": len(before),
               "archive_unchanged": before == after, "worker_exit_code": process.returncode,
               "worker_stderr": process.stderr, "worker_stdout": process.stdout,
               "result": result, "valid": process.returncode == 0 and before == after,
               "driver_sha256": sha(driver), "claim_limit": "Archived SDK function evidence only; no new SDK or wire execution, novelty or human review"}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(checked, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"valid": checked["valid"], "archive_files": len(before),
                      "mutations_rejected": len(result["mutation_checks"]) if result else None,
                      "output": args.output}))
    return int(not checked["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
