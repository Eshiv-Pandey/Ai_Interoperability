"""One fresh source-bound capture of authored original-Server owner tests only."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OWN = "scripts/capture_ap2_hp_server_owner_tests_v1.py"
TEST = "tests/test_ap2_hp_original_server_owner_v1.py"
PINS = {
    "src/interoperability/ap2_hp_original_server_owner_v1.py": "4dc3dde0e602ce7e863c291bf58e1dfb4c2a1b8b6430dec8c7a6beae4cb9ca26",
    "src/interoperability/ap2_hp_original_binding_v1.py": "27c37938751dfb00f21a3a53043ea2f468814d264df71bb8024dd58cea5ac3af",
    "src/interoperability/ap2_hp_final_asgi_binding_v1.py": "51623f3333c0479a708d05b10b1bac46117cee2c2cde8a8b75d033659445c1d3",
    "src/interoperability/ap2_hp_reference_execution_v1.py": "821b463c1e8d8500b32774b7c04ace2b865c7089c7a8e0ca1f5e7f20ab5df340",
    "src/interoperability/ap2_hp_passive_capture_v1.py": "e3abb063246ee0688b098bba933a74c3c2e6c5789b7c9b39bc59cc12b135a5a8",
    TEST: "202896abdcac87acfe5a62b9ad8e60bd46e9d7326941eb4c6d2f8a8284038906",
}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def regular(path, directory=False):
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Linked/reparse capture path refused")
    need(path.is_dir() if directory else path.is_file(), "Regular capture path required")
    return path


def identity(path):
    regular(path)
    need(path.stat().st_size <= 32 * 1024 * 1024, "Capture file exceeds bound")
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(root):
    regular(root, True)
    result = {}
    for path in sorted(root.rglob("*")):
        regular(path, path.is_dir())
        if path.is_file():
            need(len(result) < 8192, "Capture file inventory exceeds bound")
            result[path.relative_to(root).as_posix()] = identity(path)
    return result


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


PROGRAM = r'''
from pathlib import Path
import json,os,runpy,sys,unittest
root=Path(sys.argv[1])
outcome=Path(sys.argv[2])
def guard(event,args):
    if event.startswith("socket.") or event in ("subprocess.Popen","os.system","ctypes.dlopen"):
        raise RuntimeError("Constructed Server-owner capture denies network/process/native-library operations")
sys.addaudithook(guard)
class RetainedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.outcomes=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.outcomes.append({"id":test.id(),"status":"passed"})
    def addFailure(self,test,error):
        super().addFailure(test,error);self.outcomes.append({"id":test.id(),"status":"failed","error_type":error[0].__name__})
    def addError(self,test,error):
        super().addError(test,error);self.outcomes.append({"id":test.id(),"status":"error","error_type":error[0].__name__})
    def addSkip(self,test,reason):
        super().addSkip(test,reason);self.outcomes.append({"id":test.id(),"status":"skipped"})
namespace=runpy.run_path(str(root/"tests/test_ap2_hp_original_server_owner_v1.py"),run_name="captured_owner_tests")
suite=unittest.defaultTestLoader.loadTestsFromTestCase(namespace["OwnerChecks"])
result=unittest.TextTestRunner(verbosity=2,resultclass=RetainedResult).run(suite)
record={"tests_run":result.testsRun,"outcomes":result.outcomes,"failures":len(result.failures),"errors":len(result.errors),
        "skips":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),
        "successful":result.wasSuccessful(),"isolated_python":sys.flags.isolated==1,"site_disabled":sys.flags.no_site==1,
        "bytecode_disabled":sys.dont_write_bytecode,"older_test_suites_executed":False,
        "SDK_module_loaded":any(name.split(".",1)[0] in ("uvicorn","google","a2a","ap2") for name in sys.modules)}
with outcome.open("x",encoding="utf-8") as stream:
    json.dump(record,stream,sort_keys=True,indent=2);stream.write("\n");stream.flush();os.fsync(stream.fileno())
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def capture(output, allocation):
    output = output.absolute()
    parent = ROOT / "runs/ap2-hp-server-owner-software"
    need(output.parent == parent and output.name not in ("", ".", ".."), "Capture requires one named fresh owner-software allocation")
    need(not output.exists() and not output.is_symlink(), "Preserve consumed capture output")
    regular(parent.parent, True)
    if not parent.exists():
        parent.mkdir(exist_ok=False)
    regular(parent, True)
    before = {name: identity(ROOT / name) for name in (*PINS, OWN)}
    need(len(before) == 7 and all(before[name]["sha256"] == value for name, value in PINS.items()),
         "Pinned owner/dependency/test closure differs")
    tree = ast.parse((ROOT / TEST).read_bytes())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "OwnerChecks"]
    need(len(classes) == 1, "Exact new primary test class required")
    names = sorted(node.name for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    need(len(names) == len(set(names)) == 13, "Exactly thirteen unique owner tests required")
    output.mkdir(exist_ok=False)
    allocation["output"] = output
    copied = output / "captured-checkout"
    copied.mkdir()
    for name, expected in before.items():
        destination = copied / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write((ROOT / name).read_bytes())
        need(identity(destination) == expected and identity(ROOT / name) == expected, "Captured owner source bytes differ")
    need(inventory(copied) == before, "Captured source closure membership differs")
    environment = dict(os.environ)
    environment["AP2_HP_SERVER_OWNER_ARTIFACTS"] = str(output / "constructed-artifacts")
    command = [sys.executable, "-I", "-S", "-B", "-c", PROGRAM, str(copied), str(output / "test-outcomes.json")]
    write(output / "plan.json", {"schema_version": "ap2-hp-server-owner-software-plan/1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "inputs_before": before,
        "command": command, "interpreter": {"path": sys.executable, **identity(Path(sys.executable))},
        "expected_test_count": 13, "declared_test_names": names,
        "scope": "Only new authored OwnerChecks; no original/SDK/planner or consumed suite execution"})
    returncode, timed_out = None, False
    with (output / "tests.stdout.bin").open("xb") as stdout, (output / "tests.stderr.bin").open("xb") as stderr:
        try:
            returncode = subprocess.run(command, cwd=copied, env=environment, stdout=stdout, stderr=stderr,
                                        timeout=120, check=False).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    outcome_path = output / "test-outcomes.json"
    outcomes = json.loads(outcome_path.read_bytes()) if outcome_path.is_file() else {}
    membership = (outcomes.get("tests_run") == 13 and len(outcomes.get("outcomes", [])) == 13
                  and sorted(row["id"].rsplit(".", 1)[-1] for row in outcomes["outcomes"]) == names
                  and all(row["status"] == "passed" for row in outcomes["outcomes"]))
    flags = all(outcomes.get(key) is True for key in ("successful", "isolated_python", "site_disabled", "bytecode_disabled"))
    flags = flags and outcomes.get("SDK_module_loaded") is False and outcomes.get("older_test_suites_executed") is False
    flags = flags and all(outcomes.get(key) == 0 for key in ("failures", "errors", "skips", "expected_failures", "unexpected_successes"))
    after = {name: identity(ROOT / name) for name in before}
    unchanged = after == before and inventory(copied) == before
    artifacts = output / "constructed-artifacts"
    artifact_membership = (artifacts.is_dir()
        and sorted(path.name for path in artifacts.iterdir() if path.is_dir()) == names
        and all((artifacts / name / "constructed-owner-reports.json").is_file()
                and json.loads((artifacts / name / "constructed-owner-reports.json").read_bytes()).get("synthetic_only") is True
                for name in names))
    result = {"schema_version": "ap2-hp-server-owner-software-capture/1",
        "status": "passed_constructed_owner_tests_only" if returncode == 0 and not timed_out and membership and flags and unchanged and artifact_membership else "failed_or_incomplete_constructed_capture",
        "returncode": returncode, "timed_out": timed_out, "tests_run": outcomes.get("tests_run"),
        "declared_test_membership_verified": membership, "execution_scope_flags_verified": flags,
        "captured_source_files": len(before), "inputs_after": after, "original_and_captured_inputs_unchanged": unchanged,
        "constructed_artifact_membership_verified": artifact_membership,
        "retained_files_before_result": inventory(output), "original_source_executed": False,
        "SDK_module_loaded_in_test_parent": outcomes.get("SDK_module_loaded"),
        "native_application_execution": False, "model_requests": 0, "credential_read": False,
        "graceful_native_shutdown_proven": False, "native_qualification_established": False,
        "claim_limit": "Constructed source-bound descriptor/ownership software checks only; no original Server, process exit, native task grade or checkpoint credit"}
    write(output / "result.json", result)
    print(json.dumps({key: result[key] for key in ("status", "tests_run", "captured_source_files", "original_and_captured_inputs_unchanged")}))
    return 0 if result["status"] == "passed_constructed_owner_tests_only" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    allocation = {"output": None}
    try:
        return capture(parser.parse_args(argv).output, allocation)
    except BaseException as error:
        result = {"schema_version": "ap2-hp-server-owner-capture-failure/1", "status": "failed_driver_preparation_or_retention",
                  "error_type": type(error).__name__, "native_qualification_established": False,
                  "graceful_native_shutdown_proven": False}
        if allocation["output"] is not None:
            try:
                write(allocation["output"] / "driver.failure.json", result)
            except BaseException:
                pass
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
