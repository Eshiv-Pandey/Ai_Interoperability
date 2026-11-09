"""Capture current source and create a fresh WSL workspace; never launch an app."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2); handle.write("\n")


def mounted(path):
    path = str(path.resolve()).replace("\\", "/")
    if len(path) < 3 or path[1:3] != ":/":
        raise ValueError("Expected an absolute Windows drive path")
    return "/mnt/" + path[0].lower() + path[2:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-root", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "runs"):
        parser.error("Use a new output directory inside workspace runs")
    sys.path.insert(0, str(ROOT / "scripts"))
    import agentops_admission_live_plan_v2 as design
    ingestion_path = ROOT / design.PINNED_DOCS[0]
    ingestion = json.loads(ingestion_path.read_bytes())
    app = [row["extracted"] for row in ingestion["records"] if row["kind"] == "regular_file"]
    if len(app) != 421:
        raise ValueError("Expected the exact original app source inventory")
    selected = {ROOT / row["path"] for row in app}
    selected.update(ROOT / name for name in design.PINNED_DOCS)
    for folder in ("scripts", "tests", "src/interoperability"):
        selected.update(path for path in (ROOT / folder).iterdir() if path.is_file() and path.suffix in (".py", ".mjs"))
    for folder in ("examples/refinement-development", "examples/benchmark-development"):
        selected.update(path for path in (ROOT / folder).rglob("*") if path.is_file())
    selected = sorted(selected)
    records = []
    for path in selected:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError("Stage only regular workspace-owned files")
        raw = path.read_bytes()
        records.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest()})
    actual = {row["path"]: row for row in records}
    if any(actual[row["path"]] != row for row in app):
        raise ValueError("Original application source changed")
    output.mkdir(parents=True)
    archive_path = output / "source.tar.gz"
    with tarfile.open(archive_path, "x:gz") as archive:
        for path, row in zip(selected, records, strict=True):
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Source changed while capturing stage")
            item = tarfile.TarInfo(row["path"]); item.size = len(raw); item.mode = 0o600
            archive.addfile(item, io.BytesIO(raw))
    manifest = {"schema_version": "agentops-admission-stage/1",
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "linux_workspace": "/var/tmp/agentops-admission-live-v1-" + uuid.uuid4().hex[:16],
        "reuse_root": args.reuse_root, "files": records,
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "application_requests": 0, "live_model_calls": 0}
    manifest_path = output / "stage-plan.json"
    write(manifest_path, manifest)
    argv = ["wsl.exe", "-d", "Ubuntu", "--", "python3", "-I", "-B",
        mounted(ROOT / "scripts/extract_agentops_admission_stage_v1.py"),
        "--archive", mounted(archive_path), "--manifest", mounted(manifest_path),
        "--reuse-root", args.reuse_root, "--receipt", mounted(output / "linux-stage.json")]
    with (output / "stdout.bin").open("xb") as stdout, (output / "stderr.bin").open("xb") as stderr:
        child = subprocess.run(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=180)
    unchanged = all(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"] for row in records)
    result = {"schema_version": "agentops-admission-stage-parent/1",
        "status": "passed" if child.returncode == 0 and unchanged else "failed", "returncode": child.returncode,
        "source_unchanged": unchanged, "linux_workspace": manifest["linux_workspace"],
        "argv": argv, "application_requests": 0, "live_model_calls": 0}
    write(output / "result.json", result)
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
