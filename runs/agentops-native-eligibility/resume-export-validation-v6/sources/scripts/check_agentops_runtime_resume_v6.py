"""Read-only parent verification of resume-v6 exports; never execute archived code.

Reuses the original effect/wire checkers and trusted native/HTTP gate code.
Linux command operands are checked before rebasing the two receipt reads needed
by the native gate. Hashes always cover the original unmodified bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import tomllib

import agentops_native_probe_v5 as native
from check_agentops_effect_v2 import seed_snapshot
from check_agentops_http_v1 import check as check_wire
from check_agentops_linux_workspace_v5 import (
    ROOT, require, load, zero, verify_rows, linux_relative, trusted_module,
    stage_receipt, record, relative_file, referenced_records,
)
from inspect_agentops_runtime_v5 import CRITICAL

SEAL = ROOT / "docs/research/source-evidence/agentops-runtime-resume-v6/manifest.json"
PRIOR = ROOT / "runs/agentops-native-eligibility/linux-filesystem-v5"
REVALIDATION = "runs/agentops-native-eligibility/runtime-revalidation-v5"
NATIVE = "runs/agentops-native-eligibility/native-probe-v5"
HTTP = "runs/agentops-http-control/native-http-linux-v3"
SETUP = "runs/agentops-native-eligibility/dependencies-linux-v4"
RUNTIME = "external/runtime-agentops-linux-v4/venv/bin/python"
INSPECTOR = "scripts/inspect_agentops_runtime_v5.py"


def linux_path(root, relative):
    return str(PurePosixPath(root) / relative)


def interval(receipt):
    start, end = (datetime.fromisoformat(receipt[key])
                  for key in ("started_at_utc", "finished_at_utc"))
    require(start.tzinfo is not None and end.tzinfo is not None and start <= end,
            "Invalid capture interval")
    return start, end


def capture_receipt(exported, directory, label, argv, cwd):
    receipt = load(exported / directory / (label + ".json"))
    require(receipt.get("argv") == argv and receipt.get("cwd", cwd) == cwd,
            "Unexpected captured command/workspace")
    require(zero(receipt.get("returncode")) and receipt.get("timed_out") is False,
            "Capture did not complete successfully")
    interval(receipt)
    for suffix in ("stdout", "stderr"):
        expected = record(exported / directory / f"{label}.{suffix}.bin", exported)
        require(receipt.get(suffix) == expected, "Capture stream binding differs")
    return receipt


def package_integrity(run, expected_inputs, prior=PRIOR):
    execution, result, manifest = (load(run / name) for name in
                                  ("execution.json", "result.json", "export-manifest.json"))
    exported = run / "workspace"
    require(execution.get("schema_version") == result.get("schema_version") ==
            "agentops-linux-runtime-resume/6", "Unexpected resume schema")
    require(execution["inputs"] == expected_inputs, "Resume inputs differ from their seal")
    require(result.get("parent_inputs_unchanged") is True, "Parent input integrity failed")
    require(result.get("export_reference_failures") == [] and manifest["reference_failures"] == [],
            "Export references failed")
    linux_root = result["linux_workspace"]
    require(PurePosixPath(linux_root).is_absolute() and ".." not in PurePosixPath(linux_root).parts,
            "Invalid original Linux root")
    require(execution["linux_workspace"] == manifest["original_linux_root"] == linux_root
            and load(run / "linux-workspace.json")["path"] == linux_root, "Inconsistent Linux roots")
    prior_result, prior_manifest = load(prior / "result.json"), load(prior / "export-manifest.json")
    require(prior_result["status"] == "failed" and prior_result["native_result"] ==
            prior_result["http_result"] == "not_run", "Unexpected original attempt")
    require(prior_result["linux_workspace"] == prior_manifest["original_linux_root"] == linux_root,
            "Resume changed the original workspace identity")
    require(execution["prior_attempt"] == result["prior_attempt"] == record(prior / "result.json", ROOT)
            and execution["prior_export"] == record(prior / "export-manifest.json", ROOT),
            "Resume is not bound to the retained original failure")
    for field in ("installations", "live_model_calls", "research_gate_credit_added"):
        require(zero(result.get(field)), f"Unexpected {field}")
    require(result.get("qualified_second_domain") is False, "Unestablished domain qualification")
    interval(result)
    names = verify_rows(exported, manifest["files"], [row["path"] for row in expected_inputs])
    verify_rows(exported, expected_inputs)
    verify_rows(exported, prior_manifest["files"])
    actual = set()
    for path in exported.rglob("*"):
        require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(),
                "Materialized export link")
        if path.is_file():
            actual.add(path.relative_to(exported).as_posix())
    require(names == actual, "Export contains undeclared files")
    require(type(result["exported_files"]) is int and result["exported_files"] == len(names),
            "Export file count differs")
    require(type(manifest["bytes"]) is int and manifest["bytes"] ==
            sum(row["bytes"] for row in manifest["files"]), "Export byte count differs")
    for link in manifest.get("inert_symlinks", []):
        target = relative_file(exported, link["path"])
        require(link["path"] not in names and not target.exists(), "Inert link was materialized")
    return exported, result, manifest


def validators_for(exported, expected_inputs, linux_root):
    """Load trusted local validators; normalize only verified receipt operands."""
    sources = [row for row in expected_inputs if row["path"].startswith("external/agentops-c806b7f1/")]
    require(len(sources) == 421, "Expected original 421-file application source")

    def digest(path):
        path = Path(path).resolve()
        if not path.is_relative_to(exported.resolve()):
            require(path.is_relative_to(ROOT), "Validator path outside known roots")
            path = exported / path.relative_to(ROOT)
        return record(path, exported)

    def read(path):
        value = load(path)
        path = Path(path)
        if path == exported / REVALIDATION / "runtime-inspection.json":
            require(value.get("argv") == [linux_path(linux_root, RUNTIME), "-I",
                    linux_path(linux_root, INSPECTOR)], "Wrong original inspection command")
            value["argv"] = [str(exported / RUNTIME), "-I", str(exported / INSPECTOR)]
        elif path == exported / REVALIDATION / "managed-capability.json":
            require(value.get("argv", [])[:3] == [linux_path(linux_root, RUNTIME), "-I", "-c"],
                    "Wrong original managed interpreter command")
            value["argv"][0] = str(exported / RUNTIME)
        return value

    reader = SimpleNamespace(load_json=read, digest=digest, within=native.original.within,
        SOURCE=exported / "external/agentops-c806b7f1", NODEID=native.original.NODEID,
        PLUGIN=exported / "scripts/agentops_native_probe_v2_plugin.py",
        CHECKER=exported / "scripts/check_agentops_effect_v2.py",
        SPEC=exported / "docs/research/source-evidence/agentops-native-probe-v2/protocol.md",
        __file__=str(ROOT / "scripts/agentops_native_probe_v2.py"), source_inventory=lambda: sources)
    rebased = trusted_module("parent_native_resume_v6_check", "agentops_native_probe_v5.py")
    rebased.ROOT, rebased.RUNS = exported, exported / "runs/agentops-native-eligibility"
    rebased.RUNTIME, rebased.INSPECTOR = exported / RUNTIME, exported / INSPECTOR
    rebased.REVALIDATOR = exported / "scripts/revalidate_agentops_runtime_v5.py"
    rebased.original = reader
    http = trusted_module("parent_http_resume_v6_check", "agentops_http_control_v3.py")
    http.ROOT, http.PREREQUISITE = exported, exported / NATIVE
    http.native, http.evidence = rebased, reader
    return http, sources


def verify_runtime(exported, linux_root):
    inventory = load(exported / REVALIDATION / "runtime-inspection.stdout.bin")
    native.validate_inventory(inventory)
    prefix = "external/runtime-agentops-linux-v4/venv"
    require(inventory["python"] == [3, 13, 1] and all(type(v) is int for v in inventory["python"]),
            "Unexpected selected Python version")
    require(linux_relative(inventory["runtime_prefix"], linux_root) == prefix, "Wrong runtime prefix")
    executable = linux_relative(inventory["executable"], linux_root)
    require(PurePosixPath(executable).is_relative_to("external/runtime-agentops-linux-v4"),
            "Interpreter outside selected runtime")
    require(inventory["agentops_direct_url"] == {
        "url": (PurePosixPath(linux_root) / "external/agentops-c806b7f1/agents/python").as_uri(),
        "dir_info": {"editable": True}}, "Wrong original editable source URL")
    lock_path = exported / "external/agentops-c806b7f1/agents/python/uv.lock"
    require(inventory["lock"] == record(lock_path, exported), "Wrong original lock binding")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    pins = {(row["name"], row["version"]) for row in lock["package"]}
    versions = {}
    for package in inventory["packages"]:
        require(package["name"] not in versions and (package["name"], package["version"]) in pins,
                "Duplicate or unlocked runtime distribution")
        versions[package["name"]] = package["version"]
        relative_file(exported, package["location"])
        require(PurePosixPath(package["location"]).is_relative_to(prefix),
                "Distribution outside isolated runtime")
        for row in package["metadata_files"]:
            require(PurePosixPath(row["path"]).is_relative_to(prefix), "Metadata outside runtime")
    require(set(inventory["critical_locked_versions"]) == CRITICAL, "Critical package requirements omitted")
    for name, version in inventory["critical_locked_versions"].items():
        require(versions.get(name) == version and (name, version) in pins, "Missing critical package")
    site = next(row["location"] for row in inventory["packages"] if row["name"] == "google-adk")
    selected = [site + "/" + name for name in (
        "_pytest/tmpdir.py", "a2a/server/request_handlers/default_request_handler.py",
        "google/adk/a2a/executor/a2a_agent_executor.py", "starlette/testclient.py", "httpx/_client.py")]
    require([row["path"] for row in inventory["selected_sources"]] == selected,
            "Required installed boundary source inventory differs")
    for row in referenced_records(inventory):
        verify_rows(exported, [row])
    provider = inventory["fcntl_native"]
    providers = provider["provider_files"]
    require(provider["module"] == "fcntl" and providers and provider["provider_file"] == providers[0],
            "Missing native fcntl provider binding")
    verify_rows(exported, providers)
    for row in providers:
        require(PurePosixPath(row["path"]).is_relative_to("external/runtime-agentops-linux-v4"),
                "Native provider outside selected runtime")
    if provider["kind"] == "builtin":
        require(provider["origin"] == "built-in" and providers[0]["path"] == executable,
                "Built-in provider does not identify the recorded interpreter")
    else:
        require(provider["kind"] == "extension" and providers[0]["path"] ==
                linux_relative(provider["origin"], linux_root), "Wrong native extension binding")
    return inventory


def verify_revalidation(exported, linux_root, http, sources):
    binding = http.native.validate_setup()
    result = load(exported / REVALIDATION / "result.json")
    require(zero(result.get("installations")) and zero(result.get("application_requests"))
            and zero(result.get("live_model_calls")), "Unexpected revalidation side effects")
    previous = load(exported / SETUP / "result.json")
    require(previous.get("status") == "failed" and previous.get("stage") == "runtime-inspection"
            and previous.get("source_unchanged_after") is True and previous["source_files"] == sources,
            "Original setup failure/source differs")
    verify_rows(exported, previous["files"])
    sync = load(exported / SETUP / "locked-sync.json")
    require(sync["argv"] == [linux_path(linux_root, "external/runtime-agentops-linux-v4/uv"),
            "sync", "--locked", "--project", linux_path(linux_root, "external/agentops-c806b7f1/agents/python"),
            "--python", "3.13.1", "--python-preference", "only-managed"], "Unexpected original sync command")
    capture_receipt(exported, REVALIDATION, "runtime-inspection",
                    [linux_path(linux_root, RUNTIME), "-I", linux_path(linux_root, INSPECTOR)], linux_root)
    # Bind the complete managed probe, not merely an interpreter prefix.
    import ast
    tree = ast.parse((ROOT / "scripts/revalidate_agentops_runtime_v5.py").read_text(encoding="utf-8"))
    codes = [node.value.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "code" for target in node.targets)
             and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
    require(len(codes) == 1, "Cannot identify the approved managed capability command")
    capture_receipt(exported, REVALIDATION, "managed-capability",
                    [linux_path(linux_root, RUNTIME), "-I", "-c", codes[0],
                     linux_path(linux_root, REVALIDATION + "/managed-capability")], linux_root)
    inventory = verify_runtime(exported, linux_root)
    require(result["native_module_kind"] == inventory["fcntl_native"]["kind"]
            and result["package_count"] == len(inventory["packages"]), "Revalidation inventory summary differs")
    return binding, inventory


def ordered_stages(run, linux_root, stages):
    receipts = [stage_receipt(run, label, arguments, linux_root) for label, arguments in stages]
    for before, after in zip(receipts, receipts[1:]):
        require(interval(before)[1] <= interval(after)[0], "Controller stages overlap or are out of order")
    return receipts


def inspection_captures(exported, directory, linux_root):
    for label in ("prepared-runtime", "execution-runtime"):
        capture_receipt(exported, directory, label,
            [linux_path(linux_root, RUNTIME), "-I", linux_path(linux_root, INSPECTOR)], linux_root)


def native_process_captures(exported, linux_root, bootstrap):
    inspection_captures(exported, NATIVE, linux_root)
    project = linux_path(linux_root, "external/agentops-c806b7f1/agents/python")
    directory = linux_path(linux_root, NATIVE)
    capture_receipt(exported, NATIVE, "upstream-confirmation", [linux_path(linux_root, RUNTIME),
        "-B", "-m", "pytest", "-c", project + "/pyproject.toml", "-p", "agentops_native_probe_v2_plugin",
        "--basetemp", directory + "/pytest-temp", "-o", "cache_dir=" + directory + "/pytest-cache",
        "--junitxml", directory + "/junit.xml", native.original.NODEID], project)
    capture_receipt(exported, NATIVE, "independent-effect-check", [bootstrap, "-B",
        linux_path(linux_root, "scripts/check_agentops_effect_v2.py"), "--profile", directory + "/passive-profile.json",
        "--seed-db", linux_path(linux_root, "external/agentops-c806b7f1/agents/data/incidents.db"),
        "--output", directory + "/effect-check.json"], linux_root)


def check(run):
    expected = load(SEAL)["replica_inputs"]
    verify_rows(ROOT, expected)  # All executable validator inputs remain approved parent code.
    exported, result, manifest = package_integrity(run, expected)
    report = {"status": "artifact_integrity_verified", "recorded_attempt_status": result["status"],
        "files_checked": len(manifest["files"]), "runtime_revalidation": "not_rechecked",
        "native_semantics": "not_rechecked", "http_semantics": "not_rechecked",
        "fresh_experiment": False, "independent_semantic_oracle": False, "scientific_gate_credit_added": 0,
        "limitation": "Retained evidence consistency; not capture authenticity, full runtime authentication or scientific review"}
    passed_native = result["native_result"] == "upstream_and_boundary_effect_check_passed"
    passed_http = result["http_result"] == "wire_and_effect_check_passed"
    for field, folder in (("native_result", NATIVE), ("http_result", HTTP)):
        inner = exported / folder / "result.json"
        require(result[field] == (load(inner)["status"] if inner.exists() else "not_run"),
                "Outer outcome differs from retained inner result")
    require(not passed_http or passed_native, "HTTP success without native success")
    require(result["status"] != "native_and_http_controls_passed" or (passed_native and passed_http),
            "False overall success")
    revalidation_file = exported / REVALIDATION / "result.json"
    if not revalidation_file.exists() or load(revalidation_file).get("status") != "installed_runtime_revalidated":
        require(not passed_native and not passed_http, "Application success without runtime revalidation")
        return report
    stages = [("runtime-revalidation", ["scripts/revalidate_agentops_runtime_v5.py"])]
    ordered_stages(run, result["linux_workspace"], stages)
    http, sources = validators_for(exported, expected, result["linux_workspace"])
    _, inventory = verify_revalidation(exported, result["linux_workspace"], http, sources)
    report["runtime_revalidation"] = "verified_with_native_provider_bytes"
    if not passed_native:
        return report
    stages.extend([("native-prepare", ["scripts/agentops_native_probe_v5.py", "prepare"]),
                   ("native-control", ["scripts/agentops_native_probe_v5.py", "run"])])
    stage_rows = ordered_stages(run, result["linux_workspace"], stages)
    native_process_captures(exported, result["linux_workspace"], stage_rows[-1]["argv"][0])
    native_binding = http.validate_native(sources)  # Recomputes original effect semantics.
    native_result = load(exported / NATIVE / "result.json")
    require(zero(native_result.get("pytest_returncode")) and zero(native_result.get("live_model_calls")),
            "Invalid native result counters")
    report["native_semantics"] = "rechecked_with_existing_effect_checker"
    if not passed_http:
        return report
    stages.extend([("http-prepare", ["scripts/agentops_http_control_v3.py", "prepare"]),
                   ("http-control", ["scripts/agentops_http_control_v3.py", "run"])])
    stage_rows = ordered_stages(run, result["linux_workspace"], stages)
    directory = exported / HTTP
    outcome = load(directory / "result.json")
    require(outcome.get("schema_version") == "agentops-http-result/3" and zero(outcome.get("live_model_calls"))
            and outcome.get("status") == "wire_and_effect_check_passed"
            and outcome.get("source_unchanged_after") is True, "Unexpected HTTP result")
    require(outcome.get("forced_service_stop") is False and not outcome.get("cleanup_errors")
            and zero(outcome.get("service_returncode")), "HTTP service cleanup failed")
    verify_rows(exported, outcome["files"], [HTTP + "/" + name for name in (
        "plan.json", "preparation-result.json", "execution.json", "prepared-runtime.stdout.bin",
        "execution-runtime.stdout.bin", "check.json", "service-result.json")])
    plan = load(directory / "plan.json")
    require(plan.get("schema_version") == "agentops-http-plan/1"
            and plan.get("controller_version") == "agentops-http-control/3"
            and plan["source_files"] == sources and plan["harness_files"] == http.harness(inventory),
            "HTTP controller/source/harness differs")
    require(plan["native_prerequisite"] == native_binding
            and plan["runtime_inventory"] == record(directory / "prepared-runtime.stdout.bin", exported),
            "HTTP prerequisite/runtime binding differs")
    require(load(directory / "prepared-runtime.stdout.bin") == inventory
            and load(directory / "execution-runtime.stdout.bin") == inventory, "HTTP runtime changed")
    inspection_captures(exported, HTTP, result["linux_workspace"])
    require(load(directory / "preparation-result.json").get("status") == "prepared_not_executed",
            "HTTP preparation did not pass")
    execution = load(directory / "execution.json")
    require(execution.get("schema_version") == "agentops-http-execution/3"
            and execution["plan"] == record(directory / "plan.json", exported)
            and execution["native_prerequisite"] == native_binding, "HTTP execution binding differs")
    linux_directory = linux_path(result["linux_workspace"], HTTP)
    capture_receipt(exported, HTTP, "wire-check", [stage_rows[-1]["argv"][0], "-B",
        linux_path(result["linux_workspace"], "scripts/check_agentops_http_v1.py"),
        "--run", linux_directory, "--output", linux_directory + "/check.json"], result["linux_workspace"])
    semantic = check_wire(directory, seed_snapshot(exported / "external/agentops-c806b7f1/agents/data/incidents.db"))
    recorded = load(directory / "check.json")
    require(recorded.get("schema_version") == "agentops-http-check/1"
            and all(recorded.get(key) == value for key, value in semantic.items()), "Stored HTTP semantic report differs")
    for row in recorded["inputs"]:
        if row["path"] not in {"wire-check.stdout.bin", "wire-check.stderr.bin"}:
            require(record(relative_file(directory, row["path"]), directory)["sha256"] == row["sha256"],
                    "Stable HTTP checker input changed")
    report.update(status="artifact_integrity_and_semantics_verified", http_semantics=semantic,
        checker_stream_limit="Stored checker input hashes predate its stdout; terminal file hashes are checked")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "runs/agentops-native-eligibility/linux-runtime-resume-v6")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Never overwrite an earlier audit")
    report = {"schema_version": "agentops-runtime-resume-recheck/6", "status": "failed"}
    try:
        report.update(check(args.run.resolve()))
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["status"] == "failed" else 0)
