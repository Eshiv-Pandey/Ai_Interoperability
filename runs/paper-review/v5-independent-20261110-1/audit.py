"""Fresh independent raw-reading paper review; no solver, checker or SDK imports."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
BUDGETS = (32, 256, 4096, 100000)
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift", "guard_pruned")
LABELS = ("Legacy direct", "Goal-pruned direct", "Original refinement", "Shared lifting", "Constraint-pruned direct")


def load(path):
    return json.loads(path.read_bytes())


def canonical(item):
    return json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def require(value, label):
    if not value:
        raise ValueError(label)


def table(text, header):
    lines = text.splitlines()
    first = next(i for i, line in enumerate(lines) if line == header)
    result = []
    for line in lines[first + 2:]:
        if not line.startswith("|"):
            break
        result.append([v.strip() for v in line.strip().strip("|").split("|")])
    return result


draft = (ROOT / "paper/working-draft-v5.md").read_text(encoding="utf-8")
draft_sha = hashlib.sha256(draft.encode()).hexdigest()
totals, sizes, certified_sets, pairs, raw_cells = {}, {}, {}, {}, 0
unknowns = 0
for allowance in BUDGETS:
    original = [json.loads(line) for line in (ROOT / f"runs/shared-lifting-scaling/v3-20261110-1/budget-{allowance}/results.jsonl").read_text().splitlines()]
    extra = [json.loads(line) for line in (ROOT / f"runs/guard-pruned-comparison/download-42836579527/budget-{allowance}/results.jsonl").read_text().splitlines()]
    old, new = {r["case_id"]: r for r in original}, {r["case_id"]: r for r in extra}
    require(set(old) == set(new) and len(old) == 66, "exact case membership")
    for arm in ARMS:
        totals[allowance, arm] = Counter()
        sizes[allowance, arm] = []
        certified_sets[allowance, arm] = set()
    for case_id, original_row in old.items():
        added = new[case_id]
        require(all(original_row[k] == added[k] for k in ("family", "model_sha256", "input_schema", "evaluation_clock")), "same supplied-profile identity")
        results = {}
        for arm in ARMS:
            row = (added if arm == "guard_pruned" else original_row)["algorithms"][arm]
            execution = row["execution"]
            result = execution["result"]
            require(row["valid_result"] and execution["status"] == "returned"
                    and execution["process"]["returncode"] == 0 and not execution["process"]["timed_out"], "raw return validity")
            accepted = result["decision"] in {"supported", "unsupported"} and row["certificate_valid"] is True
            if accepted:
                require(row["certificate_check"]["result"] is True, "certificate acceptance")
                certified_sets[allowance, arm].add(case_id)
                proof = len(canonical(result["certificate"]))
                sizes[allowance, arm].append(proof)
            else:
                require(result["decision"] == "unknown" and result["certificate"] is None, "unknown proof missing")
                unknowns += 1
                proof = 0
            totals[allowance, arm].update({"certified": int(accepted), result["decision"]: 1,
                                         "work": result["stats"]["work_units"], "proof": proof})
            results[arm] = result
            raw_cells += 1
        if allowance == 100000 and case_id in certified_sets[allowance, "shared_lift"]:
            require(canonical(results["candidate"]["certificate"]) == canonical(results["shared_lift"]["certificate"]), "unchanged refinement proof bytes")
    shared, direct, guard = (certified_sets[allowance, arm] for arm in ("shared_lift", "direct_pruned", "guard_pruned"))
    require(not shared - direct and not guard - direct, "no added certified case beyond strongest direct")
    pairs[allowance] = [len(shared & direct), len(direct - shared), len(shared - direct), 66 - len(shared | direct)]
    if allowance == 100000:
        require(all(certified_sets[allowance, arm] == direct for arm in ARMS), "same54profiles not merely same count")
    require(all(totals[allowance, arm]["supported"] + totals[allowance, arm]["unsupported"] + totals[allowance, arm]["unknown"] == 66 for arm in ARMS), "unknown denominator retained")
require(raw_cells == 1320 and unknowns == 461, "full combined matrix count")
require(table(draft, "| Work allowance | " + " | ".join(LABELS) + " |") == [
    [f"{allowance:,}", *[f'{totals[allowance, arm]["certified"]}/66' for arm in ARMS]] for allowance in BUDGETS], "Table1 raw reconstruction")
require(table(draft, "| Method | Solver work units | Total canonical certificate bytes | Largest certificate bytes |") == [
    [label, f'{totals[100000, arm]["work"]:,}', f'{totals[100000, arm]["proof"]:,}', f'{max(sizes[100000, arm]):,}']
    for label, arm in zip(LABELS, ARMS)], "Table3 raw reconstruction")
pair_table = table(draft, "| Allowance | Both | Direct only | Shared only | Neither | Paired difference | Family-resampling range |")
require([r[:6] for r in pair_table] == [[f"{allowance:,}", *map(str, pairs[allowance]), f'{100*(pairs[allowance][2]-pairs[allowance][1])/66:.2f}'] for allowance in BUDGETS], "Table2 counts and percentage from raw")
stress = next(r for r in original if r["case_id"] == "scale-0031")
candidate, shared, direct = [stress["algorithms"][arm]["execution"]["result"] for arm in ("candidate", "shared_lift", "direct_pruned")]
require([candidate["stats"]["relation_checks"], shared["stats"]["relation_checks"], candidate["stats"]["work_units"], shared["stats"]["work_units"], len(canonical(candidate["certificate"])), len(canonical(shared["certificate"]))] == [1024, 16, 5566, 14773, 8895, 8895], "stress relation/work/proof numbers")
require([direct["stats"]["product_states"], direct["stats"]["argument_assignments"], direct["stats"]["work_units"], len(canonical(direct["certificate"]))] == [4, 16, 134, 338], "strong direct stress numbers")
control = load(ROOT / "runs/abstraction-control/postcapture-20261110-v1/result.json")["analysis"]["pairs_abstract_over_recipe"]
require(table(draft, "| Inner-graph decision | Full-recipe direct decision | Profiles |") == [
    ["Supported", "Supported", str(control["supported/supported"])],
    ["Supported", "Unsupported", str(control["supported/unsupported"])],
    ["Supported", "Unknown", str(control["supported/unknown"])],
    ["Unsupported", "Unsupported", str(control["unsupported/unsupported"])]], "Table4 matches preserved postcapture audit")
native = load(ROOT / "runs/ci-agentops-native/download-42808110286-independent-review.json")
require(native["status"] == "strict_success_verified", "native retained audit status")
for arm in ("N11", "B7"):
    case = native["cases"][arm]
    require(case["task_completed"] and case["effect"]["new_audit_rows"] == 1 and case["effect"]["final_inventory_status"] == "operational"
            and case["client_returncode"] == case["service_returncode"] == 0 and not case["cleanup_errors"] and not case["forced_cleanup"], "Table5 task/effect/lifecycle matches prior audit")
require([native["cases"][arm]["asgi_requests"] for arm in ("N11", "B7")] == [7, 11], "Table5 ASGI counts")
report = {"schema_version": "independent-paper-v5-raw-reading/1", "status": "passed", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
          "reviewer": "/root/agentops_task_bank", "draft_sha256": draft_sha, "raw_cells_read": raw_cells, "unknown_cells": unknowns,
          "tables1_and3_fully_reconstructed_from_raw": True, "table2_counts_and_difference_reconstructed_from_raw": True,
          "table2_family_ranges": "Previously independently verified; not recomputed here", "table4_and5": "Matched authoritative preserved audits; not independently rerun here",
          "same54certified_profile_sets_at100000": True, "guard_or_shared_adds_a_certified_case": False, "54shared_proofs_equal_original": True,
          "strongest_comparator": "Goal-pruned direct under declared coverage/work/proof metrics, not CPU timing",
          "literature_review_scope": "Read22 references and scoped attribution against retained literature synthesis; no new primary source acquisition",
          "new_solver_checker_application_provider_calls": 0, "human_scientific_review": False,
          "wording_findings": ["Section4.1 outside this four-method matrix is stale after all five sentence", "Section7.3 4688 legal tuples should be complete domain tuples;3281 are guard-false"]}
with (OUT / "result.json").open("x", encoding="utf-8") as target:
    json.dump(report, target, indent=2)
    target.write("\n")
print(json.dumps({"status": report["status"], "raw_cells_read": raw_cells, "unknown_cells": unknowns, "draft_sha256": draft_sha}))
