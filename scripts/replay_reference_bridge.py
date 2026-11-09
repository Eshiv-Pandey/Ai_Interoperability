"""Replay an exact reference-bridge archive in an isolated clean interpreter."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


WORKER = r'''
import json, runpy, sys, unittest
from pathlib import Path
archive = Path(sys.argv[1]).resolve()
saved = json.loads(Path(sys.argv[2]).read_bytes().decode("utf-8"))
sys.path.insert(0, str(archive / "src"))
scope = runpy.run_path(str(archive / "scripts/verify_reference_bridge.py"))
from interoperability import status_projection, status_projection_checker, baseline, oracle
module_paths = {module.__name__: str(Path(module.__file__).resolve()) for module in
                (status_projection, status_projection_checker, baseline, oracle)}
if not all(Path(value).is_relative_to(archive / "src") for value in module_paths.values()):
    raise SystemExit("Non-archived implementation import")
checks = [scope["check_run"](archive, row["input"]) for row in saved["checks"]]
exact = checks == saved["checks"]
suite = unittest.defaultTestLoader.discover(str(archive / "tests"))
tests = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
valid = exact and all(row["valid"] for row in checks) and tests.wasSuccessful()
print(json.dumps({"python": sys.version, "module_paths": module_paths,
                  "run_count": len(checks), "exact_checks_match": exact,
                  "tests_run": tests.testsRun, "failures": len(tests.failures),
                  "errors": len(tests.errors), "skips": len(tests.skipped), "valid": valid}))
raise SystemExit(0 if valid else 1)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verification, output = args.verification.resolve(), args.output.resolve()
    saved = json.loads(verification.read_bytes().decode("utf-8"))
    if saved.get("schema_version") != "reference-bridge-verification/1" or saved.get("valid") is not True:
        raise SystemExit("Requires successful reference-bridge verification")
    archive = Path(saved["archive"]).resolve()
    driver = output.with_suffix(".driver.py")
    if output.exists() or driver.exists() or output.is_relative_to(archive):
        raise SystemExit("Replay output and driver must be new paths outside archive")
    before = inventory(archive)
    matches = bool(before) and before == saved["archive_sha256"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with driver.open("xb") as handle:
        handle.write(Path(__file__).read_bytes())
    command = [str(args.python.resolve()), "-I", "-B", "-c", WORKER, str(archive), str(verification)]
    worker = subprocess.run(command, cwd=archive, capture_output=True, text=True, encoding="utf-8", timeout=300)
    try:
        result = json.loads(worker.stdout)
    except json.JSONDecodeError:
        result = {"valid": False, "unparsed_stdout": worker.stdout}
    after = inventory(archive)
    valid = matches and before == after and worker.returncode == 0 and result.get("valid") is True
    report = {"schema_version": "reference-bridge-archive-replay/1", "recorded_at": datetime.now(timezone.utc).isoformat(),
              "claim_limit": "Exact archived software/source/data replay only; no native service rerun, model experiment, method advantage, novelty or human review",
              "verification": str(verification), "verification_sha256": sha256(verification),
              "archive": str(archive), "archive_file_count": len(before), "archive_matches_verification": matches,
              "archive_unchanged": before == after, "driver_snapshot": str(driver), "driver_sha256": sha256(driver),
              "worker_command": [command[0], "-I", "-B", "-c", "WORKER in hashed driver", str(archive), str(verification)],
              "worker_exit_code": worker.returncode, "worker_result": result, "test_and_error_output": worker.stderr,
              "valid": valid}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "archive_unchanged": before == after,
                      "tests_run": result.get("tests_run"), "output": str(output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
