"""Build a preserved V13 successor from the reviewed common-cost audit3."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath
import statistics

ROOT = Path(__file__).resolve().parents[1]
V13 = ROOT / "paper/working-draft-v13.md"
GUIDE = ROOT / "docs/research/paper-artifact-guide-v14.md"
METHODS = ("legacy_direct", "goal_pruned_direct", "original_refinement", "shared_lift", "guard_pruned_direct")
FIELDS = ("cpu_total_ns", "outer_wall_ns", "peak_rss_bytes")
STATUSES = ("certified", "unknown", "failure", "timeout", "stopped", "stopped_without_closing_receipt", "not_started")
FINAL_AUDIT_SHA = "737ce96dfbe415898c5d7e31eb38f2f25e4fedaabaf2c622b7563a2c9b61338e"


def need(condition, label):
    if not condition:
        raise ValueError(label)


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "duplicate_JSON_key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("nonfinite_JSON_value")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def read(path):
    return parse(Path(path).read_bytes())


def record(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink(), "workspace_regular_input_required")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def byte_identity(row):
    return {key: row[key] for key in ("bytes", "sha256")}


def inherited_records():
    provenance = read(ROOT / "paper/working-draft-v13.provenance.json")
    audit = read(ROOT / "paper/working-draft-v13.audit.json")
    need(provenance["paper_sha256"] == record(V13)["sha256"] and audit["passed"] is True,
         "audited_frozen_V13_required")
    for row in provenance["inputs"] + audit["inputs"]:
        need(record(ROOT / row["path"]) == row, "frozen_V13_evidence_changed:" + row["path"])
    return provenance["inputs"] + audit["inputs"] + [record(path) for path in (V13,
        ROOT / "paper/working-draft-v13.provenance.json", ROOT / "paper/working-draft-v13.audit.json")]


def bind_cost(base, audit_path):
    base, audit_path = Path(base).resolve(), Path(audit_path).resolve()
    need(base == ROOT / "runs/common-cost-development/v1/retained-42927208534-1"
         and audit_path == ROOT / "runs/common-cost-development/v1/read-audit-42927208534-3/result.json",
         "actual_reviewed_common_cost_retention_and_audit3_required")
    need(record(audit_path)["sha256"] == FINAL_AUDIT_SHA, "final_reviewed_audit3_bytes_changed")
    audit = read(audit_path)
    need(audit["schema_version"] == "common-cost-independent-read-audit/1"
         and audit["status"] == "passed_read_only_archive_receipt_and_physical_cost_audit"
         and audit["run_id"] == 42927208534 and audit["run_attempt"] == 1
         and audit["new_worker_solver_checker_application_or_provider_executions"] == 0
         and audit["certificate_semantics_reexecuted"] is False
         and audit["certificate_header_identity_verified_without_semantic_execution"] is True,
         "completed_read_only_cost_audit_required")
    run, receipt, api = [read(base / name) for name in ("github-run.json", "retention.json", "github-artifacts.json")]
    archive = record(base / "artifact.zip")
    need(run["status"] == "completed" and run["id"] == audit["run_id"]
         and run["run_attempt"] == audit["run_attempt"] and run["head_sha"] == audit["head_sha"]
         and run["conclusion"] == audit["workflow_conclusion"]
         and receipt["status"] == "retained" and receipt["run_id"] == run["id"]
         and receipt["head_sha"] == run["head_sha"]
         and receipt["archive_bytes"] == archive["bytes"] and receipt["archive_sha256"] == archive["sha256"]
         and audit["archive_identity"] == byte_identity(archive)
         and receipt["api_digest"] == "sha256:" + archive["sha256"] and receipt["digest_matches_api"] is True,
         "actual_completed_cost_run_archive_binding_changed")
    artifacts = [row for row in api["artifacts"] if row["id"] == receipt["artifact_id"]]
    need(len(artifacts) == 1 and artifacts[0]["digest"] == receipt["api_digest"]
         and artifacts[0]["size_in_bytes"] == archive["bytes"]
         and artifacts[0]["workflow_run"]["id"] == run["id"]
         and artifacts[0]["workflow_run"]["head_sha"] == run["head_sha"], "cost_API_artifact_changed")
    directory = audit_path.parent
    inputs = [record(audit_path), archive]
    for row in audit["exports"]:
        path = directory / row["path"]
        need(byte_identity(record(path)) == byte_identity(row), "cost_audit_export_changed")
        inputs.append(record(path))
    evidence = read(directory / "evidence-files.json")
    for row in evidence["saved_metadata_and_archive"]:
        path = base / PurePosixPath(row["path"]).name
        need(byte_identity(record(path)) == byte_identity(row), "cost_audit_metadata_binding_changed")
        inputs.append(record(path))
    source = directory / "auditor-source.py"
    need(byte_identity(record(source)) == byte_identity(audit["auditor_source_identity"]), "exact_audit3_source_changed")
    inputs.append(record(source))
    cells = [parse(raw) for raw in (directory / "cells.jsonl").read_bytes().splitlines()]
    need(len(cells) == 1650 and [row["cell"]["index"] for row in cells] == list(range(1650))
         and len({row["cell"]["id"] for row in cells}) == 1650, "all1650_ordered_cost_cells_required")
    counts = {}
    for method in METHODS:
        rows = [row for row in cells if row["cell"]["method_id"] == method]
        status = Counter(row["status"] for row in rows)
        need(len(rows) == 330 and set(status).issubset(STATUSES), "complete330_method_denominator_required")
        counts[method] = {key: status[key] for key in STATUSES}
        counts[method]["allocated"] = len(rows)
        counts[method].update(supported=sum(row["status"] == "certified" and row["decision"] == "supported" for row in rows),
                              unsupported=sum(row["status"] == "certified" and row["decision"] == "unsupported" for row in rows))
        captured = next(row for row in audit["method_totals"] if row["method_id"] == method)
        need(captured["all_status_counts"] == {key: status[key] for key in STATUSES}
             and captured["captured_certified_supported"] == counts[method]["supported"]
             and captured["captured_certified_unsupported"] == counts[method]["unsupported"], "cost_status_table_not_raw_audit_cells")
    need(not audit["summary"]["certified_contradictions"] and not audit["summary"]["hash_seed_probe_disagreements"]
         and not audit["logical_headroom_raw_label_discrepancies"]
         and audit["independent_cost_cohorts_differ_from_frozen_runner"] is False,
         "actual_capture_contradictions_or_cohort_discrepancies_require_separate_reporting")
    pairs = {}
    for left, right in itertools.combinations(METHODS, 2):
        key = left + "__" + right
        rows = audit["paired_profile_costs"][key]["per_profile"]
        need(len(rows) == audit["paired_profile_costs"][key]["complete_same_decision_certified_profile_count"] == 54
             and all(row["paired_repeats"] == 5 for row in rows), "all_ten_actual54_profile_cohorts_required")
        pairs[key] = {"left_method": left, "right_method": right, "profiles": len(rows),
                      "medians": {field: statistics.median(row[field]["left_over_right"] for row in rows) for field in FIELDS}}
    shared = {}
    rows = audit["paired_profile_costs"]["goal_pruned_direct__shared_lift"]["per_profile"]
    for field in FIELDS:
        ratios = [row[field]["right_median"] / row[field]["left_median"] for row in rows]
        shared[field] = {"median_ratio": statistics.median(ratios), "min_ratio": min(ratios), "max_ratio": max(ratios),
                         "lower": sum(value < 1 for value in ratios), "equal": sum(value == 1 for value in ratios),
                         "higher": sum(value > 1 for value in ratios)}
    inputs += [record(ROOT / name) for name in ("docs/research/common-cost-results-v1.md", "docs/research/common-cost-benchmark-v1.md")]
    return audit, counts, pairs, shared, inputs


def cost_section(audit, counts, pairs, shared, audit_path):
    status = ["| Method | Allocated | Certified | Supported | Unsupported | Unknown | Failure | Timeout | Stopped | Unclosed | Not started |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for method in METHODS:
        row = counts[method]
        values = [330, row["certified"], row["supported"], row["unsupported"], row["unknown"], row["failure"],
                  row["timeout"], row["stopped"], row["stopped_without_closing_receipt"], row["not_started"]]
        status.append("| " + method + " | " + " | ".join(map(str, values)) + " |")
    comparisons = ["| Left / right method | Paired profiles | Median CPU ratio | Median wall ratio | Median peak RSS ratio |",
                   "| --- | ---: | ---: | ---: | ---: |"]
    for pair in pairs.values():
        comparisons.append(f"| {pair['left_method']} / {pair['right_method']} | {pair['profiles']} | "
            + " | ".join(f"{pair['medians'][field]:.6f}" for field in FIELDS) + " |")
    directional = ["| Metric | Median shared/direct ratio | Observed profile ratio range | Shared lower / equal / higher |",
                   "| --- | ---: | --- | ---: |"]
    for field, label in zip(FIELDS, ("Lifetime CPU", "Outer wall", "Lifetime peak RSS")):
        row = shared[field]
        directional.append(f"| {label} | {row['median_ratio']:.6f} | {row['min_ratio']:.6f} to {row['max_ratio']:.6f} | "
                           f"{row['lower']} / {row['equal']} / {row['higher']} |")
    return f"""### 8.12. Actual common end-to-end physical-cost development comparison

