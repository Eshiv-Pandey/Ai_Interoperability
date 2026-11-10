"""Retain one completed Actions run, metadata and exact ZIP in a fresh allocation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = "Eshiv-Pandey/Ai_Interoperability"


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def command(argv, output, *, limit=180):
    started = datetime.now(timezone.utc).isoformat()
    timed_out = False
    with output.open("xb") as stdout, output.with_suffix(output.suffix + ".stderr").open("xb") as stderr:
        process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL)
        try:
            process.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait(timeout=10)
    write(output.with_suffix(output.suffix + ".receipt.json"),
          {"argv": argv, "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
           "returncode": process.returncode, "timed_out": timed_out, "timeout_seconds": limit,
           "stdout_bytes": output.stat().st_size,
           "stdout_sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    if timed_out or process.returncode:
        raise ValueError("Metadata/archive transfer failed; retained allocation remains consumed")


def retain(run_id, output, artifact_name=None):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "runs"):
        raise ValueError("Require fresh allocation under workspace runs")
    output.mkdir(parents=True)
    write(output / "plan.json", {"run_id": run_id, "repository": REPO, "artifact_name": artifact_name,
          "created_at_utc": datetime.now(timezone.utc).isoformat(), "application_rerun": False})
    command(["gh", "api", f"repos/{REPO}/actions/runs/{run_id}"], output / "github-run.json", limit=60)
    run = json.loads((output / "github-run.json").read_bytes())
    if run["status"] != "completed":
        raise ValueError("Only completed run evidence can be sealed")
    command(["gh", "api", f"repos/{REPO}/actions/runs/{run_id}/artifacts"], output / "github-artifacts.json", limit=60)
    artifacts = json.loads((output / "github-artifacts.json").read_bytes())["artifacts"]
    selected = [a for a in artifacts if artifact_name is None or a["name"] == artifact_name]
    if len(selected) != 1 or selected[0]["expired"]:
        raise ValueError("Require exactly one retained unexpired selected artifact")
    artifact = selected[0]
    if artifact["size_in_bytes"] > 250_000_000:
        raise ValueError("Artifact exceeds bounded allocation")
    archive = output / "artifact.zip"
    command(["gh", "api", f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip"], archive)
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    api_digest = artifact.get("digest")
    if api_digest is not None and api_digest != "sha256:" + archive_digest:
        raise ValueError("Archive differs from GitHub artifact digest")
    base = output / "extracted"
    with zipfile.ZipFile(archive) as source:
        members, seen = [], set()
        total = 0
        for item in source.infolist():
            name = item.filename
            path = PurePosixPath(name)
            total += item.file_size
            if (name in seen or path.is_absolute() or PureWindowsPath(name).drive or ".." in path.parts
                    or "\\" in name or stat.S_ISLNK(item.external_attr >> 16)
                    or not base.joinpath(*path.parts).resolve().is_relative_to(base.resolve())
                    or total > 1_000_000_000):
                raise ValueError("Unsafe or oversized archive member")
            seen.add(name)
            members.append(item)
        base.mkdir()
        inventory = []
        for item in members:
            target = base.joinpath(*PurePosixPath(item.filename).parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            data = source.read(item)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
            inventory.append({"path": item.filename, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    result = {"status": "retained", "run_id": run_id, "head_sha": run["head_sha"],
              "workflow_conclusion": run["conclusion"], "artifact_id": artifact["id"],
              "artifact_name": artifact["name"], "archive_bytes": archive.stat().st_size,
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
              "api_digest": api_digest, "digest_matches_api": api_digest == "sha256:" + archive_digest,
              "extracted_files": len(inventory), "scientific_acceptance": "evaluate individual raw profiles separately"}
    write(output / "extracted-manifest.json", {"files": inventory})
    write(output / "retention.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-name")
    args = parser.parse_args()
    print(json.dumps(retain(args.run_id, args.output, args.artifact_name)))
