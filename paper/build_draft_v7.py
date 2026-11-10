"""Build an evidence-bound manuscript successor from audited development studies."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = "runs/shared-cache-ablation/read-review-42879031721-1/result.json"
AP2 = "runs/ap2-reference-development/v5/retained-42881390576-2/extracted/independent-evaluation/result.json"
AP2_PEER = "runs/ap2-reference-development/v5/retained-42881390576-2/independent-peer-review-v1.json"
AP2_NUMERIC = "runs/ap2-reference-development/v5/retained-42881390576-2/numeric-peer-review-v1.json"
AGENTOPS = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted/evaluation.json"
AGENTOPS_AUDIT = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/independent-raw-state-census-v1.json"
ADK = "runs/ap2-original-shopper-development/v7/retained-42886479185-1/extracted/independent-bank-evaluation/result.json"
ADK_PEER = "runs/ap2-original-shopper-development/v7/retained-42886479185-1/independent-raw-peer-review-v1.json"


def load(name):
    return json.loads((ROOT / name).read_bytes())


def record(name):
    data = (ROOT / name).read_bytes()
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(name, value):
    with (ROOT / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, indent=2) + "\n")


def build(*, publish=True):
    cache, ap2, peer, agentops, adk = map(load, (CACHE, AP2, AP2_PEER, AGENTOPS, ADK))
    numeric, adk_peer = map(load, (AP2_NUMERIC, ADK_PEER))
    agentops_audit = load(AGENTOPS_AUDIT)
    if cache["algorithm_cells"] != 1584 or ap2["declared_cells"] != 65 or len(agentops["cases"]) != 34 or adk["candidate_denominator"] != 34:
        raise ValueError("Preserved study denominators differ")
    if numeric["status"] != "independent_numeric_raw_evidence_verified" or numeric["reviewed_cells"] != 65:
        raise ValueError("Independent numerical AP2 review missing")
    if peer["status"] != "65_cell_source_gate_and_numeric_peer_audits_agree" or peer["disagreements"]:
        raise ValueError("Independent AP2 source/numerical audits disagree")
    if peer["source_gate_verified_cells"] != 65 or peer["numeric_verified_cells"] != 65 or not peer["all_rejection_controls_passed"]:
        raise ValueError("Incomplete independent AP2 source/numerical review")
    if agentops_audit["status"] != "passed_independent_raw_source_and_state_census":
        raise ValueError("Raw AgentOps source/state census missing")
    if (adk_peer["status"] != "independent_original_adk_raw_evidence_verified"
            or adk_peer["candidate_denominator"] != 34 or adk_peer["complete_original_adk_prefixes"] != 29
            or adk_peer["generic_status_adverse_boundaries"] != 28 or adk_peer["actual_original_purchases"] != 0
            or adk_peer["first_evaluator_disagreements"]):
        raise ValueError("Independent original ADK review incomplete or disagrees")
    text = (ROOT / "paper/working-draft-v6.md").read_bytes().decode()
    text = text.replace("Research manuscript, version 6, 10 November 2026.", "Research manuscript, version 7, 11 November 2026.", 1)
    text = text.replace("unestablished.\n\n## Abstract", "unestablished. This successor adds the complete cache ablation, original\npayment-tool comparison and source-bank reference feasibility results.\n\n## Abstract", 1)
    text = text.replace("paper-artifact-guide-v6.md", "paper-artifact-guide-v7.md")
    text = text.replace("**Application external validity.** The AgentOps result uses one original\ndeterministic confirmation fixture. Shared lifting is not the method executed\nby that application run.", "**Application external validity.** The original AgentOps effect result uses\none deterministic confirmation fixture and does not execute shared lifting.\nThe subsequent 34-candidate governed-App census and original ADK shopper\nallocation add source-bound offline feasibility observations; their incomplete\nrecipes and unrealized branches remain distinct from qualified task outcomes.")
    text = text.replace("task effects and observation completeness. They do not establish algorithmic", "task effects and observation completeness. A separate 1,584-cell cache\nablation supplies no additional certified cases over goal-pruned direct. A\n65-cell original AP2 payment-tool development comparison observes 3/13 demo\npurchases with admission alone versus 10/13 with informed public recovery;\n36 purchase observations include five subsequent duplicate-call errors. The\noriginal ADK shopper allocation observes 29/29 prefixes but zero completed\npurchases, preserving the original missing-challenge boundary. These offline\ndevelopment observations do not establish algorithmic", 1)
    methods = ("direct_pruned", "cache_neither", "cache_prefix", "cache_relation", "cache_both")
    index = {(row["budget"], row["method"]): row for row in cache["totals"]}
    table = "| Allowance | Goal-pruned direct | Neither | Prefix only | Relation only | Both |\n| ---: | ---: | ---: | ---: | ---: | ---: |\n"
    for budget in (32, 256, 4096, 100000):
        table += "| " + str(budget) + " | " + " | ".join(str(index[budget, m]["certified"]) + "/66" for m in methods) + " |\n"
    cache_section = """### 7.5. Separately allocated cache-component ablations

