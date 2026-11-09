"""Read installed distribution metadata without importing AgentOps or its SDKs.

Run with the selected runtime's isolated Python. This verifies installed versions
and records selected import-source hashes, not the missing installation history.
"""
from __future__ import annotations

import hashlib
import _imp
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


def classify_native_module(module) -> str:
    """Distinguish real built-in/extension loader identities from Python shims."""
    name = module.__name__
    spec = module.__spec__
    if spec is None or spec.name != name:
        raise ValueError("Native module has no matching import specification")
    builtin = importlib.machinery.BuiltinImporter.find_spec(name)
    if (name in sys.builtin_module_names and _imp.is_builtin(name)
            and builtin is not None and builtin.origin == "built-in"
            and builtin.loader is importlib.machinery.BuiltinImporter
            and spec.origin == "built-in" and spec.loader is importlib.machinery.BuiltinImporter
            and module.__loader__ is importlib.machinery.BuiltinImporter
            and not hasattr(module, "__file__")):
        return "builtin"
    filename = getattr(module, "__file__", None)
    if (filename is not None and isinstance(module.__loader__, importlib.machinery.ExtensionFileLoader)
            and isinstance(spec.loader, importlib.machinery.ExtensionFileLoader)
            and Path(spec.origin).resolve() == Path(filename).resolve()
            and Path(filename).is_file()
            and any(str(filename).endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES)
            and Path(filename).resolve().is_relative_to(Path(sys.base_prefix).resolve())):
        return "extension"
    raise ValueError("Expected a real interpreter built-in or native extension, never a Python shim")


def inspect() -> dict:
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("The unchanged application requires the Linux x86_64 control")
    import fcntl
    native_kind = classify_native_module(fcntl)
    if not callable(getattr(fcntl, "flock", None)) or not all(
            type(getattr(fcntl, name, None)) is int for name in ("LOCK_EX", "LOCK_UN", "LOCK_NB")):
        raise ValueError("Native fcntl does not expose the required flock operations")
    provider = (Path(sys.executable).resolve() if native_kind == "builtin"
                else Path(fcntl.__file__).resolve())
    providers = [file_record(provider)]
    if native_kind == "builtin" and sysconfig.get_config_var("Py_ENABLE_SHARED"):
        loaded = set()
        for line in Path("/proc/self/maps").read_text().splitlines():
            fields = line.split(None, 5)
            if len(fields) == 6 and Path(fields[5]).name.startswith("libpython"):
                library = Path(fields[5]).resolve()
                if not library.is_relative_to(Path(sys.base_prefix).resolve()):
                    raise ValueError("Loaded libpython lies outside the selected interpreter")
                loaded.add(library)
        if not loaded:
            raise ValueError("Shared interpreter has no identifiable loaded libpython")
        providers.extend(file_record(path) for path in sorted(loaded))
    native_record = {"kind": native_kind, "module": "fcntl", "origin": fcntl.__spec__.origin,
                     "provider_file": providers[0], "provider_files": providers}
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
        "schema_version": "agentops-installed-runtime-inspection/6",
        "status": "installed_versions_match_lock",
        "python": list(sys.version_info[:3]), "executable": str(Path(sys.executable).resolve()),
        "runtime_prefix": str(runtime), "lock": file_record(SOURCE / "uv.lock"),
        "critical_locked_versions": pins,
        "packages": sorted(packages, key=lambda row: row["name"]),
        "selected_sources": [file_record(site / name) for name in selected],
        "agentops_direct_url": direct,
        "platform": {"system": platform.system(), "machine": platform.machine(),
                     "libc": list(platform.libc_ver()), "release": platform.release()},
        "fcntl_native": native_record,
        "setup_receipt": "runs/agentops-native-eligibility/dependencies-linux-v7/result.json",
        "all_runtime_files_authenticated": False,
        "dependency_closure_independently_resolved": False,
        "application_imports": 0, "application_requests": 0, "model_calls": 0,
    }


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2, sort_keys=True))
