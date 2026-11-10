"""Prospective four-cache-policy comparison on every retained profile/budget."""
from collections import Counter
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from interoperability import benchmark
from interoperability import shared_lifting_comparison_v3 as frozen
from interoperability import shared_cache_comparison_v3 as fresh
import run_abstraction_control_v1 as capture

BUDGETS = (32, 256, 4096, 100000)
POLICIES = ("neither", "prefix", "relation", "both")
LIMIT = "All original authored development profiles; no held-out, application, novelty or universal speed claim. Cache units include shared representation/deduplication work."


def deterministic(value):
    return {key: ({k: v for k, v in item.items() if k != "elapsed_ns"}
                  if key == "stats" else item)
            for key, item in value.items() if key != "method"}


def analyze(rows, old):
    capture.require(len(rows) == len(old) == 66, "Changed denominator")
    counts = {p: Counter() for p in POLICIES}
    pairs = {p: Counter() for p in POLICIES}
    work = {p: 0 for p in POLICIES}
    hits = {p: Counter() for p in POLICIES}
    for row, prior in zip(rows, old):
        capture.require((row["case_id"], row["model_sha256"], row["evaluation_clock"]) ==
                        (prior["case_id"], prior["model_sha256"], prior["evaluation_clock"]), "Changed inputs")
        for name in ("baseline", "direct_pruned"):
            capture.require(deterministic(row["algorithms"][name]["execution"]["result"]) ==
                            deterministic(prior["algorithms"][name]["execution"]["result"]), "Changed comparator")
        capture.require(deterministic(row["algorithms"]["cache_both"]["execution"]["result"]) ==
                        deterministic(prior["algorithms"]["shared_lift"]["execution"]["result"]), "Both-enabled drift")
        direct = row["algorithms"]["direct_pruned"]["execution"]["result"]["decision"]
        for policy in POLICIES:
            arm = row["algorithms"]["cache_" + policy]
            capture.require(arm["valid_result"] is True, "Invalid result")
            result = arm["execution"]["result"]
            decision, stats = result["decision"], result["stats"]
            if decision != "unknown":
                capture.require(arm["certificate_valid"] is True, "Invalid certificate")
            counts[policy][decision] += 1
            pairs[policy][direct + "/" + decision] += 1
            work[policy] += stats["work_units"]
            for name in ("prefix_cache_hits", "relation_cache_hits", "prefix_cache_entries", "relation_cache_entries"):
                hits[policy][name] += stats[name]
            if policy in ("neither", "relation"):
                capture.require(stats["prefix_cache_entries"] == stats["prefix_cache_hits"] == 0, "Disabled prefix used")
            if policy in ("neither", "prefix"):
                capture.require(stats["relation_cache_entries"] == stats["relation_cache_hits"] == 0, "Disabled relation used")
    return {p: {"cases": 66, "decisions": dict(counts[p]), "direct_pairs": dict(pairs[p]),
                "solver_work_units": work[p], "cache_counters": dict(hits[p])} for p in POLICIES}


def run(source, output):
    source, output = source.resolve(), output.resolve()
    capture.require(not output.exists(), "Refuse existing allocation")
    suite = source / "inputs/suite.json"
    _, cases = benchmark._suite(suite)
    capture.require(len(cases) == 66, "Wrong retained suite")
    bindings = {}
    for budget in BUDGETS:
        folder = source / f"budget-{budget}"
        frozen.verify(folder)
        bindings[budget] = capture.record(folder / "manifest.json", folder)
    output.mkdir(parents=True)
    shutil.copyfile(__file__, output / "driver-source.py")
    capture.write(output / "plan.json", {"schema_version": "shared-cache-ablation-plan/3",
        "started_at": datetime.now(timezone.utc).isoformat(), "case_count": 66,
        "budgets": list(BUDGETS), "cache_policies": list(POLICIES), "evaluation_clock": 100,
        "worker_timeout_seconds": 30, "source_manifests": bindings, "claim_limit": LIMIT,
        "analysis": "All cells and failures retained; both-enabled, baseline and goal-pruned direct must reproduce retained deterministic results. Pair policies with strongest direct on identical inputs. Include checking/proof/process costs."})
    reports, verifications = {}, {}
    try:
        for budget in BUDGETS:
            result = fresh.run(suite, output / f"budget-{budget}", work_budget=budget, timeout_seconds=30)
            capture.require(result["status"] == "passed", "Benchmark unsuccessful")
            verifications[budget] = result["verification"]
            reports[budget] = analyze(capture.rows(output / f"budget-{budget}/results.jsonl"),
                                     capture.rows(source / f"budget-{budget}/results.jsonl"))
        for budget in BUDGETS:
            frozen.verify(source / f"budget-{budget}")
            capture.require(capture.record(source / f"budget-{budget}/manifest.json", source / f"budget-{budget}") ==
                            bindings[budget], "Frozen source changed")
        capture.write(output / "result.json", {"schema_version": "shared-cache-ablation-result/3", "status": "passed",
            "reports": reports, "verifications": verifications, "claim_limit": LIMIT,
            "algorithm_cells": 66 * 4 * 6, "cache_policy_cells": 66 * 4 * 4,
            "new_application_requests": 0, "new_provider_requests": 0})
        capture.write(output / "manifest.json", {"files": [capture.record(p, output) for p in sorted(output.rglob("*")) if p.is_file()]})
        return reports
    except Exception as error:
        capture.write(output / "failure.json", {"status": "failed", "error_type": type(error).__name__, "error": str(error)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), sort_keys=True))
