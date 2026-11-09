"""Audit the v6 context integration while preserving all sealed prior evidence."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper/continuation-integrity-v6.json"
if OUTPUT.exists():
    raise SystemExit("Refusing to overwrite the v6 audit.")


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def receipt(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), relative
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


pre_path = "paper/continuation-pre-edit-integrity-v6.json"
pre = read(pre_path)
assert pre["status"] == "passed" and pre["changed_files_before_edit"] == []
mapping = {item["original"]: item["snapshot"] for item in pre["mutable_record_snapshots"]}
assert len(mapping) == 6
for item in pre["mutable_record_snapshots"]:
    actual = receipt(item["snapshot"])
    assert actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"]
assert receipt(pre["prior_integrity_report"]["path"]) == pre["prior_integrity_report"]
historical = []
for item in pre["verified_inputs"]:
    path = mapping.get(item["path"], item["path"])
    actual = receipt(path)
    assert actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"], item["path"]
    historical.append({"original": item["path"], "checked_path": path,
                       "bytes": actual["bytes"], "sha256": actual["sha256"],
                       "v6_snapshot_used": path != item["path"]})
assert len(historical) == pre["prior_input_entries_checked"] + pre["prior_current_records_checked"]
assert len(pre["stable_paper_files"]) == 12
for item in pre["stable_paper_files"]:
    assert receipt(item["path"]) == item
draft_path = "paper/draft-audit-v1.1.json"
draft = read(draft_path)
assert draft["status"] == "passed" and draft["draft_words"] == 4216
assert draft["claims_with_evidence_paths"] == 23 and draft["references"] == 18
assert draft["new_service_requests"] == draft["new_model_calls"] == 0
current = []
for item in draft["files"]:
    assert receipt(item["path"]) == item, item["path"]
    current.append({"report": draft_path, **item})
screen_path = "docs/research/source-evidence/origin-surface-closure-v1-verification.json"
screen = read(screen_path)
assert screen["status"] == "passed" and screen["source_copy_pairs_checked"] == 26
assert screen["coverage_complete"] is screen["source_to_runtime_closure_verified"] is False
assert screen["application_execution"] is screen["novelty_demonstrated"] is False
assert receipt(screen["manifest"]["path"]) == screen["manifest"] == pre["new_screen_manifest"]
for item in read(screen["manifest"]["path"])["files"]:
    assert receipt(item["path"]) == item, item["path"]
    current.append({"report": screen["manifest"]["path"], **item})
index = read("docs/research/source-evidence/origin-surface-closure-v1/source-index.json")
for item in index["entries"]:
    assert receipt(item["copy"]["path"]) == item["copy"]
    assert receipt(item["original"]["path"]) == item["original"]
    assert item["copy"]["sha256"] == item["original"]["sha256"]
checkpoint = read("docs/research/checkpoint-status.json")
cp2 = next(item for item in checkpoint["checkpoints"] if item["id"] == "CP2")
cp7 = next(item for item in checkpoint["checkpoints"] if item["id"] == "CP7")
assert cp2["status"] == "in_progress" and cp7["status"] == "pending"
assert checkpoint["progress_percent"] == 5
assert checkpoint["novelty_demonstrated"] is checkpoint["human_review_completed"] is False
assert cp7["latest_working_draft"] == "../../paper/working-draft-v1.md"
assert "source-evidence/origin-surface-closure-v1-verification.json" in cp2["evidence"]
assert "../../paper/draft-audit-v1.json" in cp7["evidence"]
assert "../../paper/continuation-integrity-v5.json" in cp7["evidence"]
evidence_paths = []
for cp in [cp2, cp7]:
    assert len(cp["evidence"]) == len(set(cp["evidence"]))
    for relative in cp["evidence"]:
        resolved = (ROOT / "docs/research" / relative).resolve().relative_to(ROOT).as_posix()
        evidence_paths.append(receipt(resolved)["path"])
links = []
documents = [relative for relative in mapping if relative.endswith(".md")] + [
    "paper/working-draft-v1.md", "paper/references-v2.md",
    "docs/research/source-evidence/origin-surface-closure-v1/decision.md",
]
for relative in documents:
    document = ROOT / relative
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (document.parent / target.split("#", 1)[0]).resolve().relative_to(ROOT).as_posix()
        links.append({"document": relative, "target": receipt(path)["path"]})
record_paths = list(mapping) + [
    "scripts/update_continuation_records_v6.py", "scripts/audit_continuation_integrity_v6.py",
    pre_path, pre["prior_integrity_report"]["path"], draft_path, screen_path,
] + [item["path"] for item in pre["stable_paper_files"]]
report = {
    "schema_version": "continuation-retained-integrity/6", "checked_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "historical_entries_checked": len(historical),
    "historical_entries_using_v6_snapshots": sum(item["v6_snapshot_used"] for item in historical),
    "current_file_entries_checked": len(current), "source_copy_pairs_checked": len(index["entries"]),
    "stable_v0_v1_paper_files_unchanged": 12, "mutable_snapshots": pre["mutable_record_snapshots"],
    "draft_words": 4216, "claims": 23, "references": 18,
    "checkpoint_evidence_paths_checked": len(evidence_paths), "document_links_checked": len(links),
    "historical_checks": historical, "current_checks": current,
    "current_records": [receipt(relative) for relative in dict.fromkeys(record_paths)],
    "new_application_requests": 0, "new_model_calls": 0, "new_tests": 0,
    "new_archive_replays": 0, "new_installations": 0, "candidate_performance_trials": 0,
    "novelty_demonstrated": False, "human_review_completed": False,
    "checkpoint_progress_percent": 5, "goal_complete": False,
    "scope": "Historical retention, exact local sources, unchanged papers and context/link consistency; no source-to-runtime or complete-negative proof, benchmark or scientific review.",
}
with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: value for key, value in report.items() if key not in [
    "historical_checks", "current_checks", "current_records", "mutable_snapshots",
]}, indent=2))
