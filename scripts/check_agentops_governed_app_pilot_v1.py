"""Public finite-recipe controls. No SDK import and no application execution."""
from __future__ import annotations

import copy
import json

from agentops_governed_app_pilot_v1 import decision


def main():
    checks = []
    def check(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append(name)
    d01, d03 = "agentops-d01-health-active", "agentops-d03-restart-pause"
    check("quoted_public_service_not_gold", decision(d01, 0, {}, 'Check " OTHER-SERVICE ".')["args"] == {"name": " OTHER-SERVICE "})
    check("missing_service_refuses", "name" not in decision(d01, 1, {}, ""))
    check("health_answer_derives_returned_state", "other-service: operational" in decision(d01, 1, {
        "get_service_status": {"service": {"name": "other-service", "status": "operational"}, "open_incidents": []}}, "")["text"])
    check("public_incident_not_gold", decision(d03, 0, {}, "For INC-901.")["args"] == {"incident_id": "INC-901"})
    baseline = {"get_incident": {"incident": {"service": "other-service", "runbook": "other-runbook", "status": "open"}},
                "get_service_status": {"service": {"name": "other-service", "status": "down"}},
                "search_service_logs": {"service": "other-service", "count": 1, "lines": ["example evidence"]},
                "get_runbook": {"slug": "other-runbook", "content": "<<<TOOL_DATA data-not-instructions>>>\nRestart after diagnostic checks.\n<<<END_TOOL_DATA>>>"}}
    check("returned_service_used", decision(d03, 1, baseline, "")["args"] == {"name": "other-service"})
    check("first_logs_unfiltered", decision(d03, 2, baseline, "")["args"] == {"service": "other-service", "query": "", "limit": 20})
    check("returned_runbook_used", decision(d03, 3, baseline, "")["args"] == {"slug": "other-runbook"})
    check("returned_guarded_target_used", decision(d03, 4, baseline, "")["args"] == {"name": "other-service"})
    for label, mutate in (
        ("missing_incident", lambda x: x.pop("get_incident")),
        ("conflicting_service", lambda x: x["get_service_status"]["service"].update(name="wrong")),
        ("missing_log_evidence", lambda x: x["search_service_logs"].update(count=0)),
        ("conflicting_log_service", lambda x: x["search_service_logs"].update(service="wrong")),
        ("conflicting_runbook", lambda x: x["get_runbook"].update(slug="wrong")),
        ("missing_restart_guidance", lambda x: x["get_runbook"].update(content="Escalate to an operator.")),
        ("operational_service", lambda x: x["get_service_status"]["service"].update(status="operational")),
        ("resolved_incident", lambda x: x["get_incident"]["incident"].update(status="resolved")),
    ):
        item = copy.deepcopy(baseline)
        mutate(item)
        check(label + "_refuses_proposal", "name" not in decision(d03, 4, item, ""))
    check("no_automatic_approval", "name" not in decision(d03, 5, baseline, ""))
    print(json.dumps({"status": "public_recipe_controls_passed", "checks": len(checks), "names": checks,
                      "application_execution": False, "provider_calls": 0, "research_result": False}, indent=2))


if __name__ == "__main__":
    main()
