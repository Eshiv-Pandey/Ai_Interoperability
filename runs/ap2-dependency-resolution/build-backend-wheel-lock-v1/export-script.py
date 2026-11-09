"""Freeze artifacts from retained AP2 pip reports, without re-solving or fetching wheels."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


WORKSPACE = Path(__file__).resolve().parents[1]
BASE = WORKSPACE / "runs/ap2-dependency-resolution"
KINDS = {
    "indexed-runtime": {"source": "windows-cp313-dry-run-v1", "output": "indexed-wheel-lock-v1", "status": "indexed_resolution_report_captured", "count": 184, "count_field": "selected_indexed_distributions", "requirement_file": "indexed-runtime-requirements.txt"},
    "declared-build-backends": {"source": "build-backend-dry-run-v1", "output": "build-backend-wheel-lock-v1", "status": "declared_build_backend_report_captured", "count": 7, "count_field": "selected_distributions", "requirement_file": "separate-build-requirements.txt"},
}
LOCAL_NAMES = {"ap2", "ap2-samples", "x402-a2a"}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def strict_json(body):
    def reject_constant(value):
        raise ValueError("Non-JSON numeric constant: " + value)
    return json.loads(body, object_pairs_hook=strict_object, parse_constant=reject_constant)


def canonical_name(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*", name):
        raise ValueError("Invalid reported distribution name.")
    return re.sub(r"[-_.]+", "-", name).lower()


def export(kind):
    config = KINDS[kind]
    source = BASE / config["source"]
    output = BASE / config["output"]
    if output.exists():
        raise ValueError("Output namespace is already consumed; do not rerun.")
    snapshots = {}
    def read(path):
        body = path.read_bytes()
        snapshots[path] = body
        return body
    report_body = read(source / "pip-report.json")
    result_body = read(source / "result.json")
    plan_body = read(source / "plan.json")
    report, result, plan = [strict_json(body) for body in (report_body, result_body, plan_body)]
    if not (result["status"] == config["status"] and result["exit_code"] == 0 and result["timed_out"] is False and result["report_present"] is True and result["report_schema_valid"] is True and result[config["count_field"]] == config["count"] and all(value is True for value in result["inputs_unchanged"].values()) and result["source_built"] is False and result["environment_installed"] is False and result["original_application_imported"] is False and result["native_application_executed"] is False and result["model_requests"] == 0):
        raise ValueError("The exact terminal dry-run scope is not verified.")
    bound_artifacts = {row["file"]: row for row in result["artifacts"]}
    for name, body in (("pip-report.json", report_body), ("plan.json", plan_body)):
        if sha(body) != bound_artifacts[name]["sha256"] or len(body) != bound_artifacts[name]["bytes"]:
            raise ValueError("Dry-run artifact differs from its terminal receipt.")
    required_input_names = (config["requirement_file"], "source-descriptors.json", "result.json")
    for name in required_input_names:
        captured = read(source / "input-snapshots" / name)
        current = read(BASE / "input-v1" / name)
        if captured != current or sha(captured) != bound_artifacts["input-snapshots/" + name]["sha256"]:
            raise ValueError("Original requirements/descriptor binding differs: " + name)
    descriptors = strict_json(snapshots[BASE / "input-v1/source-descriptors.json"])
    argv = plan.get("actual_argv", plan.get("argv"))
    prefix = [descriptors["target"]["native_interpreter"]["executable"], "-I", "-m", "pip", "--isolated", "install"]
    if not isinstance(argv, list) or argv[:6] != prefix or any(token not in argv for token in ("--dry-run", "--ignore-installed", "--only-binary=:all:", "--disable-pip-version-check", "--no-cache-dir", "--no-input")):
        raise ValueError("Captured command is not the isolated binary-only dry-run.")
    if plan.get("environment_constraints", {}).get("PIP_CONFIG_FILE") != "nul":
        raise ValueError("Captured child did not declare the required global/site pip-config suppression.")
    required_options = {"--index-url": "https://pypi.org/simple", "--platform": "win_amd64", "--implementation": "cp", "--python-version": "3.13", "--abi": "cp313"}
    for option, expected in required_options.items():
        if argv.count(option) != 1 or argv[argv.index(option) + 1] != expected:
            raise ValueError("Captured command target/index differs: " + option)
    if "--extra-index-url" in argv or "--find-links" in argv:
        raise ValueError("Captured indexed dry-run has an unexpected secondary source.")
    if report["version"] != "1" or len(report["install"]) != config["count"]:
        raise ValueError("Unexpected pip report format or distribution membership.")
    environment = report["environment"]
    if not (environment["implementation_name"] == "cpython" and environment["os_name"] == "nt" and environment["platform_machine"].lower() in {"amd64", "x86_64"} and environment["python_version"] == "3.13" and environment["sys_platform"] == "win32"):
        raise ValueError("Reported environment is not the recorded native Windows CPython 3.13 target.")
    wheel_rows = []
    names = set()
    urls = set()
    for ordinal, item in enumerate(report["install"], 1):
        if item.get("is_yanked") is not False:
            raise ValueError("Unexpected yanked or unclassified reported artifact.")
        metadata = item["metadata"]
        name = canonical_name(metadata["name"])
        version = metadata["version"]
        if name in LOCAL_NAMES or name in names:
            raise ValueError("Duplicate distribution or source-local package shadow: " + name)
        if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z.!+_-]+", version):
            raise ValueError("Invalid exact reported version: " + name)
        names.add(name)
        info = item["download_info"]
        url = info["url"]
        if not isinstance(url, str) or any(character.isspace() for character in url):
            raise ValueError("Invalid reported wheel URL: " + name)
        parsed = urlsplit(url)
        if not (parsed.scheme == "https" and parsed.netloc == "files.pythonhosted.org" and parsed.username is None and parsed.password is None and parsed.port is None and not parsed.query and not parsed.fragment and parsed.path.endswith(".whl")):
            raise ValueError("Reported artifact is not an exact public PyPI HTTPS wheel URL: " + name)
        if url in urls or "vcs_info" in info or "dir_info" in info:
            raise ValueError("Unexpected duplicate/non-wheel source: " + name)
        urls.add(url)
        filename = unquote(parsed.path.rsplit("/", 1)[-1])
        if "/" in filename or "\\" in filename or any(character.isspace() for character in filename):
            raise ValueError("Encoded path separator or whitespace in reported wheel filename.")
        fields = filename[:-4].split("-")
        if len(fields) not in (5, 6) or canonical_name(fields[0]) != name or fields[1] != version.replace("-", "_"):
            raise ValueError("Wheel filename identity does not match report metadata: " + name)
        digest = info["archive_info"]["hashes"]["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Missing exact wheel SHA256: " + name)
        legacy_hash = info["archive_info"].get("hash")
        if legacy_hash is not None and legacy_hash != "sha256=" + digest:
            raise ValueError("Conflicting reported artifact hash: " + name)
        wheel_rows.append({"report_ordinal": ordinal, "name": metadata["name"], "normalized_name": name, "version": version, "wheel_url": url, "wheel_filename": filename, "sha256": digest, "metadata": metadata, "report_download_info": info, "requested": item.get("requested"), "is_direct": item.get("is_direct"), "is_yanked": item.get("is_yanked"), "wheel_bytes_downloaded_by_export": False, "wheel_bytes_independently_verified": False})
    lines = ["# Immutable wheel artifact selection derived from one retained pip dry-run.", "# Indexed artifacts only; no local source wheels or complete combined environment.", "# A later fetch/install must verify hashes and use --no-deps; this export performs no fetch/install."]
    for row in wheel_rows:
        lines.append(row["normalized_name"] + " @ " + row["wheel_url"] + " --hash=sha256:" + row["sha256"])
    requirements = ("\n".join(lines) + "\n").encode("utf-8")
    for path, body in snapshots.items():
        if path.read_bytes() != body:
            raise ValueError("An exact report/input changed during export preparation.")
    output.mkdir()
    outputs = {"wheel-url-requirements.txt": requirements, "export-script.py": Path(__file__).read_bytes()}
    input_rows = []
    for ordinal, (path, body) in enumerate(snapshots.items(), 1):
        name = f"input-snapshots/{ordinal:02d}-{path.name}"
        outputs[name] = body
        input_rows.append({"file": path.relative_to(WORKSPACE).as_posix(), "snapshot": name, "sha256": sha(body), "bytes": len(body)})
    output_rows = []
    for name, body in outputs.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as target:
            target.write(body)
        output_rows.append({"file": name, "sha256": sha(body), "bytes": len(body)})
    preservation = []
    for path, body in snapshots.items():
        after_body = path.read_bytes()
        preservation.append({"file": path.relative_to(WORKSPACE).as_posix(), "sha256": sha(body), "after_sha256": sha(after_body), "unchanged": after_body == body})
    manifest = {"schema_version": "ap2-report-derived-wheel-artifact-lock/1", "status": "frozen_report_derived_indexed_artifacts" if all(row["unchanged"] for row in preservation) else "input_changed_after_export", "kind": kind, "exported_at_utc": datetime.now(timezone.utc).isoformat(), "source_capture": source.relative_to(WORKSPACE).as_posix(), "source_result_sha256": sha(result_body), "source_report_sha256": sha(report_body), "source_plan_sha256": sha(plan_body), "pip_version": report["pip_version"], "report_environment": environment, "target": descriptors["target"], "distribution_count": len(wheel_rows), "wheels": wheel_rows, "source_local_projects_excluded": sorted(LOCAL_NAMES), "source_local_project_descriptors": descriptors["local_source_projects"], "inputs": input_rows, "input_preservation": preservation, "outputs": output_rows, "export_script_sha256": sha(Path(__file__).read_bytes()), "resolver_executed_by_export": False, "network_requests_by_export": 0, "wheel_downloads_by_export": 0, "source_built": False, "environment_installed": False, "acquired_source_imported": False, "native_application_executed": False, "model_requests": 0, "complete_combined_environment_established": False, "dynamic_backend_hook_dependencies_verified": False, "claim_limits": ["Report-derived indexed wheel artifact selection only; no re-solving/download/import/build/install", "Reported wheel hash and metadata retained; wheel bytes not independently fetched or verified by this export", "Three source-bound local packages and their builds remain separate", "Declared backend artifacts do not verify dynamic build-hook requirements", "No original-source runtime compatibility, bootstrap, native workflow, domain or checkpoint credit"]}
    with (output / "manifest.json").open("xb") as target:
        target.write(encoded(manifest))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=KINDS, required=True)
    args = parser.parse_args()
    manifest = export(args.kind)
    print(json.dumps({key: manifest[key] for key in ("status", "kind", "distribution_count", "source_report_sha256")}))


if __name__ == "__main__":
    main()
