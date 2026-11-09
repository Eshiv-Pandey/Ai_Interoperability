"""Reconcile all retained budget outputs and write a development results note."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
RUN = REVIEW.parent
ROOT = RUN.parents[2]
BUDGETS = (32, 256, 4096, 100000)


def load(path):
    return json.loads(path.read_bytes())


def record(path, root=RUN):
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory():
    return [record(path) for path in sorted(RUN.rglob("*")) if path.is_file() and not path.is_relative_to(REVIEW)]


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def main():
    before = inventory()
    write_new(REVIEW / "before.json", before)
    report = {"schema_version": "recipe-scaling-matrix-review/1", "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "started", "reviewer": "AI result reconciliation; not human review",
              "plan": record(RUN / "plan-v2.json"), "matrix_result": record(RUN / "result.json"),
              "benchmarks_rerun": 0, "failures": [], "budgets": {}, "worker_jobs": 0,
              "certificate_checks": 0, "certificate_rejections": 0, "checker_errors_or_exhaustions": 0,
              "nonempty_worker_stderr_files": 0, "authored_expectation_contradictions": []}

    def check(value, message):
        if not value:
            report["failures"].append(message)

    try:
        plan, matrix = load(RUN / "plan-v2.json"), load(RUN / "result.json")
        check(matrix["status"] == "passed" and matrix["frozen_inputs_package_and_plan_unchanged"] is True, "Matrix did not complete unchanged")
        check(matrix["plan"] == record(RUN / "plan-v2.json"), "Matrix plan hash mismatch")
        for row in plan["files"] + [plan["driver"]] + [entry["plan"] for entry in plan["allocations"]]:
            check(record(RUN / row["path"]) == row, "Frozen matrix input mismatch: " + row["path"])
        labels = load(RUN / "inputs/manifest.json")["cases"]
        expected = {item["profile_id"]: item["expected_decision_with_sufficient_budget"] for item in labels}
        profiles = {item["profile_id"]: load(RUN / "inputs" / item["input"]["path"]) for item in labels}
        report["authored_sufficient_budget_expectations"] = dict(Counter(expected.values()))
        original_ids = None
        for budget in BUDGETS:
            directory = RUN / f"budget-{budget}"
            manifest, summary, execution = (load(directory / name) for name in ("manifest.json", "summary.json", "execution.json"))
            actual = [record(path, directory) for path in sorted(directory.rglob("*")) if path.is_file() and path != directory / "manifest.json"]
            check(sorted(actual, key=lambda row: row["path"]) == sorted(manifest["files"], key=lambda row: row["path"]),
                  "Budget manifest inventory differs: " + str(budget))
            check(sum(row["bytes"] for row in actual) == manifest["bytes"], "Manifest byte sum differs")
            check(execution["work_budget"] == budget and execution["evaluation_clock"] == 100, "Clock/allowance mismatch")
            for path in sorted((RUN / "source/interoperability").glob("*.py")):
                check(path.read_bytes() == (directory / "source/interoperability" / path.name).read_bytes(), "Captured package differs: " + path.name)
            rows = [json.loads(line) for line in (directory / "results.jsonl").read_bytes().splitlines()]
            ids = [(row["case_id"], row["model_sha256"]) for row in rows]
            if original_ids is None:
                original_ids = ids
            check(ids == original_ids and len(ids) == 66, "Input order/digests differ across budgets")
            conclusive_on_reference_unknown = 0
            algorithms = {}
            for name, item in summary["algorithms"].items():
                algorithms[name] = {key: item[key] for key in ("supported", "unsupported", "unknown", "certificates_valid",
                    "certified_coverage", "certificates_invalid", "certificate_check_errors", "conclusive_on_reference_unknown",
                    "abstained_on_reference_decided")}
                algorithms[name]["certificate_cost"] = {"calls": item["certificate_timing"]["invocations"],
                    "function_ns": item["certificate_timing"]["evaluation_ns"]["total"],
                    "worker_wall_ns": item["certificate_timing"]["worker_wall_ns"]["total"]}
            for row in rows:
                check(row["evaluation_clock"] == 100, "Case clock mismatch")
                for name in ("baseline", "candidate"):
                    value = row["algorithms"][name]
                    result = value["execution"]["result"]
                    check(result["stats"]["budget"] == budget, "Actual solver budget differs")
                    if result["decision"] in ("supported", "unsupported"):
                        check(value.get("certificate_valid") is True, "Conclusive result lacks accepted certificate")
                        if result["decision"] != expected[row["case_id"]]:
                            report["authored_expectation_contradictions"].append({"budget": budget, "case_id": row["case_id"], "algorithm": name})
                    else:
                        check(result["certificate"] is None, "Unknown has a certificate")
                    if budget == 100000:
                        check(result["decision"] == expected[row["case_id"]], "Sufficient-budget authored expectation mismatch")
                candidate = row["algorithms"]["candidate"]
                conclusive_on_reference_unknown += (row["reference"]["result"]["decision"] == "unknown"
                    and candidate.get("certificate_valid") is True)
            check(conclusive_on_reference_unknown == algorithms["candidate"]["conclusive_on_reference_unknown"], "Reference abstention count mismatch")
            jobs = list((directory / "jobs").iterdir())
            check(len(jobs) == summary["all_invocation_timing"]["invocations"], "Invocation accounting differs")
            for folder in jobs:
                job, process, reply = (load(folder / name) for name in ("input.json", "process.json", "reply.json"))
                check(job["runtime_manifest"] == profiles[job["runtime_manifest"]["id"]], "A job received a different input or external labels")
                check(job["now"] == 100, "Worker clock differs")
                check(process["returncode"] == 0 and process["timed_out"] is False, "Worker failed/timed out")
                check(reply["status"] == "returned" and reply["input_unchanged"] is True, "Worker failed or mutated input")
                report["worker_jobs"] += 1
                report["nonempty_worker_stderr_files"] += (folder / "stderr.bin").stat().st_size > 0
                if job["kind"] == "certificate":
                    report["certificate_checks"] += 1
                    report["certificate_rejections"] += reply.get("result") is not True
                    report["checker_errors_or_exhaustions"] += reply["status"] != "returned" or reply.get("result") is not True
                else:
                    check(job.get("keyword_arguments") == {"budget": budget}, "A solver/reference job has different allowance")
            report["budgets"][str(budget)] = {"manifest": record(directory / "manifest.json"), "jobs": len(jobs),
                "algorithms": algorithms, "families": matrix["budgets"][str(budget)]["families"]}
        check(not report["authored_expectation_contradictions"], "A conclusive result contradicted an authored expectation")
        check(report["worker_jobs"] == 1145 and report["certificate_checks"] == 353, "Unexpected total job/check count")
        check(report["certificate_rejections"] == report["checker_errors_or_exhaustions"] == 0, "Rejected/errored certificate checks")
    except Exception as error:
        report["failures"].append(type(error).__name__ + ": " + str(error))
    after = inventory()
    write_new(REVIEW / "after.json", after)
    report["measured_artifacts_unchanged"] = before == after
    check(before == after, "Measured artifacts changed during reconciliation")
    report["status"] = "verified" if not report["failures"] else "review_discrepancies"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_new(REVIEW / "result.json", report)
    print(json.dumps({key: report[key] for key in ("status", "worker_jobs", "certificate_checks", "certificate_rejections", "checker_errors_or_exhaustions", "measured_artifacts_unchanged", "failures")}, indent=2))
    return report


if __name__ == "__main__":
    report = main()
    raise SystemExit(0 if report["status"] == "verified" else 1)
