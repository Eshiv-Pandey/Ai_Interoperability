"""Read-only integrity and semantic recheck of an exported Linux v5 attempt.

Uses trusted parent-side validators with rebased data readers. Never imports
exported code or executes the app, installer, WSL, or a network request. This is
artifact revalidation, not a fresh experiment or independently authored oracle.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
from types import SimpleNamespace
import tomllib

import agentops_native_probe_v4 as native
from check_agentops_effect_v2 import seed_snapshot
from check_agentops_http_v1 import check as check_wire
from inspect_agentops_runtime_v4 import CRITICAL
from run_agentops_linux_workspace_v5 import record, relative_file, referenced_records

ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / "docs/research/source-evidence/agentops-linux-filesystem-v5/manifest.json"
NATIVE = "runs/agentops-native-eligibility/native-probe-v4"
HTTP = "runs/agentops-http-control/native-http-linux-v2"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object)


def zero(value):
    return type(value) is int and value == 0


def verify_rows(base, rows, required=()):
    names = set()
    folded = set()
    for row in rows:
        require(set(row) == {"path", "bytes", "sha256"}, "Unexpected file-record fields")
        name = row["path"]
        require(isinstance(name, str) and name not in names and name.casefold() not in folded,
                "Duplicate or Windows-colliding file record")
        require(type(row["bytes"]) is int and row["bytes"] >= 0, "Invalid recorded byte length")
        require(isinstance(row["sha256"], str) and re.fullmatch("[a-f0-9]{64}", row["sha256"]), "Invalid SHA-256")
        path = relative_file(base, name)
        for ancestor in (path, *path.parents):
            if ancestor == base:
                break
            require(not getattr(ancestor, "is_junction", lambda: False)(), "Junction in evidence path")
        require(record(path, base) == row, f"Changed/missing file: {name}")
        names.add(name)
        folded.add(name.casefold())
    require(set(required) <= names, "Mandatory file omitted from retained inventory")
    return names


def linux_relative(name, linux_root):
    path, base = PurePosixPath(name), PurePosixPath(linux_root)
    require(path.is_absolute() and base.is_absolute() and ".." not in path.parts, "Invalid absolute Linux path")
    try:
        relative = path.relative_to(base)
    except ValueError as error:
        raise ValueError("Absolute Linux path lies outside execution workspace") from error
    require(bool(relative.parts), "Expected a path below the Linux workspace")
    return relative.as_posix()


def package_integrity(run, expected_inputs):
    execution = load(run / "execution.json")
    result = load(run / "result.json")
    manifest = load(run / "export-manifest.json")
    exported = run / "workspace"
    require(execution["inputs"] == expected_inputs, "Execution inputs differ from approved replica input seal")
    require(result.get("parent_inputs_unchanged") is True, "Parent input integrity did not pass")
    require(result.get("export_reference_failures") == [] and manifest["reference_failures"] == [], "Export references failed")
    require(manifest["original_linux_root"] == result["linux_workspace"], "Inconsistent original Linux roots")
    location = load(run / "linux-workspace.json")
    require(location["path"] == result["linux_workspace"], "Linux workspace location receipt differs")
    require(result["schema_version"] == "agentops-linux-filesystem-attempt/5", "Unexpected attempt schema")
    names = verify_rows(exported, manifest["files"], [row["path"] for row in expected_inputs])
    verify_rows(exported, expected_inputs)
    actual = set()
    for path in exported.rglob("*"):
        require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(), "Materialized export link")
        if path.is_file():
            actual.add(path.relative_to(exported).as_posix())
    require(actual == names, "Export contains undeclared files")
    for link in manifest.get("inert_symlinks", []):
        relative_file(exported, link["path"])
        require(link["path"] not in names and not (exported / link["path"]).exists(), "Inert link materialized or overlaps a file")
    require(result["exported_files"] == len(names), "Export file count differs")
    require(manifest["bytes"] == sum(row["bytes"] for row in manifest["files"]), "Export byte count differs")
    return exported, result, manifest


def trusted_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validators_for(exported, expected_inputs):
    """Rebase data reads only; load all executable validator code from parent."""
    source_rows = [row for row in expected_inputs if row["path"].startswith("external/agentops-c806b7f1/")]
    require(len(source_rows) == 421, "Expected the approved original 421-file source set")

    def digest(path):
        path = Path(path).resolve()
        if not path.is_relative_to(exported.resolve()):
            require(path.is_relative_to(ROOT), "Validator path lies outside known roots")
            path = exported / path.relative_to(ROOT)
        return record(path, exported)

    reader = SimpleNamespace(load_json=load, digest=digest, within=native.original.within,
                             SOURCE=exported / "external/agentops-c806b7f1", NODEID=native.original.NODEID,
                             source_inventory=lambda: source_rows)
    rebased_native = trusted_module("parent_native_v5_recheck", "agentops_native_probe_v4.py")
    rebased_native.ROOT = exported
    rebased_native.RUNS = exported / "runs/agentops-native-eligibility"
    rebased_native.RUNTIME = exported / "external/runtime-agentops-linux-v4/venv/bin/python"
    rebased_native.original = reader
    # These hashes come from the unchanged parent-side approved native harness.
    rebased_native.harness = native.harness
    rebased_native.validate_pytest_reports = native.validate_pytest_reports
    http = trusted_module("parent_http_v5_recheck", "agentops_http_control_v2.py")
    http.ROOT = exported
    http.PREREQUISITE = exported / NATIVE
    http.native = rebased_native
    http.evidence = reader
    return http, source_rows


def stage_receipt(run, label, arguments, linux_root):
    receipt = load(run / f"{label}.json")
    started = load(run / f"{label}.started.json")
    require(receipt["cwd"] == linux_root and receipt["argv"][1:] == ["-B", "-X", "utf8", *arguments], "Unexpected controller command/workspace")
    require(all(receipt.get(key) == value for key, value in started.items() if key != "timed_out"), "Launch/completion receipt mismatch")
    require(zero(receipt.get("returncode")) and receipt.get("timed_out") is False, "Controller did not complete successfully")
    require(type(receipt.get("linux_pid")) is int and receipt["linux_pid"] > 0, "Invalid recorded process ID")
    start, finish = (datetime.fromisoformat(receipt[key]) for key in ("started_at_utc", "finished_at_utc"))
    require(start.tzinfo is not None and finish.tzinfo is not None and start <= finish, "Invalid controller interval")
    verify_rows(run, receipt["streams"], [f"{label}.stdout.bin", f"{label}.stderr.bin"])
    return receipt


def verify_runtime(exported, linux_root):
    inventory = load(exported / NATIVE / "prepared-runtime.stdout.bin")
    prefix = "external/runtime-agentops-linux-v4/venv"
    require(inventory["python"] == [3, 13, 1] and all(type(value) is int for value in inventory["python"]), "Unexpected selected Python version")
    require(linux_relative(inventory["runtime_prefix"], linux_root) == prefix, "Unexpected runtime prefix")
    require(PurePosixPath(linux_relative(inventory["executable"], linux_root)).is_relative_to("external/runtime-agentops-linux-v4"), "Interpreter outside selected runtime")
    require(inventory["agentops_direct_url"] == {
        "url": (PurePosixPath(linux_root) / "external/agentops-c806b7f1/agents/python").as_uri(),
        "dir_info": {"editable": True}}, "Wrong original editable source URL")
    lock = tomllib.loads((exported / "external/agentops-c806b7f1/agents/python/uv.lock").read_text(encoding="utf-8"))
    pins = {(row["name"], row["version"]) for row in lock["package"]}
    versions = {}
    for package in inventory["packages"]:
        require(package["name"] not in versions and (package["name"], package["version"]) in pins, "Duplicate or unlocked runtime distribution")
        versions[package["name"]] = package["version"]
        require(PurePosixPath(package["location"]).is_relative_to(prefix), "Distribution outside isolated runtime")
    require(set(inventory["critical_locked_versions"]) == CRITICAL, "Critical package requirements omitted")
    for name, version in inventory["critical_locked_versions"].items():
        require(versions.get(name) == version, "Missing critical runtime package")
    for row in referenced_records(inventory):
        verify_rows(exported, [row])
    fcntl = inventory["fcntl_extension"]
    path = relative_file(exported, linux_relative(fcntl["path"], linux_root))
    require(record(path, exported)["sha256"] == fcntl["sha256"], "Native fcntl snapshot differs")
    return inventory


def check(run):
    expected = load(SEAL)["replica_inputs"]
    exported, result, manifest = package_integrity(run, expected)
    report = {"status": "artifact_integrity_verified", "recorded_attempt_status": result["status"],
              "files_checked": len(manifest["files"]), "native_semantics": "not_rechecked",
              "http_semantics": "not_rechecked", "fresh_experiment": False,
              "independent_semantic_oracle": False, "scientific_gate_credit_added": 0}
    if result["native_result"] != "upstream_and_boundary_effect_check_passed":
        require(result["status"] != "native_and_http_controls_passed" and result["http_result"] == "not_run", "False success or HTTP without native success")
        report["limitation"] = "Retained failed/partial attempt; no native or HTTP success established"
        return report
    native_stage = stage_receipt(run, "native-pipeline", ["scripts/run_agentops_linux_v4.py"], result["linux_workspace"])
    http, sources = validators_for(exported, expected)
    native_result = http.validate_native(sources)
    inventory = verify_runtime(exported, result["linux_workspace"])
    report["native_semantics"] = "rechecked_with_existing_effect_checker"
    if result["http_result"] != "wire_and_effect_check_passed":
        require(result["status"] != "native_and_http_controls_passed", "False HTTP success")
        return report
    prepare_stage = stage_receipt(run, "http-prepare", ["scripts/agentops_http_control_v2.py", "prepare"], result["linux_workspace"])
    http_stage = stage_receipt(run, "http-control", ["scripts/agentops_http_control_v2.py", "run"], result["linux_workspace"])
    require(datetime.fromisoformat(native_stage["finished_at_utc"]) <= datetime.fromisoformat(prepare_stage["started_at_utc"])
            and datetime.fromisoformat(prepare_stage["finished_at_utc"]) <= datetime.fromisoformat(http_stage["started_at_utc"]), "Controller stages overlap or are out of order")
    directory = exported / HTTP
    outcome = load(directory / "result.json")
    require(outcome.get("schema_version") == "agentops-http-result/2" and zero(outcome.get("live_model_calls")), "Unexpected HTTP result schema/model usage")
    require(outcome["status"] == "wire_and_effect_check_passed" and outcome["source_unchanged_after"] is True, "HTTP outcome differs")
    require(not outcome.get("forced_service_stop") and not outcome.get("cleanup_errors"), "HTTP service cleanup was not clean")
    verify_rows(exported, outcome["files"], [HTTP + "/" + name for name in (
        "plan.json", "preparation-result.json", "execution.json", "prepared-runtime.stdout.bin",
        "execution-runtime.stdout.bin", "check.json", "service-result.json")])
    plan = load(directory / "plan.json")
    require(plan["controller_version"] == "agentops-http-control/2" and plan["source_files"] == sources, "Wrong HTTP controller/source")
    require(plan["native_prerequisite"] == native_result and plan["harness_files"] == http.harness(inventory), "HTTP prerequisite/harness differs")
    require(load(directory / "prepared-runtime.stdout.bin") == inventory, "HTTP and native runtimes differ")
    require(load(directory / "execution-runtime.stdout.bin") == inventory, "HTTP runtime changed at execution")
    require(load(directory / "preparation-result.json")["status"] == "prepared_not_executed", "HTTP preparation failed")
    require(load(directory / "execution.json")["plan"] == record(directory / "plan.json", exported), "HTTP execution does not bind its plan")
    semantic = check_wire(directory, seed_snapshot(exported / "external/agentops-c806b7f1/agents/data/incidents.db"))
    # The original checker records these streams before it prints to stdout.
    # Terminal hashes above and fresh semantic evaluation cover final bytes.
    volatile = {"wire-check.stdout.bin", "wire-check.stderr.bin"}
    recorded_check = load(directory / "check.json")
    require(recorded_check.get("status") == "passed", "Stored HTTP check did not pass")
    for item in recorded_check.get("inputs", []):
        if item["path"] not in volatile:
            path = relative_file(directory, item["path"])
            require(record(path, directory)["sha256"] == item["sha256"], "Stable HTTP checker input changed")
    report.update(status="artifact_integrity_and_semantics_verified", http_semantics=semantic,
                  checker_stream_limit="check.json inputs predate its own stdout; terminal result.files hashes used",
                  limitation="Consistent retained evidence; not independent capture authenticity, fresh replay or scientific review")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "runs/agentops-native-eligibility/linux-filesystem-v5")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Never overwrite an earlier audit")
    report = {"schema_version": "agentops-linux-export-recheck/1", "status": "failed"}
    try:
        report.update(check(args.run.resolve()))
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["status"] == "failed" else 0)
