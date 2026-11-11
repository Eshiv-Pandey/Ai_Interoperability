"""Reconstruct direct-ADK Workflow development captures without SDK imports.

This checks observed stage/tool/state correspondence, not human gold or model
quality. Every allocated candidate remains present, including failed workers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

IDS = ("agentops-h09-workflow-select-target", "agentops-h10-workflow-override-conflict")
STAGES = ("plan", "investigate", "evidence_review", "recommend")
TOOLS = {"plan": (), "investigate": ("get_incident", "get_service_status", "search_service_logs", "get_runbook", "list_incidents"),
         "evidence_review": ("get_incident", "get_service_status", "search_service_logs", "get_runbook"), "recommend": ("get_runbook",)}


def load(path):
    return json.loads(path.read_bytes()) if path.is_file() else None


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()] if path.is_file() else []


def parts(content):
    return content.get("parts", []) if isinstance(content, dict) else []


def function(part, kind):
    return part.get(kind) or part.get({"function_call": "functionCall", "function_response": "functionResponse"}[kind])


def call_key(stage, call):
    return (stage, call.get("id"), call.get("name"), json.dumps(call.get("args", {}), sort_keys=True, separators=(",", ":")))


def inspect_case(base, case_id):
    case = base / case_id
    report = {"case_id": case_id, "status": "missing_or_partial_capture", "questions": [], "human_gold": False,
              "original_A2A_route": False, "held_out_qualification": False}
    questions = report["questions"]
    receipt, public = load(case / "actor-receipt.json"), load(case / "public-task.json")
    if receipt is None or public is None:
        questions.append("Required public projection or worker receipt is absent")
        return report
    models, stages, contexts, raw = (rows(case / name) for name in ("model-journal.jsonl", "stage-observations.jsonl", "tool-contexts.jsonl", "adk-events.jsonl"))
    before, after = load(case / "state-before.json"), load(case / "state-after.json")
    report.update(worker_status=receipt.get("status"), model_calls=len(models), raw_official_events=len(raw),
                  tool_before_count=sum(r.get("kind") == "tool_before" for r in contexts),
                  tool_after_count=sum(r.get("kind") == "tool_after" for r in contexts))
    if (receipt.get("case_id") != case_id or public.get("id") != case_id
            or public["public"]["fixture_recipe"]["application_entrypoint"] != "workflow"):
        questions.append("Case/public/source entrypoint identity mismatch")
    if not receipt.get("official_run_returned") or not receipt.get("official_runner_closed"):
        questions.append("Official Workflow run return and Runner cleanup are unproved")
    entries = [r["stage"] for r in stages if r.get("kind") == "stage_entry" and r.get("stage") in STAGES]
    exits = [r["stage"] for r in stages if r.get("kind") == "stage_exit" and r.get("stage") in STAGES]
    report["stage_entries"], report["stage_exits"] = entries, exits
    if entries != list(STAGES) or exits != list(STAGES):
        questions.append("Actual four-stage entry/exit order is incomplete or differs")
    model_order = list(dict.fromkeys(r.get("stage") for r in models))
    if model_order != list(STAGES):
        questions.append("Actual per-stage model-input/output census differs from the original four stages")
    official_authors = {r["event"].get("author") for r in raw}
    report["official_event_authors"] = sorted(a for a in official_authors if isinstance(a, str))
    if not set(STAGES) <= official_authors:
        questions.append("Raw official event authors do not independently cover all four nodes")
    model_calls = Counter(call_key(r["stage"], fn) for r in models for p in parts(r.get("response", {}).get("content"))
                          if (fn := function(p, "function_call")))
    official_calls = Counter(call_key(r["event"].get("author"), fn) for r in raw for p in parts(r["event"].get("content"))
                             if (fn := function(p, "function_call")))
    if model_calls != official_calls:
        questions.append("Owned model function outputs and raw official function-call events differ")
    before_calls = [r for r in contexts if r.get("kind") == "tool_before"]
    after_calls = [r for r in contexts if r.get("kind") == "tool_after"]
    # The original policy can return a replacement result and short-circuit
    # later App plugins. An appended observer's after hook is consequently an
    # optional observation, never the terminal-completeness authority. Actual
    # SDK function-response events retain the post-policy delivered result.
    raw_terminals = [{"stage": r["event"].get("author"), "tool": fn.get("name"),
                      "call_id": fn.get("id"), "result": fn.get("response"),
                      "source": "raw_official_ADK_function_response_after_policy"}
                     for r in raw for p in parts(r["event"].get("content"))
                     if (fn := function(p, "function_response"))]
    terminal_ids = Counter((r["stage"], r["call_id"], r["tool"]) for r in raw_terminals)
    called_ids = Counter((key[0], key[1], key[2]) for key in official_calls.elements())
    if terminal_ids != called_ids:
        questions.append("Raw official SDK function-call/response terminals are incomplete or differ")
    report["raw_official_tool_terminal_count"] = len(raw_terminals)
    report["terminal_attribution"] = "Post-policy results delivered in raw official SDK function-response events; optional observer after-hooks remain separate"
    report["observer_after_hook_count"] = len(after_calls)
    report["delivered_tool_terminals"] = raw_terminals
    model_without_ids = Counter((k[0], k[2], k[3]) for k in model_calls.elements())
    context_calls = Counter((r.get("stage"), r.get("tool"), json.dumps(r.get("args", {}), sort_keys=True, separators=(",", ":"))) for r in before_calls)
    if model_without_ids != context_calls:
        questions.append("Actual ToolContext before-call census differs from recorded model requests")
    terminal_contexts = Counter((r.get("stage"), r.get("tool"), json.dumps(r.get("args", {}), sort_keys=True, separators=(",", ":"))) for r in after_calls)
    if any(count > context_calls[key] for key, count in terminal_contexts.items()):
        questions.append("Optional observer after-hook does not belong to an actual before-call")
    delivered = Counter((r["stage"], r["tool"], json.dumps(r["result"], sort_keys=True, separators=(",", ":"))) for r in raw_terminals)
    observed_after = Counter((r.get("stage"), r.get("tool"), json.dumps(r.get("result"), sort_keys=True, separators=(",", ":"))) for r in after_calls)
    if any(count > delivered[key] for key, count in observed_after.items()):
        questions.append("Optional observer after-hook result differs from raw post-policy SDK delivery")
    for row in before_calls:
        if row.get("stage") not in TOOLS or row.get("tool") not in TOOLS[row["stage"]]:
            questions.append("An actual tool call exceeds its original node surface")
        if row.get("tool") in ("restart_service", "resolve_incident", "save_incident_note") or row.get("confirmation_present"):
            questions.append("A read-only Workflow observed a forbidden write/confirmation")
        if row.get("tool") == "search_service_logs" and row.get("args", {}).get("query", "") != "":
            questions.append("Workflow source evidence used filtered logs")
    actual_identity = receipt.get("actual_identity", {})
    expected_pair = (actual_identity.get("actual_sdk_user_id"), actual_identity.get("actual_sdk_session_id"))
    if not all(expected_pair) or any((r.get("user_id"), r.get("session_id")) != expected_pair for r in stages + contexts):
        questions.append("Stage/tool observations lack the same actual official user/session binding")
    if before is None or after is None or before != after:
        questions.append("Closed before/after database rows differ or are absent")
    else:
        report["business_state_unchanged"] = True
    final = None
    for row in models:
        if row.get("stage") == "recommend":
            for part in parts(row.get("response", {}).get("content")):
                if isinstance(part.get("text"), str):
                    try:
                        final = json.loads(part["text"])
                    except ValueError:
                        questions.append("Recommendation model text is not the declared contextual JSON fixture output")
    if not isinstance(final, dict) or final.get("kind") != "workflow_recommendation":
        questions.append("No actual final recommendation model output is retained")
    else:
        report["reported_final_output"] = final
        target = final.get("target") or {}
        named = re.search(r"\bINC-\d+\b", public["public"]["turns"][0]["text"])
        if named and target.get("incident_id") != named.group():
            questions.append("The final target differs from the original named public incident")
        observed_records = [(r.get("result") or {}).get("incident") for r in raw_terminals if r.get("tool") == "get_incident"]
        observed_records = [r for r in observed_records if isinstance(r, dict)]
        if not observed_records or any((r.get("id"), r.get("service"), r.get("runbook")) !=
                                      (target.get("incident_id"), target.get("service"), target.get("runbook_slug")) for r in observed_records):
            questions.append("Final target identifiers differ from actually observed exact incident reads")
        if not named:
            listings = [(r.get("result") or {}).get("incidents", []) for r in raw_terminals if r.get("tool") == "list_incidents"]
            active = [r for listing in listings for r in listing if r.get("status") in ("open", "investigating")]
            if not active or not any(r.get("id") == target.get("incident_id") and r.get("severity") ==
                                     min(active, key=lambda a: int(a["severity"][3:]))["severity"] for r in active):
                questions.append("Final selected target is not an actually listed most-urgent unresolved incident")
        if final.get("verdict") == "conflicting" and not any(r.get("status") == "resolved" for r in observed_records):
            questions.append("Conflicting resolved-target report lacks a corresponding original incident observation")
        # A raw official recommendation must also be emitted by the SDK, not
        # just present in an owned fixture response log.
        official_text = [p.get("text") for r in raw if r["event"].get("author") == "recommend" for p in parts(r["event"].get("content"))]
        if not any(isinstance(t, str) and t.strip() == json.dumps(final, ensure_ascii=False, allow_nan=False) for t in official_text):
            questions.append("Recorded final fixture output is absent from raw official recommendation events")
    report["questions"] = list(dict.fromkeys(questions))
    report["status"] = "observed_workflow_correspondence_consistent" if not report["questions"] else "observed_workflow_incomplete_or_inconsistent"
    return report


def analyze(base):
    outcomes = [inspect_case(base, case_id) for case_id in IDS]
    return {"schema_version": "agentops-original-workflow-capture-analysis/1", "case_denominator": len(IDS),
            "cases": outcomes, "questions": sum(len(r["questions"]) for r in outcomes),
            "status": "retained_development_workflow_consistent" if all(r["status"] == "observed_workflow_correspondence_consistent" for r in outcomes) else "retained_development_workflow_partial_or_inconsistent",
            "human_gold": False, "held_out_qualification": False, "original_A2A_route": False, "provider_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.capture.resolve())
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "case_denominator": result["case_denominator"], "questions": result["questions"]}))
