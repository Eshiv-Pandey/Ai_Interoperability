"""Freeze and run one four-arm extension of the preserved 66-profile matrix.

This is an authored development experiment, not held-out application evidence.
Preparation performs no solver work. Execution uses only the pilot's captured
v3 package and refuses every consumed output allocation.
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
import re
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "runs/refinement-scaling/v2"
PILOT = ROOT / "runs/shared-lifting-pilot/v1"
PARENT = ROOT / "runs/shared-lifting-scaling"
DEFAULT_OUTPUT = PARENT / "v3-20261110-1"
PLAN_DOC = ROOT / "docs/research/shared-lifting-scaling-plan-v3.md"
BUDGETS = (32, 256, 4096, 100000)
CLOCK, CASE_COUNT, WORKER_TIMEOUT, CHECK_BUDGET = 100, 66, 30, 2000000
ENTRYPOINT = "interoperability.shared_lifting_comparison_v3"
ARMS = {
    "baseline": "interoperability.refinement_oracle",
    "direct_pruned": "interoperability.direct_goal_pruned_v2",
    "candidate": "interoperability.refinement",
    "shared_lift": "interoperability.refinement_shared_lift_v2",
}
CHECKER = "interoperability.direct_goal_pruned_v2"
V2_PLAN_SHA = "22e8ad19e16e8a09027ace151594779da0f5cbafa4de4ede062a23aee036536a"
PILOT_PLAN_SHA = "8c66caa0467f09588a533019526df2401f1ac526cd53b7aa364961bffe612265"
EXPECTED_IMPORTS = {
    "__future__", "argparse", "base64", "collections", "contextlib", "copy",
    "ctypes", "dataclasses", "datetime", "hashlib", "importlib", "itertools",
    "json", "math", "pathlib", "platform", "re", "resource", "subprocess",
    "sys", "time", "traceback", "typing", "urllib.parse",
}
BOOT = """import sys
def deny_network(event, arguments):
    if event.startswith('socket.') or event in ('http.client.connect', 'urllib.Request'):
        raise PermissionError('Offline scaling coordinator denies network capabilities')
