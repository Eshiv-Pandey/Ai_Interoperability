"""Classify a pinned, denied urllib3 import probe without allowing its bind.

This is an offline research fixture guard, not an adversarial security sandbox.
No application/SDK functions are replaced. Every disallowed operation still
raises the original RuntimeError, including the recognized capability probe.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import socket
import sys
import sysconfig
from types import CodeType

SOURCE_SHA256 = "2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74"
SOURCE_BYTES = 4444


class OfflineSocketPolicy:
    def __init__(self, source: Path | None = None, *, listener_port: int | None = None):
        if listener_port is not None and (type(listener_port) is not int or not 1024 <= listener_port <= 65535):
            raise ValueError("Expected an unprivileged loopback listener port")
        self.source = (source or Path(sysconfig.get_path("purelib")) / "urllib3/util/connection.py").resolve()
        raw = self.source.read_bytes()
        if len(raw) != SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
            raise ValueError("The installed urllib3 capability source differs from the reviewed pin")
        self.module_code = compile(raw, str(self.source), "exec", dont_inherit=True)
        self.probe_code, = [code for code in self.module_code.co_consts
                            if isinstance(code, CodeType) and code.co_name == "_has_ipv6"]
        self.listener_port = listener_port
        self.socket_source = Path(socket.__file__).resolve()
        self.record = {
            "schema_version": "agentops-offline-socket-policy/1",
            "capability_source": {"installed_path": str(self.source), "bytes": len(raw), "sha256": SOURCE_SHA256},
            "listener_port": listener_port, "denied_capability_probes": [],
            "listener_binds": [], "internal_socketpairs": [], "unexpected": [],
        }

    def audit(self, event, arguments):
        if event not in {"socket.connect", "socket.bind"}:
            return
        sock, address = arguments[:2]
        frame = sys._getframe(1)
        row = {"event": event, "address": list(address) if isinstance(address, tuple) else repr(address),
               "family": int(sock.family), "socket_type": int(sock.type)}
        if (event == "socket.bind" and address == ("::1", 0)
                and sock.family == socket.AF_INET6 and sock.type == socket.SOCK_STREAM
                and frame.f_code == self.probe_code and frame.f_back is not None
                and frame.f_back.f_code == self.module_code
                and frame.f_globals.get("__name__") == "urllib3.util.connection"
                and Path(frame.f_globals.get("__file__", "")).resolve() == self.source):
            row.update(action="blocked", function="_has_ipv6", phase="module-import",
                       source_sha256=SOURCE_SHA256)
            self.record["denied_capability_probes"].append(row)
            # The pinned source already catches Exception and reports no IPv6.
            # Preserve v2 behavior: neither bind nor connection reaches the OS.
            raise RuntimeError("The in-process offline control forbids socket connections/listeners")
        if (self.listener_port is not None and event == "socket.bind"
                and address == ("127.0.0.1", self.listener_port)
                and sock.family == socket.AF_INET and sock.type == socket.SOCK_STREAM):
            self.record["listener_binds"].append(row)
            return
        cursor = frame
        while cursor is not None:
            if (cursor.f_code.co_name == "socketpair"
                    and Path(cursor.f_code.co_filename).resolve() == self.socket_source
                    and isinstance(address, tuple) and len(address) >= 2
                    and address[0] in {"127.0.0.1", "::1"}
                    and type(address[1]) is int and 0 <= address[1] <= 65535):
                self.record["internal_socketpairs"].append(row)
                return
            cursor = cursor.f_back
        row["stack"] = []
        while frame is not None:
            row["stack"].append({"path": frame.f_code.co_filename,
                                 "function": frame.f_code.co_name, "line": frame.f_lineno})
            frame = frame.f_back
        self.record["unexpected"].append(row)
        raise RuntimeError("The in-process offline control forbids socket connections/listeners")
