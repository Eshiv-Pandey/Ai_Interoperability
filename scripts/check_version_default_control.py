"""Check retained SDK controls without importing the capture driver or SDK.

This is a separate implementation by the integrating assistant, not independent
human authorship. It checks source/input binding and actual function records;
it does not prove absence of arbitrary effects or HTTP protocol conformance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


SDK_HASH = "57ab549afa0e2cb2bef0de37f88f1ea0192c918b360322232bbd6d30263cd643"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, relative):
    require(isinstance(relative, str) and bool(relative), "Missing relative path")
    require(not Path(relative).is_absolute(), "Absolute evidence path")
    candidate = (root / relative).resolve()
    require(candidate.is_relative_to(root.resolve()), "Evidence path escapes root")
    return candidate


def check_semantics(report):
    """Validate actual observations; never trust the driver's pass booleans."""
    require(report["schema_version"] == "sdk-version-default-function-control/1", "Wrong schema")
    require(report["kind"] == "SOFTWARE/SDK CONTROL", "Wrong evidence classification")
    require(report["actual_supported_versions"] == ["1.0"], "Wrong supported versions")
    interfaces = report["card"]["supportedInterfaces"]
    require(len(interfaces) == 1 and interfaces[0]["protocolBinding"] == "JSONRPC"
            and interfaces[0]["protocolVersion"] == "1.0", "Card is not JSONRPC 1.0-only")
    require(interfaces[0]["url"] == "https://version-control.invalid/a2a", "Changed control URL")
    expected = [
        ("D1", False, None, {}, "0.3", False),
        ("D2", True, "", {"a2a-version": ""}, "0.3", False),
        ("D3", True, "1.0", {"a2a-version": "1.0"}, "1.0", True),
        ("D4", True, "0.3", {"a2a-version": "0.3"}, "0.3", False),
    ]
    require(len(report["cases"]) == 4 and len(report["case_plan"]) == 4, "Missing/extra case")
    expected_calls = [("getSupportedVersions", None)]
    for record, planned, control in zip(report["cases"], report["case_plan"], expected):
        case_id, present, value, headers, effective, accepted = control
        require(record["case_id"] == case_id and record["attempt"] == 1, "Reordered/repeated case")
        require(record["input"] == planned and planned["case_id"] == case_id, "Case input mismatch")
        require(planned["requested_version_property_present"] is present, "Wrong planned property presence")
        require(("requested_version" in planned) is present, "Absent property was not omitted")
        require(planned.get("requested_version") == value and planned["headers"] == headers, "Wrong planned input")
        descriptor = record["actual_options_descriptor"]
        require(descriptor["own_requested_version_property"] is present
                and descriptor["requested_version_value"] == value, "Wrong actual builder input")
        require(descriptor["headers"] == headers and descriptor["user"]["is_authenticated"] is False,
                "Wrong headers/authentication")
        require(record["headers_saved_by_builder"] == headers, "Builder changed saved headers")
        require(record["effective_requested_version"] == effective, "Wrong effective version")
        require(record["validation"]["accepted"] is accepted, "Wrong validator decision")
        require("unexpected_error" not in record and "mapping_error" not in record, "Unexpected function error")
        expected_calls.extend([("defaultServerCallContextBuilder", case_id), ("validateVersion", case_id)])
        if accepted:
            require(record["validation"]["returned_undefined"] is True
                    and record["validation"]["actual_return"] == {"type": "undefined", "representation": "undefined"},
                    "Wrong successful return")
            require("optional_official_jsonrpc_mapping" not in record, "Mapped a successful call")
        else:
            error = record["validation"]["semantic_exception"]
            require(error["name"] == "VersionNotSupportedError" and error["reason"] == "VERSION_NOT_SUPPORTED",
                    "Wrong semantic exception")
            require(all(error[key] is False for key in ("has_code", "has_envelope_code", "has_data")),
                    "Invented wire properties on semantic exception")
            require(effective in error["message"] and "1.0" in error["message"], "Wrong exception message")
            mapped = record["optional_official_jsonrpc_mapping"]
            require(type(mapped["code"]) is int and mapped["code"] == -32009, "Wrong mapped code")
            require(isinstance(mapped["data"], list) and len(mapped["data"]) == 1
                    and mapped["data"][0]["reason"] == "VERSION_NOT_SUPPORTED", "Wrong mapped reason")
            expected_calls.append(("JsonRpcTransportHandler.mapToJSONRPCError", case_id))
    calls = report["function_calls"]
    require([(call["function"], call.get("case_id")) for call in calls] == expected_calls,
            "Missing/extra/reordered direct function call")
    require(calls[0]["result"] == ["1.0"], "Support call/result disagreement")
    for call in calls[1:]:
        record = next(row for row in report["cases"] if row["case_id"] == call["case_id"])
        if call["function"] == "defaultServerCallContextBuilder":
            require(call["result"] == {"requestedVersion": record["effective_requested_version"],
                                       "headers": record["headers_saved_by_builder"]}, "Builder result disagreement")
        elif call["function"] == "validateVersion":
            require(call["arguments"]["requested_version"] == record["effective_requested_version"]
                    and call["arguments"]["protocol_binding"] == "JSONRPC", "Validator argument disagreement")
            require(call.get("result") == record["validation"] if record["validation"]["accepted"]
                    else call.get("error") == record["validation"]["semantic_exception"], "Validator result disagreement")
        else:
            require(call["result"] == record["optional_official_jsonrpc_mapping"], "Mapping result disagreement")
        require(int(call["started"]["monotonic_ns"]) <= int(call["completed"]["monotonic_ns"]),
                "Function completed before start")
    counts = Counter(name for name, _ in expected_calls)
    require(report["costs"] == {"function_calls": 12, "builder_calls": counts["defaultServerCallContextBuilder"],
            "validator_calls": counts["validateVersion"], "support_set_calls": 1, "optional_mapping_calls": 3,
            "network_requests": 0, "model_calls": 0}, "Wrong direct-call costs")
    require(report["applications_executed"] is False
            and all(report[key] == 0 for key in ("servers_started", "child_processes_started", "network_requests", "model_calls")),
            "Control boundary changed")
    require(report["cleanup"]["process_id"] == report["pid"] and report["exit_code"] == 0
            and report["outcome"] == "passed-software-control", "Nonterminal/failed control")
    require(all(not report[key] for key in ("post_source_errors", "post_source_changes", "post_tree_changes")),
            "Source integrity failure")
    return [{"case_id": row[0], "effective_version": row[4], "accepted": row[5]} for row in expected]


