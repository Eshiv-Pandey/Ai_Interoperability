"""Set up and execute one unchanged AgentOps control on Linux x86_64.

Requires a Linux bootstrap Python >=3.11. Downloads the checksum-pinned upstream
uv tool, installs CPython 3.13.1 and the unchanged dependency lock into this
workspace, then prepares and runs the separate native v6 attempt. No live model,
HTTP service, bridge, system installation or source modification is requested.
Existing setup or attempt directories are never reused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.request

import agentops_native_probe_v2 as evidence

ROOT = evidence.WORKSPACE
RUNTIME = ROOT / "external/runtime-agentops-linux-v7"
OUTPUT = ROOT / "runs/agentops-native-eligibility/dependencies-linux-v7"
NATIVE = ROOT / "runs/agentops-native-eligibility/native-probe-v6"
PYTHON_VERSION = "3.13.1"
CAPABILITY_CODE = "import fcntl,sys\nfrom pathlib import Path\np=Path(sys.argv[1]); p.mkdir(mode=0o700)\nwith (p/'lock').open('w+b') as first, (p/'lock').open('r+b') as second:\n fcntl.flock(first.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)\n try:\n  fcntl.flock(second.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)\n except BlockingIOError:\n  pass\n else:\n  raise AssertionError('Second independent open acquired an excluded lock')\n fcntl.flock(first.fileno(),fcntl.LOCK_UN)\n fcntl.flock(second.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)\n fcntl.flock(second.fileno(),fcntl.LOCK_UN)\nprint('Managed interpreter mode0700 and flock exclusion passed')\n"


def require_linux():
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("Run this in Linux x86_64 (for example WSL Ubuntu), not Windows Python")
    if platform.libc_ver()[0] != "glibc":
        raise ValueError("This version is restricted to glibc Linux")


def tool_pin():
    lock = tomllib.loads((evidence.SOURCE / "mise.lock").read_text(encoding="utf-8"))
    entries = lock["tools"]["aqua:astral-sh/uv"]
    if len(entries) != 1 or entries[0]["version"] != "0.12.0":
        raise ValueError("Unexpected upstream uv tool pin")
    pin = entries[0]["platforms.linux-x64"]
    expected_url = "https://github.com/astral-sh/uv/releases/download/0.12.0/uv-x86_64-unknown-linux-gnu.tar.gz"
    if pin["url"] != expected_url or not pin["checksum"].startswith("sha256:"):
        raise ValueError("Unexpected upstream Linux tool URL/checksum")
    return {"url": pin["url"], "sha256": pin["checksum"].removeprefix("sha256:")}


def unpack_uv(archive: Path, destination: Path, expected_sha: str):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("Downloaded uv archive checksum mismatch")
    with tarfile.open(archive, "r:gz") as stream:
        members = [member for member in stream.getmembers()
                   if member.name == "uv-x86_64-unknown-linux-gnu/uv"]
        if len(members) != 1 or not members[0].isfile() or members[0].size > 100_000_000:
            raise ValueError("Expected one regular uv executable in the pinned archive")
        # Extract only verified file bytes to an explicit destination; no archive paths.
        with stream.extractfile(members[0]) as source, destination.open("xb") as target:
            while block := source.read(1024 * 1024):
                target.write(block)
    destination.chmod(0o755)


def capture(argv, label, environment, timeout):
    started = evidence.now()
    timed_out = False
    returncode = None
    error = None
    with (OUTPUT / f"{label}.stdout.bin").open("xb") as stdout, (OUTPUT / f"{label}.stderr.bin").open("xb") as stderr:
        try:
            process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait(timeout=15)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    receipt = {"argv": argv, "started_at_utc": started, "finished_at_utc": evidence.now(),
               "returncode": returncode, "timed_out": timed_out, "error": error,
               "stdout": evidence.digest(OUTPUT / f"{label}.stdout.bin"),
               "stderr": evidence.digest(OUTPUT / f"{label}.stderr.bin")}
    evidence.write_json(OUTPUT / f"{label}.json", receipt)
    if returncode != 0 or error:
        raise ValueError(f"{label} failed; preserve its recorded output and do not retry")


def setup():
    require_linux()
    for path in (RUNTIME, OUTPUT, NATIVE):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Existing setup or native attempt must be preserved: {path}")
    sources = evidence.source_inventory()
    pin = tool_pin()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    state = {"schema_version": "agentops-linux-setup/7", "status": "failed",
             "started_at_utc": evidence.now(), "python_selection": PYTHON_VERSION,
             "source_files": sources, "tool_pin": pin, "tests": 0,
             "harness_files": [evidence.digest(Path(__file__).resolve()),
                 evidence.digest(ROOT / "scripts/inspect_agentops_runtime_v6.py")],
             "application_requests": 0, "live_model_calls": 0}
    evidence.write_json(OUTPUT / "pre-execution.json", state)
    try:
        RUNTIME.mkdir(parents=True, exist_ok=False)
        (OUTPUT / "temp").mkdir()
        environment = evidence.clean_environment(OUTPUT)
        environment.update({
            "UV_PROJECT_ENVIRONMENT": str(RUNTIME / "venv"),
            "UV_CACHE_DIR": str(RUNTIME / "cache"),
            "UV_PYTHON_INSTALL_DIR": str(RUNTIME / "python"),
            "UV_PYTHON_BIN_DIR": str(RUNTIME / "bin"),
            "UV_HTTP_TIMEOUT": "30", "UV_HTTP_RETRIES": "0",
            "UV_PYTHON_DOWNLOADS": "automatic", "UV_LINK_MODE": "copy",
        })
        state["stage"] = "download-uv"
        archive = RUNTIME / "uv-linux.tar.gz"
        deadline = time.monotonic() + 120
        with archive.open("xb") as target, urllib.request.urlopen(pin["url"], timeout=30) as response:
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > 50_000_000 or time.monotonic() > deadline:
                    raise ValueError("Tool download exceeded its size/time limit")
                target.write(block)
        uv = RUNTIME / "uv"
        unpack_uv(archive, uv, pin["sha256"])
        state["tool_archive"] = evidence.digest(archive)
        state["tool_executable"] = evidence.digest(uv)
        state["stage"] = "uv-version"
        capture([str(uv), "--version"], "uv-version", environment, 15)
        version = (OUTPUT / "uv-version.stdout.bin").read_text(encoding="utf-8").strip()
        if not (version == "uv 0.12.0" or version.startswith("uv 0.12.0 ")):
            raise ValueError("Unexpected downloaded uv version")
        state["stage"] = "locked-sync"
        print("Installing the unchanged lock in a separate Linux runtime; logs are retained.", flush=True)
        capture([str(uv), "sync", "--locked", "--project", str(evidence.PROJECT),
                 "--python", PYTHON_VERSION, "--python-preference", "only-managed"],
                "locked-sync", environment, 1800)
        state["stage"] = "runtime-inspection"
        capture([str(RUNTIME / "venv/bin/python"), "-I",
                 str(ROOT / "scripts/inspect_agentops_runtime_v6.py")],
                "installed-runtime", environment, 60)
        state["runtime_inventory"] = evidence.digest(OUTPUT / "installed-runtime.stdout.bin")
        state["stage"] = "managed-capability"
        capture([str(RUNTIME / "venv/bin/python"), "-I", "-c", CAPABILITY_CODE,
                 str(OUTPUT / "managed-capability")], "managed-capability", environment, 30)
        state["managed_capability_passed"] = True
        state["status"] = "dependencies_ready"
        state["stage"] = "complete"
    except Exception as exc:
        state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            state["source_unchanged_after"] = evidence.source_inventory() == sources
        except Exception as exc:
            state["source_unchanged_after"] = False
            state["source_error"] = f"{type(exc).__name__}: {exc}"
        if not state["source_unchanged_after"]:
            state["status"] = "failed_source_integrity"
        state["finished_at_utc"] = evidence.now()
        state["files"] = [evidence.digest(path) for path in sorted(OUTPUT.iterdir()) if path.is_file()]
        evidence.write_json(OUTPUT / "result.json", state)
    print(json.dumps({"status": state["status"], "stage": state.get("stage"),
                      "error": state.get("error"), "result": str(OUTPUT / "result.json")}))
    if state["status"] != "dependencies_ready":
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true")
    args = parser.parse_args()
    setup()
    if not args.setup_only:
        import agentops_native_probe_v6 as native
        native.prepare(NATIVE)
        native.run(NATIVE)


if __name__ == "__main__":
    main()