The prospective six-arm allocation re-executes every original profile at every
original allowance in fresh Linux workers. Its 1,584 method cells include
1,056 cache-policy cells; these are related repeated configurations, not 1,584
independent problems. Both-enabled certificates and deterministic counters
match all 264 retained shared-lifting cells exactly, excluding method labels
and elapsed time. Neither disabled cache changes whole-frame deduplication,
typed equality, witness ownership or incomplete-coverage rules.

**Table CA. Certified cache-ablation decisions on the same 66 profiles.**

""" + table + """
At allowance 100,000, neither/prefix/relation/both charge
46,278/44,432/50,150/46,840 units, versus 3,382 for goal-pruned direct.
Prefix-only saves 1,846 charges relative to neither cache; relation-only adds
3,872 and both adds 562. All four cache arms produce the same 27,248 accepted
proof bytes, versus 19,880 for direct. Recorded reuse is real: prefix-only
has 608 prefix hits, relation-only 2,184 relation hits and both has 608/720.
No policy certifies an additional case beyond goal-pruned direct. These charges
are method-specific, and a cache hit does not imply CPU speed or novelty.

The raw/source read audit checks 14,590 archive members and every dispatch,
result, certificate job and profile/clock join. Unknowns and failures stay in
their denominators. The exported [figure](../runs/shared-cache-ablation/figures-42879031721-1/shared-cache-ablation.pdf)
and [cell table](../runs/shared-cache-ablation/read-review-42879031721-1/case-methods.csv)
retain proof/checking and process observations. This ablation resolves the
component question while preserving the adverse aggregate comparison.

"""
    text = text.replace("## 8. Admission followed by an original application effect", cache_section + "## 8. Admission followed by an original application effect", 1)
    arms = ("reference", "conventional", "recovery", "shared", "recovery_shared")
    totals = {arm: sum(row["purchase_completed"] for row in ap2["cells"] if row["arm_id"] == arm) for arm in arms}
    purchase_table = "| Public development case | Reference | Conventional | Recovery | Admission | Recovery + admission |\n| --- | ---: | ---: | ---: | ---: | ---: |\n"
    for row in ap2["paired_comparisons"]:
        purchase_table += "| " + row["case_id"].replace("_", " ") + " | " + " | ".join(str(int(row["arms"][arm]["purchase_completed"])) for arm in arms) + " |\n"
    purchase_table += "| Total / 13 | " + " | ".join(str(totals[arm]) for arm in arms) + " |\n"
    states = Counter(row["status"] for row in agentops["cases"])
    application_section = """### 8.6. Original payment tools: paired development outcomes

The next prospectively allocated AP2 experiment executes both unchanged
original shopper payment/OTP tool bodies and the original merchant, processor
and credentials-provider handlers. It preserves 13 development cases across
five arms, for 65 fresh application cells. Every capture is verified; there
are no missing cells or evaluator refusals. Buyer-root signature/disclosure
and receipt-reference checks remain distinct from native/provider, financial
settlement and whole-task gold qualification. An independent cross-domain AI
read review reconstructs the raw outcomes and adverse paired result.

The conventional arm consumes the actual generic original payment-tool return.
The recovery arm makes one original public task read and restores recoverable
caller values. Admission alone checks a finite received-request relation;
the fifth arm adds that check to public recovery. Reference retains canonical
sender values as a disclosed upper bound. The arms have these stated evidence
and action differences; this is not the equal-budget primary held-out trial.
Transport DataPart loss is an explicit injected control, while failure to
surface the original challenge is an observed original-tool boundary.

**Table AP. Observed demo purchase completion (1), not unconditional strict
whole-task success; all cases are retained.**

""" + purchase_table + f"""
The {ap2['totals']['verified_purchases']} completion observations match both actual
original Tasks, their common context, caller receipt and credential-provider
delivery. Admission alone completes {totals['shared']}/13 versus informed recovery
{totals['recovery']}/13; it therefore supplies no observed utility advantage in
this development set. Recovery plus admission completes {totals['recovery_shared']}/13.
Wrong/missing replies are not repaired. Gate refusals avoid invalid or stale
dispatches but are not purchase completion. A second duplicate call fails after
an earlier successful receipt in conventional/recovery/reference; those suffix
errors remain retained even when the purchase-completion indicator is one.
The admitted duplicate is refused after its first dispatch. An expired finite
certificate is refused although an ungated original continuation can still
complete. These results illustrate the difference between correct bounded
admission, available repair and end-to-end utility.

