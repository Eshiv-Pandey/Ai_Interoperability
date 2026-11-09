"""Read the user-supplied ZIP without extracting or importing application code."""
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

SOURCE = Path(r"P:\JUNKK\Also Junk\sem_7\agentops-c806b7f1.zip")
COMMIT = "c806b7f1cd0042c9817c0a4c46d80a9a95a24293"
EXPECTED_ROOT = "agentops-open-course-" + COMMIT
data = SOURCE.read_bytes()
with zipfile.ZipFile(SOURCE) as archive:
    members = archive.infolist()
    roots = {PurePosixPath(item.filename).parts[0] for item in members}
    assert roots == {EXPECTED_ROOT}, roots
    filenames = [item.filename for item in members]
    assert len(filenames) == len(set(filenames))
    for item in members:
        parts = PurePosixPath(item.filename).parts
        assert not PurePosixPath(item.filename).is_absolute()
        assert ".." not in parts and "\\" not in item.filename and ":" not in item.filename
        assert not stat.S_ISLNK(item.external_attr >> 16), item.filename
    print(json.dumps({
        "source": str(SOURCE), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "expected_root": EXPECTED_ROOT, "root_label_matches_requested_commit": True,
        "zip_comment_utf8": archive.comment.decode("utf-8", errors="replace"),
        "entries": len(members), "files": sum(not item.is_dir() for item in members),
        "uncompressed_bytes": sum(item.file_size for item in members),
        "crc_check_first_error": archive.testzip(),
        "instructions": [item.filename for item in members if PurePosixPath(item.filename).name == "AGENTS.md"],
        "git_metadata_present": any(".git" in PurePosixPath(item.filename).parts for item in members),
        "extraction_performed": False, "application_execution": False,
        "source_pin_independently_authenticated": False,
    }, indent=2))
    for item in members:
        if PurePosixPath(item.filename).name == "AGENTS.md":
            print("\nInstructions: " + item.filename + "\n")
            print(archive.read(item).decode("utf-8"))
