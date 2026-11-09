"""Check a historical restart snapshot pair from an existing binding bundle.

This captures a logical consistency check. It does not launch an application,
read a live database, authenticate source evidence or grade an upstream case.
"""
from datetime import datetime, timezone
import argparse
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.agentops_raw_events_v1 import _digest, _encode, _json, _need, _regular, _write


def inventory(root):
    _regular(root, directory=True)
    result = {}
    total = 0
    for path in sorted(root.rglob("*")):
        _regular(path, directory=path.is_dir())
        if path.is_dir():
            continue
        raw = path.read_bytes()
        total += len(raw)
        _need(total <= 512 * 1024 * 1024 and len(result) < 10000, "Binding allocation exceeds limits")
        result[path.relative_to(root).as_posix()] = raw
    return result


def decoded(raw):
    return _json(raw.decode("utf-8"))


def check_manifest(files):
    report = decoded(files["result.json"])
    _need(report.get("schema_version") == "agentops-event-binding/1" and report.get("status") == "passed",
          "A passed event binding is required")
    for flag in ("inputs_unchanged", "implementation_unchanged", "captured_files_unchanged", "input_manifests_verified"):
        _need(report.get(flag) is True, "Binding preservation/manifest check is absent")
    manifest = {}
    for row in report["files"]:
        _need(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "Invalid binding manifest entry")
        name = row["path"]
        _need(type(name) is str and name not in manifest and name != "result.json"
              and ":" not in name and "\\" not in name and not PurePosixPath(name).is_absolute()
              and ".." not in PurePosixPath(name).parts and PurePosixPath(name).as_posix() == name,
              "Invalid binding manifest path")
        _need(type(row["bytes"]) is int and row["bytes"] >= 0
              and type(row["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None,
              "Invalid binding manifest digest")
        _need(name in files and _digest(files[name]) == {key: row[key] for key in ("bytes", "sha256")},
              "Binding manifest differs from captured bytes")
        manifest[name] = row
    _need(set(manifest) | {"result.json"} == set(files), "Binding membership differs from manifest")
    return report


def select_fixture(files, report):
    functions = decoded(files["inputs/raw/function-observations.json"])
    by_identity = {(row["event_id"], row["part_index"]): row for row in functions}
    _need(len(by_identity) == len(functions), "Duplicate raw function identity")
    bound = []
    for pair in report["pairs"]:
        row = by_identity[(pair["matched_raw_event_id"], pair["matched_raw_part_index"])]
        _need(all(row[key] == pair[key] for key in ("app_name", "user_id", "session_id"))
              and row["invocation_id"] == pair["matched_raw_invocation_id"], "Binding/runtime scope mismatch")
        bound.append((pair, row))
    executed = [(pair, row) for pair, row in bound if row["kind"] == "function_response"
                and row["function"].get("name") == "restart_service"
                and type(row["function"].get("response")) is dict
                and "audit" in row["function"]["response"]]
    _need(len(executed) == 1, "Need one bound executed restart response")
    pair, response = executed[0]
    identity = {key: response[key] for key in ("app_name", "user_id", "session_id", "invocation_id")}
    same_scope = [row for _, row in bound if all(row[key] == value for key, value in identity.items())]
    calls = [row for row in same_scope if row["kind"] == "function_call"
             and row["function_id"] == response["function_id"] and row["function"]["name"] == "restart_service"]
    _need(len(calls) == 1, "Need one bound original restart call")
    approvals = [row for row in same_scope if row["kind"] == "function_response" and row["author"] == "user"
                 and row["function"]["name"] == "adk_request_confirmation"
                 and row["function"].get("response", {}).get("confirmed") is True]
    _need(len(approvals) == 1, "Need one bound user confirmation response")
    approval = approvals[0]["function"]
    confirmations = [row for row in same_scope if row["kind"] == "function_call"
                     and row["function"].get("name") == "adk_request_confirmation"
                     and row["function_id"] == approval["id"]]
    _need(len(confirmations) == 1, "Need one bound matching confirmation call")
    confirmation_args = confirmations[0]["function"].get("args")
    _need(type(confirmation_args) is dict
          and _encode(confirmation_args.get("originalFunctionCall")) == _encode(calls[0]["function"])
          and type(confirmation_args.get("toolConfirmation")) is dict
          and confirmation_args["toolConfirmation"].get("confirmed") is False,
          "Confirmation does not bind the selected original restart call")
    rationale = approval["response"]["payload"]["rationale"]
    view = decoded(files["inputs/public/observations.json"])
    sequences = []
    for record in view["records"]:
        message = record.get("request", {}).get("params", {}).get("message")
        if record.get("rpc_method") not in ("SendMessage", "message/send") or type(message) is not dict:
            continue
        if message.get("taskId") != pair["task_id"] or message.get("contextId") != pair["context_id"]:
            continue
        for part in message.get("parts", []):
            if part.get("metadata", {}).get("adk_type") == "function_response" and _encode(part.get("data")) == _encode(approval):
                sequences.append(record["capture_sequence"])
    _need(len(sequences) == 1, "Need one actual linked approval request")
    prefix = f"inputs/public/wire/{sequences[0]:06d}/"
    supplied = {**response, "original_function_call": calls[0]["function"]}
    args = (decoded(files[prefix + "before.snapshot.json"]), decoded(files[prefix + "after.snapshot.json"]),
            supplied, identity, rationale, decoded(files[prefix + "exchange.json"]))
    return args, {"task_id": pair["task_id"], "context_id": pair["context_id"], "approval_sequence": sequences[0],
                  "original_call_event_id": calls[0]["event_id"], "executed_event_id": response["event_id"],
                  "confirmation_event_id": confirmations[0]["event_id"], "approval_event_id": approvals[0]["event_id"],
                  "supplied_confirmation_payload_links_checked": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binding, output = args.binding.absolute(), args.output.absolute()
    _need(not output.exists() and not output.is_symlink(), "Refusing an existing output")
    _need(not output.resolve().is_relative_to(binding.resolve()), "Output must be outside binding input")
    output.mkdir(parents=True, exist_ok=False)
    files, captures, implementations = None, {}, {}
    receipt = {"schema_version": "agentops-restart-effect-capture/1", "status": "failed",
               "new_native_runs": 0, "model_calls": 0, "application_requests": 0, "graded_upstream_cases": 0,
               "source_authenticity_proven": False, "causal_order_proven": False, "client_receipt_proven": False,
               "complete_event_stream_proven": False, "qualification_established": False}
    try:
        files = inventory(binding)
        binding_report = check_manifest(files)
        source_paths = (ROOT / "src/interoperability/agentops_restart_effects_v1.py",
                        ROOT / "src/interoperability/agentops_raw_events_v1.py", Path(__file__))
        implementations = {path: _regular(path).read_bytes() for path in source_paths}
        plan = {"schema_version": "agentops-restart-effect-capture-plan/1", "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "binding": str(binding), "binding_receipt": _digest(files["result.json"]),
                "sources": {path.name: _digest(raw) for path, raw in implementations.items()},
                "scope": "Historical clean-text restart logical snapshot consistency; no new native execution or upstream-case grade"}
        captures["plan.json"] = _encode(plan)
        for path, raw in implementations.items():
            captures["source/" + path.name] = raw
        for name, raw in files.items():
            captures["binding/" + name] = raw
        for name, raw in captures.items():
            _write(output / name, raw)
        supplied, association = select_fixture(files, binding_report)
        copied_module = output / "source/agentops_restart_effects_v1.py"
        spec = importlib.util.spec_from_file_location("captured_restart_effect", copied_module)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        assessment = module.check_restart_effect(*supplied)
        captures["assessment.json"] = _encode(assessment)
        _write(output / "assessment.json", captures["assessment.json"])
        receipt.update(status=assessment["status"], association=association,
                       assessment_status=assessment["status"], binding_manifest_verified=True)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, ImportError, AttributeError) as error:
        receipt.update(status="failed", error=f"{type(error).__name__}: {error}")
    finally:
        try:
            receipt["input_unchanged"] = files is not None and inventory(binding) == files
            _need(receipt["input_unchanged"], "Input binding changed or was unavailable")
            receipt["implementation_unchanged"] = bool(implementations) and all(_regular(path).read_bytes() == raw for path, raw in implementations.items())
            _need(receipt["implementation_unchanged"], "Effect implementation changed or was unavailable")
            membership = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
            receipt["captured_files_unchanged"] = membership == set(captures) and all(_regular(output / name).read_bytes() == raw for name, raw in captures.items())
            _need(receipt["captured_files_unchanged"], "Copied evidence changed")
        except (OSError, ValueError) as error:
            receipt.update(status="failed", preservation_error=f"{type(error).__name__}: {error}")
        receipt["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["files"] = [{"path": path.relative_to(output).as_posix(), **_digest(path.read_bytes())}
                            for path in sorted(output.rglob("*")) if path.is_file()]
        _write(output / "result.json", _encode(receipt))
    print(json.dumps({"status": receipt["status"], "error": receipt.get("error"), "receipt": str(output / "result.json")}))
    return 0 if receipt["status"] == "consistent" else 1


if __name__ == "__main__":
    raise SystemExit(main())
