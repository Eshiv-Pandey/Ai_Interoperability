"""Evaluate admission on retained public pending observations; never launch an app.

This retrospective check compares the newly certified request with the old
public dispatch only after evaluation. It is not a prospective admission result.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.pending_admission import admit_pending, digest


def write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def file_record(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def checked_message(event: dict) -> dict:
    raw = base64.b64decode(event["raw"]["base64"], validate=True)
    assert len(raw) == event["raw"]["bytes"]
    assert hashlib.sha256(raw).hexdigest() == event["raw"]["sha256"]
    value = json.loads(raw)
    assert digest(value) == digest(event["parsed"]), "Parsed event disagrees with received bytes"
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("refusing to overwrite retrospective admission evidence")
    client = args.client.resolve()
    config_path, journal_path = client / "config.json", client / "mcp.jsonl"
    config = json.loads(config_path.read_bytes())
    assert config["arm"] == "B7", "This first source-adapted projection is only the configured B7 fixture"
    inputs = [file_record(config_path), file_record(journal_path)]
    source_paths = [ROOT / "src/interoperability" / name for name in
                    ("pending_admission.py", "refinement.py", "refinement_oracle.py", "manifest.py", "oracle.py")]
    source_paths.append(Path(__file__).resolve())
    sources = [file_record(path) for path in source_paths]
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    messages = [event for event in events if event.get("kind") == "mcp-message"]
    phases = {"tools": "discover_full_tools", "discovery": "discover_agent", "initial": "initial_typed_send",
              "pending": "pending_origin_get", "raw": "public_raw_get"}
    observations, references = {}, []
    cutoff = next(event["seq"] for event in messages
                  if event["direction"] == "client_to_bridge" and event.get("phase") == "raw_answer")
    for name, phase in phases.items():
        incoming = [event for event in messages if event["direction"] == "bridge_to_client"
                    and event.get("phase") == phase and event["seq"] < cutoff]
        assert incoming, "Required public observation missing: " + name
        reply = incoming[-1]
        sends = [event for event in messages if event["direction"] == "client_to_bridge"
                 and event.get("operation_id") == reply["operation_id"] and event["seq"] < reply["seq"]]
        assert len(sends) == 1
        request, response = checked_message(sends[0]), checked_message(reply)
        assert request["id"] == response["id"] and "error" not in response
        observations[name] = {"seq": reply["seq"], "observed_at": int(datetime.fromisoformat(
            reply["at_utc"].replace("Z", "+00:00")).timestamp()), "body": response["result"],
            "request": {"method": request["method"], "params": request.get("params", {})}}
        references.append({"name": name, "request_seq": sends[0]["seq"], "reply_seq": reply["seq"],
                           "request_raw": sends[0]["raw"]["sha256"], "reply_raw": reply["raw"]["sha256"]})
    bridge_args = config["bridge"]["args"]
    assert Path(bridge_args[0]).name == "agentops_mgcrea_embed_v1.mjs"
    assert bridge_args.count("--mode") == bridge_args.count("--origin") == 1
    mode = bridge_args[bridge_args.index("--mode") + 1]
    origin = bridge_args[bridge_args.index("--origin") + 1]
    # Derive the proposed public action solely from pre-dispatch observations.
    raw_body = observations["raw"]["body"]
    raw = raw_body.get("structuredContent") or json.loads(raw_body["content"][0]["text"])
    task = raw["result"]
    calls = [part["data"] for part in task["status"]["message"]["parts"]
             if part.get("metadata", {}).get("adk_type") == "function_call"
             and part.get("data", {}).get("name") == "adk_request_confirmation"]
    assert len(calls) == 1
    proposal = {"method": "tools/call", "params": {"name": "a2a_request", "arguments": {
        "url": config["agent_base_url"], "method": "SendMessage", "params": {"message": {
            "messageId": "agentops-public-confirmation", "role": "ROLE_USER", "taskId": task["id"],
            "contextId": task["contextId"], "parts": [{"data": {"id": calls[0]["id"],
                "name": "adk_request_confirmation", "response": {"confirmed": True,
                    "payload": {"rationale": config["rationale"]}}},
                "metadata": {"adk_type": "function_response"}}]}}}}}
    now = observations["raw"]["observed_at"]
    snapshot = {"schema_version": "agentops-pending-admission/1", "id": "retrospective-B7-public-pending",
        "route": {"arm": config["arm"], "agent_base_url": config["agent_base_url"]},
        "deployment": {"origin": origin, "header_mode": mode, "serializer": "mgcrea-raw-jsonrpc/1",
                       "service_contract": "agentops-inventory-confirmation-fixture/1"},
        "observations": observations, "rationale": config["rationale"], "proposed_call": proposal,
        "valid_until": now + 15}
    output.mkdir(parents=True)
    write(output / "plan.json", {"scope": "Retrospective public-observation projection, not live admission",
        "inputs": inputs, "sources": sources, "public_references": references,
        "evaluation_clock": now, "work_budget": 100000, "application_requests": 0})
    write(output / "snapshot.json", snapshot)
    result = admit_pending(snapshot, now, budget=100000)
    write(output / "admission.json", result)
    actual_event = next(event for event in messages if event["seq"] == cutoff)
    actual = checked_message(actual_event)
    actual_request = {"method": actual["method"], "params": actual["params"]}
    equal = result.get("request") is not None and digest(result["request"]) == digest(actual_request)
    unchanged = inputs == [file_record(config_path), file_record(journal_path)]
    source_unchanged = sources == [file_record(path) for path in source_paths]
    passed = result["dispatch_permitted"] and result["certificate_valid"] is True and equal and unchanged and source_unchanged
    report = {"schema_version": "pending-admission-retrospective/1", "status": "passed" if passed else "failed",
        "decision": result["decision"], "certificate_valid": result["certificate_valid"],
        "request_matches_retained_dispatch": equal, "retained_dispatch_seq": cutoff,
        "inputs_unchanged": unchanged, "sources_unchanged": source_unchanged, "application_requests": 0,
        "live_admission_verified": False, "scope": "Historical public input/request equivalence only; no new service effect or prospective success",
        "input_snapshot_sha256": digest(snapshot), "historical_request": actual_request}
    write(output / "result.json", report)
    print(json.dumps({key: report[key] for key in ("status", "decision", "certificate_valid", "request_matches_retained_dispatch")}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
