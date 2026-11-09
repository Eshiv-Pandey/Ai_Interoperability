"""Read-only independent review of a terminal preparation/3 export.

No application, test suite, solver, benchmark, subprocess or WSL command runs.
Only hash-bound captured evidence checkers are re-evaluated. This script is
prepared before export and refuses to start without terminal parent/export
receipts and a separately supplied export-manifest digest.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
REVIEW = Path(__file__).resolve().parent
STAGE = REVIEW.parent
ROOT = STAGE.parents[2]
PARENT = STAGE.with_name(STAGE.name + "-invocation")
EXPORT = STAGE / "export"
WORKSPACE = EXPORT / "workspace"
GROUP = "runs/agentops-admission-live-v1"
PREFIX = "runs/agentops-http-control/admission-live-v1-"
PHASES = ["software", "prepare", "preflight", "launch", "after"]
SOFTWARE = ["test_agentops_admitted_client_v1", "test_agentops_admission_live_plan_v3",
            "test_agentops_admission_chain_v3", "test_export_agentops_admission_v3",
            "test_pending_admission", "test_refinement", "test_agentops_owned_child_v1",
            "test_agentops_interpreter_exit_diagnostics_v1", "test_check_agentops_interpreter_exit_v2",
            "test_agentops_startup_diagnostics_v1", "test_check_agentops_startup_v1",
            "test_refinement_scaling_generator_v1", "node-controller"]


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path, root):
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def safe_name(name):
    path = PurePosixPath(name)
    if (not path.parts or path.is_absolute() or ".." in path.parts
            or any(char in name for char in ("\\", ":", "\0")) or name != path.as_posix()):
        raise ValueError("Unsafe retained relative path: " + repr(name))
    return name


def inventory(root):
    files, pending = [], [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as stream:
            entries = sorted(stream, key=lambda item: item.name)
        for entry in entries:
            path = Path(entry.path)
            info = path.lstat()
            if (stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                raise ValueError("Link/reparse point in evidence: " + str(path))
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                files.append(record(path, root))
            else:
                raise ValueError("Nonregular evidence: " + str(path))
    return sorted(files, key=lambda row: row["path"])


def write_new(name, value):
    with (REVIEW / name).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def workspace_record(name):
    return record(WORKSPACE / safe_name(name), WORKSPACE)


def missing_file_equivalent(original, relocated, case):
    """Accept only the known Linux/Windows missing-file message difference."""
    if original == relocated:
        return True, None
    left, right = dict(original), dict(relocated)
    a, b = left.pop("validation_errors", None), right.pop("validation_errors", None)
    missing = case / "service/service-result.json"
    allowed = (left == right and not missing.exists() and isinstance(a, list) and isinstance(b, list)
               and len(a) == len(b) == 1 and all(text.startswith("FileNotFoundError:")
               and "service-result.json" in text for text in a + b))
    return allowed, ({"retained_errors": a, "relocated_errors": b,
                      "reason": "Same absent service-result.json; platform/path exception text differs"} if allowed else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-export-manifest-sha256", required=True)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{64}", args.expected_export_manifest_sha256):
        parser.error("Require the separately observed terminal export-manifest digest")
    parent = load(PARENT / "result.json")
    exported = load(EXPORT / "result.json")
    if (not parent.get("finished_at_utc") or parent.get("status") not in ("recorded", "failed_or_incomplete")
            or exported.get("status") != "exported" or not exported.get("finished_at_utc")):
        raise ValueError("Parent/export is not terminal and complete; do not audit mutable evidence")
    if (REVIEW / "execution.json").exists() or (REVIEW / "result.json").exists():
        raise FileExistsError("Preserve the existing review allocation")
    report = {"schema_version": "agentops-admission-independent-export-review/2",
              "started_at_utc": now(), "reviewer": "Independent AI evidence review; not human approval",
              "status": "started", "application_launches": 0, "wsl_launches": 0,
              "solver_benchmark_or_test_reruns": 0, "failures": [], "limitations": [],
              "source": record(Path(__file__), REVIEW),
              "expected_manifest_sha256": args.expected_export_manifest_sha256}
    write_new("execution.json", report)
    before, parent_before = inventory(EXPORT), inventory(PARENT)
    write_new("export-before.json", before)
    write_new("parent-before.json", parent_before)
    stage_before = [record(path, STAGE) for path in sorted(STAGE.iterdir()) if path.is_file()]
    write_new("stage-before.json", stage_before)
    config = Path(r"C:\Users\Lenovo\.wslconfig")
    config_before = config.read_bytes()

    def check(condition, message):
        if not condition:
            report["failures"].append(message)

    def check_streams(directory, item):
        for stream in item.get("streams", []):
            path = directory / safe_name(stream["path"])
            check(sha(path) == stream["sha256"], "Stream digest differs: " + str(path))

    def summarize_check(value):
        keys = ("valid", "complete", "strict_success", "outcome", "classification",
                "validation_errors", "observation_gaps", "completion_blockers", "phases",
                "captures_started", "captures_completed", "trace_bytes", "readiness_observed", "observer_stopped")
        return {key: value[key] for key in keys if key in value}

    try:
        manifest = load(EXPORT / "manifest.json")
        manifest_record = record(EXPORT / "manifest.json", EXPORT)
        check(exported["schema_version"] == "agentops-admission-export-result/3"
              and manifest["schema_version"] == "agentops-admission-export-manifest/3", "Wrong export schema")
        check(manifest_record == exported["manifest"] and manifest_record["sha256"] == args.expected_export_manifest_sha256,
              "Export manifest is not bound to the supplied digest/result")
        check(manifest["status"] == "exported" and not exported["failures"] and not manifest["failures"], "Export integrity failure")
        check(exported["sources_unchanged"] is True and exported["copies_match_source_before"] is True,
              "Export source/copy equality missing")
        copied = [{**row, "path": row["path"].removeprefix("workspace/")}
                  for row in before if row["path"].startswith("workspace/")]
        check(copied == manifest["copied"]["files"] == manifest["source_before"]["files"] == manifest["source_after"]["files"],
              "Actual/copy/source-before/source-after files differ")
        check(all(manifest[key]["complete"] is True and not manifest[key]["errors"]
                  for key in ("source_before", "source_after", "copied")), "Incomplete export inventory")
        check(len(copied) == exported["copied_files"] and sum(row["bytes"] for row in copied) == exported["copied_bytes"],
              "Export size/count differs from actual bytes")
        check(exported["external_runtime_closure_copied"] is False
              and not any(row["path"].startswith("external/runtime") for row in copied), "Unexpected runtime export scope")
        exporter_record = record(EXPORT / "exporter-source.py", EXPORT)
        check(exporter_record == exported["exporter_source"] == manifest["exporter"]["copy_before"] == manifest["exporter"]["copy_after"],
              "Captured exporter bytes differ")
        check(exporter_record["sha256"] == sha(WORKSPACE / "scripts/export_agentops_admission_v3.py")
              and exported["exporter_source_unchanged"] is True and exported["exporter_copy_matches_before"] is True
              and manifest["exporter"]["before"] == manifest["exporter"]["after"], "Exporter source identity differs")

        stage = load(STAGE / "stage-plan.json")
        stage_result, linux_stage = load(STAGE / "result.json"), load(STAGE / "linux-stage.json")
        staged_copy = load(WORKSPACE / GROUP / "stage-manifest.json")
        check(staged_copy == stage, "Windows/Linux stage manifests differ")
        check(stage_result["status"] == linux_stage["status"] == "passed"
              and stage_result["source_unchanged"] is True and linux_stage["source_unchanged"] is True
              and linux_stage["runtime_inspection_returncode"] == 0, "Staging did not verify unchanged source/runtime")
        check(stage["linux_workspace"] == stage_result["linux_workspace"] == linux_stage["linux_workspace"] == exported["workspace"],
              "Stage/export workspace identities differ")
        check(re.fullmatch(r"/var/tmp/agentops-admission-live-v1-[0-9a-f]{16}", stage["linux_workspace"]) is not None,
              "Unexpected staged workspace allocation")
        plan = load(WORKSPACE / GROUP / "preparation/plan.json")
        check(plan["schema_version"] == "agentops-admission-live-preparation/3"
              and plan["workspace"] == stage["linux_workspace"] and plan["reuse_root"] == stage["reuse_root"] == exported["reuse_root"],
              "Preparation/runtime identity differs")
        for row in stage["files"]:
            check(workspace_record(row["path"]) == row, "Stage/export source differs: " + row["path"])
            check(record(ROOT / safe_name(row["path"]), ROOT) == row, "Current original source differs from stage: " + row["path"])
        for row in plan["inputs"]:
            check(workspace_record(row["path"]) == row, "Preparation input differs: " + row["path"])
        allowed = {row["path"] for row in plan["inputs"]}
        allowed.update(row["path"] for row in copied if any(row["path"].startswith(tree + "/") for tree in (GROUP, PREFIX + "N11", PREFIX + "B7")))
        check(allowed == {row["path"] for row in copied}, "Export contains out-of-scope files")
        archives = [STAGE / name for name in ("stage.tar.gz", "source.tar.gz", "stage.tar") if (STAGE / name).is_file()]
        if not archives:
            archives = list(STAGE.glob("*.tar*"))
        check(len(archives) == 1, "Expected one retained stage archive")
        if len(archives) == 1:
            archive = archives[0]
            check(sha(archive) == stage["archive_sha256"], "Stage archive hash differs")
            archive_rows = []
            with tarfile.open(archive, "r:*") as bundle:
                for member in bundle.getmembers():
                    check(member.isfile(), "Nonregular stage archive member: " + member.name)
                    if member.isfile():
                        name = safe_name(member.name)
                        raw = bundle.extractfile(member).read()
                        archive_rows.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            check(sorted(archive_rows, key=lambda row: row["path"]) == sorted(stage["files"], key=lambda row: row["path"]),
                  "Stage archive contents differ from stage manifest")
        report["integrity"] = {"manifest": manifest_record, "workspace_files": len(copied),
                               "workspace_bytes": sum(row["bytes"] for row in copied), "staged_files": len(stage["files"]),
                               "prepared_inputs": len(plan["inputs"]), "export_files": len(before),
                               "workspace": stage["linux_workspace"], "reuse_root": stage["reuse_root"],
                               "external_runtime_closure_copied": False, "exporter_source": exporter_record}

        parent_plan = load(PARENT / "plan.json")
        check(parent["schema_version"] == "agentops-admission-windows-invocation/3", "Wrong parent schema")
        check(parent_plan["stage_output"] == str(STAGE) and parent_plan["reuse_root"] == stage["reuse_root"], "Parent stage/runtime identity differs")
        check(sha(PARENT / "record_attempt.py") == parent_plan["recorder_sha256"], "Outer recorder capture differs")
        for row in parent_plan["sources"]:
            check(sha(WORKSPACE / safe_name(row["path"])) == row["sha256"], "Reviewed/staged launcher differs: " + row["path"])
        for item in parent["invocations"]:
            check(item == load(PARENT / (item["name"] + ".result.json")), "Parent invocation receipt differs")
            check_streams(PARENT, item)
        check([item["name"] for item in parent["invocations"]] == ["stage", "chain"], "Parent did not record exactly one stage and chain")
        parent_recorded = (len(parent["invocations"]) == 2 and all(item["returncode"] == 0 for item in parent["invocations"])
                           and not parent["errors"] and parent["wslconfig_unchanged"] is True
                           and parent["reviewed_sources_unchanged"] is True)
        check(parent["status"] == ("recorded" if parent_recorded else "failed_or_incomplete"), "Parent status differs from retained invocation outcomes")
        expected_python = stage["reuse_root"] + "/external/runtime-agentops-linux-v7/venv/bin/python"
        mounted_export = str(EXPORT).replace("\\", "/")
        mounted_export = "/mnt/" + mounted_export[0].lower() + mounted_export[2:]
        expected_chain_argv = ["wsl.exe", "-d", "Ubuntu", "--", expected_python, "-B",
                               stage["linux_workspace"] + "/scripts/run_agentops_admission_chain_v3.py",
                               "--workspace", stage["linux_workspace"], "--export-output", mounted_export]
        check(parent["invocations"][0]["argv"] == parent_plan["stage_argv"]
              and parent["invocations"][1]["argv"] == expected_chain_argv, "Parent stage/chain argv identity differs")
        check(parent["host_configuration_mutations"] == parent_plan["host_configuration_mutations"] == 0
              and parent["wslconfig_unchanged"] is True and parent["reviewed_sources_unchanged"] is True,
              "Parent source/config integrity differs")
        original_config = (PARENT / "wslconfig-before.bin").read_bytes()
        check(config_before == original_config and hashlib.sha256(original_config).hexdigest() == parent_plan["wslconfig_sha256"],
              "Current host config differs from pre-invocation bytes")
        report["host_configuration"] = {"unchanged_since_parent_start": config_before == original_config,
                                        "sha256": hashlib.sha256(config_before).hexdigest(), "review_mutations": 0}

        chain_dir = WORKSPACE / GROUP / "phase-chain"
        chain_plan, chain = load(chain_dir / "plan.json"), load(chain_dir / "result.json")
        check(chain_plan["schema_version"] == "agentops-admission-phase-chain/3"
              and chain["schema_version"] == "agentops-admission-phase-chain-result/3", "Wrong chain schema")
        check(sha(chain_dir / "run_chain.py") == sha(WORKSPACE / "scripts/run_agentops_admission_chain_v3.py"), "Captured chain source differs")
        for row in chain_plan["sources"]:
            check(sha(WORKSPACE / safe_name(row["path"])) == row["sha256"], "Chain-bound source differs")
        check([item["phase"] for item in chain_plan["commands"]] == PHASES
              and chain_plan["maximum_attempts_per_phase"] == 1, "Chain plan/order/attempt limit differs")
        check(chain_plan["export_argv"] == [expected_python, "-B", stage["linux_workspace"] + "/scripts/export_agentops_admission_v3.py",
                                            "--workspace", stage["linux_workspace"], "--output", mounted_export], "Chain exporter argv/version differs")
        for command in chain_plan["commands"]:
            check(command["argv"] == [expected_python, "-B", stage["linux_workspace"] + "/scripts/execute_agentops_admission_phase_v3.py",
                                      "--workspace", stage["linux_workspace"], "--phase", command["phase"]], "Chain phase argv/version differs")
        actual_phases = [item["phase"] for item in chain["commands"]]
        check(actual_phases == PHASES[:len(actual_phases)] and chain["unexecuted_phases"] == PHASES[len(actual_phases):],
              "Chain phase inventory differs")
        phases, python_total, python_skipped, node_total = {}, 0, 0, 0
        python_suites = []
        for item in chain["commands"]:
            phase = item["phase"]
            check(item == load(chain_dir / (phase + ".receipt.json")), "Chain phase receipt differs: " + phase)
            check_streams(chain_dir, item)
            phase_dir = WORKSPACE / GROUP / ("phase-" + phase)
            phase_report, phase_plan = load(phase_dir / "result.json"), load(phase_dir / "plan.json")
            check(sha(phase_dir / "execute_phase.py") == sha(WORKSPACE / "scripts/execute_agentops_admission_phase_v3.py"),
                  "Captured phase driver differs: " + phase)
            check(load(phase_dir / "driver-source.json")["sha256"] == sha(phase_dir / "execute_phase.py"), "Phase source binding differs")
            expected_names = SOFTWARE if phase == "software" else (["python-runtime-after", "verify-prepared-inputs"] if phase == "after" else [phase])
            check([command["name"] for command in phase_plan["commands"]] == expected_names, "Unexpected phase commands: " + phase)
            for index, command in enumerate(phase_report["commands"]):
                check(command == load(phase_dir / (command["name"] + ".receipt.json")), "Phase command receipt differs")
                check({key: command[key] for key in ("name", "argv", "cwd")} == phase_plan["commands"][index], "Executed command differs from phase plan")
                check_streams(phase_dir, command)
                if phase == "software" and command["name"].startswith("test_"):
                    text = (phase_dir / (command["name"] + ".stderr.bin")).read_text(encoding="utf-8")
                    match = re.search(r"^Ran (\d+) tests? in .+\n\s*\nOK(?: \(skipped=(\d+)\))?\s*$", text, re.MULTILINE)
                    check(command["returncode"] != 0 or match is not None, "Missing clean unittest summary: " + command["name"])
                    count, skips = (int(match[1]), int(match[2] or 0)) if match else (0, 0)
                    python_total += count - skips
                    python_skipped += skips
                    python_suites.append({"suite": command["name"], "ran": count, "passed": count - skips, "skipped": skips,
                                          "returncode": command["returncode"]})
                elif phase == "software" and command["name"] == "node-controller":
                    text = (phase_dir / "node-controller.stdout.bin").read_text(encoding="utf-8")
                    metrics = {key: int(value) for key, value in re.findall(r"^# (tests|pass|fail|cancelled|skipped|todo) (\d+)\s*$", text, re.MULTILINE)}
                    check(command["returncode"] != 0 or (metrics.get("pass") == metrics.get("tests") and metrics.get("fail") == 0
                          and metrics.get("cancelled") == metrics.get("skipped") == metrics.get("todo") == 0), "Node test summary differs")
                    node_total = metrics.get("pass", 0)
            calculated = (len(phase_report["commands"]) == len(expected_names)
                          and all(command["returncode"] == 0 for command in phase_report["commands"])
                          and phase_report["staged_sources_unchanged"] is True
                          and (phase != "after" or phase_report.get("python_runtime_equal") is True))
            check(phase_report["status"] == ("passed" if calculated else "failed")
                  and (item["returncode"] == 0) == calculated, "Phase process/status calculation differs: " + phase)
            phases[phase] = {"status": phase_report["status"], "commands": len(phase_report["commands"]),
                             "staged_sources_unchanged": phase_report["staged_sources_unchanged"], "returncode": item["returncode"]}
        if "launch" in actual_phases:
            check(all(phases[name]["status"] == "passed" for name in PHASES[:3]) and "after" in actual_phases,
                  "Launch gate or mandatory after-inspection violated")
        expected_chain_success = actual_phases == PHASES and all(item["returncode"] == 0 for item in chain["commands"])
        check(chain["status"] == ("phases_passed" if expected_chain_success else "phase_failed"), "Chain status differs from actual phases")
        report["execution_levels"] = {"parent_status": parent["status"], "parent_errors": parent["errors"],
                                      "chain_status": chain["status"], "phases": phases,
                                      "application_success_inferred_from_parent_or_chain": False}
        report["software_tests"] = {"python_passed": python_total, "python_skipped": python_skipped,
                                    "node_passed": node_total, "python_suites": python_suites,
                                    "rerun_during_review": False}

        preparation = load(WORKSPACE / GROUP / "preparation/verification.json")
        if "after" in phases:
            runtime_before = WORKSPACE / GROUP / "python-runtime-before.json"
            runtime_after = WORKSPACE / GROUP / "phase-after/python-runtime-after.stdout.bin"
            after_phase = load(WORKSPACE / GROUP / "phase-after/result.json")
            runtime_equal = load(runtime_before) == load(runtime_after)
            check(after_phase.get("python_runtime_equal") == runtime_equal, "Runtime equality receipt differs from inspections")
            after_verify = load(WORKSPACE / GROUP / "phase-after/verify-prepared-inputs.stdout.bin")
            check(preparation["bridge"] == after_verify["bridge"], "Before/after bridge verification differs")
            check(after_verify["staged_files"] == len(plan["inputs"]), "After verification input count differs")
            report["runtime_evidence"] = {"python_before": record(runtime_before, WORKSPACE), "python_after": record(runtime_after, WORKSPACE),
                                          "inspection_objects_equal": runtime_equal, "inspection_bytes_equal": runtime_before.read_bytes() == runtime_after.read_bytes(),
                                          "bridge_before_after_equal": preparation["bridge"] == after_verify["bridge"],
                                          "bridge": after_verify["bridge"], "external_runtime_reinspected_during_review": False}

        # No captured modules are imported unless all package/input integrity checks passed.
        if report["failures"]:
            raise ValueError("Pre-check integrity discrepancies; retained checker code was not imported")
        sys.path[:0] = [str(WORKSPACE / "scripts"), str(WORKSPACE / "src")]
        bridge = importlib.import_module("check_agentops_bridge_v1")
        effects = importlib.import_module("check_agentops_effect_v2")
        diagnostics = importlib.import_module("check_agentops_bridge_diagnostic_v1")
        exits = importlib.import_module("check_agentops_interpreter_exit_v2")
        startup = importlib.import_module("check_agentops_startup_v1")
        seed = effects.seed_snapshot(WORKSPACE / "external/agentops-c806b7f1/agents/data/incidents.db")
        group_path = WORKSPACE / GROUP / "attempt/result.json"
        if not group_path.exists():
            report["live_outcome"] = {"group_status": "not_executed", "reason": "No terminal attempt group in stable export"}
            report["limitations"].append("No live group is available for application verification")
        else:
            group = load(group_path)
            check(group["status"] == exported["group_execution"]["status"], "Export/group execution status differs")
            check(group["plan"] == workspace_record(GROUP + "/preparation/plan.json") and group.get("plan_unchanged") is True,
                  "Group plan identity differs")
            check(group["live_model_calls"] == group["research_gate_credit_added"] == 0, "Unexpected model calls or gate credit")
            live = {"group_status": group["status"], "cases": {}, "candidate_application_executed": False,
                    "candidate_strict_success": False, "root_cause_established": False}
            for name in ("N11", "B7"):
                item, case = group["cases"][name], WORKSPACE / (PREFIX + name)
                if item["status"] in ("skipped", "unexecuted"):
                    check(item == load(WORKSPACE / GROUP / "attempt" / (name + "." + item["status"] + ".json")), "Skipped/unexecuted case receipt differs")
                    check(not case.exists(), "Skipped/unexecuted case was allocated")
                    check(not (WORKSPACE / GROUP / "attempt" / (name + ".invocation.json")).exists(), "Skipped/unexecuted case has invocation marker")
                    live["cases"][name] = dict(item)
                    continue
                if not (case / "result.json").exists():
                    live["cases"][name] = {**item, "independent_recheck": "No complete case result; partial record retained"}
                    report["limitations"].append(name + " lacks a complete case result")
                    continue
                result, case_plan = load(case / "result.json"), load(case / "plan.json")
                check(item["result"] == workspace_record(PREFIX + name + "/result.json") and item["status"] == result["status"], "Group/case result differs: " + name)
                for field, source in (("service_source", "scripts/serve_agentops_bridge_diagnostic_v4.py"),
                                      ("startup_observer_source", "scripts/agentops_startup_diagnostics_v1.py"),
                                      ("startup_checker_source", "scripts/check_agentops_startup_v1.py")):
                    check(case_plan[field] == workspace_record(source), "Case version source differs: " + field)
                check(case_plan["client_config"] == workspace_record(PREFIX + name + "/client-config.json")
                      and case_plan["admission_preparation"] == workspace_record(GROUP + "/preparation/plan.json"), "Case config/preparation binding differs")
                check(case_plan["readiness_timeout_seconds"] == 65 and case_plan["startup_stack_seconds"] == case_plan["exit_watchdog_seconds"] == 5,
                      "Prospective deadline/diagnostic options differ")
                for row in result["files"]:
                    check(workspace_record(row["path"]) == row, "Case recorded file differs: " + row["path"])
                service_check = bridge.check_service(case / "service", seed)
                if name == "N11":
                    checked = bridge.check_case(case, seed)
                else:
                    # Re-evaluate only the two inspected read-only functions from captured coordinator source.
                    source = WORKSPACE / "scripts/agentops_admission_control_v3.py"
                    tree = ast.parse(source.read_bytes(), filename=str(source))
                    names = {"check_certified_origin_request", "admitted_case_check"}
                    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
                    if len(nodes) != 2:
                        raise ValueError("Captured read-only admitted checker functions are missing")
                    scope = {"json": json, "ROOT": WORKSPACE, "design": SimpleNamespace(load=load, record=record),
                             "parse_asgi_exchange": bridge.parse_asgi_exchange, "check_owned_group": bridge.check_owned_group,
                             "at_utc": effects.at_utc}
                    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), scope)
                    checked = scope["admitted_case_check"](case, plan, result, service_check)
                    live["candidate_application_executed"] = (case / "client.started.json").is_file()
                values = {"service": service_check, "case": checked,
                          "diagnostic": diagnostics.validate_diagnostics(case, checked),
                          "interpreter-exit": exits.validate_interpreter_exit(case), "startup": startup.validate_startup(case)}
                retained_names = {"service": "check.json", "case": "case-check.json", "diagnostic": "diagnostic-check.json",
                                  "interpreter-exit": "interpreter-exit-check.json", "startup": "startup-check.json"}
                differences = []
                for label, value in values.items():
                    write_new(name + "-" + label + "-recheck.json", value)
                    equivalent, difference = missing_file_equivalent(load(case / retained_names[label]), value, case)
                    check(equivalent, "Recomputed " + name + " " + label + " classification differs")
                    if difference:
                        differences.append({"checker": label, **difference})
                process = load(case / "service-process.json")
                launch = startup.diagnostic_launch(case, process)
                check(launch["argv"][0] == stage["reuse_root"] + "/external/runtime-agentops-linux-v7/venv/bin/python"
                      and launch["argv"][2] == stage["linux_workspace"] + "/scripts/serve_agentops_bridge_diagnostic_v4.py",
                      "Service argv does not bind prepared interpreter/wrapper")
                child, cleanup = result.get("service_child_cleanup", {}), result.get("service_group_cleanup", {})
                check(child.get("pid") == process["pid"] and child.get("argv") == process["argv"]
                      and child.get("returncode") == result.get("service_returncode") and child.get("owned_group") == cleanup,
                      "Owned child/PID/argv/returncode/group differ")
                check(bridge.check_owned_group(cleanup, process["pid"]), "Owned service-group evidence fails independent validation")
                strict = (checked.get("strict_success") is True and result.get("status") == "recorded"
                          and values["diagnostic"].get("valid") is True and values["diagnostic"].get("complete") is True
                          and values["diagnostic"].get("classification") == "asyncio_run_returned"
                          and values["interpreter-exit"].get("valid") is True and values["interpreter-exit"].get("complete") is True
                          and values["startup"].get("valid") is True and values["startup"].get("complete") is True)
                check(item["strict_success"] == strict, "Strict case gate differs: " + name)
                if name == "B7":
                    live["candidate_strict_success"] = strict
                    check(group["cases"]["N11"].get("strict_success") is True and group["cases"]["N11"].get("status") == "recorded",
                          "B7 ran without a qualified fresh native prerequisite")
                lifecycles = {}
                for folder in ("startup-diagnostics", "shutdown-diagnostics", "interpreter-exit-diagnostics"):
                    path = case / "service" / folder / "lifecycle.jsonl"
                    if path.is_file():
                        events = [json.loads(line) for line in path.read_bytes().splitlines()]
                        check(all(event["pid"] == process["pid"] for event in events), "Lifecycle PID differs: " + folder)
                        lifecycles[folder] = [event["phase"] for event in events]
                trace = case / "service/startup-diagnostics/startup-stacks.txt"
                locations = re.findall(r'^\s*File "([^"]+)", line (\d+) in (.*)$', trace.read_text(encoding="utf-8"), re.MULTILINE) if trace.is_file() else []
                live["cases"][name] = {"status": result["status"], "strict_success": strict, "error": result.get("error"),
                    "service_returncode": result.get("service_returncode"), "forced_service_stop": result.get("forced_service_stop"),
                    "child_reaped_before_group_check": child.get("reaped_before_group_check"), "cleanup_errors": result.get("cleanup_errors"),
                    "service_group_cleanup": cleanup, "service_process": process, "lifecycle_phases": lifecycles,
                    "startup_stack_locations": [{"file": path, "line": int(line), "function": function} for path, line, function in locations],
                    "client_launch_recorded": (case / "client.started.json").is_file(),
                    "checkers": {label: summarize_check(value) for label, value in values.items()},
                    "service_task_completed": service_check.get("task_completed"), "service_effect": service_check.get("effect"),
                    "platform_exception_differences": differences}
            strict_group = all(group["cases"][name].get("strict_success") for name in ("N11", "B7"))
            if group["status"] in ("strict_success", "attempts_recorded"):
                check(group["status"] == ("strict_success" if strict_group else "attempts_recorded"), "Group strict gate differs")
            report["live_outcome"] = live
        imported = []
        for name, module in sorted(sys.modules.items()):
            if name.startswith(("check_agentops", "agentops_", "interoperability")) and getattr(module, "__file__", None):
                path = Path(module.__file__).resolve()
                check(path.is_relative_to(WORKSPACE), "Local module imported outside verified export: " + name)
                imported.append({"module": name, "source": record(path, WORKSPACE)})
        report["exported_modules_imported"] = imported
    except Exception as error:
        report["failures"].append(type(error).__name__ + ": " + str(error))
    finally:
        after, parent_after = inventory(EXPORT), inventory(PARENT)
        stage_after = [record(path, STAGE) for path in sorted(STAGE.iterdir()) if path.is_file()]
        write_new("export-after.json", after)
        write_new("parent-after.json", parent_after)
        write_new("stage-after.json", stage_after)
        report["export_unchanged_during_review"] = before == after
        report["parent_unchanged_during_review"] = parent_before == parent_after
        report["stage_receipts_unchanged_during_review"] = stage_before == stage_after
        report["host_configuration_unchanged_during_review"] = config_before == config.read_bytes()
        for key in ("export_unchanged_during_review", "parent_unchanged_during_review",
                    "stage_receipts_unchanged_during_review", "host_configuration_unchanged_during_review"):
            check(report[key], key + " is false")
        report["finished_at_utc"] = now()
        report["status"] = "review_discrepancies" if report["failures"] else ("verified_strict_success" if report.get("live_outcome", {}).get("candidate_strict_success") else "verified_recorded_outcome")
        report["review_files"] = [record(path, REVIEW) for path in sorted(REVIEW.iterdir()) if path.is_file()]
        write_new("result.json", report)
    print(json.dumps({key: report.get(key) for key in ("status", "integrity", "execution_levels", "software_tests", "live_outcome", "failures")}, indent=2))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
