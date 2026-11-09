"""Copy one preparation/3 admission allocation without running applications.

Embedded paths are preserved as evidence, not followed. External Python/Node
runtime closures are deliberately not copied. A failed attempt is retained and
the destination must never be reused. Exact exporter source bytes are captured
outside the workspace replica; the tool need not be staged into the experiment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

GROUP = "runs/agentops-admission-live-v1"
PREPARATION_SCHEMA = "agentops-admission-live-preparation/3"
EXPORTER_SOURCE = "exporter-source.py"
PLAN = GROUP + "/preparation/plan.json"
TERMINAL = GROUP + "/attempt/result.json"
TREES = (GROUP, "runs/agentops-http-control/admission-live-v1-N11",
         "runs/agentops-http-control/admission-live-v1-B7")
TERMINAL_STATUSES = {"strict_success", "attempts_recorded", "failed", "failed_integrity"}


def now():
    return datetime.now(timezone.utc).isoformat()


def relative_name(name):
    if type(name) is not str:
        raise ValueError("Evidence path must be a string")
    path = PurePosixPath(name)
    if (not path.parts or path.is_absolute() or ".." in path.parts
            or any(char in name for char in ("\\", ":", "\0"))
            or name != path.as_posix()):
        raise ValueError("Unsafe or noncanonical evidence path: " + repr(name))
    return name


def checked_path(path, *, missing=False):
    """Reject symlinks/reparse points in every existing component."""
    path = Path(path)
    if ".." in path.parts:
        raise ValueError("Path traversal is not allowed: " + str(path))
    path = path.absolute()
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            info = current.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ValueError("Symlink or reparse point refused: " + str(current))
    if path.resolve(strict=not missing) != path:
        raise ValueError("Resolved path differs from requested path: " + str(path))
    return path


def source_file(root, name):
    path = checked_path(root / relative_name(name))
    if not path.is_relative_to(root) or not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Evidence must be a regular file inside the workspace: " + name)
    return path


def read_file(root, name, destination=None):
    """Hash bytes actually read; exclusive binary copy when requested."""
    path = source_file(root, name)
    expected_stat = path.stat()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    digest, length = hashlib.sha256(), 0
    with os.fdopen(os.open(path, flags), "rb") as source:
        opened_stat = os.fstat(source.fileno())
        if (not stat.S_ISREG(opened_stat.st_mode)
                or (opened_stat.st_dev, opened_stat.st_ino) != (expected_stat.st_dev, expected_stat.st_ino)):
            raise ValueError("Source changed while opening: " + name)
        target = None
        try:
            if destination is not None:
                destination = checked_path(destination, missing=True)
                destination.parent.mkdir(parents=True, exist_ok=True)
                checked_path(destination.parent)
                target = destination.open("xb")
            while block := source.read(1024 * 1024):
                digest.update(block)
                length += len(block)
                if target is not None:
                    target.write(block)
        finally:
            if target is not None:
                target.close()
        final_stat = os.fstat(source.fileno())
    current = source_file(root, name).stat()
    # Windows stat/fstat may expose different legacy ctime semantics. Content
    # hashes and mtime/identity checks are used on both platforms; POSIX also
    # has a consistent inode change time.
    signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
                               value.st_ctime_ns if os.name != "nt" else None)
    if signature(opened_stat) != signature(final_stat) or signature(final_stat) != signature(current):
        raise ValueError("Source changed while reading: " + name)
    return {"path": name, "bytes": length, "sha256": digest.hexdigest()}


def walk_tree(root, name, errors):
    """Return actual regular files and directories, never follow links."""
    start = checked_path(root / name, missing=True)
    if not start.exists():
        return [], [], False
    if not start.is_dir():
        raise ValueError("Expected evidence directory: " + name)
    files, directories, pending = [], [name], [start]
    while pending:
        folder = checked_path(pending.pop())
        with os.scandir(folder) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            child = Path(entry.path)
            relative = child.relative_to(root).as_posix()
            try:
                relative_name(relative)
                checked_path(child)
                mode = child.lstat().st_mode
                if stat.S_ISREG(mode):
                    files.append(relative)
                elif stat.S_ISDIR(mode):
                    directories.append(relative)
                    pending.append(child)
                else:
                    raise ValueError("Nonregular evidence entry refused: " + relative)
            except (OSError, ValueError) as error:
                errors.append(str(error))
    return files, directories, True


def snapshot(root, inputs, trees=TREES):
    names, directories, missing_trees, errors = set(inputs), [], [], []
    for name in trees:
        try:
            files, folders, exists = walk_tree(root, name, errors)
            names.update(files)
            directories.extend(folders)
            if not exists:
                missing_trees.append(name)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    rows = []
    for name in sorted(names):
        try:
            rows.append(read_file(root, name))
        except (OSError, ValueError) as error:
            errors.append(name + ": " + str(error))
    return {"files": rows, "directories": sorted(set(directories)),
            "missing_scope_directories": missing_trees,
            "complete": not errors, "errors": errors}


def staged_inputs(plan, root):
    if (type(plan) is not dict or plan.get("schema_version") != PREPARATION_SCHEMA
            or plan.get("workspace") != str(root) or type(plan.get("inputs")) is not list
            or type(plan.get("reuse_root")) is not str):
        raise ValueError("Malformed preparation plan or workspace identity mismatch")
    result = {}
    for row in plan["inputs"]:
        if (type(row) is not dict or set(row) != {"path", "bytes", "sha256"}
                or type(row["bytes"]) is not int or row["bytes"] < 0
                or type(row["sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None):
            raise ValueError("Malformed staged input record")
        name = relative_name(row["path"])
        if name in result:
            raise ValueError("Duplicate staged input: " + name)
        result[name] = row
    return result


def group_execution(replica):
    """Summarize retained bytes without granting success to missing records."""
    report = {"path": TERMINAL, "record_status": "missing", "status": None,
              "cases": {name: {"record_status": "missing", "status": None} for name in ("N11", "B7")}}
    try:
        path = source_file(replica, TERMINAL)
    except FileNotFoundError:
        return report
    try:
        value = json.loads(path.read_bytes())
        if type(value) is not dict:
            raise ValueError("Group result must be an object")
        report["status"] = value.get("status")
        cases = value.get("cases")
        if type(cases) is dict:
            for name in report["cases"]:
                item = cases.get(name)
                if type(item) is dict:
                    report["cases"][name] = {"record_status": "present" if type(item.get("status")) is str else "incomplete",
                                             "status": item.get("status"), "record": item}
        complete = (value.get("schema_version") == "agentops-admission-live-group/1"
                    and type(value.get("status")) is str and value["status"] in TERMINAL_STATUSES
                    and type(value.get("started_at_utc")) is str and bool(value["started_at_utc"])
                    and type(value.get("finished_at_utc")) is str and bool(value["finished_at_utc"])
                    and type(value.get("plan")) is dict
                    and all(item["record_status"] == "present" for item in report["cases"].values()))
        report["record_status"] = "terminal" if complete else "incomplete"
    except (OSError, ValueError) as error:
        report.update(record_status="invalid", error=str(error))
    return report


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def export_workspace(workspace, output):
    root = checked_path(workspace)
    output = checked_path(output, missing=True)
    exporter_path = checked_path(Path(__file__))
    if not root.is_dir() or root.is_relative_to(output) or output.is_relative_to(root):
        raise ValueError("Workspace and export directory must be disjoint directories")
    output.mkdir(parents=True, exist_ok=False)
    replica = output / "workspace"
    replica.mkdir()
    manifest = {"schema_version": "agentops-admission-export-manifest/3", "started_at_utc": now(),
                "original_workspace": str(root), "export_directory": str(output),
                "scope": {"plan": PLAN, "preparation_schema": PREPARATION_SCHEMA,
                          "run_directories": list(TREES), "embedded_references_followed": False,
                          "external_runtime_closure_copied": False,
                          "exporter_source_outside_workspace": True,
                          "external_references": "Original absolute diagnostic/source paths remain unchanged references; external runtime packages are not included."},
                "reuse_root": None, "expected_staged_inputs": [], "source_before": None,
                "source_after": None, "copied": None, "sources_unchanged": None,
                "copies_match_source_before": None, "failures": []}
    exporter = manifest["exporter"] = {"original_path": str(exporter_path), "before": None, "after": None,
        "copy_before": None, "copy_after": None, "source_unchanged": None, "copy_matches_before": None}
    inputs, plan = {}, None
    try:
        exporter["before"] = read_file(exporter_path.parent, exporter_path.name)
        source_copy = read_file(exporter_path.parent, exporter_path.name, output / EXPORTER_SOURCE)
        exporter["copy_before"] = read_file(output, EXPORTER_SOURCE)
        if (source_copy != exporter["before"]
                or {**exporter["copy_before"], "path": exporter_path.name} != exporter["before"]):
            raise ValueError("Exporter source changed between inventory and capture")
        plan_path = source_file(root, PLAN)
        plan_raw = plan_path.read_bytes()
        plan = json.loads(plan_raw)
        if type(plan) is dict:
            manifest["reuse_root"] = plan.get("reuse_root")
        inputs = staged_inputs(plan, root)
        manifest["expected_staged_inputs"] = list(inputs.values())
        before = manifest["source_before"] = snapshot(root, inputs)
        manifest["failures"].extend(before["errors"])
        actual = {row["path"]: row for row in before["files"]}
        if actual.get(PLAN) != {"path": PLAN, "bytes": len(plan_raw), "sha256": hashlib.sha256(plan_raw).hexdigest()}:
            manifest["failures"].append("Preparation plan changed between parsing and inventory")
        for name, expected in inputs.items():
            if actual.get(name) != expected:
                manifest["failures"].append("Staged input differs from preparation plan: " + name)
        for row in before["files"]:
            try:
                copied = read_file(root, row["path"], replica / row["path"])
                if copied != row:
                    manifest["failures"].append("Source changed between inventory and copy: " + row["path"])
            except (OSError, ValueError) as error:
                manifest["failures"].append("Copy " + row["path"] + ": " + str(error))
    except (OSError, ValueError, TypeError) as error:
        manifest["failures"].append(type(error).__name__ + ": " + str(error))
    finally:
        manifest["source_after"] = snapshot(root, inputs)
        manifest["copied"] = snapshot(replica, (), trees=(".",))
        manifest["failures"].extend(manifest["source_after"]["errors"] + manifest["copied"]["errors"])
        before, after, copied = manifest["source_before"], manifest["source_after"], manifest["copied"]
        if before is not None and before["complete"] and after["complete"]:
            manifest["sources_unchanged"] = before == after
            if not manifest["sources_unchanged"]:
                manifest["failures"].append("Selected source inventory changed during export")
        if before is not None and before["complete"] and copied["complete"]:
            manifest["copies_match_source_before"] = before["files"] == copied["files"]
            if not manifest["copies_match_source_before"]:
                manifest["failures"].append("Copied inventory differs from source before export")
        try:
            exporter["after"] = read_file(exporter_path.parent, exporter_path.name)
            exporter["copy_after"] = read_file(output, EXPORTER_SOURCE)
            if exporter["before"] is not None:
                exporter["source_unchanged"] = exporter["before"] == exporter["after"]
                exporter["copy_matches_before"] = ({**exporter["copy_after"], "path": exporter_path.name} == exporter["before"]
                    and exporter["copy_after"] == exporter["copy_before"])
                if not exporter["source_unchanged"]:
                    manifest["failures"].append("Exporter source changed during export")
                if not exporter["copy_matches_before"]:
                    manifest["failures"].append("Captured exporter differs from its original source inventory")
        except (OSError, ValueError) as error:
            manifest["failures"].append("Exporter source verification: " + str(error))
        manifest["failures"] = sorted(set(manifest["failures"]))
        manifest["finished_at_utc"] = now()
        execution = group_execution(replica)
        status = "exported" if (not manifest["failures"] and manifest["sources_unchanged"] is True
                                  and manifest["copies_match_source_before"] is True
                                  and exporter["source_unchanged"] is True and exporter["copy_matches_before"] is True) else "failed"
        manifest["status"] = status
        write_new(output / "manifest.json", manifest)
        result = {"schema_version": "agentops-admission-export-result/3", "status": status,
                  "finished_at_utc": manifest["finished_at_utc"], "workspace": str(root), "output": str(output),
                  "group_execution": execution, "reuse_root": manifest["reuse_root"],
                  "exporter_source": exporter["copy_after"] or exporter["copy_before"],
                  "exporter_source_unchanged": exporter["source_unchanged"],
                  "exporter_copy_matches_before": exporter["copy_matches_before"],
                  "external_runtime_closure_copied": False, "sources_unchanged": manifest["sources_unchanged"],
                  "copies_match_source_before": manifest["copies_match_source_before"],
                  "copied_files": len(copied["files"]), "copied_bytes": sum(row["bytes"] for row in copied["files"]),
                  "manifest": read_file(output, "manifest.json"), "failures": manifest["failures"]}
        write_new(output / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = export_workspace(args.workspace, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, type(error).__name__ + ": " + str(error) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "exported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
