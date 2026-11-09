"""Verify v5 retention, snapshot context, then integrate the sealed screen once."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "docs/research/snapshots/continuation-v6"
PRE = ROOT / "paper/continuation-pre-edit-integrity-v6.json"
PRIOR = ROOT / "paper/continuation-integrity-v5.json"
RECORDS = [
    "RESEARCH_WORKFLOW.md", "docs/research/execution-handoff.md",
    "docs/research/implementation-novelty-gate.md", "docs/research/cp2-review-packet-v1.md",
    "docs/research/checkpoint-status.json", "paper/draft-status-v1.json",
]
STABLE = [
    "paper/working-draft-v0.md", "paper/claim-ledger-v0.json", "paper/draft-status-v0.json",
    "paper/references-v1.json", "paper/references-v1.bib", "paper/references-v1.md",
    "paper/working-draft-v1.md", "paper/claim-ledger-v1.json", "paper/draft-status-v1.json",
    "paper/references-v2.json", "paper/references-v2.bib", "paper/references-v2.md",
]
if PRE.exists() or SNAPSHOTS.exists():
    raise SystemExit("Refusing to repeat or replace the v6 update.")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def receipt(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), str(path)
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


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

base = "docs/research/source-evidence/origin-surface-closure-v1"
screen = read(ROOT / (base + "-verification.json"))
assert screen["status"] == "passed" and screen["files_checked"] == 39
assert screen["source_copy_pairs_checked"] == 26 and screen["application_execution"] is False
assert receipt(ROOT / screen["manifest"]["path"]) == screen["manifest"]
for item in read(ROOT / screen["manifest"]["path"])["files"]:
    assert receipt(ROOT / item["path"]) == item, item["path"]

additions = {
    "RESEARCH_WORKFLOW.md": (
        "## 1. Research direction and what changes",
        "\n\n**Direct-origin surface follow-up (25 October):** the\n"
        "[sealed source screen](docs/research/source-evidence/origin-surface-closure-v1/decision.md)\n"
        "extends the two-bridge inventory to ordinary form/MRTR continuations,\n"
        "all twelve write-enabled mgcrea tools and nine raw RPC method literals.\n"
        "Twenty-six exact local source copies, both licenses and retained\n"
        "read failures pass a 39-file check. Outbound local response annotates\n"
        "the mirror; the original-task goal still requires origin completion.\n"
        "Permitted URL/peer alternatives, callback/SDK paths, installed runtime\n"
        "fidelity, timing and independent closure review remain open. This\n"
        "partial source inventory issues no admission/refutation certificate\n"
        "and establishes no C1 novelty. No application or performance trial\n"
        "ran; CP2/CP7 remain open and verified credit remains 5%.",
    ),
    "docs/research/implementation-novelty-gate.md": (
        "## What the fresh source audit changes",
        "\n\nThe [direct-origin surface screen](source-evidence/origin-surface-closure-v1/decision.md)\n"
        "extends source coverage beyond the four historical actions to MRTR/form\n"
        "continuation and twelve mgcrea tools. Its 26 byte-preserving local copies\n"
        "and 39-file integrity check support scoped constructor/mirror facts,\n"
        "without closing dynamic peer/URL, callback/SDK, runtime or time paths.\n"
        "Ordinary source invariant reasoning remains the baseline. Unknown\n"
        "is required beyond the inspected families; no C1 step, certificate,\n"
        "performance result, second domain or human gate credit is added.",
    ),
    "docs/research/cp2-review-packet-v1.md": (
        "## Claims currently rejected",
        "\n\n**Direct-origin coverage addendum (25 October):** the\n"
        "[source inventory](source-evidence/origin-surface-closure-v1/decision.md)\n"
        "covers the ordinary form/MRTR accepted-answer constructor and all twelve\n"
        "write-enabled mgcrea tool registrations. Local outbound response changes\n"
        "a mirror, which cannot by itself establish authoritative original-task\n"
        "completion. Twenty-six exact source copies and both licenses pass the\n"
        "[39-file integrity check](source-evidence/origin-surface-closure-v1-verification.json).\n"
        "The ledger keeps peer/URL, callback/SDK, installed-runtime, timing and\n"
        "independent closure obligations open. Four failed wire traces plus\n"
        "this inventory do not prove all legal continuations fail. No new\n"
        "runtime experiment, novel procedure, advantage or human review occurred.",
    ),
    "docs/research/execution-handoff.md": (
        "**Latest continuation update (25 October 2026):**",
        "\n\n- [Direct-origin surface closure v1](source-evidence/origin-surface-closure-v1/decision.md)\n"
        "  is now complete as a partial evidence package. It captures 26 exact\n"
        "  local files, both licenses and the peer-URL argument definition. The\n"
        "  source index, five scoped claims/five open obligations and 39-file\n"
        "  [integrity check](source-evidence/origin-surface-closure-v1-verification.json)\n"
        "  pass. MRTR/form and Tasks send paths share the empty-reference builder;\n"
        "  mgcrea registers twelve tools/nine raw methods. Outbound local response\n"
        "  annotates the mirror, while the benchmark requires origin completion.\n"
        "  Dynamic peer/URL alternatives, callback/SDK/serialization, installed\n"
        "  runtime, time/concurrency and independent source/task review remain\n"
        "  open. No full-interface refutation, novel step or certificate follows.\n"
        "  The malformed regex failure and truncated corrected reads are retained\n"
        "  as complete serialized tool results, not binary process-stream capture.\n"
        "  No application requests, installations, tests, archive replays, model\n"
        "  calls or performance trials ran. Both v0/v1 manuscript, claim, status\n"
        "  and reference sets remain unchanged. Six current records are snapshotted\n"
        "  under continuation-v6 before integration; five context records change.\n"
        "  CP7 now also links the existing v1 draft/v5 integrity audits. Continue\n"
        "  actual C1 distinction and accessible pinned second-domain eligibility;\n"
        "  source inventory adds no gate credit. CP2 open, CP7 pending, credit 5%.",
    ),
}
prepared = {}
for relative, (anchor, addition) in additions.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert text.count(anchor) == 1, relative
    prepared[relative] = text.replace(anchor, anchor + addition, 1)
checkpoint = read(ROOT / "docs/research/checkpoint-status.json")
cp2 = next(item for item in checkpoint["checkpoints"] if item["id"] == "CP2")
cp7 = next(item for item in checkpoint["checkpoints"] if item["id"] == "CP7")
assert cp2["status"] == "in_progress" and cp7["status"] == "pending"
assert checkpoint["progress_percent"] == 5
assert checkpoint["novelty_demonstrated"] is checkpoint["human_review_completed"] is False
new_evidence = ["source-evidence/origin-surface-closure-v1/" + name for name in [
    "decision.md", "coverage-ledger.json", "source-index.json", "manifest.json",
]] + ["source-evidence/origin-surface-closure-v1-verification.json"]
for relative in new_evidence:
    assert relative not in cp2["evidence"]
    receipt(ROOT / "docs/research" / relative)
cp2["evidence"].extend(new_evidence)
cp2["source_leads"]["direct_origin_surface"] = (
    "26 exact local sources; MRTR/form plus 12 tools/9 raw methods inspected; "
    "peer/URL, callback/SDK, installed-runtime, time and independent closure open; no certificate or C1 step"
)
for relative in ["../../paper/draft-audit-v1.json", "../../paper/continuation-pre-edit-integrity-v5.json",
                 "../../paper/continuation-integrity-v5.json"]:
    assert relative not in cp7["evidence"]
    receipt(ROOT / "docs/research" / relative)
    cp7["evidence"].append(relative)
prepared["docs/research/checkpoint-status.json"] = json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n"
assert set(prepared) == set(RECORDS) - {"paper/draft-status-v1.json"}
stable = [receipt(ROOT / relative) for relative in STABLE]
snapshots = []
for relative in RECORDS:
    snapshot = SNAPSHOTS / relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open("xb") as stream:
        stream.write((ROOT / relative).read_bytes())
    actual = receipt(snapshot)
    assert snapshot.read_bytes() == (ROOT / relative).read_bytes()
    snapshots.append({"original": relative, "snapshot": actual["path"],
                      "bytes": actual["bytes"], "sha256": actual["sha256"]})
report = {
    "schema_version": "continuation-pre-edit-integrity/6", "checked_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "prior_integrity_report": receipt(PRIOR),
    "prior_input_entries_checked": len(prior["historical_checks"]) + len(prior["current_checks"]),
    "prior_current_records_checked": len(prior["current_records"]),
    "verified_inputs": checks, "mutable_record_snapshots": snapshots,
    "stable_paper_files": stable, "new_screen_manifest": screen["manifest"],
    "changed_files_before_edit": [], "context_files_to_update": list(prepared),
    "scope": "Exact retention and pre-edit copies; no software tests, application or inference.",
}
with PRE.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
for relative, content in prepared.items():
    (ROOT / relative).write_text(content, encoding="utf-8", newline="\n")
for item in stable:
    assert receipt(ROOT / item["path"]) == item
print(json.dumps({
    "status": "updated", "prior_entries_checked": len(checks), "snapshots": len(snapshots),
    "context_files_updated": len(prepared), "stable_paper_files_unchanged": len(stable),
    "new_cp2_evidence_paths": len(new_evidence), "new_cp7_existing_audit_paths": 3,
    "progress_percent": 5, "application_requests": 0, "model_calls": 0,
}, indent=2))
