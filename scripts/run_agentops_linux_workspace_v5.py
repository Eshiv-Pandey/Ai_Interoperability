"""Run an exact, small research-workspace replica on a native Linux filesystem.

The failed /mnt/p installation is preserved. This is a new environment attempt
with its own output namespace. All original application and v4 controller bytes
are copied unchanged. Evidence is exported without rewriting embedded paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile

import agentops_native_probe_v2 as evidence

ROOT = evidence.WORKSPACE
OUTPUT = ROOT / "runs/agentops-native-eligibility/linux-filesystem-v5"
SPEC = "docs/research/source-evidence/agentops-linux-filesystem-v5/protocol.md"
INPUTS = [
    "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json",
    "external/downloads/agentops-c806b7f1.zip",
    "docs/research/source-evidence/agentops-local-archive-v1/symlink-payloads/agents/python/agent",
    "docs/research/source-evidence/agentops-local-archive-v1/symlink-payloads/infra/observability/prometheus-rules.yml",
    "docs/research/source-evidence/agentops-native-probe-v2/protocol.md",
    "docs/research/source-evidence/agentops-native-probe-v4/protocol.md",
    "docs/research/source-evidence/agentops-http-control-v2/protocol.md",
    SPEC,
    "scripts/agentops_native_probe_v2.py", "scripts/agentops_native_probe_v2_plugin.py",
    "scripts/check_agentops_effect_v2.py", "scripts/agentops_native_probe_v4.py",
    "scripts/inspect_agentops_runtime_v4.py", "scripts/run_agentops_linux_v4.py",
    "scripts/agentops_http_control_v2.py", "scripts/agentops_http_bytes_v1.py",
    "scripts/serve_agentops_http_v1.py", "scripts/check_agentops_http_v1.py",
    "tests/test_agentops_http_control_v2.py",
    "scripts/run_agentops_linux_workspace_v5.py", "scripts/run_agentops_wsl_v5.ps1",
]
MAX_EXPORT_BYTES = 512 * 1024 * 1024


def record(path: Path, base: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    return {"path": path.relative_to(base).as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def relative_file(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in {"..", "."} for part in path.parts) or "\\" in name or ":" in name:
        raise ValueError(f"Invalid relative evidence path: {name}")
    candidate = root.joinpath(*path.parts)
    # Reject symlinks at every level, even if their target remains in the root.
    for parent in (candidate, *candidate.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError(f"Evidence symlink is not permitted: {name}")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Evidence path escapes its root: {name}")
    return candidate


def mount_for(path: str, mountinfo: str) -> dict:
    target = PurePosixPath(path)
    matches = []
    for line in mountinfo.splitlines():
        left, separator, right = line.partition(" - ")
        if not separator:
            raise ValueError("Invalid Linux mountinfo row")
        fields = left.split()
        mountpoint = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])
        mount = PurePosixPath(mountpoint)
        if target == mount or mount in target.parents:
            matches.append({"mountpoint": mountpoint, "fstype": right.split()[0]})
    if not matches:
        raise ValueError("Linux filesystem could not be identified")
    return max(matches, key=lambda row: len(PurePosixPath(row["mountpoint"]).parts))


def require_native_filesystem(path: Path) -> dict:
    filesystem = mount_for(path.resolve().as_posix(), Path("/proc/self/mountinfo").read_text())
    if filesystem["fstype"] not in {"ext4", "xfs", "btrfs", "overlay"}:
        raise ValueError(f"Use a Linux disk filesystem, not {filesystem['fstype']}: {path}")
    return filesystem


def copy_exact(source_root: Path, target_root: Path, rows: list[dict]):
    for row in rows:
        source = relative_file(source_root, row["path"])
        if record(source, source_root) != row:
            raise ValueError(f"Source bytes changed: {row['path']}")
        target = relative_file(target_root, row["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as stream, target.open("xb") as output:
            shutil.copyfileobj(stream, output, length=1024 * 1024)
        if record(target, target_root) != row:
            raise ValueError(f"Copied bytes differ: {row['path']}")


def filesystem_probe(root: Path) -> dict:
    import fcntl
    original = root / "filesystem-probe-original"
    renamed = root / "filesystem-probe-renamed"
    original.mkdir(mode=0o700)
    payload = original / "data"
    payload.write_bytes(b"probe")
    with payload.open("rb") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    (original / "link").symlink_to("data")
    original.rename(renamed)
    if (renamed / "link").read_bytes() != b"probe":
        raise ValueError("Linux filesystem rename/symlink check failed")
    return {"mode0700_write": True, "directory_rename": True, "symlink_read": True, "fcntl_lock": True}


def capture(root: Path, label: str, arguments: list[str], timeout: int) -> dict:
    environment = evidence.clean_environment(OUTPUT)
    environment["PYTHONPATH"] = str(root / "scripts")
    environment["AGENTOPS_PROBE_OUTPUT"] = str(root / "runs/unused-controller-environment")
    # All temporary writes by this bootstrap also stay on the Linux filesystem.
    for name in ("TEMP", "TMP", "TMPDIR"):
        environment[name] = str(root / "bootstrap-temp")
    argv = [sys.executable, "-B", "-X", "utf8", *arguments]
    receipt = {"argv": argv, "cwd": str(root), "started_at_utc": evidence.now(), "timed_out": False}
    process = None
    try:
        with (OUTPUT / f"{label}.stdout.bin").open("xb") as stdout, (OUTPUT / f"{label}.stderr.bin").open("xb") as stderr:
            process = subprocess.Popen(argv, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            receipt["linux_pid"] = process.pid
            evidence.write_json(OUTPUT / f"{label}.started.json", receipt)
            try:
                receipt["returncode"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                receipt["timed_out"] = True
                os.killpg(process.pid, signal.SIGKILL)
                receipt["returncode"] = process.wait(timeout=15)
    except BaseException:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=15)
        raise
    finally:
        receipt["finished_at_utc"] = evidence.now()
        receipt["streams"] = [record(OUTPUT / f"{label}.{suffix}.bin", OUTPUT) for suffix in ("stdout", "stderr")
                              if (OUTPUT / f"{label}.{suffix}.bin").is_file()]
        evidence.write_json(OUTPUT / f"{label}.json", receipt)
    return receipt


def referenced_records(value):
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys() and isinstance(value["path"], str):
            yield {key: value[key] for key in ("path", "bytes", "sha256")}
        for child in value.values():
            yield from referenced_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from referenced_records(child)


def export_evidence(root: Path, destination: Path, inputs: list[dict]) -> dict:
    """Export exact source, receipts and explicitly referenced runtime file bytes.

    Relative references resolve inside the exported replica, never the parent
    Windows attempt. Missing/mismatched references are reported, not rewritten.
    """
    selected = {row["path"]: row for row in inputs}
    failures = []
    symlinks = []
    supplemental_sources = set()
    if (root / "runs").exists():
        for path in (root / "runs").rglob("*"):
            if path.is_symlink():
                # Pytest creates convenience *current links. Preserve their
                # literal targets as inert metadata without following/materializing.
                symlinks.append({"path": path.relative_to(root).as_posix(), "target": os.readlink(path)})
            elif path.is_file():
                row = record(path, root)
                selected[row["path"]] = row
    # The runtime inspection is JSON serialized into .stdout.bin, so include
    # those known inspection streams as well as ordinary receipt JSON.
    pending = list(selected)
    inspected = set()
    while pending:
        name = pending.pop()
        if name in inspected:
            continue
        inspected.add(name)
        if not name.startswith("runs/") or not (name.endswith(".json") or name.endswith("runtime.stdout.bin")):
            continue
        path = relative_file(root, name)
        try:
            data = json.loads(path.read_bytes())
        except (UnicodeError, ValueError):
            continue
        for row in referenced_records(data):
            try:
                referenced = relative_file(root, row["path"])
                if not referenced.is_file() or record(referenced, root) != row:
                    raise ValueError(f"Missing/changed referenced bytes: {row['path']}")
                previous = selected.get(row["path"])
                if previous is not None and previous != row:
                    raise ValueError(f"Conflicting retained hashes: {row['path']}")
                if previous is None:
                    selected[row["path"]] = row
                    pending.append(row["path"])
            except (OSError, ValueError) as error:
                failures.append(str(error))
        if isinstance(data, dict) and "fcntl_extension" in data:
            item = data["fcntl_extension"]
            try:
                module = Path(item["path"])
                name = module.relative_to(root).as_posix()
                row = record(relative_file(root, name), root)
                if row["sha256"] != item["sha256"]:
                    raise ValueError("Native fcntl bytes changed")
                selected[name] = row
            except (OSError, ValueError) as error:
                failures.append(str(error))
        if isinstance(data, dict) and data.get("schema_version") == "agentops-installed-runtime-inspection/4":
            # Preserve terminal installed source bytes for the next converter/
            # version-fidelity analysis, separately from pre-execution pin claims.
            folders = {"google-adk": "google/adk/a2a", "a2a-sdk": "a2a/compat"}
            for package in data["packages"]:
                if package["name"] not in folders:
                    continue
                folder_name = package["location"] + "/" + folders[package["name"]]
                folder = relative_file(root, folder_name)
                for module in folder.rglob("*.py"):
                    name = module.relative_to(root).as_posix()
                    row = record(relative_file(root, name), root)
                    selected.setdefault(name, row)
                    supplemental_sources.add(name)
    rows = sorted(selected.values(), key=lambda row: row["path"])
    total = sum(row["bytes"] for row in rows)
    if total > MAX_EXPORT_BYTES:
        raise ValueError(f"Evidence export exceeds {MAX_EXPORT_BYTES} bytes; Linux original retained at {root}")
    destination.mkdir(parents=True, exist_ok=False)
    copy_exact(root, destination, rows)
    return {"files": rows, "bytes": total, "inert_symlinks": symlinks,
            "post_execution_runtime_source_files": sorted(supplemental_sources),
            "reference_failures": sorted(set(failures)),
            "original_linux_root": str(root), "export_root": str(destination),
            "scope": "Exact inputs, run outputs and referenced runtime bytes; not a complete executable runtime"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-parent", type=Path, default=Path("/tmp"))
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() != "x86_64" or platform.libc_ver()[0] != "glibc":
        raise ValueError("Run in Ubuntu Linux x86_64 with glibc and Python >=3.11")
    filesystem = require_native_filesystem(args.linux_parent)
    prior_path = ROOT / "runs/agentops-native-eligibility/dependencies-linux-v4/result.json"
    prior = evidence.load_json(prior_path)
    if (prior.get("status") != "failed" or prior.get("stage") != "locked-sync"
            or prior.get("source_unchanged_after") is not True):
        raise ValueError("Expected the retained terminal v4 installation failure before this recovery")
    for row in prior["files"]:
        if record(relative_file(ROOT, row["path"]), ROOT) != row:
            raise ValueError("Prior installation failure evidence changed")
    source = evidence.source_inventory()
    names = sorted({row["path"] for row in source} | set(INPUTS))
    inputs = [record(relative_file(ROOT, name), ROOT) for name in names]
    OUTPUT.mkdir(parents=True, exist_ok=False)
    state = {"schema_version": "agentops-linux-filesystem-attempt/5", "status": "failed",
             "started_at_utc": evidence.now(), "filesystem": filesystem,
             "prior_attempt": record(prior_path, ROOT),
             "native_result": "not_run", "http_result": "not_run", "live_model_calls": 0,
             "qualified_second_domain": False, "research_gate_credit_added": 0}
    evidence.write_json(OUTPUT / "execution.json", {**state, "inputs": inputs})
    replica = None
    try:
        replica = Path(tempfile.mkdtemp(prefix="agentops-research-v5-", dir=args.linux_parent)).resolve()
        state["linux_workspace"] = str(replica)
        evidence.write_json(OUTPUT / "linux-workspace.json", {"path": str(replica), "filesystem": filesystem})
        state["filesystem_probe"] = filesystem_probe(replica)
        (replica / "bootstrap-temp").mkdir()
        copy_exact(ROOT, replica, inputs)
        print(f"Executing from Linux filesystem: {replica}", flush=True)
        print(f"Logs and exported evidence: {OUTPUT}", flush=True)
        state["stage"] = "native-setup-and-control"
        native = capture(replica, "native-pipeline", ["scripts/run_agentops_linux_v4.py"], 3600)
        native_path = replica / "runs/agentops-native-eligibility/native-probe-v4/result.json"
        if native_path.exists():
            state["native_result"] = evidence.load_json(native_path)["status"]
        if native["returncode"] != 0 or state["native_result"] != "upstream_and_boundary_effect_check_passed":
            raise ValueError("Native setup/control did not pass; preserve this attempt")
        state["stage"] = "http-prepare"
        prepared = capture(replica, "http-prepare", ["scripts/agentops_http_control_v2.py", "prepare"], 120)
        if prepared["returncode"] != 0:
            raise ValueError("HTTP preparation failed; no HTTP execution requested")
        state["stage"] = "http-control"
        http = capture(replica, "http-control", ["scripts/agentops_http_control_v2.py", "run"], 600)
        http_path = replica / "runs/agentops-http-control/native-http-linux-v2/result.json"
        if http_path.exists():
            state["http_result"] = evidence.load_json(http_path)["status"]
        if http["returncode"] != 0 or state["http_result"] != "wire_and_effect_check_passed":
            raise ValueError("HTTP control did not pass; preserve this attempt")
        state["status"] = "native_and_http_controls_passed"
    except (Exception, KeyboardInterrupt) as error:
        state["error"] = f"{type(error).__name__}: {error}"
    finally:
        if replica is not None:
            try:
                exported = export_evidence(replica, OUTPUT / "workspace", inputs)
                evidence.write_json(OUTPUT / "export-manifest.json", exported)
                state["exported_files"] = len(exported["files"])
                state["export_reference_failures"] = exported["reference_failures"]
                if exported["reference_failures"]:
                    state["status"] = "failed_evidence_export"
            except Exception as error:
                state["status"] = "failed_evidence_export"
                state["export_error"] = f"{type(error).__name__}: {error}"
        try:
            state["parent_inputs_unchanged"] = all(record(ROOT / row["path"], ROOT) == row for row in inputs)
        except Exception:
            state["parent_inputs_unchanged"] = False
        if not state["parent_inputs_unchanged"]:
            state["status"] = "failed_parent_integrity"
        state["finished_at_utc"] = evidence.now()
        evidence.write_json(OUTPUT / "result.json", state)
    print(json.dumps(state, indent=2), flush=True)
    if state["status"] != "native_and_http_controls_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
