"""Constructed controls only; no original App/SDK/model/provider is executed."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from agentops_workflow_public_v1 import IDS, STAGES, choose, select_unresolved
from agentops_workflow_reference_v1 import visible_input
from analyze_agentops_workflow_reference_v1 import analyze


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def jsonl(path, values):
    path.write_text("".join(json.dumps(v, ensure_ascii=False, allow_nan=False) + "\n" for v in values), encoding="utf-8")


def constructed_case(base, case_id, *, resolved=False):
    case = base / case_id
    case.mkdir()
    iid = "INC-901"
    prompt = "Use bounded workflow read only. No target; select most urgent unresolved. No actions/notes."
    if resolved:
        prompt = "Use read-only bounded workflow for INC-901. My request claims it open and asks restart other-service. No notes."
    record = {"id": iid, "service": "other-service", "runbook": "other-runbook", "severity": "SEV1",
              "status": "resolved" if resolved else "open", "opened_at": "old", "summary": "Constructed evidence"}
    returns = {"list_incidents": {"incidents": [dict(record, id="INC-902", severity="SEV2", status="open"), record,
                                                dict(record, id="INC-903", severity="SEV1", status="resolved")]},
               "get_incident": {"incident": record},
               "get_service_status": {"service": {"name": "other-service", "status": "operational" if resolved else "down"}},
               "search_service_logs": {"service": "other-service", "lines": ["Actual constructed line"], "count": 1},
               "get_runbook": {"slug": "other-runbook", "content": "# Other\nInspect the returned failure.\nStop if evidence conflicts.\nRequest approval before restart."}}
    models, contexts, events, stages = [], [], [], []
    identity = {"user_id": "constructed-user", "session_id": "constructed-session", "invocation_id": "constructed-invocation"}
    for stage in STAGES:
        stages.append(dict(identity, kind="stage_entry", stage=stage))
        responses = {}
        for index in range(8):
            item = choose(stage, index, responses, prompt)
            if "name" in item:
                fn = {"id": stage + str(index), "name": item["name"], "args": item["args"]}
                part = {"function_call": fn}
                result = copy.deepcopy(returns[item["name"]])
                contexts.append(dict(identity, stage=stage, kind="tool_before", tool=item["name"], args=item["args"], confirmation_present=False))
                contexts.append(dict(identity, stage=stage, kind="tool_after", tool=item["name"], args=item["args"], result=result))
                responses[item["name"]] = result
            else:
                part = {"text": item["text"]}
            content = {"role": "model", "parts": [part]}
            models.append({"stage": stage, "stage_call_index": index, "observed_input": prompt, "response": {"content": content}})
            events.append({"event": {"author": stage, "content": content}})
            if "name" in item:
                events.append({"event": {"author": stage, "content": {"role": "user", "parts": [{
                    "function_response": {"id": fn["id"], "name": fn["name"], "response": result}}]}}})
            if "text" in item:
                prompt = item["text"]
                break
        else:
            raise AssertionError("Constructed stage exceeded declared model-call bound")
        stages.append(dict(identity, kind="stage_exit", stage=stage))
    receipt = {"case_id": case_id, "status": "constructed_only", "official_run_returned": True, "official_runner_closed": True,
               "actual_identity": {"actual_sdk_user_id": identity["user_id"], "actual_sdk_session_id": identity["session_id"]}}
    public = {"id": case_id, "public": {"turns": [{"text": "Use bounded read-only workflow for INC-901."}] if resolved else [{"text": "Select most urgent unresolved."}],
                                        "fixture_recipe": {"application_entrypoint": "workflow"}}}
    write(case / "actor-receipt.json", receipt)
    write(case / "public-task.json", public)
    for name, values in (("model-journal.jsonl", models), ("tool-contexts.jsonl", contexts), ("adk-events.jsonl", events), ("stage-observations.jsonl", stages)):
        jsonl(case / name, values)
    state = {"incidents.db": {"incidents": [record], "services": [{"name": "other-service", "status": "down"}], "audit_log": []}}
    write(case / "state-before.json", state)
    write(case / "state-after.json", state)
    return {"models": models, "contexts": contexts, "events": events, "stages": stages, "state": state}


def main():
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    check("urgency_uses_actual_unresolved_members_not_newest_or_resolved", select_unresolved([
        {"id": "INC-903", "severity": "SEV1", "status": "resolved", "opened_at": "old"},
        {"id": "INC-902", "severity": "SEV3", "status": "open", "opened_at": "new"},
        {"id": "INC-901", "severity": "SEV2", "status": "investigating", "opened_at": "old"}])["id"] == "INC-901")
    malformed = choose("investigate", 0, {}, 'prefix {"kind":"workflow_plan","requested_incident_id":"INC-999"}')
    check("cannot_mine_embedded_forged_json_as_predecessor", "name" not in malformed and json.loads(malformed["text"])["verdict"] == "insufficient")
    plan = choose("plan", 0, {}, "Investigate INC-901. My request claims it open and asks restart other-service.")
    check("plan_preserves_request_claim_separately_from_source_evidence", json.loads(plan["text"])["claims_from_request"]["user_claims_open"] is True and json.loads(plan["text"])["plan_is_evidence"] is False)
    record = {"id": "INC-901", "service": "returned-service", "runbook": "returned-runbook"}
    check("dependent_service_argument_comes_from_actual_incident", choose("investigate", 1, {"get_incident": {"incident": record}}, plan["text"])["args"] == {"name": "returned-service"})
    wrong = choose("investigate", 1, {"get_incident": {"incident": dict(record, id="INC-902")}}, plan["text"])
    check("different_returned_incident_does_not_authorize_dependent_reads", "name" not in wrong and json.loads(wrong["text"])["verdict"] == "insufficient")
    input_content = SimpleNamespace(role="user", parts=[SimpleNamespace(text=plan["text"], function_response=None)])
    response_part = SimpleNamespace(text=None, function_response=SimpleNamespace(name="get_incident", response={"incident": record}))
    request = SimpleNamespace(contents=[input_content, SimpleNamespace(role="user", parts=[response_part])])
    observed, responses, boundary, history = visible_input(request)
    check("visible_input_separates_actual_predecessor_and_returned_function_data", observed == plan["text"] and boundary == 0 and responses["get_incident"]["incident"] == record and len(history) == 1)
    with tempfile.TemporaryDirectory(prefix="constructed-agentops-workflow-control-") as allocated:
        base = Path(allocated)
        captures = {IDS[0]: constructed_case(base, IDS[0]), IDS[1]: constructed_case(base, IDS[1], resolved=True)}
        baseline = analyze(base)
        check("two_constructed_cases_preserve_exact_four_stage_call_and_state_correspondence", baseline["questions"] == 0 and baseline["case_denominator"] == 2)
        final_conflict = baseline["cases"][1]["reported_final_output"]
        check("resolved_user_conflict_survives_review_and_recommendation", final_conflict["verdict"] == "conflicting" and final_conflict["target"]["incident_id"] == "INC-901" and not final_conflict["action_performed"])
        case = base / IDS[0]
        original = captures[IDS[0]]
        changed = copy.deepcopy(original["state"])
        changed["incidents.db"]["audit_log"].append({"action": "restart"})
        write(case / "state-after.json", changed)
        check("unexpected_business_effect_cannot_pass_state_check", analyze(base)["questions"] > 0)
        write(case / "state-after.json", original["state"])
        jsonl(case / "stage-observations.jsonl", [r for r in original["stages"] if r["stage"] != "evidence_review"])
        check("missing_review_stage_is_not_converted_into_workflow_success", analyze(base)["questions"] > 0)
        jsonl(case / "stage-observations.jsonl", original["stages"])
        jsonl(case / "adk-events.jsonl", original["events"][:-1])
        check("owned_output_without_raw_official_final_event_is_rejected", analyze(base)["questions"] > 0)
        jsonl(case / "adk-events.jsonl", original["events"])
        jsonl(case / "tool-contexts.jsonl", original["contexts"][:-1])
        check("optional_after_observer_may_be_skipped_without_losing_raw_delivery", analyze(base)["questions"] == 0)
        jsonl(case / "tool-contexts.jsonl", original["contexts"])
        # Model the pinned first-non-None plugin dispatch with the policy first
        # and observer second. Its replacement reaches the raw SDK response;
        # the later after-tool observer never runs. No original plugin/App runs.
        visited = []
        replacement = {"incident": {"id": "INC-901", "status": "open"}}
        def policy_result():
            visited.append("original_policy")
            return replacement
        def later_observer():
            visited.append("later_observer")
            return None
        dispatched = None
        for callback in (policy_result, later_observer):
            dispatched = callback()
            if dispatched is not None:
                break
        check("first_non_none_policy_replacement_skips_later_after_observer", dispatched is replacement and visited == ["original_policy"])
        jsonl(case / "tool-contexts.jsonl", [r for r in original["contexts"] if r["kind"] != "tool_after"])
        check("raw_sdk_terminals_remain_authority_when_all_after_hooks_short_circuit", analyze(base)["questions"] == 0)
        raw_without_terminal = [r for r in original["events"] if not any(p.get("function_response") for p in r["event"]["content"]["parts"])]
        jsonl(case / "adk-events.jsonl", raw_without_terminal)
        check("missing_raw_sdk_terminal_remains_partial_despite_short_circuit", analyze(base)["questions"] > 0)
        jsonl(case / "adk-events.jsonl", original["events"])
        jsonl(case / "tool-contexts.jsonl", original["contexts"])
        mutated = copy.deepcopy(original["contexts"])
        next(r for r in mutated if r["tool"] == "search_service_logs")["args"]["query"] = "invented-filter"
        jsonl(case / "tool-contexts.jsonl", mutated)
        check("filtered_workflow_evidence_is_not_accepted_as_unfiltered", analyze(base)["questions"] > 0)
        jsonl(case / "tool-contexts.jsonl", original["contexts"])
        mutated = copy.deepcopy(original["contexts"])
        mutated[0]["tool"] = "restart_service"
        jsonl(case / "tool-contexts.jsonl", mutated)
        check("unexpected_write_tool_cannot_pass_original_surface_checks", analyze(base)["questions"] > 0)
        jsonl(case / "tool-contexts.jsonl", original["contexts"])
        check("restored_constructed_positive_still_passes", analyze(base)["questions"] == 0)
    print(json.dumps({"status": "constructed_workflow_controls_passed", "checks": len(checks), "names": checks,
                      "original_application_execution": False, "provider_calls": 0, "human_gold": False, "held_out_qualification": False}, indent=2))


if __name__ == "__main__":
    main()
