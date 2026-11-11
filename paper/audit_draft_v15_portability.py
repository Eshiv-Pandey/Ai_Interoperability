"""Read-only Git-index/archive-parts portability census for V15; stdlib only.

Never stages Git files, restores archives, writes historical evidence, imports
application/SDK/evaluator sources, or contacts a provider. Writes one fresh audit.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUFFER = 1024 * 1024


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit():
    need(subprocess.check_output(["git", "rev-parse", "--show-object-format"], cwd=ROOT).strip() == b"sha1",
         "this_index_comparison_requires_SHA1_git_objects")
    index_rows = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT).split(b"\0")
    indexed = {}
    for row in index_rows:
        if not row:
            continue
        header, path = row.split(b"\t", 1)
        mode, object_sha, stage = header.split()
        need(stage == b"0", "unmerged_Git_index")
        indexed[path.decode("utf-8")] = object_sha.decode("ascii")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    files = {}

    def file(path):
        if path not in files:
            target = ROOT / path
            need(target.is_file() and not target.is_symlink(), "regular_local_file_required:" + path)
            size = target.stat().st_size
            digest = hashlib.sha256()
            blob = hashlib.sha1(b"blob " + str(size).encode() + b"\0")
            with target.open("rb") as stream:
                for chunk in iter(lambda: stream.read(BUFFER), b""):
                    digest.update(chunk)
                    blob.update(chunk)
            files[path] = {"path": path, "bytes": size, "sha256": digest.hexdigest(),
                           "git_blob_sha1": blob.hexdigest(), "indexed_exact": indexed.get(path) == blob.hexdigest()}
        return files[path]

    archive_cache = {}
    open_archives = {}
    prerequisites = set()
    candidates_rejected = []

    def archive(base):
        if base in archive_cache:
            return archive_cache[base]
        path = base + "/artifact.zip"
        actual = file(path)
        source = None
        if actual["indexed_exact"]:
            source = {"kind": "exact_indexed_archive", "archive": path, "source_paths": [path]}
        else:
            candidates = sorted((ROOT / base).glob("archive-parts*/index.json"), reverse=True)
            for candidate in candidates:
                index_path = candidate.relative_to(ROOT).as_posix()
                value = read(index_path)
                if value.get("identity") != {key: actual[key] for key in ("bytes", "sha256")}:
                    candidates_rejected.append({"index": index_path, "reason": "different_archive_identity"})
                    continue
                sources = [index_path] + [(candidate.parent / part["name"]).relative_to(ROOT).as_posix()
                                          for part in value["parts"]]
                missing = [item for item in sources if not file(item)["indexed_exact"]]
                if missing:
                    prerequisites.update(missing)
                    candidates_rejected.append({"index": index_path, "reason": "source_bytes_not_indexed", "paths": missing})
                    continue
                whole, whole_bytes = hashlib.sha256(), 0
                for part, part_path in zip(value["parts"], sources[1:], strict=True):
                    current = file(part_path)
                    need(all(current[key] == part[key] for key in ("bytes", "sha256")), "part_index_payload_changed")
                    with (ROOT / part_path).open("rb") as stream:
                        for chunk in iter(lambda: stream.read(BUFFER), b""):
                            whole.update(chunk)
                            whole_bytes += len(chunk)
                need(whole.hexdigest() == actual["sha256"] and whole_bytes == actual["bytes"],
                     "indexed_archive_parts_not_exact_whole_bytes")
                source = {"kind": "exact_indexed_archive_parts", "archive": path,
                          "index": index_path, "source_paths": sources, "whole_bytes": whole_bytes,
                          "whole_sha256": whole.hexdigest()}
                break
        if source is None:
            prerequisites.add(path)
            source = {"kind": "archive_requires_staging", "archive": path, "source_paths": [path]}
        inventory_path = base + "/extracted-manifest.json"
        inventory = read(inventory_path)
        if not file(inventory_path)["indexed_exact"]:
            prerequisites.add(inventory_path)
        source["inventory"] = inventory_path
        source["inventory_indexed_exact"] = file(inventory_path)["indexed_exact"]
        source["required_restore_metadata"] = []
        for name in ("retention.json", "github-run.json", "github-artifacts.json", "plan.json"):
            metadata_path = base + "/" + name
            if not file(metadata_path)["indexed_exact"]:
                prerequisites.add(metadata_path)
            source["required_restore_metadata"].append(metadata_path)
        source["members"] = {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in inventory["files"]}
        archive_cache[base] = source
        return source

    provenance = read("paper/working-draft-v15.provenance.json")
    records, inputs = [], provenance["inputs"]
    for expected in inputs:
        path = expected["path"]
        current = file(path)
        need(all(current[key] == expected[key] for key in ("bytes", "sha256")), "sealed_V15_input_changed:" + path)
        row = {**expected, "status": ""}
        if current["indexed_exact"]:
            row["status"] = "directly_indexed_exact_bytes"
        elif "/extracted/" in path:
            base, member = path.split("/extracted/", 1)
            source = archive(base)
            need(source["members"].get(member) == {key: expected[key] for key in ("bytes", "sha256")},
                 "needed_member_identity_not_in_retained_inventory:" + path)
            if source["archive"] not in open_archives:
                open_archives[source["archive"]] = zipfile.ZipFile(ROOT / source["archive"])
            raw = open_archives[source["archive"]].read(member)
            need(len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"],
                 "needed_input_not_exact_archive_member:" + path)
            row["status"] = "recoverable_exact_archive_member" if source["kind"] != "archive_requires_staging" else "recovery_source_requires_staging"
            row["recovery"] = {key: source[key] for key in ("archive", "inventory", "kind")}
            row["recovery"]["member"] = member
            if "index" in source:
                row["recovery"]["index"] = source["index"]
        elif path.endswith("/artifact.zip"):
            source = archive(path.removesuffix("/artifact.zip"))
            row["status"] = "recoverable_exact_archive_from_parts" if source["kind"] != "archive_requires_staging" else "recovery_source_requires_staging"
            row["recovery"] = {key: source[key] for key in ("archive", "kind")}
            if "index" in source:
                row["recovery"]["index"] = source["index"]
        else:
            row["status"] = "exact_file_requires_staging"
            prerequisites.add(path)
        records.append(row)
    for zipped in open_archives.values():
        zipped.close()
    counts = dict(Counter(row["status"] for row in records))
    package_paths = ["paper/build_draft_v15.py", "paper/audit_draft_v15.py", "paper/working-draft-v15.md",
                     "paper/working-draft-v15.provenance.json", "paper/claim-ledger-v15.json",
                     "paper/working-draft-v15.audit.json", "docs/research/paper-artifact-guide-v15.md"]
    package = [file(path) for path in package_paths]
    archive_summaries = [{key: value for key, value in row.items() if key != "members"}
                         for _, row in sorted(archive_cache.items())]
    for item in archive_summaries:
        item["restore_base"] = str(Path(item["archive"]).parent).replace("\\", "/")
        item["standard_restorer"] = "scripts/restore_retained_evidence_v1.py"
        item["restore_missing_flag"] = True
    return {"schema_version": "paper-v15-Git-index-and-archive-parts-portability/1",
            "audited_utc": datetime.now(timezone.utc).isoformat(), "git_HEAD_snapshot": head,
            "git_index_snapshot_is_remote_publication": False,
            "status": "packaging_closure_required" if prerequisites or not all(row["indexed_exact"] for row in package) else "all_inputs_indexed_or_exactly_recoverable",
            "sealed_provenance_identity": file("paper/working-draft-v15.provenance.json"),
            "input_count": len(records), "input_status_counts": counts, "inputs": records,
            "exact_untracked_prerequisite_paths_to_stage": sorted(prerequisites),
            "unindexed_V15_package_paths_to_stage": [row["path"] for row in package if not row["indexed_exact"]],
            "V15_package": package, "archive_recovery_sources": archive_summaries,
            "rejected_archive_index_candidates": candidates_rejected,
            "guide_gap": "Sealed V15/V14 guidance does not give every required base/index pair. Use the new restoration supplement; restore both V8 source archives before the inherited wrapper.",
            "restoration_supplement": "docs/research/paper-v15-offline-restoration-guide-v1.md",
            "new_git_stage_restore_application_SDK_provider_solver_checker_or_evaluator_executions": 0,
            "audit_is_fresh_clone_execution": False,
            "limitations": ["Read-only current Git-index and exact archive-member/part census; root must validate an isolated fresh checkout after staging/committing closure.",
                            "Already indexed paths are compared with current Git blob identities; source parts are joined and checked against whole-archive hashes.",
                            "No sealed V15 output or historical evidence is rewritten."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to(ROOT / "paper") and not output.exists(), "fresh_paper_portability_audit_required")
    value = audit()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: value[key] for key in ("status", "input_count", "input_status_counts", "exact_untracked_prerequisite_paths_to_stage", "unindexed_V15_package_paths_to_stage")}, indent=2))


if __name__ == "__main__":
    main()
