"""Audit exported dependency declarations/snapshots without executing sources/pip."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "runs/ap2-dependency-resolution/input-v1"
OUT = ROOT / "runs/ap2-dependency-resolution/input-v1-independent-review.json"
PENDING = OUT.with_suffix(".json.pending")
if OUT.exists() or PENDING.exists():
    raise FileExistsError("Independent input review allocation consumed")
def desc(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
def inventory():
    return {path.relative_to(BASE).as_posix(): desc(path.read_bytes()) for path in sorted(BASE.rglob("*")) if path.is_file()}
checks = []
def check(name, value):
    checks.append({"name": name, "passed": bool(value)})
before = inventory()
result = json.loads((BASE / "result.json").read_bytes())
record = json.loads((BASE / "source-descriptors.json").read_bytes())
check("result_schema_status", result.get("schema_version") == "ap2-dependency-input-export-result/1" and result.get("status") == "prepared_source_derived_inputs")
check("descriptor_schema", record.get("schema_version") == "ap2-source-derived-dependency-inputs/1")
check("manifest_exact_allocation_membership", set(before) == {row["file"] for row in result["outputs"]} | {"result.json"})
check("nine_unique_manifest_outputs", len(result["outputs"]) == len({row["file"] for row in result["outputs"]}) == 9)
for row in result["outputs"]:
    check("manifest:" + row["file"], before.get(row["file"]) == {key: row[key] for key in ("bytes", "sha256")})
snapshot_objects = {}
current_before = {}
check("five_unique_snapshot_bindings", len(result["inputs"]) == len({row["file"] for row in result["inputs"]}) == len({row["snapshot"] for row in result["inputs"]}) == 5)
for row in result["inputs"]:
    current = desc((ROOT / row["file"]).read_bytes())
    captured = desc((BASE / row["snapshot"]).read_bytes())
    current_before[row["file"]] = current
    check("current_snapshot_binding:" + row["file"], current == captured and current["sha256"] == row["sha256"] and row["unchanged"] is True)
    snapshot_objects[row["file"]] = (BASE / row["snapshot"]).read_bytes()
exporter = ROOT / "scripts/prepare_ap2_dependency_inputs_v1.py"
exporter_before = desc(exporter.read_bytes())
check("exact_frozen_current_captured_exporter", exporter_before == desc((BASE / "prepare-script.py").read_bytes()) and exporter_before["sha256"] == result["exporter_sha256"] == "290acf02c2ccb8ee666f1d74e99b0a0d376ffaa448dc5e31491ed2d503d527a8")

ap2_manifest_path = "docs/research/source-evidence/ap2-procurement-screen-v1/source-result.json"
x_manifest_path = "docs/research/source-evidence/ap2-x402-package-v1/manifest.json"
ap2_manifest = json.loads(snapshot_objects[ap2_manifest_path])
x_manifest = json.loads(snapshot_objects[x_manifest_path])
ap2_pin = "e1ea56db72a6385bce3e5c1112b3a56ce60acb43"
x_pin = "125db5526a965d2325459d1a9df2e274a7e42396"
check("original_source_pin", ap2_manifest["commit"] == ap2_pin)
check("selected_complete_x402_manifest", x_manifest["commit"] == x_pin and x_manifest["status"] == "complete_selected_package_source" and x_manifest["package_file_coverage_complete"] is True and desc(snapshot_objects[x_manifest_path])["sha256"] == "74db7661df834b7d05371d84aa4a6f0e6d9d243f344204923cef65e15b449d07")
projects = (
    ("ap2", "docs/research/source-evidence/ap2-procurement-screen-v1/source/pyproject.toml", ap2_pin, ".", "pyproject.toml"),
    ("ap2-samples", "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/samples/python/pyproject.toml", ap2_pin, "code/samples/python", "code/samples/python/pyproject.toml"),
    ("x402-a2a", "docs/research/source-evidence/ap2-x402-package-v1/source/python/x402_a2a/pyproject.toml", x_pin, "python/x402_a2a", "python/x402_a2a/pyproject.toml"),
)
floating = "x402-a2a @ git+https://github.com/google-agentic-commerce/a2a-x402.git#subdirectory=python/x402_a2a"
runtime, builds, local = [], [], []
check("three_ordered_local_source_descriptors", [value["project"] for value in record["local_source_projects"]] == [value[0] for value in projects])
for (name, path, pin, subdirectory, entry_path), supplied in zip(projects, record["local_source_projects"]):
    body = snapshot_objects[path]
    data = tomllib.loads(body.decode("utf-8"))
    entries = {entry["path"]: entry for entry in (x_manifest if name == "x402-a2a" else ap2_manifest)["files"]}
    check("pyproject_retained_source_entry:" + name, desc(body)["sha256"] == entries[entry_path]["sha256"])
    check("descriptor_exact_project_identity:" + name, supplied["project"] == data["project"]["name"] == name and supplied["version"] == data["project"]["version"] and supplied["requires_python"] == data["project"]["requires-python"] and supplied["commit"] == pin and supplied["subdirectory"] == subdirectory and supplied["pyproject"] == path and supplied["pyproject_sha256"] == desc(body)["sha256"])
    check("descriptor_preserves_original_requirements:" + name, supplied["original_runtime_dependencies"] == data["project"]["dependencies"] and supplied["build_system"] == data["build-system"])
    expected_tool = {key: value for key, value in data.get("tool", {}).items() if key in {"setuptools", "hatch", "uv"}}
    check("source_build_config_preserved:" + name, supplied["source_build_configuration"] == expected_tool)
    for ordinal, requirement in enumerate(data["project"]["dependencies"], 1):
        base = {"source_project": name, "source_ordinal": ordinal, "original_requirement": requirement}
        if name == "ap2-samples" and requirement in {"ap2", floating}:
            base["selected_project"] = "ap2" if requirement == "ap2" else "x402-a2a"
            base["selected_commit"] = ap2_pin if requirement == "ap2" else x_pin
            local.append(base)
        else:
            runtime.append(base)
    for ordinal, requirement in enumerate(data["build-system"]["requires"], 1):
        builds.append({"source_project": name, "source_ordinal": ordinal, "original_requirement": requirement})
check("25_exact_runtime_trace_rows", len(runtime) == result["runtime_requirement_count"] == 25 and [{key: row[key] for key in ("source_project", "source_ordinal", "original_requirement")} for row in record["indexed_runtime_requirement_rows"]] == runtime)
check("all_runtime_classifications_indexed", all(row["classification"] == "indexed_runtime" for row in record["indexed_runtime_requirement_rows"]))
check("two_exact_local_edges_only", len(local) == result["local_source_edges"] == 2 and [{key: row[key] for key in ("source_project", "source_ordinal", "original_requirement", "selected_project", "selected_commit")} for row in record["local_source_dependency_edges"]] == local)
check("three_exact_separate_build_rows", len(builds) == result["separate_build_requirement_count"] == 3 and [{key: row[key] for key in ("source_project", "source_ordinal", "original_requirement")} for row in record["separate_build_requirement_rows"]] == builds)
def requirements(path):
    return [line for line in (BASE / path).read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
check("runtime_text_exact_order_duplicates", requirements("indexed-runtime-requirements.txt") == [row["original_requirement"] for row in runtime])
check("build_text_exact_order_duplicates", requirements("separate-build-requirements.txt") == [row["original_requirement"] for row in builds])
check("no_local_direct_source_in_index_runtime", not any(" @ " in value or value == "ap2" for value in requirements("indexed-runtime-requirements.txt")))
check("root_declared_pytest_retained", "pytest==9.0.2" in requirements("indexed-runtime-requirements.txt"))
check("dev_lint_not_silently_runtime", record["dev_and_lint_groups_included"] is False)
check("original_overlap_preserved", record["duplicate_requirements_preserved"] is True and record["original_exact_and_broad_requirements_preserved"] is True)
target = record["target"]
check("exact_target_bound", target == result["target"] and target["os"] == "Windows" and target["python_version"] == "3.13" and target["pip_platform"] == "win_amd64" and target["pip_implementation"] == "cp" and target["pip_abi"] == "cp313" and target["pointer_bits"] == 64 and target["native_interpreter"]["machine"].lower() in {"amd64", "x86_64"})
expected_argv = [target["native_interpreter"]["executable"], "-I", "-m", "pip", "--isolated", "install", "--dry-run", "--ignore-installed", "--only-binary=:all:", "--index-url", "https://pypi.org/simple", "--platform", "win_amd64", "--implementation", "cp", "--python-version", "3.13", "--abi", "cp313", "--report", str(BASE.parent / "windows-cp313-dry-run-v1/pip-report.json"), "-r", str(BASE / "indexed-runtime-requirements.txt")]
check("exact_prospective_binary_only_pip_argv", record["prospective_indexed_dry_run_argv"] == expected_argv)
for key in ("prospective_command_executed", "complete_runtime_lock_established", "source_wheels_built", "environment_installed", "source_imported", "native_application_executed"):
    check("descriptor_no_upgrade:" + key, record[key] is False)
for key in ("resolver_executed", "source_wheels_built", "environment_installed", "acquired_source_imported", "native_application_executed"):
    check("receipt_no_upgrade:" + key, result[key] is False)
check("recorded_export_network_model_zero", type(result["network_requests"]) is int and type(result["model_requests"]) is int and result["network_requests"] == result["model_requests"] == 0)
check("allocation_preserved_during_review", inventory() == before)
for path, expected in current_before.items():
    check("original_input_preserved:" + path, desc((ROOT / path).read_bytes()) == expected)
check("exporter_preserved", desc(exporter.read_bytes()) == exporter_before)
report = {
    "schema_version": "ap2-dependency-input-independent-review/1",
    "status": "verified_source_input_export" if all(row["passed"] for row in checks) else "failed",
    "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "reviewer": "separate_AI_agent_method_next_step",
    "result_digest": before["result.json"], "capture_files": before, "current_source_inputs": current_before,
    "exporter_digest": exporter_before, "reviewer_script_digest": desc(Path(__file__).read_bytes()),
    "checks_passed": sum(row["passed"] for row in checks), "checks": checks,
    "discrepancies": [row["name"] for row in checks if not row["passed"]],
    "indexed_runtime_rows": runtime, "local_edges": local, "separate_build_rows": builds,
    "resolver_executed_by_reviewer": False, "source_imports_by_reviewer": 0, "installation_by_reviewer": False,
    "native_or_model_requests_by_reviewer": 0,
    "additional_runtime_constraint": "Actual future pip driver must set child PIP_CONFIG_FILE=os.devnull to suppress global/site config as well as Python -I and pip --isolated; the immutable prepared argv alone does not clear global extra-index/find-links config.",
    "scope": "Retained source declarations, exact row/order/overlap/local-edge/build split, snapshots, input/output/current hashes and preservation only. No pip/resolver, package metadata/build/import/install/native/model execution. No combined lock, local wheels, installed environment, compatibility, loaded-source workflow, quota or domain/scientific qualification. Zero execution fields are preparation-time recorder assertions and source-scope limits."
}
with PENDING.open("xb") as stream:
    stream.write((json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    stream.flush()
    os.fsync(stream.fileno())
os.link(PENDING, OUT)
PENDING.unlink()
print(json.dumps({"status": report["status"], "checks_passed": report["checks_passed"], "discrepancies": report["discrepancies"], "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest()}))
