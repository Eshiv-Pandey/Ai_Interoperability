"""Prepare, then perform one retained offline AP2 environment installation.

Uses the frozen 184 indexed wheels and three reviewed source-built wheels.
No original role imports, installed .pth startup, credentials or model calls.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import runpy
import shutil
import stat
import struct
import sys
import time
import types
import zipfile


ROOT = Path(__file__).absolute().parents[1]
OUTPUT_NAME = "runs/ap2-environment-preparation/installed-environment-v1"
INPUTS = {
    "wheel_store": ("runs/ap2-environment-preparation/wheel-store-v1/manifest.json", "ac4e3883891a108b141eed6f5bf4cb1e2b97439316f003bd6baeb89ca7ff8689"),
    "runtime_lock": ("runs/ap2-dependency-resolution/indexed-wheel-lock-v1/manifest.json", "d1ed29b81ae3dfd6bc4d89d95d2130e88c0e287a320c77032cbf80888abde106"),
    "source_stage": ("runs/ap2-environment-preparation/source-stage-v1/manifest.json", "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463"),
}
LOCAL_VERSIONS = {"ap2": "0.1", "ap2-samples": "0.1", "x402-a2a": "0.1.0"}
PACKAGES = {"google-adk": "1.28.0", "a2a-sdk": "0.3.24", "google-genai": "1.66.0", "pydantic": "2.12.5"}
JOB_HELPER = ("src/interoperability/windows_owned_job_v1.py", "67b5dc8190aee3a75b3c1954a530d0bba3edeb3bc64dc2770dd815173ecbd53a")


def need(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def notice(value):
    try:
        print(json.dumps(value), flush=True)
    except BaseException:
        pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": digest(raw)}


def regular(path, directory=False):
    path = Path(path)
    need(path.is_absolute(), "Absolute artifact path required")
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400, "Reparse/link paths are refused")
    need(path.is_dir() if directory else path.is_file(), "Expected regular artifact")
    return path


def tree(root):
    regular(root, True)
    result = {}
    for path in sorted(root.rglob("*")):
        regular(path, path.is_dir())
        need("__pycache__" not in path.parts and path.suffix != ".pyc", "Bytecode/cache trees are refused")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = identity(path)
    return result


def read_json(path, expected=None):
    raw = regular(path).read_bytes()
    need(expected is None or digest(raw) == expected, "Pinned input digest differs")
    return json.loads(raw)


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def wheel_metadata(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)), "Duplicate wheel archive members")
        selected = [name for name in names if name.endswith(".dist-info/METADATA") and len(PurePosixPath(name).parts) == 2]
        need(len(selected) == 1, "Exact wheel distribution metadata required")
        raw = archive.read(selected[0])
        value = BytesParser().parsebytes(raw)
        return {"name": normalized(value["Name"]), "version": value["Version"],
                "metadata_sha256": digest(raw), "requires_python": value.get("Requires-Python"),
                "requires_dist": value.get_all("Requires-Dist", [])}


def validate_inputs(root, local_path, local_sha):
    regular(local_path)
    need(local_path.name == "result.json" and local_path.is_relative_to(root / "runs/ap2-environment-preparation"), "Explicit local build receipt must belong to this preparation tree")
    receipts = {key: read_json(root / name, expected) for key, (name, expected) in INPUTS.items()}
    store, lock, source = receipts["wheel_store"], receipts["runtime_lock"], receipts["source_stage"]
    need(store["schema_version"] == "ap2-frozen-wheel-byte-capture/1" and store["status"] == "all_frozen_wheel_bytes_verified"
        and store["unique_artifacts"] == store["verified_artifacts"] == 189 and len(store["artifacts"]) == 189, "Passed complete wheel-store receipt required")
    need(lock["schema_version"] == "ap2-report-derived-wheel-artifact-lock/1" and lock["status"] == "frozen_report_derived_indexed_artifacts"
        and lock["distribution_count"] == len(lock["wheels"]) == 184, "Exact frozen indexed runtime lock required")
    need(source["schema_version"] == "ap2-hp-pristine-source-stage/1" and source["status"] == "pristine_source_stage_created"
        and source["ap2_files"] == 136 and source["x402_files"] == 24 and len(source["files"]) == 160, "Exact pristine source-stage receipt required")
    source_root = root / INPUTS["source_stage"][0]
    source_root = source_root.parent
    expected_source = {}
    for row in source["files"]:
        prefix = "ap2" if row["project"] == "ap2" else "a2a-x402"
        name = prefix + "/" + row["path"]
        need(name not in expected_source, "Duplicate source-stage identity")
        expected_source[name] = {"bytes": row["bytes"], "sha256": row["sha256"]}
    actual_source = {prefix + "/" + name: value for prefix in ("ap2", "a2a-x402") for name, value in tree(source_root / prefix).items()}
    need(actual_source == expected_source, "Pristine source-stage bytes/membership changed")
    store_root = (root / INPUTS["wheel_store"][0]).parent
    artifacts = {row["wheel_filename"]: row for row in store["artifacts"]}
    need(len(artifacts) == 189, "Duplicate stored wheel filename")
    for filename, row in artifacts.items():
        need(Path(filename).name == filename and filename.endswith(".whl") and row["verified"] is True, "Invalid stored wheel record")
        need(identity(regular(store_root / "wheels" / filename)) == {"bytes": row["bytes"], "sha256": row["expected_sha256"]}, "Stored wheel bytes differ")
    local = read_json(local_path, local_sha)
    need(local["schema_version"] in {"ap2-isolated-local-wheel-build-result/1", "ap2-isolated-local-wheel-build-result/2"}
        and local["status"] == "three_original_source_wheels_built_and_inspected", "Passed three-wheel build receipt required")
    need(local.get("source_stage_sha256") == INPUTS["source_stage"][1] and local.get("wheel_store_sha256") == INPUTS["wheel_store"][1], "Local build source/store binding differs")
    need(local.get("all_pristine_sources_and_frozen_backend_inputs_unchanged") is True
        and local.get("all_original_files_in_working_source_copies_unchanged") is True
        and local.get("owned_job_authority_remaining") is False and local.get("source_wheel_builds_attempted") == 3, "Build preservation or owner settlement incomplete")
    need(set(local["builds"]) == set(local["inspections"]) == set(LOCAL_VERSIONS), "Exactly the three original local projects are required")
    need(all(row["unchanged"] is True for key in ("input_preservation", "working_source_copy_preservation") for row in local[key]), "Local build input preservation failed")
    need(local.get("commands") and all(row.get("passed") is True and row["cleanup"].get("job_empty_observed") is True
        and row["cleanup"].get("handles_closed") is True and row["cleanup"].get("errors") == [] for row in local["commands"]), "Local build command ownership is unsettled")
    need(not local_path.parent.joinpath("publication-failures.json").exists(), "Build publication failure retained")
    wheels = []
    for row in lock["wheels"]:
        filename = row["wheel_filename"]
        artifact = artifacts[filename]
        need(artifact["expected_sha256"] == row["sha256"] and normalized(artifact["name"]) == row["normalized_name"] and artifact["version"] == row["version"], "Indexed wheel/lock identity differs")
        wheels.append({"name": row["normalized_name"], "version": row["version"], "source_path": str(store_root / "wheels" / filename),
                       "filename": filename, "sha256": row["sha256"], "bytes": artifact["bytes"], "origin": "frozen_indexed_runtime_lock"})
    for name, version in LOCAL_VERSIONS.items():
        row, inspected = local["builds"][name], local["inspections"][name]
        need(row["status"] == "wheel_built_once" and inspected["status"] == "original_wheel_metadata_and_modules_verified"
            and inspected["wheel_filename"] == row["wheel_filename"] and inspected["wheel_sha256"] == row["wheel_sha256"], "Inspected local wheel identity differs")
        path = local_path.parent / "wheels" / row["wheel_filename"]
        need(Path(row["wheel_filename"]).name == row["wheel_filename"] and identity(regular(path)) == {"bytes": row["wheel_bytes"], "sha256": row["wheel_sha256"]}, "Local wheel bytes differ")
        wheels.append({"name": name, "version": version, "source_path": str(path), "filename": row["wheel_filename"],
                       "sha256": row["wheel_sha256"], "bytes": row["wheel_bytes"], "origin": "pinned_source_local_build"})
    need(len(wheels) == len({row["name"] for row in wheels}) == len({row["filename"] for row in wheels}) == 187, "Exact unique 187 runtime wheels required")
    for row in wheels:
        meta = wheel_metadata(Path(row["source_path"]))
        need(meta["name"] == row["name"] and meta["version"] == row["version"], "Wheel archive metadata identity differs")
        row["metadata"] = meta
    return wheels


def clean_environment(output):
    child = {key: value for key, value in os.environ.items() if not key.upper().startswith(("PYTHON", "PIP_"))}
    child.pop("_PIP_RUNNING_IN_SUBPROCESS", None)
    child.update({"PIP_CONFIG_FILE": "nul", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
                  "TEMP": str(output / "temporary"), "TMP": str(output / "temporary")})
    return child


def prepare(root, output, local_path, local_sha):
    need(sys.platform == "win32" and platform.machine() == "AMD64" and struct.calcsize("P") == 8 and sys.version_info[:2] == (3, 13), "Native Windows AMD64 CPython3.13 required")
    need(re.fullmatch("[0-9a-f]{64}", local_sha or "") is not None, "Pinned passed local-build result digest required")
    regular(output.parent, True)
    need(not output.exists(), "Installed-environment-v1 allocation is consumed")
    need(local_path is not None, "Explicit successful local-build manifest path required")
    wheels = validate_inputs(root, local_path, local_sha)
    helper_path = regular(root / JOB_HELPER[0])
    need(identity(helper_path)["sha256"] == JOB_HELPER[1], "Frozen ownership helper differs")
    pip_wheel = regular(Path(sys.base_prefix) / "Lib/ensurepip/_bundled/pip-24.3.1-py3-none-any.whl")
    output.mkdir()
    for name in ("input-snapshots", "wheels", "tooling", "temporary"):
        (output / name).mkdir()
    snapshots = {key: {"source_path": str(root / name), "sha256": expected} for key, (name, expected) in INPUTS.items()}
    snapshots["local_build"] = {"source_path": str(local_path), "sha256": local_sha}
    for key, value in snapshots.items():
        shutil.copyfile(value["source_path"], output / "input-snapshots" / (key + ".json"))
    driver = Path(__file__).read_bytes()
    (output / "installer-driver.py").write_bytes(driver)
    shutil.copyfile(helper_path, output / "owned-job-helper.py")
    shutil.copyfile(pip_wheel, output / "tooling" / pip_wheel.name)
    requirements = []
    for row in wheels:
        destination = output / "wheels" / row["filename"]
        shutil.copyfile(row["source_path"], destination)
        need(identity(destination) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "Copied runtime wheel bytes differ")
        requirements.append(row["name"] + " @ " + destination.as_uri() + " --hash=sha256:" + row["sha256"])
    requirements_path = output / "runtime-requirements.txt"
    requirements_path.write_bytes(("\n".join(requirements) + "\n").encode())
    envroot = output / "environment"
    envpython = envroot / "Scripts/python.exe"
    piproot = output / "tooling/pip-sources"
    pipargv = [sys.executable, "-I", "-S", "-B", str(output / "installer-driver.py"), "--phase", "pip", "--pip-root", str(piproot), "--",
               "--isolated", "--python", str(envpython), "install", "--prefix", str(envroot), "--no-index", "--no-deps", "--require-hashes", "--no-compile",
               "--ignore-installed", "--only-binary=:all:", "--disable-pip-version-check", "--no-cache-dir", "--no-input", "--report", str(output / "installer-report.json"),
               "-r", str(requirements_path)]
    plan = {"schema_version": "ap2-offline-installed-environment-plan/1", "status": "prepared_without_installation", "created_at_utc": stamp(),
            "project_root": str(root), "output_root": str(output), "local_build_sha256": local_sha, "inputs": snapshots, "wheels": wheels,
            "driver_sha256": digest(driver), "base_interpreter": {"path": sys.executable, **identity(Path(sys.executable)), "version": sys.version},
            "pip_tool": {"source_path": str(pip_wheel), "filename": pip_wheel.name, **identity(pip_wheel), "version": "24.3.1"},
            "owned_job_helper": {"source_path": str(helper_path), "sha256": JOB_HELPER[1]},
            "requirements": identity(requirements_path), "venv_argv": [sys.executable, "-I", "-S", "-B", "-m", "venv", "--without-pip", "--copies", str(envroot)],
            "install_argv": pipargv, "environment_constraints": {"PIP_CONFIG_FILE": "nul", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"},
            "runtime_wheel_count": 187, "indexed_wheel_count": 184, "source_wheel_count": 3,
            "original_application_imported": False, "original_runtime_compatibility_established": False, "model_requests": 0}
    write(output / "plan.json", plan)
    print(json.dumps({"status": plan["status"], "plan": str(output / "plan.json"), "sha256": identity(output / "plan.json")["sha256"], "wheels": 187}))


def settle(job, held_jobs):
    receipt = job.finish(graceful_seconds=0, forced_seconds=5)
    receipt["process_created"] = getattr(job, "created", False)
    if (receipt.get("job_empty_observed") is True or receipt["process_created"] is False) and receipt.get("handles_closed") is True and receipt.get("errors") == []:
        held_jobs.remove(job)
    return receipt


def command(output, name, argv, child_env, timeout, WindowsJob, held_jobs):
    write(output / (name + ".argv.json"), {"argv": argv, "cwd": str(output), "timeout_seconds": timeout})
    result = {"name": name, "started_at_utc": stamp(), "returncode": None, "timed_out": False}
    job = None
    try:
        with (output / (name + ".stdout.bin")).open("xb") as stdout, (output / (name + ".stderr.bin")).open("xb") as stderr:
            job = WindowsJob()
            held_jobs.append(job)
            previous_environment = dict(os.environ)
            try:
                os.environ.clear()
                os.environ.update(child_env)
                result["pid"] = job.launch(argv, str(output), stdout, stderr)
            finally:
                os.environ.clear()
                os.environ.update(previous_environment)
            notice({"command": name, "pid": result["pid"], "status": "owned_command_running"})
            deadline = time.monotonic() + timeout
            while job.poll() is None and time.monotonic() < deadline:
                time.sleep(.1)
            result["returncode"] = job.poll()
            result["timed_out"] = result["returncode"] is None
    except BaseException as error:
        job = job or getattr(error, "owned_job", None)
        if job is not None and job not in held_jobs:
            held_jobs.append(job)
        result["error_type"] = type(error).__name__
    finally:
        if job is not None:
            try:
                result["cleanup"] = settle(job, held_jobs)
            except BaseException as error:
                result["cleanup"] = {"error_type": type(error).__name__, "authority_retained": True}
    result["finished_at_utc"] = stamp()
    result["passed"] = result["returncode"] == 0 and not result["timed_out"] and "error_type" not in result
    result["passed"] = result["passed"] and result.get("cleanup", {}).get("job_empty_observed") is True and result["cleanup"].get("handles_closed") is True and result["cleanup"].get("errors") == []
    write(output / (name + ".result.json"), result)
    return result


def inspect_environment(site, envroot, expected_wheels, initial_files):
    expected = {row["name"]: row for row in expected_wheels}
    distributions, recorded = {}, set()
    for distribution in metadata.distributions(path=[str(site)]):
        name, version = normalized(distribution.metadata["Name"]), distribution.version
        need(name not in distributions and name in expected and version == expected[name]["version"], "Installed distribution membership/version differs")
        meta_path = Path(distribution._path) / "METADATA"
        need(identity(meta_path)["sha256"] == expected[name]["metadata"]["metadata_sha256"], "Installed metadata differs from its selected wheel")
        record_path = Path(distribution._path) / "RECORD"
        rows = list(csv.reader(record_path.read_text(encoding="utf-8").splitlines()))
        for filename, encoded_hash, size in rows:
            path = (site / filename).resolve()
            need(path.is_relative_to(envroot), "Installed RECORD escapes environment")
            regular(path)
            need(path.suffix != ".pyc" and "__pycache__" not in path.parts, "Installed bytecode refused")
            raw = path.read_bytes()
            if encoded_hash:
                algorithm, value = encoded_hash.split("=", 1)
                need(algorithm == "sha256" and base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode() == value and int(size) == len(raw), "Installed RECORD file hash/size differs")
            else:
                need(path == record_path.resolve() and not size, "Unhashed installed file other than RECORD")
            recorded.add(path.relative_to(envroot).as_posix())
        distributions[name] = {"version": version, "metadata_sha256": identity(meta_path)["sha256"], "record_sha256": identity(record_path)["sha256"],
                               "requires_python": distribution.metadata.get("Requires-Python"), "requires_dist": distribution.metadata.get_all("Requires-Dist", []),
                               "wheel_filename": expected[name]["filename"], "wheel_sha256": expected[name]["sha256"], "origin": expected[name]["origin"]}
    need(set(distributions) == set(expected), "Installed environment does not contain exactly187 selected distributions")
    files = tree(envroot)
    need(set(files) - set(initial_files) <= recorded, "Unrecorded installed files found")
    need(all(files[name] == value for name, value in initial_files.items()), "Initial virtual-environment files changed")
    interpreter_bytes = [str(envroot / ("Scripts/" + name)).encode() for name in ("python.exe", "pythonw.exe")]
    script_count = 0
    for name in set(files) - set(initial_files):
        if name.startswith("Scripts/") and name.endswith(".exe"):
            need(any(value in (envroot / name).read_bytes() for value in interpreter_bytes), "Generated console script interpreter differs")
            script_count += 1
        elif name.startswith("Scripts/") and name.endswith(".py"):
            first = (envroot / name).read_bytes().split(b"\n", 1)[0]
            if first.startswith(b"#!"):
                need(any(value in first for value in interpreter_bytes), "Installed script shebang interpreter differs")
                script_count += 1
    return distributions, files, script_count


def execute(output, plan_sha):
    need(re.fullmatch("[0-9a-f]{64}", plan_sha or "") is not None, "Reviewed prepared plan digest required for execution")
    plan = read_json(output / "plan.json", plan_sha)
    need(plan["schema_version"] == "ap2-offline-installed-environment-plan/1" and plan["status"] == "prepared_without_installation" and plan["output_root"] == str(output), "Exact prepared installation plan required")
    need(digest(Path(__file__).read_bytes()) == plan["driver_sha256"] and identity(Path(sys.executable)) == {key: plan["base_interpreter"][key] for key in ("bytes", "sha256")}, "Executed installer/tool interpreter changed")
    root = Path(plan["project_root"])
    local_path = Path(plan["inputs"]["local_build"]["source_path"])
    wheels = validate_inputs(root, local_path, plan["local_build_sha256"])
    need(wheels == plan["wheels"], "Prepared source/wheel selection changed")
    for key, row in plan["inputs"].items():
        need(identity(output / "input-snapshots" / (key + ".json"))["sha256"] == row["sha256"], "Input snapshot changed")
    need(identity(output / "runtime-requirements.txt") == plan["requirements"], "Prepared offline requirements changed")
    need(identity(output / "tooling" / plan["pip_tool"]["filename"]) == {key: plan["pip_tool"][key] for key in ("bytes", "sha256")}, "Copied pip tooling wheel changed")
    helper_bytes = regular(output / "owned-job-helper.py").read_bytes()
    need(digest(helper_bytes) == plan["owned_job_helper"]["sha256"] == JOB_HELPER[1]
        and identity(regular(root / JOB_HELPER[0]))["sha256"] == JOB_HELPER[1], "Copied/original ownership helper changed")
    helper = types.ModuleType("_ap2_installer_owned_job")
    helper.__file__ = str(output / "owned-job-helper.py")
    exec(compile(helper_bytes, helper.__file__, "exec"), helper.__dict__)
    for row in wheels:
        need(identity(output / "wheels" / row["filename"]) == {key: row[key] for key in ("bytes", "sha256")}, "Copied runtime wheel changed")
    write(output / "execution.started.json", {"started_at_utc": stamp(), "plan_sha256": identity(output / "plan.json")["sha256"]})
    commands, failure, held_jobs = [], None, []
    envroot, site = output / "environment", output / "environment/Lib/site-packages"
    try:
        piproot = output / "tooling/pip-sources"
        piproot.mkdir()
        with zipfile.ZipFile(output / "tooling" / plan["pip_tool"]["filename"]) as archive:
            for member in archive.infolist():
                name = PurePosixPath(member.filename)
                need(not name.is_absolute() and ".." not in name.parts and ":" not in member.filename and "\\" not in member.filename
                    and not stat.S_ISLNK(member.external_attr >> 16) and ".pyc" != name.suffix and "__pycache__" not in name.parts, "Unsafe pip tooling archive member")
            archive.extractall(piproot)
        tooling_before = tree(piproot)
        write(output / "pip-tooling-files.json", tooling_before)
        child_env = clean_environment(output)
        commands.append(command(output, "create-venv", plan["venv_argv"], child_env, 120, helper.WindowsJob, held_jobs))
        need(commands[-1]["passed"], "Fresh no-pip virtual environment creation failed")
        initial = tree(envroot)
        need(not any(site.iterdir()) and "include-system-site-packages = false" in (envroot / "pyvenv.cfg").read_text(), "Fresh target site must be empty and isolated")
        write(output / "initial-environment-files.json", initial)
        commands.append(command(output, "offline-install", plan["install_argv"], child_env, 600, helper.WindowsJob, held_jobs))
        need(commands[-1]["passed"], "Offline187-wheel installation failed")
        report = read_json(output / "installer-report.json")
        selected = {(normalized(row["metadata"]["name"]), row["metadata"]["version"]): row for row in report["install"]}
        need(report.get("version") == "1" and len(report["install"]) == len(selected) == 187 and set(selected) == {(row["name"], row["version"]) for row in wheels}, "Pip installation report selection differs")
        for row in wheels:
            download = selected[(row["name"], row["version"])]["download_info"]
            need(download["url"] == (output / "wheels" / row["filename"]).as_uri() and download["archive_info"]["hashes"]["sha256"] == row["sha256"], "Pip report source wheel identity differs")
        distributions, files, script_count = inspect_environment(site, envroot, wheels, initial)
        write(output / "installed-distributions.json", distributions)
        checkargv = [sys.executable, "-I", "-S", "-B", str(output / "installer-driver.py"), "--phase", "pip", "--pip-root", str(piproot), "--site-packages", str(site), "--",
                     "--isolated", "--disable-pip-version-check", "--no-cache-dir", "--no-input", "check"]
        commands.append(command(output, "pip-consistency", checkargv, child_env, 120, helper.WindowsJob, held_jobs))
        need(commands[-1]["passed"], "Installed dependency consistency failed")
        need(validate_inputs(root, local_path, plan["local_build_sha256"]) == wheels, "Original frozen inputs changed during installation")
        need(tree(piproot) == tooling_before, "Extracted installer tooling changed")
        need(identity(output / "runtime-requirements.txt") == plan["requirements"], "Prepared requirements changed during installation")
        for row in wheels:
            need(identity(output / "wheels" / row["filename"]) == {key: row[key] for key in ("bytes", "sha256")}, "Copied wheel bytes changed during installation")
        need(tree(envroot) == files, "Environment bytes changed during isolated pip consistency inspection")
        manifest = {"schema_version": "ap2-hp-native-environment/1", "status": "installed_hash_verified", "platform": "win32", "root": str(envroot), "site_packages": str(site),
                    "interpreter": {"path": str(envroot / "Scripts/python.exe"), "sha256": files["Scripts/python.exe"]["sha256"]}, "packages": {name: distributions[name]["version"] for name in PACKAGES},
                    "files": files, "all_distributions": distributions, "source_receipts": plan["inputs"], "installer_plan_sha256": identity(output / "plan.json")["sha256"],
                    "installer_report_sha256": identity(output / "installer-report.json")["sha256"], "installer_tool": plan["pip_tool"], "base_interpreter": plan["base_interpreter"],
                    "owned_job_helper": plan["owned_job_helper"], "all_tooling_command_jobs_settled": not held_jobs,
                    "external_base_runtime_fully_inventoried": False, "generated_console_script_interpreters_verified": script_count,
                    "indexed_distribution_count": 184, "local_distribution_count": 3, "total_distribution_count": 187, "pip_consistency_passed": True,
                    "installed_pth_executed": False, "original_application_imported": False, "original_runtime_compatibility_established": False, "native_application_executed": False, "model_requests": 0}
        need(manifest["packages"] == PACKAGES, "Native four-pin requirement differs")
        write(output / "environment-manifest.json", manifest)
    except BaseException as error:
        failure = {"error_type": type(error).__name__, "message": str(error)}
    cleanup_retries = []
    for job in list(held_jobs):
        try:
            cleanup_retries.append(settle(job, held_jobs))
        except BaseException as error:
            cleanup_retries.append({"error_type": type(error).__name__, "authority_retained": True})
    # In-process and CLI callers both block with authority retained until every
    # Job is positively empty/closed. No later result construction, output or
    # publication can then lose live ownership.
    while held_jobs:
        notice({"status": "owned_cleanup_pending_installer_retains_authority", "owned_jobs": len(held_jobs)})
        try:
            for job in list(held_jobs):
                try:
                    cleanup_retries.append(settle(job, held_jobs))
                except BaseException as error:
                    cleanup_retries.append({"error_type": type(error).__name__, "authority_retained": True})
        except BaseException:
            pass
        if held_jobs:
            try:
                time.sleep(5)
            except BaseException:
                pass
    result = {"schema_version": "ap2-offline-installed-environment-result/1", "status": "installed_metadata_and_file_hashes_verified" if failure is None else "offline_environment_not_established",
              "finished_at_utc": stamp(), "commands": commands, "failure": failure, "environment_manifest_present": (output / "environment-manifest.json").is_file(),
              "driver_sha256": plan["driver_sha256"], "plan_sha256": identity(output / "plan.json")["sha256"], "original_application_imported": False,
              "cleanup_retries": cleanup_retries, "owned_job_authority_remaining": bool(held_jobs),
              "original_runtime_compatibility_established": False, "installed_pth_executed": False, "model_requests": 0, "native_application_executed": False,
              "claim_limit": "Offline installation, selected distribution metadata/RECORD hashes and dependency consistency only; original import/runtime compatibility remains unverified."}
    try:
        write(output / "result.json", result)
    except BaseException as error:
        failure = failure or {"error_type": type(error).__name__, "message": "Final installer receipt publication failed"}
        result.update(status="result_publication_failed", failure=failure)
        notice({"status": "result_publication_failed", "error_type": type(error).__name__})
    notice({key: result[key] for key in ("status", "failure", "environment_manifest_present")})
    return 0 if failure is None else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "execute", "pip"), default="prepare")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--local-build-sha256")
    parser.add_argument("--local-build-manifest", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--pip-root", type=Path)
    parser.add_argument("--site-packages", type=Path)
    args, pip_args = parser.parse_known_args(argv)
    if args.phase == "pip":
        regular(args.pip_root, True)
        sys.path.insert(0, str(args.pip_root))
        if args.site_packages:
            regular(args.site_packages, True)
            sys.path.insert(1, str(args.site_packages))
        sys.argv = ["pip", *(pip_args[1:] if pip_args[:1] == ["--"] else pip_args)]
        runpy.run_module("pip", run_name="__main__", alter_sys=True)
        return 0
    need(not pip_args, "Unexpected installer arguments")
    output = args.output or args.root / OUTPUT_NAME
    if args.phase == "prepare":
        prepare(args.root, output, args.local_build_manifest, args.local_build_sha256)
        return 0
    return execute(output, args.plan_sha256)


if __name__ == "__main__":
    raise SystemExit(main())
