"""Prepare/verify one fresh N11 then admitted-B7 allocation; never launch apps."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agentops-admission-live-preparation/3"
CASE_PREFIX = "runs/agentops-http-control/admission-live-v1-"
GROUP = "runs/agentops-admission-live-v1"
PORT = 18764
SERVICE_ENTRYPOINT = "scripts/serve_agentops_bridge_diagnostic_v4.py"
READINESS_TIMEOUT_SECONDS = 65
STARTUP_STACK_SECONDS = 5.0
EXIT_WATCHDOG_SECONDS = 5.0
RATIONALE = "Inventory is down and INC-002 matches the service-down runbook."
LIMITS = {"request_timeout_ms": 15000, "poll_interval_ms": 100, "poll_attempts": 30,
          "total_timeout_ms": 180000, "max_response_bytes": 33554432}
CASES = {"N11": {"case_id": "N11", "kind": "native", "profile": "mg-raw-header",
                  "representation": "data", "native_prerequisites": []},
         "B7": {"case_id": "B7", "kind": "bridge", "arm": "B7", "native_prerequisites": ["N11"]}}
REQUIRED_SCRIPTS = (
    "agentops_admission_live_plan_v3.py", "agentops_admission_control_v3.py",
    "stage_agentops_admission_v3.py", "execute_agentops_admission_phase_v3.py",
    "run_agentops_admission_chain_v3.py",
    "export_agentops_admission_v3.py", "agentops_startup_diagnostics_v1.py",
    "serve_agentops_bridge_diagnostic_v4.py", "check_agentops_startup_v1.py",
    "check_agentops_interpreter_exit_v2.py",
    "agentops_owned_child_v1.py", "agentops_interpreter_exit_diagnostics_v1.py",
    "serve_agentops_bridge_diagnostic_v3.py", "check_agentops_interpreter_exit_v1.py",
    "agentops_admission_client_v1.mjs", "agentops_admission_controller_v1.mjs",
    "check_agentops_admitted_client_v1.py", "agentops_native_profile_client_v1.mjs",
    "agentops_bridge_client_v1.mjs", "agentops_mgcrea_embed_v1.mjs",
    "serve_agentops_bridge_diagnostic_v2.py", "serve_agentops_bridge_v1.py",
    "agentops_shutdown_diagnostics_v2.py", "agentops_socket_policy_v1.py",
    "agentops_asgi_capture_v1.py", "agentops_native_probe_v2.py",
    "agentops_protocol_wire_v1.py", "agentops_http_bytes_v1.py",
    "agentops_owned_process_v1.py", "check_agentops_bridge_v1.py",
    "check_agentops_effect_v2.py", "check_agentops_socket_policy_v1.py",
    "agentops_bridge_runtime_archive_v1.py", "check_agentops_bridge_diagnostic_v1.py",
)
PINNED_DOCS = (
    "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json",
    "docs/research/source-evidence/agentops-bridge-control-v1/runtime/graph.json",
    "docs/research/source-evidence/agentops-bridge-control-v1/runtime/materialization.json",
    "docs/research/pending-admission-source-map-v1.md",
    "docs/research/pending-admission-source-map-v1.json",
    "docs/research/pending-admission-live-plan-v1.md",
    "docs/research/pending-admission-live-plan-v2.md",
    "docs/research/pending-admission-live-plan-v3.md",
    "docs/research/agentops-startup-diagnostics-v1.md",
)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def record(path, root):
    path, root = Path(path), Path(root)
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def executable_record(path):
    path = Path(path).absolute()
    raw = path.read_bytes()
    return {"path": str(path), "resolved": str(path.resolve()), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def bridge_environment(case):
    return {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC",
            "A2A_ALLOW_WRITES": "1", "A2A_CHANNEL": "0", "A2A_MAX_RETRIES": "0",
            "A2A_CONFIG": str(case / "absent-bridge-config.json"),
            "A2A_STATE_DIR": str(case / "bridge-state"), "TMPDIR": str(case / "temp"),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1"}


def client_config(case_id, case, plan, root=ROOT):
    definition = CASES[case_id]
    base = {"output_dir": str(case / "client"), "agent_base_url": f"http://127.0.0.1:{PORT}/",
            "rationale": RATIONALE, "limits": deepcopy(LIMITS)}
    if definition["kind"] == "native":
        return {**base, "schema_version": "agentops-native-profile-client-config/1",
                "profile": "mg-raw-header", "representation": "data", "runtime_root": plan["bridge_runtime"]}
    return {**base, "schema_version": "agentops-admitted-client-config/1", "arm": "B7", "agent_alias": "agentops",
            "admission": {"python": plan["runtime_python"], "budget": 100000, "timeout_ms": 30000,
                "deployment": {"origin": base["agent_base_url"], "header_mode": "version-header",
                    "serializer": "mgcrea-raw-jsonrpc/1", "service_contract": "agentops-inventory-confirmation-fixture/1"}},
            "bridge": {"command": plan["node"]["path"], "args": [str(root / "scripts/agentops_mgcrea_embed_v1.mjs"),
                "--workspace", plan["bridge_runtime"], "--mode", "version-header", "--origin", base["agent_base_url"]],
                "cwd": plan["bridge_runtime"], "env": bridge_environment(case)}}


def staged_inventory(root):
    ingestion = load(root / PINNED_DOCS[0])
    source = [row["extracted"] for row in ingestion["records"] if row["kind"] == "regular_file"]
    if len(source) != 421:
        raise ValueError("Expected the 421 original application files")
    for row in source:
        if record(root / row["path"], root) != row:
            raise ValueError("Changed staged application source: " + row["path"])
    app = root / "external/agentops-c806b7f1"
    actual = {path.relative_to(root).as_posix() for path in app.rglob("*") if path.is_file()}
    if actual != {row["path"] for row in source} or any(path.is_symlink() for path in app.rglob("*")):
        raise ValueError("Staged application inventory is not exact")
    for name in REQUIRED_SCRIPTS:
        if not (root / "scripts" / name).is_file():
            raise ValueError("Required staged helper missing: " + name)
    paths = sorted(path for path in (root / "scripts").iterdir() if path.suffix in (".py", ".mjs"))
    paths += [root / name for name in PINNED_DOCS]
    paths += sorted((root / "src/interoperability").rglob("*.py"))
    for name in ("tests", "examples/refinement-development", "examples/benchmark-development"):
        directory = root / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Required reproduction directory missing or nonregular: " + name)
        candidates = directory.iterdir() if name == "tests" else directory.rglob("*")
        for path in sorted(candidates):
            if path.is_symlink():
                raise ValueError("Reproduction inputs refuse symlinks: " + str(path))
            if path.is_file() and (name != "tests" or path.suffix in (".py", ".mjs")):
                paths.append(path)
    for name in ("examples/refinement-development/manifest.json", "examples/benchmark-development/recipe-v1.json",
                 "examples/benchmark-development/suite.json"):
        if root / name not in paths:
            raise ValueError("Required reproduction fixture missing: " + name)
    if not (root / "src/interoperability/pending_admission.py").is_file():
        raise ValueError("Pending-state adapter is absent")
    for path in paths:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Nonregular staged input: " + str(path))
    return sorted(source + [record(path, root) for path in paths], key=lambda row: row["path"])


def probe_port():
    """Transient loopback bind only; no service/request and no reservation claim."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", PORT))
    return {"status": "available_at_probe", "host": "127.0.0.1", "port": PORT, "reserved": False}


