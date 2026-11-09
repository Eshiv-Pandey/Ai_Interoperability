"""Capture one focused restart-effect software validation from frozen copies."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


SOURCES = (
    "src/interoperability/__init__.py",
    "src/interoperability/agentops_raw_events_v1.py",
    "src/interoperability/agentops_restart_effects_v1.py",
    "tests/test_agentops_restart_effects_v1.py",
    "scripts/capture_restart_effect_example_v1.py",
    "tests/test_restart_effect_capture_v1.py",
)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    originals = {name: (root / name).read_bytes() for name in SOURCES}
    captured_root = output / "workspace"
    for name, raw in originals.items():
        target = captured_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test*restart_effect*.py", "-v"]
    write_json(output / "plan.json", {
        "schema_version": "agentops-restart-effect-software-plan/1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command, "cwd": str(captured_root),
        "source_files": {name: digest(raw) for name, raw in originals.items()},
        "application_requests": 0, "model_calls": 0,
        "scope": "Temporary logical snapshots; historical archives are not executed or exported by this validation.",
    })
    start = time.perf_counter_ns()
    try:
        process = subprocess.run(command, cwd=captured_root, capture_output=True, timeout=120)
        stdout, stderr, exit_code = process.stdout, process.stderr, process.returncode
        error = None
    except subprocess.TimeoutExpired as exception:
        stdout, stderr, exit_code = exception.stdout or b"", exception.stderr or b"", None
        error = "Focused validation exceeded 120 seconds"
    elapsed = time.perf_counter_ns() - start
    (output / "stdout.txt").write_bytes(stdout)
    (output / "stderr.txt").write_bytes(stderr)
    lines = stderr.decode("utf-8", errors="replace").splitlines()
    counts = [int(match[1]) for line in lines if (match := re.fullmatch(r"Ran (\d+) tests? in .+", line))]
    successful_summary = "OK" in lines
    unchanged = all((root / name).read_bytes() == raw and (captured_root / name).read_bytes() == raw
                    for name, raw in originals.items())
    status = "passed" if exit_code == 0 and successful_summary and len(counts) == 1 and counts[0] > 0 and unchanged else "failed"
    result = {
        "schema_version": "agentops-restart-effect-software/1", "status": status,
        "exit_code": exit_code, "tests_run": counts[0] if len(counts) == 1 else None,
        "skips": sum("... skipped " in line for line in lines), "elapsed_ns": elapsed,
        "original_and_captured_source_unchanged": unchanged,
        "source_files": {name: digest(raw) for name, raw in originals.items()},
        "application_requests": 0, "model_calls": 0, "original_archives_exported": 0,
        "stdout": digest(stdout), "stderr": digest(stderr), "error": error,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output / "result.json", result)
    print(json.dumps(result))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
