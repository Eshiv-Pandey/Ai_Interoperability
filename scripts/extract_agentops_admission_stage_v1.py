"""Extract a checked source bundle into one new Linux admission workspace."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2); handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reuse-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    destination = Path(manifest["linux_workspace"])
    if sys.platform != "linux" or not re.fullmatch(r"/var/tmp/agentops-admission-live-v1-[0-9a-f]{16}", str(destination)):
        raise ValueError("Expected a fresh, explicitly allocated Linux admission root")
    if destination.exists() or args.receipt.exists():
        raise FileExistsError("Never overwrite a staging attempt")
    if destination.is_relative_to(args.reuse_root.resolve()) or args.reuse_root.resolve().is_relative_to(destination):
        raise ValueError("Source allocation and reused runtime must be disjoint")
    archive_bytes = args.archive.read_bytes()
    if hashlib.sha256(archive_bytes).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Archive changed after source capture")
    records = {row["path"]: row for row in manifest["files"]}
    if len(records) != len(manifest["files"]):
        raise ValueError("Duplicate staged path")
    for name in records:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name or "\\" in name:
            raise ValueError("Unsafe staged path")
    with tarfile.open(args.archive, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) != len(records) or {member.name for member in members} != set(records):
            raise ValueError("Archive inventory differs from source plan")
        # Verify every member before creating the destination.
        for member in members:
            if not member.isfile() or member.size != records[member.name]["bytes"]:
                raise ValueError("Nonregular or wrong-sized archive member")
            raw = archive.extractfile(member).read()
            if hashlib.sha256(raw).hexdigest() != records[member.name]["sha256"]:
                raise ValueError("Archive member hash mismatch")
        destination.mkdir(mode=0o700)
        for member in members:
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(archive.extractfile(member).read())
    group = destination / "runs/agentops-admission-live-v1"
    group.mkdir(parents=True)
    write(group / "stage-manifest.json", manifest)
    interpreter = args.reuse_root / "external/runtime-agentops-linux-v7/venv/bin/python"
    inspector = args.reuse_root / "scripts/inspect_agentops_runtime_v6.py"
    if inspector.read_bytes() != (destination / "scripts/inspect_agentops_runtime_v6.py").read_bytes():
        raise ValueError("Reused read-only inspector differs from the staged source")
    argv = [str(interpreter), "-I", "-B", str(inspector)]
    with (group / "python-runtime-before.json").open("xb") as stdout, (group / "python-runtime-before.stderr.bin").open("xb") as stderr:
        child = subprocess.run(argv, cwd=args.reuse_root, stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr, timeout=120)
    inspection = json.loads((group / "python-runtime-before.json").read_bytes()) if child.returncode == 0 else {}
    unchanged = all(hashlib.sha256((destination / row["path"]).read_bytes()).hexdigest() == row["sha256"]
                    for row in records.values())
    passed = child.returncode == 0 and inspection.get("application_imports") == 0 and unchanged
    result = {"schema_version": "agentops-admission-stage-result/1", "status": "passed" if passed else "failed",
        "linux_workspace": str(destination), "staged_files": len(records), "source_unchanged": unchanged,
        "runtime_inspection_argv": argv, "runtime_inspection_returncode": child.returncode,
        "runtime_inspector_sha256": hashlib.sha256(inspector.read_bytes()).hexdigest(),
        "runtime_inspection": str(group / "python-runtime-before.json"),
        "application_requests": 0, "application_imports": 0, "live_model_calls": 0}
    write(args.receipt, result)
    print(json.dumps(result))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
