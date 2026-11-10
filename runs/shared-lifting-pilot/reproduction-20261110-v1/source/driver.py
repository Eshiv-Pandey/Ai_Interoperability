"""Reproduce the complete retained four-budget pilot once in a fresh allocation.

Uses the original captured replay/verify entrypoints, not current solver files.
Preserves every original allocation file and compares deterministic payloads.
Host-dependent timing/memory observations are retained but never equated.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "runs/shared-lifting-pilot/v1"
BUDGETS = (32, 256, 4096, 100000)
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift")
ENTRYPOINT = "interoperability.shared_lifting_comparison_v3"
BOOT = (
    "import sys; "
    "sys.addaudithook(lambda event,args: (_ for _ in ()).throw("
    "PermissionError('network denied in replay CLI')) if event.startswith('socket.') else None); "
    "sys.path.insert(0,sys.argv[1]); "
    "from interoperability.shared_lifting_comparison_v3 import main; "
    "raise SystemExit(main(sys.argv[2:]))"
)
LIMIT = (
    "Engineering reproduction of 12 authored development inputs at four budgets. "
    "No held-out/application evidence, scientific novelty, speed ranking, "
    "checkpoint pass or human/supervisor approval."
)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def record(path):
    return digest_bytes(Path(path).read_bytes())


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def inventory(directory):
    entries = {}
    for path in sorted(Path(directory).rglob("*")):
        if path.is_symlink():
            raise ValueError("Symbolic link in retained allocation: " + str(path))
        if path.is_file():
            entries[path.relative_to(directory).as_posix()] = record(path)
    return entries


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def without_elapsed(value):
    """Only solver elapsed_ns is nondeterministic inside a result payload."""
    if isinstance(value, dict):
        return {key: without_elapsed(item) for key, item in value.items() if key != "elapsed_ns"}
    if isinstance(value, list):
        return [without_elapsed(item) for item in value]
    return value


def projected_worker(worker):
    keys = ("status", "input_sha256_before", "input_sha256_after", "input_unchanged", "result")
    return {key: without_elapsed(worker[key]) for key in keys if key in worker}


def projected_case(row):
    keys = ("record_type", "case_id", "family", "input_schema", "model_sha256",
            "input_snapshot", "evaluation_clock", "provenance", "reference_valid")
    result = {key: row[key] for key in keys}
    result["reference"] = projected_worker(row["reference"])
    result["algorithms"] = {}
    for name in ARMS:
        arm = row["algorithms"][name]
        selected = {key: arm[key] for key in
                    ("status", "valid_result", "certificate_valid", "decision_agreement")}
        selected["execution"] = projected_worker(arm["execution"])
        if "certificate_check" in arm:
            selected["certificate_check"] = projected_worker(arm["certificate_check"])
        result["algorithms"][name] = selected
    return result


def rows(directory):
    return [json.loads(line) for line in (directory / "results.jsonl").read_bytes().splitlines()]


def observations(case_rows):
    result = {}
    for name in ("reference", *ARMS):
        workers = []
        for row in case_rows:
            if name == "reference":
                workers.append(row["reference"])
            else:
                workers.append(row["algorithms"][name]["execution"])
                if "certificate_check" in row["algorithms"][name]:
                    workers.append(row["algorithms"][name]["certificate_check"])
        peaks = [worker.get("resources", {}).get("memory", {}).get("peak_resident_bytes")
                 for worker in workers]
        observed = [value for value in peaks if type(value) is int]
        result[name] = {
            "workers": len(workers), "memory_observed": len(observed),
            "memory_missing": len(workers) - len(observed),
            "maximum_process_peak_bytes": max(observed) if observed else None,
            "evaluation_ns_observed_total": sum(worker.get("evaluation_ns", 0) or 0 for worker in workers),
            "worker_wall_ns_observed_total": sum(worker["process"]["worker_wall_ns"] for worker in workers),
        }
    return result


def reconcile(original, reproduced):
    old_rows, new_rows = rows(original), rows(reproduced)
    if len(old_rows) != 12 or len(new_rows) != 12:
        raise ValueError("Reproduction does not contain all 12 original cases")
    old, new = list(map(projected_case, old_rows)), list(map(projected_case, new_rows))
    differences = []
    for before, after in zip(old, new):
        if canonical(before) != canonical(after):
            differences.append({"original_case": before["case_id"], "reproduced_case": after["case_id"],
                                "original": before, "reproduced": after})
    execution_keys = ("suite_id", "split", "evaluation_clock", "timeout_seconds", "input_schema",
                      "work_budget", "schema_adapter", "reference_implementation_is_baseline", "algorithms")
    before_execution, after_execution = read(original / "execution.json"), read(reproduced / "execution.json")
    execution_match = canonical({key: before_execution[key] for key in execution_keys}) == canonical(
        {key: after_execution[key] for key in execution_keys})
    coverage = {}
    old_summary, new_summary = read(original / "summary.json"), read(reproduced / "summary.json")
    for name in ARMS:
        fields = ("scheduled", "supported", "unsupported", "unknown", "certificates_valid",
                  "certificates_invalid", "certificate_check_errors", "errors", "decision_agreements")
        before = {key: old_summary["algorithms"][name][key] for key in fields}
        after = {key: new_summary["algorithms"][name][key] for key in fields}
        coverage[name] = {"original": before, "reproduced": after, "matches": canonical(before) == canonical(after)}
    return {
        "deterministic_case_count": 12,
        "deterministic_cases_match": not differences,
        "execution_configuration_matches": execution_match,
        "differences": differences, "coverage": coverage,
        "original_projection": digest_bytes(canonical(old).encode()),
        "reproduced_projection": digest_bytes(canonical(new).encode()),
        "original_observations": observations(old_rows),
        "reproduced_observations": observations(new_rows),
        "observation_limit": "Separate host observations; no equality, speed or memory-superiority claim.",
        "original_status": old_summary["status"], "reproduced_status": new_summary["status"],
    }


def preflight(output):
    output = output.resolve()
    if output.parent != ORIGINAL.parent or output.exists() or output.is_symlink():
        raise ValueError("Require a fresh named allocation directly under runs/shared-lifting-pilot")
    plan = read(ORIGINAL / "plan.json")
    if plan["budgets"] != list(BUDGETS) or plan["case_count"] != 12 or plan["worker_timeout_seconds"] != 30:
        raise ValueError("Original pilot scope or timeout differs")
    captured = ORIGINAL / "source/interoperability"
    expected = {name.removeprefix("source/interoperability/"): entry for name, entry in plan["snapshots"].items()
                if name.startswith("source/interoperability/")}
    actual = {path.relative_to(captured).as_posix(): record(path) for path in captured.rglob("*.py")}
    if actual != expected or len(actual) != 21:
        raise ValueError("Captured package differs from the original prospective plan")
    imported = set()
    for path in captured.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
    unexpected = imported - set(sys.stdlib_module_names) - {"__future__", "interoperability"}
    if unexpected:
        raise ValueError("Captured source imports nonstandard packages: " + repr(sorted(unexpected)))
    forbidden = imported & {"socket", "requests", "http", "google", "openai", "httpx", "grpc"}
    if forbidden:
        raise ValueError("Captured source imports network/provider packages: " + repr(sorted(forbidden)))
    for budget in BUDGETS:
        directory = ORIGINAL / f"budget-{budget}"
        execution = read(directory / "execution.json")
        if (execution["work_budget"] != budget or execution["timeout_seconds"] != 30.0
                or execution["evaluation_clock"] != 100 or execution["runtime"]["executable"] != sys.executable
                or tuple(row["name"] for row in execution["algorithms"]) != ARMS):
            raise ValueError("Original bundle execution identity/scope differs")
        local = {path.relative_to(directory / "source/interoperability").as_posix(): record(path)
                 for path in (directory / "source/interoperability").rglob("*.py")}
        if local != actual:
            raise ValueError("Original budget captured source differs from pilot source")
        if len(read(directory / "replay-suite.json")["cases"]) != 12:
            raise ValueError("Original replay suite lacks complete membership")
    return output, sorted(imported)


def invoke(output, label, argv, limit, environment):
    folder = output / "commands" / label
    folder.mkdir()
    command = {"argv": argv, "cwd": str(ROOT), "timeout_seconds": limit,
               "started_at": now(), "environment_names": sorted(environment), "timed_out": False}
    write(folder / "request.json", command)
    start = time.perf_counter_ns()
    with (folder / "stdout.bin").open("xb") as stdout, (folder / "stderr.bin").open("xb") as stderr:
        try:
            child = subprocess.run(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout,
                                   stderr=stderr, env=environment, timeout=limit)
            command["returncode"] = child.returncode
        except subprocess.TimeoutExpired:
            command.update(returncode=None, timed_out=True)
        except OSError as error:
            command.update(returncode=None, error_type=type(error).__name__, error=str(error))
    command.update(finished_at=now(), wall_ns=time.perf_counter_ns() - start,
                   stdout=record(folder / "stdout.bin"), stderr=record(folder / "stderr.bin"))
    write(folder / "result.json", command)
    return command


def execute(output):
    output, imported = preflight(output)
    before = inventory(ORIGINAL)
    driver = record(Path(__file__))
    interpreter = record(sys.executable)
    output.mkdir()
    (output / "commands").mkdir()
    (output / "source").mkdir()
    with (output / "source/driver.py").open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    environment = {name: os.environ[name] for name in ("SystemRoot", "WINDIR", "TEMP", "TMP") if name in os.environ}
    commands = []
    for budget in BUDGETS:
        original = ORIGINAL / f"budget-{budget}"
        reproduced = output / f"budget-{budget}"
        prefix = [sys.executable, "-I", "-S", "-B", "-c", BOOT, str(ORIGINAL / "source")]
        commands.extend([
            {"label": f"budget-{budget}-replay", "budget": budget, "kind": "replay",
             "argv": prefix + ["replay", str(original), "--output", str(reproduced)], "timeout_seconds": 3420},
            {"label": f"budget-{budget}-verify", "budget": budget, "kind": "verify",
             "argv": prefix + ["verify", str(reproduced)], "timeout_seconds": 120},
        ])
    plan = {"schema_version": "shared-lifting-pilot-reproduction-plan/1", "created_at": now(),
            "original": str(ORIGINAL), "output": str(output), "budgets": list(BUDGETS), "cases_per_budget": 12,
            "arms": list(ARMS), "commands": commands, "original_files": before, "driver": driver,
            "interpreter": {"path": sys.executable, **interpreter}, "stdlib_import_roots": imported,
            "network_limit": "Minimal environment and socket audit denial in outer replay/verify CLI; nested original workers are source-inspected, not OS-network-sandboxed.",
            "worker_bounds": "Sequential original workers: 30 seconds each; maximum 108 per budget; replay internal bound 3360 seconds.",
            "claim_limit": LIMIT}
    write(output / "plan.json", plan)
    write(output / "plan-seal.json", record(output / "plan.json"))
    executions, comparisons, failures = [], {}, []
    start = time.perf_counter_ns()
    try:
        for budget in BUDGETS:
            print(json.dumps({"budget": budget, "status": "starting", "output": str(output)}), flush=True)
            if inventory(ORIGINAL) != before or record(Path(__file__)) != driver or record(sys.executable) != interpreter:
                raise ValueError("Original allocation, driver or interpreter changed before command")
            for command in [row for row in commands if row["budget"] == budget]:
                executed = invoke(output, command["label"], command["argv"], command["timeout_seconds"], environment)
                executions.append({"label": command["label"], **executed})
                if executed["returncode"] != 0 or executed["timed_out"]:
                    raise ValueError("Captured command failed: " + command["label"])
            reproduced = output / f"budget-{budget}"
            comparison = reconcile(ORIGINAL / f"budget-{budget}", reproduced)
            write(output / f"comparison-{budget}.json", comparison)
            comparisons[str(budget)] = comparison
            if (not comparison["deterministic_cases_match"] or not comparison["execution_configuration_matches"]
                    or not all(row["matches"] for row in comparison["coverage"].values())
                    or comparison["reproduced_status"] != "passed"):
                failures.append("Deterministic comparison differs at budget " + str(budget))
            print(json.dumps({"budget": budget, "status": "reproduced",
                              "deterministic_cases_match": comparison["deterministic_cases_match"]}), flush=True)
    except Exception as error:
        failures.append(type(error).__name__ + ": " + str(error))
        with (output / "failure.txt").open("x", encoding="utf-8", newline="\n") as stream:
            traceback.print_exc(file=stream)
    after = inventory(ORIGINAL)
    preserved = before == after and record(Path(__file__)) == driver and record(sys.executable) == interpreter
    if not preserved:
        failures.append("Original allocation, driver or interpreter preservation failed")
    worker_counts = Counter()
    for comparison in comparisons.values():
        for name, observed in comparison["reproduced_observations"].items():
            worker_counts["reference" if name == "reference" else "solver_and_certificate"] += observed["workers"]
    complete = len(comparisons) == 4 and len(executions) == 8
    result = {"schema_version": "shared-lifting-pilot-reproduction-result/1", "status": "passed" if complete and not failures else "failed",
              "finished_at": now(), "wall_ns": time.perf_counter_ns() - start, "complete_four_budget_reproduction": complete,
              "deterministic_cases": 12 * len(comparisons), "algorithm_evaluations": 48 * len(comparisons),
              "worker_counts": dict(worker_counts), "original_files_monitored": len(before),
              "original_allocation_driver_interpreter_unchanged": preserved, "executions": executions,
              "comparisons": comparisons, "failures": failures, "live_application_runs": 0,
              "live_model_calls": 0, "claim_limit": LIMIT}
    write(output / "result.json", result)
    write(output / "manifest.json", {"schema_version": "shared-lifting-pilot-reproduction-manifest/1", "files": inventory(output)})
    print(json.dumps({key: result[key] for key in ("status", "complete_four_budget_reproduction", "deterministic_cases",
                      "algorithm_evaluations", "worker_counts", "original_files_monitored",
                      "original_allocation_driver_interpreter_unchanged", "failures")}), flush=True)
    return 0 if result["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        output, imports = preflight(args.output)
        print(json.dumps({"status": "prepared_without_execution", "output": str(output),
                          "budgets": BUDGETS, "cases_per_budget": 12, "stdlib_import_roots": imports}))
        return 0
    return execute(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
