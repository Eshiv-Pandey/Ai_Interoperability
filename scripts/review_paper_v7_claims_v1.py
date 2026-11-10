"""Independent read-only claim review of the v7 manuscript or builder preview."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_bytes())


def identity(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def review():
    builder_path = ROOT / "paper/build_draft_v7.py"
    spec = importlib.util.spec_from_file_location("_peer_v7_builder_preview", builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    draft_path = ROOT / "paper/working-draft-v7.md"
    mode = "published_local_draft" if draft_path.exists() else "read_only_builder_preview"
    text = draft_path.read_text(encoding="utf-8") if draft_path.exists() else builder.build(publish=False)
    flat = re.sub(r"\s+", " ", text)
    source_peer = read(ROOT / builder.AP2_PEER)
    numeric = read(ROOT / builder.AP2_NUMERIC)
    cache = read(ROOT / builder.CACHE)
    agentops = read(ROOT / builder.AGENTOPS_AUDIT)
    adk = read(ROOT / builder.ADK_PEER)
    checks = []

    def check(name, value, evidence):
        checks.append({"id": name, "passed": bool(value), "evidence": evidence})

    arms = ("reference", "conventional", "recovery", "shared", "recovery_shared")
    totals = {arm: sum(row["purchase_completed"] for row in numeric["cells"] if row["arm_id"] == arm) for arm in arms}
    check("ap2_same_65_cell_purchase_and_error_free_denominators",
          numeric["reviewed_cells"] == source_peer["declared_cells"] == 65
          and totals == source_peer["purchase_counts"]
          and numeric["total_verified_purchases"] == 36
          and numeric["total_strict_error_free_owned_cell_purchases"] == 31,
          {"purchase_counts": totals, "error_free_owned_cell_count": 31})
    expected_table = []
    by_case = {}
    for row in numeric["cells"]:
        by_case.setdefault(row["case_id"], {})[row["arm_id"]] = row["purchase_completed"]
    for case, values in by_case.items():
        line = "| " + case.replace("_", " ") + " | " + " | ".join(str(int(values[arm])) for arm in arms) + " |"
        expected_table.append(line)
    expected_table.append("| Total / 13 | " + " | ".join(str(totals[arm]) for arm in arms) + " |")
    check("ap2_every_paired_table_row_matches_independent_raw_numeric_audit",
          all(line in text for line in expected_table), {"rows": len(expected_table)})
    duplicates = [row for row in numeric["cells"] if row["case_id"] == "duplicate_continuation"]
    check("all_five_duplicate_purchases_keep_exact_error_classification",
          len(duplicates) == 5 and all(row["purchase_completed"] and not row["strict_error_free_owned_cell_purchase"] for row in duplicates)
          and [row["actor_error_type"] for row in duplicates] == ["A2AClientJSONRPCError"] * 3 + ["AdmissionRefused"] * 2
          and "31/65 error-free owned-cell" in flat and "Both gated duplicates retain an `AdmissionRefused` suffix" in flat,
          [{"arm": row["arm_id"], "suffix": row["actor_error_type"]} for row in duplicates])
    check("adverse_ap2_utility_and_unequal_information_are_disclosed",
          "3/13 versus informed recovery 10/13" in flat
          and "no observed utility advantage" in flat and "Reference retains canonical sender values" in flat
          and "not the equal-budget primary held-out trial" in flat,
          {"shared_minus_recovery_purchases": totals["shared"] - totals["recovery"], "denominator": 13})
    methods = ("direct_pruned", "cache_neither", "cache_prefix", "cache_relation", "cache_both")
    cache_index = {(row["budget"], row["method"]): row for row in cache["totals"]}
    cache_rows = ["| " + str(budget) + " | " + " | ".join(str(cache_index[budget, method]["certified"]) + "/66"
                  for method in methods) + " |" for budget in (32, 256, 4096, 100000)]
    check("cache_ablation_table_and_method_cell_denominators",
          cache["algorithm_cells"] == 1584 and cache["cache_policy_cells"] == 1056
          and all(line in text for line in cache_rows) and "not 1,584 independent problems" in flat,
          {"profiles": 66, "method_cells": 1584, "cache_policy_cells": 1056})
    max_rows = [cache_index[100000, method] for method in methods]
    check("cache_work_proof_and_hits_match_retained_audit",
          [row["work_units_sum"] for row in max_rows] == [3382, 46278, 44432, 50150, 46840]
          and [row["proof_bytes_sum"] for row in max_rows] == [19880, 27248, 27248, 27248, 27248]
          and "46,278/44,432/50,150/46,840" in flat and "No policy certifies an additional case" in flat,
          {"work_units": [row["work_units_sum"] for row in max_rows], "proof_bytes": [row["proof_bytes_sum"] for row in max_rows]})
    check("agentops_34_candidate_mechanical_reference_scope",
          "20 complete mechanically observed recipes, 10 partial recipes, two unsupported public workflows and two failed checks" in flat
          and "none becomes a human-qualified held-out trial" in flat,
          {"retained_audit_status": agentops["status"]})
    check("adk_prefix_process_denominator_not_full_task_success",
          adk["candidate_denominator"] == 34 and adk["new_original_processes"] == adk["complete_original_adk_prefixes"] == 29
          and adk["generic_status_adverse_boundaries"] == 28 and adk["actual_original_purchases"] == 0
          and "29/29 verified original ADK prefixes" in flat and "0 actual original shopper purchase processes" in flat
          and "six previous SDK boundary observations" in flat and "two-process reset pair" in flat
          and "remains unrealized for its candidate" in flat,
          {"candidate_denominator": 34, "new_processes": 29, "generic_adverse": 28, "purchases": 0})
    check("inherited_artifact_guide_link_updated", "paper-artifact-guide-v7.md" in text
          and "paper-artifact-guide-v6.md" not in text, "New studies must be covered by the v7 guide.")
    check("inherited_one_fixture_external_validity_statement_scoped",
          "The AgentOps result uses one original deterministic confirmation fixture" not in flat
          and "34-candidate governed-App census" in flat and "unrealized branches" in flat,
          "The earlier effect fixture and new candidate references have different scopes.")
    build_source = builder_path.read_text(encoding="utf-8")
    check("builder_requires_complete_passed_ap2_and_adk_peers",
          all(marker in build_source for marker in ("peer[\"source_gate_verified_cells\"]", "peer[\"numeric_verified_cells\"]",
              "peer[\"all_rejection_controls_passed\"]", "adk_peer[\"status\"]")),
          "Hash binding alone must not accept a failed or incomplete independent review.")
    links = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
    broken = []
    for target in links:
        parsed = urlparse(target)
        if not parsed.scheme:
            resolved = ((ROOT / "paper") / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                broken.append(target)
    check("all_local_manuscript_links_resolve", not broken, {"broken": broken, "checked": len(links)})
    return {"schema_version": "paper-v7-independent-claim-counterreview/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode, "passed": all(row["passed"] for row in checks), "checks": checks,
        "findings_addressed": ["AP2 36 payments versus 31 error-free cells and all five duplicate suffix errors",
            "Adverse shared versus recovery utility and unequal arm information", "Inherited v6 artifact-guide and one-fixture scope",
            "Passed peer-status and complete-denominator requirements before building"],
        "inputs": [identity(ROOT / name) for name in (builder.AP2_PEER, builder.AP2_NUMERIC, builder.CACHE,
                    builder.AGENTOPS_AUDIT, builder.ADK_PEER)] + [identity(builder_path)],
        "draft_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "human_scientific_review": False, "new_application_provider_solver_calls": 0,
        "limits": ["This review checks retained numerical and scope claims; it does not establish novelty, human gold, publication readiness or broad external validity."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh_counterreview_output_required")
    result = review()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "mode": result["mode"],
                      "failed_checks": [row["id"] for row in result["checks"] if not row["passed"]]}))
    raise SystemExit(0 if result["passed"] else 1)
