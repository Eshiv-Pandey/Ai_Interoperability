"""Independent retained Linux release audit using stdlib and trusted pure checks.

No downloaded source, original SDK/application or provider is executed. Current
certificate checkers are used only after binding their bytes to captured source.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN = 43079771054
HEAD = "577f34a82a32d3a891db2018a68823ba98f21e48"
ARCHIVE_SHA = "994131b2ce6f063c6a806c8cdf136b3412fe1b9a30fcf082be8a44c005aa3208"
METHODS = ("baseline", "direct_pruned", "candidate", "shared_lift")


def need(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def file_identity(path):
    need(path.is_file() and not path.is_symlink(), "regular_file_required:" + str(path))
    h, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(262144):
            h.update(raw)
            size += len(raw)
    return {"bytes": size, "sha256": h.hexdigest()}


def record(path):
    path = path.resolve()
    need(path.is_relative_to(ROOT), "workspace_evidence_required")
    return {"path": path.relative_to(ROOT).as_posix(), **file_identity(path)}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


class Evidence:
    def __init__(self, base):
        self.base = base.resolve()
        self.bindings = {}
        self.retention = self.external("retention.json")
        need(self.retention["run_id"] == RUN and self.retention["head_sha"] == HEAD
             and self.retention["archive_bytes"] == 16754100 and self.retention["archive_sha256"] == ARCHIVE_SHA
             and self.retention["api_digest"] == "sha256:" + ARCHIVE_SHA, "exact_release_retention_required")
        run = self.external("github-run.json")
        need(run["id"] == RUN and run["head_sha"] == HEAD and run["conclusion"] == "success", "run_metadata_binding_differs")
        artifacts = self.external("github-artifacts.json")["artifacts"]
        selected = [row for row in artifacts if row["id"] == self.retention["artifact_id"]]
        need(len(selected) == 1 and selected[0]["digest"] == "sha256:" + ARCHIVE_SHA
             and selected[0]["name"] == self.retention["artifact_name"], "API_artifact_binding_differs")
        archive = self.base / "artifact.zip"
        archive_identity = record(archive)
        need(archive_identity["sha256"] == ARCHIVE_SHA and archive_identity["bytes"] == 16754100, "actual_ZIP_identity_differs")
        self.bindings[archive_identity["path"]] = archive_identity
        manifest = self.external("extracted-manifest.json")["files"]
        self.members = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in manifest}
        need(len(self.members) == len(manifest) == 12999, "complete_extracted_inventory_required")
        seen = set()
        self.expanded_bytes = 0
        with zipfile.ZipFile(archive) as zipped:
            for item in zipped.infolist():
                if item.is_dir():
                    continue
                name = PurePosixPath(item.filename)
                need(not name.is_absolute() and ".." not in name.parts and "\\" not in item.filename
                     and str(name) == item.filename and item.filename not in seen, "unsafe_duplicate_archive_member")
                seen.add(item.filename)
                expected = self.members.get(item.filename)
                h, size = hashlib.sha256(), 0
                with zipped.open(item) as stream:
                    while raw := stream.read(262144):
                        h.update(raw)
                        size += len(raw)
                actual = {"bytes": size, "sha256": h.hexdigest()}
                need(actual == expected, "archive_manifest_member_differs:" + item.filename)
                need(file_identity(self.base / "extracted" / item.filename) == expected, "extracted_member_differs:" + item.filename)
                self.expanded_bytes += size
        need(seen == set(self.members), "archive_inventory_membership_differs")

    def external(self, name):
        path = self.base / name
        binding = record(path)
        self.bindings[binding["path"]] = binding
        return json.loads(path.read_bytes())

    def raw(self, name):
        need(name in self.members, "unbound_member_read:" + name)
        path = self.base / "extracted" / name
        need(file_identity(path) == self.members[name], "member_changed_during_review:" + name)
        self.bindings[path.relative_to(ROOT).as_posix()] = {"member": name, **self.members[name]}
        return path.read_bytes()

    def json(self, name):
        return json.loads(self.raw(name))

    def rows(self, name):
        rows = [json.loads(line) for line in self.raw(name).splitlines() if line.strip()]
        need(len({row["case_id"] for row in rows}) == len(rows), "unique_case_rows_required")
        return {row["case_id"]: row for row in rows}

    def check_records(self, prefix, records):
        seen = set()
        for item in records:
            name = prefix + item["path"]
            need(name not in seen, "duplicate_record")
            seen.add(name)
            need(self.members.get(name) == {key: item[key] for key in ("bytes", "sha256")},
                 "record_member_identity_differs:" + name)
        return len(seen)


def deterministic(execution):
    result = execution.get("result")
    if not isinstance(result, dict):
        projected = {"status": execution.get("status"), "result": result}
    else:
        projected = {"status": execution.get("status"),
            "result": {key: value for key, value in result.items() if key != "stats"}}
        projected["result"]["stats"] = {key: value for key, value in result.get("stats", {}).items() if key != "elapsed_ns"}
    projected.update({key: execution.get(key) for key in ("input_sha256_before", "input_sha256_after", "input_unchanged")})
    return canonical(projected)


def audit(base, component_path):
    evidence = Evidence(base)
    manifest_reviews = []
    for name in sorted(name for name in evidence.members if name.endswith("retained-manifest.json")):
        manifest = evidence.json(name)
        prefix = name[:-len("retained-manifest.json")]
        files = manifest["files"]
        evidence.check_records(prefix, files)
        expected = {prefix + item["path"] for item in files}
        actual = {member for member in evidence.members if member.startswith(prefix) and member != name}
        need(expected == actual, "nested_retained_manifest_membership_differs:" + name)
        need(manifest["status"] == "passed", "retained_manifest_status_not_passed:" + name)
        manifest_reviews.append({"path": name, "status": "passed", "members": len(files)})
    outer_plan = evidence.json("plan.json")
    outer_result = evidence.json("result.json")
    software_plan = evidence.json("software/plan.json")
    software_result = evidence.json("software/result.json")
    need(outer_plan["historical_failed_run"] == 43076696650 and outer_plan["historical_failure_preserved"] is True,
         "first_failed_run_not_preserved")
    need(outer_result["status"] == software_result["status"] == "passed"
         and outer_result["outer_owned_groups_confirmed_closed"] is True
         and software_result["outer_owned_groups_confirmed_closed"] is True, "release_result_not_strict_success")
    need(outer_result["software_result"] == {"path": "software/result.json", **evidence.members["software/result.json"]},
         "outer_software_result_binding_differs")
    need(canonical(outer_plan["source"]) == canonical(outer_result["sources_after"]), "outer_sources_before_after_differ")
    sources = software_plan["source"]
    source_count = evidence.check_records("software/source/", sources)
    need(source_count == 819, "exact_executed_source_fixture_inventory_required")
    need(canonical(sources) == canonical(software_result["source_after"])
         and software_plan["captured_source_matches_preflight"] is True
         and software_result["sources_unchanged"] is True
         and software_result["captured_source_matches_preflight"] is True
         and software_result["captured_sources_unchanged"] is True, "software_source_snapshot_or_status_differs")
    source_map = {item["path"]: item for item in sources}
    for row in outer_plan["source"]:
        need(source_map.get(row["path"]) == row, "outer_source_not_bound_to_software_capture")
    github = software_plan["github"]
    need(github["GITHUB_SHA"] == HEAD and github["GITHUB_RUN_ID"] == str(RUN)
         and github["GITHUB_RUN_ATTEMPT"] == "1" and github["RUNNER_OS"] == "Linux" and github["RUNNER_ARCH"] == "X64",
         "outer_software_run_environment_binding_differs")
    current_differences = []
    for item in sources:
        try:
            actual = file_identity(ROOT / item["path"])
        except (OSError, ValueError) as error:
            actual = {"error": type(error).__name__}
        if actual != {key: item[key] for key in ("bytes", "sha256")}:
            current_differences.append({"path": item["path"], "actual": actual})
    core_plan = evidence.json("software/core/plan.json")
    core_result = evidence.json("software/core/result.json")
    need(core_result["status"] == "passed" and core_result["post_test_integrity"]["unchanged"] is True
         and core_result["final_integrity"]["unchanged"] is True, "core_outcome_or_integrity_not_passed")
    captured_count = evidence.check_records("software/core/", core_plan["captured_inventory"])
    need(captured_count == len(core_plan["original_inventory"]) == 335,
         "exact_core_source_fixture_inventory_required")
    for item in core_plan["original_inventory"]:
        need(source_map.get(item["path"]) == item, "core_original_inventory_not_bound_to_outer_source")
    seal = evidence.json("software/core/plan-seal.json")
    need(seal["plan"] == {"path": "plan.json", **evidence.members["software/core/plan.json"]}, "core_plan_seal_differs")
    tests = evidence.json("software/core/commands/existing-core-tests/stdout.bin")
    need(tests == core_result["tests"] and tests["tests_run"] == 167 and tests["successful"] is True
         and tests["errors"] == tests["failures"] == tests["skipped"] == 0, "actual_core_tests_not_all_passed")
    # Current trusted verification/checking sources must equal executed captures.
    trusted_names = ("__init__", "direct_goal_pruned_v2", "refinement_oracle", "oracle", "manifest", "refinement", "benchmark", "shared_lifting_comparison_v3", "direct_comparison_v2", "benchmark_resources_v1")
    for name in trusted_names:
        path = "src/interoperability/" + name + ".py"
        need(file_identity(ROOT / path) == {key: source_map[path][key] for key in ("bytes", "sha256")},
             "trusted_current_checker_or_verifier_source_differs:" + path)
    sys.path.insert(0, str(ROOT / "src"))
    from interoperability import shared_lifting_comparison_v3 as trusted
    from interoperability import direct_goal_pruned_v2 as checker
    from interoperability import refinement_oracle as reference_checker
    budgets = []
    reference_checks, solver_checks, checker_output_comparisons = 0, 0, 0
    for budget in (32, 256, 4096, 100000):
        start = time.monotonic()
        prefix = "software/core/budget-" + str(budget) + "/"
        bundle = evidence.base / "extracted" / prefix
        verified = trusted.verify(bundle)
        need(verified["status"] == verified["benchmark_status"] == "passed", "trusted_bundle_verification_failed")
        actual = evidence.rows(prefix + "results.jsonl")
        previous = evidence.rows("software/core/reference/budget-" + str(budget) + "/results.jsonl")
        need(set(actual) == set(previous) == {case["id"] for case in core_plan["cases"]}, "full_core_case_membership_differs")
        coverage = {method: Counter() for method in METHODS}
        comparisons, reference_comparisons, certificate_comparisons = 0, 0, 0
        checks_here, reference_here = 0, 0
        for case in core_plan["cases"]:
            row, old = actual[case["id"]], previous[case["id"]]
            for key in ("family", "evaluation_clock", "model_sha256", "input_schema", "reference_valid"):
                need(canonical(row.get(key)) == canonical(old.get(key)), "case_common_field_deterministic_difference")
            need(deterministic(row["reference"]) == deterministic(old["reference"]), "reference_deterministic_difference")
            reference_comparisons += 1
            model = evidence.json(prefix + row["input_snapshot"])
            reference = row["reference"]["result"]
            if reference["decision"] != "unknown":
                need(reference_checker.check_certificate(model, reference, row["evaluation_clock"]) is True,
                     "reference_certificate_recheck_failed")
                reference_here += 1
            else:
                need(reference.get("certificate") is None, "unknown_reference_has_certificate")
            need(set(row["algorithms"]) == set(METHODS), "actual_method_membership_differs")
            for method in METHODS:
                arm, historical = row["algorithms"][method], old["algorithms"][method]
                need(deterministic(arm["execution"]) == deterministic(historical["execution"]), "solver_deterministic_difference")
                comparisons += 1
                for key in ("status", "valid_result", "certificate_valid", "decision_agreement"):
                    need(canonical(arm.get(key)) == canonical(historical.get(key)), "deterministic_arm_flag_difference")
                need(("certificate_check" in arm) == ("certificate_check" in historical), "checker_membership_difference")
                result = arm["execution"]["result"]
                coverage[method][result["decision"]] += 1
                if "certificate_check" in arm:
                    need(deterministic(arm["certificate_check"]) == deterministic(historical["certificate_check"]), "checker_deterministic_difference")
                    certificate_comparisons += 1
                if result["decision"] == "unknown":
                    need(result.get("certificate") is None and arm["certificate_valid"] is None,
                         "unknown_solver_certificate_or_validity_not_missing")
                else:
                    need(arm["certificate_valid"] is True and checker.check_certificate(model, result, row["evaluation_clock"]) is True,
                         "solver_certificate_independent_recheck_failed")
                    coverage[method]["certified"] += 1
                    checks_here += 1
        retained_budget = next(row for row in core_result["budgets"] if row["budget"] == budget)
        need(canonical({method: dict(counts) for method, counts in coverage.items()}) == canonical(retained_budget["coverage"]),
             "retained_core_coverage_differs_from_raw_census")
        need(retained_budget["deterministic_unchanged"] is True and not retained_budget["differences"], "retained_core_reconciliation_not_passed")
        reference_checks += reference_here
        solver_checks += checks_here
        checker_output_comparisons += certificate_comparisons
        budgets.append({"budget": budget, "cases": len(actual), "algorithm_comparisons": comparisons,
            "reference_comparisons": reference_comparisons, "checker_output_comparisons": certificate_comparisons,
            "solver_certificates_independently_rechecked": checks_here,
            "reference_certificates_independently_rechecked": reference_here,
            "coverage": {method: dict(counts) for method, counts in coverage.items()},
            "trusted_verification": verified, "read_check_elapsed_seconds": round(time.monotonic() - start, 6)})
    need(sum(row["algorithm_comparisons"] for row in budgets) == core_result["algorithm_comparisons"] == 1056
         and sum(row["trusted_verification"]["worker_jobs_bound"] for row in budgets) == core_result["worker_jobs_bound"] == 2003
         and solver_checks == core_result["certificate_jobs_bound"] == 683
         and reference_checks == 172 and checker_output_comparisons == 683,
         "core_aggregate_counts_differ")
    component = json.loads(component_path.read_bytes())
    # Component reviewer owns independent demo/outer-group/test/bank reconstruction.
    need(component["schema_version"] == "research-v1-release-independent-component-review/1"
         and component["status"] == "verified" and component["run_id"] == RUN
         and component["run_attempt"] == 1 and component["head_sha"] == HEAD
         and not component.get("material_consistency_questions", []),
         "component_review_identity_or_consistency_differs")
    failed = json.loads((ROOT / "runs/v1-release-software/v1-failure-43076696650-1/retention.json").read_bytes())
    need(failed["run_id"] == 43076696650 and failed["software_acceptance_credit"] == 0
         and failed["status"] == "failed_before_source_capture_tests_or_demo", "first_failure_credit_changed")
    return {
        "schema_version": "research-v1-release-V2-independent-raw-review/1",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "current_V1_software_Linux_qualification_verified",
        "run_id": RUN, "head_sha": HEAD, "archive_identity": {"bytes": 16754100, "sha256": ARCHIVE_SHA},
        "archive_API_digest_and_all_members_verified": True, "archive_members": len(evidence.members),
        "expanded_bytes": evidence.expanded_bytes, "nested_retained_manifests": manifest_reviews,
        "executed_software_source_fixture_inputs": source_count, "core_captured_inputs": captured_count,
        "current_checkout_source_differences": current_differences, "current_verifier_checker_sources_match_execution": True,
        "actual_core_tests": tests, "budget_reconciliation": budgets,
        "algorithm_comparisons": 1056, "reference_comparisons": sum(row["reference_comparisons"] for row in budgets),
        "checker_output_comparisons": checker_output_comparisons,
        "solver_certificate_rechecks": solver_checks, "reference_certificate_rechecks": reference_checks,
        "new_certificate_checker_calls_by_reviewer": solver_checks + reference_checks,
        "fresh_solver_execution_by_reviewer": False,
        "original_application_or_SDK_execution_by_reviewer": False, "provider_requests_by_reviewer": 0,
        "downloaded_code_execution_by_reviewer": False, "Git_actions_by_reviewer": 0,
        "component_review_identity": record(component_path), "component_review": component,
        "historical_failed_first_attempt": record(ROOT / "runs/v1-release-software/v1-failure-43076696650-1/retention.json"),
        "historical_failed_first_attempt_credit": 0, "material_consistency_questions": [],
        "eighth_release_software_criterion": "accepted_for_current_development_software_scope",
        "whole_original_study_complete": False, "publication_ready": False, "human_gold_or_scientific_review": False,
        "scope_limit": "Current fresh Linux software/source/fixture qualification with retained full finite core comparison, demo/replay and candidate-bank structure. It does not complete the original research study, qualify human gold/holdout, authenticate full runtime/capture, establish novelty or grade application utility.",
        "observations": ["Child GitHub environment fields are null by the owned coordinator's sanitized environment; software outer plan supplies exact hosted run/head/Linux binding.",
                         "Captured source list contains the actual 819 files at the executed head; later added local files outside that inventory are not retroactively claimed as executed.",
                         "Earlier failed first attempt remains failed with zero credit; timeout-test failures are intentional constructed ownership controls, separate from actual successful matrix workers."],
        "validated_input_identities": evidence.bindings, "review_source": record(Path(__file__)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained", type=Path, required=True)
    parser.add_argument("--component-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to(ROOT / "runs") and not output.exists(), "fresh_workspace_audit_directory_required")
    output.mkdir(parents=True)
    try:
        report = audit(args.retained, args.component_review.resolve())
    except Exception as error:
        write(output / "review.json", {
            "schema_version": "research-v1-release-V2-independent-raw-review/1",
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "failed_independent_raw_review", "run_id": RUN, "head_sha": HEAD,
            "error": {"type": type(error).__name__, "message": str(error)},
            "eighth_release_software_criterion": "not_accepted",
            "review_source": record(Path(__file__)),
        })
        raise
    write(output / "review.json", report)
    print(json.dumps({"status": report["status"], "archive_members": report["archive_members"],
        "source_fixture_inputs": report["executed_software_source_fixture_inputs"],
        "solver_certificate_rechecks": report["solver_certificate_rechecks"],
        "reference_certificate_rechecks": report["reference_certificate_rechecks"],
        "current_source_differences": len(report["current_checkout_source_differences"])}))


if __name__ == "__main__":
    main()
