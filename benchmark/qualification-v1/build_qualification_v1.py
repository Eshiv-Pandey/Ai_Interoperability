"""Build candidate qualification proposals from retained text/JSON only.

This builder never imports an original application, actor, model, evaluator,
solver or checker. It never allocates, dispatches, writes retained evidence,
or qualifies gold. Its outputs are new review proposals.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
AG = Path("runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1")
AP = Path("runs/ap2-original-shopper-development/v7/retained-42886479185-1")


def read(path: Path | str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def jsonl(path: Path):
    return [json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines() if line]


def sha(path: Path | str):
    h = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(256 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def binding(path: Path | str, pointer: str = ""):
    path = Path(path)
    return {"path": path.as_posix(), "sha256": sha(path), "bytes": (ROOT / path).stat().st_size, "json_pointer": pointer}


def artifact_text(task):
    return [p["text"] for a in task.get("artifacts") or [] for p in a.get("parts") or [] if p.get("kind") == "text"]


def function_parts(events, field):
    return [p[field] for e in events for p in (e.get("content") or {}).get("parts") or [] if p.get(field)]


def agentops_raw(case_id, census):
    base = AG / "extracted" / case_id
    receipt = read(base / "actor-receipt.json")
    if census["retained_mechanical_status"] == "unsupported_public_recipe":
        assert receipt["tasks"] == [] and census["observed_SDK_tasks"] == 0
        return {"tasks": [], "actual_tool_calls": [], "business_state_unchanged": None,
                "provider_calls": receipt["provider_calls"], "unsupported_public_turns": receipt["unsupported_public_turns"],
                "unrealized_fixture_obligations": receipt["unrealized_obligations"], "evidence": [binding(base / "actor-receipt.json")],
                "scope": "No original task/runtime/state execution; unavailable snapshots are not inferred unchanged."}
    before, after = read(base / "state-before.json"), read(base / "state-after.json")
    contexts = jsonl(base / "tool-contexts.jsonl")
    raw_tasks, evidence = [], [binding(base / name) for name in ("actor-receipt.json", "state-before.json", "state-after.json", "tool-contexts.jsonl", "model-journal.jsonl")]
    for turn in receipt["tasks"]:
        path = base / f"turn-{turn['turn']}" / "task-get.response.raw.json"
        task = read(path)["result"]
        assert (task["id"], task["contextId"], task["status"]["state"]) == (turn["task_id"], turn["context_id"], turn["last_state"])
        raw_tasks.append({"turn": turn["turn"], "task_id": task["id"], "context_id": task["contextId"], "state": task["status"]["state"], "answer_text": artifact_text(task)})
        evidence.append(binding(path))
    assert len(raw_tasks) == census["observed_SDK_tasks"]
    business_unchanged = before.get("incidents.db") == after.get("incidents.db")
    assert business_unchanged == census["business_state_unchanged"]
    assert len(contexts) == census["tool_calls"]
    return {"tasks": raw_tasks, "actual_tool_calls": contexts, "business_state_unchanged": business_unchanged,
            "provider_calls": receipt["provider_calls"], "unsupported_public_turns": receipt["unsupported_public_turns"],
            "unrealized_fixture_obligations": receipt["unrealized_obligations"], "evidence": evidence}


def ap2_raw(process_id, peer):
    base = AP / "extracted/bank/cells" / process_id
    events = jsonl(base / "original-adk-events.jsonl")
    tools = jsonl(base / "adk-tool-capture.jsonl")
    conversation = jsonl(base / "human-conversation.jsonl")
    calls, responses = function_parts(events, "functionCall"), function_parts(events, "functionResponse")
    for capture in tools:
        observed = calls if capture["boundary"] == "before" else responses
        matches = [p for p in observed if p.get("id") == capture["function_call_id"] and p.get("name") == capture["name"]]
        assert len(matches) == 1, (process_id, capture["index"])
        if capture["boundary"] == "before":
            assert matches[0]["args"] == capture["args"]
        else:
            # get_shipping_address returns original ContactAddress model; the
            # callback serializes it as a dict, while ADK wraps the model result.
            expected = capture["result"] if isinstance(capture["result"], dict) and capture["name"] != "get_shipping_address" else {"result": capture["result"]}
            assert matches[0]["response"] == expected, (process_id, capture["index"], capture["name"], type(capture["result"]).__name__)
    state, before, after = read(base / "caller-final-state.json"), read(base / "original-state-before.json"), read(base / "original-state-after.json")
    outcome = read(base / "shopper-outcome.json")
    reference = read(base / "reference-result.json")
    original_calls = [c for c in calls if c["name"] != "transfer_to_agent"]
    assert [c["name"] for c in original_calls] == peer["original_tool_order"]
    assert len(events) == outcome["original_adk_events"]
    assert len([c for c in conversation if c["role"] == "user"]) == outcome["human_turns"]
    assert before["credential_tokens"] == before["merchant_store"] == {}
    assert before["private_signing_key_files"] == 0
    assert all(store["task_ids"] == [] for store in before["task_stores"].values())
    otp = [c for c in original_calls if c["name"] == "initiate_payment_with_otp"]
    receipt = state.get("payment_receipt")
    assert len(otp) == peer["otp_continuations"] == 0
    assert receipt is None and peer["actual_original_purchase_observed"] is False
    pending = [{"endpoint": r["endpoint"], "task_id": r["public_value"]["id"], "context_id": r["public_value"]["contextId"], "state": r["public_value"]["status"]["state"]}
               for r in reference["public_records"] if r["boundary"] == "returned" and isinstance(r.get("public_value"), dict) and r["public_value"].get("kind") == "task" and r["public_value"]["status"]["state"] == "input-required"]
    return {"process_id": process_id, "actual_original_tool_order": [c["name"] for c in original_calls], "official_adk_events": len(events),
            "actual_human_turns": outcome["human_turns"], "actual_payment_tool_return": outcome["original_payment_tool_return"],
            "terminal_reason": outcome["terminal_reason"], "otp_calls": len(otp), "original_purchase_observed": False,
            "fresh_before_stores": True, "pending_wire_tasks": pending, "selected_cart_id": state.get("chosen_cart_id"),
            "checkout_amount_cents": state.get("checkout_data", {}).get("amount_cents"),
            "checkout_currency": state.get("checkout_data", {}).get("currency"),
            "actual_credential_bindings": [{"token": key, "alias": value.get("payment_method_alias"), "transaction": value.get("payment_mandate_id")} for key, value in after["credential_tokens"].items()],
            "evidence": [binding(base / name) for name in ("original-adk-events.jsonl", "adk-tool-capture.jsonl", "human-conversation.jsonl", "caller-final-state.json", "original-state-before.json", "original-state-after.json", "shopper-outcome.json", "reference-result.json")]}


def build(second_instance_dir=None):
    notes = read("benchmark/qualification-v1/candidate-notes.json")
    ag_census_path = AG / "independent-raw-state-census-v1.json"
    ag_sem_path = AG / "independent-semantic-peer-review-v1.json"
    ap_peer_path = AP / "independent-raw-peer-review-v1.json"
    ap_eval_path = AP / "extracted/independent-bank-evaluation/result.json"
    ag_census = {r["case_id"]: r for r in read(ag_census_path)["cases"]}
    ag_sem = {r["case_id"]: r for r in read(ag_sem_path)["cases"]}
    ap_peer = {r["process_id"]: r for r in read(ap_peer_path)["processes"]}
    ap_eval = {r["candidate_id"]: r for r in read(ap_eval_path)["candidates"]}
    public, private, table, plans, inputs = [], [], [], [], []
    for domain in ("agentops", "ap2"):
        app_path, ev_path = [Path(f"benchmark/tasks-v1/{domain}/{name}.json") for name in ("application", "evaluator")]
        app, ev = read(app_path), read(ev_path)
        evaluator = {r["id"]: r for r in ev["records"]}
        inputs += [binding(app_path), binding(ev_path)]
        for index, record in enumerate(app["records"]):
            case_id = record["id"]
            expectation = evaluator[case_id]
            key = case_id.split("-", 2)[1] if domain == "agentops" else case_id.removeprefix("ap2-")
            answer, next_check = notes[domain][key]
            public.append({"id": case_id, "domain": domain, "split": record["split"], "template_family": record["template_family"], "public": record["public"]})
            execution_class = record["public"]["fixture_recipe"].get("execution_class", "original_governed_app")
            base = {"id": case_id, "domain": domain, "split": record["split"], "template_family": record["template_family"], "distinct_obligation": record["distinct_obligation"], "execution_class": execution_class,
                    "task_status": "authored_candidate_not_qualified", "human_review": "not_reviewed", "gold_status": "proposed_not_validated", "near_miss_status": "proposed_not_validated",
                    "held_out_status": "exposed_authoring_and_development_evidence_not_independent_holdout", "route_status": "all_three_study_paths_unqualified", "qualified": False}
            if domain == "agentops":
                census, semantic = ag_census[case_id], ag_sem[case_id]
                mechanical = census["retained_mechanical_status"]
                disposition = {"observed_reference_recipe": "fixed_reference_obligation_observed", "observed_partial_reference_recipe": "partial_case", "unsupported_public_recipe": "bounded_unsupported_workflow", "checks_failed": "failed_reference_checks"}[mechanical]
                if case_id == "agentops-d03-restart-pause":
                    disposition = "partial_decision_preconditions"
                raw = agentops_raw(case_id, census)
                observed = {"historical_mechanical_status": mechanical, "semantic_status": semantic["semantic_disposition"], "failed_checks": census.get("preserved_failed_checks", []), "raw_summary": raw,
                            "peer_bindings": [binding(ag_census_path, f"/cases/{index}"), binding(ag_sem_path, f"/cases/{index}")]}
                gaps = list(semantic["unrealized_fixture_obligations"]) + [r["reason"] for r in semantic["unsupported_public_turns"]] + census.get("preserved_failed_checks", [])
                if case_id == "agentops-d03-restart-pause":
                    gaps.append("Observed down/crash-loop symptoms do not establish runbook understood cause and dependency/configuration, deploy/image or resource checks.")
            else:
                result = ap_eval[case_id]
                mechanical = result["disposition"]
                disposition = {"candidate_source_obligation_observed_pending_human_gold": "fixed_reference_obligation_observed", "candidate_original_reset_pair_obligation_observed": "fixed_reference_reset_pair_observed", "candidate_required_otp_receipt_or_fault_branch_unrealized_after_original_generic_status": "partial_case", "prior_original_sdk_source_boundary_observed_not_new_full_shopper": "boundary_only"}[mechanical]
                raw = [ap2_raw(r["id"], ap_peer[r["id"]]) for r in result.get("processes", [])]
                observed = {"historical_mechanical_status": mechanical, "raw_summaries": raw, "peer_bindings": [binding(ap_eval_path, f"/candidates/{index}"), binding(ap_peer_path)]}
                if result.get("prior_case") is not None:
                    prior = read(AP / "extracted/bank/prior-source-boundary-actor-output.json")
                    actual_prior = next(r for r in prior["cases"] if r["id"] == case_id)
                    assert actual_prior == result["prior_case"] and prior["provider_requests"] == 0 and prior["full_shopper_workflow_completed"] is False
                    observed["prior_source_boundary_observation"] = result["prior_case"]
                    observed["raw_prior_binding"] = binding(AP / "extracted/bank/prior-source-boundary-actor-output.json")
                gaps = []
                if disposition == "partial_case":
                    gaps.append("Complete original prefix ends at generic input_required before the required candidate-specific OTP/receipt/fault branch; no human OTP or shopper purchase observed.")
                if disposition == "boundary_only":
                    gaps.append("Executed direct original source-boundary control is not a full shopper task; comparable main-study scope remains unresolved.")
            base.update({"disposition": disposition, "reference": observed, "candidate_specific_gaps": list(dict.fromkeys(gaps)), "next_reference_check": next_check,
                         "common_gaps": ["Independent semantic/feasibility human review and validated proposed answer/near misses.", "Source-to-model fidelity and unchanged native/provider route qualification.", "Two independently implemented supported bridge paths and one/two/three crossing placements.", "Two independently reviewed instance recipes per held-out template; exposed candidates cannot become untouched held-out gold."]})
            table.append(base)
            private.append({"id": case_id, "domain": domain, "gold_status": "proposed_not_validated", "proposed_answer": answer,
                            "answer_contract": {k: expectation[k] for k in ("expected_facts", "expected_order", "expected_state", "reset", "legitimate_alternatives", "near_misses")},
                            "source_refs": expectation["source_refs"], "source_record_binding": binding(ev_path, f"/records/{index}"), "human_review": "not_reviewed"})
            plans.append({"id": case_id, "mode": "source_bound_next_reference_plan_only", "execution_class": execution_class,
                          "public_record_id": case_id, "proposed_check": next_check, "expected_answer_record_id": case_id,
                          "allocation": None, "execution_allowed": False, "requires_owner_coordination_before_new_allocation": True,
                          "required_retention": ["fresh exclusive allocation and exact source/config/recipe hashes", "full original request/response/events and actual owner/task/session/invocation identities", "before/after closed state with attributed writer cleanup", "all outcomes, errors, unsupported and unexecuted branches"],
                          "reference_limits": "Original public application/tool/entrypoint restrictions remain unchanged; direct boundary controls cannot replace full original workflows."})
    held_out = [r for r in public if r["split"] == "held_out"]
    assert len(held_out) == 48
    second_outputs = {}
    second_records = {}
    if second_instance_dir is not None:
        for name in ("second-instance-application.json", "second-instance-evaluator-private.json", "second-instance-source-checks.json"):
            second_outputs[name] = read(second_instance_dir / name)
        second_outputs["second-instance-review.md"] = (ROOT / second_instance_dir / "second-instance-review.md").read_text(encoding="utf-8")
        second_records = {r["candidate_id"]: r for r in second_outputs["second-instance-application.json"]["records"]}
        assert set(second_records) == {r["id"] for r in held_out}
        inputs += [binding(second_instance_dir / name) for name in ("second-instance-application.json", "second-instance-evaluator-private.json", "second-instance-source-checks.json")]
    slots = []
    for row in held_out:
        for ordinal in (1, 2):
            slots.append({"id": f"{row['id']}--instance-{ordinal}", "candidate_id": row["id"], "domain": row["domain"], "instance_ordinal": ordinal,
                          "recipe_status": "authored_base_recipe_pending_independent_review" if ordinal == 1 else "second_source_bound_instance_recipe_not_authored",
                          "public_record_id": row["id"] if ordinal == 1 else None, "qualified": False, "execution_allowed": False})
            if ordinal == 2 and second_records:
                second = second_records[row["id"]]
                slots[-1].update(recipe_status=second["status"], public_record_id=second["id"] if second["public"] is not None else None,
                                 specific_blocker=second["specific_blocker"], source_instance_projection="second-instance-application.json")
    paths = ["native_reference", "independent_bridge_1", "independent_bridge_2"]
    cells = [{"id": f"{s['id']}--{p}", "instance_id": s["id"], "path": p, "route_binding": None, "crossing_placement": None, "status": "blocked_pending_route_task_gold_freeze", "execution_allowed": False} for s in slots for p in paths]
    crossing_slots = [{"id": f"crossing-subset-{i:02}", "instance_id": None, "status": "prospective_subset_selection_pending_route_eligibility_before_outcomes"} for i in range(1, 25)]
    crossings = [{"id": f"{s['id']}--{p}--count-{n}", "subset_slot": s["id"], "path": p, "crossing_count": n, "composed_route_binding": None, "status": "blocked_pending_supported_placement_and_prespecified_subset", "execution_allowed": False} for s in crossing_slots for p in paths[1:] for n in (2, 3)]
    scope = {"original_candidates": 68, "split_counts": {"development": 12, "calibration": 8, "held_out": 48}, "held_out_task_slots": 96, "path_cells": 288, "additional_crossing_cells": 96, "initial_episode_slots": 384,
             "qualified_tasks": 0, "independent_held_out_tasks": 0, "allocation_is_executable_study": False,
             "scope_rule": "All candidates and original study slots retained. Unauthored instances, unselected crossing subset and unqualified paths are explicit gaps, not completed episodes or permission to shrink scope."}
    inputs += [binding(ag_census_path), binding(ag_sem_path), binding(ap_peer_path), binding(ap_eval_path), binding("benchmark/qualification-v1/candidate-notes.json"), binding("docs/research/student-budget-experiment-design.md")]
    for path in (AG, AP):
        expected = read(path / "retention.json")
        archive = binding(path / "artifact.zip")
        assert archive["sha256"] == expected["archive_sha256"] and archive["bytes"] == expected["archive_bytes"]
        inputs += [archive, binding(path / "retention.json")]
    envelope = {"schema_version": "candidate-qualification/1", "as_of": "2026-11-11", "authorship": "AI-authored retained-evidence review proposal; not independent human gold", "scope": scope, "inputs": inputs}
    outputs = {
        "application.json": {"schema_version": "qualification-public-projection/1", "projection": "application-only exact authored public inputs", "records": public},
        "evaluator-private.json": {"schema_version": "qualification-proposed-private-gold/1", "projection": "evaluator-only proposed answers, source obligations, alternatives and near misses; not for model/runtime discovery", "gold_status": "proposed_not_validated", "records": private},
        "candidate-table.json": {**envelope, "disposition_counts": dict(collections.Counter(r["disposition"] for r in table)), "records": table},
        "next-reference-plan.json": {"schema_version": "source-bound-next-reference-plan/1", "provider_calls_allowed": 0, "dispatch_allowed": False, "new_allocations_authorized_by_this_file": False, "records": plans},
        "study-allocation.json": {"schema_version": "preserved-study-allocation/1", "scope": scope, "task_slots": slots, "path_cells": cells, "crossing_subset_slots": crossing_slots, "crossing_cells": crossings},
    }
    instance_text = "48 second-instance recipes remain unauthored" if not second_records else "25 second-instance source recipes are authored and 23 slots have specific refusals; all remain exposed/unqualified"
    md = ["# Candidate qualification table v1", "", "11 November 2026. All 68 AI-authored candidates were joined to exact source/evaluator records and retained AgentOps v4/AP2 v7 evidence. The builder reads text/JSON and performs no original application, actor, model, evaluator, solver or checker calls. All answers and near misses remain proposed and human-unreviewed; all study routes remain unqualified.", "", "The historical AgentOps 20/10/2/2 census is preserved. A separate semantic distinction leaves 19 fixed reference obligations and one partially supported decision (d03). AP2 has eight observed early/source obligations, one reset pair, 19 unrealized later branches and six prior boundary-only controls. These are task-level review dispositions, not full-domain or held-out qualification.", "", f"The [private answer rows](evaluator-private.json) contain concrete proposed answers and exact source obligations, alternatives and near misses. [Public rows](application.json) preserve original public inputs. [Next checks](next-reference-plan.json) are a disabled execution plan requiring owner coordination. [Allocation](study-allocation.json) preserves 96 task slots, 288 path cells and 96 crossing cells; {instance_text}. All route/crossing bindings remain unqualified.", "", "| Candidate | Reference disposition | Concrete next check |", "| --- | --- | --- |"]
    for row in table:
        md.append(f"| {row['id']} | {row['disposition']} | {row['next_reference_check'].replace('|', '/')} |")
    outputs["candidate-table.md"] = "\n".join(md) + "\n"
    packet = ["# Minimal human-review packet v1", "", "Review concrete [public task/fixture rows](application.json), [same-id proposed answer/source/alternative/near-miss rows](evaluator-private.json) and [retained outcome/gap table](candidate-table.json). All 68 remain not_reviewed. This packet records no approval and asks no human to endorse aggregate counts as gold.", "", "For each candidate record, enter: reviewer identity/date; source feasibility; proposed-answer correct/needs revision/uncertain; meaningful alternative and near-miss acceptance; fixture/reset/allowed-state limits; distinctness family; comparable whole-task versus boundary-only scope; and a decision with rationale. A second independent human assessment and disagreement record are required before gold freeze. The assistant's retained-evidence review does not supply either human assessment.", "", "Resolve these concrete decisions first:", "", "1. AgentOps d03 and related restart recipes: the actual down/crash-loop prefix lacks runbook decision preconditions. Accept refusal/escalation as the bounded answer or request a separately source-supported fixture; retain the original proposal observation.", "2. AgentOps h09/h10: keep the unchanged four-stage workflow obligations. Current harness support is absent; a conversational substitute cannot qualify them.", "3. AgentOps h20/h21: distinguish unsupported same-invocation replay from a real new invocation and independently judge second-action support. Never convert refusal or unsupported delivery into an executed audit.", "4. AP2's 19 later-branch tasks: approve expected predicates only as proposed specifications; the shared generic input_required prefix has not realized them. Original user-facing continuation remains a runtime gate.", "5. AP2 h019-h024: decide comparable full-study scope for six direct source-boundary controls, including separately routed DPC. Keep all candidates and scientific transfer requirements until a versioned decision; boundary evidence is not purchase completion.", f"6. Instance and independence freeze: there are 48 authored base fixtures in the 96 planned held-out slots; {instance_text}. The authored and observed candidates are development exposure. Approve a prospective independent instance/review protocol before any held-out use.", "", "No review request, message, issue, pull request or experiment was sent by this packet. Route/model, resource, source-to-model and bridge qualification remain technical work, not questions a reviewer can waive by approving answer text.", "", "| Candidate | Concrete proposed answer, not validated gold |", "| --- | --- |"]
    for row in private:
        packet.append(f"| {row['id']} | {row['proposed_answer'].replace('|', '/')} |")
    if second_records:
        packet += ["", "The [second-instance review rows](second-instance-review.md) show all 48 slot decisions and the 25 concrete proposed second-instance answers. Refused slots contain a specific blocker and no invented completion answer.", ""]
    outputs["human-review-packet.md"] = "\n".join(packet)
    outputs.update(second_outputs)
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh proposal directory; existing files refuse before writes")
    parser.add_argument("--second-instance-dir", type=Path)
    args = parser.parse_args()
    outputs = build(args.second_instance_dir)
    target = args.output_dir.resolve()
    if target.exists():
        raise SystemExit("Output directory must be fresh; retained/review artifacts are never overwritten")
    target.mkdir(parents=True, exist_ok=False)
    for name, value in outputs.items():
        text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        with (target / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    print(json.dumps({"output": str(target), "files": len(outputs), "candidates": 68, "held_out_task_slots": 96, "qualified_tasks": 0}))


if __name__ == "__main__":
    main()
