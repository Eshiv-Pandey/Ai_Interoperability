"""Store/restore exact public retained archives in bounded Git-sized parts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART_BYTES = 32 * 1024 * 1024


def digest(path):
    value, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
            size += len(block)
    return {"bytes": size, "sha256": value.hexdigest()}


def pack(base):
    base = base.resolve()
    if not base.is_relative_to(ROOT / "runs"):
        raise ValueError("Workspace retained run required")
    receipt = json.loads((base / "retention.json").read_bytes())
    archive = base / "artifact.zip"
    whole = digest(archive)
    if whole != {"bytes": receipt["archive_bytes"], "sha256": receipt["archive_sha256"]} or receipt["api_digest"] != "sha256:" + whole["sha256"]:
        raise ValueError("Archive/API byte identity differs")
    output = base / "archive-parts-v1"
    output.mkdir(exist_ok=False)
    records = []
    with archive.open("rb") as stream:
        while block := stream.read(PART_BYTES):
            name = f"part-{len(records):04d}.bin"
            with (output / name).open("xb") as target:
                target.write(block)
            records.append({"name": name, "bytes": len(block), "sha256": hashlib.sha256(block).hexdigest()})
    index = {"schema_version": "public-retained-archive-parts/1", "archive": "artifact.zip",
        "run_id": receipt["run_id"], "api_digest": receipt["api_digest"], "identity": whole,
        "part_byte_limit": PART_BYTES, "parts": records, "original_archive_modified": False}
    with (output / "index.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(index, stream, indent=2)
        stream.write("\n")
    return {"status": "exact_archive_stored_in_parts", "parts": len(records), "identity": whole}


def restore(index_path):
    index_path = index_path.resolve()
    if not index_path.is_relative_to(ROOT / "runs"):
        raise ValueError("Workspace part index required")
    index = json.loads(index_path.read_bytes())
    if index["schema_version"] != "public-retained-archive-parts/1" or index["archive"] != "artifact.zip":
        raise ValueError("Unsupported archive index")
    combined, total = hashlib.sha256(), 0
    for number, row in enumerate(index["parts"]):
        if row["name"] != f"part-{number:04d}.bin" or type(row["bytes"]) is not int or not 0 < row["bytes"] <= PART_BYTES:
            raise ValueError("Invalid bounded part sequence")
        part = index_path.parent / row["name"]
        if part.is_symlink() or digest(part) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise ValueError("Part identity differs")
        with part.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                combined.update(block)
                total += len(block)
        if total > 250_000_000:
            raise ValueError("Archive bound exceeded")
    whole = {"bytes": total, "sha256": combined.hexdigest()}
    if whole != index["identity"] or index["api_digest"] != "sha256:" + whole["sha256"]:
        raise ValueError("Combined archive/API identity differs")
    archive = index_path.parent.parent / "artifact.zip"
    if archive.exists():
        if archive.is_symlink() or digest(archive) != whole:
            raise ValueError("Existing archive differs; no overwrite")
        return {"status": "existing_exact_archive_verified", "identity": whole}
    with archive.open("xb") as target:
        for row in index["parts"]:
            with (index_path.parent / row["name"]).open("rb") as source:
                while block := source.read(1024 * 1024):
                    target.write(block)
    if digest(archive) != whole:
        raise ValueError("Restored archive differs; failed output retained")
    return {"status": "exact_archive_restored", "identity": whole}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pack", type=Path)
    mode.add_argument("--restore", type=Path)
    args = parser.parse_args()
    print(json.dumps(pack(args.pack) if args.pack else restore(args.restore)))
