"""Two-stage owned AP2 bootstrap: validate before DPAPI, then before originals.

Never run this script without the prospective exact native contract. It imports
only stdlib/helper code before current gate/environment/usage checks pass. No
original server/application/model/credential operation has been run here.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import types


def _load_exact(reference):
    path = Path(reference["path"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Bootstrap implementation bytes changed")
    module = types.ModuleType("_ap2_bootstrap_" + path.stem)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def _powershell_literal(value):
    if not isinstance(value, str) or "\0" in value:
        raise ValueError("Invalid controlled launcher literal")
    return "'" + value.replace("'", "''") + "'"


def _exact_job_membership(handle):
    if sys.platform != "win32" or type(handle) is not int or handle <= 0:
        raise ValueError("Exact inherited task-owned Windows Job handle required")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.GetCurrentProcess.argtypes, api.GetCurrentProcess.restype = [], wintypes.HANDLE
    api.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    api.IsProcessInJob.restype = wintypes.BOOL
    member = wintypes.BOOL()
    if not api.IsProcessInJob(api.GetCurrentProcess(), wintypes.HANDLE(handle), ctypes.byref(member)) or not member.value:
        raise ValueError("Current process is not in the exact inherited task-owned Job")
    return {"inherited_job_handle": handle, "current_process_membership_verified": True}


def bootstrap(plan_path, role, stage, job_handle):
    # Initial JSON loading is stdlib-only; the exact helper is subsequently
    # hash-bound before executing its purely stdlib validation implementation.
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    expected_helper = Path(__file__).absolute().parents[1] / "src/interoperability/ap2_hp_native_gate_v1.py"
    if Path(plan["bootstrap_helper"]["path"]) != expected_helper:
        raise ValueError("Bootstrap cannot execute an arbitrary plan-selected helper before validation")
    helper = _load_exact(plan["bootstrap_helper"])
    plan = helper.strict_json(Path(plan_path).read_bytes())
    helper.reference(plan["bootstrap_script"])
    helper.need(Path(plan["bootstrap_script"]["path"]) == Path(__file__).absolute(), "Executed bootstrap script origin differs.")
    service = next((item for item in helper.SERVICES if item["role"] == role), None)
    helper.need(service is not None and stage in ("before-key", "original"), "Unknown original bootstrap role/stage.")
    output = helper.regular(plan["output_root"], directory=True)
    helper.need(Path(plan_path) == output / "plan.json", "Bootstrap must use its allocated immutable plan file.")
    root = helper.regular(output / "services" / role, directory=True)
    binding = helper.launch_binding(plan, role)
    validated = helper.validate_plan(plan, datetime.now(timezone.utc))
    runtime_module = _load_exact(plan["windows_runtime"])
    runtime = runtime_module.WindowsRuntime()
    gate = helper.strict_json((root / "prelaunch.json").read_bytes())
    check = helper.immediate_check(gate, binding, runtime.memory_sample(), runtime.now())
    membership = _exact_job_membership(job_handle)
    helper.need(str(Path(sys.executable)) == plan["interpreter"]["path"] and helper.sha(Path(sys.executable).read_bytes()) == plan["interpreter"]["sha256"], "Executed interpreter differs from the bound environment.")
    helper.need(sys.version_info >= (3, 11), "Original AP2 requires Python >=3.11.")
    for folder in (output / ".temp-db", output / ".logs"):
        helper.regular(folder, directory=True)
    if stage == "before-key":
        helper.publish(root / "bootstrap.before-key.json", {"status": "guarded_before_credential_helper", "pid": os.getpid(),
            "binding": binding, "resource_check": check, "membership": membership,
            "validated_inputs": validated, "key_accesses_before_this_gate": 0})
        # These supported configuration variables contain no API credential.
        os.environ["PAYMENT_METHOD"] = "CARD"
        os.environ["TEMP_DB_DIR"] = str(output / ".temp-db")
        os.environ["AGENT_PROVIDER_PUBLIC_KEY_PATH"] = str(output / ".temp-db/agent_provider_signing_key.pub")
        arguments = ["-I", "-S", "-B", plan["bootstrap_script"]["path"], "--stage", "original", "--plan", str(plan_path),
            "--role", role, "--job-handle", str(job_handle)]
        text = "$ErrorActionPreference = 'Stop'\n$ap2OriginalArguments = @(\n" + ",\n".join("  " + _powershell_literal(item) for item in arguments) + "\n)\n"
        text += ". " + _powershell_literal(plan["credential_helper"]["path"]) + " -Program " + _powershell_literal(plan["interpreter"]["path"]) + " -ProgramArguments $ap2OriginalArguments\nexit $LASTEXITCODE\n"
        launcher = root / "credential-launch.ps1"
        with launcher.open("xb") as stream:
            stream.write(text.encode("utf-8")); stream.flush(); os.fsync(stream.fileno())
        # Recheck immediate headroom immediately before the helper can decrypt.
        helper.immediate_check(gate, binding, runtime.memory_sample(), runtime.now())
        child = subprocess.run([plan["powershell"]["path"], "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(launcher)],
            cwd=output, check=False, creationflags=subprocess.CREATE_NO_WINDOW, close_fds=False)
        helper.publish(root / "bootstrap.credential-child-exit.json", {"binding": binding, "returncode": child.returncode})
        return child.returncode
    helper.need(os.environ.get("PAYMENT_METHOD") == "CARD" and os.environ.get("TEMP_DB_DIR") == str(output / ".temp-db")
        and os.environ.get("AGENT_PROVIDER_PUBLIC_KEY_PATH") == str(output / ".temp-db/agent_provider_signing_key.pub"), "Original shared configuration environment differs.")
    # The per-request provider guard executes only after source/env/usage/gate
    # checks. Its exact implementation and closed review are mandatory inputs.
    source = Path(plan["source_root"])
    sys.path[:0] = [str(source / "code/samples/python/src"), str(source / "code/sdk/python"), validated["site_packages"]]
    sys.dont_write_bytecode = True
    hook = _load_exact(plan["usage_hook"])
    acknowledgment = hook.install_guard(plan=deepcopy(plan), service=deepcopy(service), configuration_sha256=helper.configuration_hash(plan))
    helper.need(isinstance(acknowledgment, dict) and acknowledgment.get("status") == "installed"
        and acknowledgment.get("contract") == "enforce_before_every_provider_request"
        and acknowledgment.get("configuration_sha256") == helper.configuration_hash(plan), "Provider usage hook did not establish its bound enforcement contract.")
    check = helper.immediate_check(gate, binding, runtime.memory_sample(), runtime.now())
    helper.publish(root / "bootstrap.before-original.json", {"status": "guarded_before_original_import", "pid": os.getpid(),
        "binding": binding, "resource_check": check, "usage_hook": acknowledgment, "membership": membership,
        "original_module": service["module"], "interpreter_sha256": plan["interpreter"]["sha256"]})
    sys.argv = [service["module"]]
    runpy.run_module(service["module"], run_name="__main__", alter_sys=False)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--role", choices=("merchant", "credentials", "processor"), required=True)
    parser.add_argument("--stage", choices=("before-key", "original"), required=True)
    parser.add_argument("--job-handle", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        return bootstrap(args.plan, args.role, args.stage, args.job_handle)
    except BaseException as error:
        # Original exceptions may contain request/credential text; only class
        # identity is emitted by this wrapper. Existing original logs persist.
        print(json.dumps({"schema_version": "ap2-hp-bootstrap-refusal/1", "status": "refused_or_original_stage_failed",
                          "error_type": type(error).__name__, "role": args.role, "stage": args.stage}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