sys.addaudithook(deny_network)
sys.path.insert(0, sys.argv[1])
from interoperability.shared_lifting_comparison_v3 import main
raise SystemExit(main(sys.argv[2:]))
"""
CLAIM_LIMIT = (
    "Four-arm extension of the same 66 related authored development profiles. "
    "No independently authored held-out templates, application qualification, "
    "algorithmic novelty, universal superiority, speed ranking or checkpoint pass."
)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def record(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path, root):
    path = Path(path)
    require(path.resolve().is_relative_to(root.resolve()), "Path escaped its declared root")
    require(path.is_file() and not path.is_symlink(), "Require an existing regular file: " + str(path))
    for ancestor in path.parents:
        if ancestor == root:
            break
        require(not ancestor.is_symlink(), "Refusing a symbolic directory: " + str(ancestor))
    return path


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def require_record(path, expected):
    require(record(regular(path, ROOT)) == {key: expected[key] for key in ("bytes", "sha256")},
            "Retained bytes differ: " + str(path))


def files_below(path):
    require(path.is_dir() and not path.is_symlink(), "Require a regular directory: " + str(path))
    paths = sorted(path.rglob("*"))
    require(not any(p.is_symlink() for p in paths), "Symbolic member in source/input tree")
    return [p for p in paths if p.is_file()]


def choose_output(path):
    path = Path(path).resolve()
    require(path.parent == PARENT.resolve() and re.fullmatch(r"v3-20261110-[1-9][0-9]*", path.name),
            "Output must be a named fresh v3-20261110 allocation in runs/shared-lifting-scaling")
    require(not PARENT.is_symlink() and not path.is_symlink(), "Symbolic allocation path")
    return path


def prerequisites():
    v2_plan = read(V2 / "plan.json")
    pilot_plan = read(PILOT / "plan.json")
    require(record(V2 / "plan.json")["sha256"] == V2_PLAN_SHA, "Preserved v2 plan hash changed")
    require(record(PILOT / "plan.json")["sha256"] == PILOT_PLAN_SHA, "Preserved pilot plan hash changed")
    require(v2_plan["case_count"] == CASE_COUNT and v2_plan["budgets"] == list(BUDGETS)
            and v2_plan["evaluation_clock"] == CLOCK, "Unexpected frozen v2 scope")
    require(pilot_plan["algorithms"] == ARMS and pilot_plan["clock"] == CLOCK
            and pilot_plan["worker_timeout_seconds"] == WORKER_TIMEOUT,
            "Unexpected captured pilot comparison configuration")
    for item in v2_plan["files"]:
        require_record(V2 / item["path"], item)
    suite = read(V2 / "inputs/suite.json")
    manifest = read(V2 / "inputs/manifest.json")
    require(suite["schema_version"] == "admission-benchmark-suite/1"
            and suite["split"] == "development" and suite["evaluation_clock"] == CLOCK
            and len(suite["cases"]) == CASE_COUNT, "Require the exact 66-case development suite")
    require(manifest["development_only"] is True and manifest["held_out"] is False
            and len(manifest["cases"]) == CASE_COUNT, "Unexpected retained input provenance")
    expected = {row["input"]["path"]: row for row in manifest["cases"]}
    require(len(expected) == CASE_COUNT and len({r["path"] for r in suite["cases"]}) == CASE_COUNT
            and {r["path"] for r in suite["cases"]} == set(expected), "Suite/manifest membership differs")
    cases = []
    for entry in suite["cases"]:
        original = regular(V2 / "inputs" / entry["path"], V2 / "inputs")
        item = expected[entry["path"]]
        require_record(original, item["input"])
        profile = read(original)
        require(profile["schema_version"] == "recipe-continuation/1"
                and profile["id"] == item["profile_id"] and entry["family"] == item["family"],
                "Profile identity/family changed")
        cases.append({"id": profile["id"], "family": item["family"], "scenario": item["scenario"],
                      "parameters": item["parameters"], "path": entry["path"],
                      "expected_with_sufficient_budget": item["expected_decision_with_sufficient_budget"],
                      **record(original)})
    source_records = {name: value for name, value in pilot_plan["snapshots"].items()
                      if name.startswith("source/")}
    require(len(source_records) == 21, "Require the complete 21-file captured v3 package")
    require({p.relative_to(PILOT).as_posix() for p in files_below(PILOT / "source")}
            == set(source_records), "Captured pilot source membership changed")
    imports = set()
    for name, expected_source in source_records.items():
        source = regular(PILOT / name, PILOT)
        require_record(source, expected_source)
        tree = ast.parse(source.read_bytes())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module)
        if source.name == "refinement_oracle.py":
            values = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "CHECK_BUDGET" for t in node.targets)]
            require(values == [CHECK_BUDGET], "Frozen checker allowance changed")
    require(imports == EXPECTED_IMPORTS, "Captured source imports differ from reviewed stdlib-only closure")
    overlap = files_below(V2 / "source/interoperability")
    for old_source in overlap:
        new_source = PILOT / "source/interoperability" / old_source.relative_to(V2 / "source/interoperability")
        require_record(new_source, record(old_source))
    return cases, source_records, len(overlap)


def snapshot(original, target, watches, snapshots, output):
    raw = regular(original, ROOT).read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    value = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    watches[original.relative_to(ROOT).as_posix()] = value
    snapshots[target.relative_to(output).as_posix()] = value


def prepare(output):
    require(not output.exists(), "Preparation allocation is consumed; never reuse it")
    cases, source_records, overlap = prerequisites()
    PARENT.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    watches, snapshots = {}, {}
    watched_trees = [V2 / "inputs", V2 / "source", PILOT / "inputs", PILOT / "source"]
    tree_membership = {p.relative_to(ROOT).as_posix(): [q.relative_to(p).as_posix() for q in files_below(p)]
                       for p in watched_trees}
    for tree in watched_trees:
        for source in files_below(tree):
            watches[source.relative_to(ROOT).as_posix()] = record(source)
    for source in [V2 / "plan.json", PILOT / "plan.json", PILOT / "plan-seal.json",
                   *[V2 / f"budget-{b}/results.jsonl" for b in BUDGETS],
                   *[V2 / f"budget-{b}/summary.json" for b in BUDGETS]]:
        watches[source.relative_to(ROOT).as_posix()] = record(regular(source, ROOT))
    snapshot(Path(__file__).resolve(), output / "driver.py", watches, snapshots, output)
    snapshot(PLAN_DOC, output / "plan.md", watches, snapshots, output)
    snapshot(V2 / "inputs/manifest.json", output / "provenance/v2-input-manifest.json", watches, snapshots, output)
    snapshot(V2 / "plan.json", output / "provenance/v2-plan.json", watches, snapshots, output)
    snapshot(PILOT / "plan.json", output / "provenance/pilot-plan.json", watches, snapshots, output)
    snapshot(V2 / "inputs/suite.json", output / "inputs/suite.json", watches, snapshots, output)
    for case in cases:
        snapshot(V2 / "inputs" / case["path"], output / "inputs" / case["path"], watches, snapshots, output)
    for name in source_records:
        snapshot(PILOT / name, output / name, watches, snapshots, output)
    base = [sys.executable, "-I", "-S", "-B", "-c", BOOT, str(output / "source")]
    commands = []
    for budget in BUDGETS:
        bundle = output / f"budget-{budget}"
        commands.extend([
            {"label": f"budget-{budget}-run", "budget": budget, "kind": "run",
             "argv": base + ["run", "--suite", str(output / "inputs/suite.json"), "--output", str(bundle),
                             "--work-budget", str(budget), "--timeout-seconds", str(WORKER_TIMEOUT)]},
            {"label": f"budget-{budget}-verify", "budget": budget, "kind": "verify",
             "argv": base + ["verify", str(bundle)]},
        ])
    plan = {"schema_version": "shared-lifting-scaling-plan/3", "prepared_at": now(),
            "status": "prepared_not_executed", "budgets": list(BUDGETS), "clock": CLOCK,
            "case_count": CASE_COUNT, "cases": cases, "source_file_count": 21,
            "unchanged_v2_package_overlap": overlap, "algorithms": ARMS, "reference": ARMS["baseline"],
            "checker": CHECKER, "checker_work_allowance": CHECK_BUDGET, "worker_timeout_seconds": WORKER_TIMEOUT,
            "commands": commands, "watches": watches, "snapshots": snapshots,
            "watched_tree_membership": tree_membership, "runtime": {"executable": sys.executable,
            "python": sys.version, "platform": sys.platform}, "serial_workers": True,
            "maximum_worker_jobs": CASE_COUNT * len(BUDGETS) * (1 + 2 * len(ARMS)),
            "coordinator_timeout_seconds": None,
            "coordinator_timeout_reason": "All workers are individually bounded; coordinator is not killed while owning a worker.",
            "network_scope": "Coordinator socket/http/urllib audit denial; frozen workers have reviewed stdlib-only source and fixed module dispatch, not inherited audit denial.",
            "certificate_size": "UTF-8 JSON; sorted keys, compact separators, ensure_ascii=False, allow_nan=False; null when no certificate.",
            "performance_scope": "Single fixed-order observations on the current host; overlapping timing fields are not added; reference and coordinator costs separate.",
            "claim_limit": CLAIM_LIMIT}
    write(output / "plan.json", plan)
    write(output / "plan-seal.json", {"plan": record(output / "plan.json"), "sealed_at": now()})
    print(json.dumps({"status": "prepared_not_executed", "output": str(output),
                      "plan": record(output / "plan.json"), "cases": CASE_COUNT, "source_files": 21}), flush=True)


def guards(output, plan):
    changes = []
    for category, root, entries in (("original", ROOT, plan["watches"]),
                                    ("snapshot", output, plan["snapshots"])):
        for name, expected in entries.items():
            try:
                actual = record(regular(root / name, root))
            except (OSError, ValueError) as error:
                actual = {"error": str(error)}
            if actual != expected:
                changes.append({"category": category, "path": name, "expected": expected, "actual": actual})
    for name, expected in plan["watched_tree_membership"].items():
        try:
            actual = [p.relative_to(ROOT / name).as_posix() for p in files_below(ROOT / name)]
        except (OSError, ValueError) as error:
            actual = {"error": str(error)}
        if actual != expected:
            changes.append({"category": "original_inventory", "path": name, "actual": actual})
    expected = set(plan["snapshots"])
    actual = {p.relative_to(output).as_posix() for folder in ("inputs", "source", "provenance")
              for p in files_below(output / folder)} | {"driver.py", "plan.md"}
    if actual != expected:
        changes.append({"category": "snapshot_inventory", "missing": sorted(expected - actual), "added": sorted(actual - expected)})
    if record(output / "plan.json") != read(output / "plan-seal.json")["plan"]:
        changes.append({"category": "plan_seal"})
    return {"checked_at": now(), "unchanged": not changes, "changes": changes}


def invoke(output, command):
    folder = output / "commands" / command["label"]
    folder.mkdir(parents=True, exist_ok=False)
    environment = {name: os.environ[name] for name in
                   ("SystemRoot", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT", "PATH") if name in os.environ}
    environment.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    receipt = {**command, "cwd": str(output), "started_at": now(), "returncode": None,
               "environment_keys": sorted(environment), "outer_timeout_seconds": None}
    tick = time.perf_counter_ns()
    with (folder / "stdout.bin").open("xb") as stdout, (folder / "stderr.bin").open("xb") as stderr:
        try:
            receipt["returncode"] = subprocess.run(command["argv"], cwd=output, env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False).returncode
        except OSError as error:
            receipt["error"] = type(error).__name__ + ": " + str(error)
    receipt.update(finished_at=now(), coordinator_wall_ns=time.perf_counter_ns() - tick,
                   stdout=record(folder / "stdout.bin"), stderr=record(folder / "stderr.bin"))
    write(folder / "process.json", receipt)
    return receipt


def rows(path):
    result = {}
    for line in path.read_bytes().splitlines():
        value = json.loads(line)
        require(value["case_id"] not in result, "Duplicate result case ID")
        result[value["case_id"]] = value
    return result


def observation(execution):
    execution = execution or {}
    result = execution.get("result")
    result = result if isinstance(result, dict) else {}
    stats = result.get("stats", {})
    certificate = result.get("certificate")
    certificate_raw = canonical(certificate) if isinstance(certificate, dict) else None
    prefixes = certificate.get("refuted_prefixes") if isinstance(certificate, dict) else None
    layers = certificate.get("product_layers") if isinstance(certificate, dict) else None
    return {"execution_status": execution.get("status", "missing"), "decision": result.get("decision"),
            "reason": result.get("reason"), "deterministic_solver_stats": {k: v for k, v in stats.items() if k != "elapsed_ns"},
            "certificate_kind": certificate.get("kind") if isinstance(certificate, dict) else None,
            "canonical_certificate_bytes": len(certificate_raw) if certificate_raw is not None else None,
            "canonical_certificate_sha256": hashlib.sha256(certificate_raw).hexdigest() if certificate_raw is not None else None,
            "refutation_count": len(prefixes) if isinstance(prefixes, list) else None,
            "refutation_edge_count": sum(map(len, prefixes)) if isinstance(prefixes, list) else None,
            "product_layer_count": len(layers) if isinstance(layers, list) else None,
            "product_frame_count": sum(map(len, layers)) if isinstance(layers, list) else None,
            "timing_observations": {"solver_internal_elapsed_ns": stats.get("elapsed_ns"),
                "evaluation_ns": execution.get("evaluation_ns"), "worker_body_ns": execution.get("worker_body_ns"),
                "worker_wall_ns": (execution.get("process") or {}).get("worker_wall_ns")},
            "resource_observations": execution.get("resources"), "input_unchanged": execution.get("input_unchanged")}


def deterministic(execution):
    result = execution.get("result")
    if not isinstance(result, dict):
        return {"status": execution.get("status"), "result": result}
    return {"status": execution.get("status"), "decision": result.get("decision"), "reason": result.get("reason"),
            "certificate": result.get("certificate"),
            "stats": {k: v for k, v in result.get("stats", {}).items() if k != "elapsed_ns"}}


def budget_report(output, plan, budget):
    bundle = output / f"budget-{budget}"
    actual = rows(bundle / "results.jsonl")
    previous = rows(V2 / f"budget-{budget}/results.jsonl")
    expected = {case["id"] for case in plan["cases"]}
    require(set(actual) == expected == set(previous), "Missing or unexpected planned result case")
    verified = read(output / "commands" / f"budget-{budget}-verify/stdout.bin")
    summary = read(bundle / "summary.json")
    coverage = {name: Counter() for name in ARMS}
    families = {}
    cases, differences = [], []
    comparisons = 0
    for case in plan["cases"]:
        row, old = actual[case["id"]], previous[case["id"]]
        require(row["family"] == case["family"] and row["evaluation_clock"] == CLOCK
                and row["model_sha256"] == old["model_sha256"], "Recorded profile binding differs")
        view = {"id": case["id"], "family": case["family"], "scenario": case["scenario"],
                "parameters": case["parameters"], "source": "inputs/" + case["path"],
                "source_sha256": case["sha256"], "model_sha256": row["model_sha256"], "algorithms": {}}
        family = families.setdefault(case["family"], {name: Counter() for name in ARMS})
        for name in ARMS:
            arm = row["algorithms"][name]
            evaluation = observation(arm["execution"])
            decision = evaluation["decision"] or evaluation["execution_status"]
            certified = arm.get("valid_result") is True and arm.get("certificate_valid") is True
            coverage[name][decision] += 1
            coverage[name]["certified"] += int(certified)
            family[name][decision] += 1
            family[name]["certified"] += int(certified)
            view["algorithms"][name] = {"evaluation": evaluation, "valid_result": arm.get("valid_result"),
                "certificate_valid": arm.get("certificate_valid"), "decision_agreement": arm.get("decision_agreement"),
                "checker": arm.get("certificate_check"), "certified": certified}
            if name != "shared_lift":
                comparisons += 1
                if deterministic(arm["execution"]) != deterministic(old["algorithms"][name]["execution"]):
                    differences.append({"id": case["id"], "arm": name, "kind": "deterministic_execution"})
                if arm.get("certificate_valid") != old["algorithms"][name].get("certificate_valid"):
                    differences.append({"id": case["id"], "arm": name, "kind": "certificate_acceptance"})
        view["reference"] = observation(row["reference"])
        cases.append(view)
    paired = Counter()
    for case in cases:
        left = case["algorithms"]["direct_pruned"]["certified"]
        right = case["algorithms"]["shared_lift"]["certified"]
        paired["both_certified" if left and right else "direct_only" if left else "shared_only" if right else "neither_certified"] += 1
    return {"budget": budget, "planned_cases": CASE_COUNT, "recorded_cases": len(actual),
            "coverage": {k: dict(v) for k, v in coverage.items()},
            "family_coverage": {k: {a: dict(v) for a, v in arms.items()} for k, arms in families.items()},
            "shared_vs_direct_paired_certification": dict(paired), "cases": cases,
            "legacy_reconciliation": {"comparisons": comparisons, "unchanged": not differences, "differences": differences},
            "benchmark_summary": summary, "verification": verified,
            "resource_summary": verified.get("resource_summary"),
            "all_cases_remain_in_denominator": True}


def execute(output):
    require(output.is_dir(), "Run preparation before execution")
    plan = read(output / "plan.json")
    require(plan["schema_version"] == "shared-lifting-scaling-plan/3" and plan["budgets"] == list(BUDGETS)
            and plan["case_count"] == CASE_COUNT and plan["clock"] == CLOCK and plan["algorithms"] == ARMS,
            "Unexpected prospective plan")
    require(sys.executable == plan["runtime"]["executable"], "Execution interpreter differs from preparation")
    require(not any((output / name).exists() for name in ("started.json", "result.json", "refused-execution.json", "commands",
                *[f"budget-{budget}" for budget in BUDGETS])), "Execution allocation is consumed; never rerun it")
    initial = guards(output, plan)
    if not initial["unchanged"]:
        write(output / "refused-execution.json", {"refused_at": now(), "guards": initial})
        raise ValueError("Prospective source/input guards failed")
    write(output / "started.json", {"started_at": now(), "plan": record(output / "plan.json"), "guards": initial})
    calls, failure = [], None
    try:
        for command in plan["commands"]:
            before = guards(output, plan)
            require(before["unchanged"], "Frozen inputs/source changed before " + command["label"])
            print("Starting " + command["label"], flush=True)
            receipt = invoke(output, command)
            after = guards(output, plan)
            write(output / "commands" / command["label"] / "guards.json", {"before": before, "after": after})
            calls.append(receipt)
            print(command["label"] + " returned " + str(receipt["returncode"]), flush=True)
            require(after["unchanged"], "Frozen inputs/source changed after " + command["label"])
    except Exception as error:
        failure = {"type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()}
    reports = []
    for budget in BUDGETS:
        try:
            reports.append(budget_report(output, plan, budget))
        except Exception as error:
            reports.append({"budget": budget, "report_error": str(error), "traceback": traceback.format_exc(),
                            "raw_bundle": f"budget-{budget}"})
    final_guard = guards(output, plan)
    complete = len(calls) == 8 and all(c["returncode"] == 0 for c in calls)
    passed = complete and failure is None and final_guard["unchanged"] and all(
        not r.get("report_error") and r["legacy_reconciliation"]["unchanged"]
        and r["verification"]["status"] == "passed" for r in reports)
    result = {"schema_version": "shared-lifting-scaling-result/3", "status": "passed" if passed else "failed",
              "finished_at": now(), "plan": record(output / "plan.json"), "commands": calls,
              "not_invoked_commands": [c["label"] for c in plan["commands"] if c["label"] not in {r["label"] for r in calls}],
              "failure": failure, "final_guards": final_guard, "budgets": reports,
              "source_file_count": plan["source_file_count"], "source_snapshot_hashes": {k: v for k, v in plan["snapshots"].items() if k.startswith("source/")},
              "case_count": CASE_COUNT, "clock": CLOCK, "checker_work_allowance": CHECK_BUDGET,
              "checker_internal_work_counters": None,
              "checker_counter_limit": "Frozen checker returns boolean; internal work counters are not exposed. Function/worker costs are retained.",
              "claim_limit": CLAIM_LIMIT, "network_scope": plan["network_scope"],
              "timing_scope": plan["performance_scope"], "coordinator_cost_separate": True,
              "all_four_budget_bundles_verified": sum(c["kind"] == "verify" and c["returncode"] == 0 for c in calls) == 4}
    write(output / "result.json", result)
    print(json.dumps({"status": result["status"], "result": str(output / "result.json"),
                      "all_four_budget_bundles_verified": result["all_four_budget_bundles_verified"]}), flush=True)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            "Run this driver with -I -S -B")
    output = choose_output(args.output)
    if args.phase == "prepare":
        allocation_existed = output.exists()
        try:
            prepare(output)
        except Exception as error:
            if not allocation_existed and output.is_dir() and not (output / "preparation-failure.json").exists():
                write(output / "preparation-failure.json", {"failed_at": now(), "error": str(error), "traceback": traceback.format_exc()})
            raise
        return 0
    return execute(output)


if __name__ == "__main__":
    raise SystemExit(main())
