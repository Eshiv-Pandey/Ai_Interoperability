"""Recompute final five-arm CSV cells directly from retained evidence."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent / "v2-20261110-3"
SOURCE = ROOT / "runs/shared-lifting-scaling/v3-20261110-1"
GUARD = ROOT / "runs/guard-pruned-comparison/download-42836579527"
read_csv = lambda path: list(csv.DictReader(path.open(encoding="utf-8", newline="")))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
result = json.loads((BASE / "result.json").read_bytes())
assert result["status"] == "verified"
for record in result["input_files"]:
    assert sha(ROOT / record["path"]) == record["sha256"]
for record in result["outputs"]:
    path = BASE / record["path"]
    assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"]
cells = read_csv(BASE / "case-methods.csv")
old = read_csv(ROOT / "runs/research-analysis/v1-20261110-3/case-methods.csv")
assert len(cells) == 1320 and cells[:1056] == old and len(old) == 1056
keys = {(row["budget"], row["case_id"], row["method"]) for row in cells}
assert len(keys) == 1320
guards = {(int(row["budget"]), row["case_id"]): row for row in cells if row["method"] == "guard_pruned"}
joins = {(int(row["budget"]), row["case_id"]): row for row in read_csv(BASE / "join-ledger.csv")}
assert len(guards) == len(joins) == 264
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
for budget in (32, 256, 4096, 100000):
    original = [json.loads(line) for line in (SOURCE / f"budget-{budget}/results.jsonl").read_bytes().splitlines()]
    supplemental = [json.loads(line) for line in (GUARD / f"budget-{budget}/results.jsonl").read_bytes().splitlines()]
    assert len(original) == len(supplemental) == 66
    for previous, current in zip(original, supplemental):
        key = budget, current["case_id"]
        for name in ("case_id", "family", "model_sha256", "evaluation_clock", "input_schema"):
            assert previous[name] == current[name]
        p0 = SOURCE / f"budget-{budget}" / previous["input_snapshot"]
        p1 = GUARD / f"budget-{budget}" / current["input_snapshot"]
        before, after = json.loads(p0.read_bytes()), json.loads(p1.read_bytes())
        assert before == after and before["model"]["horizon"] == after["model"]["horizon"]
        join = joins[key]
        assert join["model_sha256"] == current["model_sha256"] and join["evaluation_clock"] == "100"
        assert join["horizon"] == str(after["model"]["horizon"])
        assert join["original_captured_input_sha256"] == sha(p0) and join["supplement_captured_input_sha256"] == sha(p1)
        entry = current["algorithms"]["guard_pruned"]
        response = entry["execution"]["result"]
        cell = guards[key]
        assert cell["decision"] == response["decision"]
        assert cell["model_sha256"] == current["model_sha256"] and cell["family"] == current["family"]
        assert cell["solver_work_units"] == str(response["stats"]["work_units"])
        if response["decision"] == "unknown":
            assert cell["certified"] == "0" and cell["certificate_bytes"] == "" and response["certificate"] is None
        else:
            assert cell["certified"] == "1" and entry["certificate_valid"] is True
            assert cell["certificate_bytes"] == str(len(canonical(response["certificate"])))
totals = read_csv(BASE / "budget-methods.csv")
for total in totals:
    subset = [row for row in cells if row["budget"] == total["budget"] and row["method"] == total["method"]]
    decisions = Counter(row["decision"] for row in subset)
    assert len(subset) == int(total["profiles"]) == 66
    assert sum(int(row["certified"]) for row in subset) == int(total["certified"])
    for name in ("supported", "unsupported", "unknown", "execution_error"):
        assert decisions[name] == int(total[name])
    assert sum(int(row["solver_work_units"]) for row in subset if row["solver_work_units"] != "") == int(total["solver_work_units"])
    assert sum(int(row["certificate_bytes"]) for row in subset if row["certificate_bytes"] != "") == int(total["certificate_bytes"])
assert read_csv(BASE / "paired-certification-original.csv") == read_csv(ROOT / "runs/research-analysis/v1-20261110-3/paired-certification.csv")
paired = read_csv(BASE / "paired-comparisons.csv")
for row in paired:
    paired_cells = defaultdict(dict)
    for cell in cells:
        if cell["budget"] == row["budget"]:
            paired_cells[cell["case_id"]][cell["method"]] = int(cell["certified"])
    left, right = row["left_method"], row["right_method"]
    values = list(paired_cells.values())
    assert sum(item[left] and item[right] for item in values) == int(row["both_certified"])
    assert sum(item[left] and not item[right] for item in values) == int(row["left_only"])
    assert sum(item[right] and not item[left] for item in values) == int(row["right_only"])
    assert sum(item[left] - item[right] for item in values) / 66 == float(row["paired_coverage_difference"])
    if left == "guard_pruned" and right == "direct_pruned":
        assert row["left_only"] == "0"
assert (BASE / "development-comparison-five-arm.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
assert (BASE / "development-comparison-five-arm.pdf").read_bytes().startswith(b"%PDF-")
assert b"<svg " in (BASE / "development-comparison-five-arm.svg").read_bytes()[:1000]
audit = {"schema_version": "five-arm-development-read-audit/2", "status": "all_retained_cells_and_joins_verified",
         "original_cells_exactly_match_v1_saved_CSV": 1056, "supplemental_guard_cells_independently_recomputed": 264,
         "total_cells": 1320, "exact_profile_clock_joins": 264, "unknown_proof_metrics_blank": True,
         "unknown_cells": sum(row["decision"] == "unknown" for row in cells),
         "original_shared_direct_family_resampling_table_exactly_preserved": True,
         "guard_adds_certified_cases_over_goal_pruned_direct": False,
         "figure_format_headers_checked": ["PNG", "SVG", "PDF"],
         "new_solver_checker_application_or_model_requests": 0,
         "independent_human_review": False, "evaluator_independent_authorship": False,
         "scope": "Fresh read audit; AI-authored related development profiles, method-specific work, exploratory family ranges"}
with (BASE.parent / "v2-20261110-3-independent-review.json").open("x", encoding="utf-8") as stream:
    json.dump(audit, stream, indent=2)
print(json.dumps(audit, indent=2))
