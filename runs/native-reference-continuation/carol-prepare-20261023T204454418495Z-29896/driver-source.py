"""Bounded original-source A2A 0.3 Carol probe. No bridge edits or model calls.

Prepare and execution are separate, exclusively recorded attempts. The original
public source is downloaded byte-for-byte and run in its own pinned environment.
"""
from __future__ import annotations

import argparse
import ast
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PIN = "6603ba3f2c31a7ef33e70b9d8b5b5f8be42ac9a3"
SOURCE_BASE = "samples/python/agents/number_guessing_game/"
RUNTIME = ROOT / "source-evidence" / "reference-continuation" / "runtime"
ORIGINAL = RUNTIME / "original-number-game"
VENV = RUNTIME / "python-3.12-sdk-0.3.0"
PYTHON = VENV / "Scripts" / "python.exe"
FILES = ["README.md", "agent_Alice.py", "agent_Bob.py", "agent_Carol.py", "config.py", "requirements.txt", "utils/__init__.py", "utils/game_logic.py", "utils/helpers.py", "utils/protocol_wrappers.py", "utils/server.py"]


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exclusive_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def safe_env() -> dict[str, str]:
    result = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME"):
        result.pop(key, None)
    result.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", PIP_CONFIG_FILE="NUL", PIP_NO_INPUT="1")
    return result