The independent raw reconstruction additionally reports only
{numeric['total_strict_error_free_owned_cell_purchases']}/65 error-free owned-cell
purchases: reference/conventional/recovery/admission/recovery-plus-admission
are 10/2/9/2/8. Both gated duplicates retain an `AdmissionRefused` suffix;
all five duplicate cells therefore fail this stricter owned-cell indicator.
Neither indicator establishes full original ADK task success or human gold.

### 8.7. Original governed-App candidate references

The complete 34-record AgentOps attempt allocation retains all original bank
IDs and public recipes. The strict mechanical status census is
20 complete mechanically observed recipes, 10 partial recipes, two unsupported
public workflows and two failed checks, retaining the full denominator.
The independent raw/source/state census verifies all 1,621 extracted files
and the 421 original source members without application or evaluator calls.
Reference passes, partial obligations, unsupported public
workflows, check failures and missing evidence are distinct; none becomes a
human-qualified held-out trial. The separate eight-recipe predecessor remains
5/8 strict, including three preserved evidence/schema-check mismatches. Its
raw/state audit verifies actual same-user note persistence and recall across
two different completed SDK Tasks in one original session, without domain
action effects. A successful workflow exit alone is never a task grade.

The source-bound cold-import intervention skips an actual diagnosed urllib3
IPv6 capability probe, restores Python's flag before App startup and permits
no socket operation. The original 0/2 diagnostic failures remain unchanged.
Original App policy, source bodies, SDK task/session stores and attribution
are retained. Conditional confirmation, identity/replay and note initialization
timing limits remain in the individual records and complete denominator.

### 8.8. Original ADK shopper feasibility and remaining branches

The original ADK shopper successor retains all 34 AP2 candidates: 28 original
workflow candidates allocate 29 fresh official ADK workers, including a
two-process reset pair; six previous SDK boundary observations are linked as
mixed-scope controls, not new full-shopper runs. The original root/subagent
configurations, instruction/tool bodies and official sessions/ToolContexts
remain unchanged under a disclosed deterministic BaseLlm registry fixture.
Private evaluator reads are denied and an actual denial probe is retained.

The full allocation reports {adk['totals']['verified_original_adk_prefix_processes']}/29
verified original ADK prefixes, {adk['totals']['generic_status_adverse_processes']}
observed generic-status adverse processes, {adk['totals']['missing_processes']}
missing processes and {adk['totals']['actual_purchase_processes']} actual original
shopper purchase processes. These are feasibility observations. An OTP,
receipt or injected-fault branch that the original conversation never reaches
remains unrealized for its candidate, rather than counted as a passed task.
The wallet-display successor renders original list-valued address lines and
scalar components; its earlier scalar-only fixture omission is retained as
an owned fixture problem, not natural protocol loss. Human gold, independent
held-out qualification and provider quality remain unestablished.

"""
    text = text.replace("## 9. Discussion", application_section + "## 9. Discussion", 1)
    evidence = ["paper/working-draft-v6.md", "paper/claim-ledger-v6.json", "paper/draft-audit-v6-5.json", CACHE, AP2, AP2_PEER, AGENTOPS, ADK,
                AP2_NUMERIC, ADK_PEER, AGENTOPS_AUDIT,
                "runs/ci-agentops-governed-app-reference-v3/retained-42882455521-1/semantic-read-review-1.json",
                "runs/shared-cache-ablation/figures-42879031721-1/result.json"]
    if not publish:
        return text
    write("paper/working-draft-v7.md", text)
    write("paper/claim-ledger-v7.json", {"schema_version": "working-paper-claim-ledger/7", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "draft": record("paper/working-draft-v7.md"), "builder": record("paper/build_draft_v7.py"), "inherited_ledger": "paper/claim-ledger-v6.json",
        "evidence": [record(name) for name in evidence], "artifact_guide": record("docs/research/paper-artifact-guide-v7.md"), "human_scientific_review_claimed": False,
        "cache_cells": 1584, "AP2_development_cells": 65, "AP2_purchase_totals": totals, "AgentOps_statuses": dict(states),
        "AP2_ADK_totals": adk["totals"], "original_full_study_scope_complete": False})
    write("paper/draft-status-v7.json", {"schema_version": "working-paper-draft-status/7", "document": "paper/working-draft-v7.md",
        "full_manuscript_drafted": True, "publication_ready": False, "human_scientific_review_claimed": False,
        "original_full_study_scope_complete": False, "new_application_or_provider_calls_for_drafting": 0, "claim_ledger": "paper/claim-ledger-v7.json"})
    print(json.dumps({"status": "drafted_with_bound_evidence", "purchase_totals": totals, "AgentOps_statuses": dict(states), "ADK_totals": adk["totals"]}))


if __name__ == "__main__":
    build()
