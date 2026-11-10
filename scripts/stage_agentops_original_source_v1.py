"""Stage only missing checksum-pinned original files before constructed controls."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

from ci_agentops_admission_v1 import ROOT, SOURCE_SHA, extract_source, fetch, now, regular_bytes, sha, source_records, verified_source, write_new

INGESTION = "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json"
SOURCE = "external/agentops-c806b7f1"


def publish_missing(staged, checkout, rows):
    source = checkout / SOURCE
    if source.is_symlink():
        raise ValueError("Original checkout root cannot be a symlink")
    expected = {row["path"]: row for row in rows}
    present = {path.relative_to(checkout).as_posix() for path in source.rglob("*") if path.is_file()} if source.exists() else set()
    if not present <= expected.keys() or any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Checkout contains unpinned source files or symlinks")
    # Preflight every existing member and every destination before any write.
    missing = []
    for row in rows:
        target = checkout / row["path"]
        if not target.resolve().is_relative_to(source.resolve()):
            raise ValueError("Original destination escapes intended source root")
        if target.exists():
            raw = regular_bytes(target)
            if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
                raise ValueError("Existing source member differs; never overwrite: " + row["path"])
        else:
            missing.append(row)
        staged_raw = regular_bytes(staged / row["path"])
        if len(staged_raw) != row["bytes"] or sha(staged_raw) != row["sha256"]:
            raise ValueError("Staged source member differs")
    for row in missing:
        target = checkout / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(regular_bytes(staged / row["path"]))
    verified_source(checkout, rows)
    return {"source_files": len(rows), "existing_files_verified_without_overwrite": len(present),
        "missing_files_exclusively_created": len(missing), "missing_paths": [row["path"] for row in missing],
        "all_original_source_bytes_verified": True}


def execute(output):
    if sys.platform != "linux" or platform.machine() != "x86_64" or os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise ValueError("Source staging requires the standard hosted Linux checkout")
    if output.exists() or not output.resolve().is_relative_to(ROOT / "runs/ci-agentops-source-stage-v1"):
        raise ValueError("Use a fresh source-stage allocation")
    output.mkdir(parents=True)
    result = {"schema_version": "agentops-original-source-stage/1", "status": "failed",
        "started_at_utc": now(), "application_imports": 0, "application_requests": 0,
        "provider_calls": 0, "source_archive_sha256": SOURCE_SHA,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_sha": os.environ.get("GITHUB_SHA")}
    try:
        ingestion = json.loads(regular_bytes(ROOT / INGESTION))
        if ingestion["retained_archive"]["sha256"] != SOURCE_SHA or len(source_records(ingestion)) != 421:
            raise ValueError("Original source ingestion pin differs")
        archive = output / "original-agentops.zip"
        fetch(ingestion["requested_download_url"], archive, SOURCE_SHA, 5_000_000)
        with tempfile.TemporaryDirectory(prefix="agentops-control-source-stage-", dir="/var/tmp") as allocated:
            staged = Path(allocated)
            rows = extract_source(archive, staged, ingestion)
            result.update(publish_missing(staged, ROOT, rows))
            write_new(output / "original-source-manifest.json", {"files": rows})
        with (output / "staging-source.py").open("xb") as target:
            target.write(Path(__file__).read_bytes())
        result["status"] = "original_source_staged_without_overwrite"
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result["finished_at_utc"] = now()
        write_new(output / "result.json", result)
        files = [{"path": path.relative_to(output).as_posix(), "bytes": len(path.read_bytes()), "sha256": sha(path.read_bytes())}
            for path in sorted(output.rglob("*")) if path.is_file() and not path.is_symlink()]
        write_new(output / "manifest.json", {"files": files})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute(args.output.resolve())
