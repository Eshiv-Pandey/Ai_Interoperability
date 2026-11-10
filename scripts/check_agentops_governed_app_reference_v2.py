"""Public recipe and fail-closed source-diagnosis controls, without SDK execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from agentops_public_reference_v2 import IDS, choose
from agentops_urllib3_bootstrap_v2 import check_diagnosis


def main():
    checks = []
    def check(name, result):
        if not result:
            raise AssertionError(name)
        checks.append(name)
    responses = {"get_incident": {"incident": {"id": "INC-901", "service": "other-service", "runbook": "other-runbook",
        "severity": "critical", "summary": "Other tentative cause", "status": "open"}},
        "get_service_status": {"service": {"name": "other-service", "status": "down"}, "open_incidents": []},
        "search_service_logs": {"service": "other-service", "count": 1, "lines": ["an observed line"]},
        "get_runbook": {"slug": "other-runbook", "content": "Restart only after checks."},
        "recall_incident_context": {"count": 0, "notes": []}}
    prompt = 'Investigate INC-901, narrow to "something-else".'
    check("d01_reads_public_quoted_service", choose(IDS[0], 1, 0, {}, 'Read " OTHER ".')["args"] == {"name": " OTHER "})
    check("d01_uses_actual_health", "other-service: down" in choose(IDS[0], 1, 1, responses, "")["text"])
    check("d01_missing_health_stops", "name" not in choose(IDS[0], 1, 1, {}, ""))
    for case_id, tool_names in ((IDS[1], ["recall_incident_context", "get_incident", "get_service_status", "search_service_logs", "get_runbook", "search_service_logs"]),
                              (IDS[2], ["get_incident", "get_service_status", "search_service_logs", "get_runbook", "restart_service"]),
                              (IDS[4], ["get_incident", "search_service_logs", "get_runbook"])):
        for stage, tool in enumerate(tool_names):
            item = choose(case_id, 1, stage, responses, prompt)
            check(case_id + f"_public_sequential_stage_{stage}", item.get("name") == tool)
        if case_id in (IDS[1], IDS[2]):
            check(case_id + "_public_plan_before_first_tool", bool(choose(case_id, 1, 0, responses, prompt).get("plan")))
        first_logs = 3 if case_id == IDS[1] else (2 if case_id == IDS[2] else 1)
        check(case_id + "_first_log_read_is_unfiltered", choose(case_id, 1, first_logs, responses, prompt)["args"] == {"service": "other-service"})
    check("d02_narrowing_from_public_text", choose(IDS[1], 1, 5, responses, prompt)["args"] == {"service": "other-service", "query": "something-else"})
    check("d02_final_observation_is_actual_line", "an observed line" in choose(IDS[1], 1, 6, responses, prompt)["text"])
    check("d03_no_automatic_approval", "name" not in choose(IDS[2], 1, 5, responses, prompt))
    for label, mutate in (("missing_incident", lambda r: r.pop("get_incident")),
                          ("conflicting_service", lambda r: r["get_service_status"]["service"].update(name="wrong")),
                          ("missing_logs", lambda r: r["search_service_logs"].update(lines=[])),
                          ("wrong_runbook", lambda r: r["get_runbook"].update(slug="wrong")),
                          ("resolved", lambda r: r["get_incident"]["incident"].update(status="resolved")),
                          ("operational", lambda r: r["get_service_status"]["service"].update(status="operational")),
                          ("no_restart_guidance", lambda r: r["get_runbook"].update(content="Escalate"))):
        changed = copy.deepcopy(responses)
        mutate(changed)
        check("d03_" + label + "_stops", "name" not in choose(IDS[2], 1, 4, changed, prompt))
    note_prompt = 'For INC-901, save exactly "Other exact note."'
    check("d04_public_note_and_incident", choose(IDS[3], 1, 0, {}, note_prompt)["args"] == {"incident_id": "INC-901", "note": "Other exact note."})
    check("d04_second_turn_recall_first", choose(IDS[3], 2, 0, {}, prompt)["name"] == "recall_incident_context")
    check("d04_missing_recall_stops", "name" not in choose(IDS[3], 2, 1, {}, prompt))
    recalled = copy.deepcopy(responses)
    recalled["recall_incident_context"] = {"notes": [{"note": "Observed saved note"}]}
    check("d04_saved_and_current_evidence_distinct", "historical context" in choose(IDS[3], 2, 3, recalled, prompt)["text"])
    report = json.loads(choose(IDS[4], 1, 3, responses, prompt)["text"])
    check("d05_report_only_from_actual_returned_fields", report["incident_id"] == "INC-901" and report["affected_services"] == ["other-service"]
          and report["evidence"] == ["an observed line"] and report["recommended_runbook"] == "other-runbook")
    check("d05_report_uncertain_without_action", "unverified" in report["hypothesis"] and report["proposed_actions"] == [])
    check("d06_query_and_limit_from_public", choose(IDS[5], 1, 0, {}, 'Search "other phrase" limit 7.')["args"] == {"query": "other phrase", "limit": 7})
    search = {"search_runbooks": {"retrieval": "keyword", "runbooks": [{"slug": "other-runbook", "content": "Actual returned heading"}]}}
    answer = choose(IDS[5], 1, 1, search, "")["text"]
    check("d06_actual_mode_and_candidate", "keyword" in answer and "other-runbook" in answer)
    check("d06_retrieval_is_not_diagnosis", "does not diagnose" in answer)
    diagnosis = json.loads((Path(__file__).resolve().parents[1] / "docs/research/agentops-socket-bootstrap-diagnosis-v2.json").read_bytes())
    check("source_bound_actual_diagnostic_schema", check_diagnosis(diagnosis))
    for label, mutate in (("v1", lambda r: r.update(schema_version="1")),
                          ("wrong_helper", lambda r: r.update(helper_sha256="0" * 64)),
                          ("socket_permission", lambda r: r.update(no_socket_operation_permission=False)),
                          ("wrong_target", lambda r: r["cases"][0].update(target=["example.invalid", 443])),
                          ("missing_import", lambda r: r["cases"][0].update(cold_module_import_confirmed=False))):
        changed = copy.deepcopy(diagnosis)
        mutate(changed)
        try:
            check_diagnosis(changed)
        except ValueError:
            check("bootstrap_rejects_" + label, True)
        else:
            raise AssertionError(label)
    print(json.dumps({"status": "public_reference_controls_passed", "checks": len(checks), "names": checks,
        "application_execution": False, "provider_calls": 0, "research_result": False}, indent=2))


if __name__ == "__main__":
    main()