def check_archive(root, report_path):
    report_file = inside(root, report_path)
    report = decode(report_file.read_text(encoding="utf-8"))
    cases = check_semantics(report)
    pre = report["pre_execution"]
    require(decode((report_file.parent / "pre-execution-ledger.json").read_text(encoding="utf-8")) == pre,
            "Pre-execution ledger/report mismatch")
    require(decode((report_file.parent / "card.json").read_text(encoding="utf-8")) == report["card"], "Card mismatch")
    require(decode((report_file.parent / "case-plan.json").read_text(encoding="utf-8")) == report["case_plan"], "Plan mismatch")
    require(pre["sdk"]["version"] == "1.1.0" and pre["sdk"]["server_sha256"] == SDK_HASH, "Wrong SDK pin")
    require(pre["node"]["version"] == "v22.13.0"
            and report["post_node_executable_sha256"] == pre["node"]["executable_sha256"], "Node identity changed")
    preserved = 0
    for name, entry in pre["source_hashes"].items():
        snapshot = inside(root, entry["snapshot"])
        require(sha(snapshot) == entry["sha256"] and snapshot.stat().st_size == entry["bytes"], f"Changed snapshot: {name}")
        require(report["post_source_sha256"][name] == entry["sha256"], f"Post-source mismatch: {name}")
        preserved += 1
    for manifest in (pre["sdk"]["installed_manifest"], pre["runtime_dependency"]["manifest"]):
        snapshot_root = inside(root, manifest["snapshot_root"])
        require(len(manifest["entries"]) == manifest["file_count"], "Wrong manifest count")
        names = [entry["path"] for entry in manifest["entries"]]
        require(len(names) == len(set(names)), "Duplicate manifest path")
        require(set(names) == {p.relative_to(snapshot_root).as_posix() for p in snapshot_root.rglob("*") if p.is_file()},
                "Added/removed snapshot file")
        serialized = json.dumps(manifest["entries"], ensure_ascii=False, separators=(",", ":"))
        require(hashlib.sha256(serialized.encode()).hexdigest() == manifest["entries_sha256"], "Manifest digest mismatch")
        for entry in manifest["entries"]:
            filename = inside(snapshot_root, entry["path"])
            require(sha(filename) == entry["sha256"] and filename.stat().st_size == entry["bytes"], "Changed SDK/dependency bytes")
            require(report["post_source_sha256"][f"{manifest['root']}/{entry['path']}"] == entry["sha256"], "Dependency post-hash mismatch")
            preserved += 1
    for entry in pre["exact_input_files"]:
        require(sha(inside(root, entry["path"])) == entry["sha256"], "Changed exact input")
    event_file = inside(root, report["event_log"]["path"])
    require(sha(event_file) == report["event_log"]["sha256"], "Changed function event log")
    events = [decode(line) for line in event_file.read_text(encoding="utf-8").splitlines()]
    require([row["type"] for row in events] == ["pre-execution-ledger-frozen"]
            + [kind for _ in range(4) for kind in ("case-started", "case-completed")], "Event sequence mismatch")
    require(events[0]["sha256"] == sha(report_file.parent / "pre-execution-ledger.json"), "Event ledger hash mismatch")
    for index, case in enumerate(report["cases"]):
        require(events[1 + 2 * index]["input"] == case["input"], "Started-case input mismatch")
        completed = {key: value for key, value in events[2 + 2 * index].items() if key not in ("type", "observed")}
        require(completed == case, "Completed-case event/report mismatch")
    return {"report": report_path, "report_sha256": sha(report_file), "cases": cases,
            "preserved_files_checked": preserved, "valid": True,
            "authorship": "Separate checker implementation by integrating assistant; no independent human review",
            "claim_limit": "SDK function observations and archival integrity only; no wire conformance or novelty"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = check_archive(args.root.resolve(), args.report)
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    result["checker_sha256"] = sha(Path(__file__))
    target = inside(args.root.resolve(), args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
