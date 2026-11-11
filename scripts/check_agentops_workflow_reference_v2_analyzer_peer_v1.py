"""Replay constructed analyzer acceptance mutations without App/SDK execution.

Only owned standard-library modules are imported. Temporary constructed files
are the positive fixture; each tested mutation uses in-memory analyzer readers.
The output is an additive observation, not human gold or provider qualification.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import analyze_agentops_workflow_reference_v1 as v1
import analyze_agentops_workflow_reference_v2 as v2
from agentops_workflow_public_v1 import IDS
from check_agentops_workflow_reference_v2 import bind_constructed_case


def run():
    sources = {}
    for module in (v1, v2):
        path = Path(module.__file__).resolve()
        raw = path.read_bytes()
        sources[path.name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        # Use exact source despite rapid same-second implementation changes.
        exec(compile(raw.decode("utf-8"), str(path), "exec"), module.__dict__)
    observations = []
    with tempfile.TemporaryDirectory(prefix="constructed-workflow-analyzer-peer-") as directory:
        base = Path(directory)
        for case_id in IDS:
            bind_constructed_case(base, case_id)
        baseline = v2.analyze(base)
        blobs = {str(path): json.loads(path.read_bytes())
                 for case_id in IDS for path in (base / case_id).glob("*.json")}
        journals = {str(path): [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]
                    for case_id in IDS for path in (base / case_id).glob("*.jsonl")}
        original_load, original_rows = v1.load, v1.rows

        def key(name):
            return str(base / IDS[0] / name)

        def observe(name, mutation, change):
            changed_blobs, changed_journals = copy.deepcopy(blobs), copy.deepcopy(journals)
            change(changed_blobs, changed_journals)
            def load(path):
                return copy.deepcopy(changed_blobs.get(str(path)))
            def rows(path):
                return copy.deepcopy(changed_journals.get(str(path), []))
            v1.load = v2.load = load
            v1.rows = v2.rows = rows
            try:
                result = v2.analyze(base)
                questions = result["cases"][0]["questions"]
                observations.append({"case": name, "mutation": mutation,
                                     "status": result["status"], "questions": result["questions"],
                                     "mutated_case_questions": questions,
                                     "invalid_capture_accepted": not questions})
            except Exception as error:
                observations.append({"case": name, "mutation": mutation,
                                     "analyzer_exception": type(error).__name__,
                                     "invalid_capture_accepted": False})
            finally:
                v1.load = v2.load = original_load
                v1.rows = v2.rows = original_rows

        def overlap(blobs, rows):
            stage_rows = rows[key("stage-observations.jsonl")]
            rows[key("stage-observations.jsonl")] = [row for row in stage_rows if row["kind"] == "stage_entry"] + [row for row in stage_rows if row["kind"] == "stage_exit"]
        def callback_wrong(blobs, rows):
            rows[key("model-journal.jsonl")][0]["actual_callback_invocation_id"] = "different-invocation"
        def stage_wrong(blobs, rows):
            rows[key("stage-observations.jsonl")][0]["invocation_id"] = "different-invocation"
        def raw_wrong(blobs, rows):
            for row in rows[key("adk-events.jsonl")]:
                row["event"]["invocation_id"] = "different-invocation"
        def terminal_before_call(blobs, rows):
            events = rows[key("adk-events.jsonl")]
            index = next(i for i, row in enumerate(events)
                         if any("function_response" in part for part in row["event"]["content"]["parts"]))
            events[index - 1], events[index] = events[index], events[index - 1]
        def denied(event):
            def change(blobs, rows):
                blobs[key("actor-receipt.json")]["denied_capability_probes"] = [{"event": event, "arguments": ["backend.example", 443]}]
            return change
        def failed_receipt(blobs, rows):
            blobs[key("actor-receipt.json")].update(status="failed", error_type="ValueError", copied_data_unchanged_during_task=False)
        def request_model(blobs, rows):
            rows[key("model-journal.jsonl")][0]["actual_governed_request_model"] = "different-model"
        def exported_model(blobs, rows):
            blobs[key("actor-receipt.json")]["nodes"][0]["original_model_identifier"] = "different-exported-model"
        def sdk_error_message(blobs, rows):
            rows[key("adk-events.jsonl")][0]["event"]["error_message"] = "Backend model failure without code"
        def raw_confirmation(blobs, rows):
            rows[key("adk-events.jsonl")][0]["event"]["actions"] = {"requested_tool_confirmations": {"investigate0": {"confirmed": True}}}

        tests = [
            ("overlapping_stages", "All four stage entries precede all four stage exits", overlap),
            ("callback_invocation_mismatch", "First callback invocation differs from stage/tool invocation", callback_wrong),
            ("stage_invocation_mismatch", "First stage entry invocation differs from all other observations", stage_wrong),
            ("raw_invocation_mismatch", "All raw events use a different invocation than callback/stage/tool rows", raw_wrong),
            ("response_before_call", "First raw function-response event is moved before its matching function-call event", terminal_before_call),
        ]
        for event in ("socket.connect_ex", "socket.getaddrinfo", "socket.sendto", "socket.sendmsg"):
            tests.append(("denied_" + event, "Receipt retains denied " + event + " backend operation", denied(event)))
        tests.extend([
            ("worker_failed_after_return", "Receipt has status failed, error_type ValueError and copied_data_unchanged_during_task false", failed_receipt),
            ("governed_request_model_mismatch", "First recorded governed-request model differs from preserved compiled model", request_model),
            ("exported_model_identifier_mismatch", "Exported original model identifier contradicts preserved compiled model claim", exported_model),
            ("sdk_error_message_without_code", "First raw event retains an error_message without error_code", sdk_error_message),
            ("raw_tool_confirmation", "First raw event actions request a confirmed tool confirmation", raw_confirmation),
        ])
        for name, mutation, change in tests:
            observe(name, mutation, change)
    sdk_imported = any(name == "agent" or name.startswith(("agent.", "google.adk")) for name in sys.modules)
    accepted = sum(row["invalid_capture_accepted"] for row in observations)
    return {"schema_version": "agentops-workflow-v2-analyzer-peer-review/1",
            "analyzer_sources": sources, "baseline_status": baseline["status"],
            "baseline_questions": baseline["questions"], "case_denominator": baseline["case_denominator"],
            "mutation_count": len(observations), "invalid_capture_accepted_count": accepted,
            "mutations": observations, "original_application_or_sdk_imported": sdk_imported,
            "provider_calls": 0, "human_gold": False, "held_out_qualification": False,
            "repository_capture_mutated": False,
            "status": "constructed_analyzer_mutations_rejected" if not baseline["questions"] and not accepted else "constructed_analyzer_acceptance_gaps_observed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-rejected", action="store_true")
    args = parser.parse_args()
    result = run()
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "baseline_questions": result["baseline_questions"],
                      "mutation_count": result["mutation_count"], "invalid_capture_accepted_count": result["invalid_capture_accepted_count"],
                      "original_application_or_sdk_imported": result["original_application_or_sdk_imported"]}))
    if args.expect_rejected and (result["baseline_questions"] or result["invalid_capture_accepted_count"] or result["original_application_or_sdk_imported"]):
        raise SystemExit(1)