The [separate hosted common-cost allocation](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42927208534),
attempt 1 at revision `{audit['head_sha']}`, retained all 1,650 allocated
attempts: the same 66 authored development profiles, five unchanged methods
and five dependent timing repeats per method. Each profile/method occupies
every serial position once across the five repeats, with a shared hash seed
within each profile/repeat block. This is a separate development allocation.

All 1,650 attempts opened, closed and retained terminal resource observations.
The unchanged independent checker accepted 1,350 captured conclusive results;
300 unknown results remain in the full census with their measured costs.
They supply no certified verdict or cost-ratio observation. The profile-level
decisions agree across all five methods/repeats: 28 supported, 26 unsupported
and 12 unknown. Capture acceptance is audited from its retained source/result
and checking receipt; neither this build nor the read auditor reexecutes proof
semantics.

**Table V14A. All allocated statuses, with denominator 330 for each method.**

{chr(10).join(status)}

All ten paired comparisons contain 54 profiles. Each eligible profile has all
five paired repeats certified to one decision and nonbinding logical/CPU/wall
limits. Unknown, rejected, failed, timed out, stopped and unstarted attempts
remain in the census and are excluded from descriptive cost ratios. A
profile-wide supported/unsupported certificate contradiction would quarantine
that profile across every comparison; none occurred here.

