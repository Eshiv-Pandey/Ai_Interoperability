"""Once-only isolated dependency setup, then the upstream offline control.

Preserve every setup/test result. Never import application code in this
supervisor, modify the upstream source/lock, or replace a failed attempt.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "external/agentops-c806b7f1"
PROJECT = TREE / "agents/python"
RUNTIME = ROOT / "external/runtime-agentops-v1"
RUN = ROOT / "runs/agentops-native-eligibility/v1"
PYTHON = ROOT / ".venv/Scripts/python.exe"
TEST = "tests/test_server.py::test_a2a_confirmation_response_resumes_the_guarded_action_with_audit_identity"
if RUN.exists() or RUNTIME.exists():
    raise SystemExit("Refusing to repeat or overwrite setup/control v1.")


def receipt(path):
    data = path.read_bytes()
    return {"path": path.resolve().relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


ingestion = json.loads((ROOT / "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json").read_text())
assert ingestion["status"] == "passed" and ingestion["regular_files"] == 421
for item in ingestion["records"]:
    assert receipt(ROOT / item["extracted"]["path"]) == item["extracted"]
stable = [receipt(TREE / relative) for relative in [
    "AGENTS.md", "agents/LICENSE", "agents/data/incidents.db", "agents/python/pyproject.toml",
    "agents/python/uv.lock", "agents/python/tests/conftest.py", "agents/python/tests/test_server.py",
    "agents/python/src/agent/actions.py", "agents/python/src/agent/data.py", "agents/python/src/agent/server.py",
]]
assert sys.version_info[:2] == (3, 13)
RUN.mkdir(parents=True)
RUNTIME.mkdir(parents=True)
bootstrap = RUNTIME / "bootstrap"
venv = RUNTIME / "venv"
base_env = dict(os.environ)
base_env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
uv_env = dict(base_env)
uv_env.update({
    "PYTHONPATH": str(bootstrap), "UV_PROJECT_ENVIRONMENT": str(venv),
    "UV_CACHE_DIR": str(RUNTIME / "uv-cache"), "UV_PYTHON_DOWNLOADS": "never",
    "UV_HTTP_TIMEOUT": "15", "UV_HTTP_RETRIES": "0", "UV_NO_PROGRESS": "1",
})
commands = [
    {"id": "bootstrap", "argv": [str(PYTHON), "-m", "pip", "install", "--no-cache-dir",
        "--disable-pip-version-check", "--retries", "0", "--timeout", "15",
        "--only-binary=:all:", "--target", str(bootstrap), "uv==0.12.0"],
     "cwd": ROOT, "env": base_env, "timeout_seconds": 180},
    {"id": "locked-sync", "argv": [str(PYTHON), "-m", "uv", "sync", "--locked",
        "--project", str(PROJECT), "--python", str(PYTHON)],
     "cwd": ROOT, "env": uv_env, "timeout_seconds": 900},
    {"id": "upstream-confirmation", "argv": [str(venv / "Scripts/python.exe"), "-m", "pytest",
        "--basetemp", str(RUNTIME / "test-temp"), "-o", "cache_dir=" + str(RUNTIME / "pytest-cache"), TEST],
     "cwd": PROJECT, "env": base_env, "timeout_seconds": 300},
]
write_new(RUN / "pre-execution.json", {
    "schema_version": "agentops-native-preparation/1", "prepared_at_utc": datetime.now(UTC).isoformat(),
    "source_ingestion": receipt(ROOT / "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json"),
    "source_files_before": stable, "commands": [
        {key: str(value) if isinstance(value, Path) else value for key, value in item.items() if key != "env"}
        for item in commands], "sequence_stops_on_any_failure": True,
    "dependency_tool_pin_source": "external/agentops-c806b7f1/mise.toml: aqua:astral-sh/uv=0.12.0",
    "isolated_runtime": RUNTIME.relative_to(ROOT).as_posix(), "source_changes_authorized": False,
    "source_symlinks_not_materialized": True,
    "test_scope": "Single unchanged upstream offline test; not root maintainer/full coverage gate, real-pipe HTTP trace, independent gold or domain qualification.",
    "model_double": "Upstream _ConfirmationLlm; conftest clears provider/runtime variables and disables telemetry",
    "study_inference_authorized_or_planned": False,
})
steps = []
for command in commands:
    started = datetime.now(UTC)
    try:
        completed = subprocess.run(command["argv"], cwd=command["cwd"], env=command["env"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=command["timeout_seconds"], check=False)
        stdout, stderr, exit_code, timed_out = completed.stdout, completed.stderr, completed.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, exit_code, timed_out = error.stdout or b"", error.stderr or b"", None, True
    except OSError as error:
        stdout, stderr, exit_code, timed_out = b"", str(error).encode("utf-8"), None, False
    output_paths = []
    for label, payload in [("stdout", stdout), ("stderr", stderr)]:
        path = RUN / (command["id"] + "." + label + ".bin")
        with path.open("xb") as stream:
            stream.write(payload)
        output_paths.append(receipt(path))
    step = {"id": command["id"], "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(UTC).isoformat(), "exit_code": exit_code,
            "timed_out": timed_out, "streams": output_paths,
            "stdout_utf8": stdout.decode("utf-8", errors="replace"),
            "stderr_utf8": stderr.decode("utf-8", errors="replace")}
    write_new(RUN / (command["id"] + ".json"), step)
    steps.append(step)
    print(json.dumps(step, indent=2), flush=True)
    if exit_code != 0:
        break
for item in ingestion["records"]:
    assert receipt(ROOT / item["extracted"]["path"]) == item["extracted"]
summary = {
    "schema_version": "agentops-native-preparation-result/1", "finished_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed_focused_control" if len(steps) == 3 and all(item["exit_code"] == 0 for item in steps) else "setup_or_control_failed",
    "steps_executed": [item["id"] for item in steps],
    "stopped_at": steps[-1]["id"], "all_source_payloads_unchanged": True,
    "upstream_test_executed": any(item["id"] == "upstream-confirmation" for item in steps),
    "paid_or_live_model_calls": 0, "wire_bridge_requests": 0,
    "qualified_second_domain": False, "novelty_demonstrated": False,
    "human_review_completed": False, "checkpoint_progress_percent": 5,
    "full_upstream_maintainer_gate_run": False, "goal_complete": False,
}
write_new(RUN / "result.json", summary)
print(json.dumps(summary, indent=2), flush=True)
