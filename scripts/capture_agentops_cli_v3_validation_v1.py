"""One exclusive frozen-copy capture of the ten new constructed CLI tests."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CLI = "scripts/assess_upstream_agentops_case_v3.py"
TEST = "tests/test_assess_upstream_agentops_case_v3.py"
OWN = "scripts/capture_agentops_cli_v3_validation_v1.py"
FIXTURE = "tests/test_agentops_case_boundary_evidence_v1.py"
FIXTURE_SHA256 = "941d1e9965858cdec95463074b81abec52b874d974a67fb90f916179f0ffc7a0"
PROJECTIONS = {
    "application": "runs/upstream-agentops-cases/v1/application/cases.json",
    "expectations": "runs/upstream-agentops-cases/v1/evaluator/expectations.json",
    "obligations": "docs/research/upstream-agentops-grading-obligations-v1.json",
    "answer_schema_design": "docs/research/agentops-answer-schema-assessment-design-v1.json",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path, directory=False):
    for ancestor in (*reversed(path.parents), path):
        info = ancestor.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "linked/reparse capture path is unsupported")
    need(stat.S_ISDIR(path.stat().st_mode) if directory else stat.S_ISREG(path.stat().st_mode),
         "nonregular capture path")
    return path


def relative(name):
    need(type(name) is str and name and ":" not in name and "\\" not in name,
         "unsupported capture dependency path")
    value = PurePosixPath(name)
    need(not value.is_absolute() and ".." not in value.parts and value.as_posix() == name,
         "noncanonical capture dependency path")
    return name


def identity(path):
    raw = regular(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(root):
    regular(root, True)
    items = {}
    for path in sorted(root.rglob("*")):
        regular(path, path.is_dir())
        if path.is_file():
            items[path.relative_to(root).as_posix()] = identity(path)
    return items


def write(path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n"); out.flush(); os.fsync(out.fileno())


def assignments(path):
    result = {}
    for node in ast.parse(regular(path).read_bytes()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("SOURCES", "FROZEN_SOURCE_SHA256", "PINNED_INPUT_SHA256"):
                result[node.targets[0].id] = ast.literal_eval(node.value)
    need(set(result) == {"SOURCES", "FROZEN_SOURCE_SHA256", "PINNED_INPUT_SHA256"},
         "new CLI literal source closure is missing")
    return result


TEST_PROGRAM = r'''
from pathlib import Path
import hashlib,json,os,runpy,subprocess,sys,unittest
root=Path(sys.argv[1]).resolve()
outcome=Path(sys.argv[2])
cli_sha=sys.argv[3]
pending_launch=None
original_run=subprocess.run
def guarded_run(argv,*positional,**kwargs):
    global pending_launch
    if not (pending_launch is None and not positional and type(argv) is list
            and len(argv)>=5 and all(type(item) is str for item in argv)
            and Path(argv[0]).resolve()==Path(sys.executable).resolve()
            and argv[1:4]==["-I","-S","-B"]
            and Path(argv[4]).name=="assess_upstream_agentops_case_v3.py"
            and hashlib.sha256(Path(argv[4]).read_bytes()).hexdigest()==cli_sha
            and kwargs.get("shell",False) is False
            and (kwargs.get("executable") is None
                 or Path(kwargs["executable"]).resolve()==Path(sys.executable).resolve())):
        raise RuntimeError("Constructed CLI capture permits only the bound read-only evaluator")
    kwargs["executable"]=sys.executable
    # Bind the platform's exact audit representation without parsing command text.
    pending_launch={"argv":subprocess.list2cmdline(argv) if os.name=="nt" else list(argv),
                    "script":Path(argv[4]),"cwd":kwargs.get("cwd"),"env":kwargs.get("env")}
    try:
        return original_run(argv,**kwargs)
    finally:
        pending_launch=None
def guard(event,args):
    if event.startswith("socket."):
        raise RuntimeError("Constructed CLI capture denies network")
    if event == "subprocess.Popen":
        executable,argv,cwd,env=args
        if not (pending_launch is not None and type(executable) is str
                and Path(executable).resolve()==Path(sys.executable).resolve()
                and type(argv) is type(pending_launch["argv"]) and argv==pending_launch["argv"]
                and cwd==pending_launch["cwd"] and env is pending_launch["env"]
                and hashlib.sha256(pending_launch["script"].read_bytes()).hexdigest()==cli_sha):
            raise RuntimeError("Constructed CLI capture permits only the bound read-only evaluator")
sys.addaudithook(guard)
subprocess.run=guarded_run
class RetainedResult(unittest.TextTestResult):
    def __init__(self,*a,**k):
        super().__init__(*a,**k); self.outcomes=[]
    def addSuccess(self,test):
        super().addSuccess(test); self.outcomes.append({"id":test.id(),"status":"passed"})
    def addFailure(self,test,error):
        super().addFailure(test,error); self.outcomes.append({"id":test.id(),"status":"failed","error_type":error[0].__name__})
    def addError(self,test,error):
        super().addError(test,error); self.outcomes.append({"id":test.id(),"status":"error","error_type":error[0].__name__})
    def addSkip(self,test,reason):
        super().addSkip(test,reason); self.outcomes.append({"id":test.id(),"status":"skipped"})
namespace=runpy.run_path(str(root/"tests/test_assess_upstream_agentops_case_v3.py"),run_name="captured_corrected_cli_tests")
suite=unittest.defaultTestLoader.loadTestsFromTestCase(namespace["CorrectedCliTests"])
result=unittest.TextTestRunner(verbosity=2,resultclass=RetainedResult).run(suite)
record={"tests_run":result.testsRun,"outcomes":result.outcomes,"failures":len(result.failures),"errors":len(result.errors),
        "skips":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),
        "successful":result.wasSuccessful(),"isolated_python":sys.flags.isolated==1,"site_disabled":sys.flags.no_site==1,
        "bytecode_disabled":sys.dont_write_bytecode,"old_test_suites_executed":False,
        "SDK_module_loaded":any(name=="google" or name.startswith(("google.","a2a.","ap2.")) for name in sys.modules)}
with outcome.open("x",encoding="utf-8") as out:
    json.dump(record,out,sort_keys=True,indent=2); out.write("\n")
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def capture(output):
    output = output.resolve()
    need(output.is_relative_to(ROOT / "runs/agentops-grading-software"), "output outside named grading software captures")
    need(not output.exists() and not output.is_symlink(), "output already consumed")
    regular(output.parent, True)
    declared = assignments(ROOT / CLI)
    sources = set(declared["SOURCES"]) | {TEST, OWN, FIXTURE, *PROJECTIONS.values()}
    design = json.loads(regular(ROOT / PROJECTIONS["answer_schema_design"]).read_bytes())
    need(type(design) is dict and type(design.get("source_artifacts")) is list, "unsupported source-bound design")
    source_artifacts = {}
    for row in design["source_artifacts"]:
        name = relative(row["path"])
        bound = {key: row[key] for key in ("bytes", "sha256")}
        need(name not in source_artifacts or source_artifacts[name] == bound, "conflicting design dependency")
        source_artifacts[name] = bound; sources.add(name)
    need(len(sources) <= 1024, "oversized captured source set")
    before = {relative(name): identity(ROOT / relative(name)) for name in sorted(sources)}
    for key, name in PROJECTIONS.items():
        need(before[name]["sha256"] == declared["PINNED_INPUT_SHA256"][key], "frozen input projection differs")
    for name, expected in declared["FROZEN_SOURCE_SHA256"].items():
        need(before[name]["sha256"] == expected, "frozen evaluator dependency differs")
    for name, expected in source_artifacts.items():
        need(before[name] == expected, "frozen original design dependency differs")
    need(before[FIXTURE]["sha256"] == FIXTURE_SHA256, "frozen fixture builder differs")
    tree = ast.parse(regular(ROOT / TEST).read_bytes())
    names = sorted(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    need(len(names) == len(set(names)) == 10, "exactly ten unique new tests required")
    output.mkdir()
    checkout = output / "captured-checkout"; checkout.mkdir()
    for name, expected in before.items():
        destination = checkout / name; destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as out:
            out.write(regular(ROOT / name).read_bytes())
        need(identity(destination) == expected and identity(ROOT / name) == expected, "copied input differs")
    copied = inventory(checkout)
    need(copied == before, "captured checkout closure differs")
    environment = dict(os.environ)
    environment["ASSESS_CLI_V3_ARTIFACTS"] = str(output / "constructed-artifacts")
    command = [sys.executable, "-I", "-S", "-B", "-c", TEST_PROGRAM, str(checkout),
               str(output / "test-outcomes.json"), before[CLI]["sha256"]]
    write(output / "capture-plan.json", {
        "schema_version": "agentops-corrected-cli-software-plan/1", "created_at_utc": now(), "command": command,
        "interpreter": {"path": sys.executable, **identity(Path(sys.executable))}, "inputs_before": before,
        "captured_inputs": copied, "declared_test_names": names, "expected_test_count": 10,
        "only_new_primary_test_class_executed": True,
        "scope": "Constructed retained instances and exact CLI helper bytes; no original application or model execution"})
    started = now(); returncode = None; timed_out = False
    with (output / "tests.stdout.bin").open("xb") as stdout, (output / "tests.stderr.bin").open("xb") as stderr:
        try:
            returncode = subprocess.run(command, cwd=checkout, env=environment, stdout=stdout, stderr=stderr,
                                        timeout=600, check=False).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    outcome_path = output / "test-outcomes.json"
    outcomes = json.loads(outcome_path.read_bytes()) if outcome_path.is_file() else {}
    members = (outcomes.get("tests_run") == 10 and len(outcomes.get("outcomes", [])) == 10
               and sorted(row["id"].rsplit(".", 1)[-1] for row in outcomes["outcomes"]) == names
               and all(row["status"] == "passed" for row in outcomes["outcomes"]))
    flags = all(outcomes.get(key) is True for key in ("successful", "isolated_python", "site_disabled", "bytecode_disabled"))
    flags = flags and outcomes.get("SDK_module_loaded") is False and outcomes.get("old_test_suites_executed") is False
    after = {name: identity(ROOT / name) for name in before}
    unchanged = after == before and inventory(checkout) == copied
    result = {
        "schema_version": "agentops-corrected-cli-software-capture/1",
        "status": "passed_constructed_software_tests_only" if returncode == 0 and not timed_out and members and flags and unchanged else "failed_or_incomplete_constructed_capture",
        "started_at_utc": started, "finished_at_utc": now(), "returncode": returncode, "timed_out": timed_out,
        "tests_run": outcomes.get("tests_run"), "declared_test_membership_verified": members,
        "execution_scope_flags_verified": flags, "captured_input_files": len(copied), "inputs_after": after,
        "original_and_captured_inputs_unchanged": unchanged, "retained_files_before_result": inventory(output),
        "original_case_execution": False, "native_application_execution": False, "model_requests": 0,
        "credential_read": False, "native_qualification_established": False,
        "claim_limit": "Source-bound corrected CLI integration over synthetic retained instances only; no native task grade or checkpoint credit"}
    write(output / "result.json", result)
    print(json.dumps({key: result[key] for key in ("status", "tests_run", "captured_input_files", "original_and_captured_inputs_unchanged")}))
    return 0 if result["status"] == "passed_constructed_software_tests_only" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    return capture(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
