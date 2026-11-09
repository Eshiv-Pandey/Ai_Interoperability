"""Seal/check the local source-screen record; never downloads or executes services."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "docs/research/source-evidence/advertising-screen-v2"
ATTEMPT = ROOT / "docs/research/source-evidence/advertising-screen-v2-20261024T192359210164Z-9868"
MANIFEST = SCREEN / "manifest.json"
SOURCES = {
    "amirk-config.ts": "external/a2a-to-mcp/src/config.ts",
    "amirk-a2a-client.ts": "external/a2a-to-mcp/src/a2a-client.ts",
    "amirk-tools.ts": "external/a2a-to-mcp/src/tools.ts",
    "amirk-LICENSE": "external/a2a-to-mcp/LICENSE",
    "mgcrea-writes.ts": "external/mcp-a2a/src/tools/writes.ts",
    "mgcrea-fetch.ts": "external/mcp-a2a/src/client/fetch.ts",
    "mgcrea-LICENSE": "external/mcp-a2a/LICENSE",
}


def write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def entry(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def seal() -> None:
    if MANIFEST.exists() or (SCREEN / "local-sources").exists():
        raise SystemExit("Refusing to replace an existing seal or source snapshot.")
    queries = sorted(SCREEN.glob("*.query.json"))
    results = sorted(SCREEN.glob("*.result.json"))
    if len(queries) != 15 or len(results) != 15:
        raise SystemExit("Expected all fifteen retained query/result pairs.")
    if {p.name[:-11] for p in queries} != {p.name[:-12] for p in results}:
        raise SystemExit("Unpaired retrieval record.")
    (SCREEN / "local-sources").mkdir()
    for name, source in SOURCES.items():
        with (SCREEN / "local-sources" / name).open("xb") as stream:
            stream.write((ROOT / source).read_bytes())
    files = sorted(p for p in SCREEN.rglob("*") if p.is_file())
    files.extend(sorted(p for p in ATTEMPT.rglob("*") if p.is_file()))
    files.extend([Path(__file__).resolve(), ROOT / "scripts/screen_advertising_domains_v2.py"])
    write_new(MANIFEST, {
        "schema_version": "advertising-screen-local-manifest/2",
        "sealed_at_utc": datetime.now(UTC).isoformat(),
        "retrieval_pairs": len(queries),
        "web_records_are_original_source_bytes": False,
        "web_record_representation": "JSON serialization of retained tool query/result objects",
        "local_source_snapshots_are_original_bytes": True,
        "local_source_mapping": SOURCES,
        "direct_acquisition_attempt": ATTEMPT.relative_to(ROOT).as_posix(),
        "claims": {"source_screen_only": True, "runtime_executed": False,
                   "qualified_second_domain": False, "novelty_demonstrated": False,
                   "human_review_completed": False, "progress_percent": 5},
        "files": [entry(p) for p in files],
        "limit": "Local integrity only; no source authenticity, SDK conformance or runtime replay claim.",
    })


def verify() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["files"]
    paths = [item["path"] for item in expected]
    if len(paths) != len(set(paths)):
        raise SystemExit("Duplicate manifest paths.")
    for item in expected:
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(ROOT) or entry(path) != item:
            raise SystemExit("Record changed or outside workspace: " + item["path"])
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
    for name, source in SOURCES.items():
        if (SCREEN / "local-sources" / name).read_bytes() != (ROOT / source).read_bytes():
            raise SystemExit("Current local source differs from snapshot: " + source)
    return {"schema_version": "advertising-screen-integrity-check/2",
            "checked_at_utc": datetime.now(UTC).isoformat(), "status": "passed",
            "manifest": entry(MANIFEST), "files_checked": len(expected),
            "retrieval_pairs": manifest["retrieval_pairs"], "source_snapshots_checked": len(SOURCES),
            "application_execution": False, "check_scope": "local file hashes, JSON syntax and source byte equality"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.seal:
        seal()
    report = verify()
    if args.output:
        output_path = args.output.resolve()
        if not output_path.is_relative_to(ROOT):
            raise SystemExit("Output must be within this workspace.")
        write_new(output_path, report)
    print(json.dumps(report, indent=2))
