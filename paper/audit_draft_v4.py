"""Read-only paper/source value audit; never invokes solvers, SDKs or models."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import traceback
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "runs/research-analysis/v1-20261110-3"
RAW = ROOT / "runs/shared-lifting-scaling/v3-20261110-1"
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift")
LABELS = ("Legacy direct", "Goal-pruned direct", "Original refinement", "Shared lifting")
BUDGETS = (32, 256, 4096, 100000)


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_bytes())


def record(path, base=ROOT):
    value = path.read_bytes()
    return {"path": path.relative_to(base).as_posix(), "bytes": len(value),
            "sha256": hashlib.sha256(value).hexdigest()}


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def tables(text):
    result, current = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            current.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif current:
            result.append(current)
            current = []
    return result


def find_table(items, header):
    found = [item for item in items if item[0] == header]
    require(len(found) == 1, "Missing/duplicate table: " + repr(header))
    return found[0][2:]


def audit():
    draft_path = ROOT / "paper/working-draft-v4.md"
    guide_path = ROOT / "docs/research/paper-artifact-guide-v4.md"
    ledger_path = ROOT / "paper/claim-ledger-v4.json"
    draft = draft_path.read_text(encoding="utf-8")
    guide = guide_path.read_text(encoding="utf-8")
    ledger = load(ledger_path)
    status = load(ROOT / "paper/draft-status-v4.json")
    require(draft.splitlines()[0] == (ROOT / "paper/working-draft-v3.md").read_text(encoding="utf-8").splitlines()[0],
            "Registered paper title changed")
    require(len(draft.split()) >= 6000, "Full manuscript body is unexpectedly short")
    require(ledger["draft"] == record(draft_path), "Draft/ledger binding changed")
    require(ledger["artifact_guide"] == record(guide_path), "Guide/ledger binding changed")
    require(status["full_manuscript_drafted"] is True and status["publication_ready"] is False
            and status["original_research_validity_gates_complete"] is False,
            "Draft completion conflated with scientific validity")
    require(ledger["human_scientific_review_claimed"] is False
            and status["human_scientific_review_claimed"] is False, "Human review incorrectly claimed")

    evidence = {}
    for claim in ledger["claims"]:
        require(claim["kind"] in ("conditional_design", "source_bound_implementation", "observed_development",
                "observed_exploratory", "observed_stress_case", "observed_resources", "observed_reproduction",
                "observed_weaker_control", "observed_application_fixture", "not_established",
                "observed_analysis", "retained_citation_metadata", "observed_source_boundary"), "Unknown claim status")
        for item in claim["evidence"]:
            name = PurePosixPath(item["path"])
            require(not name.is_absolute() and ".." not in name.parts, "Unsafe evidence path")
            require(record(ROOT / item["path"]) == item, "Changed claim evidence: " + item["path"])
            evidence[item["path"]] = item

    links = []
    for source, text in ((draft_path, draft), (guide_path, guide)):
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            url = urlparse(target)
            if url.scheme in ("http", "https"):
                require(bool(url.netloc), "Malformed external link")
                links.append({"source": source.relative_to(ROOT).as_posix(), "target": target,
                              "kind": "external_syntax_only"})
                continue
            require(not url.scheme, "Unsupported local link scheme")
            path = (source.parent / unquote(url.path)).resolve()
            require(path.is_relative_to(ROOT) and path.exists(), "Broken/outside local link: " + target)
            links.append({"source": source.relative_to(ROOT).as_posix(), "target": target,
                          "kind": "local_exists"})

    references = load(ROOT / "paper/references-v2.json")["entries"]
    numbers = [entry["number"] for entry in references]
    keys = [entry["key"] for entry in references]
    require(numbers == list(range(1, 19)) and len(set(keys)) == 18, "Reference numbering/key mismatch")
    require(set(map(int, re.findall(r"\[(\d+)\]", draft))) == set(numbers), "Citation coverage mismatch")
    bibliography = (ROOT / "paper/references-v2.md").read_text(encoding="utf-8")
    retained_lines = [line for line in bibliography.splitlines() if re.match(r"^\d+\. ", line)]
    draft_lines = [line for line in draft.splitlines() if re.match(r"^\d+\. ", line)]
    require(draft_lines == retained_lines and len(draft_lines) == 18, "Bibliography text/version changed")
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", (ROOT / "paper/references-v2.bib").read_text(encoding="utf-8")))
    require(bib_keys == set(keys), "BibTeX/JSON key mismatch")
    reference_evidence = set()
    for entry in references:
        require(all(isinstance(entry["fields"].get(field), str) and entry["fields"][field]
                    for field in ("title", "author", "year", "url")), "Incomplete required reference metadata")
        require(urlparse(entry["fields"]["url"]).scheme in ("https", "http"), "Reference URL syntax")
        require(entry["evidence"], "Missing retained primary provenance")
        for item in entry["evidence"]:
            require((ROOT / item["path"]).is_file() and item["location"], "Broken reference provenance")
            reference_evidence.add(item["path"])
    require("pages" not in references[16]["fields"], "Unresolved DEEPSEC pagination invented")
    require(references[3]["fields"]["author"].split(" and ").count("Chen, Xi") == 2,
            "Repeated primary BRIDGE author order altered")

    case_rows = csv_rows(ANALYSIS / "case-methods.csv")
    aggregate_rows = csv_rows(ANALYSIS / "budget-methods.csv")
    family_rows = csv_rows(ANALYSIS / "family-methods.csv")
    paired_rows = csv_rows(ANALYSIS / "paired-certification.csv")
    require(len(case_rows) == 1056 and len(aggregate_rows) == 16
            and len(family_rows) == 80 and len(paired_rows) == 4, "Analysis row membership")
    index = {(int(row["budget"]), row["method"], row["case_id"]): row for row in case_rows}
    require(len(index) == 1056, "Duplicate analysis case rows")
    unknowns = certificates = 0
    actual_work, actual_proof, actual_coverage, actual_decisions, actual_wall = {}, {}, {}, {}, {}
    raw_by_budget = {}
    for budget in BUDGETS:
        raw_rows = [json.loads(line) for line in (RAW / f"budget-{budget}/results.jsonl").read_text(encoding="utf-8").splitlines()]
        require(len(raw_rows) == 66 and len({row["case_id"] for row in raw_rows}) == 66, "Raw case membership")
        raw_by_budget[budget] = {row["case_id"]: row for row in raw_rows}
        for arm in ARMS:
            work = proof = count = wall = 0
            decisions = Counter()
            for row in raw_rows:
                require(set(row["algorithms"]) == set(ARMS) and row["evaluation_clock"] == 100, "Design mismatch")
                entry = row["algorithms"][arm]
                execution = entry["execution"]
                result = execution["result"]
                decision = result["decision"]
                cert = decision in ("supported", "unsupported") and entry["certificate_valid"] is True
                csv_row = index[budget, arm, row["case_id"]]
                require(execution["status"] == "returned" and execution["process"]["returncode"] == 0
                        and execution["process"]["timed_out"] is False, "Raw execution failure")
                require(csv_row["decision"] == decision and int(csv_row["certified"]) == int(cert)
                        and int(csv_row["solver_work_units"]) == result["stats"]["work_units"], "Case value mismatch")
                size = len(canonical(result["certificate"])) if cert else None
                require(csv_row["certificate_bytes"] == (str(size) if size is not None else ""), "Proof byte mismatch")
                if cert:
                    require(entry["valid_result"] is True and entry["certificate_check"]["result"] is True,
                            "Conclusive result lacks accepted independent certificate")
                    certificates += 1
                else:
                    require(decision == "unknown" and result["certificate"] is None, "Unknown/certificate semantics")
                    unknowns += 1
                work += result["stats"]["work_units"]
                proof += size or 0
                count += int(cert)
                decisions[decision] += 1
                wall += execution["process"]["worker_wall_ns"]
                if "certificate_check" in entry:
                    wall += entry["certificate_check"]["process"]["worker_wall_ns"]
            key = budget, arm
            actual_work[key], actual_proof[key], actual_coverage[key] = work, proof, count
            actual_decisions[key], actual_wall[key] = dict(decisions), wall
    require((certificates, unknowns) == (683, 373), "Total certified/unknown counts")
    for row in aggregate_rows:
        key = int(row["budget"]), row["method"]
        require(int(row["profiles"]) == 66 and int(row["certified"]) == actual_coverage[key]
                and int(row["solver_work_units"]) == actual_work[key]
                and int(row["certificate_bytes"]) == actual_proof[key], "Aggregate/raw mismatch")
        require({name: int(row[name]) for name in ("supported", "unsupported", "unknown")}
                == {name: actual_decisions[key].get(name, 0) for name in ("supported", "unsupported", "unknown")},
                "Decision aggregate/raw mismatch")

    paper_tables = tables(draft)
    coverage = find_table(paper_tables, ["Work allowance", *LABELS])
    expected_coverage = [[f"{budget:,}", *[f"{actual_coverage[budget, arm]}/66" for arm in ARMS]] for budget in BUDGETS]
    require(coverage == expected_coverage, "Paper Table 1 mismatch")
    paired = find_table(paper_tables, ["Allowance", "Both", "Direct only", "Shared only", "Neither", "Paired difference", "Family-resampling range"])
    expected_paired = []
    for row in paired_rows:
        budget = int(row["budget"])
        counts = Counter((int(index[budget, "direct_pruned", case]["certified"]),
                          int(index[budget, "shared_lift", case]["certified"])) for case in raw_by_budget[budget])
        values = [counts[1, 1], counts[1, 0], counts[0, 1], counts[0, 0]]
        require(values == [int(row[field]) for field in ("both_certified", "direct_only", "shared_only", "neither_certified")],
                "Paired raw counts mismatch")
        require(abs(float(row["paired_coverage_difference"]) - (values[2] - values[1]) / 66) < 1e-14,
                "Paired difference mismatch")
        expected_paired.append([f"{budget:,}", *map(str, values), f"{100 * float(row['paired_coverage_difference']):.2f}",
                               f"[{100 * float(row['family_resampling_lower']):.2f}, {100 * float(row['family_resampling_upper']):.2f}]"])
    require(paired == expected_paired, "Paper Table 2 mismatch")
    work_table = find_table(paper_tables, ["Method", "Solver work units", "Total canonical certificate bytes", "Largest certificate bytes"])
    expected_work = []
    for arm, label in zip(ARMS, LABELS):
        sizes = [int(row["certificate_bytes"]) for row in case_rows
                 if row["budget"] == "100000" and row["method"] == arm and row["certificate_bytes"]]
        expected_work.append([label, f"{actual_work[100000, arm]:,}", f"{actual_proof[100000, arm]:,}", f"{max(sizes):,}"])
    require(work_table == expected_work, "Paper Table 3 mismatch")
    require([round(actual_wall[100000, arm] / 1e9, 3) for arm in ARMS] == [16.689, 16.861, 16.538, 16.896],
            "Narrative worker-wall totals mismatch")
    family_counts = {row["family"]: int(row["profiles"]) for row in family_rows
                     if row["budget"] == "100000" and row["method"] == "baseline"}
    require(family_counts == {"argument_product": 16, "layered_reconvergence": 16, "correlated_frames": 16,
                             "horizon_boundary": 6, "off_goal_load": 12}, "Family counts mismatch")
    require(all(actual_decisions[100000, arm] == {"supported": 28, "unsupported": 26, "unknown": 12}
                for arm in ARMS), "High-allowance decisions mismatch")

    stress = raw_by_budget[100000]["scale-0031"]["algorithms"]
    old, shared, direct = [stress[arm]["execution"]["result"] for arm in ("candidate", "shared_lift", "direct_pruned")]
    require((old["stats"]["relation_checks"], shared["stats"]["relation_checks"], old["stats"]["work_units"],
             shared["stats"]["work_units"], direct["stats"]["work_units"]) == (1024, 16, 5566, 14773, 134), "Stress counters mismatch")
    require((len(canonical(old["certificate"])), len(canonical(shared["certificate"])), len(canonical(direct["certificate"])))
            == (8895, 8895, 338), "Stress proof bytes mismatch")
    require(len(old["certificate"]["refuted_prefixes"]) == len(shared["certificate"]["refuted_prefixes"]) == 256,
            "Stress refutation counts")
    require(old["stats"]["abstract_paths"] == shared["stats"]["abstract_paths"] == 256
            and direct["stats"]["product_states"] == 4 and direct["stats"]["argument_assignments"] == 16, "Stress structure")
    require(all(canonical(row["algorithms"]["candidate"]["execution"]["result"]["certificate"])
                == canonical(row["algorithms"]["shared_lift"]["execution"]["result"]["certificate"])
                for row in raw_by_budget[100000].values()
                if row["algorithms"]["candidate"]["execution"]["result"]["decision"] != "unknown"),
            "High-allowance original/shared certificate identity")

    control = load(ROOT / "runs/abstraction-control/postcapture-20261110-v1/result.json")
    require(control["status"] == "passed" and control["original_terminal_status"] == "failed"
            and control["new_solver_jobs"] == control["new_certificate_jobs"] == 0, "Control audit/failed execution conflation")
    pairs = control["analysis"]["pairs_abstract_over_recipe"]
    expected_control = [[*[value.title() for value in key.split("/")], str(pairs[key])] for key in
                        ("supported/supported", "supported/unsupported", "supported/unknown", "unsupported/unsupported")]
    require(find_table(paper_tables, ["Inner-graph decision", "Full-recipe direct decision", "Profiles"]) == expected_control,
            "Paper Table 4 mismatch")
    require(control["analysis"]["cases"] == 66 and control["analysis"]["new_worker_jobs"] == 330
            and control["analysis"]["accepted_checks_including_duplicate_baseline"] == 132, "Control worker/check multiplicity")

    application = load(ROOT / "runs/ci-agentops-native/download-42808110286-independent-review.json")
    require(application["head_sha"] == "76d133f3ba251ffe37e7f932cb986af8e7830f28"
            and application["live_model_calls"] == 0 and application["native_completed_before_b7_start"], "Application identity/order")
    cases = application["cases"]
    for name in ("N11", "B7"):
        case = cases[name]
        require(case["strict_success"] and case["task_completed"] and case["final_state"] == "completed"
                and case["effect"]["final_inventory_status"] == "operational" and case["effect"]["new_audit_rows"] == 1,
                "Application task/effect claim")
        require(case["client_returncode"] == case["service_returncode"] == 0 and not case["forced_cleanup"]
                and case["cleanup_errors"] == [] and case["groups_initially_and_finally_empty"], "Application lifecycle")
    expected_application = [["Original task completed", "Yes", "Yes"],
                            ["Original inventory status became `operational`", "Yes", "Yes"],
                            ["New attributable audit rows", "1", "1"],
                            ["Captured ASGI requests", str(cases["N11"]["asgi_requests"]), str(cases["B7"]["asgi_requests"])],
                            ["Client/service exit codes", "0 / 0", "0 / 0"],
                            ["Forced cleanup or cleanup errors", "None", "None"]]
    require(find_table(paper_tables, ["Observation", "Native N11", "Admitted B7"]) == expected_application, "Paper Table 5 mismatch")
    admission = cases["B7"]["admission"]
    require(admission["decision"] == "supported" and admission["certificate_valid"]
            and admission["work_units"] == 33 and admission["budget"] == 100000
            and admission["certificate_to_origin"]["continuation_count"] == 1
            and admission["certificate_to_origin"]["service_sequence"] == 9, "Admission/actual origin claim")
    require((application["copied_files_hash_checked"], application["staged_inputs_hash_checked"], application["original_source_files"])
            == (1138, 864, 421), "Application inventories")

    core = load(ROOT / "runs/ci-research-core/download-42819352517-independent-review.json")
    require(core["status"] == "passed" and core["head_sha"] == "9ef339fa349cf73b6c3558d2c3f51dc967f89444"
            and core["algorithm_comparisons"] == 1056 and core["reference_comparisons"] == 264
            and core["checker_output_comparisons"] == 683 and core["worker_jobs_bound"] == 2003, "Core reproduction claims")
    require(core["tests"] == {"tests_run": 167, "errors": 0, "failures": 0, "skipped": 0, "successful": True}
            and core["retained_inventory"] == {"files": 10821, "bytes": 33707262}, "Core test/file claims")
    require(core["solver_certificates_independently_rechecked"] == 683
            and core["reference_certificates_independently_rechecked"] == 172, "Core independent certificate counts")
    require(core["head_sha"] in draft and application["head_sha"] in draft, "Execution commit absent/mistyped")

    bank = load(ROOT / "runs/task-bank-review/complete-68-v1.json")
    require(bank["status"] == "structurally_valid" and len(bank["domains"]) == 2, "Complete bank structural receipt")
    require({item["domain"]: item["templates"] for item in bank["domains"]} == {"agentops": 34, "ap2": 34},
            "Paper bank count mismatch")
    require(all(item["split_counts"] == {"development": 6, "calibration": 4, "held_out": 24}
                for item in bank["domains"]), "Bank split allocation mismatch")
    for item in bank["inputs"]:
        require(record(ROOT / item["path"]) == item, "Final bank bytes differ from complete receipt")
    ap2 = load(ROOT / "runs/ap2-task-qualification/v1-20261110-2/result.json")
    require(ap2["status"] == "development_source_boundary_qualification_passed" and ap2["source_cases_per_pass"] == 6
            and ap2["original_imported_invocations_total"] == 12 and len(ap2["runs"]) == 2, "AP2 source case count")
    require(ap2["provider_requests"] == 0 and ap2["full_application_qualification"] is False
            and ap2["human_review"] is False and ap2["independent_holdout"] is False, "AP2 scope conflation")
    for run in ap2["runs"]:
        require(run["grade"]["passed"] == run["grade"]["total"] == 6
                and run["imported_environment_files_verified"] == 540
                and run["private_evaluator_read_probe_blocked"] is True, "AP2 pass/module/probe claim")
        require(len({item["id"] for item in run["grade"]["cases"]}) == 6
                and all(item["source_boundary_passed"] for item in run["grade"]["cases"]), "AP2 case verdicts")
    require(ap2["adversarial_controls"]["all_rejected"] and ap2["adversarial_controls"]["missing_case_rejected"]
            and len(ap2["adversarial_controls"]["mutated_outputs"]) == 6, "AP2 near-miss controls")

    analysis_result = load(ANALYSIS / "result.json")
    for item in analysis_result["outputs"]:
        require(record(ANALYSIS / item["path"], ANALYSIS) == item, "Analysis output changed")
    for item in analysis_result["input_files"]:
        require(record(ROOT / item["path"])["sha256"] == item["sha256"], "Analysis input changed")
    require(len(analysis_result["outputs"]) == 7 and len(analysis_result["input_files"]) == 17, "Analysis binding count")
    for name, item in evidence.items():
        require(record(ROOT / name) == item, "Evidence changed during audit")
    return {"draft_words": len(draft.split()), "claim_count": len(ledger["claims"]), "empirical_tables_checked": 5,
            "raw_algorithm_cells_reconstructed": 1056, "accepted_algorithm_certificates": certificates,
            "unknown_proof_sizes_correctly_missing": unknowns, "local_and_external_links": links,
            "reference_entries": 18, "retained_reference_provenance_files": sorted(reference_evidence),
            "reference_online_refresh_performed": False, "figure_output_bindings_checked": 7,
            "analysis_input_bindings_checked": 17, "claim_evidence_files_hashed": len(evidence),
            "draft_binding": record(draft_path), "ledger_binding": record(ledger_path),
            "guide_binding": record(guide_path), "audit_source": record(Path(__file__)),
            "scope": "Reconstructed document values, byte bindings, citation structure and local links. No solver/checker/application/model execution, no new visual render, no mechanized proof or human review."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "paper") and not output.exists(), "Choose an unused paper audit allocation")
    report = {"schema_version": "working-paper-value-audit/4", "status": "failed",
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "new_solver_or_certificate_jobs": 0,
              "new_model_or_application_calls": 0, "human_review": False}
    try:
        report.update(audit())
        report["status"] = "passed"
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        report["traceback"] = traceback.format_exc()
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "error": report.get("error"),
                      "draft_words": report.get("draft_words"), "output": str(output)}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
