"""Capture exact local source bytes and seal the partial surface screen once.

Uses only the standard library. Literal inventory checks are not a TypeScript
parser, a source-to-runtime proof, a benchmark run, or scientific review.
"""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "docs/research/source-evidence/origin-surface-closure-v1"
INDEX = SCREEN / "source-index.json"
MANIFEST = SCREEN / "manifest.json"
OUTPUT = SCREEN.parent / "origin-surface-closure-v1-verification.json"


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
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


assert not any(path.exists() for path in [INDEX, MANIFEST, OUTPUT, SCREEN / "sources"]), \
    "Refusing to repeat or overwrite the source screen."
ledger = read(SCREEN / "coverage-ledger.json")
assert ledger["checkpoint_progress_percent"] == 5
for flag in ["source_to_runtime_closure_verified", "public_surface_coverage_complete",
             "can_certify_supported", "can_certify_unsupported", "novelty_demonstrated",
             "qualified_second_domain", "human_review_completed"]:
    assert ledger[flag] is False, flag
assert all(value == 0 for value in ledger["execution"].values())
assert len(ledger["direct_origin_claims"]) == len(ledger["open_obligations"]) == 5

plans = []
origins = {
    "amirk": ("external/a2a-to-mcp", [
        "LICENSE", "src/tools.ts", "src/a2a-client.ts", "src/mrtr.ts",
        "src/tasks/handlers.ts", "src/tasks/intercept.ts", "src/server.ts",
        "src/http.ts", "src/index.ts", "src/handles.ts", "src/config.ts",
    ]),
    "mgcrea": ("external/mcp-a2a", [
        "LICENSE", "src/tools/index.ts", "src/tools/auth.ts", "src/tools/agents.ts",
        "src/tools/tasks.ts", "src/tools/writes.ts", "src/tools/request.ts",
        "src/tools/util.ts", "src/client/peer.ts", "src/client/fetch.ts",
        "src/store/tasks.ts", "src/store/paths.ts", "src/store/peers.ts", "src/config.ts",
    ]),
    "fixture": ("scripts/fixtures", ["carol-reference-v1.mjs"]),
}
for origin, (directory, relatives) in origins.items():
    for relative in relatives:
        original = ROOT / directory / relative
        copied = SCREEN / "sources" / origin / relative
        plans.append((origin, original, copied, original.read_bytes()))

# Check actual current bytes before writing any source copies. These are scoped
# literal checks, not claims that the inventory closes all dynamic dispatch.
source_text = {original.relative_to(ROOT).as_posix(): data.decode("utf-8")
               for _, original, _, data in plans}
tools_text = "\n".join(source_text["external/mcp-a2a/src/tools/" + name + ".ts"]
                       for name in ["auth", "agents", "tasks", "writes", "request"])
registered = re.findall(r'server\.registerTool\(\s*"([^"]+)"', tools_text)
assert len(registered) == len(set(registered)) == 12
assert sorted(registered) == sorted(ledger["mgcrea_write_enabled_tools"])
request = source_text["external/mcp-a2a/src/tools/request.ts"]
methods = {}
for label in ["READ_METHODS", "WRITE_METHODS"]:
    block = re.search(r"const " + label + r" = \[(.*?)\] as const;", request, re.S)
    assert block is not None
    methods[label] = re.findall(r'"([^"]+)"', block.group(1))
assert len(methods["READ_METHODS"]) == 5 and len(methods["WRITE_METHODS"]) == 4
assert "ctx.peers.rawRpc(url, method, params)" in request
for tool in ledger["amirk_tools"]:
    assert '"' + tool + '"' in source_text["external/a2a-to-mcp/src/tools.ts"]
for method in ledger["amirk_task_methods"]:
    assert '"' + method + '"' in source_text["external/a2a-to-mcp/src/tasks/handlers.ts"]
