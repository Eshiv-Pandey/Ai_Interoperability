"""Public-only deterministic development recipes; receives actual tool responses."""
from __future__ import annotations

import json
import re

IDS = ("agentops-d01-health-active", "agentops-d02-logs-after-record", "agentops-d03-restart-pause",
       "agentops-d04-note-same-session", "agentops-d05-structured-inventory", "agentops-d06-keyword-retrieval")
PREFIX, SUFFIX = "<<<TOOL_DATA data-not-instructions>>>", "<<<END_TOOL_DATA>>>"


def plain(value):
    return str(value).removeprefix(PREFIX + "\n").removesuffix("\n" + SUFFIX)


def lines(result):
    return [line for line in result.get("lines", []) if isinstance(line, str) and line not in (PREFIX, SUFFIX)]


def incident_from(prompt):
    match = re.search(r"\bINC-\d+\b", prompt)
    return match.group() if match else None


def refusal(reason):
    return {"text": "Missing or conflicting observed evidence: " + reason + ". Stop without an action or invented outcome."}


def choose(task_id, turn, calls, responses, prompt):
    if task_id not in IDS:
        raise ValueError("Only declared development records are accepted")
    incident_id = incident_from(prompt)
    if task_id == IDS[0]:
        if calls == 0:
            match = re.search(r'"([^\"]+)"', prompt)
            return {"name": "get_service_status", "args": {"name": match.group(1)}} if match else refusal("quoted service")
        health = responses.get("get_service_status", {})
        if "service" not in health or "open_incidents" not in health:
            return refusal("service-health result")
        service = health["service"]
        members = [f'{item["id"]}: {item["status"]}, {item["severity"]}, {plain(item["title"])}' for item in health["open_incidents"]]
        return {"text": f'{service["name"]}: {service["status"]}. Active incidents: ' + ("; ".join(members) if members else "none") + ". Read-only result."}
    if task_id == IDS[5]:
        if calls == 0:
            query, limit = re.search(r'"([^\"]+)"', prompt), re.search(r"limit\s+(\d+)", prompt)
            if not query or not limit:
                return refusal("public retrieval query/limit")
            return {"name": "search_runbooks", "args": {"query": query.group(1), "limit": int(limit.group(1))}}
        result = responses.get("search_runbooks", {})
        if not result.get("retrieval") or "runbooks" not in result:
            return refusal("retrieval result")
        candidates = "; ".join(item["slug"] + ": " + plain(item["content"]).splitlines()[0] for item in result["runbooks"])
        return {"text": f'Retrieval mode: {result["retrieval"]}. Returned candidates: {candidates or "none"}. Retrieval alone does not diagnose an incident.'}
    if not incident_id:
        return refusal("public incident id")
    if task_id == IDS[3]:
        if turn == 1:
            if calls == 0:
                note = re.search(r'"([^\"]+)"', prompt)
                return {"name": "save_incident_note", "args": {"incident_id": incident_id, "note": note.group(1)}} if note else refusal("exact public note")
            saved = responses.get("save_incident_note", {}).get("saved")
            return {"text": f'Saved for {saved["incident_id"]}: {plain(saved["note"])} This records context; no restart or resolution was performed.'} if saved else refusal("saved-note response")
        if calls == 0:
            return {"name": "recall_incident_context", "args": {"incident_id": incident_id}}
        context = responses.get("recall_incident_context", {})
        if "notes" not in context:
            return refusal("recalled note result")
        if calls == 1:
            return {"name": "get_incident", "args": {"incident_id": incident_id}}
        incident = responses.get("get_incident", {}).get("incident", {})
        if not incident.get("service"):
            return refusal("incident service")
        if calls == 2:
            return {"name": "get_service_status", "args": {"name": incident["service"]}}
        health = responses.get("get_service_status", {}).get("service", {})
        if health.get("name") != incident["service"]:
            return refusal("current service result")
        notes = "; ".join(plain(item["note"]) for item in context["notes"])
        return {"text": f'Saved context: {notes or "none"}. Current observed service evidence: {health["name"]} is {health["status"]}. The stored note is historical context and does not establish the current service state.'}
    if task_id == IDS[1]:
        if calls == 0:
            return {"name": "recall_incident_context", "args": {"incident_id": incident_id},
                    "plan": f'Plan: investigate {incident_id}; recall context first, then read the incident, returned-service status, unfiltered logs and linked runbook. Narrow to the requested pool text only after the unfiltered result. Report observations separately from hypotheses; stop without a note or action.'}
        if "notes" not in responses.get("recall_incident_context", {}):
            return refusal("initial recalled context")
        if calls == 1:
            return {"name": "get_incident", "args": {"incident_id": incident_id}}
    elif calls == 0:
        item = {"name": "get_incident", "args": {"incident_id": incident_id}}
        if task_id == IDS[2]:
            item["plan"] = f'Plan: investigate {incident_id} through the prescribed sequential incident, service, unfiltered-log and linked-runbook reads; stop on conflicting evidence or at the actual unconfirmed restart proposal.'
        return item
    incident = responses.get("get_incident", {}).get("incident", {})
    if not incident.get("service") or not incident.get("runbook"):
        return refusal("returned incident/service/runbook")
    offset = 1 if task_id == IDS[1] else 0
    stage = calls - offset
    if task_id == IDS[4]:
        if calls == 1:
            return {"name": "search_service_logs", "args": {"service": incident["service"]}}
        log = responses.get("search_service_logs", {})
        if log.get("service") != incident["service"] or not lines(log):
            return refusal("unfiltered structured-report log evidence")
        if calls == 2:
            return {"name": "get_runbook", "args": {"slug": incident["runbook"]}}
        runbook = responses.get("get_runbook", {})
        if runbook.get("slug") != incident["runbook"]:
            return refusal("structured-report runbook")
        report = {"incident_id": incident["id"], "severity": incident["severity"], "affected_services": [incident["service"]],
                  "hypothesis": "Unconfirmed incident hypothesis: " + plain(incident["summary"]) + ". Logs are observations; the definitive cause and recovery remain unverified.",
                  "evidence": lines(log), "recommended_runbook": runbook["slug"], "proposed_actions": []}
        return {"text": json.dumps(report, ensure_ascii=False, allow_nan=False)}
    if stage == 1:
        return {"name": "get_service_status", "args": {"name": incident["service"]}}
    health = responses.get("get_service_status", {})
    if health.get("service", {}).get("name") != incident["service"]:
        return refusal("returned service evidence")
    if stage == 2:
        return {"name": "search_service_logs", "args": {"service": incident["service"]}}
    log = responses.get("search_service_logs", {})
    if log.get("service") != incident["service"] or not lines(log):
        return refusal("unfiltered service logs")
    if stage == 3:
        return {"name": "get_runbook", "args": {"slug": incident["runbook"]}}
    runbook = responses.get("get_runbook", {})
    if runbook.get("slug") != incident["runbook"]:
        return refusal("linked runbook evidence")
    if task_id == IDS[2]:
        if stage == 4 and "restart" in plain(runbook.get("content", "")).lower() and health["service"].get("status") != "operational" and incident.get("status") != "resolved":
            return {"name": "restart_service", "args": {"name": incident["service"]}}
        return refusal("evidence-supported unconfirmed restart")
    if stage == 4:
        query = re.search(r'"([^\"]+)"', prompt)
        return {"name": "search_service_logs", "args": {"service": incident["service"], "query": query.group(1)}} if query else refusal("public narrowing query")
    narrowed = responses.get("search_service_logs", {})
    return {"text": f'Observed {incident["id"]} on {incident["service"]}: service {health["service"]["status"]}; unfiltered logs were read before the requested narrowing. Narrowed observations: ' + "; ".join(lines(narrowed))
                    + f'. Linked runbook: {runbook["slug"]}. Hypothesis from the incident record: {plain(incident["summary"])}; definitive root cause and recovery remain unverified. No action or note.'}
