"""Prepare or run one source-pinned, offline AgentOps HTTP control.

Preparation is permitted before the native test finishes. Execution requires
the original v3 test and its effect check to have passed. Every attempt is
exclusive and retains partial captures and failures without automatic retries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import agentops_native_probe_v3 as native
import agentops_http_bytes_v1 as wire

evidence = native.original
ROOT = native.ROOT
RUNS = ROOT / "runs/agentops-http-control"
SERVICE = ROOT / "scripts/serve_agentops_http_v1.py"
CHECKER = ROOT / "scripts/check_agentops_http_v1.py"
SPEC = ROOT / "docs/research/source-evidence/agentops-http-control-v1/protocol.md"
PREREQUISITE = native.RUNS / "native-probe-v3"
RATIONALE = "Inventory is down and INC-002 matches the service-down runbook."
START = {"jsonrpc": "2.0", "id": "approval-start", "method": "message/stream", "params": {
    "message": {"kind": "message", "messageId": "approval-message", "role": "user",
                "parts": [{"kind": "text", "text": "Restart inventory."}]}}}


def harness():
    paths = [Path(__file__).resolve(), Path(wire.__file__).resolve(), SERVICE, CHECKER, SPEC,
             ROOT / "scripts/check_agentops_effect_v2.py",
             ROOT / "tests/test_agentops_http_control.py",
             ROOT / "scripts/run_agentops_http_v1.ps1"]
    return native.harness() + [evidence.digest(path) for path in paths]


def prepare(output: Path, port: int) -> None:
    source = evidence.source_inventory()
    files = harness()
    if not 1024 <= port <= 65535:
        raise ValueError("Use an unprivileged local port")
    output.mkdir(parents=True, exist_ok=False)
    (output / "temp").mkdir()
    runtime = native.runtime_inspection(output, "prepared-runtime", evidence.clean_environment(output))
    evidence.write_json(output / "plan.json", {
        "schema_version": "agentops-http-plan/1", "prepared_at_utc": evidence.now(),
        "source_files": source, "harness_files": files, "port": port,
        "runtime_inventory": evidence.digest(output / "prepared-runtime.stdout.bin"),
        "runtime_package_count": len(runtime["packages"]),
        "prerequisite": "runs/agentops-native-eligibility/native-probe-v3/result.json",
        "binding": "HTTP JSON-RPC; no A2A-Version header, matching original test input",
        "sequence": ["card", "start", "get-pending", "resume", "get-completed"],
        "application_imports": 0, "application_requests": 0,
        "live_model_calls": 0, "bridge_qualification": False})
    print(json.dumps({"status": "prepared_not_executed", "output": str(output), "port": port}))


def validate_native(plan):
    from check_agentops_effect_v2 import check_record, seed_snapshot
    result = evidence.load_json(PREREQUISITE / "result.json")
    if (result.get("status") != "upstream_and_boundary_effect_check_passed"
            or result.get("source_unchanged_after") is not True
            or result.get("pytest_returncode") != 0 or result.get("independent_check") != "passed"):
        raise ValueError("The original native test and effect check must pass first")
    for row in result["files"]:
        path = evidence.within(ROOT / row["path"], PREREQUISITE)
        if evidence.digest(path) != row:
            raise ValueError("Native evidence differs from its retained result")
    old_plan = evidence.load_json(PREREQUISITE / "plan.json")
    if old_plan["source_files"] != plan["source_files"] or old_plan["harness_files"] != native.harness():
        raise ValueError("Native source/harness does not match this control")
    if ((PREREQUISITE / "prepared-runtime.stdout.bin").read_bytes()
            != (ROOT / plan["runtime_inventory"]["path"]).read_bytes()):
        raise ValueError("HTTP and native prepared runtimes differ")
    reports = evidence.load_json(PREREQUISITE / "pytest-reports.json")
    if (reports["exitstatus"] != 0 or len(reports["reports"]) != 3
            or {row["when"] for row in reports["reports"]} != {"setup", "call", "teardown"}
            or any(row["nodeid"] != evidence.NODEID or row["outcome"] != "passed"
                   for row in reports["reports"])):
        raise ValueError("Native pytest phases are incomplete")
    check_record(evidence.load_json(PREREQUISITE / "passive-profile.json"),
                 seed_snapshot(evidence.SOURCE / "agents/data/incidents.db"))
    return evidence.digest(PREREQUISITE / "result.json")


def response(output, label):
    status, headers, body = wire.decode_response((output / f"{label}.response.bin").read_bytes())
    if status != 200:
        raise ValueError(f"{label} returned HTTP {status}")
    return headers, body


def run(output: Path) -> None:
    plan = evidence.load_json(output / "plan.json")
    if plan["source_files"] != evidence.source_inventory() or plan["harness_files"] != harness():
        raise ValueError("Prepared source/harness changed; preserve the plan")
    if evidence.digest(ROOT / plan["runtime_inventory"]["path"]) != plan["runtime_inventory"]:
        raise ValueError("Prepared runtime inventory changed")
    prerequisite = validate_native(plan)
    evidence.write_json(output / "execution.json", {
        "schema_version": "agentops-http-execution/1", "started_at_utc": evidence.now(),
        "plan": evidence.digest(output / "plan.json"), "native_prerequisite": prerequisite})
    result = {"schema_version": "agentops-http-result/1", "status": "failed",
              "live_model_calls": 0, "bridge_qualification": False}
    process, streams = None, []
    boundaries = []

    def snapshot(label):
        row = {"label": label, "observed_at_utc": evidence.now(), "monotonic_ns": time.monotonic_ns(),
               "database": evidence.database_snapshot(output / "state/incidents.db", output, "run")}
        evidence.write_json(output / f"{label}.snapshot.json", row)
        boundaries.append(row)

    try:
        environment = evidence.clean_environment(output)
        current = native.runtime_inspection(output, "execution-runtime", environment)
        if current != json.loads((ROOT / plan["runtime_inventory"]["path"]).read_bytes()):
            raise ValueError("Runtime changed after preparation")
        port = plan["port"]
        environment.update({"AGENT_MODEL_PROVIDER": "openai-compatible", "AGENT_MODEL": "qwen3:4b-instruct",
                            "AGENT_DATA_DIR": str(evidence.SOURCE / "agents/data"),
                            "AGENT_STATE_DIR": str(output / "state"), "AGENT_A2A_HOST": "127.0.0.1",
                            "AGENT_A2A_BIND_HOST": "127.0.0.1", "AGENT_A2A_PORT": str(port)})
        if (output / "state").exists():
            raise ValueError("Fresh wire control unexpectedly has runtime state")
        streams = [(output / f"service.{name}.bin").open("xb") for name in ("stdout", "stderr")]
        argv = [str(native.RUNTIME), "-B", str(SERVICE), "--output", str(output), "--port", str(port)]
        process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=streams[0], stderr=streams[1], shell=False)
        evidence.write_json(output / "service-process.json", {"pid": process.pid, "argv": argv,
                                                              "started_at_utc": evidence.now()})
        deadline = time.monotonic() + 65
        while not (output / "service-ready.json").exists():
            if process.poll() is not None:
                raise RuntimeError("Service exited before readiness; inspect retained streams")
            if time.monotonic() >= deadline:
                raise TimeoutError("Service readiness deadline")
            time.sleep(0.1)
        if process.poll() is not None:
            raise RuntimeError("Owned service already exited")
        snapshot("before-card")
        wire.exchange(output, "card", port, "GET", "/.well-known/agent-card.json")
        response(output, "card")
        snapshot("before-start")
        wire.exchange(output, "start", port, "POST", "/", START)
        headers, body = response(output, "start")
        if not headers.get("content-type", "").startswith("text/event-stream"):
            raise ValueError("Initial response is not SSE")
        initial = wire.rpc_results(body, "approval-start")
        snapshot("after-start")
        pending = initial[-1]
        if pending["status"]["state"] != "input-required" or pending["final"] is not False:
            raise ValueError("Original approval pause was not observed")
        task_id, context_id = pending["taskId"], pending["contextId"]
        calls = [part["data"] for part in pending["status"]["message"]["parts"]
                 if part.get("kind") == "data" and part.get("metadata", {}).get("adk_type") == "function_call"
                 and part.get("data", {}).get("name") == "adk_request_confirmation"]
        if len(calls) != 1:
            raise ValueError("Expected one source-owned confirmation identifier")
        for label, rpc_id in [("get-pending", "get-pending")]:
            wire.exchange(output, label, port, "POST", "/", {
                "jsonrpc": "2.0", "id": rpc_id, "method": "tasks/get", "params": {"id": task_id}})
            response(output, label)
        snapshot("before-resume")
        call = calls[0]
        resume = {"jsonrpc": "2.0", "id": "approval-resume", "method": "message/stream", "params": {
            "message": {"kind": "message", "messageId": "approval-response", "role": "user",
                        "taskId": task_id, "contextId": context_id,
                        "parts": [{"kind": "data", "data": {"id": call["id"], "name": call["name"],
                                  "response": {"confirmed": True, "payload": {"rationale": RATIONALE}}},
                                   "metadata": {"adk_type": "function_response"}}]}}}
        wire.exchange(output, "resume", port, "POST", "/", resume)
        response(output, "resume")
        snapshot("after-resume")
        wire.exchange(output, "get-completed", port, "POST", "/", {
            "jsonrpc": "2.0", "id": "get-completed", "method": "tasks/get", "params": {"id": task_id}})
        response(output, "get-completed")
        snapshot("after-get-completed")
        result["status"] = "captured_check_pending"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            evidence.write_json(output / "stop-requested.json", {"requested_at_utc": evidence.now()})
            try:
                process.wait(timeout=20)
                result["forced_service_stop"] = False
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
                result["forced_service_stop"] = True
            result["service_returncode"] = process.returncode
        for stream in streams:
            stream.close()
        evidence.write_json(output / "boundaries.json", boundaries)
        try:
            result["source_unchanged_after"] = evidence.source_inventory() == plan["source_files"]
        except Exception as error:
            result["source_unchanged_after"] = False
            result["source_error"] = str(error)
        if result["status"] == "captured_check_pending":
            try:
                if result.get("forced_service_stop") or result.get("service_returncode") != 0:
                    raise ValueError("Service did not shut down cleanly")
                checked = evidence.capture([sys.executable, "-B", str(CHECKER), "--run", str(output),
                    "--output", str(output / "check.json")], output=output, label="wire-check",
                    cwd=ROOT, environment=evidence.clean_environment(output), timeout=30)
                if checked["returncode"] != 0:
                    raise ValueError("Wire/effect check failed; retained without retry")
                result["status"] = "wire_and_effect_check_passed"
            except Exception as error:
                result.update(status="failed", error=f"{type(error).__name__}: {error}")
        if not result["source_unchanged_after"]:
            result["status"] = "failed_source_integrity"
        result["finished_at_utc"] = evidence.now()
        result["files"] = [evidence.digest(path) for path in sorted(output.iterdir()) if path.is_file()]
        evidence.write_json(output / "result.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    if result["status"] != "wire_and_effect_check_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--output", type=Path, default=RUNS / "native-http-v1")
    parser.add_argument("--port", type=int, default=18761)
    args = parser.parse_args()
    target = evidence.within(args.output, RUNS)
    if args.command == "prepare":
        prepare(target, args.port)
    else:
        run(target)
