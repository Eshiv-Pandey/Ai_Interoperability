"""Independent data-only checks for the disclosed offline fixture policy.

No observer, application, SDK or archived source code is imported/executed.
Capture provenance and installed-source bytes remain separate obligations.
"""
from pathlib import PurePosixPath

PIN = "2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74"


def require(value, message):
    if value is not True:
        raise ValueError(message)


def check_policy(value, *, listener_port=None):
    require(value.get("schema_version") == "agentops-offline-socket-policy/1", "socket policy schema")
    require(value.get("listener_port") == listener_port, "socket listener configuration")
    source = value["capability_source"]
    path = PurePosixPath(source["installed_path"])
    require(path.is_absolute() and ".." not in path.parts
            and path.as_posix().endswith("/lib/python3.13/site-packages/urllib3/util/connection.py"),
            "Linux capability source path")
    require(source["sha256"] == PIN and type(source["bytes"]) is int and source["bytes"] == 4444,
            "capability source pin")
    require(value["unexpected"] == [] and value["internal_socketpairs"] == [],
            "Linux control attempted an unexpected network operation")
    probes = value["denied_capability_probes"]
    require(type(probes) is list and len(probes) <= 1, "single import capability probe")
    expected = {"event": "socket.bind", "address": ["::1", 0], "family": 10,
                "socket_type": 1, "action": "blocked", "function": "_has_ipv6",
                "phase": "module-import", "source_sha256": PIN}
    # JSON serialization distinguishes booleans from integers.
    import json
    require(all(json.dumps(row, sort_keys=True) == json.dumps(expected, sort_keys=True) for row in probes),
            "capability probe was not the exact blocked initialization event")
    binds = value["listener_binds"]
    wanted = [] if listener_port is None else [{"event": "socket.bind", "address": ["127.0.0.1", listener_port],
                                              "family": 2, "socket_type": 1}]
    require(json.dumps(binds, sort_keys=True) == json.dumps(wanted, sort_keys=True), "listener bind inventory")
    return {"status": "passed", "blocked_capability_probes": len(probes), "listener_binds": len(binds)}
