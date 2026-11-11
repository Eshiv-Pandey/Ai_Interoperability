"""Reconstruct V2 before-model fixture binding and original raw correspondence.

This standard-library analyzer imports no original App, SDK or provider. Failed
and incomplete attempts remain in the same two-case development denominator.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from agentops_workflow_public_v1 import IDS, STAGES
from agentops_workflow_reference_v1 import INSTRUCTION_SHA256
from agentops_workflow_public_v1 import TOOLS
from analyze_agentops_workflow_reference_v1 import analyze as analyze_v1, function, load, parts, rows

BOUNDARY = "App before_model callback after unchanged original policy"


def event_value(event, name, camel):
    if name in event and camel in event and event[name] != event[camel]:
        return None
    return event[name] if name in event else event.get(camel)


def chronological_terminals(raw):
    """Require unique earlier raw calls, keyed by actual stage/invocation/id/name."""
    pending, seen, errors, pairs = {}, set(), [], 0
    for index, row in enumerate(raw):
        event = row["event"]
        invocation = event_value(event, "invocation_id", "invocationId")
        for part in parts(event.get("content")):
            for kind in ("function_call", "function_response"):
                fn = function(part, kind)
                if not fn:
                    continue
                key = (event.get("author"), invocation, fn.get("id"), fn.get("name"))
                if key[0] not in STAGES or not all(isinstance(value, str) and value for value in key):
                    errors.append("Raw tool call/response lacks an original stage and actual invocation/id/name")
                    continue
                if kind == "function_call":
                    if key in seen:
                        errors.append("Raw official tool call identity is duplicated")
                    else:
                        seen.add(key)
                        pending[key] = index
                elif key not in pending or pending[key] >= index:
                    errors.append("Raw official tool response has no unique earlier matching call")
                else:
                    del pending[key]
                    pairs += 1
    if pending:
        errors.append("An earlier raw official tool call has no later terminal response")
    return pairs, list(dict.fromkeys(errors))


def analyze(base):
    result = analyze_v1(base)
    result["schema_version"] = "agentops-original-workflow-capture-analysis/2"
    result["fixture_boundary"] = BOUNDARY
    for report in result["cases"]:
        case = base / report["case_id"]
        receipt = load(case / "actor-receipt.json") or {}
        models = rows(case / "model-journal.jsonl")
        stages = rows(case / "stage-observations.jsonl")
        contexts = rows(case / "tool-contexts.jsonl")
        raw = rows(case / "adk-events.jsonl")
        questions = report["questions"]
        if receipt.get("schema_version") != "agentops-original-workflow-reference/2" or receipt.get("fixture_boundary") != BOUNDARY:
            questions.append("V2 worker schema or actual fixture boundary is absent/differs")
        if (receipt.get("status") != "official_original_workflow_observed" or receipt.get("error_type")
                or receipt.get("error") or receipt.get("copied_data_unchanged_during_task") is not True
                or receipt.get("official_run_returned") is not True or receipt.get("official_runner_closed") is not True):
            questions.append("Worker failure, copied-input preservation or official return/cleanup evidence is incomplete")
        actual = receipt.get("actual_identity", {})
        pair = (actual.get("actual_sdk_user_id"), actual.get("actual_sdk_session_id"))
        if any(row.get("fixture_boundary") != BOUNDARY or row.get("actual_callback_agent_name") != row.get("stage")
               or (row.get("actual_callback_user_id"), row.get("actual_callback_session_id")) != pair
               or not row.get("actual_callback_invocation_id") for row in models):
            questions.append("Owned fixture response lacks actual governed stage/user/session/invocation binding")
        expected_invocation = actual.get("actual_sdk_invocation_id")
        invocation_ids = ([row.get("actual_callback_invocation_id") for row in models]
                          + [row.get("invocation_id") for row in stages + contexts]
                          + [event_value(row["event"], "invocation_id", "invocationId") for row in raw])
        if (not isinstance(expected_invocation, str) or not expected_invocation or not invocation_ids
                or any(identifier != expected_invocation for identifier in invocation_ids)):
            questions.append("Fixture, stage, tool and raw events do not share the one actual fresh SDK invocation")
        report["actual_sdk_invocation_id"] = expected_invocation
        lifecycle = [(row.get("kind"), row.get("stage")) for row in stages if row.get("stage") in STAGES]
        if lifecycle != [(kind, stage) for stage in STAGES for kind in ("stage_entry", "stage_exit")]:
            questions.append("Original sequential stage lifecycle is not ordered entry then exit for each stage")
        counts = {stage: sum(row.get("stage") == stage for row in models) for stage in STAGES}
        report["fixture_callback_counts"] = counts
        if receipt.get("fixture_callback_counts") != counts or not all(0 < n <= 8 for n in counts.values()) or len(models) > 24:
            questions.append("Declared before-model fixture census/bounds differ or a stage was never bound")
        if (receipt.get("model_calls") != len(models) or receipt.get("raw_official_events") != len(raw)
                or receipt.get("tool_observations") != len(contexts) or len(raw) > 80
                or any([row.get("stage_call_index") for row in models if row.get("stage") == stage] != list(range(counts[stage])) for stage in STAGES)):
            questions.append("Actual journal census, call-index sequence or event bounds differ from the worker receipt")
        nodes = receipt.get("nodes", [])
        if ([node.get("name") for node in nodes] != list(STAGES)
                or not all(node.get("compiled_node_is_distinct_exported_clone") is True
                           and node.get("compiled_model_matches_exported_original_model") is True
                           and node.get("original_node_callbacks_unchanged") is True
                           and node.get("compiled_node_callbacks_unchanged") is True
                           and node.get("compiled_instruction_sha256") == digest
                           and tuple(node.get("compiled_tools", [])) == TOOLS[node["name"]]
                           for node, digest in zip(nodes, INSTRUCTION_SHA256))):
            questions.append("Original compiled/exported clone/model/callback preservation is unproved")
        node_map = {node.get("name"): node for node in nodes}
        if any(not isinstance(node.get("original_model_identifier"), str) or not node.get("original_model_identifier")
               or node.get("original_model_identifier") != node.get("compiled_original_model_identifier")
               or not node.get("original_model_type") or node.get("original_model_type") != node.get("compiled_original_model_type")
               for node in nodes):
            questions.append("Exported and compiled original model types/identifiers do not agree")
        if any(row.get("actual_governed_request_model") != node_map.get(row.get("stage"), {}).get("compiled_original_model_identifier")
               or row.get("request", {}).get("model") != row.get("actual_governed_request_model") for row in models):
            questions.append("Actual governed request model differs from its preserved compiled model or request record")
        app_identity = receipt.get("original_app_identity", {})
        graph_names = app_identity.get("compiled_graph_node_names", [])
        if (app_identity.get("compiled_graph_container") != "list" or not isinstance(graph_names, list)
                or not all(isinstance(name, str) for name in graph_names)
                or len(graph_names) != len(set(graph_names)) or set(graph_names) != {*STAGES, "__START__"}):
            questions.append("Actual compiled list-graph name map is missing, ambiguous or differs from the original stages")
        actual_nodes = [row for row in stages if row.get("kind") == "stage_entry" and row.get("stage") in STAGES]
        if (len(actual_nodes) != 4 or not all(row.get("actual_agent_is_compiled_node") is True
                and row.get("actual_agent_is_exported_node") is False
                and row.get("actual_original_model_type") for row in actual_nodes)):
            questions.append("Actual stage execution is not bound to the preserved original compiled clones")
        if len(nodes) == len(actual_nodes) == 4 and any(
                row.get("actual_original_model_type") != node.get("compiled_original_model_type")
                or row.get("actual_original_model_identifier") != node.get("compiled_original_model_identifier")
                for row, node in zip(actual_nodes, nodes)):
            questions.append("Actual executing-stage model type/identifier differs from its preserved compiled model")
        plugins = receipt.get("runtime_plugins", [])
        if (len(plugins) != 3 or not plugins[0].endswith(".AgentOpsPolicyPlugin")
                or not plugins[1].endswith(".PublicWorkflowFixturePlugin")
                or not plugins[2].endswith(".ObservationalPlugin")):
            questions.append("Actual App plugin ordering differs from original-policy then fixture then observer")
        errors = Counter(row["event"].get("error_code") for row in raw if row["event"].get("error_code"))
        report["raw_official_error_events"] = dict(errors)
        if errors or any(row["event"].get("error_message") or row["event"].get("errorMessage") or row["event"].get("errorCode") for row in raw):
            questions.append("Raw official SDK error events remain in the actual attempt")
        if any(row["event"].get("actions", {}).get("requested_tool_confirmations")
               or row["event"].get("actions", {}).get("requestedToolConfirmations") for row in raw):
            questions.append("Raw official SDK event requested a confirmation in the read-only allocation")
        pairs, ordering_errors = chronological_terminals(raw)
        questions.extend(ordering_errors)
        report["chronological_raw_tool_terminal_pairs"] = pairs
        denials = receipt.get("denied_capability_probes", [])
        sockets = [row for row in denials if str(row.get("event", "")).startswith("socket.")]
        report["denied_socket_operation_attempts"] = dict(Counter(row["event"] for row in sockets))
        report["denied_socket_connect_attempts"] = sum(row.get("event") == "socket.connect" for row in sockets)
        if sockets:
            questions.append("Actual denied socket operations show the bounded fixture did not fully bypass network activity")
        if (denials != rows(case / "audit-denials.jsonl") or receipt.get("private_evaluator_probe_denied") is not True
                or sum(row.get("event") == "private_evaluator_open" for row in denials) != 1
                or any(row.get("event") != "private_evaluator_open" and not str(row.get("event", "")).startswith("socket.") for row in denials)):
            questions.append("Actual denial journal/private-evaluator probe is absent, altered or inconsistent")
        bootstrap = receipt.get("socket_bootstrap", {})
        if (bootstrap.get("status") != "source_bound_cold_import_without_probe_socket"
                or bootstrap.get("observed_network_attempts_during_bootstrap") != []
                or bootstrap.get("socket_operation_permission_added") is not False
                or bootstrap.get("helper_code_unchanged") is not True or bootstrap.get("cold_import_before_App") is not True
                or type(bootstrap.get("restored_socket_has_ipv6")) is not bool or type(bootstrap.get("original_socket_has_ipv6")) is not bool
                or bootstrap.get("restored_socket_has_ipv6") != bootstrap.get("original_socket_has_ipv6")):
            questions.append("The disclosed source-bound no-socket bootstrap is not established")
        report["actual_original_stage_bindings"] = actual_nodes
        report["status"] = "observed_workflow_correspondence_consistent" if not questions else "observed_workflow_incomplete_or_inconsistent"
    result["questions"] = sum(len(report["questions"]) for report in result["cases"])
    result["status"] = "retained_development_workflow_consistent" if not result["questions"] else "retained_development_workflow_partial_or_inconsistent"
    return result


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
