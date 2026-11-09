"""Prospective development budget matrix; write only this fresh allocation."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

sys.dont_write_bytecode = True
RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
BUDGETS = (32, 256, 4096, 100000)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_bytes())


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def record(path, root=RUN):
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(directory):
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink not allowed in frozen inputs")
        if path.is_file():
            files.append(record(path))
    return files


def verify_rows(rows):
    for row in rows:
        if record(RUN / row["path"]) != row:
            raise ValueError("Frozen file changed: " + row["path"])


def prepare():
    if (RUN / "plan.json").exists() or (RUN / "inputs").exists():
        raise FileExistsError("Matrix allocation is already prepared/consumed")
    generator_path = ROOT / "scripts/generate_refinement_scaling_v1.py"
    spec = importlib.util.spec_from_file_location("matrix_generator", generator_path)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generated = generator.generate(RUN / "inputs", generator.configuration(
        widths=(2, 4), depths=(2, 4), argument_counts=(1, 2), budgets=BUDGETS))
    if generated["cases"] != 66:
        raise ValueError("Unexpected generated case count")
    package = RUN / "source/interoperability"
    package.mkdir(parents=True, exist_ok=False)
    originals = sorted((ROOT / "src/interoperability").glob("*.py"))
    before = [record(path, ROOT) for path in originals]
    for path in originals:
        if path.is_symlink():
            raise ValueError("Symlink in original package")
        with (package / path.name).open("xb") as target:
            target.write(path.read_bytes())
    if before != [record(path, ROOT) for path in originals]:
        raise ValueError("Current package changed during snapshot")
    for name in generator.SOURCES:
        if (package / name).read_bytes() != (RUN / "inputs/source" / name).read_bytes():
            raise ValueError("Generation and frozen measurement package differ: " + name)
    environment = {"PYTHONPATH": str(RUN / "source"), "PYTHONDONTWRITEBYTECODE": "1"}
    allocations = []
    for budget in BUDGETS:
        allocation = RUN / "invocations" / ("budget-" + str(budget))
        allocation.mkdir(parents=True, exist_ok=False)
        output = RUN / ("budget-" + str(budget))
        if output.exists():
            raise FileExistsError("Prospective benchmark output already exists")
        command = [sys.executable, "-B", "-m", "interoperability", "benchmark",
                   "--suite", str(RUN / "inputs/suite.json"), "--algorithm", "candidate=interoperability.refinement:evaluate",
                   "--work-budget", str(budget), "--timeout-seconds", "30", "--output", str(output)]
        verify = [sys.executable, "-B", "-m", "interoperability", "benchmark", "--verify", str(output)]
        value = {"schema_version": "recipe-scaling-budget-allocation/1", "budget": budget,
                 "benchmark_output": str(output), "cwd": str(RUN), "environment_overrides": environment,
                 "benchmark_argv": command, "verify_argv": verify, "maximum_attempts": 1,
                 "evaluation_clock": 100, "case_count": 66, "worker_timeout_seconds": 30,
                 "coordinator_timeout_seconds": 1800}
        write_new(allocation / "plan.json", value)
        allocations.append({"budget": budget, "plan": record(allocation / "plan.json")})
    plan = {"schema_version": "recipe-scaling-matrix-plan/1", "created_at_utc": now(),
            "status": "frozen_not_evaluated", "run": str(RUN), "budgets": list(BUDGETS), "case_count": 66,
            "evaluation_clock": 100, "allocations": allocations, "files": inventory(RUN / "inputs") + inventory(RUN / "source"),
            "driver": record(Path(__file__)), "generator_original": record(generator_path, ROOT),
            "original_package": before, "python": {"executable": sys.executable, "version": sys.version,
                "platform": platform.platform(), "logical_cpus": os.cpu_count()},
            "comparison": "Current benchmark CLI and verifier from one frozen package; same input bytes, clock and integer budget for reference/direct/candidate",
            "contention": "Other root live-work may contend for CPU. Wall-clock observations are retained but do not support speed superiority claims.",
            "development_only": True, "held_out": False, "qualified_domains": 0, "novelty_established": False,
            "work_units_are_identical_primitives": False, "reference_implementation_is_baseline": True}
    write_new(RUN / "plan.json", plan)
    print(json.dumps({"status": plan["status"], "cases": 66, "budgets": list(BUDGETS), "plan": record(RUN / "plan.json")}), flush=True)


def invoke(folder, name, argv, environment, timeout):
    receipt = {"argv": argv, "cwd": str(RUN), "started_at_utc": now(), "timed_out": False,
               "returncode": None, "environment_overrides": environment}
    write_new(folder / (name + ".started.json"), receipt)
    start = time.perf_counter_ns()
    with (folder / (name + ".stdout.bin")).open("xb") as stdout, (folder / (name + ".stderr.bin")).open("xb") as stderr:
        try:
            result = subprocess.run(argv, cwd=RUN, env={**os.environ, **environment}, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, timeout=timeout)
            receipt["returncode"] = result.returncode
        except subprocess.TimeoutExpired:
            receipt["timed_out"] = True
        except OSError as error:
            receipt["error"] = type(error).__name__ + ": " + str(error)
    receipt.update(finished_at_utc=now(), coordinator_wall_ns=time.perf_counter_ns() - start,
                   streams=[record(folder / (name + suffix)) for suffix in (".stdout.bin", ".stderr.bin")])
    write_new(folder / (name + ".receipt.json"), receipt)
    return receipt


def aggregate(directory):
    rows = [json.loads(line) for line in (directory / "results.jsonl").read_bytes().splitlines()]
    summary = load(directory / "summary.json")
    profiles = {item["profile_id"]: item for item in load(RUN / "inputs/manifest.json")["cases"]}
    families, details = {}, []
    for row in rows:
        detail = {"case_id": row["case_id"], "family": row["family"],
                  "scenario": profiles[row["case_id"]]["scenario"], "parameters": profiles[row["case_id"]]["parameters"],
                  "authored_expectation": profiles[row["case_id"]]["expected_decision_with_sufficient_budget"],
                  "algorithms": {}}
        for name in ("baseline", "candidate"):
            algorithm = row["algorithms"][name]
            execution = algorithm["execution"]
            result = execution.get("result") or {}
            group = families.setdefault(row["family"], {}).setdefault(name, {
                "cases": 0, "decisions": Counter(), "reasons": Counter(), "certificate_valid": 0,
                "certificate_invalid": 0, "execution_statuses": Counter(), "stats_totals": Counter()})
            group["cases"] += 1
            group["decisions"][result.get("decision", "missing")] += 1
            group["reasons"][result.get("reason", "missing")] += 1
            group["execution_statuses"][execution["status"]] += 1
            group["certificate_valid"] += algorithm.get("certificate_valid") is True
            group["certificate_invalid"] += algorithm.get("certificate_valid") is False
            for key, value in result.get("stats", {}).items():
                if type(value) is int and key not in ("elapsed_ns", "budget", "peak_frames"):
                    group["stats_totals"][key] += value
            detail["algorithms"][name] = {"decision": result.get("decision"), "reason": result.get("reason"),
                "certificate_valid": algorithm.get("certificate_valid"), "stats": result.get("stats"),
                "execution_status": execution["status"]}
        details.append(detail)
    algorithms = {}
    for name, values in summary["algorithms"].items():
        algorithms[name] = {key: values[key] for key in ("scheduled", "returned_valid", "errors", "supported", "unsupported", "unknown",
             "conclusive", "certificates_valid", "certificates_invalid", "certificate_check_errors", "certified_coverage", "decision_agreements")}
        algorithms[name]["certificate_timing"] = values["certificate_timing"]
    return {"summary": record(directory / "summary.json"), "results": record(directory / "results.jsonl"),
            "status": summary["status"], "algorithms": algorithms, "families": families, "cases": details,
            "all_invocation_timing": summary["all_invocation_timing"], "reference_timing": summary["reference_timing"]}


def run():
    plan = load(RUN / "plan.json")
    verify_rows(plan["files"] + [plan["driver"]] + [row["plan"] for row in plan["allocations"]])
    plan_record = record(RUN / "plan.json")
    result = {"schema_version": "recipe-scaling-matrix-result/1", "status": "started", "started_at_utc": now(),
              "plan": plan_record, "budgets": {}, "errors": [], "development_only": True, "held_out": False,
              "qualified_domains": 0, "novelty_established": False, "contention": plan["contention"]}
    write_new(RUN / "execution.json", result)
    try:
        for allocation in plan["allocations"]:
            budget = allocation["budget"]
            frozen = load(RUN / allocation["plan"]["path"])
            folder = (RUN / allocation["plan"]["path"]).parent
            verify_rows(plan["files"] + [plan["driver"], plan_record, allocation["plan"]])
            print(json.dumps({"event": "budget_started", "budget": budget, "at_utc": now()}), flush=True)
            benchmark = invoke(folder, "benchmark", frozen["benchmark_argv"], frozen["environment_overrides"], 1800)
            verify = invoke(folder, "verify", frozen["verify_argv"], frozen["environment_overrides"], 300)
            output = Path(frozen["benchmark_output"])
            row = {"benchmark": record(folder / "benchmark.receipt.json"), "verify": record(folder / "verify.receipt.json"),
                   "benchmark_returncode": benchmark["returncode"], "verify_returncode": verify["returncode"],
                   "status": "invalid_or_incomplete"}
            result["budgets"][str(budget)] = row
            if benchmark["returncode"] != 0 or verify["returncode"] != 0:
                raise ValueError("Budget output invalid/incomplete; later allocations remain unexecuted: " + str(budget))
            row.update(status="verified", **aggregate(output))
            verify_rows(plan["files"] + [plan_record, plan["driver"]])
            write_new(folder / "result.json", row)
            print(json.dumps({"event": "budget_complete", "budget": budget, "status": row["status"],
                "decisions": {name: {key: values[key] for key in ("supported", "unsupported", "unknown")}
                              for name, values in row["algorithms"].items()}}), flush=True)
        result["status"] = "passed"
    except Exception as error:
        result["status"] = "failed"
        result["errors"].append(type(error).__name__ + ": " + str(error))
    finally:
        for budget in BUDGETS:
            result["budgets"].setdefault(str(budget), {"status": "unexecuted", "reason": "An earlier allocation did not validate"})
        try:
            verify_rows(plan["files"] + [plan_record, plan["driver"]])
            result["frozen_inputs_package_and_plan_unchanged"] = True
        except Exception as error:
            result["frozen_inputs_package_and_plan_unchanged"] = False
            result["status"] = "failed"
            result["errors"].append(str(error))
        result["finished_at_utc"] = now()
        write_new(RUN / "result.json", result)
    print(json.dumps({"event": "matrix_complete", "status": result["status"], "errors": result["errors"]}), flush=True)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["run"]:
        raise SystemExit(run())
    else:
        raise SystemExit("Use prepare once, then run once")
