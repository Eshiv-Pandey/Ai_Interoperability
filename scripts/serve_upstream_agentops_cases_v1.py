"""Gated native bootstrap for original AgentOps core/report/workflow objects.

Importing this module is standard-library only. The outer runner owns allocations,
credentials, inputs, clients, database retention and process/job qualification.
No SDK or application import occurs until the actual main's prelaunch checks pass.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, MutableMapping


SCHEMA = "upstream-agentops-bootstrap/1"
MINIMUMS = {"physical_available_bytes": 1024**3, "commit_available_bytes": 2 * 1024**3}
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_MODEL = re.compile(r"^gemini-[A-Za-z0-9._-]{1,100}$")
_SOURCE_FILES = (
    "agents/python/src/agent/__init__.py", "agents/python/src/agent/config.py",
    "agents/python/src/agent/server.py", "agents/python/src/agent/composition.py",
    "agents/python/src/agent/governance.py", "agents/python/src/agent/report.py",
    "agents/python/src/agent/workflow.py", "agents/python/src/agent/model.py",
    "agents/python/src/agent/models.py", "agents/python/src/agent/data.py", "agents/python/src/agent/longterm.py",
    "agents/python/src/agent/tools.py", "agents/python/src/agent/memory.py",
    "agents/python/src/agent/mcp_client.py", "agents/python/src/agent/skills.py",
    "agents/python/src/agent/state.py", "agents/python/src/agent/budget.py",
    "agents/python/src/agent/compaction.py", "agents/python/src/agent/resilience.py",
    "agents/python/src/agent/actions.py", "agents/python/src/agent/guardrails.py",
    "agents/python/src/agent/pii.py", "agents/python/src/agent/telemetry.py",
    "agents/python/pyproject.toml", "agents/python/uv.lock", "agents/data/incidents.db",
)
_RECEIPTS = ("bootstrap.created.json", "bootstrap.stop-ack.json", "bootstrap.stop-error.json", "bootstrap.exit.json")


@dataclass(frozen=True)
class BootstrapConfig:
    source_root: Path
    service_dir: Path
    family: str
    provider: str
    model: str
    host: str
    port: int
    resource_gate_receipt: Path
    stop_token: str


def parse_args(argv: list[str] | None = None) -> BootstrapConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--service-dir", required=True, type=Path)
    parser.add_argument("--family", required=True, choices=("core", "report", "workflow"))
    parser.add_argument("--provider", required=True, choices=("gemini",))
    parser.add_argument("--model", required=True)
    parser.add_argument("--host", required=True, choices=("127.0.0.1",))
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--resource-gate-receipt", required=True, type=Path)
    parser.add_argument("--stop-token", required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or not _MODEL.fullmatch(args.model) or not _TOKEN.fullmatch(args.stop_token):
        parser.error("port, explicit Gemini model identifier, or nonsecret stop token is invalid")
    if any(not path.is_absolute() for path in (args.source_root, args.service_dir, args.resource_gate_receipt)):
        parser.error("source, service and resource-gate paths must be absolute")
    return BootstrapConfig(**vars(args))


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()


def binding_for(config: BootstrapConfig, interpreter: str | None = None, bootstrap_sha256: str | None = None) -> dict:
    return {"source_root": str(config.source_root.resolve()), "service_dir": str(config.service_dir.resolve()),
            "family": config.family, "provider": config.provider, "model": config.model,
            "host": config.host, "port": config.port, "interpreter": str(Path(interpreter or sys.executable).resolve()),
            "bootstrap_sha256": bootstrap_sha256 or _sha256(Path(__file__).resolve()), "stop_token": config.stop_token}


def _plain_int(value: Any, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _utc(value: Any) -> datetime:
    if type(value) is not str or not _UTC.fullmatch(value):
        raise ValueError("resource observation must use an explicit UTC ISO timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("malformed resource observation timestamp") from None
    if result.utcoffset() != timezone.utc.utcoffset(result):
        raise ValueError("resource observation is not UTC")
    return result


def validate_resource_gate(receipt: Any, expected_binding: dict, now: datetime) -> dict:
    """Check a recent bound outer gate; this is not signed authorization."""
    if type(now) is not datetime or now.tzinfo is None or now.utcoffset() != timezone.utc.utcoffset(now):
        raise ValueError("gate main-entry time must be aware UTC")
    if (type(receipt) is not dict or receipt.get("schema_version") != "upstream-agentops-resource-gate/1"
            or receipt.get("stage") != "prelaunch" or receipt.get("eligible") is not True):
        raise ValueError("passed prelaunch resource gate is required")
    binding = receipt.get("binding")
    if type(binding) is not dict or set(binding) != set(expected_binding):
        raise ValueError("resource gate binding fields differ")
    if any(type(binding[key]) is not type(expected_binding[key]) or binding[key] != expected_binding[key] for key in expected_binding):
        raise ValueError("resource gate is not bound to this exact launch")
    minima = receipt.get("minimums")
    if type(minima) is not dict or set(minima) != set(MINIMUMS) or any(type(minima[key]) is not int or minima[key] != value for key, value in MINIMUMS.items()):
        raise ValueError("resource gate minima must match the declared bootstrap thresholds")
    samples = receipt.get("samples")
    if type(samples) is not list or len(samples) != 2:
        raise ValueError("resource gate requires exactly two observations")
    times = []
    for sample in samples:
        if type(sample) is not dict or not {"observed_at_utc", "monotonic_ns", *MINIMUMS} <= set(sample):
            raise ValueError("resource sample is missing typed observations")
        if not _plain_int(sample["monotonic_ns"]):
            raise ValueError("resource monotonic counter must be a nonnegative integer")
        for key, minimum in MINIMUMS.items():
            if not _plain_int(sample[key], minimum):
                raise ValueError("resource sample does not satisfy typed headroom minima")
        times.append(_utc(sample["observed_at_utc"]))
    wall_gap = (times[1] - times[0]).total_seconds()
    monotonic_gap = (samples[1]["monotonic_ns"] - samples[0]["monotonic_ns"]) / 1_000_000_000
    age = (now - times[1]).total_seconds()
    if not 10 <= wall_gap <= 30 or not 10 <= monotonic_gap <= 30 or abs(wall_gap - monotonic_gap) > 1:
        raise ValueError("resource observations must establish a consistent 10 to 30 second interval")
    if not 0 <= age <= 60:
        raise ValueError("resource gate is future-dated or older than 60 seconds at main entry")
    return {"schema_version": receipt["schema_version"], "stage": "prelaunch", "eligible": True,
            "binding": dict(binding), "minimums": dict(MINIMUMS), "sample_count": 2, "age_seconds_at_main_entry": age,
            "signed_authorization_proven": False, "threshold_safety_proven": False}


def _regular(path: Path, *, directory: bool = False) -> None:
    try:
        info = path.lstat()
    except OSError:
        raise ValueError("required regular launch path is unavailable") from None
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        raise ValueError("linked/reparse launch or control paths are unsupported")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError("expected a regular launch directory or file")


def _closed_directory(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("launch directory must be absolute")
    for parent in reversed((path, *path.parents)):
        _regular(parent, directory=True)


def validate_paths(config: BootstrapConfig) -> None:
    """Validate allocated paths without creating state, captures or receipts."""
    if config.family not in {"core", "report", "workflow"} or config.provider != "gemini" or config.host != "127.0.0.1":
        raise ValueError("unsupported original family/provider/loopback binding")
    if (not _plain_int(config.port, 1) or config.port > 65535 or type(config.model) is not str
            or type(config.stop_token) is not str or not _MODEL.fullmatch(config.model) or not _TOKEN.fullmatch(config.stop_token)):
        raise ValueError("invalid explicit launch parameters")
    _closed_directory(config.source_root)
    _closed_directory(config.service_dir)
    state = config.service_dir / "state"
    _regular(state, directory=True)
    if state.resolve().parent != config.service_dir.resolve() or any(state.iterdir()):
        raise ValueError("run state must be a closed, existing, empty service/state directory")
    if any((config.service_dir / name).exists() or (config.service_dir / name).is_symlink()
           for name in (*_RECEIPTS, "wire", "stop.request.json")):
        raise ValueError("service bootstrap/capture/control allocation is already consumed")
    if config.source_root.resolve().is_relative_to(config.service_dir.resolve()) or config.service_dir.resolve().is_relative_to(config.source_root.resolve()):
        raise ValueError("source and service allocations must be disjoint")
    for relative in _SOURCE_FILES:
        path = config.source_root / relative
        _regular(path)
        if not path.resolve().is_relative_to(config.source_root.resolve()):
            raise ValueError("upstream source file escapes the bound source root")
    _regular(config.resource_gate_receipt)
    if config.resource_gate_receipt.resolve().is_relative_to(config.service_dir.resolve()):
        raise ValueError("outer resource gate receipt must be outside the service allocation")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member in gate/control evidence")
        result[key] = value
    return result


def read_json_regular(path: Path) -> dict:
    _closed_directory(path.parent)
    _regular(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("gate/control JSON exceeds the declared byte limit")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("gate/control evidence is not regular UTF-8 JSON") from None


def nonsecret_environment(config: BootstrapConfig) -> dict[str, str]:
    """Explicit original settings; no environment reads or dotenv loading."""
    return {
        "AGENT_ENTRYPOINT": "workflow" if config.family == "workflow" else "agent",
        "AGENT_MODEL_PROVIDER": config.provider, "AGENT_MODEL": config.model,
        "AGENT_DATA_DIR": str((config.source_root / "agents/data").resolve()),
        "AGENT_STATE_DIR": str((config.service_dir / "state").resolve()),
        "AGENT_A2A_BIND_HOST": config.host, "AGENT_A2A_HOST": config.host,
        "AGENT_A2A_PORT": str(config.port), "AGENT_A2A_PROTOCOL": "http",
        "AGENT_A2A_MAX_LLM_CALLS": "12", "AGENT_A2A_STREAMING": "false",
        "AGENT_DRAIN_TIMEOUT_S": "10", "AGENT_MODEL_TIMEOUT_S": "60", "AGENT_TOOL_TIMEOUT_S": "30",
        "AGENT_MAX_RETRIES": "2", "AGENT_RETRY_BACKOFF_S": "0.5",
        "AGENT_WRITES_DISABLED": "false", "AGENT_SANITIZE_TOOL_OUTPUT": "true",
        "AGENT_SEMANTIC_RETRIEVAL": "false", "AGENT_CIRCUIT_BREAKER_ENABLED": "false",
        "GOOGLE_GENAI_USE_ENTERPRISE": "false", "OTEL_SDK_DISABLED": "true",
        "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS": "false", "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false",
    }


def configure_environment(config: BootstrapConfig, environ: MutableMapping[str, str] | None = None) -> None:
    target = os.environ if environ is None else environ
    # Preserve the supplied secret by name only. Never fetch/copy/log its value.
    if "GOOGLE_API_KEY" not in target:
        raise ValueError("GOOGLE_API_KEY must be supplied by the outer secure helper")
    prefixes = ("AGENT_", "GOOGLE_", "GEMINI_", "OPENAI_", "OTEL_", "MLFLOW_", "ADK_", "MCP_", "STATE_BACKUP")
    special = {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "PYTHONPATH", "PYTHONHOME", "DOTENV_FILE"}
    for name in list(target):
        upper = name.upper()
        if upper != "GOOGLE_API_KEY" and (upper.startswith(prefixes) or upper in special):
            del target[name]
    for name, value in nonsecret_environment(config).items():
        target[name] = value


def expected_settings(config: BootstrapConfig) -> dict:
    return {"entrypoint": "workflow" if config.family == "workflow" else "agent", "model_provider": config.provider,
            "model": config.model, "data_dir": (config.source_root / "agents/data").resolve(),
            "state_dir": (config.service_dir / "state").resolve(), "a2a_bind_host": config.host,
            "a2a_host": config.host, "a2a_port": config.port, "a2a_protocol": "http", "a2a_max_llm_calls": 12,
            "a2a_streaming": False, "drain_timeout_s": 10.0, "model_timeout_s": 60.0, "tool_timeout_s": 30.0,
            "max_retries": 2, "retry_backoff_s": 0.5, "writes_disabled": False, "sanitize_tool_output": True,
            "semantic_retrieval": False, "circuit_breaker_enabled": False, "google_genai_use_enterprise": False,
            "mcp_url": None, "mcp_token": None, "prompt_uri": None, "model_fallback": None,
            "model_temperature": None, "trusted_identity_header": None, "max_history_messages": None,
            "max_tokens_per_session": None}


def _module_origin(module: Any, expected: Path) -> str:
    value = getattr(module, "__file__", None)
    if type(value) is not str or Path(value).resolve() != expected.resolve():
        raise ValueError("runtime module is not the bound original source/observer file")
    return str(expected.resolve())


def build_observed_app(config: BootstrapConfig, *, importer: Any) -> tuple[Any, dict]:
    """Only main supplies the real importer, after its gate; tests supply mocks."""
    server = importer("agent.server")
    source = config.source_root / "agents/python/src/agent"
    origins = {"agent.server": _module_origin(server, source / "server.py")}
    settings = getattr(server, "settings", None)
    for name, expected in expected_settings(config).items():
        actual = getattr(settings, name, object())
        if isinstance(expected, Path):
            valid = isinstance(actual, Path) and actual.resolve() == expected
        elif name in {"entrypoint", "model_provider"}:
            valid = isinstance(actual, str) and str(actual) == expected
        else:
            valid = type(actual) is type(expected) and actual == expected
        if not valid:
            raise ValueError("loaded original configuration differs from the explicit nonsecret whitelist")
    if config.family == "core":
        selected = server.root_agent
        expected_name, composition = "agentops_agent", "original default create_app()"
    else:
        module_name = "agent.report" if config.family == "report" else "agent.workflow"
        module = importer(module_name)
        origins[module_name] = _module_origin(module, source / ("report.py" if config.family == "report" else "workflow.py"))
        selected = getattr(module, "triage_report_agent" if config.family == "report" else "triage_workflow")
        expected_name = "triage_report_agent" if config.family == "report" else "triage_workflow"
        composition = "explicit unchanged original object via create_app(agent=...)"
    if getattr(selected, "name", None) != expected_name:
        raise ValueError("selected original object has an unexpected family identity")
    app = server.create_app() if config.family == "core" else server.create_app(agent=selected)
    capture_module = importer("agentops_asgi_capture_v1")
    origins["agentops_asgi_capture_v1"] = _module_origin(capture_module, Path(__file__).resolve().parent / "agentops_asgi_capture_v1.py")
    wrapped = capture_module.Capture(app, config.service_dir)
    return wrapped, {"family": config.family, "composition": composition, "original_object_name": expected_name,
                     "original_object_type": f"{type(selected).__module__}.{type(selected).__qualname__}",
                     "original_object_id": id(selected), "original_app_type": f"{type(app).__module__}.{type(app).__qualname__}",
                     "module_origins": origins, "policy_boundary": "original server create_app/build_app",
                     "configuration": nonsecret_environment(config), "tool_restriction": False, "autoapproval": False,
                     "model_replacement": False, "business_request_snapshots": True,
                     "state_evidence_requirements": {"business_db": "state/incidents.db", "runtime_db": "state/runtime.db",
                         "memory_db": "state/memory.db", "memory_db_is_lazy": True, "retention_owned_by_outer_runner": True}}


def global_memory_status() -> dict:
    """Single immediate native-Windows check; never called by import or tests."""
    if os.name != "nt":
        raise ValueError("native Windows GlobalMemoryStatusEx is required")
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
                    ("total_pagefile", ctypes.c_ulonglong), ("available_pagefile", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ValueError("GlobalMemoryStatusEx failed")
    return {"physical_available_bytes": int(status.available_physical), "commit_available_bytes": int(status.available_pagefile)}


def validate_stop_request(value: Any, expected_token: str) -> None:
    if (type(value) is not dict or set(value) != {"schema_version", "stop_token"}
            or value["schema_version"] != "upstream-agentops-stop/1" or type(value["stop_token"]) is not str
            or value["stop_token"] != expected_token):
        raise ValueError("stop marker is malformed or belongs to another owned launch")


def _write_json(path: Path, value: dict) -> None:
    _closed_directory(path.parent)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


async def _watch_stop(server: Any, config: BootstrapConfig, *, poll_seconds: float = 0.1) -> dict:
    marker = config.service_dir / "stop.request.json"
    while True:
        if marker.exists() or marker.is_symlink():
            try:
                value = read_json_regular(marker)
                validate_stop_request(value, config.stop_token)
            except BaseException as error:
                _write_json(config.service_dir / "bootstrap.stop-error.json", {"schema_version": SCHEMA, "status": "rejected",
                            "observed_at_utc": datetime.now(timezone.utc).isoformat(), "error_type": type(error).__name__})
                raise
            # Uvicorn skips its normal shutdown path when should_exit is set
            # during startup. Wait for its own ready flag before an accepted
            # marker requests drain; failed imports/startup are outer-job cleanup.
            if not getattr(server, "started", False):
                await asyncio.sleep(poll_seconds)
                continue
            server.should_exit = True
            acknowledgment = {"schema_version": "upstream-agentops-stop-ack/1", "status": "accepted",
                              "observed_at_utc": datetime.now(timezone.utc).isoformat(), "request_sha256": _sha256(marker),
                              "should_exit_requested": True, "lifespan_close_completed": False}
            _write_json(config.service_dir / "bootstrap.stop-ack.json", acknowledgment)
            return acknowledgment
        await asyncio.sleep(poll_seconds)


async def serve_with_stop(server: Any, config: BootstrapConfig) -> dict:
    serving = asyncio.create_task(server.serve())
    watching = asyncio.create_task(_watch_stop(server, config))
    acknowledgment = None
    try:
        done, _ = await asyncio.wait((serving, watching), return_when=asyncio.FIRST_COMPLETED)
        if watching in done:
            try:
                acknowledgment = watching.result()
            except BaseException:
                server.should_exit = True  # reject control, drain only this owned server, then report failure
                await serving
                raise
        await serving
        return {"status": "stopped" if acknowledgment and getattr(server, "started", False) else "returned_without_owned_ready_stop",
                "owned_stop_accepted": acknowledgment is not None, "uvicorn_started": bool(getattr(server, "started", False)),
                "original_serve_returned": True, "process_exit_proven": False, "database_retention_completed": False}
    finally:
        for task in (watching, serving):
            if not task.done():
                task.cancel()
        await asyncio.gather(watching, serving, return_exceptions=True)


def validate_runtime_flags(flags: Any = None) -> None:
    value = sys.flags if flags is None else flags
    if any(type(getattr(value, name, None)) is not int or getattr(value, name) != 1
           for name in ("isolated", "no_site", "dont_write_bytecode")):
        raise ValueError("native bootstrap requires interpreter -I -S -B flags")


def _install_source_path(config: BootstrapConfig, runtime_library: Path | None = None) -> dict:
    if any(name == "agent" or name.startswith("agent.") for name in sys.modules):
        raise ValueError("original application was imported before the prelaunch gate")
    # Under Python 3.13 -S, sys.prefix may refer to the base interpreter rather
    # than the venv. Derive the native venv from its executable, never prefix.
    runtime_root = Path(sys.executable).resolve().parent.parent
    library = runtime_library if runtime_library is not None else runtime_root / "Lib/site-packages"
    _closed_directory(library)
    pyvenv = runtime_root / "pyvenv.cfg"
    if runtime_library is None:
        _regular(pyvenv)
    initial = list(sys.path)  # isolated -S interpreter's standard-library paths
    if any(not item or any(part.casefold() == "site-packages" for part in Path(item).parts) for item in initial):
        raise ValueError("site-packages/current-directory path existed before the gate")
    source = (config.source_root / "agents/python/src").resolve()
    observer = Path(__file__).resolve().parent
    sys.path[:] = [str(source), str(observer), *initial, str(library.resolve())]
    return {"runtime_library": str(library.resolve()), "staged_original_src": str(source), "observer_scripts": str(observer),
            "initial_stdlib_paths": initial, "site_addsitedir_used": False, "pth_executed": False,
            "pyvenv_cfg_sha256": _sha256(pyvenv) if runtime_library is None else None,
            "source_import_route": "explicit original agents/python/src; acquisition discovery symlink not required"}


def main(argv: list[str] | None = None) -> int:
    entered = datetime.now(timezone.utc)
    config = parse_args(argv)
    phase, gate_passed = "prelaunch", False
    try:
        validate_runtime_flags()
        validate_paths(config)
        binding = binding_for(config)
        gate = validate_resource_gate(read_json_regular(config.resource_gate_receipt), binding, entered)
        current = global_memory_status()
        if any(not _plain_int(current.get(key), minimum) for key, minimum in MINIMUMS.items()):
            raise ValueError("current native Windows headroom fell below the gate minima")
        gate_passed = True
        configure_environment(config)
        import_setup = _install_source_path(config)
        source_hashes = {relative: _sha256(config.source_root / relative) for relative in _SOURCE_FILES}
        phase = "native_import_or_factory"
        uvicorn = import_module("uvicorn")
        def factory() -> Any:
            app, metadata = build_observed_app(config, importer=import_module)
            if any(_sha256(config.source_root / relative) != digest for relative, digest in source_hashes.items()):
                raise ValueError("original source changed during runtime construction")
            _write_json(config.service_dir / "bootstrap.created.json", {"schema_version": SCHEMA, "status": "constructed_not_ready",
                        "observed_at_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), "binding": binding,
                        "resource_gate": gate, "immediate_headroom": current, "source_sha256": source_hashes,
                        "import_setup": import_setup, **metadata})
            return app
        server = uvicorn.Server(uvicorn.Config(factory, factory=True, host=config.host, port=config.port, lifespan="on",
                                              timeout_graceful_shutdown=10, log_config=None, log_level="warning", access_log=False))
        phase = "owned_serve"
        result = asyncio.run(serve_with_stop(server, config))
        _write_json(config.service_dir / "bootstrap.exit.json", {"schema_version": SCHEMA, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                    "binding": binding, **result, "native_case_pass_proven": False, "qualification_established": False})
        return 0 if result["status"] == "stopped" else 1
    except BaseException as error:
        # No raw provider exception, traceback, environment or caller payload.
        if gate_passed and not (config.service_dir / "bootstrap.exit.json").exists():
            try:
                _write_json(config.service_dir / "bootstrap.exit.json", {"schema_version": SCHEMA, "status": "failed",
                            "phase": phase, "error_type": type(error).__name__, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                            "native_case_pass_proven": False, "qualification_established": False})
            except BaseException:
                pass
        print(json.dumps({"schema_version": SCHEMA, "status": "failed", "phase": phase, "error_type": type(error).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