assert "referenceTaskIds: []" in source_text["external/a2a-to-mcp/src/a2a-client.ts"]
assert "referenceTaskIds: []" in source_text["external/mcp-a2a/src/client/peer.ts"]
assert "this.#agents.sendMessage(alias, {" in source_text["external/a2a-to-mcp/src/mrtr.ts"]
assert "ctx.store.applyResponse(task_id" in source_text["external/mcp-a2a/src/tools/writes.ts"]
assert "direction: record.direction, peer: record.peer" in source_text["external/mcp-a2a/src/store/tasks.ts"]
assert "writeFileAtomic(path, JSON.stringify(record))" in source_text["external/mcp-a2a/src/store/tasks.ts"]
assert "Boolean(context.userMessage?.referenceTaskIds?.length)" in source_text["scripts/fixtures/carol-reference-v1.mjs"]
assert "startsWith('well done')" in source_text["scripts/fixtures/carol-reference-v1.mjs"]
assert "Apache License" in source_text["external/a2a-to-mcp/LICENSE"]
assert "MIT License" in source_text["external/mcp-a2a/LICENSE"]
metadata = read(SCREEN / "local-git-metadata-tool-response.json")
assert metadata["status"] == "fulfilled" and metadata["value"]["exit_code"] == 0
assert set(metadata["value"]["output"].splitlines()) == set(ledger["source_revisions"].values())
failed = (SCREEN / "failed-regex-read-tool-response.json").read_text(encoding="utf-8")
assert "regex parse error" in failed and "exit_code" in failed

entries = []
for origin, original, copied, data in plans:
    copied.parent.mkdir(parents=True, exist_ok=True)
    with copied.open("xb") as stream:
        stream.write(data)
    assert copied.read_bytes() == original.read_bytes() == data
    entries.append({"origin": origin, "original": receipt(original), "copy": receipt(copied),
                    "revision_reported_by_local_git": ledger["source_revisions"].get(origin),
                    "independent_git_object_verification": False})
write_new(INDEX, {
    "schema_version": "local-source-copy-index/1", "captured_at_utc": datetime.now(UTC).isoformat(),
    "entries": entries, "copies": len(entries), "byte_equality_checked": True,
    "license_copies": [item["copy"]["path"] for item in entries
                       if Path(item["original"]["path"]).name == "LICENSE"],
    "source_to_runtime_closure_verified": False,
    "scope": "Exact current local files, not remote retrieval, independently checked Git objects, complete dependency/runtime closure or application replay.",
})
evidence = []
for claim in ledger["direct_origin_claims"]:
    assert claim["id"] and claim["limit"]
    for relative in claim["evidence"]:
        evidence.append(receipt(SCREEN / relative)["path"])
links = []
for target in re.findall(r"\]\(([^)]+)\)", (SCREEN / "decision.md").read_text(encoding="utf-8")):
    if not target.startswith(("http://", "https://", "#")):
        links.append(receipt(SCREEN / target.split("#", 1)[0])["path"])
json_paths = list(SCREEN.glob("*.json"))
for path in json_paths:
    read(path)
files = {path for path in SCREEN.rglob("*") if path.is_file()}
files |= {Path(__file__).resolve()}
files |= {ROOT / path for path in ledger["retained_inputs"]}
write_new(MANIFEST, {
    "schema_version": "partial-origin-surface-manifest/1", "sealed_at_utc": datetime.now(UTC).isoformat(),
    "files": [receipt(path) for path in sorted(files)], "source_copies": len(entries),
    "record_representation": "Complete serialized tool responses plus exact local source copies",
    "tool_output_is_original_process_byte_capture": False,
    "scope": "Literal/source-path inventory with explicitly open environment/runtime obligations; no scientific gate pass.",
})
for item in read(MANIFEST)["files"]:
    assert receipt(ROOT / item["path"]) == item
report = {
    "schema_version": "partial-origin-surface-verification/1", "checked_at_utc": datetime.now(UTC).isoformat(),
    "status": "passed", "manifest": receipt(MANIFEST), "files_checked": len(files),
    "source_copy_pairs_checked": len(entries), "license_copies_checked": 2,
    "json_records_checked": len(json_paths), "claim_evidence_links_checked": len(evidence),
    "local_document_links_checked": len(links), "mgcrea_tool_names_checked": sorted(registered),
    "raw_rpc_method_literals_checked": methods, "inventory_check_is_formal_parser_proof": False,
    "malformed_regex_failure_retained": True, "truncated_read_outputs_retained": True,
    "coverage_complete": False, "source_to_runtime_closure_verified": False,
    "application_execution": False, "new_application_requests": 0, "new_model_calls": 0,
    "new_tests": 0, "new_archive_replays": 0, "new_installations": 0,
    "candidate_performance_trials": 0, "novelty_demonstrated": False,
    "human_review_completed": False, "checkpoint_progress_percent": 5,
    "scope": "Hash/index/evidence/literal checks; no complete-negative certificate, source-to-runtime proof, new native control or human/scientific review.",
}
write_new(OUTPUT, report)
print(json.dumps(report, indent=2))
