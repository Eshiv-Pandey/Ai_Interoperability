"""Restore only the exact frozen V15 paper inputs, then run its read auditor.

Stdlib only. No full extraction/runtime qualification, application, SDK, model,
provider, solver, evaluator or certificate checker execution. Historical V1
helpers, failures and existing exact files are preserved. All needed source
bytes and archive structure are checked before publishing any evidence target.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import subprocess
import sys
import tempfile
import threading
import uuid

import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUFFER = 262144
MAX_METADATA = 32 * 1024 * 1024
MAX_ARCHIVE = 300000000
MAX_ARCHIVES_TOTAL = 2 * 1024 * 1024 * 1024
MAX_EXPANDED_PER_ARCHIVE = 2000000000
MAX_NEEDED_MEMBER_BYTES = 128 * 1024 * 1024
MAX_MEMBERS = 200000
PART_BYTES = 33554432
MAX_LOG_BYTES = 1024 * 1024
INPUT_COUNT = 3468
PROVENANCE = "paper/working-draft-v15.provenance.json"
CENSUS = "paper/working-draft-v15.portability-audit.json"
PINNED = {
    PROVENANCE: "23ba0330b4b0ecc8093a6fd3519c219db712322e3f773abd6ec7961befb95a63",
    CENSUS: "e8bb9761eeca7a4b53f89f73632d799e053dfe5152be8fe560adb6764575cb7e",
    "paper/working-draft-v15.md": "967eccdc549a683053b814044ce7c4ed3b4de63e572eb72679082a602837f4b6",
    "paper/claim-ledger-v15.json": "e5b07d8241349b1ab12d77d11cf33a712e7f6d0f263cd5f76ef4428d5ac703d9",
    "paper/audit_draft_v15.py": "c9dc9ac354acc19e0efb85de7718ce137a7abc286bf8b418a44c6023e592029a",
}
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def parse(raw):
    def unique(pairs):
        value = {}
        for key, child in pairs:
            need(key not in value, "duplicate_JSON_key")
            value[key] = child
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_JSON")))


def byte_identity(row):
    need(type(row) is dict and type(row.get("bytes")) is int and row["bytes"] >= 0
         and type(row.get("sha256")) is str and re.fullmatch("[0-9a-f]{64}", row["sha256"]),
         "valid_byte_identity_required")
    return {key: row[key] for key in ("bytes", "sha256")}


def linked(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def clean(path, root):
    path = Path(os.path.abspath(path))
    need(path.is_relative_to(root), "target_outside_workspace")
    for ancestor in (path, *path.parents):
        need(not linked(ancestor), "linked_path_or_junction_refused")
    need(path.resolve() == path, "path_alias_refused")
    return path


def portable_name(name, directory=False):
    need(type(name) is str and name and "\\" not in name and ":" not in name
         and not any(ord(char) < 32 or char in '<>"|?*' for char in name), "nonportable_relative_name")
    canonical = name[:-1] if directory and name.endswith("/") else name
    path = PurePosixPath(canonical)
    need(canonical and not path.is_absolute() and not PureWindowsPath(canonical).drive
         and ".." not in path.parts and path.as_posix() == canonical, "unsafe_relative_name")
    for part in path.parts:
        need(not part.endswith((".", " ")) and part.split(".", 1)[0].upper() not in RESERVED,
             "Windows_alias_or_reserved_name")
    return canonical


def target_for(root, name):
    return clean(root / portable_name(name), root)


def verify_existing_spelling(path, root, cache=None):
    """Reject filesystem case aliases for every existing target prefix."""
    cache = {} if cache is None else cache
    current = root
    for part in path.relative_to(root).parts:
        if not current.exists():
            break
        need(current.is_dir(), "existing_target_prefix_is_not_directory")
        if current not in cache:
            spellings = {}
            for entry in current.iterdir():
                spellings.setdefault(entry.name.casefold(), []).append(entry.name)
            cache[current] = spellings
        names = cache[current].get(part.casefold(), [])
        need(not names or names == [part], "existing_target_case_alias")
        current = current / part


def stream_identity(source, limit, target=None):
    size, digest = 0, hashlib.sha256()
    for block in iter(lambda: source.read(BUFFER), b""):
        size += len(block)
        need(size <= limit, "stream_byte_bound_exceeded")
        digest.update(block)
        if target is not None:
            target.write(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def identify(path, root, limit=MAX_ARCHIVES_TOTAL):
    path = clean(path, root)
    need(path.is_file() and path.stat().st_size <= limit, "bounded_regular_input_required")
    with path.open("rb") as stream:
        value = stream_identity(stream, limit)
    return {"path": path.relative_to(root).as_posix(), **value}


def load(root, name, source_records):
    path = target_for(root, name)
    row = identify(path, root, MAX_METADATA)
    source_records[name] = row
    return parse(path.read_bytes())


def safe_prefixes(files, directories=()):
    folded_files = {name.casefold() for name in files}
    spellings = {}
    for name in set(files) | set(directories):
        prefixes = [parent.as_posix() for parent in PurePosixPath(name).parents if parent.as_posix() != "."]
        if name in directories:
            prefixes.append(name)
        for prefix in prefixes:
            need(prefix.casefold() not in folded_files, "file_directory_prefix_conflict")
            earlier = spellings.setdefault(prefix.casefold(), prefix)
            need(earlier == prefix, "directory_prefix_case_alias")


def validate_zip(zipped, inventory):
    """Check all central names/types/sizes; do not decompress unneeded members."""
    infos = zipped.infolist()
    need(0 < len(infos) <= MAX_MEMBERS, "ZIP_member_count_bound")
    files, directories, seen, expanded = {}, set(), set(), 0
    for info in infos:
        name = portable_name(info.filename, info.is_dir())
        mode = stat.S_IFMT(info.external_attr >> 16)
        need(name.casefold() not in seen and mode in {0, stat.S_IFREG, stat.S_IFDIR}
             and not info.flag_bits & 1 and info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED},
             "duplicate_linked_encrypted_or_special_ZIP_member")
        need(mode != stat.S_IFDIR or info.is_dir(), "ZIP_directory_type_without_directory_name")
        need(mode != stat.S_IFREG or not info.is_dir(), "ZIP_regular_type_with_directory_name")
        seen.add(name.casefold())
        expanded += info.file_size
        need(0 <= info.file_size <= MAX_EXPANDED_PER_ARCHIVE and expanded <= MAX_EXPANDED_PER_ARCHIVE,
             "ZIP_advertised_expansion_bound")
        if info.is_dir():
            need(info.file_size == 0, "nonempty_ZIP_directory")
            directories.add(name)
        else:
            need(name in inventory and info.file_size == inventory[name]["bytes"],
                 "ZIP_member_size_or_inventory_membership_changed")
            files[name] = info
    need(set(files) == set(inventory), "complete_ZIP_inventory_membership_changed")
    safe_prefixes(files, directories)
    return files, expanded, len(infos)


def metadata(root, base, source_records):
    receipt, run, plan, api = [load(root, base + "/" + name, source_records)
                              for name in ("retention.json", "github-run.json", "plan.json", "github-artifacts.json")]
    whole = byte_identity({"bytes": receipt["archive_bytes"], "sha256": receipt["archive_sha256"]})
    need(0 < whole["bytes"] <= MAX_ARCHIVE and receipt["status"] == "retained"
         and receipt["api_digest"] == "sha256:" + whole["sha256"] and receipt["digest_matches_api"] is True,
         "retained_archive_API_digest_binding_changed")
    need(run["status"] == "completed" and type(run["id"]) is int and run["id"] > 0
         and type(run["run_attempt"]) is int and run["run_attempt"] > 0
         and re.fullmatch("[0-9a-f]{40}", run["head_sha"])
         and receipt["run_id"] == run["id"] == plan["run_id"]
         and receipt["head_sha"] == run["head_sha"]
         and receipt["workflow_conclusion"] == run["conclusion"] and plan["application_rerun"] is False,
         "completed_run_plan_and_retention_binding_changed")
    repository = plan["repository"]
    need(re.fullmatch("[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
         and run["html_url"] == f"https://github.com/{repository}/actions/runs/{run['id']}", "repository_run_binding_changed")
    artifacts = [row for row in api["artifacts"] if row["id"] == receipt["artifact_id"]]
    need(len(artifacts) == 1, "unique_saved_API_artifact_required")
    artifact = artifacts[0]
    need(artifact["digest"] == receipt["api_digest"] and artifact["size_in_bytes"] == whole["bytes"]
         and artifact["name"] == receipt["artifact_name"] and artifact["expired"] is False
         and artifact["workflow_run"]["id"] == run["id"]
         and artifact["workflow_run"]["head_sha"] == run["head_sha"], "saved_API_artifact_binding_changed")
    raw = load(root, base + "/extracted-manifest.json", source_records)["files"]
    need(type(raw) is list and len(raw) == receipt["extracted_files"] and 0 < len(raw) <= MAX_MEMBERS,
         "bounded_complete_inventory_required")
    inventory, folded, total = {}, set(), 0
    for row in raw:
        name, value = portable_name(row["path"]), byte_identity(row)
        need(name.casefold() not in folded, "duplicate_inventory_member")
        folded.add(name.casefold())
        inventory[name] = value
        total += value["bytes"]
        need(total <= MAX_EXPANDED_PER_ARCHIVE, "inventory_advertised_expansion_bound")
    safe_prefixes(inventory)
    return receipt, whole, inventory


def index_for(root, base, preferred, whole, source_records):
    if preferred:
        candidates = [preferred]
    else:
        candidates = [base + "/" + directory + "/index.json"
                      for directory in ("archive-parts-v3", "archive-parts-v2", "archive-parts-v1")
                      if target_for(root, base + "/" + directory + "/index.json").exists()]
    for name in candidates:
        index = load(root, name, source_records)
        if byte_identity(index["identity"]) == whole:
            return name, index
    return None, None


def verify_parts(root, base, name, index, receipt, whole, source_records, target=None):
    path = target_for(root, name)
    version = index["schema_version"]
    need(path.parent.parent == target_for(root, base) and path.name == "index.json"
         and version in {"public-retained-archive-parts/1", "public-retained-archive-parts/3"}
         and path.parent.name in ({"archive-parts-v1", "archive-parts-v2"} if version.endswith("/1") else {"archive-parts-v3"})
         and index["archive"] == "artifact.zip" and index["part_byte_limit"] == PART_BYTES
         and index["run_id"] == receipt["run_id"] and index["api_digest"] == receipt["api_digest"]
         and byte_identity(index["identity"]) == whole and index["original_archive_modified"] is False,
         "part_index_retention_version_or_path_binding_changed")
    if version.endswith("/3"):
        need(index["archive_max_bytes"] == MAX_ARCHIVE and index["copy_buffer_bytes"] == BUFFER,
             "part_index_streaming_bounds_changed")
    rows = index["parts"]
    need(type(rows) is list and 0 < len(rows) <= (MAX_ARCHIVE + PART_BYTES - 1) // PART_BYTES,
         "bounded_part_sequence_required")
    combined, total = hashlib.sha256(), 0
    for number, row in enumerate(rows):
        expected = byte_identity(row)
        need(row["name"] == f"part-{number:04d}.bin" and 0 < expected["bytes"] <= PART_BYTES
             and (number == len(rows) - 1 or expected["bytes"] == PART_BYTES), "part_sequence_or_size_changed")
        part_name = path.parent.relative_to(root).as_posix() + "/" + row["name"]
        part = target_for(root, part_name)
        need(part.is_file() and part.stat().st_size == expected["bytes"], "part_file_size_changed")
        individual, count = hashlib.sha256(), 0
        with part.open("rb") as stream:
            for block in iter(lambda: stream.read(BUFFER), b""):
                count += len(block)
                total += len(block)
                need(count <= PART_BYTES and total <= MAX_ARCHIVE, "part_stream_bound")
                individual.update(block)
                combined.update(block)
                if target is not None:
                    target.write(block)
        actual = {"bytes": count, "sha256": individual.hexdigest()}
        need(actual == expected, "part_hash_changed")
        source_records[part_name] = {"path": part_name, **actual}
    need({"bytes": total, "sha256": combined.hexdigest()} == whole, "whole_joined_archive_changed")
    if target is not None:
        target.flush()
        target.seek(0)
    return len(rows)


def make_directories(path, root):
    path = clean(path, root)
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = clean(current / part, root)
        # Reject a differently spelled existing case-insensitive alias.
        aliases = [entry.name for entry in current.parent.iterdir() if entry.name.casefold() == part.casefold()]
        need(not aliases or aliases == [part], "existing_directory_case_alias")
        if current.exists():
            need(current.is_dir(), "existing_parent_is_not_directory")
        else:
            current.mkdir()


def publish(source, target, expected, root):
    target = clean(target, root)
    need(not target.exists(), "publication_target_became_present")
    make_directories(target.parent, root)
    target = clean(target, root)
    verify_existing_spelling(target, root)
    with target.open("xb") as output:
        need(stream_identity(source, expected["bytes"], output) == expected, "exclusive_restoration_payload_changed")
        output.flush()
        os.fsync(output.fileno())
    need(byte_identity(identify(target, root, expected["bytes"])) == expected, "published_file_identity_changed")


def run_bounded(argv, output, timeout, root):
    paths = [output / "paper-read-audit.stdout.bin", output / "paper-read-audit.stderr.bin"]
    counters = [{"observed_bytes": 0, "retained_bytes": 0, "discarded_bytes": 0} for _ in paths]
    errors = []
    process = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def consume(pipe, path, counter):
        try:
            with path.open("xb") as stream:
                for block in iter(lambda: pipe.read(65536), b""):
                    counter["observed_bytes"] += len(block)
                    retain = block[:max(0, MAX_LOG_BYTES - counter["retained_bytes"])]
                    stream.write(retain)
                    counter["retained_bytes"] += len(retain)
                    counter["discarded_bytes"] += len(block) - len(retain)
        except Exception as error:
            errors.append(type(error).__name__)
        finally:
            pipe.close()
    threads = [threading.Thread(target=consume, args=(pipe, path, counter), daemon=True)
               for pipe, path, counter in zip((process.stdout, process.stderr), paths, counters, strict=True)]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        code = process.wait(timeout=10)
    for thread in threads:
        thread.join(timeout=10)
    need(not errors and not any(thread.is_alive() for thread in threads), "bounded_capture_drain_failed")
    return {"argv": argv, "returncode": code, "timed_out": timed_out, "timeout_seconds": timeout,
            "log_byte_limit_each": MAX_LOG_BYTES,
            "logs": [{"path": path.relative_to(root).as_posix(), **counter}
                     for path, counter in zip(paths, counters, strict=True)]}


def write_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    need(len(raw) <= MAX_METADATA, "receipt_metadata_bound")
    with path.open("xb") as stream:
        stream.write(raw)


def run(output, audit_timeout=180):
    root = ROOT.resolve()
    output = clean(output, root)
    need(output.is_relative_to(root / "runs") and not output.exists(), "fresh_allocation_required_under_runs")
    make_directories(output.parent, root)
    output.mkdir()
    source_records, restored, archive_rows = {}, [], []
    result = {"schema_version": "v15-exact-paper-input-restoration-verification/2", "status": "failed",
              "created_utc": datetime.now(timezone.utc).isoformat(), "phase": "input_preflight",
              "restored_required_inputs": restored, "archives": archive_rows,
              "full_extraction_or_runtime_qualification": False,
              "new_application_SDK_provider_solver_checker_or_evaluator_executions": 0,
              "existing_files_overwritten": False, "scientific_or_human_review_claimed": False}
    try:
        for name, expected_sha in PINNED.items():
            row = identify(target_for(root, name), root)
            need(row["sha256"] == expected_sha, "frozen_package_bytes_changed:" + name)
            source_records[name] = row
        package_names = list(PINNED) + ["scripts/verify_v15_paper_package_v1.py",
            "docs/research/paper-v15-offline-restoration-guide-v1.md", "scripts/verify_v15_paper_package_v2.py",
            "docs/research/paper-v15-offline-restoration-guide-v2.md"]
        package_before = [identify(target_for(root, name), root) for name in package_names]
        provenance = load(root, PROVENANCE, source_records)
        census = load(root, CENSUS, source_records)
        inputs = provenance["inputs"]
        need(len(inputs) == INPUT_COUNT and len(census["inputs"]) == INPUT_COUNT, "exact_3468_input_census_required")
        expected, census_rows, folded = {}, {}, set()
        for row in census["inputs"]:
            name = portable_name(row["path"])
            need(name not in census_rows, "duplicate_census_path")
            census_rows[name] = row
        existing, missing, spelling_cache = {}, [], {}
        groups = {}
        source_map = {portable_name(row["archive"]): row for row in census["archive_recovery_sources"]}
        member_bytes = 0
        for row in inputs:
            name, wanted = portable_name(row["path"]), byte_identity(row)
            need(name.casefold() not in folded and byte_identity(census_rows[name]) == wanted,
                 "input_census_identity_or_case_alias_changed")
            folded.add(name.casefold())
            expected[name] = wanted
            target = target_for(root, name)
            verify_existing_spelling(target, root, spelling_cache)
            if target.exists():
                need(byte_identity(identify(target, root, wanted["bytes"])) == wanted,
                     "existing_required_input_drift:" + name)
                existing[name] = wanted
            else:
                missing.append(name)
            if "/extracted/" in name:
                base, member = name.split("/extracted/", 1)
                archive = base + "/artifact.zip"
                group = groups.setdefault(archive, {"base": base, "members": {}, "publish_archive": False})
                group["members"][portable_name(member)] = (name, wanted)
                member_bytes += wanted["bytes"]
                recovery = census_rows[name].get("recovery")
                if recovery:
                    need(recovery["archive"] == archive and recovery["member"] == member
                         and recovery["inventory"] == base + "/extracted-manifest.json",
                         "census_member_mapping_leaves_exact_target")
            elif name.endswith("/artifact.zip"):
                group = groups.setdefault(name, {"base": name.removesuffix("/artifact.zip"), "members": {}, "publish_archive": False})
                group["publish_archive"] = True
            elif name in missing:
                # No legacy download/hosted targets exist in this frozen manifest.
                # Direct source/analysis inputs must be supplied by the checkout.
                raise ValueError("missing_direct_published_input:" + name)
        safe_prefixes(expected)
        need(member_bytes <= MAX_NEEDED_MEMBER_BYTES, "needed_member_byte_bound")
        result.update(required_input_count=len(expected), existing_exact_required_inputs=len(existing),
                      missing_required_input_count=len(missing), needed_archive_member_count=sum(len(row["members"]) for row in groups.values()),
                      needed_archive_member_bytes=member_bytes, source_group_count=len(groups))
        print(f"V2 preflight: {len(expected)} required inputs; {len(missing)} missing", flush=True)
        result["phase"] = "archive_and_needed_member_preflight"
        plans, total_archive_bytes = [], 0
        with ExitStack() as stack:
            for archive_name, group in sorted(groups.items()):
                base = portable_name(group["base"])
                need(base.startswith("runs/"), "retained_archive_source_must_be_under_runs")
                receipt, whole, inventory = metadata(root, base, source_records)
                if archive_name in expected:
                    need(whole == expected[archive_name], "required_archive_not_bound_to_provenance")
                total_archive_bytes += whole["bytes"]
                need(total_archive_bytes <= MAX_ARCHIVES_TOTAL, "total_source_archive_byte_bound")
                source_row = source_map.get(archive_name, {})
                preferred = source_row.get("index")
                if preferred:
                    need(portable_name(preferred).startswith(base + "/archive-parts"), "census_part_index_wrong_base")
                index_name, index = index_for(root, base, preferred, whole, source_records)
                archive_target = target_for(root, archive_name)
                part_count = 0
                if archive_target.exists():
                    actual = identify(archive_target, root, MAX_ARCHIVE)
                    need(byte_identity(actual) == whole, "existing_archive_drift")
                    source_records[archive_name] = actual
                    if index is not None:
                        part_count = verify_parts(root, base, index_name, index, receipt, whole, source_records)
                    stream = stack.enter_context(archive_target.open("rb"))
                    reconstructed = False
                else:
                    need(index is not None, "missing_archive_requires_bound_published_parts")
                    stream = stack.enter_context(tempfile.TemporaryFile(mode="w+b", dir=output))
                    part_count = verify_parts(root, base, index_name, index, receipt, whole, source_records, stream)
                    reconstructed = True
                zipped = stack.enter_context(zipfile.ZipFile(stream))
                files, expanded, central_count = validate_zip(zipped, inventory)
                for member, (_, wanted) in group["members"].items():
                    need(inventory.get(member) == wanted, "needed_member_not_same_provenance_and_inventory_bytes")
                    with zipped.open(files[member]) as source:
                        need(stream_identity(source, wanted["bytes"]) == wanted, "needed_member_hash_drift_before_mutation")
                record = {"archive": archive_name, "run_id": receipt["run_id"], "identity": whole,
                          "part_index": index_name, "parts_verified": part_count, "reconstructed_temporary_source": reconstructed,
                          "all_central_names_types_sizes_and_uniqueness_verified": central_count,
                          "advertised_total_expanded_bytes": expanded, "needed_members_byte_verified": len(group["members"]),
                          "publish_archive_as_required_input": group["publish_archive"],
                          "unneeded_member_payload_hashes_reexecuted": False}
                archive_rows.append(record)
                plans.append((archive_name, group, whole, stream, zipped, files))
                print("V2 checked " + base, flush=True)
            # Check all already present inputs again before the first publication.
            for name, wanted in existing.items():
                need(byte_identity(identify(target_for(root, name), root, wanted["bytes"])) == wanted,
                     "required_input_changed_during_global_preflight")
            result["phase"] = "publish_needed_inputs_only"
            result["all_source_preflight_passed_before_evidence_mutation"] = True
            for archive_name, group, whole, stream, zipped, files in plans:
                if group["publish_archive"] and archive_name not in existing:
                    stream.seek(0)
                    publish(stream, target_for(root, archive_name), whole, root)
                    restored.append({"path": archive_name, **whole, "kind": "required_archive"})
                for member, (name, wanted) in group["members"].items():
                    if name in existing:
                        continue
                    with zipped.open(files[member]) as source:
                        publish(source, target_for(root, name), wanted, root)
                    restored.append({"path": name, **wanted, "kind": "required_archive_member"})
        for name, wanted in expected.items():
            need(byte_identity(identify(target_for(root, name), root, wanted["bytes"])) == wanted,
                 "restored_exact_input_census_failed")
        result["phase"] = "unchanged_V15_read_audit"
        audit = root / "paper" / ("working-draft-v15.inputs-v2-" + uuid.uuid4().hex + ".json")
        clean(audit, root)
        need(not audit.exists(), "fresh_read_audit_target_required")
        argv = [sys.executable, "-I", "-S", "-B", "paper/audit_draft_v15.py",
                "--draft", "paper/working-draft-v15.md", "--provenance", PROVENANCE,
                "--ledger", "paper/claim-ledger-v15.json", "--output", str(audit)]
        command = run_bounded(argv, output, audit_timeout, root)
        write_json(output / "paper-read-audit.command.json", command)
        result["paper_read_audit_command"] = command
        need(command["returncode"] == 0 and not command["timed_out"], "fresh_V15_read_audit_command_failed")
        observed = load(root, audit.relative_to(root).as_posix(), source_records)
        need(observed["passed"] is True and observed["checks_passed"] == 19,
             "fresh_V15_read_audit_did_not_pass_19_checks")
        after = [identify(target_for(root, name), root) for name in package_names]
        need(package_before == after, "sealed_paper_or_V1_V2_package_source_changed")
        result.update(status="passed_exact_V15_paper_inputs_and_read_audit", phase="complete",
                      all_required_input_bytes_verified=len(expected), restored_required_input_count=len(restored),
                      restored_member_count=sum(row["kind"] == "required_archive_member" for row in restored),
                      restored_archive_count=sum(row["kind"] == "required_archive" for row in restored),
                      fresh_paper_audit=identify(audit, root), read_audit_checks_passed=19,
                      sealed_paper_and_V1_V2_package_sources_unchanged=True,
                      package_sources_before=package_before, package_sources_after=after)
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)[:4096]}
        result["restored_required_input_count"] = len(restored)
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        result["verified_source_records"] = list(source_records.values())
        write_json(output / "result.json", result)
        write_json(output / "manifest.json", {"files": [identify(path, root, MAX_METADATA)
                                                         for path in sorted(output.iterdir()) if path.is_file()]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    need(1 <= args.audit_timeout_seconds <= 300, "bounded_audit_timeout_required")
    value = run(args.output, args.audit_timeout_seconds)
    print(json.dumps({"status": value["status"], "restored_required_inputs": value.get("restored_required_input_count", 0),
                      "read_audit_checks": value.get("read_audit_checks_passed", 0), "new_runtime_or_provider_calls": 0}))
    raise SystemExit(value["status"] != "passed_exact_V15_paper_inputs_and_read_audit")
