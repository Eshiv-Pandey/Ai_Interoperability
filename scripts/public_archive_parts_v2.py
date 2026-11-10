"""Copy an exact retained public archive in bounded parts with small buffers.

The index stays compatible with public_archive_parts_v1.py --restore. This
successor uses a separate directory and preserves any failed V1 copy.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART_BYTES = 32 * 1024 * 1024
BUFFER_BYTES = 256 * 1024


def digest(path):
    value = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(BUFFER_BYTES):
            value.update(block)
            size += len(block)
    return {"bytes": size, "sha256": value.hexdigest()}


def pack(base):
    base = base.resolve()
    if not base.is_relative_to(ROOT / "runs"):
        raise ValueError("Workspace retained run required")
    receipt = json.loads((base / "retention.json").read_bytes())
    archive = base / "artifact.zip"
    if archive.is_symlink():
        raise ValueError("Regular retained archive required")
    whole = digest(archive)
    if (not 0 < whole["bytes"] <= 250_000_000
            or whole != {"bytes": receipt["archive_bytes"], "sha256": receipt["archive_sha256"]}
            or receipt["api_digest"] != "sha256:" + whole["sha256"]):
        raise ValueError("Archive/API byte identity differs")
    output = base / "archive-parts-v2"
    output.mkdir(exist_ok=False)
    records = []
    combined = hashlib.sha256()
    copied = 0
    with archive.open("rb") as source:
        while copied < whole["bytes"]:
            name = f"part-{len(records):04d}.bin"
            part_hash = hashlib.sha256()
            count = 0
            with (output / name).open("xb") as target:
                while count < PART_BYTES:
                    block = source.read(min(BUFFER_BYTES, PART_BYTES - count))
                    if not block:
                        break
                    target.write(block)
                    part_hash.update(block)
                    combined.update(block)
                    count += len(block)
                    copied += len(block)
            if count == 0 or copied > whole["bytes"]:
                raise ValueError("Archive changed during copy; failed output retained")
            records.append({"name": name, "bytes": count, "sha256": part_hash.hexdigest()})
        if source.read(1) or {"bytes": copied, "sha256": combined.hexdigest()} != whole:
            raise ValueError("Archive changed during copy; failed output retained")
    for row in records:
        if digest(output / row["name"]) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise ValueError("Written part differs; failed output retained")
    index = {"schema_version": "public-retained-archive-parts/1", "archive": "artifact.zip",
             "run_id": receipt["run_id"], "api_digest": receipt["api_digest"], "identity": whole,
             "part_byte_limit": PART_BYTES, "parts": records, "original_archive_modified": False,
             "copy_buffer_bytes": BUFFER_BYTES, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    with (output / "index.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(index, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return {"status": "exact_archive_stored_in_streaming_parts", "parts": len(records), "identity": whole}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(pack(args.pack)))
