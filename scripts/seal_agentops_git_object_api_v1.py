"""Seal the failed acquisition response and user clarification; no app execution."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "docs/research/source-evidence/agentops-git-object-api-v1"
MANIFEST = SCREEN / "manifest.json"
OUTPUT = SCREEN.parent / "agentops-git-object-api-v1-verification.json"
if MANIFEST.exists() or OUTPUT.exists():
    raise SystemExit("Refusing to replace or repeat the acquisition receipt.")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def receipt(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), str(path)
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


query = read(SCREEN / "query.json")
result = read(SCREEN / "tool-response.json")
assert query["open"][0]["ref_id"].endswith(
    "/git/trees/c806b7f1cd0042c9817c0a4c46d80a9a95a24293?recursive=1")
assert result["isError"] is False
assert "is not accessible via this tool" in result["content"][0]["text"]
context = read(SCREEN / "user-acquisition-context.json")
assert context["archive_inspected"] is context["user_reported_completed_download"] is False
assert context["requested_workspace_relative_path"] == "agentops-c806b7f1.zip"
links = []
for target in re.findall(r"\]\(([^)]+)\)", (SCREEN / "decision.md").read_text(encoding="utf-8")):
    if not target.startswith(("http://", "https://", "#")):
        links.append(receipt(SCREEN / target.split("#", 1)[0])["path"])
files = set(SCREEN.iterdir()) | {Path(__file__).resolve(),
    ROOT / "paper/continuation-integrity-v6.json", ROOT / "paper/draft-audit-v1.1.json"}
assert all(path.is_file() for path in files)
for path in files:
    if path.suffix == ".json":
        read(path)
write_new(MANIFEST, {
    "schema_version": "failed-acquisition-receipt-manifest/1",
    "sealed_at_utc": datetime.now(UTC).isoformat(), "files": [receipt(path) for path in sorted(files)],
    "original_source_bytes_acquired": False, "acquisition_requests": 1,
    "representation": "Exact serialized web-tool query/result plus user clarification and local analytical decision",
    "scope": "Access failure and acquisition target only; no absent-API/application, source-pin authenticity or scientific claim.",
})
for item in read(MANIFEST)["files"]:
    assert receipt(ROOT / item["path"]) == item
report = {
    "schema_version": "failed-acquisition-receipt-verification/1",
    "checked_at_utc": datetime.now(UTC).isoformat(), "status": "passed",
    "manifest": receipt(MANIFEST), "files_checked": len(files),
    "local_links_checked": len(links), "inaccessible_response_retained": True,
    "original_source_bytes_acquired": False, "application_execution": False,
    "new_application_requests": 0, "new_model_calls": 0, "new_tests": 0,
    "new_installations": 0, "new_archive_replays": 0, "candidate_performance_trials": 0,
    "checkpoint_progress_percent": 5, "novelty_demonstrated": False,
    "human_review_completed": False, "user_download_pending": True,
}
write_new(OUTPUT, report)
print(json.dumps(report, indent=2))