def subprocess_attempt(report: dict, label: str, command: list[str], timeout: int = 180) -> bytes:
    before = time.monotonic_ns()
    item = {"label": label, "command": command, "started_at_utc": utc(), "cwd": str(ROOT)}
    report["setup_attempts"].append(item)
    try:
        completed = subprocess.run(command, cwd=ROOT, env=safe_env(), capture_output=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stdout, stderr = completed.stdout, completed.stderr
        item.update(exit_code=completed.returncode, stdout_raw_base64=base64.b64encode(stdout).decode(), stderr_raw_base64=base64.b64encode(stderr).decode(), stdout_text=stdout.decode("utf-8", "replace"), stderr_text=stderr.decode("utf-8", "replace"))
        if completed.returncode:
            raise RuntimeError(f"{label} exited {completed.returncode}")
        return stdout
    except subprocess.TimeoutExpired as error:
        item.update(error=str(error), stdout_raw_base64=base64.b64encode(error.stdout or b"").decode(), stderr_raw_base64=base64.b64encode(error.stderr or b"").decode())
        raise
    finally:
        item.update(completed_at_utc=utc(), elapsed_ms=(time.monotonic_ns() - before) / 1e6)


INVENTORY_CODE = r'''
import importlib.metadata as m, hashlib, json, sys, platform
from pathlib import Path
from a2a.types import TaskState
result={'interpreter':sys.executable,'version':sys.version,'platform':platform.platform(),'task_state_values':{k:v.value for k,v in TaskState.__members__.items()},'distributions':[]}
for dist in sorted(m.distributions(),key=lambda d:d.metadata['Name'].lower()):
 files=[]
 for relative in sorted(dist.files or [],key=str):
  file=Path(dist.locate_file(relative))
  if not file.is_file() or file.suffix=='.pyc':continue
  data=file.read_bytes();files.append({'path':str(relative).replace('\\','/'),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 tree=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 result['distributions'].append({'name':dist.metadata['Name'],'version':dist.version,'installed_tree_sha256':tree,'files':files})
print(json.dumps(result,ensure_ascii=False))
'''


def source_hashes() -> dict[str, str]:
    return {relative: digest((ORIGINAL / relative).read_bytes()) for relative in FILES}


def prepare(report: dict, output_dir: Path) -> None:
    if ORIGINAL.exists() or VENV.exists():
        raise RuntimeError("Preparation destination already exists; inspect preserved attempt, do not overwrite it")
    ORIGINAL.mkdir(parents=True)
    source_records = []
    report["source_downloads"] = source_records
    for relative in FILES:
        url = f"https://raw.githubusercontent.com/a2aproject/a2a-samples/{PIN}/{SOURCE_BASE}{relative}"
        item = {"source_path": SOURCE_BASE + relative, "url": url, "started_at_utc": utc()}
        source_records.append(item)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "local-bounded-native-source-verification"}), timeout=30) as response:
                data = response.read()
                item.update(status=response.status, headers=dict(response.headers), sha256=digest(data), byte_length=len(data))
            destination = ORIGINAL / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(data)
        except Exception as error:
            item["error"] = repr(error)
            raise
        finally:
            item["completed_at_utc"] = utc()
    report["original_source_sha256"] = source_hashes()
    subprocess_attempt(report, "create_isolated_venv", [sys.executable, "-m", "venv", str(VENV)])
    subprocess_attempt(report, "install_original_exact_requirements", [str(PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-r", str(ORIGINAL / "requirements.txt")], 300)
    freeze = subprocess_attempt(report, "freeze_resolved_dependencies", [str(PYTHON), "-m", "pip", "freeze", "--all"])
    with (RUNTIME / "resolved-requirements.txt").open("xb") as handle:
        handle.write(freeze)
    inventory_bytes = subprocess_attempt(report, "inventory_installed_sources_before_execution", [str(PYTHON), "-c", INVENTORY_CODE], 120)
    inventory = json.loads(inventory_bytes)
    exclusive_json(RUNTIME / "installed-artifacts.json", inventory)
    report["installed_artifacts_sha256"] = digest((RUNTIME / "installed-artifacts.json").read_bytes())
    report["resolved_requirements_sha256"] = digest(freeze)
    report["resolved_distributions"] = [{key: dist[key] for key in ("name", "version", "installed_tree_sha256")} for dist in inventory["distributions"]]
    exclusive_json(RUNTIME / "original-source-manifest.json", {"repository": "https://github.com/a2aproject/a2a-samples", "commit": PIN, "source_sha256": source_hashes(), "protocol": "A2A 0.3.0 JSONRPC, message/send and tasks/get", "required": ["a2a-sdk==0.3.0", "uvicorn==0.35.0"], "model_calls": 0, "original_sources_modified": False})


def carol_port() -> int:
    tree = ast.parse((ORIGINAL / "config.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "AGENT_CAROL_PORT" for target in node.targets):
            return int(ast.literal_eval(node.value))
    raise RuntimeError("Original Carol port not a plain literal; no substitution performed")


def run_probe(report: dict, output_dir: Path) -> None:
    prepared = json.loads((RUNTIME / "original-source-manifest.json").read_text(encoding="utf-8"))
    before_hashes = source_hashes()
    if before_hashes != prepared["source_sha256"]:
        raise RuntimeError("Original source changed after preparation")
    report["original_source_sha256"] = before_hashes
    inventory = json.loads((RUNTIME / "installed-artifacts.json").read_text(encoding="utf-8"))
    report["installed_artifacts_sha256"] = digest((RUNTIME / "installed-artifacts.json").read_bytes())
    report["resolved_requirements_sha256"] = digest((RUNTIME / "resolved-requirements.txt").read_bytes())
    report["isolated_interpreter"] = {key: inventory[key] for key in ("interpreter", "version", "platform", "task_state_values")}
    subprocess_attempt(report, "verify_original_SDK_imports", [str(PYTHON), "-c", "import importlib.metadata as m; import a2a.server.apps.jsonrpc.starlette_app; from a2a.server.tasks.task_updater import TaskUpdater; print(m.version('a2a-sdk')); print(m.version('uvicorn'))"])
    port = carol_port()
    report["endpoint"] = f"http://127.0.0.1:{port}"
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError("Original fixed Carol port already occupied; no process terminated or port rewritten")
    command = [str(PYTHON), str(ORIGINAL / "agent_Carol.py")]
    child = subprocess.Popen(command, cwd=ORIGINAL, env=safe_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    report["process"] = {"pid": child.pid, "command": command, "cwd": str(ORIGINAL), "started_at_utc": utc()}
    output = {"stdout": bytearray(), "stderr": bytearray()}
    def drain(name: str, pipe) -> None:
        while chunk := pipe.read(1024):
            output[name].extend(chunk)
    threads = [threading.Thread(target=drain, args=(name, getattr(child, name)), daemon=True) for name in output]
    for thread in threads:
        thread.start()
    exchanges = report.setdefault("http_exchanges", [])
    sequence = 0
    def http(phase: str, method: str | None, params: dict | None = None, path: str = "/a2a/v1") -> dict:
        nonlocal sequence
        sequence += 1
        json_request = {"jsonrpc": "2.0", "id": f"native-{sequence}", "method": method, "params": params or {}} if method else None
        body = json.dumps(json_request, ensure_ascii=False, separators=(",", ":")).encode() if json_request else None
        headers = {"Content-Type": "application/json"} if body else {}
        endpoint = report["endpoint"] + path
        start = time.monotonic_ns()
        exchange = {"exchange_id": f"native-{sequence}", "phase": phase, "role": "native-client-to-original-Carol", "protocol": "A2A 0.3.0 JSONRPC" if method else "AgentCard HTTP discovery", "task_namespace": "Original Carol A2A task UUID", "context_namespace": "Original Carol A2A context UUID", "source": {"endpoint": endpoint, "sample_commit": PIN}, "request": {"url": endpoint, "http_method": "POST" if body else "GET", "headers": headers, "raw": body.decode() if body else None, "raw_base64": base64.b64encode(body).decode() if body else None, "json": json_request, "sha256": digest(body) if body else None, "started_at_utc": utc(), "monotonic_ns": start}, "response": None, "validity_interval": None, "recipient_authority": None}
        exchanges.append(exchange)
        try:
            try:
                response = urllib.request.urlopen(urllib.request.Request(endpoint, data=body, headers=headers), timeout=10)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                raw = response.read()
                exchange["response"] = {"status": response.status, "headers": dict(response.headers), "raw": raw.decode("utf-8"), "raw_base64": base64.b64encode(raw).decode(), "sha256": digest(raw), "json": json.loads(raw), "observed_at_utc": utc(), "monotonic_ns": time.monotonic_ns()}
            return exchange["response"]["json"]
        except Exception as error:
            exchange["error"] = repr(error)
            raise
        finally:
            exchange["elapsed_ms"] = (time.monotonic_ns() - start) / 1e6
    def rpc(phase: str, method: str, params: dict) -> dict:
        result = http(phase, method, params)
        if result.get("error"):
            raise RuntimeError(f"Native RPC returned {result['error']}")
        if "result" not in result:
            raise RuntimeError("Native RPC response has no result")
        return result["result"]
    expected_waiting = inventory["task_state_values"]["input_required"]
    def observe(task_id: str, wanted: str, phase: str) -> dict:
        end = time.monotonic() + 5
        last = None
        while time.monotonic() < end:
            last = rpc(phase, "tasks/get", {"id": task_id})
            if last.get("status", {}).get("state") == wanted:
                return last
            time.sleep(0.05)
        raise RuntimeError(f"Native task never observed {wanted}; last={last}")
    try:
        end = time.monotonic() + 10
        while time.monotonic() < end:
            if child.poll() is not None:
                raise RuntimeError(f"Original Carol exited {child.returncode} during startup")
            with socket.socket() as probe:
                probe.settimeout(0.2)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("Original Carol startup timed out")
        report["process"]["ready_at_utc"] = utc()
        card = http("agent_card", None, path="/.well-known/agent-card.json")
        report["observed_card"] = card
        controls = report.setdefault("controls", [])
        initial_text = json.dumps({"action": "shuffle", "history": [{"guess": 25, "response": "Go higher"}]}, separators=(",", ":"))
        report["contract"] = {"initial_text": initial_text, "answer_text": "Well done!", "initial_history_reason": "Single-entry Bob-valid history is already sorted; no source/random generator patch", "continuation_goal": "Same original task reaches completed", "guard_scope": "Public Carol application branch, not A2A-mandated dependency enforcement"}
        for name, with_refs, with_task_id in [("same_task_with_reference", True, True), ("same_task_without_reference", False, True), ("context_only_without_reference", False, False)]:
            control = {"control_id": name, "with_refs": with_refs, "with_task_id": with_task_id}
            controls.append(control)
            try:
                initial = rpc(name + ":create", "message/send", {"message": {"kind": "message", "role": "user", "messageId": uuid.uuid4().hex, "parts": [{"kind": "text", "text": initial_text}]}})
                pending = observe(initial["id"], expected_waiting, name + ":get_pending")
                task_id, context_id = pending["id"], pending["contextId"]
                control.update(task_id=task_id, context_id=context_id, pending=pending)
                message = {"kind": "message", "role": "user", "messageId": uuid.uuid4().hex, "contextId": context_id, "referenceTaskIds": [task_id] if with_refs else [], "parts": [{"kind": "text", "text": "Well done!"}]}
                if with_task_id:
                    message["taskId"] = task_id
                answered = rpc(name + ":answer", "message/send", {"message": message})
                control["answer_reply"] = answered
                final = rpc(name + ":get_original_after_answer", "tasks/get", {"id": task_id})
                control.update(final_original_task=final, same_task_answer_id=answered.get("id") == task_id, same_context_answer=answered.get("contextId") == context_id)
                if answered.get("id") and answered["id"] != task_id:
                    control["answer_created_task_get"] = rpc(name + ":get_answer_created_task", "tasks/get", {"id": answered["id"]})
                control["native_completion_observed"] = final.get("status", {}).get("state") == "completed"
                control["outcome"] = "observed"
            except Exception as error:
                control.update(outcome="failed", error=repr(error))
        report["source_discrimination_observed"] = controls[0].get("native_completion_observed") is True and controls[1].get("native_completion_observed") is False and controls[0].get("same_task_answer_id") is True and controls[1].get("same_task_answer_id") is True
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                report["process"]["forced_kill_exact_pid"] = child.pid
                child.kill()
                child.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=2)
        report["process"].update(exit_code=child.returncode, terminal_verified=child.poll() is not None, cleanup_at_utc=utc(), stdout_raw_base64=base64.b64encode(output["stdout"]).decode(), stderr_raw_base64=base64.b64encode(output["stderr"]).decode(), stdout_text=output["stdout"].decode("utf-8", "replace"), stderr_text=output["stderr"].decode("utf-8", "replace"))
        report["original_source_unchanged_after_execution"] = source_hashes() == before_hashes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run"))
    args = parser.parse_args()
    run_id = f"carol-{args.mode}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{os.getpid()}"
    output_dir = ROOT / "runs" / "native-reference-continuation" / run_id
    output_dir.mkdir(parents=True)
    report = {"schema_version": "native-reference-continuation/1", "run_id": run_id, "mode": args.mode, "started_at_utc": utc(), "command": sys.argv, "environment": {"interpreter": sys.executable, "version": sys.version, "platform": platform.platform(), "isolated_env_overrides": {key: safe_env()[key] for key in ("PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "PIP_CONFIG_FILE", "PIP_NO_INPUT")}}, "source_commit": PIN, "protocol": "Original A2A 0.3.0 JSONRPC", "setup_attempts": [], "model_calls": 0, "claim_limit": "Development native application-source verification; no bridge compatibility, natural defect, efficiency result or novelty claim"}
    with (output_dir / "driver-source.py").open("xb") as handle:
        handle.write(Path(__file__).read_bytes())
    try:
        (prepare if args.mode == "prepare" else run_probe)(report, output_dir)
        report["outcome"] = "prepared" if args.mode == "prepare" else "observed"
        report["exit_code"] = 0
    except Exception as error:
        report.update(outcome="failed", exit_code=1, error=repr(error))
    finally:
        report["completed_at_utc"] = utc()
        exclusive_json(output_dir / "report.json", report)
        print(json.dumps({"outcome": report["outcome"], "exit_code": report["exit_code"], "output": str(output_dir / "report.json"), "error": report.get("error")}))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