**Table V14B. Median of the 54 per-profile left/right cost ratios.**

{chr(10).join(comparisons)}

Each profile contributes its method's median across five dependent repeats;
the ratio divides that left median by its paired right median. The table then
reports the median of those profile ratios. A value below 1 means lower left
cost for the specified metric. It is not a ratio of pooled task totals, an
inferential confidence interval or 330 independent tasks per method.

**Table V14C. Explicit shared_lift/goal_pruned_direct direction.**

{chr(10).join(directional)}

Shared lifting adds no certified profile coverage and has higher observed
full-process median CPU, outer wall and peak RSS than goal-pruned direct on
every one of the 54 eligible profiles. Original refinement also has lower
observed CPU, wall and RSS medians than shared lifting on all 54 profiles.
These are descriptive paired development tradeoffs; they establish no
algorithmic superiority, novel contribution or held-out population result.
Observed ratio ranges above are minimum/maximum profile ratios, not uncertainty
intervals. The 300 unknown attempts retain their costs without entering ratios.

Primary costs include interpreter startup, source/profile loading, solver
import/evaluation, a fresh independent checker package namespace and fresh
input/result copies, serialization/output, group cleanup and terminal reaping.
The sole terminal Linux `wait4` supplies full child CPU and peak RSS; outer wall
spans launch through cleanup/reaping. Inner phase timings remain secondary.
The identical limits are CPU soft/hard 5/6 seconds, wall 10 seconds and 512 MiB
`RLIMIT_AS`. Peak RSS is observed worker lifetime memory, not an enforced RSS
hard cap. The preserved checker allowance is 2,000,000. A checker `False`
would remain an uncertified invalid-proof-or-soft-cap result rather than an
unsupported verdict; none occurred here.

Every solver receives the same explicit 100,000,000 logical allowance, but its
charged operations remain method-specific diagnostics. The frozen worker
labels logical headroom from counter slack alone; independent audit3 also
requires the retained result and a known nonexhaustion method/decision reason.
An exhaustion reason overrides slack, and an unbound or unrecognized reason
remains indeterminate. No raw-label discrepancy or exhaustion reason occurred;
the independently conservative cohorts match the frozen runner's cohorts.
Recorded interpreter identity has no archived executable bytes for a separate
byte verification, and small process costs remain sensitive to imports and
one runner's scheduling.

The [final independent audit3](../{Path(audit_path).resolve().relative_to(ROOT).as_posix()})
binds every raw artifact, closing receipt, captured solver result and profile/
certificate header without executing the worker, method or checker. Its prior
audit1/audit2 revisions remain preserved. The 9,438,211-byte archive has SHA-256
`bc84692b270eadb32ee80c0e1c4ac594606329542d6db0852c874287c894be23`.
All 11,634 extracted members and 1,730 pre-execution frozen inputs were verified.
The [results guide](../docs/research/common-cost-results-v1.md) preserves every
excluded-profile reason, unknown reason, phase observation and unrounded ratio.
No App, model API or provider executed in this cost allocation.

The registered 96-task, 288-path-cell and 96-crossing study remains incomplete.
Human gold, untouched holdout/near misses, complete route/source-to-model and
original native-launcher qualification, distinctive contribution and
accountable final scientific review remain unresolved. This successor supplies
physical development costs without claiming publication readiness.

