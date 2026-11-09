"""Snapshot v6 context and integrate local acquisition with a new retention audit."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "docs/research/snapshots/continuation-v7"
PRE = ROOT / "paper/continuation-pre-edit-integrity-v7.json"
OUTPUT = ROOT / "paper/continuation-integrity-v7.json"
PRIOR = ROOT / "paper/continuation-integrity-v6.json"
RECORDS = ["RESEARCH_WORKFLOW.md", "docs/research/execution-handoff.md",
           "docs/research/implementation-novelty-gate.md", "docs/research/cp2-review-packet-v1.md",
           "docs/research/checkpoint-status.json", "paper/draft-status-v1.json"]
if any(path.exists() for path in [SNAPSHOTS, PRE, OUTPUT]):
    raise SystemExit("Refusing to repeat or overwrite continuation-v7.")


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


prior = read(PRIOR)
assert prior["status"] == "passed"
checks = []
for item in prior["historical_checks"]:
    actual = receipt(ROOT / item["checked_path"])
    assert actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"], item["checked_path"]
    checks.append(actual)
for item in prior["current_checks"] + prior["current_records"]:
    actual = receipt(ROOT / item["path"])
    assert actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"], item["path"]
    checks.append(actual)
current = []
screen_paths = ["docs/research/source-evidence/agentops-local-archive-v1-verification.json",
                "docs/research/source-evidence/agentops-git-object-api-v1-verification.json"]
for relative in screen_paths:
    screen = read(ROOT / relative)
    assert screen["status"] == "passed" and screen["application_execution"] is False
    assert receipt(ROOT / screen["manifest"]["path"]) == screen["manifest"]
    for item in read(ROOT / screen["manifest"]["path"])["files"]:
        assert receipt(ROOT / item["path"]) == item, item["path"]
        current.append({"report": screen["manifest"]["path"], **item})
archive_screen = read(ROOT / screen_paths[0])
assert archive_screen["archive_member_payloads_checked"] == 423
assert archive_screen["regular_source_files_checked"] == 421
assert archive_screen["normal_terminal_setup_prepared_not_executed"] is True
stable = [receipt(ROOT / item["path"]) for item in read(ROOT / "paper/continuation-pre-edit-integrity-v6.json")["stable_paper_files"]]
assert len(stable) == 12
snapshots = []
for relative in RECORDS:
    target = SNAPSHOTS / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write((ROOT / relative).read_bytes())
    actual = receipt(target)
    assert target.read_bytes() == (ROOT / relative).read_bytes()
    snapshots.append({"original": relative, "snapshot": actual["path"],
                      "bytes": actual["bytes"], "sha256": actual["sha256"]})
write_new(PRE, {
    "schema_version": "continuation-pre-edit-integrity/7", "checked_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "prior_integrity_report": receipt(PRIOR), "verified_inputs": checks,
    "mutable_record_snapshots": snapshots, "stable_paper_files": stable,
    "changed_files_before_edit": [], "scope": "Retained evidence and exact pre-edit copies; no app or model.",
})
summary = (
    "Original AgentOps source acquisition is now resolved by the user-supplied\n"
    "commit-labeled ZIP. All 423 file entries are accounted for: 421 exact regular\n"
    "files and two inert symlink payloads. The local source/archive package passes\n"
    "a 440-file integrity check. Archive root/comment pin labels are distinct\n"
    "from independently authenticated Git objects; no complete checkout/runtime\n"
    "equivalence is claimed. Root AGENTS.md was read before extraction. The\n"
    "source still supports the original same-task DataPart confirmation and\n"
    "local transactional service/audit lead. The two inspector failures are\n"
    "retained. A once-only uv bootstrap failed with no distribution candidates;\n"
    "the runtime has PIP_NO_INDEX=1 and no required package/cache. No lock sync,\n"
    "native test, application request or model call ran. A checksum-pinned\n"
    "normal-terminal setup script is prepared and syntax-checked, unexecuted\n"
    "here. Source bytes no longer block; locked dependencies, native/card/wire,\n"
    "unchanged bridge qualification, independent task validity and C1 novelty\n"
    "remain open. No second-domain qualification or gate credit is added."
)
updates = {
    "RESEARCH_WORKFLOW.md": ("## 1. Research direction and what changes",
        "\n\n**Original AgentOps archive (25 October):**\n"
        "[Local source/setup record](docs/research/source-evidence/agentops-local-archive-v1/decision.md).\n" + summary),
    "docs/research/implementation-novelty-gate.md": ("## What the fresh source audit changes",
        "\n\n[AgentOps local archive/setup v1](source-evidence/agentops-local-archive-v1/decision.md)\n" + summary),
    "docs/research/cp2-review-packet-v1.md": ("## Claims currently rejected",
        "\n\n**AgentOps archive/setup addendum (25 October):**\n"
        "[Exact source and retained failure](source-evidence/agentops-local-archive-v1/decision.md).\n" + summary),
    "docs/research/execution-handoff.md": ("**Latest continuation update (25 October 2026):**",
        "\n\n- [AgentOps original local archive/setup v1](source-evidence/agentops-local-archive-v1/decision.md)\n"
        + "\n".join("  " + line for line in summary.splitlines())
        + "\n  Retained ZIP: external/downloads/agentops-c806b7f1.zip. Source tree:\n"
        "  external/agentops-c806b7f1. Failed setup: runs/agentops-native-eligibility/v1.\n"
        "  Next resource step: user runs scripts/setup_agentops_dependencies_v2.ps1\n"
        "  in normal PowerShell; inspect its dependencies-v2 receipts before a\n"
        "  separately versioned upstream/native control. Never rerun v1 or overwrite\n"
        "  existing source/seals. The API failure is historical and the earlier\n"
        "  no-local-archive statement is superseded. Six records are snapshotted\n"
        "  under continuation-v7; five context records change. Both v0/v1 paper,\n"
        "  claim/status and references remain unchanged. CP2 open, CP7 pending,\n"
        "  original goal active and verified credit 5%."),
}
for relative, (anchor, addition) in updates.items():
    original = (ROOT / relative).read_text(encoding="utf-8")
    assert original.count(anchor) == 1
    (ROOT / relative).write_text(original.replace(anchor, anchor + addition, 1), encoding="utf-8", newline="\n")
checkpoint_path = ROOT / "docs/research/checkpoint-status.json"
checkpoint = read(checkpoint_path)
cp2 = next(item for item in checkpoint["checkpoints"] if item["id"] == "CP2")
cp7 = next(item for item in checkpoint["checkpoints"] if item["id"] == "CP7")
assert cp2["status"] == "in_progress" and cp7["status"] == "pending"
new_cp2 = ["source-evidence/agentops-local-archive-v1/" + name for name in ["decision.md", "ingestion.json", "manifest.json"]]
new_cp2 += ["source-evidence/agentops-local-archive-v1-verification.json",
            "source-evidence/agentops-git-object-api-v1/decision.md",
            "source-evidence/agentops-git-object-api-v1/manifest.json",
            "source-evidence/agentops-git-object-api-v1-verification.json",
            "../../runs/agentops-native-eligibility/v1/pre-execution.json",
            "../../runs/agentops-native-eligibility/v1/bootstrap.json",
            "../../runs/agentops-native-eligibility/v1/result.json",
            "../../scripts/setup_agentops_dependencies_v2.ps1"]
for relative in new_cp2:
    assert relative not in cp2["evidence"]
    receipt(ROOT / "docs/research" / relative)
cp2["evidence"].extend(new_cp2)
cp2["source_leads"]["agentops"] = "0.11.0 original user-supplied commit-labeled archive; 421 exact regular files/2 inert links; native dependency/test/card/wire/bridge and human validity open"
cp2["source_leads"]["agentops_acquisition"] = "Resolved by user ZIP; original Git/browser/API failures remain historical; no independent Git-object authentication or complete checkout"
cp2["source_leads"]["agentops_runtime_setup"] = "Bootstrap v1 failed with PIP_NO_INDEX=1; no install/test; checksum-pinned normal-terminal dependencies-v2 script prepared, result pending"
for relative in ["../../paper/draft-audit-v1.1.json", "../../paper/continuation-pre-edit-integrity-v6.json", "../../paper/continuation-integrity-v6.json"]:
    assert relative not in cp7["evidence"]
    receipt(ROOT / "docs/research" / relative)
    cp7["evidence"].append(relative)
checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8", newline="\n")
assert checkpoint["progress_percent"] == 5
assert checkpoint["novelty_demonstrated"] is checkpoint["human_review_completed"] is False
for item in stable:
    assert receipt(ROOT / item["path"]) == item
mapping = {item["original"]: item["snapshot"] for item in snapshots}
historical = []
for item in checks:
    path = mapping.get(item["path"], item["path"])
    actual = receipt(ROOT / path)
    assert actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"]
    historical.append({"original": item["path"], "checked_path": path,
                       "bytes": actual["bytes"], "sha256": actual["sha256"]})
for item in current:
    assert receipt(ROOT / item["path"]) == {key: value for key, value in item.items() if key != "report"}
links = []
for relative in updates:
    document = ROOT / relative
    for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#")):
            continue
        links.append(receipt(document.parent / target.split("#", 1)[0])["path"])
evidence = []
for cp in [cp2, cp7]:
    assert len(cp["evidence"]) == len(set(cp["evidence"]))
    for relative in cp["evidence"]:
        evidence.append(receipt(ROOT / "docs/research" / relative)["path"])
write_new(OUTPUT, {
    "schema_version": "continuation-retained-integrity/7", "checked_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "historical_entries_checked": len(historical),
    "current_file_entries_checked": len(current), "mutable_snapshots": snapshots,
    "stable_v0_v1_paper_files_unchanged": 12, "archive_member_payloads_checked": 423,
    "historical_checks": historical, "current_checks": current,
    "current_records": [receipt(ROOT / path) for path in RECORDS] + [receipt(path) for path in [
        PRE, PRIOR, Path(__file__).resolve(), ROOT / screen_paths[0], ROOT / screen_paths[1]]],
    "checkpoint_evidence_paths_checked": len(evidence), "document_links_checked": len(links),
    "new_cp2_evidence_paths": len(new_cp2), "new_application_requests": 0, "new_model_calls": 0,
    "new_tests": 0, "new_archive_replays": 0, "successful_dependency_installations": 0,
    "dependency_bootstrap_attempts": 1, "novelty_demonstrated": False, "human_review_completed": False,
    "checkpoint_progress_percent": 5, "goal_complete": False,
    "scope": "Versioned context, source/archive and retained failures; no source-to-runtime, native success, C1 advantage or human scientific claim.",
})
print(json.dumps({"status": "passed", "historical_entries_checked": len(historical),
                  "current_file_entries_checked": len(current), "stable_paper_files_unchanged": 12,
                  "checkpoint_evidence_paths_checked": len(evidence), "document_links_checked": len(links),
                  "progress_percent": 5, "upstream_native_test_executed": False}, indent=2))
