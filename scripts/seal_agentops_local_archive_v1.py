"""Seal exact source/archive retention and the failed setup; no application run."""
import hashlib
import json
import re
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "docs/research/source-evidence/agentops-local-archive-v1"
TREE = ROOT / "external/agentops-c806b7f1"
MANIFEST = SCREEN / "manifest.json"
OUTPUT = SCREEN.parent / "agentops-local-archive-v1-verification.json"
if MANIFEST.exists() or OUTPUT.exists():
    raise SystemExit("Refusing to replace or repeat the local archive seal.")


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


ingestion = read(SCREEN / "ingestion.json")
assert ingestion["status"] == "passed" and ingestion["regular_files"] == 421
assert ingestion["symlink_payloads_preserved"] == 2 and ingestion["symlinks_created"] == 0
archive_path = ROOT / ingestion["retained_archive"]["path"]
assert receipt(archive_path) == ingestion["retained_archive"]
assert archive_path.read_bytes() == (ROOT.parent / "agentops-c806b7f1.zip").read_bytes()
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    for item in ingestion["records"]:
        path = ROOT / item["extracted"]["path"]
        assert receipt(path) == item["extracted"]
        assert archive.read(item["archive_member"]) == path.read_bytes()
assert len(ingestion["records"]) == 423
assert sorted(path.relative_to(TREE).as_posix() for path in TREE.rglob("AGENTS.md")) == ["AGENTS.md"]
assert not (TREE / "agents/python/agent").exists()
project = tomllib.loads((TREE / "agents/python/pyproject.toml").read_text(encoding="utf-8"))
lock = tomllib.loads((TREE / "agents/python/uv.lock").read_text(encoding="utf-8"))
assert project["project"]["version"] == "0.11.0"
assert project["project"]["requires-python"] == ">=3.13,<3.14"
packages = {item["name"]: item["version"] for item in lock["package"]}
assert packages["google-adk"] == "2.10.0" and packages["a2a-sdk"] == "1.1.5"
assert "MIT License" in (TREE / "agents/LICENSE").read_text(encoding="utf-8")
assert "test_a2a_confirmation_response_resumes_the_guarded_action_with_audit_identity" in (TREE / "agents/python/tests/test_server.py").read_text(encoding="utf-8")
setup = read(ROOT / "runs/agentops-native-eligibility/v1/result.json")
assert setup["steps_executed"] == ["bootstrap"] and setup["upstream_test_executed"] is False
bootstrap = read(ROOT / "runs/agentops-native-eligibility/v1/bootstrap.json")
assert bootstrap["exit_code"] == 1 and "No matching distribution" in bootstrap["stderr_utf8"]
for stream in bootstrap["streams"]:
    assert receipt(ROOT / stream["path"]) == stream
assert read(SCREEN / "initial-inspection-tool-response.json")["exit_code"] == 1
assert "UnicodeEncodeError" in read(SCREEN / "encoding-inspection-tool-response.json")["output"]
assert read(SCREEN / "utf8-inspection-tool-response.json")["exit_code"] == 0
links = []
for target in re.findall(r"\]\(([^)]+)\)", (SCREEN / "decision.md").read_text(encoding="utf-8")):
    if not target.startswith(("http://", "https://", "#")):
        links.append(receipt(SCREEN / target.split("#", 1)[0])["path"])
files = {path for path in SCREEN.rglob("*") if path.is_file()}
files |= {path for path in TREE.rglob("*") if path.is_file()}
files |= {path for path in (ROOT / "runs/agentops-native-eligibility/v1").iterdir() if path.is_file()}
files |= {archive_path, Path(__file__).resolve()}
files |= {ROOT / "scripts" / name for name in [
    "inspect_agentops_archive_v1.py", "inspect_agentops_archive_v1_1.py", "ingest_agentops_archive_v1.py",
    "prepare_agentops_native_v1.py", "setup_agentops_dependencies_v2.ps1",
]}
for path in files:
    if path.suffix == ".json":
        read(path)
write_new(MANIFEST, {
    "schema_version": "agentops-original-local-source-manifest/1", "sealed_at_utc": datetime.now(UTC).isoformat(),
    "files": [receipt(path) for path in sorted(files)], "archive_member_payloads_checked": 423,
    "original_local_source_bytes_available": True, "independent_git_object_authentication": False,
    "symlinks_materialized": False, "setup_succeeded": False,
    "scope": "Exact supplied source/archive and inert symlink bytes; retained setup failure; no native success or complete checkout/runtime/scientific claim.",
})
for item in read(MANIFEST)["files"]:
    assert receipt(ROOT / item["path"]) == item
report = {
    "schema_version": "agentops-original-local-source-verification/1", "checked_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "manifest": receipt(MANIFEST), "files_checked": len(files),
    "archive_member_payloads_checked": 423, "regular_source_files_checked": 421,
    "inert_symlink_payloads_checked": 2, "instructions_files_checked": 1,
    "local_document_links_checked": len(links), "source_pin_label_matches_requested_commit": True,
    "independent_git_object_authentication": False, "dependency_versions_checked": {
        "application": "0.11.0", "google-adk": "2.10.0", "a2a-sdk": "1.1.5"},
    "initial_symlink_and_encoding_failures_retained": True, "failed_bootstrap_streams_retained": True,
    "application_execution": False, "new_application_requests": 0, "new_model_calls": 0,
    "new_tests": 0, "new_archive_replays": 0, "successful_dependency_installations": 0,
    "dependency_bootstrap_attempts": 1, "normal_terminal_setup_prepared_not_executed": True,
    "qualified_second_domain": False, "novelty_demonstrated": False,
    "human_review_completed": False, "checkpoint_progress_percent": 5,
}
write_new(OUTPUT, report)
print(json.dumps(report, indent=2))