"""


def build(base, audit_path):
    inputs = inherited_records()
    audit, counts, pairs, shared, cost_inputs = bind_cost(base, audit_path)
    text = V13.read_text(encoding="utf-8")
    title = text.splitlines()[0]
    need(text.count("Research manuscript, version 13,") == 1 and text.count("## 9. Discussion") == 1,
         "frozen_V13_layout_changed")
    text = text.replace("Research manuscript, version 13,", "Research manuscript, version 14,", 1)
    text = text.replace("paper-artifact-guide-v13.md", "paper-artifact-guide-v14.md")
    meter_scope = """Equal numerical allowances therefore
compare declared method-specific accounting policies, not equal CPU or hardware
budgets. The adverse coverage result cannot by itself establish practical
efficiency or a general speed ranking."""
    need(text.count(meter_scope) == 1, "frozen_V13_logical_meter_limit_anchor_changed")
    text = text.replace(meter_scope, """Equal numerical logical work allowances therefore
compare declared method-specific accounting policies, not equal CPU or hardware
budgets. The charged-work coverage result cannot by itself establish practical
efficiency or a general speed ranking. The separate common-cost allocation
measures full-process physical costs under identical CPU/address-space/wall
limits on this authored development cohort.""", 1)
    timing_scope = """Internal checker work is unavailable, and single-order
wall time and operating-system peak memory do not support general performance
rankings."""
    need(text.count(timing_scope) == 1, "frozen_V13_historical_timing_limit_anchor_changed")
    text = text.replace(timing_scope, """Internal charged checker work remains unavailable. Historical single-order
wall time and operating-system peak memory do not support general performance
rankings. The separate common-cost allocation balances five repeated method
positions and observes complete worker costs on one serial runner. Its related
development profiles and dependent timing repeats still do not support
held-out population or general performance rankings.""", 1)
    anchor = "The lossless V2 proof codec restores all 26 retained negative certificates;"
    need(text.count(anchor) == 1, "frozen_V13_abstract_codec_anchor_changed")
    text = text.replace(anchor, """A separate common-cost development allocation retains all 1,650 attempts;
each method has 270 captured certified results and 60 unknown results. All ten
paired comparisons contain 54 profiles with five dependent timing repeats.
Shared lifting adds no certified coverage and has higher observed full-process
CPU, wall and RSS medians than goal-pruned direct on every eligible profile.
These descriptive costs establish no novelty or held-out superiority.

""" + anchor, 1)
    text = text.replace("## 9. Discussion", cost_section(audit, counts, pairs, shared, audit_path) + "## 9. Discussion", 1)
    need(text.splitlines()[0] == title, "registered_title_changed")
    inputs += cost_inputs + [record(Path(__file__)), record(GUIDE)]
    inputs += [record(ROOT / name) for name in ("scripts/restore_retained_evidence_v1.py",
        "scripts/restore_retained_paper_evidence_v1.py", "scripts/restore_retained_paper_evidence_v2.py",
        "scripts/restore_retained_paper_evidence_v3.py")]
    inputs = list({row["path"]: row for row in inputs}.values())
    provenance = {"schema_version": "paper-v14-evidence-bound-build/1", "built_utc": datetime.now(timezone.utc).isoformat(),
        "registered_title": title[2:], "paper_sha256": hashlib.sha256(text.encode()).hexdigest(), "inputs": inputs,
        "inherited_v13_sha256": record(V13)["sha256"], "cost_run_id": audit["run_id"], "cost_run_attempt": audit["run_attempt"],
        "cost_base_path": Path(base).resolve().relative_to(ROOT).as_posix(),
        "cost_audit_path": Path(audit_path).resolve().relative_to(ROOT).as_posix(),
        "cost_allocated_cells": 1650, "cost_method_counts": counts, "cost_pair_summaries": pairs,
        "shared_vs_goal_pruned_direct": shared, "comparison_unit": "66 related authored profiles; five dependent timing repeats",
        "original_study_tasks": 96, "original_study_paths": 288, "original_study_crossings": 96,
        "original_full_scope_revised": False, "full_original_study_complete": False, "publication_ready": False,
        "human_scientific_review": False, "new_application_evaluator_solver_checker_or_provider_calls": 0}
    return text, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cost-base", type=Path, required=True)
    parser.add_argument("--cost-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    output, provenance = args.output.resolve(), args.provenance.resolve()
    need(output == ROOT / "paper/working-draft-v14.md" and provenance == ROOT / "paper/working-draft-v14.provenance.json"
         and not output.exists() and not provenance.exists(), "fresh_owned_V14_artifacts_required")
    text, value = build(args.cost_base, args.cost_audit)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with provenance.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": "actual_common_cost_V14_manuscript_built", "run_id": value["cost_run_id"]}))


if __name__ == "__main__":
    main()
