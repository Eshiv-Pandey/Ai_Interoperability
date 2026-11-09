"""Read installed distribution metadata without importing AgentOps or its SDKs.

Run with the selected runtime's isolated Python. This verifies installed versions
and records selected import-source hashes, not the missing installation history.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import platform
import sysconfig
import importlib.machinery
from pathlib import Path
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "external/agentops-c806b7f1/agents/python"
CRITICAL = {"agentops-agent", "google-adk", "a2a-sdk", "pytest", "starlette", "httpx",
            "anyio", "pydantic", "pydantic-settings", "sqlalchemy", "aiosqlite"}


def file_record(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.resolve().relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def inspect() -> dict:
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("The unchanged application requires the Linux x86_64 control")
    import fcntl
    origin = Path(fcntl.__file__).resolve()
    if not origin.is_relative_to(Path(sys.base_prefix).resolve()) or not isinstance(
            fcntl.__loader__, importlib.machinery.ExtensionFileLoader):
        raise ValueError("fcntl must be the interpreter native extension, never a shim")
    runtime = Path(sys.prefix).resolve()
    if not runtime.is_relative_to(ROOT / "external"):
        raise ValueError("Interpreter must use an isolated workspace runtime")
    if sys.version_info[:2] != (3, 13):
        raise ValueError("The original application requires Python 3.13")
    lock = tomllib.loads((SOURCE / "uv.lock").read_text(encoding="utf-8"))
    allowed = {(row["name"], row["version"]) for row in lock["package"]}
    pins = {name: version for name, version in allowed if name in CRITICAL}
    if set(pins) != CRITICAL:
        raise ValueError("A required lock entry is missing")
    packages = []
    versions = {}
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"].lower().replace("_", "-").replace(".", "-")
        if name in versions:
            raise ValueError(f"Duplicate distribution: {name}")
        location = Path(distribution.locate_file("")).resolve()
        if not location.is_relative_to(runtime):
            raise ValueError(f"Distribution outside isolated runtime: {name}")
        versions[name] = distribution.version
        if (name, distribution.version) not in allowed:
            raise ValueError(f"Installed version absent from original lock: {name}")
        metadata_files = []
        for entry in distribution.files or []:
            if entry.name in {"METADATA", "RECORD", "direct_url.json"}:
                path = Path(distribution.locate_file(entry)).resolve()
                if not path.is_relative_to(runtime):
                    raise ValueError(f"Metadata outside runtime: {name}")
                metadata_files.append(file_record(path))
        packages.append({"name": name, "version": distribution.version,
                         "location": location.relative_to(ROOT).as_posix(),
                         "metadata_files": sorted(metadata_files, key=lambda row: row["path"])})
    for name, version in pins.items():
        if versions.get(name) != version:
            raise ValueError(f"Required installed version mismatch: {name}")
    agent_distribution = metadata.distribution("agentops-agent")
    direct = json.loads(agent_distribution.read_text("direct_url.json") or "{}")
    if direct != {"url": SOURCE.as_uri(), "dir_info": {"editable": True}}:
        raise ValueError("AgentOps editable distribution is not the exact original source")
    site = Path(sysconfig.get_path("purelib")).resolve()
    if not site.is_relative_to(runtime):
        raise ValueError("Selected import sources are outside the isolated runtime")
    # These bytes identify the directly used boundary code. They do not claim
    # complete runtime authenticity or validate every distribution RECORD entry.
    selected = [
        "_pytest/tmpdir.py", "a2a/server/request_handlers/default_request_handler.py",
        "google/adk/a2a/executor/a2a_agent_executor.py",
        "starlette/testclient.py", "httpx/_client.py",
    ]
    return {
        "schema_version": "agentops-installed-runtime-inspection/4",
        "status": "installed_versions_match_lock",
        "python": list(sys.version_info[:3]), "executable": str(Path(sys.executable).resolve()),
        "runtime_prefix": str(runtime), "lock": file_record(SOURCE / "uv.lock"),
        "critical_locked_versions": pins,
        "packages": sorted(packages, key=lambda row: row["name"]),
        "selected_sources": [file_record(site / name) for name in selected],
        "agentops_direct_url": direct,
        "platform": {"system": platform.system(), "machine": platform.machine(),
                     "libc": list(platform.libc_ver()), "release": platform.release()},
        "fcntl_extension": {"path": str(origin), "sha256": hashlib.sha256(origin.read_bytes()).hexdigest()},
        "setup_receipt": "runs/agentops-native-eligibility/dependencies-linux-v4/result.json",
        "all_runtime_files_authenticated": False,
        "dependency_closure_independently_resolved": False,
        "application_imports": 0, "application_requests": 0, "model_calls": 0,
    }


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2, sort_keys=True))
