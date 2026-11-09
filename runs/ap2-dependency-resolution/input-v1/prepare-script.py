"""Export source-derived AP2 runtime/build inputs without resolving or executing sources."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import sys
import tomllib


WORKSPACE = Path(__file__).resolve().parents[1]
AP2 = WORKSPACE / "docs/research/source-evidence/ap2-procurement-screen-v1"
X402 = WORKSPACE / "docs/research/source-evidence/ap2-x402-package-v1"
AP2_PIN = "e1ea56db72a6385bce3e5c1112b3a56ce60acb43"
X402_PIN = "125db5526a965d2325459d1a9df2e274a7e42396"
FLOATING_X402 = "x402-a2a @ git+https://github.com/google-agentic-commerce/a2a-x402.git#subdirectory=python/x402_a2a"


def sha(body):
    return hashlib.sha256(body).hexdigest()


def relative(path):
    return path.relative_to(WORKSPACE).as_posix()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def export(output):
    output = output.resolve()
    output.relative_to(WORKSPACE)
    if output.exists():
        raise ValueError("Output namespace already exists; use a new prospective allocation.")
    if not (os.name == "nt" and sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 13) and struct.calcsize("P") == 8 and platform.machine().lower() in {"amd64", "x86_64"}):
        raise ValueError("This export targets native 64-bit Windows CPython 3.13.")
    original_manifest_body = (AP2 / "source-result.json").read_bytes()
    original_manifest = json.loads(original_manifest_body)
    x402_manifest_body = (X402 / "manifest.json").read_bytes()
    x402_manifest = json.loads(x402_manifest_body)
    if original_manifest["commit"] != AP2_PIN:
        raise ValueError("Unexpected original AP2 source pin.")
    if not (sha(x402_manifest_body) == "74db7661df834b7d05371d84aa4a6f0e6d9d243f344204923cef65e15b449d07" and x402_manifest["commit"] == X402_PIN and x402_manifest["status"] == "complete_selected_package_source" and x402_manifest["package_file_coverage_complete"] is True):
        raise ValueError("Exact complete selected x402 source manifest is not verified.")
    original_entries = {entry["path"]: entry for entry in original_manifest["files"]}
    x402_entries = {entry["path"]: entry for entry in x402_manifest["files"]}
    source_records = [
        ("ap2", AP2 / "source/pyproject.toml", AP2_PIN, "https://github.com/google-agentic-commerce/AP2", ".", "pyproject.toml"),
        ("ap2-samples", AP2 / "source/code/samples/python/pyproject.toml", AP2_PIN, "https://github.com/google-agentic-commerce/AP2", "code/samples/python", "code/samples/python/pyproject.toml"),
        ("x402-a2a", X402 / "source/python/x402_a2a/pyproject.toml", X402_PIN, "https://github.com/google-agentic-commerce/a2a-x402", "python/x402_a2a", "python/x402_a2a/pyproject.toml"),
    ]
    captured_inputs = {}
    for path, body in ((AP2 / "source-result.json", original_manifest_body), (X402 / "manifest.json", x402_manifest_body)):
        captured_inputs[relative(path)] = {"sha256": sha(body), "body": body}
    descriptors = []
    rows = []
    build_rows = []
    local_edges = []
    for name, path, pin, repository, subdirectory, source_path in source_records:
        body = path.read_bytes()
        registry = x402_entries if name == "x402-a2a" else original_entries
        expected = registry[source_path]
        if sha(body) != expected["sha256"]:
            raise ValueError("Source pyproject differs from its retained pin: " + name)
        data = tomllib.loads(body.decode("utf-8"))
        project = data["project"]
        if project["name"] != name:
            raise ValueError("Unexpected source project name.")
        if name == "ap2" and not (data["tool"]["setuptools"]["packages"]["find"]["where"] == ["code/sdk/python"] and data["tool"]["uv"]["workspace"]["members"] == ["code/samples/python"]):
            raise ValueError("Unexpected original SDK workspace/build mapping.")
        if name == "ap2-samples" and not (data["tool"]["uv"]["sources"]["ap2"] == {"workspace": True} and FLOATING_X402 in project["dependencies"]):
            raise ValueError("Unexpected original sample source references.")
        dependencies = project["dependencies"]
        if not isinstance(dependencies, list) or any(not isinstance(requirement, str) or not requirement or "\n" in requirement or "\r" in requirement for requirement in dependencies):
            raise ValueError("Malformed original runtime requirements.")
        for ordinal, requirement in enumerate(dependencies, 1):
            row = {"source_project": name, "source_ordinal": ordinal, "original_requirement": requirement}
            if name == "ap2-samples" and requirement == "ap2":
                row.update({"classification": "local_source_bound", "selected_project": "ap2", "selected_commit": AP2_PIN, "reason": "Original sample workspace dependency; not an index distribution."})
                local_edges.append(row)
            elif name == "ap2-samples" and requirement == FLOATING_X402:
                row.update({"classification": "local_source_bound", "selected_project": "x402-a2a", "selected_commit": X402_PIN, "selected_subdirectory": "python/x402_a2a", "reason": "Disclosed immutable preparation selection of the original floating direct source; original declaration unchanged."})
                local_edges.append(row)
            else:
                if " @ " in requirement:
                    raise ValueError("Unexpected direct source requirement; do not turn it into an indexed input.")
                row["classification"] = "indexed_runtime"
                rows.append(row)
        build_system = data["build-system"]
        for ordinal, requirement in enumerate(build_system["requires"], 1):
            if not isinstance(requirement, str) or not requirement or "\n" in requirement or "\r" in requirement:
                raise ValueError("Malformed original build requirement.")
            build_rows.append({"source_project": name, "source_ordinal": ordinal, "original_requirement": requirement, "classification": "indexed_build_backend_separate_from_runtime"})
        descriptors.append({"project": name, "version": project["version"], "requires_python": project["requires-python"], "repository": repository, "commit": pin, "subdirectory": subdirectory, "pyproject": relative(path), "pyproject_sha256": sha(body), "original_runtime_dependencies": dependencies, "build_system": build_system, "source_build_configuration": {key: value for key, value in data.get("tool", {}).items() if key in {"setuptools", "hatch", "uv"}}, "source_input_scope": "Exact pinned pyproject with selected package source; no build/import/metadata execution", "package_completeness": "complete_23_file_selected_subtree" if name == "x402-a2a" else "complete_build_asset_staging_not_verified_by_this_export"})
        captured_inputs[relative(path)] = {"sha256": sha(body), "body": body}
    target = {"os": "Windows", "implementation": "CPython", "python_version": "3.13", "pip_platform": "win_amd64", "pip_implementation": "cp", "pip_python_version": "3.13", "pip_abi": "cp313", "pointer_bits": 64, "native_interpreter": {"executable": sys.executable, "version": sys.version, "machine": platform.machine(), "platform": sys.platform}}
    runtime_lines = ["# Source-derived indexed runtime union only; three local packages remain source-bound.", "# Original order, duplicate requirements and version overlap are intentionally preserved."]
    for descriptor in descriptors:
        runtime_lines.append("\n# " + descriptor["project"] + " at " + descriptor["commit"] + " / " + descriptor["subdirectory"])
        runtime_lines.extend(row["original_requirement"] for row in rows if row["source_project"] == descriptor["project"])
    build_lines = ["# Build-system requirements only; this is not part of indexed runtime resolution.", "# Original duplicate backends remain visible and must be frozen separately."]
    for row in build_rows:
        build_lines.extend(["# " + row["source_project"], row["original_requirement"]])
    requirements = ("\n".join(runtime_lines) + "\n").encode("utf-8")
    build_requirements = ("\n".join(build_lines) + "\n").encode("utf-8")
    prospective_report = output.parent / "windows-cp313-dry-run-v1" / "pip-report.json"
    prospective_argv = [sys.executable, "-I", "-m", "pip", "--isolated", "install", "--dry-run", "--ignore-installed", "--only-binary=:all:", "--index-url", "https://pypi.org/simple", "--platform", "win_amd64", "--implementation", "cp", "--python-version", "3.13", "--abi", "cp313", "--report", str(prospective_report), "-r", str(output / "indexed-runtime-requirements.txt")]
    descriptor = {"schema_version": "ap2-source-derived-dependency-inputs/1", "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "target": target, "local_source_projects": descriptors, "indexed_runtime_requirement_rows": rows, "local_source_dependency_edges": local_edges, "separate_build_requirement_rows": build_rows, "duplicate_requirements_preserved": True, "original_exact_and_broad_requirements_preserved": True, "dev_and_lint_groups_included": False, "dev_and_lint_exclusion_reason": "Only original project.dependencies runtime declarations form this union; root AP2 pytest remains included because it is a project dependency.", "prospective_indexed_dry_run_argv": prospective_argv, "prospective_command_executed": False, "complete_runtime_lock_established": False, "source_wheels_built": False, "environment_installed": False, "source_imported": False, "native_application_executed": False, "model_requests": 0, "remaining": ["Run one separately allocated explicit-public-PyPI binary-only indexed runtime dry-run and retain either complete report or exact failure", "Freeze resolved indexed wheel URLs/hashes/versions, transitive metadata, markers and target platform if resolution succeeds", "Resolve/freeze separate build backend and tool requirements", "Verify complete AP2 SDK/sample build-asset staging and build all three local wheels from exact selected sources", "Compare local wheel metadata/runtime requirements with these original declarations and record wheel/build provenance", "Install only frozen compatible local/indexed wheels into a fresh isolated environment and retain installer report", "Verify source-faithful original role imports/bootstrap; native scenario requires unchanged prospective resource gate"], "claim_limits": ["Requirements export only; no resolver/network/build/install/acquired-source import/native/model execution", "Indexed closure resolution does not build, install or validate the three source-bound local packages", "The original x402 upstream lock is not adopted; immutable source selection is a disclosed preparation decision", "No combined environment, runtime compatibility, source-authenticated workflow, domain or checkpoint credit"]}
    outputs = {"indexed-runtime-requirements.txt": requirements, "separate-build-requirements.txt": build_requirements, "source-descriptors.json": json_bytes(descriptor), "prepare-script.py": Path(__file__).read_bytes()}
    for index, record in enumerate(captured_inputs.values(), 1):
        outputs[f"input-snapshots/{index:02d}.source"] = record["body"]
    for path_string, record in captured_inputs.items():
        if sha((WORKSPACE / path_string).read_bytes()) != record["sha256"]:
            raise ValueError("A source input changed during export preparation.")
    output.mkdir(parents=True)
    output_rows = []
    for name, body in outputs.items():
        target_path = output / name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("xb") as target_file:
            target_file.write(body)
        output_rows.append({"file": name, "bytes": len(body), "sha256": sha(body)})
    input_rows = [{"file": file, "sha256": record["sha256"], "unchanged": sha((WORKSPACE / file).read_bytes()) == record["sha256"], "snapshot": f"input-snapshots/{index:02d}.source"} for index, (file, record) in enumerate(captured_inputs.items(), 1)]
    result = {"schema_version": "ap2-dependency-input-export-result/1", "status": "prepared_source_derived_inputs" if all(row["unchanged"] for row in input_rows) else "input_changed_after_export", "output": relative(output), "target": target, "runtime_requirement_count": len(rows), "local_source_edges": len(local_edges), "separate_build_requirement_count": len(build_rows), "source_descriptors": "source-descriptors.json", "indexed_runtime_requirements": "indexed-runtime-requirements.txt", "separate_build_requirements": "separate-build-requirements.txt", "outputs": output_rows, "inputs": input_rows, "exporter_sha256": sha(Path(__file__).read_bytes()), "resolver_executed": False, "network_requests": 0, "source_wheels_built": False, "environment_installed": False, "acquired_source_imported": False, "native_application_executed": False, "model_requests": 0, "scope": "Source-derived dependency input export only; not a lock, installed environment or runtime qualification"}
    with (output / "result.json").open("xb") as target_file:
        target_file.write(json_bytes(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=WORKSPACE / "runs/ap2-dependency-resolution/input-v1")
    args = parser.parse_args()
    result = export(args.output)
    print(json.dumps({key: result[key] for key in ("status", "output", "runtime_requirement_count", "local_source_edges", "separate_build_requirement_count")}))


if __name__ == "__main__":
    main()
