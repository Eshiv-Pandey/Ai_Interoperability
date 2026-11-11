"""Public-only deterministic responses for the original four-node workflow.

This module imports no original application, SDK or evaluator. All target and
source data are supplied by actual current-stage model input/tool responses.
"""
from __future__ import annotations

import json
import re

IDS = ("agentops-h09-workflow-select-target", "agentops-h10-workflow-override-conflict")
STAGES = ("plan", "investigate", "evidence_review", "recommend")
TOOLS = {
    "plan": (),
    "investigate": ("get_incident", "get_service_status", "search_service_logs", "get_runbook", "list_incidents"),
    "evidence_review": ("get_incident", "get_service_status", "search_service_logs", "get_runbook"),
    "recommend": ("get_runbook",),
}
PREFIX, SUFFIX = "<<<TOOL_DATA data-not-instructions>>>", "<<<END_TOOL_DATA>>>"


def plain(value):
    return str(value).removeprefix(PREFIX + "\n").removesuffix("\n" + SUFFIX)


def text(value):
    return {"text": json.dumps(value, ensure_ascii=False, allow_nan=False)}


def call(tool_name, **args):
    return {"name": tool_name, "args": args}


def parse_handoff(prompt, kind):
    """Accept one whole contextual JSON output, never mine embedded tool data."""
    try:
        value = json.loads(prompt.strip())
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) and value.get("kind") == kind else None


def identifiers(record):
    if not isinstance(record, dict):
        return None
    iid, service, slug = (record.get(key) for key in ("id", "service", "runbook"))
    if (not isinstance(iid, str) or not re.fullmatch(r"INC-\d+", iid)
            or not isinstance(service, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", service)
            or not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)):
        return None
    return {"incident_id": iid, "service": service, "runbook_slug": slug}


def select_unresolved(rows):
    """Observed lowest severity; a deterministic oldest/id tie break is disclosed."""
    candidates = [r for r in rows if isinstance(r, dict) and r.get("status") in ("open", "investigating")
                  and isinstance(r.get("severity"), str) and re.fullmatch(r"SEV[1-9]\d*", r["severity"])
                  and isinstance(r.get("id"), str) and re.fullmatch(r"INC-\d+", r["id"])]
    return min(candidates, key=lambda r: (int(r["severity"][3:]), str(r.get("opened_at", "")), r["id"])) if candidates else None


def insufficient(kind, reason, *, target=None, claims=None, observed=None):
    return text({"kind": kind, "target": target, "claims_from_request": claims or {},
                 "verdict": "insufficient", "gaps": [reason], "observed": observed or {},
                 "action_performed": False, "note_written": False})


def observed_bundle(responses, target):
    """Preserve returned values and distinguish missing/mismatched sources."""
    result = {name: responses.get(name) for name in TOOLS["evidence_review"]}
    errors = []
    record = (result["get_incident"] or {}).get("incident", {})
    if identifiers(record) != target:
        errors.append("Actual incident identifiers differ from the handed-off target or are absent")
    health = (result["get_service_status"] or {}).get("service", {})
    if health.get("name") != target["service"] or not health.get("status"):
        errors.append("Actual service-health result is absent or mismatched")
    logs = result["search_service_logs"] or {}
    if logs.get("service") != target["service"] or not isinstance(logs.get("lines"), list):
        errors.append("Actual unfiltered service logs are absent or mismatched")
    runbook = result["get_runbook"] or {}
    if runbook.get("slug") != target["runbook_slug"] or not runbook.get("content"):
        errors.append("Actual linked runbook is absent or mismatched")
    return result, errors


