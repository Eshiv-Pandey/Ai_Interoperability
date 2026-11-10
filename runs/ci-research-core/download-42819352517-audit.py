"""Independent read-only audit of the actual hosted core artifact.

Uses trusted current-checkout validators/checker, never downloaded Python code.
Output is a new sibling receipt; the downloaded artifact is never modified.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "runs/ci-research-core/download-42819352517"
OUTPUT = ROOT / "runs/ci-research-core/download-42819352517-independent-review.json"
sys.path.insert(0, str(ROOT / "src"))
from interoperability import benchmark
from interoperability.direct_goal_pruned_v2 import check_certificate
from interoperability.shared_lifting_comparison_v3 import verify

BUDGETS = (32, 256, 4096, 100000)
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift")
PINS = {
    32: "b33c6491e0b175e76fff8ae8826ddd039e8d545b0ed28c9d5bc19c6ff2cbedcf",
    256: "b8465e02cf8bdaf0e9dd6a67bdc982130b7c64d462de69e2cd5fbbc49a6c8399",
    4096: "de30ac1a2cbc1523a15b2f44a0ca619a2683ce06f572eac3870f1f446b8efcb0",
    100000: "92137f9cc15feac73fb51b9777cd961be307c6161bf6ad5c797ef3464ff1817c",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def raw(path):
    require(path.is_file() and not path.is_symlink(), "Nonregular retained file: " + str(path))
    return path.read_bytes()


def read(path):
    return json.loads(raw(path))


def sha(path):
    return hashlib.sha256(raw(path)).hexdigest()


def record(path, base):
    value = raw(path)
    return {"path": path.relative_to(base).as_posix(), "bytes": len(value),
            "sha256": hashlib.sha256(value).hexdigest()}


def safe(base, name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == name
            and "\\" not in name, "Unsafe manifest path")
    return base / name


def inventory(base, items, excluded=()):
    names = {item["path"] for item in items}
    require(len(names) == len(items), "Duplicate inventory records")
    for item in items:
        require(record(safe(base, item["path"]), base) == item, "Hash mismatch: " + item["path"])
    actual = {path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file()}
    require(actual == names | set(excluded), "Entire retained inventory differs")
    return {"files": len(items), "bytes": sum(item["bytes"] for item in items)}


def rows(path):
    records = [json.loads(line) for line in raw(path).splitlines()]
    require(len({item["case_id"] for item in records}) == len(records), "Duplicate case ID")
    return {item["case_id"]: item for item in records}


def deterministic(execution):
    value = deepcopy(execution)
    for name in ("evaluation_ns", "worker_body_ns", "process", "resources"):
        value.pop(name, None)
    result = value.get("result")
    if isinstance(result, dict) and isinstance(result.get("stats"), dict):
        result["stats"].pop("elapsed_ns", None)
    return value


def pure_check(model, result, clock):
    model_copy, result_copy = deepcopy(model), deepcopy(result)
    accepted = check_certificate(model_copy, result_copy, clock)
    require(accepted is True, "Independent pure checker rejected a retained certificate")
    require(model_copy == model and result_copy == result, "Pure checker mutated input/result")


def main():
    require(not OUTPUT.exists(), "Audit receipt already exists; never overwrite a completed audit")
    before = sha(ARTIFACT / "retained-manifest.json")
    manifest = read(ARTIFACT / "retained-manifest.json")
    checked = inventory(ARTIFACT, manifest["files"], ("retained-manifest.json",))
    result, plan, seal = (read(ARTIFACT / name) for name in ("result.json", "plan.json", "plan-seal.json"))
    require(record(ARTIFACT / "plan.json", ARTIFACT) == seal["plan"], "Plan seal does not bind the retained plan")
    require(result["status"] == manifest["status"] == "passed", "Hosted driver did not pass")
    require(plan["github"]["GITHUB_SHA"] == "9ef339fa349cf73b6c3558d2c3f51dc967f89444"
            and plan["github"]["GITHUB_RUN_ID"] == "42819352517"
            and plan["github"]["GITHUB_RUN_ATTEMPT"] == "1"
            and plan["github"]["RUNNER_OS"] == "Linux", "Hosted revision/run identity differs")
    require(plan["runtime"]["python"].startswith("3.13.1 "), "Hosted Python differs")
    require(plan["budgets"] == list(BUDGETS) and plan["algorithms"] == list(ARMS)
            and plan["worker_timeout_seconds"] == 30 and plan["checker_work_budget"] == 2000000,
            "Prospective algorithm/budget/checker design differs")
    require(len(plan["cases"]) == 66 and len({item["id"] for item in plan["cases"]}) == 66,
            "Incomplete planned denominator")
    captured = {item["path"]: item for item in plan["captured_inventory"]}
    for name, item in captured.items():
        require(record(safe(ARTIFACT, name), ARTIFACT) == item, "Captured plan input differs")
    current_differences = []
    for item in plan["original_inventory"]:
        source = safe(ROOT, item["path"])
        if source.is_file() and record(source, ROOT) != item:
            current_differences.append(item["path"])
        require(source.is_file(), "Current checkout original is missing: " + item["path"])
    require(not current_differences, "Current checkout source/input differs from hosted planned bytes")
    for field in ("post_test_integrity", "final_integrity"):
        require(result[field] == {"unchanged": True, "changes": []}, "Reported input integrity failed")
    require(sha(ARTIFACT / "inputs/suite.json") == "5ed596bcaf8e4868f1159db9773f1d3cb80b5334fd2b65fe4e4abbfb9fb93738"
            and sha(ARTIFACT / "inputs/manifest.json") == "73dca6c030e709da2707969c15f5f590eec7b1c35fe0bcb3ef5829fa5a87933e",
            "Original suite/manifest pin differs")
    suite, input_manifest = read(ARTIFACT / "inputs/suite.json"), read(ARTIFACT / "inputs/manifest.json")
    require(suite["evaluation_clock"] == 100 and suite["split"] == "development", "Suite clock/split differs")
    for item in input_manifest["cases"]:
        require(record(safe(ARTIFACT / "inputs", item["input"]["path"]), ARTIFACT / "inputs") == item["input"],
                "Profile no longer matches original frozen input manifest")
    commands = {item["label"]: item for item in result["commands"]}
    require(set(commands) == {"existing-core-tests", *[f"budget-{b}-{mode}" for b in BUDGETS for mode in ("run", "verify")]},
            "Missing/unexpected outer commands")
    for label, receipt in commands.items():
        require(read(ARTIFACT / f"commands/{label}/process.json") == receipt, "Outer command receipt differs")
        require(receipt["returncode"] == 0 and receipt["timed_out"] is False, "A real outer command failed")
        for name in ("stdout", "stderr"):
            require(record(safe(ARTIFACT, receipt[name]["path"]), ARTIFACT) == receipt[name], "Raw command stream binding differs")
    tests = read(ARTIFACT / "commands/existing-core-tests/stdout.bin")
    require(tests == result["tests"] == {"tests_run": 167, "errors": 0, "failures": 0, "skipped": 0, "successful": True},
            "Existing test result differs")
    require(re.search(rb"Ran 167 tests in .*\n\nOK\s*$", raw(ARTIFACT / "commands/existing-core-tests/stderr.bin")),
            "Complete unittest raw summary missing")
    reports, comparison_count, reference_count, certificate_count, reference_cert_count = [], 0, 0, 0, 0
    jobs_count, failed_workers, timed_out_workers, memory_counts = 0, 0, 0, Counter()
    for budget in BUDGETS:
        bundle = ARTIFACT / f"budget-{budget}"
        checked_bundle = verify(bundle)
        require(checked_bundle == read(ARTIFACT / f"commands/budget-{budget}-verify/stdout.bin"),
                "Trusted verifier disagrees with hosted verifier")
        reported = next(item for item in result["budgets"] if item["budget"] == budget)
        require(checked_bundle == reported["verification"] and checked_bundle["benchmark_status"] == "passed",
                "Driver budget verifier binding differs")
        require(sha(ARTIFACT / f"reference/budget-{budget}/results.jsonl") == PINS[budget], "Windows reference result pin differs")
        actual, retained = rows(bundle / "results.jsonl"), rows(ARTIFACT / f"reference/budget-{budget}/results.jsonl")
        require(set(actual) == set(retained) == {item["id"] for item in plan["cases"]}, "All cases must stay in denominator")
        coverage = {name: Counter() for name in ARMS}
        budget_certificates, budget_reference_certificates = 0, 0
        for item in plan["cases"]:
            row, old = actual[item["id"]], retained[item["id"]]
            for field in ("case_id", "family", "evaluation_clock", "model_sha256", "input_schema", "reference_valid", "provenance"):
                require(row[field] == old[field], "Cross-OS case binding differs: " + field)
            require(row["family"] == item["family"] and row["evaluation_clock"] == 100 and set(row["algorithms"]) == set(ARMS),
                    "Planned row design differs")
            require(deterministic(row["reference"]) == deterministic(old["reference"]), "Reference deterministic result differs")
            reference_count += 1
            model = read(bundle / row["input_snapshot"])
            require(benchmark.digest(model) == row["model_sha256"], "Semantic input binding differs")
            if row["reference"]["result"]["decision"] != "unknown":
                pure_check(model, row["reference"]["result"], 100)
                reference_cert_count += 1
                budget_reference_certificates += 1
            for name in ARMS:
                fresh, previous = row["algorithms"][name], old["algorithms"][name]
                require(set(fresh) == set(previous), "Arm/checker field membership differs")
                for field in set(fresh) - {"execution", "certificate_check"}:
                    require(fresh[field] == previous[field], "Validity/agreement/status flag differs")
                require(deterministic(fresh["execution"]) == deterministic(previous["execution"]), "Complete solver result/certificate/stats differs")
                comparison_count += 1
                decision = fresh["execution"]["result"]["decision"]
                coverage[name][decision] += 1
                coverage[name]["certified"] += int(fresh["valid_result"] is True and fresh["certificate_valid"] is True)
                if "certificate_check" in fresh:
                    require(deterministic(fresh["certificate_check"]) == deterministic(previous["certificate_check"]), "Checker result/input-integrity differs")
                    pure_check(model, fresh["execution"]["result"], 100)
                    certificate_count += 1
                    budget_certificates += 1
        require({arm: dict(counts) for arm, counts in coverage.items()} == reported["coverage"], "Recomputed coverage differs")
        require(reported["deterministic_unchanged"] is True and reported["differences"] == [], "Reported differences not empty")
        for folder in (bundle / "jobs").iterdir():
            receipt = read(folder / "process.json")
            jobs_count += 1
            failed_workers += int(receipt["returncode"] != 0)
            timed_out_workers += int(receipt["timed_out"])
            reply = read(folder / "reply.json")
            memory = reply["resources"]["memory"]
            require(memory["status"] == "observed" and type(memory["peak_resident_bytes"]) is int
                    and memory["peak_resident_bytes"] > 0, "Missing/nonpositive Linux peak observation")
            memory_counts[(memory["platform"], memory["source"])] += 1
        reports.append({"budget": budget, "cases": 66, "arm_comparisons": 264, "reference_comparisons": 66,
                        "solver_certificates_independently_rechecked": budget_certificates,
                        "reference_certificates_independently_rechecked": budget_reference_certificates,
                        "worker_jobs_bound": checked_bundle["worker_jobs_bound"],
                        "coverage": {arm: dict(counts) for arm, counts in coverage.items()},
                        "trusted_verifier_matches_hosted": True, "deterministic_differences": [],
                        "summary_sha256": sha(bundle / "summary.json"), "manifest_sha256": sha(bundle / "manifest.json")})
    require(comparison_count == result["algorithm_comparisons"] == 1056 and reference_count == 264,
            "Comparison denominator differs")
    require(jobs_count == result["worker_jobs_bound"] == 2003 and certificate_count == result["certificate_jobs_bound"] == 683,
            "Worker/checker totals differ")
    require(failed_workers == timed_out_workers == 0, "A real matrix worker failed or timed out")
    require(memory_counts == Counter({("linux", "getrusage(RUSAGE_SELF).ru_maxrss"): 2003}), "Unexpected OS memory meter")
    inventory(ARTIFACT, manifest["files"], ("retained-manifest.json",))
    require(sha(ARTIFACT / "retained-manifest.json") == before, "Audit mutated artifact manifest")
    review = {
        "schema_version": "ci-research-core-independent-review/1", "status": "passed",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": "42819352517", "run_attempt": 1,
        "run_url": "https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42819352517",
        "head_sha": plan["github"]["GITHUB_SHA"], "artifact_name": "research-core-42819352517-1",
        "github_artifact_id": 13765264923, "github_reported_archive_digest": "sha256:b6735569ddc6fdcc2806c43e64c1e439cf6342b43bf0d2d2fbe5b5769ab19e4a",
        "transport_archive_digest_locally_rechecked": False,
        "download_directory": ARTIFACT.relative_to(ROOT).as_posix(), "retained_inventory": checked,
        "retained_manifest_sha256": before, "sealed_plan_sha256": sha(ARTIFACT / "plan.json"),
        "captured_plan_inputs_checked": len(captured), "current_checkout_source_differences": current_differences,
        "tests": tests, "outer_commands_checked": len(commands), "actual_outer_command_failures": 0,
        "actual_matrix_worker_failures": failed_workers, "actual_matrix_worker_timeouts": timed_out_workers,
        "hosted_run_attempts_examined": [1], "favorable_auto_retry": False,
        "algorithm_comparisons": comparison_count, "reference_comparisons": reference_count,
        "checker_output_comparisons": certificate_count,
        "solver_certificates_independently_rechecked": certificate_count,
        "reference_certificates_independently_rechecked": reference_cert_count,
        "worker_jobs_bound": jobs_count, "all_cases_remain_in_denominator": True,
        "memory_observations": {"linux:getrusage(RUSAGE_SELF).ru_maxrss": 2003},
        "memory_interpretation": "Linux ru_maxrss converted from KiB to bytes; Windows references use PeakWorkingSetSize. Distinct OS meters, no cross-OS memory/timing equality claim.",
        "comparison_exclusions": ["stats.elapsed_ns", "evaluation_ns", "worker_body_ns", "process", "resources"],
        "budget_results": reports,
        "verification_method": "Independent inventory hashing/projection and trusted current-checkout verifier/pure checker; no downloaded code executed",
        "audit_source": Path(__file__).relative_to(ROOT).as_posix(), "audit_source_sha256": sha(Path(__file__)),
        "live_model_calls": result["live_model_calls"], "live_application_runs": result["live_application_runs"],
        "artifact_unchanged_by_audit": True,
        "claim_limit": "Cross-OS reproduction of the complete authored development matrix; no held-out application, human-review, novelty or superiority conclusion"}
    require(review["live_model_calls"] == review["live_application_runs"] == 0, "Unexpected model/application calls")
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(review, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": review["status"], "files": checked["files"], "bytes": checked["bytes"],
                      "tests": tests, "algorithm_comparisons": comparison_count, "reference_comparisons": reference_count,
                      "solver_certificates": certificate_count, "reference_certificates": reference_cert_count,
                      "worker_jobs": jobs_count}))


if __name__ == "__main__":
    main()
