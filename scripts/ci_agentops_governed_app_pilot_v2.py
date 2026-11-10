"""Provision the original locked AgentOps package and execute two governed-App tasks."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import tarfile
import tomllib
import uuid

from ci_agentops_admission_v1 import (ROOT, SOURCE_SHA, PYTHON, capture, extract_source, fetch,
                                    now, regular_bytes, sha, source_records, verified_source, write_new)

INGESTION = "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json"
TASKS = "benchmark/tasks-v1/agentops/application.json"
IDS = ("agentops-d01-health-active", "agentops-d03-restart-pause")
OWNED = ("scripts/agentops_governed_app_pilot_v2.py", "scripts/evaluate_agentops_governed_app_pilot_v2.py",
         "scripts/ci_agentops_governed_app_pilot_v2.py", "scripts/ci_agentops_admission_v1.py",
         "scripts/check_agentops_governed_app_pilot_v2.py", ".github/workflows/agentops-governed-app-pilot-v2.yml",
         "docs/research/agentops-governed-app-pilot-v2.md", "scripts/agentops_socket_diagnostics_v2.py")


def check_inputs():
    ingestion = json.loads(regular_bytes(ROOT / INGESTION))
    rows = source_records(ingestion)
    if ingestion["retained_archive"]["sha256"] != SOURCE_SHA:
        raise ValueError("Original source archive seal differs")
    bank = json.loads(regular_bytes(ROOT / TASKS))
    records = {r["id"]: r for r in bank["records"]}
    for task_id in IDS:
        record = records[task_id]
        if record["split"] != "development" or len(record["public"]["turns"]) != 1:
            raise ValueError("Pilot only accepts the declared one-turn development tasks")
        recipe = record["public"]["fixture_recipe"]
        if recipe["application_entrypoint"] != "agent" or recipe["before_start_changes"]:
            raise ValueError("Public fixture recipe differs")
    inputs = [{"path": name, "bytes": len(regular_bytes(ROOT / name)), "sha256": sha(regular_bytes(ROOT / name))}
              for name in (*OWNED, INGESTION, TASKS, "benchmark/tasks-v1/agentops/evaluator.json")]
    return {"status": "public_pilot_inputs_verified", "source_files": len(rows), "tasks": list(IDS),
            "inputs": inputs, "provider_calls": 0, "application_requests": 0}, ingestion, records


def execute(output):
    if (sys.platform != "linux" or platform.machine() != "x86_64" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        raise ValueError("Use standard GitHub-hosted Linux x86_64")
    if output.exists() or not output.resolve().is_relative_to(ROOT / "runs/ci-agentops-governed-app-pilot-v2"):
        raise ValueError("Use an exclusive new pilot allocation")
    output.mkdir(parents=True)
    report = {"schema_version": "agentops-governed-app-hosted-pilot/2", "status": "failed", "started_at_utc": now(),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_sha": os.environ.get("GITHUB_SHA"),
              "profile": "github-hosted-ubuntu-24.04", "provider_calls": 0,
              "private_bank_qualification": False, "admission_algorithm_integration": False}
    try:
        inputs, ingestion, records = check_inputs()
        write_new(output / "inputs.json", inputs)
        for name in OWNED:
            target = output / "owned-source" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(regular_bytes(ROOT / name))
        memory = {line.split(":", 1)[0]: int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines() if len(line.split()) == 3}
        report["resource_sample"] = {key: memory.get(key) for key in ("MemAvailable", "SwapFree", "CommitLimit", "Committed_AS")}
        if memory.get("MemAvailable", 0) < 2 * 1024**3:
            raise ValueError("Hosted profile requires at least 2 GiB available physical RAM")
        root = Path("/var/tmp/agentops-governed-app-pilot-v2-" + uuid.uuid4().hex[:16])
        root.mkdir(mode=0o700)
        report["runtime_root"] = str(root)
        report["stage"] = "source-download"
        archive = output / "original-agentops.zip"
        fetch(ingestion["requested_download_url"], archive, SOURCE_SHA, 5_000_000)
        rows = extract_source(archive, root, ingestion)
        write_new(output / "original-source-manifest.json", {"files": rows})
        original = root / "external/agentops-c806b7f1"
        runtime = root / "runtime"
        runtime.mkdir()
        entries = tomllib.loads((original / "mise.lock").read_text())["tools"]["aqua:astral-sh/uv"]
        if len(entries) != 1 or entries[0]["version"] != "0.12.0":
            raise ValueError("Original UV version pin differs")
        pin = entries[0]["platforms.linux-x64"]
        url = "https://github.com/astral-sh/uv/releases/download/0.12.0/uv-x86_64-unknown-linux-gnu.tar.gz"
        if pin["url"] != url or not pin["checksum"].startswith("sha256:"):
            raise ValueError("Original UV archive pin differs")
        uv_archive = output / "uv-linux.tar.gz"
        fetch(url, uv_archive, pin["checksum"][7:], 50_000_000)
        uv = runtime / "uv"
        with tarfile.open(uv_archive, "r:gz") as stream:
            members = [m for m in stream.getmembers() if m.name == "uv-x86_64-unknown-linux-gnu/uv"]
            if len(members) != 1 or not members[0].isfile() or members[0].size > 100_000_000:
                raise ValueError("Pinned UV member differs")
            with uv.open("xb") as target:
                target.write(stream.extractfile(members[0]).read())
        uv.chmod(0o755)
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith(("PYTHON", "GOOGLE_", "OPENAI_", "GEMINI_", "AGENT_", "OTEL_"))}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PYTHONUTF8="1", OTEL_SDK_DISABLED="true",
                   UV_PROJECT_ENVIRONMENT=str(runtime / "venv"), UV_CACHE_DIR=str(runtime / "cache"),
                   UV_PYTHON_INSTALL_DIR=str(runtime / "python"), UV_PYTHON_BIN_DIR=str(runtime / "bin"),
                   UV_HTTP_TIMEOUT="30", UV_HTTP_RETRIES="0", UV_PYTHON_DOWNLOADS="automatic", UV_LINK_MODE="copy")
        report["stage"] = "locked-dependencies"
        capture([uv, "--version"], output, "uv-version", root, env, 15)
        if not (output / "uv-version.stdout.bin").read_text().strip().startswith("uv 0.12.0"):
            raise ValueError("Pinned UV executable differs")
        capture([uv, "sync", "--locked", "--project", original / "agents/python", "--python", PYTHON,
                 "--python-preference", "only-managed"], output, "locked-sync", root, env, 480)
        verified_source(root, rows)
        python = runtime / "venv/bin/python"
        capture([python, "-B", "-c", "import sys,importlib.metadata as m,json; print(json.dumps({'python':sys.version,'packages':{n:m.version(n) for n in ['google-adk','a2a-sdk','presidio-analyzer','spacy','agentops-agent']}}))"],
                output, "runtime-versions", root, env, 15)
        failures = []
        for task_id in IDS:
            report["stage"] = task_id
            case = output / task_id
            case.mkdir()
            write_new(case / "public-task.json", records[task_id])
            try:
                capture([python, "-B", ROOT / OWNED[0], "--case", case, "--original", original,
                         "--public-task", case / "public-task.json"], output, task_id, root, env, 150)
            except ValueError as error:
                failures.append({"case_id": task_id, "error": str(error)})
        verified_source(root, rows)
        report["original_sources_unchanged_after"] = True
        report["task_process_failures"] = failures
        report["stage"] = "separate-private-evaluator"
        capture([sys.executable, "-B", ROOT / OWNED[1], "--output", output, "--original", original],
                output, "private-evaluator", root, env, 60)
        report["evaluation"] = json.loads((output / "evaluation.json").read_bytes())
        report["status"] = "pilot_captured" if not failures else "partial_pilot_captured"
    except BaseException as error:
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        raise
    finally:
        report["finished_at_utc"] = now()
        write_new(output / "result.json", report)
        files = [{"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
                 for path in sorted(output.rglob("*")) if path.is_file() and not path.is_symlink()]
        write_new(output / "manifest.json", {"files": files})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_inputs:
        print(json.dumps(check_inputs()[0], indent=2))
    elif args.execute and args.output:
        execute(args.output.resolve())
    else:
        parser.error("Select --check-inputs or --execute --output")
