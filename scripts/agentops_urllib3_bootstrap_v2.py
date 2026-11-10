"""Source-bound cold import that prevents a diagnosed capability probe socket."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import socket
import sys
import sysconfig
import threading
import types

PIN = "2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74"
SIZE = 4444


def require(value, reason):
    if not value:
        raise ValueError(reason)


def check_diagnosis(value):
    require(value.get("schema_version") == "agentops-source-bound-import-probe-diagnosis/2"
            and value.get("status") == "actual_cold_urllib3_ipv6_probe_confirmed", "fresh actual diagnostic proof required")
    require(value.get("helper_sha256") == PIN and value.get("helper_bytes") == SIZE
            and value.get("no_socket_operation_permission") is True, "diagnosis source or deny policy mismatch")
    require(value.get("allowed_harness_intervention") == "scoped_no_ipv6_cold_import_then_restore", "unreviewed bootstrap intervention")
    cases = value.get("cases", [])
    require({row.get("case_id") for row in cases} == {"agentops-d01-health-active", "agentops-d03-restart-pause"}, "both fresh diagnostic cases required")
    for row in cases:
        require(row.get("event") == "socket.bind" and row.get("target") == ["::1", 0]
                and row.get("family") == 10 and row.get("type") == 1 and row.get("protocol") == 0
                and row.get("function") == "_has_ipv6" and row.get("source_sha256") == PIN
                and row.get("cold_module_import_confirmed") is True and row.get("diagnostic_denial_journal_sha256"), "actual probe target/source/import stack mismatch")
    return True


def code_shape(code):
    def value(item):
        if isinstance(item, types.CodeType):
            return code_shape(item)
        if isinstance(item, bytes):
            return {"type": "bytes", "hex": item.hex()}
        if isinstance(item, tuple):
            return {"type": "tuple", "items": [value(child) for child in item]}
        return {"type": type(item).__name__, "value": item}
    return {"bytecode": code.co_code.hex(), "constants": [value(item) for item in code.co_consts],
            "names": list(code.co_names), "variables": list(code.co_varnames), "argument_count": code.co_argcount}


def prepare(case, diagnosis_path, denied):
    raw_diagnosis = diagnosis_path.read_bytes()
    diagnosis = json.loads(raw_diagnosis)
    check_diagnosis(diagnosis)
    # Recompute the attribution from portable retained journals and helper bytes.
    for row in diagnosis["cases"]:
        journal = diagnosis_path.parent / row["diagnostic_denial_journal_source"]
        journal_raw = journal.read_bytes()
        require(hashlib.sha256(journal_raw).hexdigest() == row["diagnostic_denial_journal_sha256"], "retained diagnostic journal differs")
        events = [json.loads(line) for line in journal_raw.splitlines()]
        attempts = [event for event in events if event["event"].startswith("socket.")]
        require(len(attempts) == 1, "diagnostic attribution has additional socket attempts")
        event = attempts[0]
        require(event["event"] == "socket.bind" and event["target_or_arguments_after_socket"] == [["::1", 0]]
                and {name: value["value"] for name, value in event["socket"].items()} == {"family": 10, "type": 1, "proto": 0}, "retained target/socket differs")
        require(any(frame["function"] == "_has_ipv6" and frame["line"] == 127 and frame.get("source_sha256") == PIN for frame in event["stack"])
                and any(frame["function"] == "<module>" and frame["line"] == 137 and frame.get("source_sha256") == PIN for frame in event["stack"]), "retained cold-helper call stack differs")
        source_raw = (diagnosis_path.parent / row["source"]).read_bytes()
        require(len(source_raw) == SIZE and hashlib.sha256(source_raw).hexdigest() == PIN, "retained diagnostic helper source differs")
    with (case / "socket-bootstrap-diagnosis.json").open("xb") as target:
        target.write(raw_diagnosis)
    evidence = case / "source-evidence/agentops-socket-bootstrap-diagnosis-v2"
    evidence.mkdir(parents=True, exist_ok=False)
    for row in diagnosis["cases"]:
        for key in ("diagnostic_denial_journal_source", "source"):
            target = case / row[key]
            if not target.exists():
                with target.open("xb") as handle:
                    handle.write((diagnosis_path.parent / row[key]).read_bytes())
    require("urllib3.util.connection" not in sys.modules and "urllib3" not in sys.modules, "bootstrap requires cold urllib3 import")
    require(len(threading.enumerate()) == 1, "bootstrap must precede App or background-thread startup")
    helper = Path(sysconfig.get_paths()["purelib"]) / "urllib3/util/connection.py"
    raw = helper.read_bytes()
    require(len(raw) == SIZE and hashlib.sha256(raw).hexdigest() == PIN, "locked urllib3 helper bytes differ")
    before = len(denied)
    modules_before = set(sys.modules)
    original = socket.has_ipv6
    require(type(original) is bool, "unexpected socket capability type")
    started = datetime.now(timezone.utc).isoformat()
    socket.has_ipv6 = False
    try:
        module = importlib.import_module("urllib3.util.connection")
    finally:
        socket.has_ipv6 = original
    require(socket.has_ipv6 is original and module.HAS_IPV6 is False, "socket flag restoration or cached probe result failed")
    require(Path(module.__file__).resolve() == helper.resolve() and helper.read_bytes() == raw, "imported helper identity/source changed")
    compiled = next(code for code in compile(raw, str(helper), "exec").co_consts if isinstance(code, types.CodeType) and code.co_name == "_has_ipv6")
    require(code_shape(module._has_ipv6.__code__) == code_shape(compiled), "imported helper code differs from unchanged source")
    require(not any(row["event"].startswith("socket.") for row in denied[before:]), "a socket attempt occurred during source-bound bootstrap")
    imported = []
    for name in sorted(set(sys.modules) - modules_before):
        path = getattr(sys.modules[name], "__file__", None)
        if path and Path(path).is_file() and Path(path).suffix == ".py":
            data = Path(path).read_bytes()
            imported.append({"module": name, "source_basename": Path(path).name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    receipt = {"schema_version": "agentops-source-bound-urllib3-bootstrap/2", "status": "source_bound_cold_import_without_probe_socket",
               "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(), "helper_sha256": PIN, "helper_bytes": SIZE,
               "diagnosis_sha256": hashlib.sha256(raw_diagnosis).hexdigest(), "original_socket_has_ipv6": original,
               "helper_source": "bootstrap-helper-source.py", "diagnosis_source": "socket-bootstrap-diagnosis.json",
               "temporary_socket_has_ipv6": False, "restored_socket_has_ipv6": socket.has_ipv6,
               "urllib3_cached_HAS_IPV6": module.HAS_IPV6, "helper_code_unchanged": True, "cold_import_before_App": True,
               "observed_network_attempts_during_bootstrap": [], "modules_imported": imported,
               "socket_operation_permission_added": False,
               "intervention": "Temporary platform-capability override during source-pinned cold import; restored immediately; urllib3 retains IPv4-only cached capability. Native-network equivalence is not claimed."}
    with (case / "socket-bootstrap.json").open("x", encoding="utf-8") as target:
        json.dump(receipt, target, indent=2)
        target.write("\n")
    with (case / "bootstrap-helper-source.py").open("xb") as target:
        target.write(raw)
    return receipt
