"""Capture one source-bound, binary-only AP2 indexed dependency dry run.

No installation, source build, original application import or model call.
Every allocated output is consumed, including failed resolution attempts.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "runs/ap2-dependency-resolution/input-v1"
OUTPUT = ROOT / "runs/ap2-dependency-resolution/windows-cp313-dry-run-v1"
EXPECTED = {
    "result.json": "c18051856084954d1d08b24701d7ab2fc981ed9f9a44441e7fef84c8890ab12d",
    "source-descriptors.json": "3d871894e37fa591ed78c51970bb30d22a71f86d2fe66eecd12b5b5a3f121e3b",
    "indexed-runtime-requirements.txt": "46b609b3a68bf63c67987107936846992362e559b9db310256ae33ee15cacf50",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    if not (sys.platform == "win32" and platform.machine() == "AMD64"
            and struct.calcsize("P") == 8 and sys.version_info[:2] == (3, 13)):
        raise RuntimeError("Requires native Windows AMD64 CPython 3.13")
    payloads = {name: (INPUT / name).read_bytes() for name in EXPECTED}
    for name, expected in EXPECTED.items():
        if digest(payloads[name]) != expected:
            raise RuntimeError(f"Source-bound input changed: {name}")
    descriptor = json.loads(payloads["source-descriptors.json"])
    prepared = descriptor["prospective_indexed_dry_run_argv"]
    required = [
        r"C:\Python313\python.exe", "-I", "-m", "pip", "--isolated", "install",
        "--dry-run", "--ignore-installed", "--only-binary=:all:",
        "--index-url", "https://pypi.org/simple", "--platform", "win_amd64",
        "--implementation", "cp", "--python-version", "3.13", "--abi", "cp313",
        "--report", str(OUTPUT / "pip-report.json"),
        "-r", str(INPUT / "indexed-runtime-requirements.txt"),
    ]
    if prepared != required or Path(sys.executable).resolve() != Path(required[0]).resolve():
        raise RuntimeError("Prepared command/interpreter binding differs")
    OUTPUT.mkdir(parents=False, exist_ok=False)
    snapshots = OUTPUT / "input-snapshots"
    snapshots.mkdir()
    for name, data in payloads.items():
        (snapshots / name).write_bytes(data)
    driver_bytes = Path(__file__).read_bytes()
    (OUTPUT / "capture-driver.py").write_bytes(driver_bytes)
    argv = required.copy()
    argv[-1] = str(snapshots / "indexed-runtime-requirements.txt")
    argv.extend(["--disable-pip-version-check", "--no-cache-dir", "--no-input"])
    child_env = dict(os.environ)
    child_env["PIP_CONFIG_FILE"] = os.devnull
    plan = {
        "schema_version": "ap2-indexed-dry-run-capture-plan/1",
        "created_at_utc": now(), "prepared_argv": prepared, "actual_argv": argv,
        "cwd": str(OUTPUT), "timeout_seconds": 300,
        "driver_sha256": digest(driver_bytes), "inputs": EXPECTED,
        "environment_constraints": {"PIP_CONFIG_FILE": os.devnull},
        "command_additions_reason": "Use exact input snapshot; suppress all pip config files, version probe, cache writes and interactive input.",
        "scope": "Indexed binary dependency resolution only; no install/build/original import/model execution.",
    }
    write_json(OUTPUT / "plan.json", plan)
    start = time.monotonic()
    started_at = now()
    exit_code = None
    failure = None
    timed_out = False
    with (OUTPUT / "pip.stdout.bin").open("xb") as stdout, (OUTPUT / "pip.stderr.bin").open("xb") as stderr:
        try:
            process = subprocess.Popen(argv, cwd=OUTPUT, env=child_env, stdout=stdout, stderr=stderr)
            try:
                exit_code = process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                exit_code = process.wait()
        except OSError as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
    unchanged = {name: digest((INPUT / name).read_bytes()) == expected for name, expected in EXPECTED.items()}
    artifacts = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            artifacts.append({"file": path.relative_to(OUTPUT).as_posix(), "bytes": len(data), "sha256": digest(data)})
    report_path = OUTPUT / "pip-report.json"
    report_ok = False
    selected_count = None
    report_error = None
    if report_path.exists():
        try:
            report = json.loads(report_path.read_bytes())
            selected_count = len(report["install"])
            report_ok = report.get("version") == "1" and isinstance(report["install"], list)
        except (ValueError, KeyError, TypeError) as exc:
            report_error = {"type": type(exc).__name__, "message": str(exc)}
    success = exit_code == 0 and report_ok and all(unchanged.values()) and not timed_out and failure is None
    result = {
        "schema_version": "ap2-indexed-dry-run-capture-result/1",
        "started_at_utc": started_at, "finished_at_utc": now(),
        "elapsed_seconds": time.monotonic() - start,
        "status": "indexed_resolution_report_captured" if success else "resolution_not_established",
        "exit_code": exit_code, "timed_out": timed_out, "launch_failure": failure,
        "report_present": report_path.exists(), "report_schema_valid": report_ok,
        "report_error": report_error, "selected_indexed_distributions": selected_count,
        "inputs_unchanged": unchanged, "artifacts": artifacts,
        "environment_installed": False, "source_built": False,
        "original_application_imported": False, "native_application_executed": False,
        "model_requests": 0, "complete_environment_established": False,
        "claim_limit": "A pip indexed report is not a complete lock or compatibility result for the three source-bound local packages.",
    }
    write_json(OUTPUT / "result.json", result)
    print(json.dumps({key: result[key] for key in ("status", "exit_code", "timed_out", "report_present", "selected_indexed_distributions", "inputs_unchanged")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
