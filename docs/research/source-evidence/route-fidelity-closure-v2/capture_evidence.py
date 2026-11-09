"""Seal selected exact sources and compare them with the retained B4 archive.

Standard library only. No application import, request, installation or replay.
This checks byte provenance, not the correctness of the accompanying source proof.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GROUP = "runs/official-handler-bridge-control/group-status-v2.json"
SOURCES = [
    "external/mcp-a2a/LICENSE",
    "external/mcp-a2a/src/a2a.ts",
    "external/mcp-a2a/src/tools/writes.ts",
    "external/mcp-a2a/src/tools/request.ts",
    "external/mcp-a2a/src/client/peer.ts",
    "external/mcp-a2a/src/client/fetch.ts",
    "external/mcp-a2a/dist/server-Dd272e4l.js",
    "external/mcp-a2a/dist/server-Dd272e4l.js.map",
    "external/mcp-a2a/node_modules/@a2a-js/sdk/LICENSE",
    "external/mcp-a2a/node_modules/@a2a-js/sdk/package.json",
    "external/mcp-a2a/node_modules/@a2a-js/sdk/dist/client/index.js",
    "external/sdk-http-control-v1/node_modules/@a2a-js/sdk/LICENSE",
    "external/sdk-http-control-v1/node_modules/@a2a-js/sdk/package.json",
    "external/sdk-http-control-v1/node_modules/@a2a-js/sdk/dist/server/index.js",
    "external/sdk-http-control-v1/node_modules/@a2a-js/sdk/dist/server/express/index.js",
    "scripts/capture-official-handler-bridge-v2.mjs",
    "scripts/fixtures/carol-reference-v1.mjs",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": digest(data)}


def save(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")


def main() -> None:
    for name in ("source-index.json", "verification.json", "manifest.json"):
        if (HERE / name).exists():
            raise SystemExit("Refusing to replace existing evidence: " + name)
    group = json.loads((ROOT / GROUP).read_text(encoding="utf-8"))
    case = next(case for case in group["cases"] if case["variant"] == "B4")
    report_path = ROOT / case["report"]["path"]
    assert record(report_path) == case["report"], "Historical B4 report changed"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    matches = {}
    for path, value in report["pre_execution"]["source_hashes"].items():
        matches[path] = value
    for tree in report["official_pre_execution"]["trees"]:
        for entry in tree["entries"]:
            matches[tree["source"] + "/" + entry["path"]] = {
                **entry, "snapshot": tree["snapshot"] + "/" + entry["path"]}
    for key in ("bridge_source_manifest", "bridge_dist_manifest"):
        tree = report["pre_execution"][key]
        for entry in tree["entries"]:
            matches[tree["root"] + "/" + entry["path"]] = entry
    entries = []
    for relative in SOURCES:
        source = ROOT / relative
        data = source.read_bytes()
        item = {"original": record(source), "historical_receipt_match": False}
        prior = matches.get(relative)
        if prior:
            assert len(data) == prior["bytes"] and digest(data) == prior["sha256"], relative
            item["historical_receipt_match"] = True
            item["historical_report"] = case["report"]["path"]
            if prior.get("snapshot"):
                archived = ROOT / prior["snapshot"]
                assert archived.read_bytes() == data, "Archive differs: " + relative
                item["historical_snapshot"] = record(archived)
        target = HERE / "sources" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        assert target.read_bytes() == data
        item["copy"] = record(target)
        entries.append(item)
    source_map = json.loads((ROOT / "external/mcp-a2a/dist/server-Dd272e4l.js.map").read_text(encoding="utf-8"))
    map_matches = []
    for relative in SOURCES:
        if not relative.startswith("external/mcp-a2a/src/") or relative.endswith("/a2a.ts"):
            continue
        suffix = relative.removeprefix("external/mcp-a2a/")
        indices = [i for i, path in enumerate(source_map["sources"]) if path.endswith(suffix)]
        assert len(indices) == 1, relative
        exact = source_map["sourcesContent"][indices[0]].encode("utf-8") == (ROOT / relative).read_bytes()
        assert exact, "Source-map content differs: " + relative
        map_matches.append({"path": relative, "exact_embedded_source_match": exact})
    card = report["card"]
    assert card["capabilities"]["pushNotifications"] is False
    assert len(card["supportedInterfaces"]) == 1
    assert card["supportedInterfaces"][0]["protocolVersion"] == "1.0"
    save(HERE / "source-index.json", {"schema_version": "route-push-source-index/1",
         "captured_at_utc": datetime.now(timezone.utc).isoformat(), "entries": entries})
    save(HERE / "verification.json", {"schema_version": "route-push-byte-check/1", "valid": True,
         "historical_group": record(ROOT / GROUP), "historical_report": record(report_path),
         "selected_source_files": len(entries),
         "historical_receipt_matches": sum(item["historical_receipt_match"] for item in entries),
         "historical_exact_snapshot_matches": sum("historical_snapshot" in item for item in entries),
         "source_map_matches": map_matches, "frozen_card_push_notifications": False,
         "application_requests": 0, "software_tests": 0, "archive_replays": 0,
         "model_calls": 0, "installations": 0, "new_runtime_claim_verified": False,
         "formal_source_semantics_proof_checked": False, "full_runtime_closure": False})
    files = [record(path) for path in sorted(HERE.rglob("*")) if path.is_file()]
    save(HERE / "manifest.json", {"schema_version": "route-push-package/1", "files": files,
         "meaning": "Byte integrity of this source-analysis package; no application or scientific gate credit"})
    print(json.dumps({"valid": True, "selected_files": len(entries), "sealed_files": len(files),
                      "source_map_exact_matches": len(map_matches), "application_requests": 0}))


if __name__ == "__main__":
    main()
