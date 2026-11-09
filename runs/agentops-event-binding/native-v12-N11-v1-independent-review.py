"""Bounded independent audit of frozen N11 binding evidence; stdlib only."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import stat


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2]
BINDING = SCRIPT.parent / "native-v12-N11-v1"
SOFTWARE = SCRIPT.parent / "software-v1"
OUTPUT = SCRIPT.with_suffix(".json")
MODULE_SHA = "d3beb0f2440d5698124bc7aedf27a8beb34136f60e15e70be1c7b6745da08fa5"
TEST_SHA = "0cccbdfed7ace4ece037d64969d2f1594df5c5b8cb9895e32bd92b8f068a2396"
KINDS = {"function_call", "function_response"}
CHECKS = []


def check(name, condition, details=None):
    row = {"check": name, "passed": bool(condition)}
    if details is not None:
        row["details"] = details
    CHECKS.append(row)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def exact(left, right):
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


def hashes(paths):
    return {label(path): digest(regular(path).read_bytes()) for path in sorted(set(paths))}


def differences(raw, public, path=()):
    """List every value/type difference without applying a numeric exception."""
    if type(raw) is not type(public):
        return [{"path": list(path), "raw_type": type(raw).__name__, "public_type": type(public).__name__,
                 "raw": raw, "public": public}]
    if type(raw) is dict:
        if raw.keys() != public.keys():
            return [{"path": list(path), "reason": "different_object_members"}]
        return [difference for key in raw for difference in differences(raw[key], public[key], path + (key,))]
    if type(raw) is list:
        if len(raw) != len(public):
            return [{"path": list(path), "reason": "different_list_length"}]
        return [difference for index, (left, right) in enumerate(zip(raw, public))
                for difference in differences(left, right, path + (index,))]
    return [] if raw == public else [{"path": list(path), "reason": "different_value", "raw": raw, "public": public}]


def relation(raw, public, kind):
    changed = differences(raw, public)
    allowed = all(kind == "function_response" and item.get("path") in
                  (["response", "audit", "id"], ["response", "audit", "schema_version"])
                  and item.get("raw_type") == "int" and item.get("public_type") == "float"
                  and type(item.get("raw")) is int and type(item.get("public")) is float
                  and 0 <= item["raw"] <= 2**53 - 1 and math.isfinite(item["public"])
                  and item["public"].is_integer() and item["public"] == item["raw"] for item in changed)
    return allowed, changed


def manifest(directory, receipt, before):
    entries = receipt["files"]
    indexed = {entry["path"]: {"bytes": entry["bytes"], "sha256": entry["sha256"]} for entry in entries}
    check("unique complete manifest: " + label(directory), len(indexed) == len(entries)
          and set(indexed) | {"result.json"} == set(inventory(directory)))
    check("manifest hashes and sizes: " + label(directory), all(before[label(directory / name)] == value for name, value in indexed.items()))
    return indexed


def audit():
    report = {"schema_version": "agentops-event-binding-independent-review/1", "status": "failed",
              "review_type": "Independent AI evidence audit; not human review",
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Frozen N11 raw/public function relations, copied evidence and captured software only",
              "comparator_executed": False, "exporters_executed": False, "sdk_imported": False,
              "database_engine_used": False, "application_requests": 0, "model_calls": 0,
              "fresh_native_runs": 0, "graded_task_outcomes": 0, "causal_order_proven": False,
              "client_receipt_proven": False, "complete_event_stream_proven": False, "source_authenticity_proven": False}
    groups, directories, monitored, before = {}, {}, [], None
    try:
        plan = decode((BINDING / "plan.json").read_bytes())
        result = decode((BINDING / "result.json").read_bytes())
        software_plan = decode((SOFTWARE / "plan.json").read_bytes())
        software_result = decode((SOFTWARE / "result.json").read_bytes())
        raw_root, public_root = Path(plan["raw_export"]), Path(plan["public_export"])
        directories = {"binding": BINDING, "original_raw": raw_root, "original_public": public_root, "software": SOFTWARE}
        groups = {name: inventory(path) for name, path in directories.items()}
        groups["authored_software_sources"] = {name: ROOT / name for name in software_plan["source_files"]}
        monitored = [path for group in groups.values() for path in group.values()] + [SCRIPT]
        before = hashes(monitored)
        report["monitored_before"] = before
        report["input_manifests"] = {name: [{"path": relative, **before[label(path)]} for relative, path in files.items()]
                                     for name, files in groups.items()}
        report["review_script"] = {"path": label(SCRIPT), **before[label(SCRIPT)]}
        raw_result, public_result = decode((raw_root / "result.json").read_bytes()), decode((public_root / "result.json").read_bytes())
        raw_plan, public_plan = decode((raw_root / "plan.json").read_bytes()), decode((public_root / "plan.json").read_bytes())
        binding_manifest = manifest(BINDING, result, before)
        raw_manifest, public_manifest = manifest(raw_root, raw_result, before), manifest(public_root, public_result, before)
        check("expected allocation counts", len(groups["binding"]) == 63 and len(binding_manifest) == 62
              and len(groups["original_raw"]) == 9 and len(raw_manifest) == 8
              and len(groups["original_public"]) == 50 and len(public_manifest) == 49)
        for kind, directory in (("raw", raw_root), ("public", public_root)):
            originals = groups["original_" + kind]
            copied = {name[len("inputs/" + kind + "/"):]: path for name, path in groups["binding"].items()
                      if name.startswith("inputs/" + kind + "/")}
            check("copied input exact membership: " + kind, set(copied) == set(originals))
            check("copied input all bytes exact: " + kind, all(originals[name].read_bytes() == copied[name].read_bytes() for name in originals))
            check("input receipt identity anchored to original: " + kind, result["input_receipts"][kind] == before[label(directory / "result.json")])
        for name, source in (("binding", result), ("raw", raw_result), ("public", public_result)):
            check("input/output success and claim limits: " + name, source["status"] == "passed"
                  and source["application_requests"] == source["model_calls"] == source["graded_task_outcomes"] == 0
                  and source["causal_order_proven"] is False and source["complete_event_stream_proven"] is False)
        check("binding preservation and all proof limits", all(result[name] is True for name in
              ("inputs_unchanged", "implementation_unchanged", "captured_files_unchanged", "input_manifests_verified"))
              and result["client_receipt_proven"] is False and result["source_authenticity_proven"] is False
              and "no source authentication" in result["claim_limit"] and "admission qualification" in result["claim_limit"])
        check("original input preservation claims", all(source[name] is True for source in (raw_result, public_result)
              for name in ("source_unchanged", "captured_files_unchanged")))
        check("raw database and exporter copies bound to prior receipt/plan bytes", digest((raw_root / "input/runtime.db").read_bytes()) == raw_result["database"]
              and digest((raw_root / "exporter.py").read_bytes())["sha256"] == raw_plan["exporter_sha256"])
        check("public copied source identity and raw helper agree", digest((public_root / "source/agentops_public_events_v1.py").read_bytes())["sha256"] == public_plan["exporter_sha256"]
              and digest((public_root / "source/agentops_raw_events_v1.py").read_bytes())["sha256"] == public_plan["helper_sha256"]
              and (raw_root / "exporter.py").read_bytes() == (public_root / "source/agentops_raw_events_v1.py").read_bytes()
              == (BINDING / "source/agentops_raw_events_v1.py").read_bytes())
        check("binding source frozen identity", plan["implementation_sha256"] == MODULE_SHA == before[label(BINDING / "source/agentops_event_binding_v1.py")]["sha256"]
              and plan["helper_sha256"] == before[label(BINDING / "source/agentops_raw_events_v1.py")]["sha256"])
        check("software source plan and result agree", exact(software_plan["source_files"], software_result["source_files"]))
        expected_software = {"plan.json", "result.json", "stdout.txt", "stderr.txt"} | {"workspace/" + name for name in software_plan["source_files"]}
        check("software exact allocation membership", set(groups["software"]) == expected_software)
        for name, expected in software_plan["source_files"].items():
            original, copied = ROOT / name, SOFTWARE / "workspace" / name
            check("tested source copies and original: " + name, before[label(original)] == expected == before[label(copied)]
                  and original.read_bytes() == copied.read_bytes())
        check("tested frozen module and test identities", software_plan["source_files"]["src/interoperability/agentops_event_binding_v1.py"]["sha256"] == MODULE_SHA
              and software_plan["source_files"]["tests/test_agentops_event_binding_v1.py"]["sha256"] == TEST_SHA
              and (SOFTWARE / "workspace/src/interoperability/agentops_event_binding_v1.py").read_bytes()
              == (BINDING / "source/agentops_event_binding_v1.py").read_bytes())
        stdout, stderr = (SOFTWARE / "stdout.txt").read_bytes(), (SOFTWARE / "stderr.txt").read_bytes()
        check("software stdout/stderr exact receipt hashes", digest(stdout) == software_result["stdout"] and digest(stderr) == software_result["stderr"])
        lines = stderr.decode("utf-8").splitlines()
        passing = [match.group(1) for line in lines if (match := re.fullmatch(r"(test_\w+) .* \.\.\. ok", line))]
        syntax = ast.parse((SOFTWARE / "workspace/tests/test_agentops_event_binding_v1.py").read_text(encoding="utf-8"))
        defined = [node.name for node in ast.walk(syntax) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        check("all 15 captured tests independently listed as passing", len(passing) == len(defined) == 15 and set(passing) == set(defined)
              and any(re.fullmatch(r"Ran 15 tests in [0-9.]+s", line) for line in lines) and stderr.decode("utf-8").rstrip().endswith("OK"))
        check("software successful with zero skips and execution claims", software_result["status"] == "passed" and software_result["exit_code"] == 0
              and software_result["tests_run"] == 15 and software_result["skips"] == 0 and software_result["error"] is None
              and software_result["original_and_captured_source_unchanged"] is True
              and all(software_result[name] == 0 for name in ("application_requests", "model_calls", "original_archives_exported"))
              and not any("skipped" in line.lower() or "FAILED" in line for line in lines))
        check("software command bound to captured workspace and focused suite", Path(software_plan["cwd"]) == SOFTWARE / "workspace"
              and software_plan["command"][1:] == ["-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_agentops_event_binding_v1.py", "-v"])

        decoded = decode((raw_root / "decoded-tables.json").read_bytes())
        raw_tables = decode((raw_root / "raw-tables.json").read_bytes())
        raw_parts = decode((raw_root / "function-observations.json").read_bytes())
        public_view = decode((public_root / "observations.json").read_bytes())
        public_parts = [part for part in public_view["observations"] if part["adk_type"] in KINDS]
        check("raw/public independently contain five function parts", len(raw_parts) == len(public_parts) == 5
              and raw_result["function_calls"] == public_result["function_calls"] == 2
              and raw_result["function_responses"] == public_result["function_responses"] == 3)
        task_rows = {row["id"]: row for row in decoded["tasks"]}
        session_rows = {(row["app_name"], row["user_id"], row["id"]): row for row in decoded["sessions"]}
        expected_bindings = {}
        for task_id, context in public_view["task_context_associations"].items():
            task = task_rows[task_id]
            metadata = task["metadata"]
            scope = (metadata["adk_app_name"], metadata["adk_user_id"], metadata["adk_session_id"])
            check("runtime task explicitly references an existing real session: " + task_id, task["context_id"] == context
                  and scope in session_rows and all(type(value) is str and value for value in scope))
            expected_bindings[task_id] = {"context_id": context, "app_name": scope[0], "user_id": scope[1], "session_id": scope[2],
                                          "mapping_basis": "Recorded task context and explicit ADK task metadata reference an existing session row"}
        check("reported task/session bindings exact", len(expected_bindings) == 1 and exact(result["task_session_bindings"], expected_bindings))
        events = {(row["id"], row["app_name"], row["user_id"], row["session_id"]): row for row in decoded["events"]}
        raw_events = {(row["id"], row["app_name"], row["user_id"], row["session_id"]): row for row in raw_tables["events"]}
        for part in raw_parts:
            key = (part["event_id"], part["app_name"], part["user_id"], part["session_id"])
            row = events[key]
            event = row["event_data"]
            source_part = event["content"]["parts"][part["part_index"]][part["kind"]]
            check("raw function projected from matching encoded event row: " + part["event_id"], exact(decode(raw_events[key]["event_data"].encode("utf-8")), event)
                  and exact(source_part, part["function"]) and event["id"] == part["event_id"] and event["invocation_id"] == row["invocation_id"] == part["invocation_id"]
                  and event["author"] == part["author"] and part["event_rowid"] == row["sqlite_rowid"] and exact(part["event_timestamp"], event["timestamp"])
                  and exact(part["database_timestamp"], row["timestamp"]) and all(field not in event or event[field] == row[field]
                  for field in ("app_name", "user_id", "session_id")))

        origins = {}
        task_replies = 0
        for sequence in range(1, 10):
            prefix = public_root / "wire" / f"{sequence:06d}"
            exchange = decode((prefix / "exchange.json").read_bytes())
            request_bytes, response_bytes = (prefix / "request.body.bin").read_bytes(), (prefix / "response.body.bin").read_bytes()
            check("copied wire exact counters and completeness: " + str(sequence), exchange["sequence"] == sequence
                  and exchange["request_bytes"] == len(request_bytes) and exchange["response_bytes"] == len(response_bytes)
                  and exchange["request_body_complete"] is True and exchange["response_body_complete"] is True)
            if exchange["method"] != "POST":
                continue
            request, response = decode(request_bytes), decode(response_bytes)
            task = response["result"]["task"] if "task" in response["result"] else response["result"]
            task_replies += 1
            versions = [value for name, value in exchange["request_headers"] if name.lower() == "a2a-version"]
            profile = versions[0] if versions else "not-declared"
            containers = [("artifact_event", item["metadata"]["adk_event_id"], "artifact", item) for item in task.get("artifacts", [])]
            containers += [("message", item["messageId"], "history", item) for item in task.get("history", [])]
            if task["status"].get("message") is not None:
                item = task["status"]["message"]
                containers.append(("message", item["messageId"], "status", item))
            if request["params"].get("message") is not None:
                item = request["params"]["message"]
                containers.append(("message", item["messageId"], "request", item))
            for namespace, identity, location, container in containers:
                for index, part in enumerate(container.get("parts", [])):
                    if part.get("metadata", {}).get("adk_type") not in KINDS:
                        continue
                    key = (namespace, identity, index, task["id"], task["contextId"], profile, sequence, location)
                    check("each raw public origin unique: " + str(key), key not in origins)
                    origins[key] = {"part": part, "container": {name: value for name, value in container.items() if name != "parts"}}
        covered = set()
        for part in public_parts:
            for representation in part["representations"]:
                key = (part["namespace"], part["identity"], part["part_index"], part["task_id"], part["context_id"],
                       part["protocol_version_header"], representation["capture_sequence"], representation["location"])
                check("public function representation exact source and exclusive: " + str(key), key in origins and key not in covered
                      and exact(origins[key]["part"], representation["part"]) and exact(origins[key]["container"], representation["container"])
                      and exact(part["part"], representation["part"]))
                covered.add(key)
        check("all copied public function origins covered exactly once", covered == set(origins) and task_replies == 8)
        indexed_public = {(part["namespace"], part["identity"], part["part_index"], part["task_id"]): part for part in public_parts}
        pair_keys = [(pair["public_namespace"], pair["public_identity"], pair["public_part_index"], pair["task_id"]) for pair in result["pairs"]]
        check("five unique reported public relations cover all five parts", len(pair_keys) == len(set(pair_keys)) == 5 and set(pair_keys) == set(indexed_public))
        audited_relations, numeric_differences = [], []
        for pair in result["pairs"]:
            key = (pair["public_namespace"], pair["public_identity"], pair["public_part_index"], pair["task_id"])
            public = indexed_public[key]
            binding = expected_bindings[pair["task_id"]]
            scoped = [part for part in raw_parts if all(part[field] == binding[field] for field in ("app_name", "user_id", "session_id"))]
            if public["namespace"] == "artifact_event":
                metadata = public["container"]["metadata"]
                candidates = [part for part in scoped if part["event_id"] == public["adk_event_id"] and part["part_index"] == public["part_index"]]
                check("artifact recorded identity exact: " + public["identity"], len(candidates) == 1 and pair["event_identity_proven"] is True
                      and pair["public_adk_event_id"] == public["identity"] == public["adk_event_id"] == metadata["adk_event_id"]
                      and candidates[0]["invocation_id"] == metadata["adk_invocation_id"] and candidates[0]["author"] == metadata["adk_author"])
            else:
                candidates = [part for part in scoped if part["kind"] == public["adk_type"] and relation(part["function"], public["part"]["data"], part["kind"])[0]]
                check("message unique payload mapping retains missing public ADK identity: " + public["identity"], len(candidates) == 1
                      and pair["event_identity_proven"] is False and pair["public_adk_event_id"] is None and public["adk_event_id"] is None
                      and "public ADK event identity remains absent" in pair["mapping_basis"]
                      and all(not any(field in container.get("metadata", {}) for field in ("adk_event_id", "adk_invocation_id", "adk_author"))
                              for container in [public["container"], *(rep["container"] for rep in public["representations"])]))
            raw = candidates[0]
            compatible, changed = relation(raw["function"], public["part"]["data"], raw["kind"])
            check("full raw/public payload relation and reported row exact: " + public["identity"], compatible and raw["kind"] == public["adk_type"] == pair["kind"]
                  and pair["function_id"] == raw["function_id"] == public["function_id"] and pair["function_name"] == raw["function"]["name"]
                  and pair["matched_raw_event_id"] == raw["event_id"] and pair["matched_raw_part_index"] == raw["part_index"]
                  and pair["matched_raw_invocation_id"] == raw["invocation_id"] and pair["matched_raw_author"] == raw["author"]
                  and all(pair[field] == binding[field] for field in ("app_name", "user_id", "session_id", "context_id")))
            numeric_differences.extend({"public_identity": public["identity"], **item} for item in changed)
            audited_relations.append({"public_namespace": public["namespace"], "public_identity": public["identity"],
                                      "matched_raw_event_id": raw["event_id"], "kind": raw["kind"], "function_id": raw["function_id"],
                                      "recorded_identity": pair["event_identity_proven"], "numeric_differences": changed})
        check("five unique matched raw function identities", len({(pair["matched_raw_event_id"], pair["matched_raw_part_index"])
              for pair in result["pairs"]}) == 5)
        check("only two declared audit integer-to-float differences occur", len(numeric_differences) == 2
              and {tuple(item["path"]) for item in numeric_differences} == {("response", "audit", "id"), ("response", "audit", "schema_version")}
              and all(item["raw_type"] == "int" and item["public_type"] == "float" and item["raw"] == 1 and item["public"] == 1.0
                      for item in numeric_differences))
        restart = [public for public in public_parts if public["adk_type"] == "function_response" and public["part"]["data"]["name"] == "restart_service"]
        pending = [part for part in restart if "error" in part["part"]["data"]["response"]]
        executed = [part for part in restart if "audit" in part["part"]["data"]["response"] and "result" in part["part"]["data"]["response"]]
        check("restart pending and executed phases remain distinct under shared call ID", len(pending) == len(executed) == 1
              and pending[0]["function_id"] == executed[0]["function_id"] and pending[0]["adk_event_id"] != executed[0]["adk_event_id"]
              and not exact(pending[0]["part"], executed[0]["part"]))
        check("binding counts and empty unresolved list independently established", result["verified_function_pairs"] == result["public_function_parts"] == result["raw_function_parts"] == 5
              and result["artifact_recorded_identity_pairs"] == 3 == sum(pair["event_identity_proven"] for pair in result["pairs"])
              and result["message_payload_only_pairs"] == 2 == sum(not pair["event_identity_proven"] for pair in result["pairs"])
              and result["unresolved"] == [] and result["input_files_verified"] == {"raw": 9, "public": 50})
        report["verified_counts"] = {"verified_function_pairs": 5, "artifact_recorded_identity_pairs": 3, "message_payload_only_pairs": 2,
                                     "runtime_task_session_bindings": 1, "raw_input_files": 9, "public_input_files": 50,
                                     "binding_allocation_files": 63, "copied_public_wire_files": 45, "public_capture_exchanges": 9,
                                     "public_task_replies": 8, "function_source_representations": len(origins),
                                     "audit_integer_float_differences": 2, "tests_run": 15, "test_skips": 0, "unresolved": 0}
        report["audited_relations"] = audited_relations
        report["runtime_task_session_bindings"] = expected_bindings
        report["numeric_differences"] = numeric_differences
        report["numeric_rule"] = "Only exact raw int to finite integral public float at response.audit.id/schema_version within 2**53-1. Bool types cannot satisfy this rule."
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        check("bounded audit completed without an exception", False)
    finally:
        try:
            after = hashes(monitored)
            report["monitored_after"] = after
            check("all monitored before/after hashes unchanged", before is not None and before == after)
            check("all evidence directory memberships unchanged", bool(directories)
                  and all(set(groups[name]) == set(inventory(directory)) for name, directory in directories.items()))
        except Exception as error:
            report["preservation_error"] = f"{type(error).__name__}: {error}"
            check("audit preservation completed", False)
        report["checks"] = CHECKS
        report["checks_passed"] = sum(row["passed"] for row in CHECKS)
        report["checks_failed"] = sum(not row["passed"] for row in CHECKS)
        report["status"] = "passed" if CHECKS and all(row["passed"] for row in CHECKS) else "failed"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        with OUTPUT.open("xb") as stream:
            stream.write((json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"],
                      "verified_counts": report.get("verified_counts"), "error": report.get("error"), "output": str(OUTPUT)}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise SystemExit("Refusing consumed independent review output")
    raise SystemExit(audit())
