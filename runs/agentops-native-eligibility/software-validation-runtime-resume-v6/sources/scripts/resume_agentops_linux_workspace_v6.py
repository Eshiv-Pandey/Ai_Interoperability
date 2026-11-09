"""Resume the installed v5 Linux runtime with a corrected, versioned inspector.

No downloads or installations. Preserve the old failed receipts and scripts;
append new versioned files and fresh native/HTTP attempts in the existing replica.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import agentops_native_probe_v2 as evidence
import run_agentops_linux_workspace_v5 as previous
from export_agentops_workspace_v6 import export_evidence

ROOT = evidence.WORKSPACE
PRIOR = ROOT / "runs/agentops-native-eligibility/linux-filesystem-v5"
OUTPUT = ROOT / "runs/agentops-native-eligibility/linux-runtime-resume-v6"
ADDITIONS = [
    "scripts/inspect_agentops_runtime_v5.py", "scripts/revalidate_agentops_runtime_v5.py",
    "scripts/agentops_native_probe_v5.py", "scripts/agentops_http_control_v3.py",
    "scripts/export_agentops_workspace_v6.py", "scripts/resume_agentops_linux_workspace_v6.py",
    "scripts/run_agentops_wsl_v6.ps1", "tests/test_agentops_http_control_v3.py",
    "docs/research/source-evidence/agentops-native-probe-v5/protocol.md",
    "docs/research/source-evidence/agentops-http-control-v3/protocol.md",
    "docs/research/source-evidence/agentops-runtime-resume-v6/protocol.md",
]


def capture(replica, label, arguments, timeout):
    environment = evidence.clean_environment(OUTPUT)
    environment["PYTHONPATH"] = str(replica / "scripts")
    for name in ("TEMP", "TMP", "TMPDIR"):
        environment[name] = str(replica / "resume-temp-v6")
    argv = [sys.executable, "-B", "-X", "utf8", *arguments]
    receipt = {"argv": argv, "cwd": str(replica), "started_at_utc": evidence.now(), "timed_out": False}
    process = None
    try:
        with (OUTPUT / f"{label}.stdout.bin").open("xb") as stdout, (OUTPUT / f"{label}.stderr.bin").open("xb") as stderr:
            process = subprocess.Popen(argv, cwd=replica, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            receipt["linux_pid"] = process.pid
            evidence.write_json(OUTPUT / f"{label}.started.json", receipt)
            try:
                receipt["returncode"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                receipt["timed_out"] = True
                os.killpg(process.pid, signal.SIGKILL)
                receipt["returncode"] = process.wait(timeout=15)
    except BaseException:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=15)
        raise
    finally:
        receipt["finished_at_utc"] = evidence.now()
        receipt["streams"] = [previous.record(OUTPUT / f"{label}.{suffix}.bin", OUTPUT)
                              for suffix in ("stdout", "stderr") if (OUTPUT / f"{label}.{suffix}.bin").is_file()]
        evidence.write_json(OUTPUT / f"{label}.json", receipt)
    if receipt.get("returncode") != 0:
        raise ValueError(f"{label} failed; see its retained stdout/stderr")


def main():
    if sys.platform != "linux":
        raise ValueError("Use the explicit Ubuntu launcher")
    prior_result = evidence.load_json(PRIOR / "result.json")
    old_export = evidence.load_json(PRIOR / "export-manifest.json")
    old_execution = evidence.load_json(PRIOR / "execution.json")
    if (prior_result.get("status") != "failed" or prior_result.get("native_result") != "not_run"
            or prior_result.get("http_result") != "not_run" or prior_result.get("parent_inputs_unchanged") is not True
            or prior_result.get("export_reference_failures") != []):
        raise ValueError("Expected the retained v5 failure before any native/HTTP attempt")
    replica = Path(prior_result["linux_workspace"])
    if (not replica.is_absolute() or replica.is_symlink() or not replica.is_dir()
            or not replica.name.startswith("agentops-research-v5-")
            or str(replica) != old_export["original_linux_root"]):
        raise ValueError("The recorded Linux workspace is missing or inconsistent; no reinstall attempted")
    previous.require_native_filesystem(replica)
    for row in old_export["files"]:
        for base in (PRIOR / "workspace", replica):
            if previous.record(previous.relative_file(base, row["path"]), base) != row:
                raise ValueError(f"Prior export or live Linux bytes changed: {row['path']}")
    old_inputs = old_execution["inputs"]
    for row in old_inputs:
        if previous.record(previous.relative_file(ROOT, row["path"]), ROOT) != row:
            raise ValueError("Original parent-side input changed")
    for name in ("runs/agentops-native-eligibility/native-probe-v4",
                 "runs/agentops-native-eligibility/native-probe-v5",
                 "runs/agentops-native-eligibility/runtime-revalidation-v5",
                 "runs/agentops-http-control/native-http-linux-v2",
                 "runs/agentops-http-control/native-http-linux-v3", "resume-temp-v6"):
        if (replica / name).exists():
            raise FileExistsError(f"Unexpected existing attempt/path: {name}")
    additions = [previous.record(previous.relative_file(ROOT, name), ROOT) for name in ADDITIONS]
    for row in additions:
        if previous.relative_file(replica, row["path"]).exists():
            raise FileExistsError(f"Versioned addition already exists: {row['path']}")
    inputs = sorted(old_inputs + additions, key=lambda row: row["path"])
    if len({row["path"] for row in inputs}) != len(inputs):
        raise ValueError("A new input would replace an original input")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    state = {"schema_version": "agentops-linux-runtime-resume/6", "status": "failed",
             "started_at_utc": evidence.now(), "linux_workspace": str(replica),
             "prior_attempt": evidence.digest(PRIOR / "result.json"),
             "native_result": "not_run", "http_result": "not_run", "installations": 0,
             "live_model_calls": 0, "qualified_second_domain": False, "research_gate_credit_added": 0}
    evidence.write_json(OUTPUT / "execution.json", {**state, "inputs": inputs,
                        "prior_export": evidence.digest(PRIOR / "export-manifest.json")})
    evidence.write_json(OUTPUT / "linux-workspace.json", {"path": str(replica)})
    try:
        previous.copy_exact(ROOT, replica, additions)
        (replica / "resume-temp-v6").mkdir()
        print(f"Resuming installed runtime in {replica}; no dependency installation.", flush=True)
        print(f"Logs and results: {OUTPUT}", flush=True)
        state["stage"] = "runtime-revalidation"
        capture(replica, "runtime-revalidation", ["scripts/revalidate_agentops_runtime_v5.py"], 180)
        state["stage"] = "native-prepare"
        capture(replica, "native-prepare", ["scripts/agentops_native_probe_v5.py", "prepare"], 180)
        state["stage"] = "native-control"
        capture(replica, "native-control", ["scripts/agentops_native_probe_v5.py", "run"], 480)
        state["native_result"] = evidence.load_json(replica / "runs/agentops-native-eligibility/native-probe-v5/result.json")["status"]
        if state["native_result"] != "upstream_and_boundary_effect_check_passed":
            raise ValueError("Native/effect control did not pass")
        state["stage"] = "http-prepare"
        capture(replica, "http-prepare", ["scripts/agentops_http_control_v3.py", "prepare"], 120)
        state["stage"] = "http-control"
        capture(replica, "http-control", ["scripts/agentops_http_control_v3.py", "run"], 600)
        state["http_result"] = evidence.load_json(replica / "runs/agentops-http-control/native-http-linux-v3/result.json")["status"]
        if state["http_result"] != "wire_and_effect_check_passed":
            raise ValueError("HTTP control did not pass")
        state["status"] = "native_and_http_controls_passed"
    except (Exception, KeyboardInterrupt) as error:
        state["error"] = f"{type(error).__name__}: {error}"
    finally:
        for key, name in (("native_result", "runs/agentops-native-eligibility/native-probe-v5/result.json"),
                          ("http_result", "runs/agentops-http-control/native-http-linux-v3/result.json")):
            if (replica / name).is_file():
                try:
                    state[key] = evidence.load_json(replica / name)["status"]
                except Exception as error:
                    state.setdefault("receipt_errors", []).append(f"{name}: {type(error).__name__}: {error}")
                    state["status"] = "failed_incomplete_receipt"
        try:
            exported = export_evidence(replica, OUTPUT / "workspace", inputs)
            evidence.write_json(OUTPUT / "export-manifest.json", exported)
            state["exported_files"] = len(exported["files"])
            state["export_reference_failures"] = exported["reference_failures"]
            if exported["reference_failures"]:
                state["status"] = "failed_evidence_export"
        except Exception as error:
            state["status"] = "failed_evidence_export"
            state["export_error"] = f"{type(error).__name__}: {error}"
        try:
            state["parent_inputs_unchanged"] = all(previous.record(ROOT / row["path"], ROOT) == row for row in inputs)
        except Exception as error:
            state["parent_inputs_unchanged"] = False
            state["parent_input_error"] = f"{type(error).__name__}: {error}"
        if not state["parent_inputs_unchanged"]:
            state["status"] = "failed_parent_integrity"
        state["finished_at_utc"] = evidence.now()
        evidence.write_json(OUTPUT / "result.json", state)
    print(json.dumps(state, indent=2), flush=True)
    if state["status"] != "native_and_http_controls_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
