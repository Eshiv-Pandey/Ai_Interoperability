"""Read-only stdlib audit of an already captured historical restart assessment.

Does not import or execute the effect API, driver, comparator, SDK or database.
Creates only a new sibling review JSON and monitors the inspected allocations.
"""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

ROOT = Path(__file__).resolve().parents[2]
EFFECT = ROOT / "runs/agentops-restart-effects/native-v12-N11-v1"
SOFTWARE = ROOT / "runs/agentops-restart-effects/software-v2"
BINDING = ROOT / "runs/agentops-event-binding/native-v12-N11-v1"
OUTPUT = Path(__file__).with_suffix(".json")
EXPECTED = {
    "src/interoperability/agentops_restart_effects_v1.py": "d04fde3c70b6028eb8b71bc72351a28d34fd0ae62cccb100fde39a150cd2750f",
    "tests/test_agentops_restart_effects_v1.py": "4be04d637fb40ca57bb046d01f76d6a60712147fb0b89f0d2539e78642828eee",
    "scripts/capture_restart_effect_example_v1.py": "aec3118ac58c7cbdf8010f780d0fd8bd37c71f429b48e770963577ab6b856aae",
    "src/interoperability/agentops_raw_events_v1.py": "de196858e75738e1976df39c077b4ab5b4c45d53298cf885cda212e82eba421b",
}
IDENTITY = ("app_name", "user_id", "session_id", "invocation_id")
PREFIX = "<<<TOOL_DATA data-not-instructions>>>"
SUFFIX = "<<<END_TOOL_DATA>>>"
RATIONALE = "Inventory is down and INC-002 matches the service-down runbook."
COLUMNS = {
    "services": {"name", "description", "status", "owner"},
    "incidents": {"id", "service", "title", "severity", "status", "runbook", "opened_at", "resolved_at", "summary"},
    "audit_log": {"id", "schema_version", "ts", "actor", "approved_by", "rationale", "context_summary", "session_id", "invocation_id", "action", "target", "detail"},
    "sqlite_sequence": {"name", "seq"},
}
DIMENSIONS = {"input_shape", "database_metadata", "service_delta", "incident_preservation", "audit_append",
              "audit_identity", "audit_context", "idempotency_consistency", "clean_text_contract", "executed_result_agreement",
              "sqlite_sequence", "timestamp_consistency", "unrelated_table_preservation"}
CHECKS = []


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def decode(raw):
    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid)
    encoded(value)
    return value


def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def check(name, condition, **evidence):
    row = {"name": name, "passed": condition is True, **evidence}
    CHECKS.append(row)
    if condition is not True:
        raise ValueError("Independent audit failed: " + name)


def regular(path, directory=False):
    for node in (*reversed(path.absolute().parents), path.absolute()):
        info = node.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("Linked input path")
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError("Unsupported input path")
    return path


