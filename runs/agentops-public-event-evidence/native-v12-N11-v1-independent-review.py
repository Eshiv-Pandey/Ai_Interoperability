"""Independent read-only audit; does not import or execute the normalizer."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2]
EXPORT = SCRIPT.parent / "native-v12-N11-v1"
SOFTWARE = SCRIPT.parent / "software-v1"
OUTPUT = SCRIPT.with_suffix(".json")
EXPECTED_MODULE = "c008b818befafa4c212a8978ecbc28e927a54d3720fd8fe34ab1f873252f53e5"
CHECKS = []


def check(name, condition, details=None):
    row = {"check": name, "passed": bool(condition)}
    if details is not None:
        row["details"] = details
    CHECKS.append(row)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def equal(left, right):
    return canonical(left) == canonical(right)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def decode(raw):
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    canonical(value)
    return value


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def label(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def regular(path):
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("Linked/reparse evidence input: " + str(component))
    if not path.is_file():
        raise ValueError("Not a regular evidence file: " + str(path))
    return path


def inventory(directory):
    return {path.relative_to(directory).as_posix(): path for path in sorted(directory.rglob("*")) if path.is_file()}


def hash_paths(paths):
    return {label(path): digest(regular(path).read_bytes()) for path in sorted(set(paths))}


def semantic_part(part):
    result = dict(part)
    if isinstance(result.get("text"), str) and "data" not in result:
        if result.get("mediaType") == "text/plain":
            del result["mediaType"]
        if result.get("kind") == "text":
            del result["kind"]
    elif isinstance(result.get("data"), dict) and result.get("kind") == "data":
        del result["kind"]
    if result.get("metadata") is None:
        result.pop("metadata", None)
    return result


def audit():
    report = {"schema_version": "agentops-public-event-independent-review/1", "status": "failed",
              "review_type": "Independent AI evidence audit; not human review",
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "normalizer_executed": False, "sdk_imported": False, "application_requests": 0,
              "model_calls": 0, "fresh_native_runs": 0, "graded_task_outcomes": 0,
              "scope": "Historical N11 public-wire normalization and captured software evidence only",
              "client_receipt_proven": False, "causal_order_proven": False, "complete_event_stream_proven": False}
    groups = {}
    monitored = []
    before = None
    try:
        plan = decode((EXPORT / "plan.json").read_bytes())
        receipt = decode((EXPORT / "result.json").read_bytes())
        observed = decode((EXPORT / "observations.json").read_bytes())
        software_plan = decode((SOFTWARE / "plan.json").read_bytes())
        software_receipt = decode((SOFTWARE / "result.json").read_bytes())
        wire = Path(plan["wire_root"])
        groups = {"original_wire": inventory(wire), "export": inventory(EXPORT), "software": inventory(SOFTWARE),
                  "authored_software_sources": {name: ROOT / name for name in software_plan["source_files"]}}
        monitored = [path for group in groups.values() for path in group.values()] + [SCRIPT]
        before = hash_paths(monitored)
        report["input_manifests"] = {name: [{"path": relative, **before[label(path)]} for relative, path in group.items()]
                                     for name, group in groups.items()}
        report["monitored_before"] = before
        report["review_script"] = {"path": label(SCRIPT), **before[label(SCRIPT)]}
        expected_wire = {f"{sequence:06d}/{name}" for sequence in range(1, 10) for name in plan["original_source_files"]}
        check("45 original wire files and exact exchange membership", set(groups["original_wire"]) == expected_wire and len(expected_wire) == 45)
        copied_wire = {name[5:]: path for name, path in groups["export"].items() if name.startswith("wire/")}
        check("45 copied wire files and exact membership", set(copied_wire) == expected_wire)
        copy_mismatches = [name for name in expected_wire if groups["original_wire"][name].read_bytes() != copied_wire[name].read_bytes()]
        check("all original and copied wire bytes equal", not copy_mismatches, copy_mismatches)
        manifest = receipt["files"]
        listed = {item["path"]: {"bytes": item["bytes"], "sha256": item["sha256"]} for item in manifest}
        check("export manifest unique and complete", len(listed) == len(manifest) == 49 and set(listed) | {"result.json"} == set(groups["export"]))
        check("export manifest hashes and sizes exact", all(before[label(EXPORT / name)] == value for name, value in listed.items()))
        check("pinned normalizer identity matches export and software", plan["exporter_sha256"] == EXPECTED_MODULE
              == before[label(EXPORT / "source/agentops_public_events_v1.py")]["sha256"]
              == software_plan["source_files"]["src/interoperability/agentops_public_events_v1.py"]["sha256"])
        check("export helper identity exact", plan["helper_sha256"] == before[label(EXPORT / "source/agentops_raw_events_v1.py")]["sha256"])
        check("software plan and receipt source manifests agree", equal(software_plan["source_files"], software_receipt["source_files"]))
        software_expected = {"plan.json", "result.json", "stdout.txt", "stderr.txt"} | {"workspace/" + name for name in software_plan["source_files"]}
        check("captured software exact file membership", set(groups["software"]) == software_expected)
        for name, expected in software_plan["source_files"].items():
            original = ROOT / name
            captured = SOFTWARE / "workspace" / name
            check("software original and captured bytes: " + name,
                  before[label(original)] == expected == before[label(captured)] and original.read_bytes() == captured.read_bytes())
        for name in ("agentops_public_events_v1.py", "agentops_raw_events_v1.py"):
            check("export and tested software copy: " + name,
                  (EXPORT / "source" / name).read_bytes() == (SOFTWARE / "workspace/src/interoperability" / name).read_bytes())
        stdout, stderr = (SOFTWARE / "stdout.txt").read_bytes(), (SOFTWARE / "stderr.txt").read_bytes()
        check("captured stdout and stderr hashes match receipt", digest(stdout) == software_receipt["stdout"] and digest(stderr) == software_receipt["stderr"])
        stderr_text = stderr.decode("utf-8")
        passing = [match.group(1) for line in stderr_text.splitlines()
                   if (match := re.fullmatch(r"(test_\w+) .* \.\.\. ok", line))]
        syntax = ast.parse((SOFTWARE / "workspace/tests/test_agentops_public_events_v1.py").read_text(encoding="utf-8"))
        defined = [node.name for node in ast.walk(syntax) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        check("stderr independently reports all 17 defined tests passing", len(passing) == len(defined) == 17 and set(passing) == set(defined)
              and any(re.fullmatch(r"Ran 17 tests in [0-9.]+s", line) for line in stderr_text.splitlines())
              and stderr_text.rstrip().endswith("OK") and "skipped" not in stderr_text.lower() and "FAILED" not in stderr_text)
        check("software receipt successful with zero skips", software_receipt["status"] == "passed" and software_receipt["exit_code"] == 0
              and software_receipt["tests_run"] == 17 and software_receipt["skips"] == 0 and software_receipt["error"] is None
              and software_receipt["original_and_captured_source_unchanged"] is True)
        check("software command uses captured workspace and focused suite", Path(software_plan["cwd"]) == SOFTWARE / "workspace"
              and software_plan["command"][1:] == ["-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_agentops_public_events_v1.py", "-v"])
        check("software declares no model/application/archive run", all(software_receipt[name] == 0 for name in ("application_requests", "model_calls", "original_archives_exported")))

        expected_parts, expected_messages, raw_records, associations = {}, {}, {}, {}
        artifact_counts, states = [], []

        def add_message(message, task_id, context_id, profile, sequence, location):
            identity = message["messageId"]
            key = (profile, task_id, context_id, identity)
            role = {"ROLE_USER": "user", "ROLE_AGENT": "agent"}[message["role"]]
            row = expected_messages.setdefault(key, {"message_id": identity, "task_id": task_id, "context_id": context_id,
                                                    "protocol_version_header": profile, "role": role, "representations": []})
            row["representations"].append({"capture_sequence": sequence, "location": location, "message": message})
            check(f"raw message binding {sequence}/{location}/{identity}", all(message.get(field, expected) == expected
                  for field, expected in (("taskId", task_id), ("contextId", context_id))) and row["role"] == role)
            container = {name: value for name, value in message.items() if name != "parts"}
            for index, part in enumerate(message.get("parts", [])):
                add_part("message", identity, index, part, container, task_id, context_id, profile, sequence, location)

        def add_part(namespace, identity, index, part, container, task_id, context_id, profile, sequence, location):
            key = (profile, task_id, context_id, namespace, identity, index)
            representation = {"capture_sequence": sequence, "location": location, "container": container, "part": part}
            if key not in expected_parts:
                expected_parts[key] = {"part": part, "container": container, "representations": []}
            else:
                previous = expected_parts[key]
                consistent = equal(previous["part"], part) and equal(previous["container"], container) if namespace == "artifact_event" else equal(semantic_part(previous["part"]), semantic_part(part))
                check(f"raw repeated part consistent {sequence}/{namespace}/{identity}/{index}", consistent)
            expected_parts[key]["representations"].append(representation)

        normalized_records = {row["capture_sequence"]: row for row in observed["records"]}
        check("nine normalized records with unique sequences", len(normalized_records) == len(observed["records"]) == 9 and set(normalized_records) == set(range(1, 10)))
        for sequence in range(1, 10):
            directory = f"{sequence:06d}"
            metadata = decode(groups["original_wire"][directory + "/exchange.json"].read_bytes())
            request_raw = groups["original_wire"][directory + "/request.body.bin"].read_bytes()
            response_raw = groups["original_wire"][directory + "/response.body.bin"].read_bytes()
            versions = [value for name, value in metadata["request_headers"] if name.lower() == "a2a-version"]
            profile = versions[0] if versions else "not-declared"
            response = decode(response_raw)
            record = normalized_records[sequence]
            check(f"raw exchange completeness and byte counters {sequence}", metadata["sequence"] == sequence
                  and metadata["schema_version"] == "agentops-asgi-exchange/1" and metadata["request_body_complete"] is True
                  and metadata["response_body_complete"] is True and metadata["request_bytes"] == len(request_raw)
                  and metadata["response_bytes"] == len(response_raw) and metadata["response_status"] == 200 and len(versions) <= 1)
            fields = {"capture_sequence": sequence, "method": metadata["method"], "path": metadata["path"],
                      "http_status": metadata["response_status"], "started_at_utc": metadata["started_at_utc"],
                      "finished_at_utc": metadata["finished_at_utc"], "protocol_version_header": profile,
                      "request_body": digest(request_raw), "response_body": digest(response_raw)}
            check(f"normalized record exact envelope and body digests {sequence}", all(equal(record[name], value) for name, value in fields.items()))
            if sequence == 1:
                check("agent card exact and non-RPC", metadata["method"] == "GET" and request_raw == b""
                      and record["outcome"] == "agent_card" and equal(record["card"], response))
                continue
            request = decode(request_raw)
            check(f"JSON-RPC envelope and exact response identity {sequence}", request["jsonrpc"] == response["jsonrpc"] == "2.0"
                  and type(request["id"]) is type(response["id"]) and request["id"] == response["id"])
            task = response["result"]["task"] if request["method"] == "SendMessage" else response["result"]
            task_id, context_id = task["id"], task["contextId"]
            check(f"A2A 1.0 wrapped/direct task shape {sequence}", request["method"] in ("SendMessage", "GetTask")
                  and "kind" not in task and record["task_shape"] == ("wrapped_task" if request["method"] == "SendMessage" else "direct_task"))
            check(f"normalized request response and task exact {sequence}", equal(record["request"], request)
                  and equal(record["response"], response) and equal(record["task"], task) and record["outcome"] == "task")
            check(f"task context association stable {sequence}", associations.get(task_id, context_id) == context_id)
            associations[task_id] = context_id
            states.append(task["status"]["state"])
            check(f"normalized state exact {sequence}", record["state"] == task["status"]["state"].removeprefix("TASK_STATE_").lower().replace("_", "-"))
            if request["method"] == "SendMessage":
                add_message(request["params"]["message"], task_id, context_id, profile, sequence, "request")
            else:
                check(f"GetTask requested exact task {sequence}", request["params"]["id"] == task_id)
            artifacts = task.get("artifacts", [])
            artifact_counts.append(len(artifacts))
            for artifact in artifacts:
                identity = artifact["metadata"]["adk_event_id"]
                container = {name: value for name, value in artifact.items() if name != "parts"}
                for index, part in enumerate(artifact["parts"]):
                    add_part("artifact_event", identity, index, part, container, task_id, context_id, profile, sequence, "artifact")
            if "message" in task["status"]:
                add_message(task["status"]["message"], task_id, context_id, profile, sequence, "status")
            for message in task.get("history", []):
                add_message(message, task_id, context_id, profile, sequence, "history")
            raw_records[sequence] = task

        actual_parts = {(row["protocol_version_header"], row["task_id"], row["context_id"], row["namespace"], row["identity"], row["part_index"]): row for row in observed["observations"]}
        check("seven unique parts exactly match independently derived identities", len(actual_parts) == len(observed["observations"]) == len(expected_parts) == 7 and set(actual_parts) == set(expected_parts))
        for key, expected in expected_parts.items():
            row = actual_parts[key]
            check("every exact part and representation: " + key[3] + "/" + key[4], equal(row["part"], expected["part"])
                  and equal(row["container"], expected["container"]) and equal(row["representations"], expected["representations"])
                  and row["observed_in_sequences"] == [item["capture_sequence"] for item in expected["representations"]]
                  and row["first_capture_sequence"] == expected["representations"][0]["capture_sequence"])
            kind = expected["part"].get("metadata", {}).get("adk_type")
            identity = expected["part"].get("data", {}).get("id") if kind in ("function_call", "function_response") else None
            check("derived function/event classification: " + key[4], row["adk_type"] == kind and row["function_id"] == identity
                  and row["adk_event_id"] == (key[4] if key[3] == "artifact_event" else None))
        actual_messages = {(row["protocol_version_header"], row["task_id"], row["context_id"], row["message_id"]): row for row in observed["messages"]}
        check("four messages and all raw request/status/history representations exact", len(actual_messages) == len(observed["messages"]) == len(expected_messages) == 4
              and set(actual_messages) == set(expected_messages) and all(equal(actual_messages[key], value) for key, value in expected_messages.items()))
        empty = [row for row in actual_messages.values() if all(not representation["message"].get("parts", []) for representation in row["representations"])]
        check("empty working message retained with original ADK metadata", len(empty) == 1 and len(empty[0]["representations"]) == 5
              and all("parts" not in item["message"] and item["message"]["metadata"].get("adk_event_id") for item in empty[0]["representations"]))
        calls = [row for row in observed["observations"] if row["adk_type"] == "function_call"]
        responses = [row for row in observed["observations"] if row["adk_type"] == "function_response"]
        confirmation = [row for row in calls if row["part"]["data"]["name"] == "adk_request_confirmation"]
        check("confirmation message has no fabricated ADK event identity", len(confirmation) == 1 and confirmation[0]["adk_event_id"] is None
              and all("adk_event_id" not in item["container"].get("metadata", {}) for item in confirmation[0]["representations"]))
        action_call = [row for row in calls if row["part"]["data"]["name"] == "restart_service"]
        action_replies = [row for row in responses if row["part"]["data"]["name"] == "restart_service"]
        pending = [row for row in action_replies if "error" in row["part"]["data"]["response"]]
        executed = [row for row in action_replies if "result" in row["part"]["data"]["response"] and "audit" in row["part"]["data"]["response"]]
        check("pending and executed response phases stay distinct despite shared call ID", len(action_call) == 1 and len(pending) == len(executed) == 1
              and pending[0]["function_id"] == executed[0]["function_id"] == action_call[0]["function_id"]
              and pending[0]["adk_event_id"] != executed[0]["adk_event_id"] and pending[0]["first_capture_sequence"] < executed[0]["first_capture_sequence"]
              and not equal(pending[0]["part"], executed[0]["part"]))
        check("nested originalFunctionCall is a binding, not a duplicate call", len(calls) == 2
              and equal(confirmation[0]["part"]["data"]["args"]["originalFunctionCall"], action_call[0]["part"]["data"]))
        repeated = sum(len(value["representations"]) - 1 for value in expected_parts.values())
        check("cumulative artifacts and repeats independently match archive", artifact_counts == [0, 0, 1, 1, 2, 4, 4, 4]
              and repeated == 26 == observed["identical_repeated_parts"] == receipt["identical_repeated_parts"])
        counts = {"capture_exchanges": 9, "task_replies": 8, "unique_parts": 7, "distinct_messages": 4,
                  "distinct_tasks": 1, "function_calls": 2, "function_responses": 3}
        check("receipt counts independently established", len(raw_records) == 8 and len(associations) == 1 and len(calls) == 2 and len(responses) == 3
              and all(receipt[name] == value for name, value in counts.items()) and equal(observed["task_context_associations"], associations))
        check("successful normalization with unchanged source and captures", receipt["status"] == "passed"
              and all(receipt[name] is True for name in ("source_unchanged", "captured_files_unchanged", "implementation_sources_unchanged", "normalization_complete"))
              and observed["normalization_complete"] is True and receipt["unsupported_sequences"] == observed["unsupported_sequences"] == [])
        check("public limits and zero fresh execution/grading claims retained", all(receipt[name] is False and observed[name] is False
              for name in ("client_receipt_proven", "causal_order_proven", "complete_event_stream_proven"))
              and all(receipt[name] == 0 for name in ("application_requests", "model_calls", "graded_task_outcomes"))
              and observed["graded_task_outcomes"] == 0 and "Server-observed" in receipt["visibility"]
              and "no upstream-case association" in receipt["interpretation"])
        report["verified_counts"] = {**counts, "original_wire_files": 45, "copied_wire_files": 45,
                                     "identical_repeated_parts": repeated, "tests_run": 17, "test_skips": 0}
        report["historical_fixture"] = {"prompt": "Restart inventory.", "artifact_counts_by_task_reply": artifact_counts,
                                         "task_states_by_capture": states, "upstream_source_cases_graded": 0}
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        check("audit completed without an exception", False)
    finally:
        try:
            after = hash_paths(monitored)
            report["monitored_after"] = after
            check("all monitored before/after hashes unchanged", before is not None and before == after)
            check("original wire export and software membership unchanged", bool(groups)
                  and all(set(groups[name]) == set(inventory(directory)) for name, directory in
                          (("original_wire", wire), ("export", EXPORT), ("software", SOFTWARE))))
        except Exception as error:
            report["preservation_error"] = f"{type(error).__name__}: {error}"
            check("audit preservation completed", False)
        report["checks"] = CHECKS
        report["checks_passed"] = sum(row["passed"] for row in CHECKS)
        report["checks_failed"] = sum(not row["passed"] for row in CHECKS)
        report["status"] = "passed" if CHECKS and all(row["passed"] for row in CHECKS) else "failed"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        with OUTPUT.open("xb") as stream:
            stream.write((json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "checks_passed": report["checks_passed"],
                      "checks_failed": report["checks_failed"], "verified_counts": report.get("verified_counts"),
                      "error": report.get("error"), "output": str(OUTPUT)}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise SystemExit("Refusing consumed independent review output")
    raise SystemExit(audit())
