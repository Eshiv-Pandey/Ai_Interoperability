"""One fresh native control followed by one admitted B7; importing never launches."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import agentops_admission_live_plan_v1 as design
import agentops_native_probe_v2 as evidence
import agentops_protocol_wire_v1 as wire
from agentops_owned_process_v1 import finish_owned_group
from check_agentops_effect_v2 import at_utc, seed_snapshot
from check_agentops_bridge_v1 import check_case, check_service, check_owned_group, parse_asgi_exchange
from check_agentops_bridge_diagnostic_v1 import validate_diagnostics

ROOT = design.ROOT


def boundary(service, name):
    design.write_new(service / (name + ".snapshot.json"), {"observed_at_utc": design.now(),
        "monotonic_ns": time.monotonic_ns(),
        "database": evidence.database_snapshot(service / "state/incidents.db", service, "run")})


def evaluator_read(service, case):
    """Read the original task only after caller group exit; never feed IDs back."""
    for folder in sorted((service / "wire").iterdir()):
        if not (folder / "exchange.json").exists():
            continue
        exchange = parse_asgi_exchange(folder)
        request = exchange.get("request")
        if not isinstance(request, dict) or request.get("method") not in ("SendMessage", "SendStreamingMessage"):
            continue
        for response in exchange.get("responses", []):
            value = response.get("result")
            if not isinstance(value, dict):
                continue
            value = value.get("task", value.get("statusUpdate", value))
            task = value.get("taskId", value.get("id"))
            context = value.get("contextId")
            if isinstance(task, str) and task and isinstance(context, str) and context:
                output = case / "evaluator"; output.mkdir(exist_ok=False)
                wire.exchange(output, "final", design.PORT, "POST", {"jsonrpc": "2.0", "id": "evaluator-final",
                    "method": "GetTask", "params": {"id": task}}, "1.0")
                return {"executed": True, "task_id": task, "context_id": context,
                    "grader_only": True, "available_to_client": False,
                    "source_sequence": exchange["record"]["sequence"]}
        break
    return {"executed": False, "reason": "No captured original task binding", "grader_only": True, "available_to_client": False}


def allowed_client_commands(argv, case, config):
    allowed = [argv]
    if "bridge" in config:
        allowed.append([config["bridge"]["command"], *config["bridge"]["args"]])
        receipt = case / "client/admission/execution.json"
        if receipt.exists():
            value = design.load(receipt); actual = value["args"]
            if (value.get("schema_version") != "agentops-admission-subprocess/1"
                    or type(actual) is not list or len(actual) != 11
                    or any(type(value) is not str for value in actual)
                    or not actual[8].isascii() or not actual[8].isdigit()
                    or str(int(actual[8])) != actual[8]):
                raise ValueError("Malformed or noncanonical admission child arguments")
            expected = ["-B", "-m", "interoperability.pending_admission", "--input",
                str(case / "client/admission/snapshot.json"), "--output", str(case / "client/admission/result.json"),
                "--now", str(int(actual[8])), "--budget", "100000"]
            if (actual != expected or value["executable"] != config["admission"]["python"]
                    or value.get("cwd") != str(ROOT)):
                raise ValueError("Admission child command does not match the frozen local operation")
            allowed.append([value["executable"], *expected])
    return allowed


def capture_client(argv, case, config):
    receipt = {"argv": argv, "cwd": str(ROOT), "started_at_utc": design.now(),
        "timed_out": False, "forced_kill": False, "cleanup_errors": []}
    process = None
    with (case / "client.stdout.bin").open("xb") as stdout, (case / "client.stderr.bin").open("xb") as stderr:
        try:
            process = subprocess.Popen(argv, cwd=ROOT, env=design.bridge_environment(case), stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True)
            receipt["pid"] = process.pid
            design.write_new(case / "client.started.json", receipt)
            process.wait(timeout=220)
        except BaseException as error:
            receipt["error"] = f"{type(error).__name__}: {error}"
            receipt["timed_out"] = isinstance(error, subprocess.TimeoutExpired)
        finally:
            if process is not None:
                try:
                    group = finish_owned_group(process.pid, allowed_client_commands(argv, case, config))
                    receipt["owned_group"] = group
                    receipt["forced_kill"] = any(row["signal"] == "SIGKILL" for row in group["signals"])
                    receipt["cleanup_errors"].extend(group["errors"])
                    process.wait(timeout=10)
                except Exception as error:
                    receipt["cleanup_errors"].append(f"Client cleanup: {type(error).__name__}: {error}")
            receipt["returncode"] = None if process is None else process.returncode
            receipt["finished_at_utc"] = design.now()
    receipt["streams"] = [design.record(case / f"client.{suffix}.bin", ROOT) for suffix in ("stdout", "stderr")]
    design.write_new(case / "client-process.json", receipt)
    return receipt


def clean_group(group):
    return (group.get("initially_empty") is True and group.get("final_empty") is True
            and group.get("forced_cleanup") is False and not group.get("errors"))


def stop_service(process, argv, service, result):
    try:
        design.write_new(service / "stop-requested.json", {"requested_at_utc": design.now()})
    except Exception as error:
        result["cleanup_errors"].append("Stop request: " + str(error))
    result["forced_service_stop"] = False
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        result["forced_service_stop"] = True
    except Exception as error:
        result["cleanup_errors"].append("Service wait: " + str(error))
    group = finish_owned_group(process.pid, [argv])
    result["service_group_cleanup"] = group
    result["forced_service_stop"] |= group["forced_cleanup"]
    result["cleanup_errors"].extend(group["errors"])
    try:
        process.wait(timeout=10)
    except Exception as error:
        result["cleanup_errors"].append("Final service wait: " + str(error))
    result["service_returncode"] = process.returncode


def check_certified_origin_request(case, original):
    """Bind certificate MCP arguments to exact ASGI method/params; RPC IDs vary."""
    report = {"valid": False, "errors": [], "continuation_count": 0}
    try:
        receipt = design.load(case / "client/admission/result.json")
        request = receipt["request"]
        if request["method"] != "tools/call" or request["params"]["name"] != "a2a_request":
            raise ValueError("Certificate did not name the admitted raw MCP operation")
        raw = request["params"]["arguments"]
        continuations = []
        for folder in sorted((case / "service/wire").iterdir()):
            exchange = parse_asgi_exchange(folder)
            observed = exchange.get("request")
            if (isinstance(observed, dict) and isinstance(observed.get("params"), dict)
                    and isinstance(observed["params"].get("message"), dict)
                    and observed["params"]["message"].get("taskId") == original["task_id"]):
                continuations.append(exchange)
        report["continuation_count"] = len(continuations)
        if len(continuations) != 1:
            raise ValueError("Expected exactly one ASGI continuation for the original task")
        observed = continuations[0]["request"]
        canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        if (raw["method"] != "SendMessage" or observed.get("method") != raw["method"]
                or canonical(observed.get("params")) != canonical(raw["params"])):
            raise ValueError("Actual origin method/params differ from the certified public request")
        report.update(valid=True, service_sequence=continuations[0]["record"]["sequence"],
            admission_receipt=design.record(case / "client/admission/result.json", ROOT))
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    return report


def admitted_case_check(case, plan, result, service_check):
    from check_agentops_admitted_client_v1 import check_client
    expected = {row["path"]: row["sha256"] for row in plan["inputs"]}
    client = check_client(case / "client", source_root=ROOT, expected_sources=expected)
    errors = []
    if not client.get("client_scope_verified"):
        errors.append("Independent admitted client check failed")
    if not service_check.get("strict_success"):
        errors.append("Independent task/effect check did not establish strict success")
    if (case / "client/config.json").read_bytes() != (case / "client-config.json").read_bytes():
        errors.append("Prepared/executed client configuration differs")
    case_plan = design.load(case / "plan.json")
    if design.record(case / "client-config.json", ROOT) != case_plan["client_config"]:
        errors.append("Client configuration differs from its prospective case digest")
    bindings = client.get("public_bindings", {})
    original = service_check.get("original") or {}
    if not original or any(bindings.get(key) != value for key, value in original.items()):
        errors.append("Client public task/context does not bind the independently checked service task")
    linkage = check_certified_origin_request(case, original)
    if not linkage["valid"]:
        errors.extend(linkage["errors"])
    process = design.load(case / "client-process.json")
    service_process = design.load(case / "service-process.json")
    if any(process.get(source) != result.get(target) for source, target in (
            ("returncode", "client_returncode"), ("timed_out", "client_timed_out"),
            ("forced_kill", "client_forced_kill"))):
        errors.append("Client process receipt/result fields differ")
    if (type(process.get("returncode")) is not int or process["returncode"] != 0
            or process.get("timed_out") is not False or process.get("forced_kill") is not False
            or process.get("cleanup_errors") or result.get("cleanup_errors")):
        errors.append("Client process/cleanup flags are not clean")
    try:
        if at_utc(process["started_at_utc"]) > at_utc(process["finished_at_utc"]):
            errors.append("Client process receipt timestamps are reversed")
        stamp = service_check.get("evaluator_final_started_at_utc")
        if not stamp or at_utc(stamp) < at_utc(process["finished_at_utc"]):
            errors.append("Evaluator final read is missing or precedes client-process finish")
    except (ValueError, KeyError, TypeError) as error:
        errors.append("Client/evaluator timestamp binding failed: " + str(error))
    evaluator = result.get("evaluator_query", {})
    if (evaluator.get("executed") is not True or evaluator.get("grader_only") is not True
            or evaluator.get("available_to_client") is not False
            or any(evaluator.get(key) != value for key, value in original.items())):
        errors.append("Evaluator query is not bound to the original task and excluded from client inputs")
    if (process.get("owned_group") != result.get("client_group_cleanup")
            or not check_owned_group(process.get("owned_group"), process.get("pid"))
            or not check_owned_group(result.get("service_group_cleanup"), service_process.get("pid"))):
        errors.append("Independent owned-process receipt checks failed")
    if (result.get("status") != "recorded" or result.get("bridge_clean_exit") is not True
            or result.get("bridge_forced_kill") is not False
            or type(result.get("service_returncode")) is not int or result["service_returncode"] != 0
            or result.get("forced_service_stop") is not False or result.get("source_unchanged_after") is not True):
        errors.append("Case/client did not finish cleanly")
    return {"schema_version": "agentops-admitted-case-check/1", "case_id": "B7",
        "strict_success": not errors, "validation_errors": errors, "client": client, "service": service_check,
        "certificate_to_origin": linkage,
        "qualified_second_domain": False, "scientific_gate_credit_added": 0,
        "claim_limit": "One fresh conditional fixture admission, actual protocol completion and domain effect; no generalized novelty or domain qualification"}


def run_case(case_id, plan, plan_path):
    design.verify(plan)
    definition = design.CASES[case_id]
    case = ROOT / (design.CASE_PREFIX + case_id)
    if case.exists():
        raise FileExistsError("Preserve allocated case; no rerun: " + str(case))
    design.probe_port()
    source = evidence.source_inventory()
    case.mkdir(parents=True, exist_ok=False); (case / "temp").mkdir()
    service = case / "service"; service.mkdir(); (service / "temp").mkdir()
    config = design.client_config(case_id, case, plan)
    design.write_new(case / "client-config.json", config)
    design.write_new(case / "plan.json", {"schema_version": "agentops-bridge-case-plan/1", **definition,
        "port": design.PORT, "client_config": design.record(case / "client-config.json", ROOT),
        "service_source": design.record(ROOT / "scripts/serve_agentops_bridge_diagnostic_v2.py", ROOT),
        "source_files": source, "prepared_at_utc": design.now(), "admission_preparation": design.record(plan_path, ROOT)})
    result = {"schema_version": "agentops-bridge-case-result/1", "case_id": case_id,
        "kind": definition["kind"], "status": "failed", "started_at_utc": design.now(),
        "cleanup_errors": [], "live_model_calls": 0, "research_gate_credit_added": 0}
    process = None; streams = []; service_check = {}
    argv = [plan["runtime_python"], "-B", str(ROOT / "scripts/serve_agentops_bridge_diagnostic_v2.py"),
            "--output", str(service), "--port", str(design.PORT)]
    try:
        environment = evidence.clean_environment(service)
        environment.update({"PYTHONPATH": os.pathsep.join([str(ROOT / "scripts"), str(ROOT / "src"),
            str(evidence.PROJECT / "src")]), "AGENT_MODEL_PROVIDER": "openai-compatible", "AGENT_MODEL": "qwen3:4b-instruct",
            "AGENT_DATA_DIR": str(evidence.SOURCE / "agents/data"), "AGENT_STATE_DIR": str(service / "state"),
            "AGENT_A2A_HOST": "127.0.0.1", "AGENT_A2A_BIND_HOST": "127.0.0.1", "AGENT_A2A_PORT": str(design.PORT)})
        streams = [(case / f"service.{suffix}.bin").open("xb") for suffix in ("stdout", "stderr")]
        process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=streams[0], stderr=streams[1], start_new_session=True)
        design.write_new(case / "service-process.json", {"argv": argv, "pid": process.pid,
            "started_at_utc": design.now(), "staged_pythonpath": environment["PYTHONPATH"]})
        deadline = time.monotonic() + 65
        while not (service / "service-ready.json").exists():
            if process.poll() is not None:
                raise RuntimeError("Fixture exited before readiness")
            if time.monotonic() >= deadline:
                raise TimeoutError("Fixture readiness deadline")
            time.sleep(0.1)
        ready = design.load(service / "service-ready.json")
        expected_factory = evidence.PROJECT / "src/agent/server.py"
        if Path(ready.get("source_factory", "")).resolve() != expected_factory.resolve():
            raise ValueError("Service imported the old editable application instead of the staged source")
        script = "agentops_native_profile_client_v1.mjs" if case_id == "N11" else "agentops_admission_client_v1.mjs"
        receipt = capture_client([plan["node"]["path"], str(ROOT / "scripts" / script), "--config", str(case / "client-config.json")], case, config)
        result.update(client_returncode=receipt["returncode"], client_timed_out=receipt["timed_out"],
            client_forced_kill=receipt["forced_kill"], client_group_cleanup=receipt.get("owned_group", {}))
        result["cleanup_errors"].extend(receipt["cleanup_errors"])
        if case_id == "B7":
            client = design.load(case / "client/result.json")
            result["bridge_clean_exit"] = client.get("child", {}).get("clean_exit") is True
            result["bridge_forced_kill"] = client.get("child", {}).get("forced_kill", False)
            result["continuation_forwarded_attempts"] = client.get("answer_attempts")
            result["admission_status"] = client.get("admission", {}).get("status")
        if not clean_group(receipt.get("owned_group", {})) or receipt["cleanup_errors"]:
            raise ValueError("Caller group is not clean; evaluator withheld")
        result["evaluator_query"] = evaluator_read(service, case)
        boundary(service, "final")
        result["status"] = "recorded" if receipt["returncode"] == 0 else "failed"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            stop_service(process, argv, service, result)
        for stream in streams:
            stream.close()
        if (service / "state/incidents.db").is_file() and result.get("service_group_cleanup", {}).get("final_empty"):
            try:
                boundary(service, "terminal")
            except Exception as error:
                result["cleanup_errors"].append("Terminal snapshot: " + str(error))
        try:
            result["source_unchanged_after"] = evidence.source_inventory() == source
            result["prepared_inputs_after"] = design.verify(plan)
        except Exception as error:
            result["source_unchanged_after"] = False; result["source_check_error"] = str(error)
        try:
            service_check = check_service(service, seed_snapshot(evidence.SOURCE / "agents/data/incidents.db"))
            design.write_new(case / "check.json", service_check)
            result["service_strict_success"] = service_check["strict_success"]
        except Exception as error:
            result["checker_error"] = str(error)
        if (result.get("forced_service_stop") or result.get("cleanup_errors") or result.get("source_unchanged_after") is not True
                or result.get("service_returncode") != 0 or not clean_group(result.get("client_group_cleanup", {}))
                or not clean_group(result.get("service_group_cleanup", {}))):
            result["status"] = "failed"
        result["finished_at_utc"] = design.now()
        result["files"] = [design.record(path, ROOT) for path in sorted(case.rglob("*")) if path.is_file()]
        design.write_new(case / "result.json", result)
        try:
            checked = (check_case(case, seed_snapshot(evidence.SOURCE / "agents/data/incidents.db")) if case_id == "N11"
                       else admitted_case_check(case, plan, result, service_check))
            design.write_new(case / "case-check.json", checked)
        except Exception as error:
            checked = {"strict_success": False, "error": f"{type(error).__name__}: {error}"}
            design.write_new(case / "case-check-error.json", checked)
        diagnostics = validate_diagnostics(case, checked)
        design.write_new(case / "diagnostic-check.json", diagnostics)
    strict = (checked.get("strict_success") is True and result["status"] == "recorded"
              and diagnostics.get("valid") is True and diagnostics.get("complete") is True
              and diagnostics.get("classification") == "asyncio_run_returned")
    return {"status": result["status"], "strict_success": strict,
            "case": str(case), "result": design.record(case / "result.json", ROOT)}


def run_group(plan_path):
    if sys.platform != "linux":
        raise ValueError("Fresh live execution requires Linux")
    plan = design.load(plan_path); design.verify(plan, require_unexecuted=True)
    output = ROOT / design.GROUP / "attempt"; output.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": "agentops-admission-live-group/1", "status": "started",
        "started_at_utc": design.now(), "plan": design.record(plan_path, ROOT), "cases": {},
        "live_model_calls": 0, "research_gate_credit_added": 0, "qualified_second_domain": False}
    design.write_new(output / "execution.json", report)
    active_case = None
    try:
        for case_id in design.CASES:
            if case_id == "B7" and (not report["cases"]["N11"]["strict_success"]
                                    or report["cases"]["N11"]["status"] != "recorded"):
                report["cases"][case_id] = {"status": "skipped", "reason": "Fresh matched native control did not qualify", "strict_success": False}
                design.write_new(output / "B7.skipped.json", report["cases"][case_id]); break
            print(f"Starting new {case_id} once", flush=True)
            design.write_new(output / (case_id + ".invocation.json"), {"case_id": case_id,
                "invoked_at_utc": design.now(), "planned_case_path": str(ROOT / (design.CASE_PREFIX + case_id)),
                "scope": "Coordinator invocation marker; application launch is proved by owned process receipts"})
            active_case = case_id
            report["cases"][case_id] = run_case(case_id, plan, plan_path)
            active_case = None
        report["status"] = "strict_success" if all(report["cases"].get(name, {}).get("strict_success") for name in design.CASES) else "attempts_recorded"
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        if active_case is not None and active_case not in report["cases"]:
            case = ROOT / (design.CASE_PREFIX + active_case)
            partial = {"status": "failed_partial" if case.exists() else "failed_before_allocation",
                "strict_success": False, "allocated": case.exists(), "case": str(case), "error": report["error"],
                "service_process_receipt_present": (case / "service-process.json").is_file(),
                "client_process_receipt_present": (case / "client.started.json").is_file(),
                "case_result_present": (case / "result.json").is_file()}
            report["cases"][active_case] = partial
            design.write_new(output / (active_case + ".partial.json"), partial)
    finally:
        for case_id in design.CASES:
            if case_id not in report["cases"]:
                report["cases"][case_id] = {"status": "unexecuted", "strict_success": False, "reason": report.get("error", "group stopped")}
                design.write_new(output / (case_id + ".unexecuted.json"), report["cases"][case_id])
        try:
            report["prepared_inputs_after"] = design.verify(plan)
            report["plan_unchanged"] = design.record(plan_path, ROOT) == report["plan"]
            if not report["plan_unchanged"]:
                raise ValueError("Prospective plan bytes changed during execution")
        except Exception as error:
            report.update(status="failed_integrity", integrity_error=str(error))
        report["finished_at_utc"] = design.now(); design.write_new(output / "result.json", report)
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        verified = design.verify(design.load(args.plan), require_unexecuted=True)
        verified["port_probe"] = design.probe_port()
        print(json.dumps(verified, indent=2))
    else:
        result = run_group(args.plan)
        raise SystemExit(0 if result["status"] in ("strict_success", "attempts_recorded") else 1)
