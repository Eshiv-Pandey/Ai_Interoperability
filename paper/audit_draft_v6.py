"""Audit preserved manuscript claims and already executed AP2 admission evidence."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import importlib.util
import json
import hashlib
import traceback

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "paper" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def audit():
    previous = module("audit_draft_v5")
    inherited = previous.audit()
    builder = module("build_draft_v6")
    draft_path = ROOT / "paper/working-draft-v6.md"
    draft = draft_path.read_text(encoding="utf-8")
    require = previous.require
    load = previous.load
    record = previous.record
    ledger = load(ROOT / "paper/claim-ledger-v6.json")
    require(builder.build() == draft and ledger["draft"] == record(draft_path), "Preserved-v5 transformation/binding")
    require(ledger["builder"] == record(ROOT / "paper/build_draft_v6.py"), "Builder changed")
    for item in ledger["evidence"]:
        require(record(ROOT / item["path"]) == item, "Changed new claim evidence: " + item["path"])
    semantic = load(ROOT / builder.SEMANTIC)
    signature = load(ROOT / builder.SIGNATURE)
    admission = semantic["shared_lift_admission"]
    require(semantic["status"] == "offline_original_application_and_checked_admission_verified"
            and signature["status"] == "completed_offline_original_app_admitted_sequence_independently_verified"
            and signature["run_id"] == "42858644500", "Actual successful admission/application audit absent")
    require(admission["decision"] == "supported" and admission["independent_certificate_valid"]
            and admission["certificate_kind"] == "recipe-path" and not admission["coverage_complete"]
            and not admission["whole_route_non_support_inference_allowed"], "Conditional positive scope")
    require(admission["evaluation_clock"] == admission["raw_dispatch_clock"] == 1794329502
            and admission["valid_until"] == 1794329517, "Clocks/expiry")
    require(admission["journal_prefix_before_admission"]["events"] == 114
            and admission["journal_prefix_before_admission"]["bytes"] == 234600
            and admission["raw_continuation_first_global_index"] == 115
            and admission["raw_continuation_exchange"] == 4
            and admission["same_actual_original_builder_and_raw_request"]
            and admission["admission_preceded_original_raw_continuation"], "Evidence before send")
    require(semantic["receipt"]["status"] == "Success" and semantic["receipt_reference_freshly_recomputed"]
            and semantic["same_original_merchant_and_processor_tasks_resumed"] and semantic["cleanup_verified"]
            and semantic["provider_requests"] == 0 and not semantic["native_qualification_established"], "Actual receipt/qualification")
    require([semantic[k] for k in ("durable_events_checked", "raw_exchanges_checked", "rpc_requests_checked", "original_source_files_checked")] == [168, 17, 12, 136], "Application counts")
    require(signature["files_checked"] == 182 and signature["actual_returncode"] == 0
            and signature["closed_clients"] == 5 and signature["fresh_buyer_root_signature_and_disclosure_checks"]
            and not signature["merchant_checkout_JWT_signature_rechecked"]
            and signature["fresh_positive_certificate_checks_at_admission_and_dispatch"]
            and signature["certificate_tamper_and_expired_clock_controls_rejected"], "Separate certificate/signature review")
    require(signature["admission_work_units"] == 427 and signature["positive_certificate_bytes"] == 10710, "Witness work/proof sizes")
    solver = load(ROOT / "runs/ap2-reference-development/v4/hosted-42858644500/extracted/application/admission/solver-result.json")
    require(solver["stats"]["work_units"] == 427 and len(previous.canonical(solver["certificate"])) == 10710, "Raw solver/certificate values")
    require(solver["stats"]["relation_checks"] == 1
            and solver["stats"]["relation_cache_hits"] == solver["stats"]["prefix_cache_hits"] == 0, "No claimed cache benefit")
    correspondence = load(ROOT / "runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/canonical-copy-correspondence.json")
    require(correspondence["same_file_union_and_bytes"] and correspondence["files_checked"] == 182
            and correspondence["canonical_raw_zip_sha256"] == correspondence["independent_raw_zip_sha256"]
            == "b169c88da578f70210b01e7e63578ab59ca7e8b236e3c334682053929066f7cf", "Two retained capture copies")
    for value in ("427", "10,710", "114-event", "234,600", "1794329502", "1794329517", "zero prefix/relation cache hits"):
        require(value in draft, "New reported value absent: " + value)
    guide = ROOT / "docs/research/paper-artifact-guide-v6.md"
    require(ledger["artifact_guide"] == record(guide), "Artifact guide binding")
    for source, text in ((draft_path, draft), (guide, guide.read_text(encoding="utf-8"))):
        for target in previous.re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            url = previous.urlparse(target)
            if url.scheme:
                require(url.scheme in ("https", "http") and url.netloc, "Malformed external link")
            else:
                path = (source.parent / previous.unquote(url.path)).resolve()
                require(path.is_relative_to(ROOT) and path.exists(), "Broken local link: " + target)
    status = load(ROOT / "paper/draft-status-v6.json")
    require(status["full_manuscript_drafted"] and not status["publication_ready"]
            and not status["original_research_validity_gates_complete"] and not status["human_scientific_review_claimed"], "Scientific completion conflation")
    governed = load(ROOT / "runs/ci-agentops-governed-app-pilot/hosted-42859288563-2/semantic-read-review-1.json")
    require(governed["status"] == "actual_completion_and_confirmation_pause_verified_with_preserved_strict_failures"
            and governed["strict_aggregate_passes"] == 0 and governed["strict_aggregate_cases"] == 2
            and governed["captured_files_hash_checked"] == 99 and governed["original_source_members_checked"] == 421, "Governed strict result/scope")
    cases = governed["cases"]
    require([(c["actual_SDK_state"], c["actual_model_calls"], c["actual_tool_calls"], c["durable_ADK_events"],
              c["original_strict_checks_passed"], c["original_strict_checks_total"]) for c in cases]
            == [("completed", 2, 1, 4, 35, 36), ("input-required", 5, 5, 12, 39, 40)], "Governed task/addendum counts")
    require(all(c["original_strict_status"] == "checks_failed" and c["preserved_failed_check"] == "no_network_attempts"
                and c["denied_socket_bind_attempts"] == 1 and c["business_state_unchanged"]
                and c["socket_bind_target_or_stack_attribution"] == "unknown: not captured" for c in cases), "Strict failure removed or attributed")
    addendum = (ROOT / "paper/agentops-governed-app-addendum-v1.md").read_text(encoding="utf-8")
    require("**0/2**" in addendum and "35/36" in addendum and "39/40" in addendum, "Addendum strict denominator")
    return {"status": "passed", "draft": record(draft_path), "guide": record(guide),
            "ledger": record(ROOT / "paper/claim-ledger-v6.json"), "audit_source": record(Path(__file__)),
            "inherited_v5_audit": {k: inherited[k] for k in ("raw_cells_reconstructed", "unknown_cells", "empirical_tables_checked", "references_checked")},
            "new_actual_AP2_admission_application_evidence_bound": True, "artifact_files": 182,
            "governed_app_cases_observed": 2, "governed_app_strict_passes": 0,
            "admission_work_units": 427, "certificate_bytes": 10710,
            "scope": "Read-only inherited-value and new executed-evidence audit; no fresh checker/signature/application/model execution or human review."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "paper") or output.exists():
        raise ValueError("Choose unused paper audit receipt")
    result = {"schema_version": "working-paper-value-audit/6", "status": "failed", "started_utc": datetime.now(timezone.utc).isoformat(),
              "new_solver_checker_application_or_model_calls": 0, "human_review": False}
    try:
        result.update(audit())
    except Exception as error:
        result.update(error=str(error), traceback=traceback.format_exc())
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "error": result.get("error"), "output": str(output)}))
    raise SystemExit(0 if result["status"] == "passed" else 1)
