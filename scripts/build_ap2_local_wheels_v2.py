"""Build three original AP2 wheels once in an offline isolated backend environment."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import time
import tomllib
import zipfile


WORKSPACE = Path(__file__).resolve().parents[1]
BASE = WORKSPACE / "runs/ap2-environment-preparation"
OUTPUT = BASE / "local-build-v2"
STAGE = BASE / "source-stage-v1"
STORE = BASE / "wheel-store-v1"
BACKEND_LOCK = WORKSPACE / "runs/ap2-dependency-resolution/build-backend-wheel-lock-v1/manifest.json"
JOB_SOURCE = WORKSPACE / "src/interoperability/windows_owned_job_v1.py"
EXPECTED = {
    "stage": "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463",
    "store": "ac4e3883891a108b141eed6f5bf4cb1e2b97439316f003bd6baeb89ca7ff8689",
    "backends": "d304cf5a3c8671bccd52fa3c4d5a7b357792aa25c5973a2ae8c2f24946da4078",
    "owned_job_helper": "67b5dc8190aee3a75b3c1954a530d0bba3edeb3bc64dc2770dd815173ecbd53a",
}
COMPATIBILITY = {
    "comspec": r"C:\WINDOWS\system32\cmd.exe",
    "platform": {"path": r"C:\Python313\Lib\platform.py", "sha256": "ca73b6b8390feb322d96df70155d981d88249af3c3848a04ed8b2d5ace023b87"},
    "subprocess": {"path": r"C:\Python313\Lib\subprocess.py", "sha256": "31963034c4a3b0e13c2fab8c6ab167ce94d7b32ea02101a480f77faff0fd2050"},
    "cmd": {"path": r"C:\Windows\System32\cmd.exe", "sha256": "ccd79a7568ea9240ccd6fe124807b9d3e4dbc3a4cf92954299ac3029f4a91d02"},
    "msvc": {"wheel_member": "setuptools/msvc.py", "sha256": "6bb37fbe305c1cf832623f65dc1586bebb06a410fc49f543976d97ed2e8accb0"},
}
PRIOR_V1 = {
    WORKSPACE / "scripts/build_ap2_local_wheels_v1.py": "a6417061bec291ca12a5805119c75749cc689f40e5755a145fb1a406c47424d3",
    BASE / "local-build-v1/result.json": "bd9d4e52a4305de811b720f1fa92919434462a252fe33dad9f574e93a4db0852",
    BASE / "local-build-v1/plan.json": "24f39db926875e81b047d73aa716f569c8a0204b23160c8475f47fbcd57fc95c",
}
PROJECTS = ("ap2", "ap2-samples", "x402-a2a")
APP_IMPORT_ROOTS = {"ap2", "common", "roles", "x402_a2a"}


class OwnedCleanupPending(RuntimeError):
    """Keep live native owner objects available to an in-process caller."""

    def __init__(self, owners, result_path, publication_failures=()):
        super().__init__("Owned cleanup remains unverified; do not discard native owners.")
        self.owned_jobs = tuple(owners)
        self.result_path = result_path
        self.publication_failures = tuple(publication_failures)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as target:
        json.dump(value, target, indent=2, sort_keys=True)
        target.write("\n")


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or "\\" in value or path.as_posix() != value:
        raise ValueError("Unsafe source or wheel-relative path.")
    return Path(*path.parts)


def requirement_key(value):
    from packaging.requirements import Requirement
    item = Requirement(value)
    return (normalize(item.name), tuple(sorted(normalize(extra) for extra in item.extras)),
            tuple(sorted((clause.operator, clause.version) for clause in item.specifier)),
            item.url, str(item.marker) if item.marker else None)


def guard_backend_child(context, decisions):
    """Allow only the genuine, pinned CPython Windows 'ver' fallback."""
    import ctypes
    from ctypes import wintypes
    compatibility = context["compatibility"]
    for label in ("platform", "subprocess", "cmd", "installed_msvc"):
        entry = compatibility[label]
        if sha(Path(entry["path"]).read_bytes()) != entry["sha256"]:
            raise ValueError("Pinned compatibility input differs: " + label)
    comspec = compatibility["comspec"]
    if os.environ.get("COMSPEC") != comspec or os.path.normcase(str(Path(comspec).resolve())) != os.path.normcase(str(Path(compatibility["cmd"]["path"]).resolve())):
        raise ValueError("COMSPEC differs from the frozen system command interpreter.")
    expected_argv = comspec + ' /c "ver"'
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.argtypes, kernel.GetCurrentProcess.restype = [], wintypes.HANDLE
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.IsProcessInJob.restype = wintypes.BOOL

    def sanitized(value, safe_values=()):
        if isinstance(value, (list, tuple)):
            return [sanitized(item, safe_values) for item in value]
        if type(value) is str:
            body = value.encode("utf-8", errors="surrogatepass")
            return {"type": "str", "text": value if value in safe_values else "<redacted unrecognized argument>", "sha256": sha(body), "characters": len(value)}
        if type(value) is bytes:
            return {"type": "bytes", "text": "<redacted unrecognized bytes>", "sha256": sha(value), "bytes": len(value)}
        return {"type": type(value).__name__, "text": None if value is None else "<redacted unrecognized value>"}

    def genuine_ver_context():
        platform_frame = subprocess_frame = False
        frame = sys._getframe(1)
        try:
            while frame is not None:
                path = os.path.normcase(frame.f_code.co_filename)
                if frame.f_code.co_name == "_syscmd_ver" and path == os.path.normcase(compatibility["platform"]["path"]):
                    original = frame.f_globals.get("_syscmd_ver")
                    platform_frame = getattr(original, "__code__", None) is frame.f_code and frame.f_locals.get("cmd") == "ver"
                if frame.f_code.co_name == "_execute_child" and path == os.path.normcase(compatibility["subprocess"]["path"]):
                    subprocess_frame = frame.f_locals.get("shell") is True and frame.f_locals.get("creationflags") == 0 and frame.f_locals.get("executable") == comspec and frame.f_locals.get("args") == expected_argv and frame.f_locals.get("cwd") is None and frame.f_locals.get("env") is None
                frame = frame.f_back
        finally:
            del frame
        for label in ("platform", "subprocess", "cmd", "installed_msvc"):
            entry = compatibility[label]
            if sha(Path(entry["path"]).read_bytes()) != entry["sha256"]:
                raise ValueError("Compatibility bytes changed before the audited probe.")
        in_job = wintypes.BOOL()
        if not kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(in_job)):
            raise OSError(ctypes.get_last_error(), "Cannot observe build child's Job membership")
        return {"genuine_platform_ver_frame": platform_frame, "frozen_subprocess_frame_shell_true_creationflags_zero": subprocess_frame,
                "caller_pid": os.getpid(), "current_process_in_job": bool(in_job.value),
                "containment": "Parent assigns suspended build child to its owned Job; creationflags=0 inherits that Job without breakaway"}

    subprocess_events = {"subprocess.Popen", "_winapi.CreateProcess", "os.system", "os.posix_spawn", "os.spawn", "os.exec", "os.startfile", "os.startfile/2"}
    def audit(event, arguments):
        if event in subprocess_events:
            executable = arguments[0] if arguments else None
            argv = arguments[1] if len(arguments) > 1 else None
            record = {"event": event, "decision": "deny", "sanitized_executable": sanitized(executable, (comspec,)),
                      "sanitized_argv": sanitized(argv, (expected_argv,)), "sanitization": "Only frozen probe strings disclosed; unknown argument bytes replaced by hashes; environment values never recorded"}
            if event == "subprocess.Popen":
                exact = len(arguments) == 4 and executable == comspec and argv == expected_argv and arguments[2] is None and arguments[3] is None
            elif event == "_winapi.CreateProcess":
                exact = len(arguments) == 3 and executable == comspec and argv == expected_argv and arguments[2] is None
            else:
                exact = False
            if exact:
                try:
                    record.update(genuine_ver_context())
                    if record["genuine_platform_ver_frame"] and record["frozen_subprocess_frame_shell_true_creationflags_zero"] and record["current_process_in_job"]:
                        record["decision"] = "allow_pinned_windows_ver_probe"
                except BaseException as error:
                    record["guard_error"] = {"type": type(error).__name__, "message": str(error)}
            decisions.append(record)
            if record["decision"] == "allow_pinned_windows_ver_probe":
                return
            raise RuntimeError("Offline backend guard denied " + event)
        if event in {"socket.__new__", "socket.connect", "socket.getaddrinfo"}:
            decisions.append({"event": event, "decision": "deny", "network_arguments_disclosed": False})
            raise RuntimeError("Offline backend guard denied " + event)
        if event == "import" and arguments and str(arguments[0]).split(".", 1)[0] in APP_IMPORT_ROOTS:
            decisions.append({"event": event, "decision": "deny", "application_namespace": str(arguments[0]).split(".", 1)[0]})
            raise ImportError("Original application import is outside local-wheel build scope.")
    sys.addaudithook(audit)


def child(context_path, action):
    """Runs only selected installed tooling. Original application imports are denied."""
    context = json.loads(context_path.read_bytes())
    result_path = Path(context["result"])
    if result_path.exists():
        raise ValueError("Child receipt already exists; do not repeat a hook/build.")
    decisions = []
    result = {"schema_version": "ap2-local-backend-operation/2", "action": action,
              "started_at_utc": utc(), "python_executable": sys.executable,
              "python_version": sys.version, "isolated": bool(sys.flags.isolated),
              "dont_write_bytecode": bool(sys.dont_write_bytecode), "installed_distributions": {},
              "application_import_guard": sorted(APP_IMPORT_ROOTS), "network_and_subprocess_guard": True,
              "subprocess_policy": "Deny all except exact hash-pinned original CPython Windows ver fallback in inherited owned Job",
              "audit_decisions": decisions, "compatibility": context["compatibility"],
              "original_application_imported": False, "model_requests": 0, "status": "failed", "error": None}
    try:
        guard_backend_child(context, decisions)
        from packaging.requirements import Requirement
        from packaging.markers import default_environment
        distributions = {normalize(item.metadata["Name"]): item.version for item in importlib.metadata.distributions()}
        result["installed_distributions"] = distributions
        expected_distributions = context["backend_versions"]
        if any(distributions.get(name) != version for name, version in expected_distributions.items()):
            raise ValueError("Installed backend distribution differs from frozen version.")
        unexpected = set(distributions) - set(expected_distributions) - {"pip"}
        if unexpected:
            raise ValueError("Unexpected ambient backend distribution: " + ",".join(sorted(unexpected)))
        if action == "probe":
            modules = {}
            for name, expected in context["backend_modules"].items():
                module = importlib.import_module(name)
                path = Path(module.__file__).resolve()
                body = path.read_bytes()
                if sha(body) != expected["sha256"]:
                    raise ValueError("Installed backend module differs from frozen wheel member.")
                modules[name] = {"file": str(path), "sha256": sha(body), "wheel_member": expected["wheel_member"], "wheel_sha256": expected["wheel_sha256"]}
            result.update({"status": "backend_environment_verified", "backend_modules": modules,
                           "pip_version": distributions.get("pip"), "packaging_version": distributions.get("packaging")})
        else:
            project = context["project"]
            module = importlib.import_module(project["backend"])
            expected = context["backend_modules"][project["backend"]]
            module_body = Path(module.__file__).read_bytes()
            if sha(module_body) != expected["sha256"]:
                raise ValueError("Backend hook module byte identity changed.")
            result["backend_module"] = {"name": project["backend"], "file": module.__file__, "sha256": sha(module_body)}
            if action == "get-requires":
                requirements = module.get_requires_for_build_wheel(config_settings=None)
                if not isinstance(requirements, list) or any(not isinstance(item, str) for item in requirements):
                    raise ValueError("Malformed dynamic backend requirement result.")
                checks = []
                for value in requirements:
                    requirement = Requirement(value)
                    environment = {**default_environment(), "extra": ""}
                    applies = requirement.marker is None or requirement.marker.evaluate(environment)
                    name = normalize(requirement.name)
                    satisfied = not applies or (not requirement.url and not requirement.extras and name in expected_distributions
                        and requirement.specifier.contains(distributions[name], prereleases=True))
                    checks.append({"requirement": value, "applies": applies, "name": name,
                                   "extras": sorted(requirement.extras), "extras_closure_verified": not requirement.extras,
                                   "frozen_version": expected_distributions.get(name), "satisfied_in_frozen_backend_closure": satisfied})
                result.update({"dynamic_requirements": requirements, "requirement_checks": checks,
                               "status": "dynamic_requirements_satisfied" if all(item["satisfied_in_frozen_backend_closure"] for item in checks) else "dynamic_requirements_unmet"})
            elif action == "build-wheel":
                wheel_dir = Path(context["wheel_directory"])
                before = {path.name for path in wheel_dir.iterdir()}
                filename = module.build_wheel(str(wheel_dir), config_settings=None, metadata_directory=None)
                if not isinstance(filename, str) or Path(filename).name != filename or "/" in filename or "\\" in filename or not filename.endswith(".whl"):
                    raise ValueError("Backend returned an unsafe wheel filename.")
                additions = {path.name for path in wheel_dir.iterdir()} - before
                if additions != {filename}:
                    raise ValueError("Backend did not produce exactly one reported new wheel.")
                body = (wheel_dir / filename).read_bytes()
                result.update({"status": "wheel_built_once", "wheel_filename": filename,
                               "wheel_sha256": sha(body), "wheel_bytes": len(body)})
            elif action == "inspect-wheel":
                filename = context["wheel_filename"]
                wheel_path = Path(context["wheel_directory"]) / filename
                source_root = Path(project["source"])
                working_pyproject_sha = sha((source_root / "pyproject.toml").read_bytes())
                pyproject_unchanged = working_pyproject_sha == project["original_pyproject_sha256"]
                with zipfile.ZipFile(wheel_path) as archive:
                    names = archive.namelist()
                    if len(names) != len(set(names)) or any(safe_relative(name).as_posix() != name for name in names if not name.endswith("/")):
                        raise ValueError("Wheel has duplicated or unsafe ZIP member paths.")
                    metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
                    if len(metadata_names) != 1:
                        raise ValueError("Wheel has no unique METADATA.")
                    metadata_body = archive.read(metadata_names[0])
                    metadata = BytesParser().parsebytes(metadata_body)
                    actual_requires = metadata.get_all("Requires-Dist", [])
                    expected_requires = project["original_runtime_requirements"]
                    requires_match = Counter(requirement_key(value) for value in actual_requires) == Counter(requirement_key(value) for value in expected_requires)
                    expected_modules = project["module_sources"]
                    module_checks = []
                    for entry in expected_modules:
                        found = entry["wheel_path"] in names
                        actual_sha = sha(archive.read(entry["wheel_path"])) if found else None
                        module_checks.append({"source": entry["source"], "wheel_path": entry["wheel_path"],
                                              "expected_sha256": entry["sha256"], "wheel_sha256": actual_sha,
                                              "present": found, "matches": found and actual_sha == entry["sha256"]})
                    expected_python = {entry["wheel_path"] for entry in expected_modules}
                    unexpected_python = [name for name in names if name.endswith(".py") and name not in expected_python]
                    cards = [{**entry, "included": entry["wheel_path"] in names,
                              "wheel_sha256": sha(archive.read(entry["wheel_path"])) if entry["wheel_path"] in names else None,
                              "included_bytes_match_source": sha(archive.read(entry["wheel_path"])) == entry["sha256"] if entry["wheel_path"] in names else None} for entry in project["agent_cards"]]
                    typed_source = project.get("py_typed")
                    typed = {"expected": typed_source, "included": not typed_source or typed_source["wheel_path"] in names,
                             "wheel_sha256": sha(archive.read(typed_source["wheel_path"])) if typed_source and typed_source["wheel_path"] in names else None,
                             "included_bytes_match_source": not typed_source or (typed_source["wheel_path"] in names and sha(archive.read(typed_source["wheel_path"])) == typed_source["sha256"])}
                    identity_match = normalize(metadata["Name"]) == normalize(project["name"]) and metadata["Version"] == project["version"] and metadata["Requires-Python"] == project["original_requires_python"]
                    success = pyproject_unchanged and identity_match and requires_match and all(row["matches"] for row in module_checks) and not unexpected_python and typed["included_bytes_match_source"] and all(row["included_bytes_match_source"] is not False for row in cards)
                    result.update({"status": "original_wheel_metadata_and_modules_verified" if success else "wheel_inspection_discrepant",
                                   "wheel_filename": filename, "wheel_sha256": sha(wheel_path.read_bytes()),
                                   "metadata_member": metadata_names[0], "metadata_sha256": sha(metadata_body),
                                   "metadata": {"Name": metadata["Name"], "Version": metadata["Version"], "Requires-Python": metadata["Requires-Python"], "Requires-Dist": actual_requires},
                                   "original_runtime_requires_dist": expected_requires, "runtime_requirement_constraints_exact": requires_match,
                                   "original_requires_python": project["original_requires_python"],
                                   "original_pyproject_sha256": project["original_pyproject_sha256"],
                                   "working_pyproject_sha256": working_pyproject_sha, "working_pyproject_unchanged": pyproject_unchanged,
                                   "requirement_comparison": "PEP508 name/extras/specifier/url/marker identity with multiplicity; backend whitespace formatting retained separately",
                                   "module_checks": module_checks, "unexpected_python_members": unexpected_python,
                                   "agent_json_inclusion": cards, "py_typed": typed,
                                   "agent_json_omission_not_repaired": True, "native_runtime_asset_qualification": False})
            else:
                raise ValueError("Unknown backend child action.")
        if any(name.split(".", 1)[0] in APP_IMPORT_ROOTS for name in sys.modules):
            raise ValueError("Original application namespace was imported.")
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    result["finished_at_utc"] = utc()
    result["allowed_windows_ver_popen_probes"] = sum(row["event"] == "subprocess.Popen" and row["decision"] == "allow_pinned_windows_ver_probe" for row in decisions)
    write_json(result_path, result)
    print(json.dumps({"action": action, "status": result["status"], "result": str(result_path)}), flush=True)
    return 0 if result["status"] in {"backend_environment_verified", "dynamic_requirements_satisfied", "wheel_built_once", "original_wheel_metadata_and_modules_verified"} else 1


def prepare():
    if OUTPUT.exists():
        raise ValueError("Exclusive local-build-v2 already exists; do not rerun.")
    inputs = {}
    def bound(path, expected=None):
        body = path.read_bytes()
        if expected and sha(body) != expected:
            raise ValueError("Frozen input byte identity changed: " + str(path))
        inputs[path] = body
        return body
    stage = json.loads(bound(STAGE / "manifest.json", EXPECTED["stage"]))
    store = json.loads(bound(STORE / "manifest.json", EXPECTED["store"]))
    lock = json.loads(bound(BACKEND_LOCK, EXPECTED["backends"]))
    for path, expected in PRIOR_V1.items():
        bound(path, expected)
    if os.environ.get("COMSPEC") != COMPATIBILITY["comspec"] or os.path.normcase(str(Path(COMPATIBILITY["comspec"]).resolve())) != os.path.normcase(str(Path(COMPATIBILITY["cmd"]["path"]).resolve())):
        raise ValueError("Require the exact frozen COMSPEC system command interpreter.")
    compatibility_snapshots = []
    for name in ("platform", "subprocess", "cmd"):
        entry = COMPATIBILITY[name]
        body = bound(Path(entry["path"]), entry["sha256"])
        compatibility_snapshots.append({"filename": {"platform": "platform.py", "subprocess": "subprocess.py", "cmd": "system-cmd.exe"}[name], "source": entry["path"], "sha256": entry["sha256"], "bytes": len(body), "body": body})
    compatibility = {**COMPATIBILITY, "installed_msvc": {"path": str(OUTPUT / "backend-venv/Lib/site-packages/setuptools/msvc.py"), "sha256": COMPATIBILITY["msvc"]["sha256"]},
                     "prospective_compatibility_only": True, "v1_cause_confirmed": False,
                     "allowed_popen_executable": COMPATIBILITY["comspec"], "allowed_popen_args": COMPATIBILITY["comspec"] + ' /c "ver"',
                     "allowed_popen_cwd": None, "allowed_popen_env": None, "required_creationflags": 0,
                     "required_platform_function": "_syscmd_ver", "required_original_cmd_local": "ver"}
    if stage["status"] != "pristine_source_stage_created" or stage["ap2_files"] != 136 or stage["x402_files"] != 24 or any(value is not True for value in stage["inputs_unchanged"].values()):
        raise ValueError("Complete pristine source-stage receipt is not verified.")
    if store["status"] != "all_frozen_wheel_bytes_verified" or store["unique_artifacts"] != 189 or store["verified_artifacts"] != 189 or any(value is not True for value in store["inputs_unchanged"].values()):
        raise ValueError("Terminal exact frozen wheel byte capture is not complete.")
    if lock["kind"] != "declared-build-backends" or lock["distribution_count"] != 7:
        raise ValueError("Unexpected selected backend closure.")
    store_rows = {row["wheel_filename"]: row for row in store["artifacts"]}
    backend_versions, backend_modules, backend_wheels = {}, {}, []
    for row in lock["wheels"]:
        actual = store_rows[row["wheel_filename"]]
        if not (actual["verified"] is True and actual["sha256"] == actual["expected_sha256"] == row["sha256"] and actual["name"] == row["normalized_name"] and actual["version"] == row["version"]):
            raise ValueError("Frozen backend wheel receipt differs from selected lock.")
        path = STORE / safe_relative(actual["retained_wheel_file"])
        body = bound(path, row["sha256"])
        backend_wheels.append({"filename": row["wheel_filename"], "name": row["normalized_name"], "version": row["version"], "sha256": row["sha256"], "body": body})
        backend_versions[row["normalized_name"]] = row["version"]
        member = {"setuptools": ("setuptools.build_meta", "setuptools/build_meta.py"), "hatchling": ("hatchling.build", "hatchling/build.py")}.get(row["normalized_name"])
        if member:
            import io
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                backend_modules[member[0]] = {"wheel_member": member[1], "sha256": sha(archive.read(member[1])), "wheel_sha256": row["sha256"]}
                if row["normalized_name"] == "setuptools":
                    msvc = archive.read(COMPATIBILITY["msvc"]["wheel_member"])
                    if sha(msvc) != COMPATIBILITY["msvc"]["sha256"]:
                        raise ValueError("Frozen setuptools compatibility source differs.")
                    compatibility_snapshots.append({"filename": "setuptools-msvc.py", "source": COMPATIBILITY["msvc"]["wheel_member"], "sha256": sha(msvc), "wheel_sha256": row["sha256"], "bytes": len(msvc), "body": msvc})
    if set(backend_modules) != {"setuptools.build_meta", "hatchling.build"}:
        raise ValueError("Exact selected build backend modules unavailable.")
    for row in stage["files"]:
        path = STAGE / safe_relative(row["project"]) / safe_relative(row["path"])
        if sha(bound(path)) != row["sha256"]:
            raise ValueError("Pristine staged source differs from its manifest.")
    job_body = bound(JOB_SOURCE, EXPECTED["owned_job_helper"])
    source_groups = {
        "ap2": ("ap2", "ap2", "code/sdk/python", []),
        "ap2-samples": ("ap2", "ap2/code/samples/python", "src", ["roles/merchant_agent/agent.json", "roles/credentials_provider_agent/agent.json", "roles/merchant_payment_processor_agent/agent.json"]),
        "x402-a2a": ("a2a-x402", "a2a-x402/python/x402_a2a", "src", []),
    }
    projects = []
    for name in PROJECTS:
        group, build_root, modules_root, cards = source_groups[name]
        source = OUTPUT / "source-copies" / name / safe_relative(build_root)
        original_root = STAGE / safe_relative(build_root)
        original = tomllib.loads(inputs[original_root / "pyproject.toml"].decode("utf-8"))
        module_base = original_root / safe_relative(modules_root)
        modules = [{"source": path.relative_to(STAGE).as_posix(), "wheel_path": path.relative_to(module_base).as_posix(), "sha256": sha(body)} for path, body in inputs.items() if path.is_relative_to(module_base) and path.suffix == ".py"]
        card_sources = [{"source": (module_base / safe_relative(card)).relative_to(STAGE).as_posix(), "wheel_path": card, "sha256": sha(inputs[module_base / safe_relative(card)])} for card in cards]
        typed = "x402_a2a/py.typed" if name == "x402-a2a" else None
        typed_source = {"source": (module_base / safe_relative(typed)).relative_to(STAGE).as_posix(), "wheel_path": typed, "sha256": sha(inputs[module_base / safe_relative(typed)])} if typed else None
        projects.append({"name": name, "version": original["project"]["version"], "backend": original["build-system"]["build-backend"], "declared_backend_requirements": original["build-system"]["requires"], "original_pyproject_sha256": sha(inputs[original_root / "pyproject.toml"]), "original_runtime_requirements": original["project"]["dependencies"], "original_requires_python": original["project"]["requires-python"], "source": str(source), "copy_group": group, "build_root": build_root, "module_sources": modules, "agent_cards": card_sources, "py_typed": typed_source})
    return {"inputs": inputs, "stage": stage, "store": store, "backend_versions": backend_versions,
            "backend_modules": backend_modules, "backend_wheels": backend_wheels, "projects": projects,
            "job_body": job_body, "compatibility": compatibility, "compatibility_snapshots": compatibility_snapshots}


def execute(*, cli=False):
    prepared = prepare()
    OUTPUT.mkdir()
    for name in ("commands", "source-copies", "backend-wheels", "input-snapshots", "compatibility-snapshots", "hooks", "wheels"):
        (OUTPUT / name).mkdir()
    script_body = Path(__file__).read_bytes()
    (OUTPUT / "build-driver.py").write_bytes(script_body)
    (OUTPUT / "owned-job-helper.py").write_bytes(prepared["job_body"])
    snapshot_rows = []
    for index, (path, body) in enumerate(prepared["inputs"].items(), 1):
        if path.name == "manifest.json" or path == BACKEND_LOCK or path in PRIOR_V1:
            target = OUTPUT / "input-snapshots" / f"{index:03d}-{path.name}"
            target.write_bytes(body)
            snapshot_rows.append({"source": str(path), "file": target.relative_to(OUTPUT).as_posix(), "sha256": sha(body)})
    for entry in prepared["compatibility_snapshots"]:
        target = OUTPUT / "compatibility-snapshots" / entry["filename"]
        with target.open("xb") as stream:
            stream.write(entry["body"])
        snapshot_rows.append({"source": entry["source"], "file": target.relative_to(OUTPUT).as_posix(), "sha256": entry["sha256"], "bytes": entry["bytes"], **({"wheel_sha256": entry["wheel_sha256"]} if "wheel_sha256" in entry else {})})
    for wheel in prepared["backend_wheels"]:
        (OUTPUT / "backend-wheels" / wheel["filename"]).write_bytes(wheel["body"])
    copy_bindings = []
    for project in prepared["projects"]:
        destination = OUTPUT / "source-copies" / project["name"]
        for row in prepared["stage"]["files"]:
            if row["project"] != project["copy_group"]:
                continue
            source = STAGE / safe_relative(row["project"]) / safe_relative(row["path"])
            target = destination / safe_relative(row["project"]) / safe_relative(row["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(prepared["inputs"][source])
            copy_bindings.append((target, prepared["inputs"][source]))
    wheel_lines = ["# Exactly seven verified frozen backend wheels; offline/no-deps/no-compile installation only."]
    for row in prepared["backend_wheels"]:
        wheel_lines.append(row["name"] + " @ " + (OUTPUT / "backend-wheels" / row["filename"]).as_uri() + " --hash=sha256:" + row["sha256"])
    requirements = OUTPUT / "backend-local-wheel-requirements.txt"
    requirements.write_text("\n".join(wheel_lines) + "\n", encoding="utf-8")
    plan = {"schema_version": "ap2-isolated-local-wheel-build-plan/2", "created_at_utc": utc(),
            "source_stage_sha256": EXPECTED["stage"], "wheel_store_sha256": EXPECTED["store"],
            "declared_backend_lock_sha256": EXPECTED["backends"], "driver_sha256": sha(script_body),
            "owned_job_helper_sha256": sha(prepared["job_body"]), "backend_versions": prepared["backend_versions"],
            "owned_process_implementation": "native Windows Job Object; suspended child assigned before resume; task-owned handles only",
            "backend_modules": prepared["backend_modules"], "projects": prepared["projects"],
            "snapshot_bindings": snapshot_rows, "environment": {"PIP_CONFIG_FILE": "nul", "credential_variables_removed_from_task_process": True},
            "compatibility": prepared["compatibility"], "prior_v1_receipt_bindings": {str(path): value for path, value in PRIOR_V1.items()},
            "policy": "One fresh v2 venv/backend installation; one dynamic hook and one build per original source project; exact frozen original platform ver probe only; no automatic dependency fetch, source edits, WMI priming, fallback forcing or application imports", "native_application_executed": False, "model_requests": 0}
    write_json(OUTPUT / "plan.json", plan)
    namespace = {"__name__": "ap2_local_build_owned_job", "__file__": str(JOB_SOURCE)}
    exec(compile(prepared["job_body"], str(JOB_SOURCE), "exec"), namespace)
    WindowsJob = namespace["WindowsJob"]
    for name in list(os.environ):
        if any(term in name.upper() for term in ("API_KEY", "ACCESS_TOKEN", "SECRET", "CREDENTIAL")) or name in {"GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"}:
            del os.environ[name]
    os.environ["PIP_CONFIG_FILE"] = "nul"
    commands, held_jobs, hooks, builds, inspections = [], [], {}, {}, {}
    def cleanup_job(job, graceful_seconds=0):
        try:
            report = job.finish(graceful_seconds=graceful_seconds, forced_seconds=5)
        except BaseException as error:
            report = {"status": "cleanup_exception", "exception": {"type": type(error).__name__, "message": str(error)},
                      "handles_closed": bool(getattr(job, "closed", False)),
                      "job_empty_observed": bool(getattr(job, "_empty_verified", False)),
                      "authority_retained": not bool(getattr(job, "closed", False)),
                      "errors": ["cleanup_exception:" + type(error).__name__]}
        released = report.get("handles_closed") is True and (not getattr(job, "created", True) or report.get("job_empty_observed") is True)
        if released and job in held_jobs:
            held_jobs.remove(job)
        return report

    def run(label, argv, cwd, timeout=120):
        directory = OUTPUT / "commands" / label
        directory.mkdir()
        record = {"label": label, "argv": argv, "cwd": str(cwd), "timeout_seconds": timeout, "started_at_utc": utc(), "exit_code": None, "timed_out": False, "error": None}
        write_json(directory / "plan.json", record)
        job = None
        try:
            with (directory / "stdout.bin").open("xb") as stdout, (directory / "stderr.bin").open("xb") as stderr:
                job = WindowsJob()
                held_jobs.append(job)
                record["pid"] = job.launch(argv, str(cwd), stdout, stderr)
                print(json.dumps({"command": label, "pid": record["pid"], "status": "running"}), flush=True)
                deadline = time.monotonic() + timeout
                while job.poll() is None and time.monotonic() < deadline:
                    time.sleep(.1)
                record["exit_code"] = job.poll()
                record["timed_out"] = record["exit_code"] is None
        except BaseException as error:
            job = job or getattr(error, "owned_job", None)
            if job is not None and job not in held_jobs:
                held_jobs.append(job)
            record["error"] = {"type": type(error).__name__, "message": str(error)}
        finally:
            if job is not None:
                record["cleanup"] = cleanup_job(job, graceful_seconds=2 if not record["timed_out"] else 0)
            record["finished_at_utc"] = utc()
            record["passed"] = record["exit_code"] == 0 and not record["timed_out"] and record["error"] is None and record.get("cleanup", {}).get("job_empty_observed") is True and record.get("cleanup", {}).get("handles_closed") is True and not record.get("cleanup", {}).get("errors")
            record["logs"] = [{"file": filename, "sha256": sha((directory / filename).read_bytes()), "bytes": (directory / filename).stat().st_size} for filename in ("stdout.bin", "stderr.bin")]
            write_json(directory / "result.json", record)
            commands.append(record)
        return record["passed"]
    environment = OUTPUT / "backend-venv"
    python = environment / "Scripts/python.exe"
    result = {"schema_version": "ap2-isolated-local-wheel-build-result/2", "status": "incomplete", "started_at_utc": utc(), "commands": commands, "dynamic_hooks": hooks, "builds": builds, "inspections": inspections, "error": None, "source_wheel_builds_attempted": 0, "original_application_imported": False, "native_application_executed": False, "model_requests": 0, "network_requests_by_driver": 0, "resolver_executed": False, "complete_combined_environment_established": False}
    result.update({"source_stage_sha256": EXPECTED["stage"], "wheel_store_sha256": EXPECTED["store"],
                   "declared_backend_lock_sha256": EXPECTED["backends"], "driver_sha256": sha(script_body),
                   "owned_job_helper_sha256": sha(prepared["job_body"]),
                   "compatibility": prepared["compatibility"], "prior_v1_cause_confirmed": False,
                   "owned_process_implementation": "native Windows Job Object; suspended child assigned before resume; task-owned handles only"})
    publication_failures = []
    def publish_owned_receipt(path, value):
        try:
            write_json(path, value)
            return True
        except BaseException as error:
            publication_failures.append({"operation": "receipt_publication", "file": str(path), "type": type(error).__name__, "message": str(error)})
            return False

    def ownership_notice(value):
        try:
            print(json.dumps(value), flush=True)
        except BaseException as error:
            publication_failures.append({"operation": "stdout_publication", "type": type(error).__name__, "message": str(error)})

    context_base = {"backend_versions": prepared["backend_versions"], "backend_modules": prepared["backend_modules"], "compatibility": prepared["compatibility"]}
    def operation(project, action, wheel_filename=None):
        label = (project["name"] if project else "backends") + "-" + action
        receipt = OUTPUT / "hooks" / (label + ".json")
        context = {**context_base, "result": str(receipt), "wheel_directory": str(OUTPUT / "wheels")}
        if project:
            context["project"] = project
        if wheel_filename:
            context["wheel_filename"] = wheel_filename
        context_path = OUTPUT / "hooks" / (label + "-input.json")
        write_json(context_path, context)
        cwd = Path(project["source"]) if project else OUTPUT
        passed = run(label, [str(python), "-I", "-B", str(OUTPUT / "build-driver.py"), "--child-action", action, "--child-input", str(context_path)], cwd)
        data = json.loads(receipt.read_bytes()) if receipt.exists() else {"status": "missing_child_receipt"}
        return passed, data
    try:
        if not run("create-backend-venv", [sys.executable, "-I", "-B", "-m", "venv", str(environment)], OUTPUT):
            raise RuntimeError("Isolated backend venv creation failed.")
        install = [str(python), "-I", "-B", "-m", "pip", "--isolated", "install", "--no-index", "--no-deps", "--require-hashes", "--no-compile", "--disable-pip-version-check", "--no-cache-dir", "--no-input", "--report", str(OUTPUT / "backend-install-report.json"), "-r", str(requirements)]
        if not run("install-frozen-backends", install, OUTPUT):
            raise RuntimeError("Exact offline backend installation failed.")
        passed, probe = operation(None, "probe")
        result["backend_probe"] = probe
        if not passed:
            raise RuntimeError("Installed backend byte/version probe failed.")
        hooks_pass = True
        for project in prepared["projects"]:
            passed, data = operation(project, "get-requires")
            hooks[project["name"]] = data
            hooks_pass = hooks_pass and passed
        if not hooks_pass:
            result["status"] = "dynamic_backend_requirements_or_hook_unmet"
        else:
            for project in prepared["projects"]:
                result["source_wheel_builds_attempted"] += 1
                passed, data = operation(project, "build-wheel")
                builds[project["name"]] = data
                if not passed:
                    raise RuntimeError("Original source wheel build failed: " + project["name"])
                passed, data = operation(project, "inspect-wheel", data["wheel_filename"])
                inspections[project["name"]] = data
                if not passed:
                    raise RuntimeError("Original source wheel inspection failed: " + project["name"])
            result["status"] = "three_original_source_wheels_built_and_inspected"
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        cleanup_retries = []
        for job in list(held_jobs):
            cleanup_retries.append(cleanup_job(job))
        result["cleanup_retries"] = cleanup_retries
        result["owned_job_authority_remaining"] = bool(held_jobs)
        def preserve(bindings):
            rows = []
            for path, body in bindings:
                row = {"file": path.relative_to(WORKSPACE).as_posix() if path.is_relative_to(WORKSPACE) else str(path), "sha256": sha(body), "after_sha256": None, "unchanged": False}
                try:
                    after = path.read_bytes()
                    row.update({"after_sha256": sha(after), "unchanged": after == body})
                except BaseException as error:
                    row["error"] = {"type": type(error).__name__, "message": str(error)}
                rows.append(row)
            return rows
        preservation = preserve(prepared["inputs"].items())
        result["input_preservation"] = preservation
        result["all_pristine_sources_and_frozen_backend_inputs_unchanged"] = all(row["unchanged"] for row in preservation)
        result["working_source_copy_preservation"] = preserve(copy_bindings)
        result["all_original_files_in_working_source_copies_unchanged"] = all(row["unchanged"] for row in result["working_source_copy_preservation"])
        audit_operations = {"backends-probe": result.get("backend_probe", {})}
        audit_operations.update({name + "-get-requires": data for name, data in hooks.items()})
        audit_operations.update({name + "-build-wheel": data for name, data in builds.items()})
        audit_operations.update({name + "-inspect-wheel": data for name, data in inspections.items()})
        result["audit_decisions_by_operation"] = {name: data.get("audit_decisions", []) for name, data in audit_operations.items()}
        result["allowed_windows_ver_popen_probes"] = sum(data.get("allowed_windows_ver_popen_probes", 0) for data in audit_operations.values())
        result["finished_at_utc"] = utc()
        result["claim_limits"] = ["Original local wheel build/metadata/source-byte evidence only; application imports and native/model execution remain absent", "Prospective exact Windows ver fallback compatibility only; no forced WMI failure/fallback and no confirmed attribution of v1 failure", "Agent JSON omissions are recorded without original packaging repairs; source-root execution remains separate", "Runtime indexed wheels were not installed into this backend-only environment", "Dynamic hooks are captured once and unmet requirements fail without fetch/resolution", "No full combined environment, runtime compatibility, native workflow, domain or checkpoint qualification"]
        if not result["all_pristine_sources_and_frozen_backend_inputs_unchanged"] or not result["all_original_files_in_working_source_copies_unchanged"] or held_jobs:
            result["status"] = "preservation_or_owned_cleanup_unverified"
        result_published = publish_owned_receipt(OUTPUT / "result.json", result)
        if held_jobs and not cli:
            raise OwnedCleanupPending(held_jobs, OUTPUT / "result.json", publication_failures)
        recovery = 0
        while held_jobs:
            ownership_notice({"status": "owned_cleanup_pending_driver_retains_authority", "owned_jobs": len(held_jobs), "initial_result": str(OUTPUT / "result.json"), "initial_result_published": result_published})
            try:
                time.sleep(10)
            except BaseException:
                pass  # CLI cannot abandon native authority when interrupted.
            recovery += 1
            recovered = [cleanup_job(job) for job in list(held_jobs)]
            publish_owned_receipt(OUTPUT / f"owned-cleanup-recovery-{recovery:04d}.json", {"observed_at_utc": utc(), "cleanup": recovered, "owned_job_authority_remaining": bool(held_jobs), "publication_failures": publication_failures})
        if recovery:
            publish_owned_receipt(OUTPUT / "owned-cleanup-terminal.json", {"observed_at_utc": utc(), "status": "all_owned_jobs_qualified_released_after_initial_failure", "owned_job_authority_remaining": False, "initial_result_preserved": True, "initial_result_published": result_published, "publication_failures": publication_failures})
    ownership_notice({"status": result["status"], "source_wheel_builds_attempted": result["source_wheel_builds_attempted"], "error": result["error"], "owned_job_authority_remaining": bool(held_jobs)})
    if publication_failures:
        publish_owned_receipt(OUTPUT / "publication-failures.json", {"status": "receipt_or_output_publication_failed", "initial_result_published": result_published, "owned_job_authority_remaining": bool(held_jobs), "publication_failures": publication_failures})
    return 0 if result["status"] == "three_original_source_wheels_built_and_inspected" and not publication_failures else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--child-action", choices=("probe", "get-requires", "build-wheel", "inspect-wheel"))
    parser.add_argument("--child-input", type=Path)
    args = parser.parse_args()
    if args.child_action:
        if not args.child_input:
            parser.error("Child context path is required.")
        return child(args.child_input, args.child_action)
    if not args.execute:
        parser.error("Use --execute only after the concrete source plan and frozen byte inputs are reviewed.")
    return execute(cli=True)


if __name__ == "__main__":
    raise SystemExit(main())
