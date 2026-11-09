"""Inspect the already installed Linux runtime; never install or rerun old setup."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import agentops_native_probe_v2 as evidence

ROOT = evidence.WORKSPACE
PRIOR = ROOT / "runs/agentops-native-eligibility/dependencies-linux-v4"
OUTPUT = ROOT / "runs/agentops-native-eligibility/runtime-revalidation-v5"
PYTHON = ROOT / "external/runtime-agentops-linux-v4/venv/bin/python"
INSPECTOR = ROOT / "scripts/inspect_agentops_runtime_v5.py"


def main():
    if sys.platform != "linux":
        raise ValueError("Revalidation must use the existing Linux workspace")
    prior = evidence.load_json(PRIOR / "result.json")
    if (prior.get("status") != "failed" or prior.get("stage") != "runtime-inspection"
            or prior.get("source_unchanged_after") is not True):
        raise ValueError("Expected the retained inspector failure after locked installation")
    for row in prior["files"]:
        if evidence.digest(ROOT / row["path"]) != row:
            raise ValueError("Original installer receipts changed")
    sync = evidence.load_json(PRIOR / "locked-sync.json")
    if type(sync.get("returncode")) is not int or sync["returncode"] != 0 or sync.get("timed_out") is not False:
        raise ValueError("The existing locked installation did not succeed")
    expected = [str(ROOT / "external/runtime-agentops-linux-v4/uv"), "sync", "--locked", "--project",
                str(evidence.PROJECT), "--python", "3.13.1", "--python-preference", "only-managed"]
    if sync["argv"] != expected:
        raise ValueError("Unexpected original installation command")
    source = evidence.source_inventory()
    if source != prior["source_files"]:
        raise ValueError("Original installed application source changed")
    files = [evidence.digest(path) for path in (Path(__file__).resolve(), INSPECTOR,
             ROOT / "docs/research/source-evidence/agentops-runtime-resume-v6/protocol.md")]
    OUTPUT.mkdir(parents=True, exist_ok=False)
    (OUTPUT / "temp").mkdir()
    state = {"schema_version": "agentops-runtime-revalidation/5", "status": "failed",
             "started_at_utc": evidence.now(), "source_files": source, "harness_files": files,
             "original_setup_result": evidence.digest(PRIOR / "result.json"),
             "locked_sync_receipt": evidence.digest(PRIOR / "locked-sync.json"),
             "installations": 0, "application_requests": 0, "live_model_calls": 0}
    evidence.write_json(OUTPUT / "plan.json", state)
    try:
        environment = evidence.clean_environment(OUTPUT)
        inspected = evidence.capture([str(PYTHON), "-I", str(INSPECTOR)], output=OUTPUT,
                                     label="runtime-inspection", cwd=ROOT, environment=environment, timeout=60)
        if inspected["returncode"] != 0:
            raise ValueError("Corrected runtime inspection failed; inspect new retained streams")
        state["runtime_inventory"] = evidence.digest(OUTPUT / "runtime-inspection.stdout.bin")
        inventory = evidence.load_json(OUTPUT / "runtime-inspection.stdout.bin")
        if inventory.get("schema_version") != "agentops-installed-runtime-inspection/5" or inventory.get("status") != "installed_versions_match_lock":
            raise ValueError("Unexpected corrected runtime inspection")
        # Exercise the installed interpreter's fcntl, not the bootstrap Python.
        # Two separate open descriptions must exclude one another until unlock.
        code = """import fcntl,sys
from pathlib import Path
p=Path(sys.argv[1]); p.mkdir(mode=0o700)
with (p/'lock').open('w+b') as first, (p/'lock').open('r+b') as second:
 fcntl.flock(first.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  fcntl.flock(second.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  pass
 else:
  raise AssertionError('Second independent open acquired an excluded lock')
 fcntl.flock(first.fileno(),fcntl.LOCK_UN)
 fcntl.flock(second.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 fcntl.flock(second.fileno(),fcntl.LOCK_UN)
print('Managed interpreter mode0700 and flock exclusion passed')
"""
        capability = evidence.capture([str(PYTHON), "-I", "-c", code, str(OUTPUT / "managed-capability")],
                                      output=OUTPUT, label="managed-capability", cwd=ROOT,
                                      environment=environment, timeout=30)
        if capability["returncode"] != 0:
            raise ValueError("Managed interpreter filesystem/flock control failed")
        state["status"] = "installed_runtime_revalidated"
        state["native_module_kind"] = inventory["fcntl_native"]["kind"]
        state["package_count"] = len(inventory["packages"])
        state["managed_capability_passed"] = True
    except Exception as error:
        state["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            state["source_unchanged_after"] = evidence.source_inventory() == source
        except Exception as error:
            state["source_unchanged_after"] = False
            state["source_error"] = f"{type(error).__name__}: {error}"
        if not state["source_unchanged_after"]:
            state["status"] = "failed_source_integrity"
        state["finished_at_utc"] = evidence.now()
        state["files"] = [evidence.digest(path) for path in sorted(OUTPUT.iterdir()) if path.is_file()]
        evidence.write_json(OUTPUT / "result.json", state)
    print(json.dumps({key: value for key, value in state.items() if key not in {"files", "source_files", "harness_files"}}, indent=2))
    if state["status"] != "installed_runtime_revalidated":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
