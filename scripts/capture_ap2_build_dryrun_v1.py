"""One binary-only dry run of AP2's separate declared build backends."""
from __future__ import annotations

from datetime import datetime, timezone
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
OUTPUT = ROOT / "runs/ap2-dependency-resolution/build-backend-dry-run-v1"
EXPECTED = {
    "result.json": "c18051856084954d1d08b24701d7ab2fc981ed9f9a44441e7fef84c8890ab12d",
    "source-descriptors.json": "3d871894e37fa591ed78c51970bb30d22a71f86d2fe66eecd12b5b5a3f121e3b",
    "separate-build-requirements.txt": "dcf3b9ee279fa4fa7b1dfdcb1204e924479e6f226e73d5d5097940ed68bf2b2f",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def publish(name, data):
    with (OUTPUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.write("\n")


def main():
    if not (sys.platform == "win32" and platform.machine() == "AMD64"
            and struct.calcsize("P") == 8 and sys.version_info[:2] == (3, 13)
            and Path(sys.executable).resolve() == Path(r"C:\Python313\python.exe").resolve()):
        raise RuntimeError("Requires bound Windows AMD64 CPython3.13")
    payloads = {name: (INPUT / name).read_bytes() for name in EXPECTED}
    if any(sha(payloads[name]) != expected for name, expected in EXPECTED.items()):
        raise RuntimeError("Prepared source-derived build inputs changed")
    descriptor = json.loads(payloads["source-descriptors.json"])
    rows = descriptor["separate_build_requirement_rows"]
    if [row["original_requirement"] for row in rows] != ["setuptools>=61.0", "setuptools>=61.0", "hatchling"]:
        raise RuntimeError("Declared backend rows differ")
    OUTPUT.mkdir(parents=False, exist_ok=False)
    snapshots = OUTPUT / "input-snapshots"
    snapshots.mkdir()
    for name, data in payloads.items():
        (snapshots / name).write_bytes(data)
    driver = Path(__file__).read_bytes()
    (OUTPUT / "capture-driver.py").write_bytes(driver)
    argv = [sys.executable, "-I", "-m", "pip", "--isolated", "install", "--dry-run", "--ignore-installed",
            "--only-binary=:all:", "--index-url", "https://pypi.org/simple", "--platform", "win_amd64",
            "--implementation", "cp", "--python-version", "3.13", "--abi", "cp313",
            "--report", str(OUTPUT / "pip-report.json"), "-r", str(snapshots / "separate-build-requirements.txt"),
            "--disable-pip-version-check", "--no-cache-dir", "--no-input"]
    child_env = dict(os.environ)
    child_env["PIP_CONFIG_FILE"] = os.devnull
    publish("plan.json", {"schema_version": "ap2-build-backend-dry-run-plan/1", "created_at_utc": utc(),
            "argv": argv, "cwd": str(OUTPUT), "inputs": EXPECTED, "driver_sha256": sha(driver),
            "environment_constraints": {"PIP_CONFIG_FILE": os.devnull}, "timeout_seconds": 180,
            "scope": "Resolve declared build backends only; dynamically requested build dependencies remain unverified."})
    start, started = time.monotonic(), utc()
    code, failure, timeout = None, None, False
    with (OUTPUT / "pip.stdout.bin").open("xb") as stdout, (OUTPUT / "pip.stderr.bin").open("xb") as stderr:
        try:
            child = subprocess.Popen(argv, cwd=OUTPUT, env=child_env, stdout=stdout, stderr=stderr)
            try:
                code = child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                timeout = True
                child.kill()
                code = child.wait()
        except OSError as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
    unchanged = {name: sha((INPUT / name).read_bytes()) == expected for name, expected in EXPECTED.items()}
    report_path = OUTPUT / "pip-report.json"
    valid, count, report_error = False, None, None
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_bytes())
            valid = report.get("version") == "1" and isinstance(report.get("install"), list)
            count = len(report["install"]) if valid else None
        except (ValueError, TypeError) as exc:
            report_error = {"type": type(exc).__name__, "message": str(exc)}
    success = code == 0 and valid and all(unchanged.values()) and failure is None and not timeout
    artifacts = [{"file": path.relative_to(OUTPUT).as_posix(), "bytes": path.stat().st_size,
                  "sha256": sha(path.read_bytes())} for path in sorted(OUTPUT.rglob("*")) if path.is_file()]
    result = {"schema_version": "ap2-build-backend-dry-run-result/1", "started_at_utc": started,
              "finished_at_utc": utc(), "elapsed_seconds": time.monotonic() - start,
              "status": "declared_build_backend_report_captured" if success else "resolution_not_established",
              "exit_code": code, "timed_out": timeout, "launch_failure": failure,
              "report_present": report_path.is_file(), "report_schema_valid": valid,
              "report_error": report_error, "selected_distributions": count,
              "inputs_unchanged": unchanged, "artifacts": artifacts,
              "environment_installed": False, "source_built": False,
              "original_application_imported": False, "native_application_executed": False, "model_requests": 0,
              "complete_build_closure_established": False,
              "claim_limit": "Declared backend resolution only; backend hooks and three local source builds remain unexecuted."}
    publish("result.json", result)
    print(json.dumps({key: result[key] for key in ("status", "exit_code", "selected_distributions", "inputs_unchanged")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
