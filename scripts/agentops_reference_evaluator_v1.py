"""Private component evaluator using seed SQL/log/runbook bytes, not actor tools.

Successful component evidence never promotes an unexecuted original App task
to a pass. Gold/answer feasibility and scientific independence remain separate.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re
import sqlite3


IDS = ("agentops-d01-health-active", "agentops-d02-logs-after-record",
       "agentops-d03-restart-pause", "agentops-d04-note-same-session",
       "agentops-d05-structured-inventory", "agentops-d06-keyword-retrieval")


def seed_gold(data_dir):
    data_dir = Path(data_dir)
    connection = sqlite3.connect(f"{(data_dir / 'incidents.db').resolve().as_uri()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        tables = {name: [dict(row) for row in connection.execute('SELECT * FROM "' + name + '" ORDER BY rowid')]
                  for name in ("services", "incidents", "audit_log")}
    finally:
        connection.close()
    logs = {path.stem: path.read_text(encoding="utf-8").splitlines()
            for path in (data_dir / "logs").glob("*.log")}
    runbooks = {path.stem: path.read_text(encoding="utf-8")
                for path in (data_dir / "runbooks").glob("*.md")}
    # Independent arithmetic over pinned texts, sharing no AgentOps tool code.
    terms = [term for term in re.findall("[a-z0-9]+", "uptime heap leak") if len(term) >= 3]
    scored = []
    for slug, content in runbooks.items():
        value = sum(content.lower().count(term) * len(runbooks) /
                    sum(term in other.lower() for other in runbooks.values())
                    for term in terms if any(term in other.lower() for other in runbooks.values()))
        value += sum(len(runbooks) * 5 for term in terms if term in slug)
        if value > 0:
            scored.append((value, slug))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return {"tables": tables, "logs": logs, "runbooks": runbooks,
            "retrieval_expected": [{"slug": slug, "content": runbooks[slug]} for _, slug in scored[:2]]}


def grade(observed, gold, profile="minimal_reads"):
    checks = []

    def check(label, condition):
        checks.append({"obligation": label, "status": "verified" if condition else "failed"})

    selected = observed.get("id")
    minimal = profile == "minimal_reads"
    check("six-existing-development-ID", selected in IDS)
    check("planned-component-profile", observed.get("component_profile") == profile)
    check("unknown-unexecuted-original-App", observed.get("original_app_executed") is False
          and observed.get("full_application_result") == "unknown" and observed.get("model_requests") == 0)
    check("private-gold-probe-and-no-offline-denials", observed.get("private_evaluator_probe_blocked") is True
          and observed.get("denials") == {"private_reads_blocked": 1, "network_operations_blocked": 0,
                                         "process_launches_blocked": 0})
    before, after = observed.get("before_state", {}), observed.get("after_state", {})
    check("initial-business-state-is-pinned-seed", before.get("incidents.db") == gold["tables"])
    check("business-state-unchanged", after.get("incidents.db") == before.get("incidents.db"))
    check("initial-note-store-absent", before.get("memory.db") is None)
    if selected != IDS[3] or minimal:
        check("no-note-store-created", after.get("memory.db") is None)
    if minimal:
        identity = observed.get("identity", {})
        check("no-invented-SDK-identity-for-unexecuted-context", identity.get("actual_sdk_user_id") is None
              and identity.get("actual_sdk_session_id") is None and identity.get("sdk_session_created") is False
              and identity.get("invocations") == [])
    rows = observed.get("trace", [])
    check("trace-sequence-contiguous", [row.get("sequence") for row in rows] == list(range(1, len(rows) + 1)))
    execution = [row for row in rows if row.get("operation") != "public_user_turns"]
    actual_order = [row.get("operation") for row in execution]
    orders = {
        IDS[0]: ["agent.tools.get_service_status"],
        IDS[1]: ["agent.longterm.recall_incident_context", "agent.tools.get_incident", "agent.tools.get_service_status",
                 "agent.tools.search_service_logs", "agent.memory.get_runbook", "agent.tools.search_service_logs"],
        IDS[2]: ["agent.tools.get_incident", "agent.tools.get_service_status", "agent.tools.search_service_logs",
                 "agent.memory.get_runbook", "agent.actions.ACTION_TOOLS[0].run_async"],
        IDS[3]: ["agent.longterm.save_incident_note.sdk_function_tool", "agent.longterm.recall_incident_context"],
        IDS[4]: ["agent.tools.get_incident", "agent.tools.search_service_logs", "agent.memory.get_runbook",
                 "agent.models.TriageReport.model_json_schema"],
        IDS[5]: ["agent.memory.search_runbooks"],
    }
    missing = []
    if minimal:
        orders[IDS[1]] = orders[IDS[1]][1:]
        orders[IDS[2]] = orders[IDS[2]][:-1]
        orders[IDS[3]] = []
        missing = {
            IDS[1]: ["original same-user incident recall before investigation"],
            IDS[2]: ["actual original guarded SDK restart request and confirmation boundary"],
            IDS[3]: ["original PII-backed note write and real same-session subsequent recall"],
        }.get(selected, [])
    check("unexecuted-components-explicitly-unknown", observed.get("unexecuted_component_obligations") == missing)
    check("ordered-original-component-recipe", actual_order == orders.get(selected))
    incident_by_id = {row["id"]: row for row in gold["tables"]["incidents"]}
    service_by_name = {row["name"]: row for row in gold["tables"]["services"]}
    incident_seen = None
    for row in execution:
        operation, args, result = row.get("operation"), row.get("arguments", {}), row.get("result", {})
        if operation == "agent.tools.get_incident":
            incident_seen = incident_by_id.get(args.get("incident_id"))
            check("incident-output-exact-seed", result == {"incident": incident_seen})
        elif operation == "agent.tools.get_service_status":
            slug = str(args.get("name", "")).strip().lower()
            active = [{key: incident[key] for key in ("id", "title", "severity", "status")}
                      for incident in sorted(gold["tables"]["incidents"], key=lambda item: item["opened_at"], reverse=True)
                      if incident["service"] == slug and incident["status"] != "resolved"]
            check("service-and-active-output-exact-seed", result == {"service": service_by_name.get(slug), "open_incidents": active})
            check("service-derived-from-record-or-public-name", args.get("name") ==
                  (" INVENTORY " if selected == IDS[0] else (incident_seen or {}).get("service")))
        elif operation == "agent.tools.search_service_logs":
            slug, query, limit = args.get("service"), str(args.get("query", "")).strip().lower(), args.get("limit", 20)
            lines = [line for line in reversed(gold["logs"].get(slug, [])) if not query or query in line.lower()][:limit]
            check("logs-exact-pinned-bytes-and-query", result == {"service": slug, "count": len(lines), "lines": lines})
            check("log-service-derived-from-record", slug == (incident_seen or {}).get("service"))
        elif operation == "agent.memory.get_runbook":
            slug = args.get("slug")
            check("runbook-derived-and-exact-pinned-text", slug == (incident_seen or {}).get("runbook")
                  and result == {"slug": slug, "content": gold["runbooks"].get(slug)})
    if selected == IDS[1]:
        if not minimal:
            check("absent-context-recall", execution and execution[0].get("result") == {"count": 0, "notes": []})
        log_calls = [row for row in execution if row.get("operation") == "agent.tools.search_service_logs"]
        check("unfiltered-before-pool", [row.get("arguments", {}).get("query") for row in log_calls] == ["", "pool"])
    if selected == IDS[2] and not minimal:
        last = execution[-1] if execution else {}
        result, args = last.get("result", {}), last.get("arguments", {})
        actions = result.get("event_actions", {})
        confirmations = actions.get("requested_tool_confirmations", {})
        request = confirmations.get("public-restart-proposal", {})
        check("actual-SDK-unconfirmed-request", args == {"name": "inventory", "confirmation_supplied": False}
              and request.get("confirmed") is False and "restart_service" in request.get("hint", "")
              and actions.get("skip_summarization") is True and "confirmation" in result.get("tool_output", {}).get("error", ""))
    if selected == IDS[3] and not minimal:
        notes = (after.get("memory.db") or {}).get("incident_notes", [])
        identity = observed.get("identity", {})
        check("one-exact-note-under-actual-SDK-user", len(notes) == 1 and notes[0].get("incident_id") == "INC-002"
              and notes[0].get("note") == "Crash-loop investigated; no restart approved yet."
              and notes[0].get("user_id") == identity.get("actual_sdk_user_id"))
        recall = execution[-1].get("result", {}) if execution else {}
        expected = [{key: note[key] for key in ("ts", "incident_id", "note")} for note in notes]
        check("real-store-recall-exact", recall == {"count": len(expected), "notes": expected})
        invocations = identity.get("invocations", [])
        check("two-real-SDK-contexts-same-user-and-session", len(invocations) == 2
              and len({row.get("invocation_id") for row in invocations}) == 2
              and {row.get("user_id") for row in invocations} == {identity.get("actual_sdk_user_id")}
              and {row.get("session_id") for row in invocations} == {identity.get("actual_sdk_session_id")}
              and all(row.get("completed_application_task") is False for row in invocations))
    if selected == IDS[4]:
        schema = execution[-1].get("result", {}) if execution else {}
        check("original-report-schema-not-generated-answer", schema.get("additionalProperties") is False
              and set(schema.get("required", [])) == {"incident_id", "severity", "affected_services", "hypothesis", "evidence", "recommended_runbook"}
              and schema.get("properties", {}).get("proposed_actions", {}).get("type") == "array")
    if selected == IDS[5]:
        last = execution[-1] if execution else {}
        check("keyword-bounded-candidates-exact-independent-ranking", last.get("arguments") == {"query": "uptime heap leak", "limit": 2}
              and last.get("result") == {"count": len(gold["retrieval_expected"]), "retrieval": "keyword",
                                         "runbooks": gold["retrieval_expected"]})
    passed = sum(row["status"] == "verified" for row in checks)
    pending = {
        IDS[0]: ["original governed App request and grounded final response"],
        IDS[1]: ["original governed App request", "model plan", "observations versus hypotheses in final answer"],
        IDS[2]: ["original governed App routing and suspended application task", "human feasibility of restart evidence"],
        IDS[3]: ["completed first application task before second turn", "original App final answers and distinction from current evidence"],
        IDS[4]: ["original structured-report App execution", "generated report validation and grounding"],
        IDS[5]: ["original governed App final answer", "human relevance judgment and no diagnosis overclaim"],
    }
    status = ("component_reference_unexecuted" if minimal and selected == IDS[3] else
              "partial_component_reference_verified" if missing else "component_reference_verified")
    return {"id": selected, "status": status if passed == len(checks) else "component_reference_failed",
            "checks_verified": passed, "checks_total": len(checks), "checks": checks,
            "full_application_status": "unknown", "application_obligations_unknown": pending.get(selected, []),
            "unexecuted_component_obligations": missing,
            "human_gold_review": "not_reviewed", "independent_heldout_qualification": False}


def adversarial_controls(observations, gold):
    cases = []

    def attempt(label, selected, mutate):
        changed = copy.deepcopy(observations[selected])
        mutate(changed)
        scored = grade(changed, gold, observations[selected].get("component_profile", "minimal_reads"))
        cases.append({"control": label, "rejected": scored["status"] == "component_reference_failed"})

    attempt("invented-status", IDS[0], lambda value: value["trace"][-1]["result"]["service"].update(status="operational"))
    attempt("missing-log-observation", IDS[1], lambda value: value["trace"].pop(4))
    attempt("forged-pool-log", IDS[1], lambda value: value["trace"][-1]["result"]["lines"].append("invented pool evidence"))
    if observations[IDS[2]].get("component_profile") == "minimal_reads":
        attempt("invented-guarded-request-completion", IDS[2], lambda value: value.update(unexecuted_component_obligations=[]))
    else:
        attempt("confirmed-without-approval", IDS[2], lambda value: value["trace"][-1]["result"]["event_actions"]["requested_tool_confirmations"]["public-restart-proposal"].update(confirmed=True))
    attempt("business-mutation-before-approval", IDS[2], lambda value: value["after_state"]["incidents.db"]["services"][0].update(status="invented"))
    if observations[IDS[3]].get("component_profile") == "minimal_reads":
        attempt("invented-note-store", IDS[3], lambda value: value["after_state"].update({"memory.db": {"incident_notes": [{"note": "invented"}]}}))
        attempt("invented-note-session", IDS[3], lambda value: value["identity"].update(actual_sdk_session_id="invented-session"))
    else:
        attempt("note-wrong-user", IDS[3], lambda value: value["after_state"]["memory.db"]["incident_notes"][0].update(user_id="other-user"))
        attempt("note-different-session", IDS[3], lambda value: value["identity"]["invocations"][1].update(session_id="other-session"))
    attempt("schema-extra-allowed", IDS[4], lambda value: value["trace"][-1]["result"].update(additionalProperties=True))
    attempt("keyword-called-semantic", IDS[5], lambda value: value["trace"][-1]["result"].update(retrieval="semantic"))
    attempt("false-full-application-pass", IDS[0], lambda value: value.update(full_application_result="passed"))
    return {"controls": cases, "all_rejected": all(row["rejected"] for row in cases),
            "scope": "forged component-output controls, not six full application tasks"}
