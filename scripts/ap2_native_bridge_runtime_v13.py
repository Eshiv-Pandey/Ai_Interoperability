"""Offline materialization of the two previously sealed original bridge runtimes.

The installed graph, package bytes, links and outgoing bridge implementations
are retained unchanged. This module does not install, launch or make requests.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/research/source-evidence/agentops-bridge-control-v1/runtime"
GRAPH_SHA = "efafadaa673d78dd1e4ccf20d92db9941e00d6bd802d909fdae4c4b8a8278de6"
ARCHIVE_SHA = "c4567dc405e74d664921f038e6c5acb454c66fd85f42f21c04a10c8e75305864"
NODE_VERSION = "v22.23.2"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def pinned_inputs():
    from agentops_bridge_runtime_archive_v1 import check_graph, safe_name
    graph_raw = (INPUT / "graph.json").read_bytes()
    archive_raw = (INPUT / "runtime.zip").read_bytes()
    receipt = json.loads((INPUT / "archive.json").read_bytes())
    if (sha(graph_raw) != GRAPH_SHA or sha(archive_raw) != ARCHIVE_SHA
            or receipt["status"] != "archive_verified"
            or receipt["graph_sha256"] != GRAPH_SHA
            or receipt["archive_sha256"] != ARCHIVE_SHA
            or receipt["bytes"] != len(archive_raw)):
        raise ValueError("sealed_original_bridge_runtime_changed")
    graph = json.loads(graph_raw)
    nodes = check_graph(graph)
    expected = {row["path"]: row for row in graph["files"]}
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        infos = archive.infolist()
        if (len(infos) != len({row.filename for row in infos})
                or {row.filename for row in infos} != set(expected) | {"graph.json"}):
            raise ValueError("bridge_archive_exact_member_set_changed")
        for row in infos:
            safe_name(row.filename)
            if row.is_dir() or row.flag_bits & 1 or ((row.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError("bridge_archive_nonregular_member")
            raw = archive.read(row)
            if row.filename == "graph.json":
                if raw != graph_raw:
                    raise ValueError("bridge_archived_graph_changed")
            elif len(raw) != expected[row.filename]["bytes"] or sha(raw) != expected[row.filename]["sha256"]:
                raise ValueError("bridge_archived_package_bytes_changed")
    return graph_raw, archive_raw, graph, nodes


def materialize(target):
    """Create one new Linux replica from verified bytes without dependency resolution."""
    if sys.platform != "linux":
        raise ValueError("bridge_runtime_materialization_requires_linux_symlinks")
    target = Path(target).absolute()
    if target.exists() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError("new_regular_bridge_runtime_destination_required")
    graph_raw, archive_raw, graph, nodes = pinned_inputs()
    target.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        for row in graph["files"]:
            path = target / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(archive.read(row["path"]))
    (target / "graph.json").write_bytes(graph_raw)
    report = {
        "schema_version": "agentops-bridge-runtime-materialization/1",
        "status": "materialized_import_check_pending", "runtime_root": str(target),
        "archive_sha256": ARCHIVE_SHA, "graph_sha256": GRAPH_SHA,
        "application_requests": 0, "live_model_calls": 0, "installations": 0,
        "links": [], "bridges": {}, "packages": len(nodes),
        "files": len(graph["files"]), "bytes": graph["total_bytes"],
        "separately_declared_ap2_native_study": True,
        "historical_runtime_materialization_receipt_reused": False,
    }

    def link(name, destination):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        relative = os.path.relpath(target / destination, path.parent)
        if not (path.parent / relative).resolve().is_relative_to(target.resolve()):
            raise ValueError("bridge_dependency_link_escapes_owned_runtime")
        path.symlink_to(relative, target_is_directory=True)
        report["links"].append({"path": name, "target": relative, "resolved": destination})

    for edge in graph["edges"]:
        link(nodes[edge["from"]]["destination"] + "/node_modules/" + edge["name"], nodes[edge["to"]]["destination"])
    for row in graph["roots"]:
        alias = "external/" + row["alias"]
        link(alias, nodes[row["node"]]["destination"])
        report["bridges"][row["alias"]] = {
            "package_root": str(target / alias), "cli": str(target / alias / "dist/cli.js"),
            "entry": str(target / alias / "dist/index.js"),
        }
    write(target / "materialization.json", report)
    verify(target)
    return report


def verify(target):
    from agentops_bridge_runtime_archive_v1 import verify_runtime
    graph_raw, _, graph, _ = pinned_inputs()
    target = Path(target).absolute()
    report = json.loads((target / "materialization.json").read_bytes())
    if report["graph_sha256"] != sha(graph_raw):
        raise ValueError("fresh_bridge_runtime_graph_identity_changed")
    return verify_runtime(target, graph, report)


def verify_outgoing_sources(records):
    """Bind source-map evidence to source files in the exact executed graph."""
    _, _, _, nodes = pinned_inputs()
    retained = {node['original_root'] + '/' + row['path']: {key: row[key] for key in ('bytes', 'sha256')}
                for node in nodes.values() if node['original_root'] in {'external/a2a-to-mcp', 'external/mcp-a2a'}
                for row in node['files']}
    for name, row in records.items():
        expected = {key: row[key] for key in ('bytes', 'sha256')}
        if retained.get(name) != expected or sha((ROOT / row['retained_path']).read_bytes()) != expected['sha256']:
            raise ValueError('original_outgoing_map_source_not_exact_sealed_runtime_source')
    return {'source_records_verified': len(records), 'executed_graph_sha256': GRAPH_SHA,
            'source_copies_equal_executed_original_package_sources': True}
