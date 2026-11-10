"""Read-only manuscript audit against retained raw results; runs no experiments."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import traceback
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "runs/research-analysis/v2-20261110-3"
RAW = ROOT / "runs/shared-lifting-scaling/v3-20261110-1"
SUPPLEMENT = ROOT / "runs/guard-pruned-comparison/download-42836579527"
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift", "guard_pruned")
LABELS = ("Legacy direct", "Goal-pruned direct", "Original refinement", "Shared lifting", "Constraint-pruned direct")
BUDGETS = (32, 256, 4096, 100000)


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_bytes())


def record(path):
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def tables(text):
    result, current = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            current.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif current:
            result.append(current)
            current = []
    return result


def find(items, header):
    found = [item for item in items if item[0] == header]
    require(len(found) == 1, "Missing/duplicate empirical table: " + str(header))
    return found[0][2:]


def audit():
    draft_path = ROOT / "paper/working-draft-v5.md"
    guide_path = ROOT / "docs/research/paper-artifact-guide-v5.md"
    draft = draft_path.read_text(encoding="utf-8")
    old = (ROOT / "paper/working-draft-v4.md").read_text(encoding="utf-8")
    ledger = load(ROOT / "paper/claim-ledger-v5.json")
    status = load(ROOT / "paper/draft-status-v5.json")
    require(draft.splitlines()[0] == old.splitlines()[0], "Registered title changed")
    require(len(draft.split()) > 6000 and "## 12. Conclusion" in draft, "Incomplete manuscript")
    require(ledger["draft"] == record(draft_path) and ledger["artifact_guide"] == record(guide_path), "Draft/guide binding")
    require(status["full_manuscript_drafted"] and not status["publication_ready"]
            and not status["original_research_validity_gates_complete"]
            and not status["human_scientific_review_claimed"], "Scientific completion overstated")
    require(not ledger["human_scientific_review_claimed"], "AI review labelled human")
    spec = importlib.util.spec_from_file_location("builder_v5", ROOT / "paper/build_draft_v5.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    require(builder.build() == draft, "Draft differs from reproducible preserved-v4 transformation")
    evidence = {}
    for claim in ledger["claims"]:
        require(claim["limits"] and claim["evidence"], "Unbounded/unbound claim")
        for item in claim["evidence"]:
            path = (ROOT / item["path"]).resolve()
            require(path.is_relative_to(ROOT) and record(path) == item, "Changed claim evidence: " + item["path"])
            evidence[item["path"]] = item
    for claim in load(ROOT / "paper/claim-ledger-v4.json")["claims"]:
        for item in claim["evidence"]:
            path = (ROOT / item["path"]).resolve()
            require(path.is_relative_to(ROOT) and record(path) == item, "Changed inherited v4 evidence: " + item["path"])
            evidence[item["path"]] = item
    links = 0
    for source, text in ((draft_path, draft), (guide_path, guide_path.read_text(encoding="utf-8"))):
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            url = urlparse(target)
            if url.scheme:
                require(url.scheme in ("https", "http") and url.netloc, "Malformed external link")
            else:
                path = (source.parent / unquote(url.path)).resolve()
                require(path.is_relative_to(ROOT) and path.exists(), "Broken local link: " + target)
            links += 1
    refs = load(ROOT / "paper/references-v3.json")["entries"]
    require([r["number"] for r in refs] == list(range(1, 23)), "Reference numbering")
    require(set(map(int, re.findall(r"\[(\d+)\](?!\()", draft))) == set(range(1, 23)), "Citation coverage")
    bib_lines = [l for l in (ROOT / "paper/references-v3.md").read_text(encoding="utf-8").splitlines() if re.match(r"^\d+\. ", l)]
    require([l for l in draft.splitlines() if re.match(r"^\d+\. ", l)] == bib_lines, "Bibliography text differs")
    require(load(ROOT / "paper/bibliography-audit-v3-2.json")["status"] == "passed", "Primary metadata audit missing")
    for ref in refs:
        require(all(ref["fields"].get(k) for k in ("title", "year", "author", "url")), "Incomplete reference")
        for item in ref["evidence"]:
            require((ROOT / item["path"]).is_file(), "Missing primary provenance")

    cells = rows(ANALYSIS / "case-methods.csv")
    require(len(cells) == 1320, "Combined cell count")
    index = {(int(r["budget"]), r["method"], r["case_id"]): r for r in cells}
    require(len(index) == 1320, "Duplicate combined cells")
    aggregates, unknown, certified = {}, 0, 0
    largest = Counter()
    for budget in BUDGETS:
        original = [json.loads(l) for l in (RAW / f"budget-{budget}/results.jsonl").read_text(encoding="utf-8").splitlines()]
        supplement = [json.loads(l) for l in (SUPPLEMENT / f"budget-{budget}/results.jsonl").read_text(encoding="utf-8").splitlines()]
        require(len(original) == len(supplement) == 66, "Raw denominator")
        oi = {r["case_id"]: r for r in original}
        si = {r["case_id"]: r for r in supplement}
        require(set(oi) == set(si) and len(oi) == 66, "Supplement case membership")
        for cid in oi:
            require(all(oi[cid][k] == si[cid][k] for k in ("family", "model_sha256", "input_schema", "evaluation_clock")), "Profile join identity")
            for arm in ARMS:
                raw = (si[cid] if arm == "guard_pruned" else oi[cid])["algorithms"][arm]
                execution = raw["execution"]
                value = execution["result"]
                csv_cell = index[budget, arm, cid]
                require(execution["status"] == "returned" and execution["process"]["returncode"] == 0
                        and not execution["process"]["timed_out"] and raw["valid_result"], "Invalid raw execution")
                is_certified = value["decision"] in ("supported", "unsupported") and raw["certificate_valid"] is True
                size = len(canonical(value["certificate"])) if is_certified else 0
                require(csv_cell["decision"] == value["decision"] and int(csv_cell["certified"]) == int(is_certified)
                        and int(csv_cell["solver_work_units"]) == value["stats"]["work_units"]
                        and csv_cell["model_sha256"] == oi[cid]["model_sha256"], "CSV/raw cell mismatch")
                require(csv_cell["certificate_bytes"] == (str(size) if is_certified else ""), "Proof size/missingness")
                if is_certified:
                    require(raw["certificate_check"]["result"] is True, "Unaccepted certificate counted")
                else:
                    require(value["decision"] == "unknown" and value["certificate"] is None, "Uncertified output not unknown")
                totals = aggregates.setdefault((budget, arm), Counter())
                totals.update({"profiles": 1, "certified": int(is_certified), value["decision"]: 1,
                               "solver_work_units": value["stats"]["work_units"], "certificate_bytes": size})
                if budget == 100000:
                    largest[arm] = max(largest[arm], size)
                unknown += value["decision"] == "unknown"
                certified += is_certified
    require(unknown == 461 and certified == 859, "Unknown/certified denominators")
    for row in rows(ANALYSIS / "budget-methods.csv"):
        counter = aggregates[int(row["budget"]), row["method"]]
        require(all(int(row[key]) == counter[key] for key in ("profiles", "certified", "supported", "unsupported", "unknown", "solver_work_units", "certificate_bytes")), "Aggregate/raw mismatch")
    manuscript_tables = tables(draft)
    coverage = find(manuscript_tables, ["Work allowance", *LABELS])
    require(coverage == [[format(b, ","), *[str(aggregates[b, a]["certified"]) + "/66" for a in ARMS]] for b in BUDGETS], "Table1/raw mismatch")
    work_table = find(manuscript_tables, ["Method", "Solver work units", "Total canonical certificate bytes", "Largest certificate bytes"])
    require(work_table == [[label, format(aggregates[100000, arm]["solver_work_units"], ","), format(aggregates[100000, arm]["certificate_bytes"], ","), format(largest[arm], ",")] for arm, label in zip(ARMS, LABELS)], "Table3/raw mismatch")
    old_tables = tables(old)
    for header in (["Allowance", "Both", "Direct only", "Shared only", "Neither", "Paired difference", "Family-resampling range"],
                   ["Inner-graph decision", "Full-recipe direct decision", "Profiles"], ["Observation", "Native N11", "Admitted B7"]):
        require(find(manuscript_tables, header) == find(old_tables, header), "Preserved empirical table changed")
    joins = rows(ANALYSIS / "join-ledger.csv")
    require(len(joins) == 264 and all(r["parsed_profile_equal"] == r["fresh_baseline_deterministic_result_equal"] == "True"
            and r["original_captured_input_sha256"] == r["supplement_captured_input_sha256"] for r in joins), "Exact join ledger")
    ap2 = load(ROOT / "runs/ap2-reference-development/v3/semantic-analysis-42845852651/result.json")
    require(ap2["status"] == "offline_original_application_semantics_verified" and ap2["receipt"]["status"] == "Success"
            and ap2["same_original_merchant_and_processor_tasks_resumed"] and ap2["cleanup_verified"]
            and ap2["receipt_reference_freshly_recomputed"] and ap2["provider_requests"] == 0
            and not ap2["native_qualification_established"], "AP2 receipt/scope")
    require([ap2[k] for k in ("original_source_files_checked", "durable_events_checked", "raw_exchanges_checked", "rpc_requests_checked")] == [136, 168, 17, 12], "AP2 counts")
    capture = load(ROOT / "runs/guard-pruned-comparison/independent-capture-audit-42836579527.json")
    challenge = load(ROOT / "runs/guard-pruned-review/v3-20261110-2/result.json")
    require(capture["status"] == challenge["status"] == "passed"
            and capture["worker_jobs_bound"] == 1140 and capture["fresh_exhaustive_certificate_checks"] == 348
            and capture["manifest_files_verified"] == 6228, "Comparator audit counts")
    require(challenge["focused_tests"]["count"] == 13
            and challenge["independent_domain_pruning_challenge"]["cases"] == 200
            and challenge["independent_domain_pruning_challenge"]["original_complete_tuples"] == 4688
            and challenge["independent_domain_pruning_challenge"]["removed_tuples_proven_definitely_false"] == 3281, "Challenge counts")
    manifest = load(ANALYSIS / "result.json")
    for item in manifest["outputs"]:
        data = (ANALYSIS / item["path"]).read_bytes()
        require(len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"], "Figure/table binding")
    return {"status": "passed", "draft": record(draft_path), "ledger": record(ROOT / "paper/claim-ledger-v5.json"),
            "guide": record(guide_path), "audit_source": record(Path(__file__)), "draft_words": len(draft.split()),
            "raw_cells_reconstructed": 1320, "unknown_cells": unknown, "accepted_certificate_records": certified,
            "empirical_tables_checked": 5, "exact_joins_checked": 264, "references_checked": 22,
            "links_checked": links, "evidence_files_hashed": len(evidence), "preserved_v4_transformation_verified": True,
            "scope": "Read-only numeric, citation, transformation and binding audit; no new visual render, mechanized proof or human review."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "paper") and not output.exists(), "Choose unused paper audit receipt")
    report = {"status": "failed", "schema_version": "working-paper-value-audit/5", "started_utc": datetime.now(timezone.utc).isoformat(),
              "new_solver_checker_application_or_model_calls": 0, "human_review": False}
    try:
        report.update(audit())
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "error": report.get("error"), "output": str(output)}))
    raise SystemExit(0 if report["status"] == "passed" else 1)
