"""Versioned export support for built-in-fcntl runtime revalidation.

Preserves prior export logic and records all JSON inspection stdout streams.
"""
import json
import os
from pathlib import Path
from run_agentops_linux_workspace_v5 import record, relative_file, copy_exact, referenced_records, MAX_EXPORT_BYTES

def export_evidence(root: Path, destination: Path, inputs: list[dict]) -> dict:
    """Export exact source, receipts and explicitly referenced runtime file bytes.

    Relative references resolve inside the exported replica, never the parent
    Windows attempt. Missing/mismatched references are reported, not rewritten.
    """
    selected = {row["path"]: row for row in inputs}
    failures = []
    symlinks = []
    supplemental_sources = set()
    if (root / "runs").exists():
        for path in (root / "runs").rglob("*"):
            if path.is_symlink():
                # Pytest creates convenience *current links. Preserve their
                # literal targets as inert metadata without following/materializing.
                symlinks.append({"path": path.relative_to(root).as_posix(), "target": os.readlink(path)})
            elif path.is_file():
                row = record(path, root)
                selected[row["path"]] = row
    # The runtime inspection is JSON serialized into .stdout.bin, so include
    # those known inspection streams as well as ordinary receipt JSON.
    pending = list(selected)
    inspected = set()
    while pending:
        name = pending.pop()
        if name in inspected:
            continue
        inspected.add(name)
        if not name.startswith("runs/") or not (name.endswith(".json") or name.endswith(".stdout.bin")):
            continue
        path = relative_file(root, name)
        try:
            data = json.loads(path.read_bytes())
        except (UnicodeError, ValueError):
            continue
        for row in referenced_records(data):
            try:
                referenced = relative_file(root, row["path"])
                if not referenced.is_file() or record(referenced, root) != row:
                    raise ValueError(f"Missing/changed referenced bytes: {row['path']}")
                previous = selected.get(row["path"])
                if previous is not None and previous != row:
                    raise ValueError(f"Conflicting retained hashes: {row['path']}")
                if previous is None:
                    selected[row["path"]] = row
                    pending.append(row["path"])
            except (OSError, ValueError) as error:
                failures.append(str(error))
        if isinstance(data, dict) and "fcntl_extension" in data:
            item = data["fcntl_extension"]
            try:
                module = Path(item["path"])
                name = module.relative_to(root).as_posix()
                row = record(relative_file(root, name), root)
                if row["sha256"] != item["sha256"]:
                    raise ValueError("Native fcntl bytes changed")
                selected[name] = row
            except (OSError, ValueError) as error:
                failures.append(str(error))
        if isinstance(data, dict) and data.get("schema_version") in {"agentops-installed-runtime-inspection/4", "agentops-installed-runtime-inspection/5"}:
            # Preserve terminal installed source bytes for the next converter/
            # version-fidelity analysis, separately from pre-execution pin claims.
            folders = {"google-adk": "google/adk/a2a", "a2a-sdk": "a2a/compat"}
            for package in data["packages"]:
                if package["name"] not in folders:
                    continue
                folder_name = package["location"] + "/" + folders[package["name"]]
                folder = relative_file(root, folder_name)
                for module in folder.rglob("*.py"):
                    name = module.relative_to(root).as_posix()
                    row = record(relative_file(root, name), root)
                    selected.setdefault(name, row)
                    supplemental_sources.add(name)
    rows = sorted(selected.values(), key=lambda row: row["path"])
    total = sum(row["bytes"] for row in rows)
    if total > MAX_EXPORT_BYTES:
        raise ValueError(f"Evidence export exceeds {MAX_EXPORT_BYTES} bytes; Linux original retained at {root}")
    destination.mkdir(parents=True, exist_ok=False)
    copy_exact(root, destination, rows)
    return {"files": rows, "bytes": total, "inert_symlinks": symlinks,
            "post_execution_runtime_source_files": sorted(supplemental_sources),
            "reference_failures": sorted(set(failures)),
            "original_linux_root": str(root), "export_root": str(destination),
            "scope": "Exact inputs, run outputs and referenced runtime bytes; not a complete executable runtime"}

