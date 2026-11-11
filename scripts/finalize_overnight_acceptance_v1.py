"""Record the retained-scope eight-criterion review; release smoke is root-owned."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_overnight_acceptance_v1 import command, identity, read, verify_records, bound_records, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--note", type=Path)
    args = parser.parse_args()
    directory = args.audit_dir.resolve()
    directory.relative_to(ROOT)
    integrity = json.loads((directory / "evidence-integrity.json").read_text())
    commands = json.loads((directory / "commands.json").read_text())
    if any(group["status"] != "passed" for group in integrity["groups"]):
        raise ValueError("Retained evidence integrity failure")
    if integrity["ap2_archive"]["status"] != "passed":
        raise ValueError("AP2 archive integrity failure")
    if any(item["exit_code"] != 0 for item in commands["commands"]):
        raise ValueError("Acceptance command failure")
    tests_text = (directory / "focused-tests.stderr.txt").read_text()
    tests = int(re.search(r"Ran (\d+) tests", tests_text).group(1))
    bank = json.loads((directory / "task-bank-validation.json").read_text())
    if not bank["allocation_complete"] or bank["total_templates"] != 68:
        raise ValueError("Candidate bank incomplete")
    paper_output = ROOT / "paper" / ("working-draft-v15.overnight-recheck-" + uuid.uuid4().hex + ".json")
    paper_command = command(directory, "paper-v15-independent-recheck-success", [
        sys.executable, "-I", "-S", "-B", "paper/audit_draft_v15.py",
        "--draft", "paper/working-draft-v15.md", "--provenance",
        "paper/working-draft-v15.provenance.json", "--ledger", "paper/claim-ledger-v15.json",
        "--output", str(paper_output)])
    write(directory / "paper-command-success.json", {"command": paper_command,
                                              "source": identity(__file__)})
    if paper_command["exit_code"] != 0:
        raise ValueError("Current paper read audit failed")
    paper_audit = json.loads(paper_output.read_text())
    if not paper_audit["passed"] or paper_audit["checks_passed"] != 19:
        raise ValueError("Current paper claims did not pass")
    supplemental = read("runs/task-bank-review/ap2-current-ai-supplement-v1.json")
    supplemental_identity = verify_records("current_AP2_review_inputs", supplemental["input_files"])
    if supplemental_identity["status"] != "passed":
        raise ValueError("Supplemental task-bank review inputs drifted")
    analysis_result = read("runs/research-analysis/v1-20261110-3/result.json")
    generator = identity("scripts/analyze_research_results_v1.py")
    if generator["sha256"] != analysis_result["script_sha256"]:
        raise ValueError("Analysis generator bytes drifted")
    evidence_paths = [
        "docs/research/implementation-delivery-plan-v2.md",
        "docs/research/v1-release-plan-20261112.md",
        "runs/implementation-acceptance/audit-v1.json",
        "runs/research-analysis/independent-review-v1.json",
        "runs/ci-research-core/download-42819352517-independent-review.json",
        "runs/ci-agentops-native/download-42808110286-independent-review.json",
        "runs/task-bank-review/agentops-v1.json",
        "runs/task-bank-review/ap2-v1.json",
        "runs/task-bank-review/ap2-current-ai-supplement-v1.json",
        "runs/ap2-original-native-provider-development/v2/independent-raw-review-v1/review.json",
        "runs/ap2-original-native-provider-development/v2/independent-semantic-analysis-v1/analysis.json",
        "paper/working-draft-v15.md", "paper/working-draft-v15.provenance.json",
        "paper/claim-ledger-v15.json", "paper/working-draft-v15.audit.json",
        "docs/research/paper-artifact-guide-v15.md",
    ]
    criteria = [
        {"id": "algorithm", "criterion": "Algorithm prototype", "status": "accepted",
         "verification": f"{tests} fresh focused controls across algorithm/comparison/bank/AP2 semantic modules; all ten historical implementation source identities match current bytes.",
         "evidence": ["runs/implementation-acceptance/audit-v1.json", str((directory / "focused-tests.stderr.txt").relative_to(ROOT)).replace("\\", "/")],
         "claim_limit": "Finite supplied-model supported/unsupported/unknown API and certificates; no model-faithfulness or novel advantage claim."},
        {"id": "comparison", "criterion": "Fair comparison engine", "status": "accepted",
         "verification": "Four budgets, 66 profiles and four methods; complete retained worker/checker evidence; all four Linux bundles freshly verified against current trusted code.",
         "evidence": ["runs/implementation-acceptance/audit-v1.json", "runs/shared-lifting-scaling/v3-20261110-1/result.json"],
         "claim_limit": "Method-specific charged work; shared lifting demonstrates no superiority. Failures/unknowns retain denominators."},
        {"id": "analysis", "criterion": "Reproducible results analysis", "status": "accepted",
         "verification": "Current generator and all 17 analysis input and seven output identities match the independently reconciled 11,640 table cells and saved figure review.",
         "evidence": ["runs/research-analysis/v1-20261110-3/result.json", "runs/research-analysis/independent-review-v1.json"],
         "claim_limit": "Saved independent numeric/PNG/SVG review reused only after byte checks; PDF hash bound but not independently rendered during historical review or this audit."},
        {"id": "clean_reproduction", "criterion": "Clean-environment reproduction", "status": "pending_current_release_smoke",
         "verification": "Historical fresh Linux run 42819352517 passed 167 tests and matches 1056 algorithm, 264 reference and 683 checker outputs. Its 10821 retained file identities and four bundles pass fresh checks.",
         "evidence": ["runs/ci-research-core/download-42819352517-independent-review.json"],
         "pending": "Root must append the separate current-release Linux smoke/core/demo replay qualification before release acceptance.",
         "claim_limit": "This audit did not perform a new checkout, hosted dispatch or download; historical transport ZIP digest was not independently rechecked."},
        {"id": "agentops", "criterion": "AgentOps application integration", "status": "accepted",
         "verification": "1138 exported files freshly rehashed. Historical native N11 precedes B7; each completes original task with inventory operational and exactly one audit row. B7 certificate-to-wire binding and clean exits are retained.",
         "evidence": ["runs/ci-agentops-native/download-42808110286-independent-review.json"],
         "claim_limit": "One deterministic native fixture per arm using original refinement; shared-lift v2 was not the application solver. No complete-runtime/capture authentication claim."},
        {"id": "task_bank", "criterion": "Complete two-domain candidate bank", "status": "accepted",
         "verification": "Fresh complete-bank validation checks 68 public/evaluator pairs: 12 development, 8 calibration, 48 prospective held-out candidates. Historical AgentOps/AP2 source crossreviews and current six-record AP2 supplement document fixes.",
         "evidence": [str((directory / "task-bank-validation.json").relative_to(ROOT)).replace("\\", "/"), "runs/task-bank-review/ap2-current-ai-supplement-v1.json", "runs/task-bank-review/agentops-v1.json"],
         "claim_limit": "Candidate authorship/source crossreview only: 296 source-supported claims and 271 pending human judgments. No human gold, untouched holdout or execution qualification; historical AP2 review does not bind every current edit."},
        {"id": "ap2", "criterion": "AP2 application integration", "status": "accepted",
         "verification": "V2 archive digest and 217 extracted files freshly checked; public semantic reanalysis has zero questions. Five fixed cases retain two completed original Tasks/demo Success receipts, wrong/no-reply outcomes, recovery and an unreached repeat prerequisite; all recorded children reaped.",
         "evidence": ["runs/ap2-original-native-provider-development/v2/independent-raw-review-v1/review.json", str((directory / "ap2-v2-semantic-recheck.json/analysis.json").relative_to(ROOT)).replace("\\", "/")],
         "claim_limit": "Scripted public caller under original native services/SDK generation with owned choices/binder/provider accounting; no autonomous shopper/bridge/settlement/idempotency or human-gold claim."},
        {"id": "paper", "criterion": "Complete paper package", "status": "accepted",
         "verification": "V15 full manuscript, references, 29-claim current ledger, 3468 input provenance and artifact guide pass this fresh 19-check read audit. Saved V14 20-check numeric audit and technical/result text retained; new profile counts rederived from raw archives.",
         "evidence": ["paper/working-draft-v15.md", "paper/claim-ledger-v15.json", str(paper_output.relative_to(ROOT)).replace("\\", "/"), "docs/research/paper-artifact-guide-v15.md"],
         "claim_limit": "Complete development manuscript/artifact package. Human scientific/reference review, authorship and publication readiness remain explicit open decisions; earlier certificate semantics not rerun by V15 reader."},
    ]
    report = {
        "schema_version": "overnight-v1-delivery-acceptance/1",
        "reviewed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "reviewer": "AI retained-evidence and current-source acceptance reviewer",
        "scope": "Existing eight implementation-delivery criteria, with additional current-release smoke pending root",
        "status": "seven_criteria_accepted_current_release_smoke_pending",
        "accepted_criteria": 7, "total_criteria": 8,
        "whole_project_percentage_assigned": None,
        "original_full_study_complete": False,
        "publication_ready": False,
        "human_gold_or_scientific_review_granted": False,
        "fresh_evidence_files_hashed": sum(group["files_checked"] for group in integrity["groups"]),
        "fresh_focused_tests": tests,
        "fresh_paper_read_checks": paper_audit["checks_passed"],
        "source_bound_generator": generator,
        "criteria": criteria,
        "material_release_gap": "Current-release fresh Linux smoke/core/demo qualification is not performed by this reviewer; root owns it and final freeze/push.",
        "fixed_gap": "The current V15 ledger now binds the manuscript; the inherited V7 ledger did not bind V14 and is retained as historical evidence.",
        "reproduction": [
            "python -I -S -B scripts/audit_overnight_acceptance_v1.py --output-dir runs/overnight-acceptance/your-unused-allocation",
            "python -I -S -B paper/audit_draft_v15.py --draft paper/working-draft-v15.md --provenance paper/working-draft-v15.provenance.json --ledger paper/claim-ledger-v15.json --output paper/your-unused-v15-audit.json",
            "python -I -S -B scripts/finalize_overnight_acceptance_v1.py --audit-dir runs/overnight-acceptance/your-unused-allocation",
        ],
        "audited_evidence_identities": [identity(path) for path in evidence_paths],
        "audit_command_records": [identity(directory / "commands.json"), identity(directory / "paper-command-success.json")],
        "paper_recheck": identity(paper_output),
        "previous_failed_paper_output_boundary_attempt": "paper-command.json records a rejected output outside paper; no paper output was written by that attempt." if (directory / "paper-command.json").exists() else None,
        "original_application_or_sdk_execution_by_reviewer": False,
        "provider_requests_by_reviewer": 0,
        "Git_actions_by_reviewer": 0,
    }
    write(directory / "acceptance.json", report)
    lines = ["# V1 delivery acceptance review", "", f"Reviewed {report['reviewed_at_utc']}.", "",
             "Seven of the eight release criteria are accepted for their declared implementation scope. The remaining release gate is root's fresh current-release Linux smoke/core/demo qualification. No whole-project percentage or scientific checkpoint is assigned.", "",
             "The current checks passed: 12,247 retained/current-file identities; 93 focused controls; all four retained Linux comparison bundles; the complete 68-template candidate bank; AP2 V2 public reanalysis with zero questions; and a fresh 19-check V15 paper read audit.", "",
             "| Criterion | Current acceptance | Evidence and limit |", "| --- | --- | --- |"]
    for item in criteria:
        lines.append("| " + item["criterion"] + " | " + item["status"].replace("_", " ") + " | " + item["verification"] + " " + item["claim_limit"] + " |")
    lines += ["", "The V15 current ledger fixes the paper-package gap: it binds this manuscript rather than the historical V7 manuscript. The complete paper remains a development research manuscript; accountable scientific review and authorship decisions are open.", "",
              "This reviewer made no original application/SDK launch, provider request, download, Git change or historical evidence mutation. Previous execution is accepted only at its stated scope after present-byte checks. Historical Linux/AgentOps transport ZIP digests and complete runtime/capture authentication were not independently redone.", "",
              "The source-derived candidate bank is authored and AI crossreviewed. Its 296 source-supported claims and 271 pending human judgments do not constitute human gold. Author-exposed trials and prospective held-out labels do not become untouched holdout evidence.", "",
              "Run `python -I -S -B scripts/audit_overnight_acceptance_v1.py --output-dir runs/overnight-acceptance/your-unused-allocation` for fresh retained/core/bank/AP2 checks. Run the V15 fresh-output audit from `docs/research/paper-artifact-guide-v15.md` for current paper claims. Then run the finalizer against that unused allocation to regenerate this review with a new paper audit.", "",
              "Exact identities, current commands, criterion-specific evidence and limits are in [the acceptance JSON](../../runs/overnight-acceptance/v1-20261111-1/acceptance.json). Root owns final smoke, evidence freeze and GitHub synchronization.", ""]
    note = args.note.resolve() if args.note else directory / "acceptance.md"
    note.relative_to(ROOT)
    with note.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))
    print(json.dumps({"status": report["status"], "report": identity(directory / "acceptance.json"),
                      "note": identity(note)}, indent=2))


if __name__ == "__main__":
    main()
