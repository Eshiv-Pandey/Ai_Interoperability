"""Copy the user archive and extract exact regular files into an isolated tree.

Symlink payloads remain inert evidence, with no symlink creation. No application
import, dependency installation, source modification, deletion or move occurs.
"""
import hashlib
import json
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "agentops-c806b7f1.zip"
COPY = ROOT / "external/downloads/agentops-c806b7f1.zip"
TREE = ROOT / "external/agentops-c806b7f1"
EVIDENCE = ROOT / "docs/research/source-evidence/agentops-local-archive-v1"
OUTPUT = EVIDENCE / "ingestion.json"
COMMIT = "c806b7f1cd0042c9817c0a4c46d80a9a95a24293"
PREFIX = "agentops-open-course-" + COMMIT
ARCHIVE_SHA256 = "491d1c0ee1bd6f54063eb183915b913fc458a277785eeb4ddfcb5efcba20ad0b"
if any(path.exists() for path in [COPY, TREE, OUTPUT, EVIDENCE / "symlink-payloads"]):
    raise SystemExit("Refusing to overwrite/repeat the original source ingestion.")


def receipt(path):
    data = path.read_bytes()
    return {"path": path.resolve().relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def write_bytes(path, data):
    assert path.resolve().is_relative_to(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


data = SOURCE.read_bytes()
assert hashlib.sha256(data).hexdigest() == ARCHIVE_SHA256
plans = []
with zipfile.ZipFile(SOURCE) as archive:
    assert archive.comment.decode("ascii") == COMMIT
    seen = set()
    for member in archive.infolist():
        full = PurePosixPath(member.filename)
        assert full.parts[0] == PREFIX
        assert not full.is_absolute() and ".." not in full.parts
        assert ":" not in member.filename and "\\" not in member.filename
        if member.is_dir():
            continue
        relative = PurePosixPath(*full.parts[1:])
        assert relative.parts
        lowered = str(relative).casefold()
        assert lowered not in seen, str(relative)
        seen.add(lowered)
        for component in relative.parts:
            assert not any(character in component for character in '<>:"\\|?*')
            assert not component.endswith((" ", "."))
            assert component.split(".")[0].upper() not in {
                "CON", "PRN", "AUX", "NUL", *["COM" + str(n) for n in range(1, 10)],
                *["LPT" + str(n) for n in range(1, 10)],
            }
        is_link = stat.S_ISLNK(member.external_attr >> 16)
        destination = (EVIDENCE / "symlink-payloads" if is_link else TREE) / str(relative)
        assert destination.resolve().is_relative_to(EVIDENCE if is_link else TREE)
        plans.append((member, relative, is_link, destination, archive.read(member)))
    assert len(plans) == 423

write_bytes(COPY, data)
assert COPY.read_bytes() == SOURCE.read_bytes()
records = []
for member, relative, is_link, destination, payload in plans:
    write_bytes(destination, payload)
    actual = receipt(destination)
    assert actual["sha256"] == hashlib.sha256(payload).hexdigest()
    records.append({
        "archive_member": member.filename, "source_relative_path": str(relative),
        "kind": "symlink_payload_not_materialized" if is_link else "regular_file",
        "archive_unix_mode": member.external_attr >> 16, "archive_crc32": member.CRC,
        "extracted": actual, "link_target": payload.decode("utf-8") if is_link else None,
    })
assert len([item for item in records if item["kind"] == "regular_file"]) == 421
assert len([item for item in records if item["kind"].startswith("symlink")]) == 2
report = {
    "schema_version": "user-source-archive-ingestion/1", "captured_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "reported_user_source_path": str(SOURCE), "retained_archive": receipt(COPY),
    "requested_download_url": "https://github.com/MLOps-Courses/agentops-open-course/archive/" + COMMIT + ".zip",
    "archive_root_and_comment_commit": COMMIT, "independent_git_object_authentication": False,
    "source_tree": TREE.relative_to(ROOT).as_posix(), "regular_files": 421,
    "symlink_payloads_preserved": 2, "symlinks_created": 0, "is_git_checkout": False,
    "records": records, "all_regular_payload_bytes_match_archive": True,
    "all_archive_file_entries_accounted_for": True, "archive_changed": False,
    "instructions_read_before_extraction": ["AGENTS.md"],
    "application_imports": 0, "application_requests": 0, "dependency_installations": 0,
    "software_tests": 0, "benchmark_archive_replays": 0, "study_model_calls": 0,
    "scope": "Original supplied ZIP and exact regular source bytes, plus inert original link payloads; no complete checkout, authenticated Git tree, installed runtime or native success claim.",
}
with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))
