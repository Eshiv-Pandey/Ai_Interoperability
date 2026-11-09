"""Prepare or run one source-pinned, offline AgentOps HTTP control.

Preparation and execution both require the original Linux test under observer v3 and its
effect checker to have passed. The wire/effect contract is unchanged; service observer v2 classifies the denied import probe. Every attempt is
exclusive and retains partial captures and failures without automatic retries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import os
import signal
import sys
import time

import agentops_native_probe_v7 as native
import agentops_http_bytes_v1 as wire

evidence = native.original
ROOT = native.ROOT
RUNS = ROOT / "runs/agentops-http-control"
SERVICE = ROOT / "scripts/serve_agentops_http_v2.py"
CHECKER = ROOT / "scripts/check_agentops_http_v2.py"
SPEC = ROOT / "docs/research/source-evidence/agentops-http-control-v5/protocol.md"
PREREQUISITE = native.RUNS / "native-probe-v7"
RATIONALE = "Inventory is down and INC-002 matches the service-down runbook."
START = {"jsonrpc": "2.0", "id": "approval-start", "method": "message/stream", "params": {
    "message": {"kind": "message", "messageId": "approval-message", "role": "user",
                "parts": [{"kind": "text", "text": "Restart inventory."}]}}}


def runtime_inventory():
    return evidence.load_json(PREREQUISITE / "prepared-runtime.stdout.bin")


def harness(runtime):
    paths = [Path(__file__).resolve(), Path(wire.__file__).resolve(), SERVICE, CHECKER, SPEC,
             ROOT / "scripts/check_agentops_effect_v3.py",
             ROOT / "tests/test_agentops_http_control_v5.py", ROOT / "scripts/check_agentops_http_v1.py"]
    # Use the verified interpreter's distribution locations. The coordinator may
    # be bootstrap Python 3.12, so its own sysconfig would point at the wrong SDK.
    modules = {
        "a2a-sdk": ("a2a/server/routes/jsonrpc_dispatcher.py", "a2a/server/routes/agent_card_routes.py",
                    "a2a/server/request_handlers/response_helpers.py", "a2a/utils/constants.py"),
        "google-adk": ("google/adk/a2a/utils/agent_to_a2a.py",),
        "uvicorn": ("uvicorn/server.py",),
    }
    runtime_root = native.RUNTIME.parents[1].resolve()
    for name, names in modules.items():
        entries = [row for row in runtime["packages"] if row["name"] == name]
        if len(entries) != 1:
            raise ValueError(f"Exactly one installed runtime distribution is required: {name}")
        site = evidence.within(ROOT / entries[0]["location"], runtime_root)
        paths.extend(evidence.within(site / module, runtime_root) for module in names)
    return native.harness() + [evidence.digest(path) for path in paths]


def prepare(output: Path, port: int) -> None:
    native.require_linux()
    output = evidence.within(output, RUNS)
    if output.exists():
        raise FileExistsError("Preparation already exists; preserve it")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Use an unprivileged local port")
    source = evidence.source_inventory()
    prerequisite = validate_native(source)
    baseline = runtime_inventory()
    files = harness(baseline)
    output.mkdir(parents=True, exist_ok=False)
    (output / "temp").mkdir()
    result = {"schema_version": "agentops-http-preparation/5", "status": "failed",
              "application_imports": 0, "application_requests": 0, "live_model_calls": 0}
    try:
        runtime = native.runtime_inspection(output, "prepared-runtime", evidence.clean_environment(output))
        if runtime != baseline:
            raise ValueError("Current HTTP runtime differs from the passed native runtime")
        evidence.write_json(output / "plan.json", {
            # The v1 wire/checker contract is unchanged. Controller provenance is
            # explicit instead of relabeling Linux observations as the old trial.
            "schema_version": "agentops-http-plan/1", "controller_version": "agentops-http-control/5",
            "prepared_at_utc": evidence.now(), "source_files": source, "harness_files": files, "port": port,
            "runtime_inventory": evidence.digest(output / "prepared-runtime.stdout.bin"),
            "runtime_package_count": len(runtime["packages"]), "native_prerequisite": prerequisite,
            "prerequisite": "runs/agentops-native-eligibility/native-probe-v7/result.json",
            "binding": "HTTP JSON-RPC; no A2A-Version header, matching original test input",
            "sequence": ["card", "start", "get-pending", "resume", "get-completed"],
            "application_imports": 0, "application_requests": 0,
            "live_model_calls": 0, "bridge_qualification": False})
        result["status"] = "prepared_not_executed"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    result["finished_at_utc"] = evidence.now()
    evidence.write_json(output / "preparation-result.json", result)
    print(json.dumps(dict(result, output=str(output), port=port)))
    if result["status"] != "prepared_not_executed":
        raise SystemExit(1)


def validate_native(source):
    from check_agentops_effect_v3 import check_record, seed_snapshot
    result = evidence.load_json(PREREQUISITE / "result.json")
    if (result.get("schema_version") != "agentops-native-result/7"
            or result.get("status") != "upstream_and_boundary_effect_check_passed"
            or result.get("source_unchanged_after") is not True
            or result.get("pytest_returncode") != 0 or result.get("independent_check") != "passed"
            or result.get("application_test_started") is not True or result.get("live_model_calls") != 0):
        raise ValueError("The original Linux native test and effect check must pass first")
    required = {"plan.json", "preparation-result.json", "prepared-runtime.stdout.bin", "execution.json",
                "execution-runtime.stdout.bin", "pytest-reports.json", "passive-profile.json",
                "seed-before.json", "isolated-seed-before.json", "effect-check.json"}
    names = [evidence.within(ROOT / row["path"], PREREQUISITE).name for row in result["files"]]
    if len(names) != len(set(names)) or not required.issubset(names):
        raise ValueError("Native evidence is missing required unique receipts")
    for row in result["files"]:
        path = evidence.within(ROOT / row["path"], PREREQUISITE)
        if evidence.digest(path) != row:
            raise ValueError("Native evidence differs from its retained result")
    old_plan = evidence.load_json(PREREQUISITE / "plan.json")
    if (old_plan.get("schema_version") != "agentops-native-plan/7"
            or old_plan["source_files"] != source or old_plan["harness_files"] != native.harness()):
        raise ValueError("Native source/harness does not match this control")
    if old_plan["runtime_setup"] != native.validate_setup():
        raise ValueError("Linux dependency setup differs from the native prerequisite")
    preparation = evidence.load_json(PREREQUISITE / "preparation-result.json")
    if preparation.get("status") != "prepared" or old_plan.get("directory_capability_in_preparation") is not True:
        raise ValueError("Original native preparation did not pass")
    inventory = runtime_inventory()
    if (inventory.get("schema_version") != "agentops-installed-runtime-inspection/6"
            or inventory.get("status") != "installed_versions_match_lock"
            or inventory.get("python", [])[:2] != [3, 13]
            or inventory.get("platform", {}).get("system") != "Linux"
            or inventory.get("platform", {}).get("machine") != "x86_64"):
        raise ValueError("Native prerequisite does not identify the required Linux runtime")
    if inventory != native.installed_inventory():
        raise ValueError("Native prerequisite differs from the installed runtime")
    if evidence.digest(PREREQUISITE / "prepared-runtime.stdout.bin") != old_plan["runtime_inventory"]:
        raise ValueError("Native prepared runtime differs from its plan")
    if evidence.digest(PREREQUISITE / "seed-before.json") != old_plan["seed_snapshot"]:
        raise ValueError("Native seed snapshot differs from its plan")
    if evidence.load_json(PREREQUISITE / "execution-runtime.stdout.bin") != inventory:
        raise ValueError("Native execution and preparation runtimes differ")
    execution = evidence.load_json(PREREQUISITE / "execution.json")
    if execution.get("plan") != evidence.digest(PREREQUISITE / "plan.json"):
        raise ValueError("Native execution does not bind the retained plan")
    reports = evidence.load_json(PREREQUISITE / "pytest-reports.json")
    native.validate_pytest_reports(reports)
    seed = seed_snapshot(evidence.SOURCE / "agents/data/incidents.db")
    isolated = evidence.load_json(PREREQUISITE / "isolated-seed-before.json")
    prepared_seed = evidence.load_json(PREREQUISITE / "seed-before.json")
    fields = {"user_tables", "schema", "user_version", "tables", "columns"}
    if ({key: isolated[key] for key in fields} != {key: seed[key] for key in fields}
            or {key: prepared_seed[key] for key in fields} != {key: seed[key] for key in fields}):
        raise ValueError("Native seed snapshots differ from immutable source")
    profile_path = PREREQUISITE / "passive-profile.json"
    checked = evidence.load_json(PREREQUISITE / "effect-check.json")
    if (checked.get("schema_version") != "agentops-independent-effect-check/3"
            or checked.get("status") != "passed"
            or checked.get("profile_sha256") != evidence.digest(profile_path)["sha256"]
            or checked.get("seed_sha256") != evidence.digest(evidence.SOURCE / "agents/data/incidents.db")["sha256"]):
        raise ValueError("Native effect-check receipt is not bound to the passed profile and seed")
    check_record(evidence.load_json(profile_path), seed)
    return evidence.digest(PREREQUISITE / "result.json")


def response(output, label):
    status, headers, body = wire.decode_response((output / f"{label}.response.bin").read_bytes())
    if status != 200:
        raise ValueError(f"{label} returned HTTP {status}")
    return headers, body


def query(output, label, port, task_id, context_id, state):
    wire.exchange(output, label, port, "POST", "/", {
        "jsonrpc": "2.0", "id": label, "method": "tasks/get", "params": {"id": task_id}})
    headers, body = response(output, label)
    if headers.get("content-type", "").split(";", 1)[0] != "application/json":
        raise ValueError("Native query did not return JSON")
    reply = wire.strict_json(body)
    if reply.get("jsonrpc") != "2.0" or reply.get("id") != label or "error" in reply:
        raise ValueError("Native task query failed")
    task = reply["result"]
    if (task.get("kind") != "task" or task.get("id") != task_id
            or task.get("contextId") != context_id or task.get("status", {}).get("state") != state):
        raise ValueError("Native task query did not confirm the expected original-task state")


def stop_owned_service(process, output, result):
    errors = []
    try:
        evidence.write_json(output / "stop-requested.json", {"requested_at_utc": evidence.now()})
    except Exception as error:
        errors.append(f"stop request: {type(error).__name__}: {error}")
    result["forced_service_stop"] = False
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        result["forced_service_stop"] = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # It exited between the deadline and the bounded cleanup.
        except Exception as error:
            errors.append(f"process-group stop: {type(error).__name__}: {error}")
        try:
            process.wait(timeout=10)
        except Exception as error:
            errors.append(f"cleanup wait: {type(error).__name__}: {error}")
    except Exception as error:
        errors.append(f"service wait: {type(error).__name__}: {error}")
    result["service_returncode"] = process.returncode
    if errors:
        result["cleanup_errors"] = errors


def run(output: Path) -> None:
    native.require_linux()
    output = evidence.within(output, RUNS)
    if (output / "execution.json").exists():
        raise FileExistsError("Attempt already reserved; never rerun it")
    plan = evidence.load_json(output / "plan.json")
    if (plan.get("schema_version") != "agentops-http-plan/1"
            or plan.get("controller_version") != "agentops-http-control/5"
            or plan.get("sequence") != ["card", "start", "get-pending", "resume", "get-completed"]
            or type(plan.get("port")) is not int or not 1024 <= plan["port"] <= 65535):
        raise ValueError("Expected the frozen Linux HTTP v5 controller plan")
    if evidence.load_json(output / "preparation-result.json").get("status") != "prepared_not_executed":
        raise ValueError("HTTP preparation did not complete successfully")
    source = evidence.source_inventory()
    prerequisite = validate_native(source)
    baseline = runtime_inventory()
    if plan.get("native_prerequisite") != prerequisite:
        raise ValueError("Native prerequisite changed after HTTP preparation")
    if plan["source_files"] != source or plan["harness_files"] != harness(baseline):
        raise ValueError("Prepared source/harness changed; preserve the plan")
    inventory_path = evidence.within(ROOT / plan["runtime_inventory"]["path"], output)
    if evidence.digest(inventory_path) != plan["runtime_inventory"]:
        raise ValueError("Prepared runtime inventory changed")
    if evidence.load_json(inventory_path) != baseline:
        raise ValueError("HTTP and native prepared runtimes differ")
    evidence.write_json(output / "execution.json", {
        "schema_version": "agentops-http-execution/5", "started_at_utc": evidence.now(),
        "plan": evidence.digest(output / "plan.json"), "native_prerequisite": prerequisite})
    result = {"schema_version": "agentops-http-result/5", "status": "failed",
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
        for name in ("stdout", "stderr"):
            streams.append((output / f"service.{name}.bin").open("xb"))
        argv = [str(native.RUNTIME), "-B", str(SERVICE), "--output", str(output), "--port", str(port)]
        process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=streams[0], stderr=streams[1], shell=False, start_new_session=True)
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
        query(output, "get-pending", port, task_id, context_id, "input-required")
        snapshot("before-resume")
        call = calls[0]
        resume = {"jsonrpc": "2.0", "id": "approval-resume", "method": "message/stream", "params": {
            "message": {"kind": "message", "messageId": "approval-response", "role": "user",
                        "taskId": task_id, "contextId": context_id,
                        "parts": [{"kind": "data", "data": {"id": call["id"], "name": call["name"],
                                  "response": {"confirmed": True, "payload": {"rationale": RATIONALE}}},
                                   "metadata": {"adk_type": "function_response"}}]}}}
        wire.exchange(output, "resume", port, "POST", "/", resume)
        headers, body = response(output, "resume")
        snapshot("after-resume")
        if not headers.get("content-type", "").startswith("text/event-stream"):
            raise ValueError("Confirmation response is not SSE")
        completed = wire.rpc_results(body, "approval-resume")[-1]
        if (completed.get("taskId") != task_id or completed.get("contextId") != context_id
                or completed.get("status", {}).get("state") != "completed" or completed.get("final") is not True):
            raise ValueError("Confirmation did not complete the original task")
        query(output, "get-completed", port, task_id, context_id, "completed")
        snapshot("after-get-completed")
        result["status"] = "captured_check_pending"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            stop_owned_service(process, output, result)
        for stream in streams:
            try:
                stream.close()
            except Exception as error:
                result.setdefault("cleanup_errors", []).append(f"stream close: {type(error).__name__}: {error}")
        evidence.write_json(output / "boundaries.json", boundaries)
        try:
            result["source_unchanged_after"] = evidence.source_inventory() == plan["source_files"]
        except Exception as error:
            result["source_unchanged_after"] = False
            result["source_error"] = str(error)
        if result["status"] == "captured_check_pending":
            try:
                if result.get("forced_service_stop") or result.get("cleanup_errors") or result.get("service_returncode") != 0:
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
    parser.add_argument("--output", type=Path, default=RUNS / "native-http-linux-v5")
    parser.add_argument("--port", type=int, default=18761)
    args = parser.parse_args()
    target = evidence.within(args.output, RUNS)
    if args.command == "prepare":
        prepare(target, args.port)
    else:
        run(target)
