"""Added public recipe/fixture safeguards, without SDK or application execution."""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile

from agentops_public_reference_v4 import IDS, choose
from agentops_public_fixture_v4 import apply_data


def main():
    checks = []
    def check(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append(name)
    public = json.loads((Path(__file__).resolve().parents[1] / "benchmark/tasks-v1/agentops/application.json").read_bytes())
    check("all34original_ids_retained_once", len(IDS) == len(set(IDS)) == 34 and set(IDS) == {r["id"] for r in public["records"]})
    example = {"id": "INC-901", "service": "other-service", "runbook": "other-runbook", "status": "open", "severity": "SEV1", "opened_at": "2026-01-01", "summary": "Other actual evidence"}
    results = {"get_incident": {"incident": example}, "get_service_status": {"service": {"name": "other-service", "status": "down"}},
        "search_service_logs": {"service": "other-service", "count": 1, "lines": ["observed pool line"]}, "get_runbook": {"slug": "other-runbook", "content": "Observed runbook"},
        "recall_incident_context": {"notes": [], "count": 0}}
    for short in ("h03", "h04", "h05", "h06", "h07"):
        case_id = next(i for i in IDS if i.split("-")[1] == short)
        for call, name in enumerate(("recall_incident_context", "get_incident", "get_service_status", "search_service_logs", "get_runbook")):
            check(short + "_public_sequential_" + str(call), choose(case_id, 1, call, results, "Investigate INC-901, autovacuum never-seen-marker-abc.").get("name") == name)
    h04 = next(i for i in IDS if "h04-" in i)
    check("h04_narrows_only_public_text_after_unfiltered_read", choose(h04, 1, 5, results, "INC-901 autovacuum")["args"] == {"service": "other-service", "query": "autovacuum"})
    h08 = next(i for i in IDS if "h08-" in i)
    missing = dict(results, search_service_logs={"error": "Actual missing log error"})
    report = json.loads(choose(h08, 1, 3, missing, "INC-901")["text"])
    check("h08_report_uses_actual_missing_log_error", report["incident_id"] == "INC-901" and report["evidence"] == ["Observed tool error: Actual missing log error"] and report["proposed_actions"] == [])
    h01 = next(i for i in IDS if "h01-" in i)
    check("h01_discovery_precedes_skill_load", choose(h01, 1, 0, {}, "")["name"] == "list_skills")
    check("h01_absent_skill_stops", "name" not in choose(h01, 1, 1, {}, ""))
    rank = {"list_skills": {"result": "incident-triage"}, "load_skill": {"result": "actual instructions"},
        "list_incidents": {"incidents": [example, dict(example, id="INC-902", service="second-service"), dict(example, id="INC-903", status="resolved")]}}
    check("h01_requires_leading_current_health", choose(h01, 1, 3, rank, "")["args"] == {"name": "other-service"})
    rank["_observed_history"] = [{"name": "get_service_status", "response": {"service": {"name": "other-service", "status": "operational"}}}]
    check("h01_requires_second_tied_current_health", choose(h01, 1, 4, rank, "")["args"] == {"name": "second-service"})
    rank["_observed_history"].append({"name": "get_service_status", "response": {"service": {"name": "second-service", "status": "down"}}})
    ranking = choose(h01, 1, 5, rank, "")["text"]
    check("h01_actual_health_breaks_tie_without_resolved_member", ranking.index("INC-902") < ranking.index("INC-901") and "INC-903" not in ranking)
    h17 = next(i for i in IDS if "h17-" in i)
    check("h17_target_is_returned_service", choose(h17, 1, 2, results, "INC-901")["args"] == {"name": "other-service"})
    check("h17_requires_actual_policy_refusal", "name" not in choose(h17, 1, 3, results, "INC-901"))
    refused = dict(results, restart_service={"error": "Observed writes-disabled refusal"})
    check("h17_reports_observed_policy_refusal", "Observed writes-disabled refusal" in choose(h17, 1, 3, refused, "INC-901")["text"])
    h24 = next(i for i in IDS if "h24-" in i)
    check("h24_note_argument_comes_from_governed_visible_text", choose(h24, 1, 0, {}, 'Save INC-901: "Operational note; [REDACTED]"')["args"]["note"] == "Operational note; [REDACTED]")
    with tempfile.TemporaryDirectory(prefix="agentops-public-fixture-control-") as allocated:
        base = Path(allocated)
        data, case = base / "copied-data", base / "case"
        data.mkdir(); case.mkdir(); (data / "logs").mkdir()
        (data / "logs/inventory.log").write_text("old line\n")
        with closing(sqlite3.connect(data / "incidents.db")) as connection, connection:
            connection.execute("CREATE TABLE incidents(id TEXT, severity TEXT, opened_at TEXT, status TEXT)")
            connection.execute("INSERT INTO incidents VALUES('INC-901','SEV2','old','open')")
        fixture = {"public": {"fixture_recipe": {"configuration": {"AGENT_WRITES_DISABLED": "false"}, "before_start_changes": [
            {"kind": "sqlite_row_update", "table": "incidents", "where": {"id": "INC-901"}, "set": {"severity": "SEV1"}},
            {"kind": "append_utf8_line", "path": "logs/inventory.log", "text": "new declared line"}]}}}
        result = apply_data(case, data, fixture)
        check("public_declared_fixture_applied_only_to_copy", result["applied_changes"] == fixture["public"]["fixture_recipe"]["before_start_changes"] and (data / "logs/inventory.log").read_text() == "old line\nnew declared line\n")
    print(json.dumps({"status": "added_full_bank_public_controls_passed", "checks": len(checks), "names": checks,
        "application_execution": False, "provider_calls": 0, "qualified_bank_tasks": 0}, indent=2))


if __name__ == "__main__":
    main()
