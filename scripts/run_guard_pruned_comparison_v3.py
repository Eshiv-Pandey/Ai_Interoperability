"""Prospective supplemental finite constraint-pruning comparison.

Four original development budgets and all original profiles. The earlier four
arms are preserved; a fresh conventional comparator is reported separately.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from interoperability import benchmark, direct_comparison_v2 as adapter
from interoperability import shared_lifting_comparison_v3 as preserved
import run_abstraction_control_v1 as capture

BUDGETS = (32, 256, 4096, 100000)
ALGORITHMS = [benchmark.AlgorithmSpec("baseline", adapter.LEGACY, input_schema=adapter.SCHEMA),
              benchmark.AlgorithmSpec("guard_pruned", "interoperability.direct_guard_pruned_v3", input_schema=adapter.SCHEMA)]
LIMIT = "Conventional constraint propagation comparator; authored related development profiles, method-specific work units, no novelty/CPU-speed/application/held-out claim."


def deterministic(execution):
    value = dict(execution["result"])
    if "stats" in value:
        value["stats"] = {k: v for k, v in value["stats"].items() if k != "elapsed_ns"}
    return value


def analyze(fresh, original):
    capture.require(len(fresh) == len(original), "Case count changed")
    counts, pairs, certified, work = Counter(), Counter(), 0, 0
    for now, old in zip(fresh, original):
        capture.require(now["case_id"] == old["case_id"] and now["model_sha256"] == old["model_sha256"]
                        and now["evaluation_clock"] == old["evaluation_clock"], "Profile/clock/order changed")
        baseline, guard = now["algorithms"]["baseline"], now["algorithms"]["guard_pruned"]
        capture.require(deterministic(baseline["execution"]) == deterministic(old["algorithms"]["baseline"]["execution"]),
                        "Fresh preserved baseline differs from original")
        capture.require(guard["valid_result"] is True, "Invalid guard comparator result")
        result = guard["execution"]["result"]
        decision = result["decision"]
        counts[decision] += 1
        work += result["stats"]["work_units"]
        if decision != "unknown":
            capture.require(guard["certificate_valid"] is True, "Guard certificate was not accepted")
            certified += 1
        direct = old["algorithms"]["direct_pruned"]["execution"]["result"]["decision"]
        pairs[direct + "/" + decision] += 1
        if direct != "unknown" and decision != "unknown":
            capture.require(direct == decision, "Conclusive contradiction with retained exact comparator")
    return {"cases": len(fresh), "decisions": dict(sorted(counts.items())), "certified": certified,
            "retained_direct_over_guard_pairs": dict(sorted(pairs.items())), "solver_work_units": work}


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    capture.require(not output.exists() and output.parent.is_dir(), "Require fresh output")
    suite_path = source / "inputs/suite.json"
    suite, cases = benchmark._suite(suite_path)
    capture.require(len(cases) == 66 and suite["evaluation_clock"] == 100, "Wrong development matrix")
    old_bundles = {budget: source / f"budget-{budget}" for budget in BUDGETS}
    old_manifests = {}
    for budget, folder in old_bundles.items():
        preserved.verify(folder)
        old_manifests[budget] = capture.record(folder / "manifest.json", folder)
    # Every interpreter module used by the retained baseline/checker must be
    # unchanged. The new guard module is an explicit supplemental source.
    for name in ("refinement_oracle.py", "oracle.py", "direct_goal_pruned_v2.py", "manifest.py"):
        capture.require((ROOT / "src/interoperability" / name).read_bytes() ==
                        (old_bundles[100000] / "source/interoperability" / name).read_bytes(), "Changed shared source: " + name)
    output.mkdir()
    shutil.copyfile(__file__, output / "driver-source.py")
    shutil.copyfile(ROOT / "src/interoperability/direct_guard_pruned_v3.py", output / "guard-source.py")
    capture.write(output / "plan.json", {"schema_version": "guard-pruned-supplement/3", "started_at": datetime.now(timezone.utc).isoformat(),
        "budgets": list(BUDGETS), "case_count": 66, "clock": 100, "algorithms": [asdict(a) for a in ALGORITHMS],
        "checker": adapter.CHECKER, "checker_budget": 2000000, "worker_timeout_seconds": 30,
        "old_manifests": old_manifests, "source": str(source), "source_suite": capture.record(suite_path, source),
        "new_guard_source": capture.record(output / "guard-source.py", output), "claim_limit": LIMIT,
        "analysis": "All cases and four original budgets. Compare certified decisions against retained goal-pruned direct; reconcile fresh historical baseline exactly. Preserve budget unknowns and adverse results."})
    reports = {}
    try:
        for budget in BUDGETS:
            with adapter._adapter(), capture.resource_workers():
                summary = benchmark.run_benchmark(suite_path, output / f"budget-{budget}", ALGORITHMS,
                                                 work_budget=budget, timeout_seconds=30)
            benchmark.verify_bundle(output / f"budget-{budget}")
            capture.require(summary["status"] == "passed", "Supplemental bundle failed")
            reports[budget] = analyze(capture.rows(output / f"budget-{budget}/results.jsonl"),
                                      capture.rows(old_bundles[budget] / "results.jsonl"))
        for budget, folder in old_bundles.items():
            preserved.verify(folder)
            capture.require(capture.record(folder / "manifest.json", folder) == old_manifests[budget], "Original bundle changed")
        capture.require((ROOT / "src/interoperability/direct_guard_pruned_v3.py").read_bytes() == (output / "guard-source.py").read_bytes(), "Guard source changed")
        capture.write(output / "result.json", {"schema_version": "guard-pruned-supplement/3", "status": "passed",
            "reports": reports, "claim_limit": LIMIT, "original_four_arm_outputs_changed": False,
            "new_application_requests": 0, "new_live_model_requests": 0})
        capture.write(output / "manifest.json", {"files": [capture.record(p, output) for p in sorted(output.rglob("*")) if p.is_file()]})
        return reports
    except Exception as error:
        capture.write(output / "failure.json", {"status": "failed", "error_type": type(error).__name__, "error": str(error)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), sort_keys=True))