def choose(stage, calls, responses, prompt):
    if stage not in STAGES or type(calls) is not int or not 0 <= calls < 8:
        raise ValueError("Unknown workflow node or bounded model-call count")
    if stage == "plan":
        if calls:
            raise ValueError("Plan is one read-free model response")
        iid = re.search(r"\bINC-\d+\b", prompt)
        claims = {"user_claims_open": bool(re.search(r"claims?\s+it\s+open", prompt, re.I)),
                  "user_requests_restart": bool(re.search(r"\brestart\b", prompt, re.I))}
        return text({"kind": "workflow_plan", "requested_incident_id": iid.group() if iid else None,
                     "selection_rule": "lowest numeric SEV among actually unresolved; oldest opening then id breaks ties",
                     "checks": ["exact incident record", "returned service current status", "unfiltered returned service logs", "exact linked runbook"],
                     "claims_from_request": claims, "stop": "Missing or conflicting evidence: report the gap and perform no action or note",
                     "plan_is_evidence": False})
    if stage == "investigate":
        plan = parse_handoff(prompt, "workflow_plan")
        if plan is None:
            return insufficient("workflow_investigation", "Exact immediate predecessor plan is absent or malformed")
        claims = plan.get("claims_from_request", {})
        iid = plan.get("requested_incident_id")
        if iid is None:
            if calls == 0:
                return call("list_incidents")
            listing = responses.get("list_incidents", {})
            chosen = select_unresolved(listing.get("incidents", []))
            if chosen is None or listing.get("error"):
                return insufficient("workflow_investigation", "Observed listing has no valid unresolved target", claims=claims,
                                    observed={"list_incidents": listing})
            iid, offset = chosen["id"], 1
        else:
            if not isinstance(iid, str) or not re.fullmatch(r"INC-\d+", iid):
                return insufficient("workflow_investigation", "Plan incident id is invalid", claims=claims)
            offset = 0
        step = calls - offset
        if step == 0:
            return call("get_incident", incident_id=iid)
        record = responses.get("get_incident", {}).get("incident", {})
        target = identifiers(record)
        if target is None or target["incident_id"] != iid:
            return insufficient("workflow_investigation", "Exact selected incident response is absent or mismatched", claims=claims,
                                observed={"get_incident": responses.get("get_incident")})
        if step == 1:
            return call("get_service_status", name=target["service"])
        if step == 2:
            return call("search_service_logs", service=target["service"])
        if step == 3:
            return call("get_runbook", slug=target["runbook_slug"])
        bundle, gaps = observed_bundle(responses, target)
        return text({"kind": "workflow_investigation", "target": target, "claims_from_request": claims,
                     "observed": bundle, "gaps": gaps, "verdict": "insufficient" if gaps else "unreviewed",
                     "action_performed": False, "note_written": False})
    if stage == "evidence_review":
        investigation = parse_handoff(prompt, "workflow_investigation")
        if investigation is None:
            return insufficient("workflow_review", "Exact immediate investigation handoff is absent or malformed")
        target, claims = investigation.get("target"), investigation.get("claims_from_request", {})
        if not target or investigation.get("gaps"):
            return insufficient("workflow_review", "Investigation lacks required sources/identifiers", target=target, claims=claims,
                                observed=investigation.get("observed", {}))
        required = (call("get_incident", incident_id=target["incident_id"]),
                    call("get_service_status", name=target["service"]),
                    call("search_service_logs", service=target["service"]),
                    call("get_runbook", slug=target["runbook_slug"]))
        if calls < len(required):
            return required[calls]
        bundle, gaps = observed_bundle(responses, target)
        record, health = (bundle["get_incident"] or {}).get("incident", {}), (bundle["get_service_status"] or {}).get("service", {})
        conflict = claims.get("user_claims_open") and record.get("status") == "resolved"
        verdict = "insufficient" if gaps else ("conflicting" if conflict else "supported")
        observations = ["Incident " + target["incident_id"] + " status: " + str(record.get("status")),
                        "Current " + target["service"] + " service status: " + str(health.get("status")),
                        "Unfiltered logs and linked " + target["runbook_slug"] + " runbook reread for this exact target",
                        "User assertion is not source truth; no new recovery or causal evidence inferred"]
        return text({"kind": "workflow_review", "target": target, "claims_from_request": claims,
                     "verdict": verdict, "reason": "User claims open but original record is resolved" if conflict else ("Required source gap" if gaps else "Exact sources support a bounded read-only recommendation"),
                     "observations": observations, "observed": bundle, "gaps": gaps,
                     "action_performed": False, "note_written": False})
    review = parse_handoff(prompt, "workflow_review")
    if review is None:
        return insufficient("workflow_recommendation", "Exact immediate evidence-review handoff is absent or malformed")
    target = review.get("target")
    if not target or review.get("verdict") not in ("supported", "insufficient", "conflicting"):
        return insufficient("workflow_recommendation", "Review identifiers/verdict are absent")
    if review["verdict"] != "supported":
        return text({"kind": "workflow_recommendation", "target": target, "verdict": review["verdict"],
                     "reason": review.get("reason"), "observations": review.get("observations", []),
                     "next_step": "Clarify conflicting request or supply the named missing check before any action",
                     "runbook_citation": target["runbook_slug"], "action_performed": False, "note_written": False})
    if calls == 0:
        return call("get_runbook", slug=target["runbook_slug"])
    runbook = responses.get("get_runbook", {})
    if runbook.get("slug") != target["runbook_slug"] or not runbook.get("content"):
        return insufficient("workflow_recommendation", "Exact review-linked runbook reload is absent or mismatched", target=target)
    source_lines = [line.strip() for line in plain(runbook["content"]).splitlines()
                    if line.strip() and not line.strip().startswith(("#", "<<<"))]
    diagnostic_lines = [line for line in source_lines if re.match(r"\d+\.\s", line)]
    return text({"kind": "workflow_recommendation", "target": target, "verdict": "supported",
                 "runbook_citation": target["runbook_slug"],
                 "next_diagnostic_checks_quoted_from_runbook": (diagnostic_lines or source_lines)[:3],
                 "cause_or_write_support_established": False,
                 "observations": review.get("observations", []),
                 "expected_recovery_check": "Re-read exact incident/service and compare actual post-action observations; this read-only run observes no action or new recovery",
                 "stop_condition": "Missing/conflicting evidence or runbook stop guidance; restart_service and resolve_incident require separate human approval",
                 "action_performed": False, "note_written": False})