def _runtime_rows(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            yield value
        for item in value.values():
            yield from _runtime_rows(item)
    elif type(value) is list:
        for item in value:
            yield from _runtime_rows(item)


def runtime_inventory(reuse_root, python_before):
    inventory = load(python_before)
    if (inventory.get("schema_version") != "agentops-installed-runtime-inspection/6"
            or inventory.get("status") != "installed_versions_match_lock"
            or inventory.get("application_imports") != 0):
        raise ValueError("Need a fresh read-only Python runtime inspection")
    rows = {row["path"]: row for row in _runtime_rows(inventory)}
    extra = [reuse_root / "scripts/inspect_agentops_runtime_v6.py"]
    extra.extend((reuse_root / "external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages").glob("*.pth"))
    for path in extra:
        row = record(path, reuse_root); rows[row["path"]] = row
    for row in rows.values():
        target = reuse_root / row["path"]
        if not target.resolve().is_relative_to(reuse_root.resolve()) or record(target, reuse_root) != row:
            raise ValueError("Changed reused Python metadata/source: " + row["path"])
    return sorted(rows.values(), key=lambda row: row["path"])


def verify(plan, root=ROOT, require_unexecuted=False):
    root = root.resolve()
    if plan.get("schema_version") != SCHEMA or plan["workspace"] != str(root) or plan["cases"] != list(CASES.values()):
        raise ValueError("Prepared workspace/case definition differs")
    if plan["inputs"] != staged_inventory(root):
        raise ValueError("Prepared source/code inputs changed")
    if record(root / plan["python_inspection"]["path"], root) != plan["python_inspection"]:
        raise ValueError("Prepared Python inspection receipt changed")
    constants = {"case_prefix": CASE_PREFIX, "port": PORT, "admission_budget": 100000,
        "admission_timeout_seconds": 30, "operational_window_seconds": 15, "max_attempts_per_case": 1,
        "live_model_calls": 0, "research_gate_credit_added": 0,
        "service_entrypoint": SERVICE_ENTRYPOINT, "readiness_timeout_seconds": READINESS_TIMEOUT_SECONDS,
        "startup_stack_seconds": STARTUP_STACK_SECONDS, "exit_watchdog_seconds": EXIT_WATCHDOG_SECONDS}
    if any(plan.get(key) != value for key, value in constants.items()):
        raise ValueError("Prepared execution constants differ")
    reuse = Path(plan["reuse_root"])
    if root.is_relative_to(reuse) or reuse.is_relative_to(root):
        raise ValueError("Fresh workspace and reused runtime must be disjoint")
    if not Path(plan["runtime_python"]).resolve().is_relative_to(reuse) or not Path(plan["bridge_runtime"]).resolve().is_relative_to(reuse):
        raise ValueError("Reused runtime paths must stay under the declared read-only workspace")
    if executable_record(plan["runtime_python"]) != plan["python"] or executable_record(plan["node"]["path"]) != plan["node"]:
        raise ValueError("Runtime executable changed")
    for row in plan["python_runtime_inputs"]:
        if record(reuse / row["path"], reuse) != row:
            raise ValueError("Reused Python input changed: " + row["path"])
    from agentops_bridge_runtime_archive_v1 import verify_runtime
    bridge = verify_runtime(Path(plan["bridge_runtime"]), load(root / PINNED_DOCS[1]), load(root / PINNED_DOCS[2]))
    if require_unexecuted and any((root / (CASE_PREFIX + name)).exists() for name in CASES):
        raise FileExistsError("A planned case path already exists; never repeat it")
    return {"status": "verified", "staged_files": len(plan["inputs"]), "bridge": bridge,
            "application_requests": 0, "python_runtime_scope": "Executable, provider, selected sources and installed metadata; not complete runtime authenticity"}


def prepare(reuse_root, python_before, output, node=Path("/usr/bin/node"), root=ROOT):
    if sys.platform != "linux" or not str(root.resolve()).startswith("/var/tmp/agentops-admission-live-v1-"):
        raise ValueError("Prepare only in a newly allocated native Linux admission workspace")
    reuse_root, root = reuse_root.resolve(), root.resolve()
    runtime_python = reuse_root / "external/runtime-agentops-linux-v7/venv/bin/python"
    plan = {"schema_version": SCHEMA, "status": "prepared_not_executed", "created_at_utc": now(),
        "workspace": str(root), "reuse_root": str(reuse_root), "runtime_python": str(runtime_python),
        "bridge_runtime": str(reuse_root / "external/runtime-agentops-bridges-v1"),
        "python": executable_record(runtime_python), "node": executable_record(node),
        "python_runtime_inputs": runtime_inventory(reuse_root, python_before),
        "python_inspection": record(python_before, root), "inputs": staged_inventory(root),
        "cases": list(CASES.values()), "case_prefix": CASE_PREFIX, "port": PORT,
        "admission_budget": 100000, "admission_timeout_seconds": 30, "operational_window_seconds": 15,
        "max_attempts_per_case": 1, "live_model_calls": 0, "research_gate_credit_added": 0,
        "service_entrypoint": SERVICE_ENTRYPOINT, "readiness_timeout_seconds": READINESS_TIMEOUT_SECONDS,
        "startup_stack_seconds": STARTUP_STACK_SECONDS, "exit_watchdog_seconds": EXIT_WATCHDOG_SECONDS,
        "claims": "One new native matched control then one candidate-gated configured-B7 continuation, each with a fresh isolated fixture; no novelty, domain qualification or percentage inferred"}
    checked = verify(plan, root, require_unexecuted=True)
    checked["port_probe"] = probe_port()
    output = output.resolve()
    if not output.is_relative_to(root / GROUP):
        raise ValueError("Preparation must be inside the new admission group")
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "plan.json", plan)
    write_new(output / "verification.json", checked)
    return {**checked, "status": "prepared_not_executed", "plan": str(output / "plan.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-root", type=Path)
    parser.add_argument("--python-before", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        report = verify(load(args.verify))
    else:
        if not all((args.reuse_root, args.python_before, args.output)):
            parser.error("prepare needs --reuse-root, --python-before and a new --output")
        report = prepare(args.reuse_root, args.python_before, args.output)
    print(json.dumps(report, indent=2))