def inventory(root):
    regular(root, True)
    files = {}
    for path in sorted(root.rglob("*")):
        regular(path, path.is_dir())
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def manifest(files, label):
    receipt = decode(files["result.json"])
    rows = receipt["files"]
    names = set()
    for row in rows:
        path = row["path"]
        check(label + "/manifest-entry", type(row) is dict and set(row) == {"path", "bytes", "sha256"}
              and type(path) is str and path not in names and path != "result.json"
              and path and ":" not in path and "\\" not in path and not PurePosixPath(path).is_absolute()
              and ".." not in PurePosixPath(path).parts and PurePosixPath(path).as_posix() == path
              and type(row["bytes"]) is int and row["bytes"] >= 0
              and type(row["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
              and path in files and digest(files[path]) == {"bytes": row["bytes"], "sha256": row["sha256"]}, path=path)
        names.add(path)
    check(label + "/manifest-membership", names | {"result.json"} == set(files), file_count=len(files))
    return receipt


def prefix_files(files, prefix):
    return {name[len(prefix):]: raw for name, raw in files.items() if name.startswith(prefix)}


def keyed(rows, key, columns):
    result = {}
    for row in rows:
        if type(row) is not dict or set(row) != columns or row[key] in result:
            raise ValueError("Invalid or duplicate logical row")
        result[row[key]] = row
    return result


def utc_interval(value):
    match = re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|\+00:00)", value)
    if match is None:
        raise ValueError("Unsupported timestamp representation")
    start = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if start.utcoffset() != timedelta(0):
        raise ValueError("Non-UTC timestamp")
    step = timedelta(microseconds=10 ** (6 - len(match[1]))) if match[1] else timedelta(seconds=1)
    return start, start + step


def function_equal(raw, public, kind):
    if kind != "function_response" or type(raw.get("response")) is not dict or type(raw["response"].get("audit")) is not dict:
        return same(raw, public)
    clone = decode(encoded(public))
    audit = clone.get("response", {}).get("audit")
    if type(audit) is not dict:
        return False
    for key in ("id", "schema_version"):
        stored, supplied = raw["response"]["audit"].get(key), audit.get(key)
        if type(stored) is int and 0 <= stored <= 2**53 - 1 and type(supplied) is float and supplied.is_integer() and supplied == stored:
            audit[key] = stored
    return same(raw, clone)


def audit(effect, binding, software, sources):
    receipt = manifest(effect, "effect")
    bound_receipt = manifest(binding, "binding")
    copied_binding = prefix_files(effect, "binding/")
    check("copied-binding/full-byte-membership", copied_binding == binding, file_count=len(binding))
    raw_export = prefix_files(binding, "inputs/raw/")
    public_export = prefix_files(binding, "inputs/public/")
    manifest(raw_export, "raw-export")
    manifest(public_export, "public-export")
    check("binding/status-and-preservation", bound_receipt["status"] == "passed"
          and all(bound_receipt[key] is True for key in ("inputs_unchanged", "implementation_unchanged", "captured_files_unchanged", "input_manifests_verified"))
          and bound_receipt["verified_function_pairs"] == 5 and len(bound_receipt["pairs"]) == 5
          and bound_receipt["unresolved"] == [])
    check("binding/input-receipts", bound_receipt["input_receipts"] == {"raw": digest(raw_export["result.json"]), "public": digest(public_export["result.json"])})
    plan = decode(effect["plan.json"])
    check("effect/binding-plan", plan["binding"] == str(BINDING) and plan["binding_receipt"] == digest(binding["result.json"]))
    for path, sha in EXPECTED.items():
        check("frozen-source/hash", digest(sources[path])["sha256"] == sha, path=path, sha256=sha)
    for name, expected in plan["sources"].items():
        source_path = "scripts/" + name if name.startswith("capture_") else "src/interoperability/" + name
        check("effect/source-copy", digest(effect["source/" + name]) == expected and effect["source/" + name] == sources[source_path], path=name)
    soft_receipt, soft_plan = decode(software["result.json"]), decode(software["plan.json"])
    check("software/final-captured-suite", soft_receipt["status"] == "passed" and type(soft_receipt["tests_run"]) is int and soft_receipt["tests_run"] == 66
          and soft_receipt["skips"] == 0 and soft_receipt["exit_code"] == 0 and soft_receipt["error"] is None
          and soft_receipt["original_and_captured_source_unchanged"] is True)
    check("software/source-manifest", len(soft_receipt["source_files"]) == 6 and soft_receipt["source_files"] == soft_plan["source_files"])
    for path, expected in soft_receipt["source_files"].items():
        check("software/source-copy", digest(sources[path]) == expected and software["workspace/" + path] == sources[path], path=path)
    expected_soft = {"result.json", "plan.json", "stdout.txt", "stderr.txt"} | {"workspace/" + path for path in soft_receipt["source_files"]}
    check("software/membership", set(software) == expected_soft, file_count=len(software))
    for stream in ("stdout", "stderr"):
        check("software/stream-hash", digest(software[stream + ".txt"]) == soft_receipt[stream], stream=stream)
    log = software["stderr.txt"].decode("utf-8")
    ok_methods = re.findall(r"^test_.* \.\.\. ok\r?$", log, re.MULTILINE)
    check("software/logged-results", len(ok_methods) == 66 and "Ran 66 tests" in log and log.rstrip().endswith("OK") and " ... skipped" not in log,
          logged_passing_tests=len(ok_methods))
    api_tree = ast.parse(software["workspace/tests/test_agentops_restart_effects_v1.py"].decode("utf-8"))
    driver_tree = ast.parse(software["workspace/tests/test_restart_effect_capture_v1.py"].decode("utf-8"))
    methods = [sum(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in ast.walk(tree)) for tree in (api_tree, driver_tree)]
    check("software/static-method-counts", methods == [60, 6], api_methods=methods[0], driver_methods=methods[1], counts_not_additive_with_software_v1=True)
    assessment = decode(effect["assessment.json"])
    check("effect/receipt-and-dimensions", receipt["status"] == receipt["assessment_status"] == assessment["status"] == "consistent"
          and set(assessment["dimensions"]) == DIMENSIONS
          and all(value["status"] == "consistent" and value["reasons"] == [] for value in assessment["dimensions"].values())
          and all(receipt[key] is True for key in ("binding_manifest_verified", "input_unchanged", "implementation_unchanged", "captured_files_unchanged")), dimensions=len(DIMENSIONS))
    for label, record, keys in (
        ("effect-receipt", receipt, ("new_native_runs", "model_calls", "application_requests", "graded_upstream_cases")),
        ("effect-assessment", assessment, ("new_native_runs", "graded_upstream_cases")),
        ("software", soft_receipt, ("model_calls", "application_requests", "original_archives_exported")),
    ):
        check("claim/zero-activity", all(type(record[key]) is int and record[key] == 0 for key in keys), record=label, fields=list(keys))
    for label, record, keys in (
        ("effect-receipt", receipt, ("source_authenticity_proven", "causal_order_proven", "client_receipt_proven", "complete_event_stream_proven", "qualification_established")),
        ("effect-assessment", assessment, ("raw_byte_binding_checked", "source_clean_transforms_proven", "phase_linkage_checked", "continuous_absence_of_mutation_proven", "causal_order_proven", "client_receipt_proven", "complete_event_stream_proven", "qualification_established")),
    ):
        check("claim/false-proofs", all(record[key] is False for key in keys), record=label, fields=list(keys))
    check("claim/narrow-rationale-scope", assessment["rationale_scope"] == "declared_clean_fixture_texts_only")
    functions, view = decode(raw_export["function-observations.json"]), decode(public_export["observations.json"])
    keyed_functions = {(row["event_id"], row["part_index"]): row for row in functions}
    check("binding/raw-function-membership", len(functions) == len(keyed_functions) == 5)
    bound = []
    for pair in bound_receipt["pairs"]:
        row = keyed_functions[(pair["matched_raw_event_id"], pair["matched_raw_part_index"])]
        check("binding/pair-runtime-projection", all(row[key] == pair[key] for key in ("app_name", "user_id", "session_id", "kind", "function_id"))
              and row["invocation_id"] == pair["matched_raw_invocation_id"] and row["author"] == pair["matched_raw_author"]
              and row["function"]["name"] == pair["function_name"], event_id=row["event_id"])
        public_rows = [item for item in view["observations"] if item["namespace"] == pair["public_namespace"]
                       and item["identity"] == pair["public_identity"] and item["part_index"] == pair["public_part_index"]
                       and item["task_id"] == pair["task_id"] and item["context_id"] == pair["context_id"]]
        check("binding/pair-public-payload", len(public_rows) == 1 and function_equal(row["function"], public_rows[0]["part"]["data"], row["kind"]), event_id=row["event_id"])
        bound.append((pair, row))
    executed = [(pair, row) for pair, row in bound if row["kind"] == "function_response" and row["function"]["name"] == "restart_service" and "audit" in row["function"]["response"]]
    check("selection/unique-executed", len(executed) == 1)
    pair, response = executed[0]
    identity = {key: response[key] for key in IDENTITY}
    scope = [row for _, row in bound if all(row[key] == identity[key] for key in IDENTITY)]
    calls = [row for row in scope if row["kind"] == "function_call" and row["function_id"] == response["function_id"] and row["function"]["name"] == "restart_service"]
    approvals = [row for row in scope if row["kind"] == "function_response" and row["author"] == "user" and row["function"]["name"] == "adk_request_confirmation" and row["function"]["response"].get("confirmed") is True]
    check("selection/unique-original-and-approval", len(calls) == len(approvals) == 1)
    call, approval = calls[0], approvals[0]
    confirmations = [row for row in scope if row["kind"] == "function_call" and row["function"]["name"] == "adk_request_confirmation" and row["function_id"] == approval["function"]["id"]]
    check("selection/confirmation-links", len(confirmations) == 1 and confirmations[0]["function"]["id"] == approval["function"]["id"]
          and same(confirmations[0]["function"]["args"]["originalFunctionCall"], call["function"])
          and confirmations[0]["function"]["args"]["toolConfirmation"]["confirmed"] is False
          and same(call["function"], {"id": "restart-inventory-call", "name": "restart_service", "args": {"name": "inventory"}}))
    association = receipt["association"]
    sequence = association["approval_sequence"]
    check("selection/exact-association", sequence == 7 and association["original_call_event_id"] == call["event_id"]
          and association["confirmation_event_id"] == confirmations[0]["event_id"] and association["approval_event_id"] == approval["event_id"]
          and association["executed_event_id"] == response["event_id"] and association["task_id"] == pair["task_id"]
          and association["context_id"] == pair["context_id"] and association["supplied_confirmation_payload_links_checked"] is True)
    prefix = f"wire/{sequence:06d}/"
    request, wire_response, exchange = [decode(public_export[prefix + name]) for name in ("request.body.bin", "response.body.bin", "exchange.json")]
    actual_approvals = [part for part in request["params"]["message"]["parts"] if part.get("metadata", {}).get("adk_type") == "function_response" and same(part.get("data"), approval["function"])]
    message = request["params"]["message"]
    check("selection/copied-approval-request", len(actual_approvals) == 1 and request["method"] in ("SendMessage", "message/send")
          and message["taskId"] == pair["task_id"] and message["contextId"] == pair["context_id"]
          and approval["function"]["response"]["payload"]["rationale"] == RATIONALE)
    record = [row for row in view["records"] if row["capture_sequence"] == sequence]
    check("selection/copied-wire-projections", len(record) == 1 and same(record[0]["request"], request) and same(record[0]["response"], wire_response)
          and exchange["sequence"] == sequence and exchange["request_bytes"] == len(public_export[prefix + "request.body.bin"])
          and exchange["response_bytes"] == len(public_export[prefix + "response.body.bin"])
          and exchange["request_body_complete"] is True and exchange["response_body_complete"] is True and exchange["response_status"] == 200)
    before, after = [decode(public_export[prefix + name]) for name in ("before.snapshot.json", "after.snapshot.json")]
    expected_raw = {"before_snapshot": before, "after_snapshot": after, "executed_function": {**response, "original_function_call": call["function"]},
                    "expected_identity": identity, "rationale": RATIONALE, "exchange": exchange}
    check("assessment/exact-selected-inputs", same(assessment["raw"], expected_raw))
    before_db, after_db = before["database"], after["database"]
    check("logical/database-metadata-and-tables", set(before_db["tables"]) == set(after_db["tables"]) == set(COLUMNS)
          and same({key: value for key, value in before_db.items() if key != "tables"}, {key: value for key, value in after_db.items() if key != "tables"}))
    before_rows, after_rows = {}, {}
    for table in COLUMNS:
        key = "id" if table in ("incidents", "audit_log") else "name"
        before_rows[table] = keyed(before_db["tables"][table], key, COLUMNS[table])
        after_rows[table] = keyed(after_db["tables"][table], key, COLUMNS[table])
    expected_services = decode(encoded(before_rows["services"]))
    expected_services["inventory"]["status"] = "operational"
    check("logical/only-inventory-service-delta", len(before_rows["services"]) == len(after_rows["services"]) == 8
          and before_rows["services"]["inventory"]["status"] == "down" and same(expected_services, after_rows["services"]), services_checked=8)
    check("logical/all-incidents-preserved", len(before_rows["incidents"]) == len(after_rows["incidents"]) == 10
          and same(before_rows["incidents"], after_rows["incidents"]), incidents_checked=10)
    check("logical/one-new-audit-and-sequence", before_rows["audit_log"] == {} and set(after_rows["audit_log"]) == {1}
          and before_rows["sqlite_sequence"] == {} and same(after_rows["sqlite_sequence"], {"audit_log": {"name": "audit_log", "seq": 1}}))
    audit_row = after_rows["audit_log"][1]
    check("logical/audit-identity-rationale-and-constants", audit_row["actor"] == "agentops-agent" and type(audit_row["id"]) is int and audit_row["id"] == 1
          and type(audit_row["schema_version"]) is int and audit_row["schema_version"] == 1 and audit_row["action"] == "restart_service"
          and audit_row["target"] == "inventory" and audit_row["detail"] == "service restarted and marked operational (mock)"
          and audit_row["approved_by"] == identity["user_id"] and audit_row["session_id"] == identity["session_id"]
          and audit_row["invocation_id"] == identity["invocation_id"] and audit_row["rationale"] == RATIONALE
          and all(type(value) is str and value.isascii() and value and value.strip() == value for value in identity.values()))
    open_rows = [row for row in before_rows["incidents"].values() if row["service"] == "inventory" and row["status"] != "resolved"]
    ordered_ids = [row["id"] for row in sorted(open_rows, key=lambda row: row["opened_at"], reverse=True)]
    context = "service inventory was down; open incidents: " + (", ".join(ordered_ids) or "none")
    check("logical/derived-context", len({row["opened_at"] for row in open_rows}) == len(open_rows) and ordered_ids == ["INC-002"]
          and audit_row["context_summary"] == context and assessment["dimensions"]["audit_context"]["derived_context_summary"] == context,
          ordered_open_incident_ids=ordered_ids, derived_context_summary=context)
    check("logical/no-prior-idempotency-key", not any(row["invocation_id"] == audit_row["invocation_id"] and row["action"] == "restart_service"
          and row["target"] == "inventory" for row in before_rows["audit_log"].values())
          and assessment["dimensions"]["idempotency_consistency"]["matching_prior_audit_ids"] == [])
    result = response["function"]["response"]
    expected_audit = dict(audit_row)
    for key in ("rationale", "context_summary", "detail"):
        expected_audit[key] = f"{PREFIX}\n{audit_row[key]}\n{SUFFIX}"
    check("logical/strict-executed-result-and-wrapping", set(result) == {"result", "audit"}
          and result["result"] == "Service 'inventory' restarted and marked operational." and same(result["audit"], expected_audit))
    labels = ("before_snapshot", "after_snapshot", "exchange_start", "exchange_finish")
    endpoints = [utc_interval(value) for value in (before["observed_at_utc"], after["observed_at_utc"], exchange["started_at_utc"], exchange["finished_at_utc"])]
    b, a, s, f = endpoints
    audit_at, audit_end = utc_interval(audit_row["ts"])
    check("logical/all-endpoint-precision-and-audit-bracket", all(left[1] <= right[0] for left, right in ((b, s), (s, f), (f, a)))
          and audit_at >= max(b[1], s[1]) and audit_end <= min(a[0], f[0])
          and type(before["monotonic_ns"]) is int and type(after["monotonic_ns"]) is int and 0 <= before["monotonic_ns"] < after["monotonic_ns"],
          audit_interval_start_utc=audit_at.isoformat(), audit_interval_end_exclusive_utc=audit_end.isoformat(),
          guaranteed_bracket_start_utc=max(b[1], s[1]).isoformat(), guaranteed_bracket_end_utc=min(a[0], f[0]).isoformat())
    time_dimension = assessment["dimensions"]["timestamp_consistency"]
    expected_intervals = {label: {"start_utc": start.isoformat(), "end_exclusive_utc": end.isoformat()} for label, (start, end) in zip(labels, endpoints)}
    check("assessment/reported-time-evidence", time_dimension["endpoint_intervals"] == expected_intervals
          and time_dimension["audit_interval_start_utc"] == audit_at.isoformat() and time_dimension["audit_interval_end_exclusive_utc"] == audit_end.isoformat()
          and time_dimension["audit_timestamp_precision_seconds"] == 1.0
          and time_dimension["guaranteed_bracket_start_utc"] == max(b[1], s[1]).isoformat() and time_dimension["guaranteed_bracket_end_utc"] == min(a[0], f[0]).isoformat()
          and time_dimension["authoritative_clock_proven"] is False)
    return {"effect_files": len(effect), "binding_files": len(binding), "copied_raw_export_files": len(raw_export), "copied_public_export_files": len(public_export),
            "software_files": len(software), "original_and_copied_software_sources": 6, "software_tests": 66, "api_test_methods": 60, "driver_test_methods": 6,
            "raw_function_observations": len(functions), "bound_function_pairs": len(bound), "services": 8, "incidents": 10, "audit_rows_appended": 1,
            "logical_dimensions": len(DIMENSIONS), "approval_sequence": sequence,
            "assessment_digest": digest(effect["assessment.json"]), "effect_receipt_digest": digest(effect["result.json"]), "binding_receipt_digest": digest(binding["result.json"])}


def monitor_summary(files):
    entries = {name: digest(raw) for name, raw in files.items()}
    return {"file_count": len(entries), "membership_and_hashes": entries, "inventory_digest": digest(encoded(entries))}


def main():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("Refusing existing review output")
    started = datetime.now(timezone.utc).isoformat()
    roots = {"effect": EFFECT, "binding": BINDING, "software": SOFTWARE}
    before = {name: inventory(path) for name, path in roots.items()}
    soft_receipt = decode(before["software"]["result.json"])
    sources = {path: regular(ROOT / path).read_bytes() for path in soft_receipt["source_files"]}
    audit_source_before = regular(Path(__file__)).read_bytes()
    status, error, counts = "failed", None, {}
    try:
        counts = audit(before["effect"], before["binding"], before["software"], sources)
        status = "passed"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as problem:
        error = f"{type(problem).__name__}: {problem}"
    after = {name: inventory(path) for name, path in roots.items()}
    sources_after = {path: regular(ROOT / path).read_bytes() for path in sources}
    preserved = before == after and sources == sources_after and regular(Path(__file__)).read_bytes() == audit_source_before
    CHECKS.append({"name": "preservation/before-after-byte-membership", "passed": preserved})
    if not preserved:
        status = "failed"
        error = "Monitored files changed during independent audit"
    review = {"schema_version": "agentops-restart-effect-independent-review/1", "status": status, "error": error,
              "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "claim_scope": "Independent checks of copied bytes, preserved allocations, captured software results and one logical historical clean-text fixture assessment only",
              "checks": CHECKS, "checks_passed": sum(row["passed"] for row in CHECKS), "checked_counts": counts,
              "monitored_before": {name: monitor_summary(files) for name, files in before.items()},
              "monitored_after": {name: monitor_summary(files) for name, files in after.items()},
              "original_sources_before": monitor_summary(sources), "original_sources_after": monitor_summary(sources_after),
              "audit_source": digest(audit_source_before), "monitored_inputs_unchanged": preserved,
              "new_native_runs": 0, "model_calls": 0, "application_requests": 0, "apis_or_comparators_executed": 0, "databases_opened": 0,
              "exports_created": 0, "graded_upstream_cases": 0, "source_authenticity_proven": False, "causal_order_proven": False,
              "complete_event_stream_proven": False, "client_receipt_proven": False, "continuous_absence_of_mutation_proven": False,
              "qualification_established": False, "software_v1_counts_added": False,
              "historical_assessment_is_new_native_success": False}
    with OUTPUT.open("xb") as stream:
        stream.write(encoded(review))
    print(json.dumps({"status": status, "error": error, "review": str(OUTPUT), "review_digest": digest(OUTPUT.read_bytes()),
                      "checked_counts": counts, "checks_passed": review["checks_passed"]}, sort_keys=True))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
