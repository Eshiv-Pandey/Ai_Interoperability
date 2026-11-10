"""Prepare and execute a separately labelled hosted-Linux N11 -> B7 profile.

--check-inputs is standard-library, read-only and platform-independent. --execute
is restricted to a standard GitHub-hosted Linux x86_64 runner. Existing source,
admission, request and acceptance implementations are copied without changes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import signal
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_INPUT = ROOT / "docs/research/source-evidence/agentops-bridge-control-v1/runtime"
SOURCE_SHA = "491d1c0ee1bd6f54063eb183915b913fc458a277785eeb4ddfcb5efcba20ad0b"
BRIDGE_SHA = "c4567dc405e74d664921f038e6c5acb454c66fd85f42f21c04a10c8e75305864"
HISTORICAL_MATERIALIZATION_SHA = "81d67fde696f90e44fead36b5759e6722f1a0216b496d5a395fef472ea14ca5d"
PYTHON = "3.13.1"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def regular_bytes(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular input: " + str(path))
    return path.read_bytes()


def source_records(ingestion):
    rows = [row["extracted"] for row in ingestion["records"] if row["kind"] == "regular_file"]
    if len(rows) != 421 or len({row["path"] for row in rows}) != 421:
        raise ValueError("Expected exactly 421 unique preserved original source files")
    for row in rows:
        name = PurePosixPath(row["path"])
        if (not row["path"].startswith("external/agentops-c806b7f1/") or name.is_absolute()
                or ".." in name.parts or str(name) != row["path"] or "\\" in row["path"]):
            raise ValueError("Unsafe original source path")
    return rows


def check_inputs():
    sys.path.insert(0, str(ROOT / "scripts"))
    import agentops_admission_live_plan_v3 as design
    from agentops_bridge_runtime_archive_v1 import check_graph, safe_name
    # The old WSL materialization is a reference only. A fresh receipt is
    # generated for the CI runtime and staged at this verifier input path.
    files = [ROOT / name for name in design.PINNED_DOCS if name != design.PINNED_DOCS[2]]
    files += [RUNTIME_INPUT / "archive.json", RUNTIME_INPUT / "runtime.zip"]
    files += [ROOT / "scripts" / name for name in design.REQUIRED_SCRIPTS]
    files += [ROOT / "scripts/inspect_agentops_runtime_v6.py",
              ROOT / "scripts/extract_agentops_admission_stage_v1.py"]
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file() or path.is_symlink()]
    if missing:
        raise ValueError("Missing or nonregular CI inputs: " + ", ".join(missing))
    ingestion = json.loads(regular_bytes(ROOT / design.PINNED_DOCS[0]))
    source_records(ingestion)
    if ingestion["retained_archive"]["sha256"] != SOURCE_SHA:
        raise ValueError("Original AgentOps archive pin changed")
    expected_url = "https://github.com/MLOps-Courses/agentops-open-course/archive/c806b7f1cd0042c9817c0a4c46d80a9a95a24293.zip"
    if ingestion["requested_download_url"] != expected_url:
        raise ValueError("Original AgentOps source URL changed")
    raw_graph = regular_bytes(RUNTIME_INPUT / "graph.json")
    graph = json.loads(raw_graph)
    nodes = check_graph(graph)
    if any(node["license"] not in ("MIT", "Apache-2.0") for node in nodes.values()):
        raise ValueError("Hosted archive may include only reviewed MIT/Apache-2.0 nodes")
    archive = json.loads(regular_bytes(RUNTIME_INPUT / "archive.json"))
    raw_archive = regular_bytes(RUNTIME_INPUT / "runtime.zip")
    if (archive["status"] != "archive_verified" or archive["archive_sha256"] != BRIDGE_SHA
            or sha(raw_archive) != BRIDGE_SHA or len(raw_archive) != archive["bytes"]
            or sha(raw_graph) != archive["graph_sha256"]):
        raise ValueError("Pinned bridge archive/graph seal mismatch")
    expected = {row["path"]: row for row in graph["files"]}
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as stream:
        infos = stream.infolist()
        if len(infos) != len(expected) + 1 or {item.filename for item in infos} != set(expected) | {"graph.json"}:
            raise ValueError("Bridge archive inventory changed")
        for item in infos:
            safe_name(item.filename)
            if item.is_dir() or item.flag_bits & 1 or ((item.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError("Nonregular or encrypted bridge archive member")
            raw = stream.read(item)
            if item.filename == "graph.json":
                if raw != raw_graph:
                    raise ValueError("Archived graph differs")
            elif len(raw) != expected[item.filename]["bytes"] or sha(raw) != expected[item.filename]["sha256"]:
                raise ValueError("Bridge archive file changed: " + item.filename)
        for node in nodes.values():
            if not any(PurePosixPath(row["path"]).name.lower().startswith("license") for row in node["files"]):
                raise ValueError("A bridge dependency has no retained license file")
    return {"status": "inputs_verified", "source_files": 421, "bridge_packages": len(nodes),
            "bridge_files": len(expected), "bridge_archive_sha256": BRIDGE_SHA,
            "bridge_archive_bytes": len(raw_archive), "source_archive_sha256": SOURCE_SHA,
            "application_imports": 0, "application_requests": 0, "live_model_calls": 0}


def fetch(url, path, expected_sha, max_bytes, timeout=90):
    deadline = time.monotonic() + timeout
    request = urllib.request.Request(url, headers={"User-Agent": "agentops-hosted-research-v1"})
    with urllib.request.urlopen(request, timeout=30) as response, path.open("xb") as target:
        count = 0
        while block := response.read(1024 * 1024):
            count += len(block)
            if count > max_bytes or time.monotonic() > deadline:
                raise ValueError("Pinned download exceeded its size/time bound")
            target.write(block)
    if sha(path.read_bytes()) != expected_sha:
        raise ValueError("Pinned download checksum mismatch: " + path.name)


def verified_source(root, rows):
    app = root / "external/agentops-c806b7f1"
    actual = {path.relative_to(root).as_posix() for path in app.rglob("*") if path.is_file()}
    if actual != {row["path"] for row in rows} or any(path.is_symlink() for path in app.rglob("*")):
        raise ValueError("Original source inventory changed")
    for row in rows:
        raw = regular_bytes(root / row["path"])
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("Original source bytes changed: " + row["path"])


def extract_source(archive, root, ingestion):
    rows = source_records(ingestion)
    members = {row["archive_member"]: row for row in ingestion["records"] if row["kind"] == "regular_file"}
    with zipfile.ZipFile(archive) as stream:
        if len({item.filename for item in stream.infolist()}) != len(stream.infolist()):
            raise ValueError("Duplicate original archive member")
        for name, record in members.items():
            info = stream.getinfo(name)
            if info.is_dir() or info.flag_bits & 1 or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError("Original regular source member changed kind")
            raw = stream.read(info)
            row = record["extracted"]
            if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
                raise ValueError("Original archive source hash mismatch")
            target = root / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(raw)
    verified_source(root, rows)
    return rows


def process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return int(fields[1]), fields[19]
    except (OSError, IndexError, ValueError):
        return None


def terminate_descendants(process):
    # Each original native child owns a new session. Follow parent identities
    # before terminating so a coordinator timeout cannot leave those sessions.
    selected = {process.pid: process_identity(process.pid)}
    changed = True
    while changed:
        changed = False
        for path in Path("/proc").iterdir():
            if not path.name.isdecimal():
                continue
            pid = int(path.name)
            identity = process_identity(pid)
            if identity and identity[0] in selected and pid not in selected:
                selected[pid] = identity
                changed = True
    killed = []
    for pid, identity in reversed(list(selected.items())):
        if identity is not None and process_identity(pid) == identity:
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
            except ProcessLookupError:
                pass
    return killed


def capture(argv, output, label, cwd, environment, timeout):
    item = {"argv": [str(value) for value in argv], "cwd": str(cwd), "started_at_utc": now(),
            "returncode": None, "timed_out": False}
    write_new(output / (label + ".started.json"), item)
    print("Starting " + label, flush=True)
    with (output / (label + ".stdout.bin")).open("xb") as stdout, (output / (label + ".stderr.bin")).open("xb") as stderr:
        child = subprocess.Popen(item["argv"], cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr, start_new_session=True)
        item["pid"] = child.pid
        try:
            item["returncode"] = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            item["timed_out"] = True
            item["forced_cleanup_pids"] = terminate_descendants(child)
            item["returncode"] = child.wait(timeout=15)
    item["finished_at_utc"] = now()
    item["streams"] = [{"path": label + "." + suffix + ".bin",
                        "sha256": sha((output / (label + "." + suffix + ".bin")).read_bytes())}
                       for suffix in ("stdout", "stderr")]
    write_new(output / (label + ".receipt.json"), item)
    print(label + " returned " + str(item["returncode"]), flush=True)
    if item["returncode"] != 0 or item["timed_out"]:
        raise ValueError(label + " failed; allocated evidence is retained and never retried")
    return item


def execute(output):
    if (sys.platform != "linux" or platform.machine() != "x86_64"
            or os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        raise ValueError("Execution requires a GitHub-hosted Linux x86_64 runner")
    if not output.resolve().is_relative_to(ROOT / "runs/ci-agentops-native") or output.exists():
        raise ValueError("Use a new allocation under runs/ci-agentops-native")
    output.mkdir(parents=True, exist_ok=False)
    fresh = None
    coordinator_deadline = time.monotonic() + 1110
    report = {"schema_version": "agentops-hosted-native-profile/1", "status": "failed", "started_at_utc": now(),
              "profile": "standard-github-hosted-ubuntu-24.04", "original_wsl_host_identity_claimed": False,
              "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
              "github_sha": os.environ.get("GITHUB_SHA"), "runner_image": os.environ.get("ImageOS"),
              "python_selection": PYTHON, "node_selection": "22.13.0",
              "application_acceptance": "unchanged preparation/3 and control/3",
              "live_model_calls": 0, "research_gate_credit_added": 0}
    try:
        report["inputs"] = check_inputs()
        write_new(output / "inputs.json", report["inputs"])
        memory = {line.split(":", 1)[0]: int(line.split()[1]) * 1024
                  for line in Path("/proc/meminfo").read_text().splitlines() if len(line.split()) == 3}
        report["resource_sample"] = {key: memory.get(key) for key in ("MemAvailable", "SwapFree", "CommitLimit", "Committed_AS")}
        # A separate Linux backing-memory gate does not reinterpret the failed
        # local Windows resource gate. Two GiB of physical backing is required.
        if memory.get("MemAvailable", 0) < 2 * 1024**3:
            raise ValueError("Hosted profile requires at least 2 GiB available physical RAM")
        report["stage"] = "source-download"
        sys.path.insert(0, str(ROOT / "scripts"))
        import agentops_admission_live_plan_v3 as design
        from agentops_bridge_runtime_archive_v1 import materialize, verify_runtime
        ingestion = json.loads((ROOT / design.PINNED_DOCS[0]).read_bytes())
        reuse = Path("/var/tmp/agentops-research-v7-ci-" + uuid.uuid4().hex[:16])
        reuse.mkdir(mode=0o700)
        report["reuse_root"] = str(reuse)
        archive = output / "original-agentops.zip"
        fetch(ingestion["requested_download_url"], archive, SOURCE_SHA, 5_000_000)
        rows = extract_source(archive, reuse, ingestion)
        for name in ("scripts/inspect_agentops_runtime_v6.py",):
            target = reuse / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(regular_bytes(ROOT / name))
        runtime = reuse / "external/runtime-agentops-linux-v7"
        runtime.mkdir()
        pin_entries = tomllib.loads((reuse / "external/agentops-c806b7f1/mise.lock").read_text())["tools"]["aqua:astral-sh/uv"]
        if len(pin_entries) != 1 or pin_entries[0]["version"] != "0.12.0":
            raise ValueError("Original uv version pin changed")
        pin = pin_entries[0]["platforms.linux-x64"]
        url = "https://github.com/astral-sh/uv/releases/download/0.12.0/uv-x86_64-unknown-linux-gnu.tar.gz"
        if pin["url"] != url or not pin["checksum"].startswith("sha256:"):
            raise ValueError("Original uv download pin changed")
        report["stage"] = "pinned-python-and-locked-dependencies"
        uv_archive = output / "uv-linux.tar.gz"
        fetch(url, uv_archive, pin["checksum"][7:], 50_000_000)
        uv = runtime / "uv"
        with tarfile.open(uv_archive, "r:gz") as stream:
            selected = [member for member in stream.getmembers() if member.name == "uv-x86_64-unknown-linux-gnu/uv"]
            if len(selected) != 1 or not selected[0].isfile() or selected[0].size > 100_000_000:
                raise ValueError("Expected one regular pinned uv executable")
            with uv.open("xb") as handle:
                handle.write(stream.extractfile(selected[0]).read())
        uv.chmod(0o755)
        environment = {key: value for key, value in os.environ.items()
                       if not key.upper().startswith(("PYTHON", "GOOGLE_", "OPENAI_", "GEMINI_", "AGENT_", "OTEL_"))}
        environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PYTHONUTF8="1", OTEL_SDK_DISABLED="true",
                           UV_PROJECT_ENVIRONMENT=str(runtime / "venv"), UV_CACHE_DIR=str(runtime / "cache"),
                           UV_PYTHON_INSTALL_DIR=str(runtime / "python"), UV_PYTHON_BIN_DIR=str(runtime / "bin"),
                           UV_HTTP_TIMEOUT="30", UV_HTTP_RETRIES="0", UV_PYTHON_DOWNLOADS="automatic", UV_LINK_MODE="copy")
        capture([uv, "--version"], output, "uv-version", reuse, environment, 15)
        if not (output / "uv-version.stdout.bin").read_text().strip().startswith("uv 0.12.0"):
            raise ValueError("Pinned uv executable version differs")
        capture([uv, "sync", "--locked", "--project", reuse / "external/agentops-c806b7f1/agents/python",
                 "--python", PYTHON, "--python-preference", "only-managed"], output, "locked-sync", reuse, environment, 480)
        verified_source(reuse, rows)
        python = runtime / "venv/bin/python"
        setup_receipt = reuse / "runs/agentops-native-eligibility/dependencies-linux-v7/result.json"
        setup_receipt.parent.mkdir(parents=True)
        write_new(setup_receipt, {"schema_version": "agentops-ci-locked-dependencies/1", "status": "dependencies_ready",
                                 "python_selection": PYTHON, "uv_version": "0.12.0", "finished_at_utc": now(),
                                 "source_unchanged_after": True, "ci_receipt": str(output / "locked-sync.receipt.json"),
                                 "ci_receipt_sha256": sha((output / "locked-sync.receipt.json").read_bytes()),
                                 "original_wsl_setup_receipt_reused": False})
        with (output / "ci-setup-receipt.json").open("xb") as handle:
            handle.write(setup_receipt.read_bytes())
        capture([Path("/usr/bin/node"), "--version"], output, "node-version", reuse, environment, 15)
        report["node_version"] = (output / "node-version.stdout.bin").read_text().strip()
        if report["node_version"] != "v22.13.0":
            raise ValueError("Hosted profile requires Node22.13.0 at the original /usr/bin/node path")
        report["stage"] = "fresh-bridge-materialization"
        materialized = materialize(RUNTIME_INPUT, reuse, reuse / "external/runtime-agentops-bridges-v1")
        graph = json.loads((RUNTIME_INPUT / "graph.json").read_bytes())
        report["bridge"] = verify_runtime(reuse / "external/runtime-agentops-bridges-v1", graph, materialized)
        write_new(output / "ci-materialization.json", materialized)
        report["historical_materialization_reference_sha256"] = HISTORICAL_MATERIALIZATION_SHA
        report["historical_materialization_loaded_or_identity_claimed"] = False
        report["ci_materialization_sha256"] = sha((output / "ci-materialization.json").read_bytes())
        report["stage"] = "source-staging"
        selected = {row["path"]: reuse / row["path"] for row in rows}
        selected.update({name: ROOT / name for name in design.PINNED_DOCS if name != design.PINNED_DOCS[2]})
        selected[design.PINNED_DOCS[2]] = output / "ci-materialization.json"
        for folder in ("scripts", "src/interoperability"):
            selected.update({path.relative_to(ROOT).as_posix(): path for path in (ROOT / folder).rglob("*")
                             if path.is_file() and path.suffix in (".py", ".mjs")})
        selected.update({path.relative_to(ROOT).as_posix(): path for path in (ROOT / "tests").iterdir()
                         if path.is_file() and path.suffix in (".py", ".mjs")})
        for folder in ("examples/refinement-development", "examples/benchmark-development"):
            selected.update({path.relative_to(ROOT).as_posix(): path for path in (ROOT / folder).rglob("*") if path.is_file()})
        records = []
        source_bundle = output / "source.tar.gz"
        with tarfile.open(source_bundle, "x:gz") as stream:
            for name, path in sorted(selected.items()):
                raw = regular_bytes(path)
                records.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})
                item = tarfile.TarInfo(name)
                item.size, item.mode = len(raw), 0o600
                stream.addfile(item, io.BytesIO(raw))
        fresh = Path("/var/tmp/agentops-admission-live-v1-" + uuid.uuid4().hex[:16])
        manifest = {"schema_version": "agentops-admission-stage/1", "prepared_at_utc": now(),
                    "linux_workspace": str(fresh), "reuse_root": str(reuse), "files": records,
                    "archive_sha256": sha(source_bundle.read_bytes()), "application_requests": 0, "live_model_calls": 0}
        write_new(output / "stage-plan.json", manifest)
        report["linux_workspace"] = str(fresh)
        capture([python, "-I", "-B", ROOT / "scripts/extract_agentops_admission_stage_v1.py",
                 "--archive", source_bundle, "--manifest", output / "stage-plan.json", "--reuse-root", reuse,
                 "--receipt", output / "stage-result.json"], output, "stage", ROOT, environment, 120)
        report["stage"] = "unchanged-native-and-admitted-chain"
        if coordinator_deadline - time.monotonic() < 680:
            raise ValueError("Provisioning left insufficient time for the unchanged native chain and evidence retention")
        capture([python, "-B", fresh / "scripts/run_agentops_admission_chain_v3.py", "--workspace", fresh,
                 "--export-output", output / "export"], output, "chain", fresh, environment, 650)
        final = json.loads((fresh / "runs/agentops-admission-live-v1/attempt/result.json").read_bytes())
        report["original_attempt_status"] = final["status"]
        report["cases"] = final.get("cases", [])
        if final["status"] != "strict_success":
            raise ValueError("Original independent acceptance did not establish strict success")
        verified_source(reuse, rows)
        report["status"] = "strict_success"
        report["stage"] = "complete"
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if report["status"] != "strict_success" and fresh is not None and fresh.is_dir():
            # A failed or timed-out chain may have no terminal export. Preserve
            # regular raw files as an explicitly unqualified failure snapshot.
            captured = []
            try:
                for name in ("runs/agentops-admission-live-v1", "runs/agentops-http-control/admission-live-v1-N11",
                             "runs/agentops-http-control/admission-live-v1-B7"):
                    subtree = fresh / name
                    if subtree.is_symlink():
                        raise ValueError("Failure evidence subtree is a symlink")
                    for path in sorted(subtree.rglob("*")):
                        if path.is_symlink():
                            raise ValueError("Failure evidence contains a symlink")
                        if path.is_file():
                            relative = path.relative_to(fresh)
                            raw = regular_bytes(path)
                            target = output / "failure-snapshot" / relative
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with target.open("xb") as handle:
                                handle.write(raw)
                            captured.append({"path": relative.as_posix(), "bytes": len(raw), "sha256": sha(raw)})
                write_new(output / "failure-snapshot.json", {"status": "unqualified_failure_snapshot", "files": captured,
                          "terminal_integrity_or_acceptance_claimed": False})
            except Exception as error:
                report["failure_snapshot_error"] = type(error).__name__ + ": " + str(error)
        report["finished_at_utc"] = now()
        write_new(output / "result.json", report)
        print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "strict_success" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-inputs", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_inputs:
        print(json.dumps(check_inputs(), indent=2))
        return 0
    if args.output is None:
        parser.error("--execute requires a new --output")
    return execute(args.output.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
