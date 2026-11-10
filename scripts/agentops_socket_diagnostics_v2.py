"""Durable, bounded socket-denial diagnostics; this module authorizes no socket."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import traceback

SOCKET_DENIALS = frozenset({"socket.bind", "socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto", "socket.sendmsg"})


def sanitized(value, aliases=(), limit=512):
    value = str(value)
    for prefix, label in sorted(aliases, key=lambda row: len(row[0]), reverse=True):
        value = value.replace(str(prefix), label)
    value = re.sub(r"AIza[A-Za-z0-9_-]{30,}", "<redacted-api-key>", value)
    value = re.sub(r"(?i)(api[_-]?key|password|authorization|bearer)[=: ]+[^\s,;]+", r"\1=<redacted>", value)
    value = re.sub(r"-----BEGIN[^\n]*PRIVATE KEY-----[\s\S]*", "<redacted-private-key>", value)
    return value[:limit]


def bounded_value(value, aliases=(), depth=0):
    if depth > 4:
        return {"kind": "depth-bound"}
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {"kind": "nonfinite"}
    if isinstance(value, str):
        return sanitized(value, aliases)
    if isinstance(value, bytes):
        return {"kind": "bytes", "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest(),
                "sanitized_text": sanitized(value[:512].decode("utf-8", "replace"), aliases)}
    if isinstance(value, (tuple, list)):
        return [bounded_value(item, aliases, depth + 1) for item in value[:8]]
    return {"kind": type(value).__name__[:80]}


def socket_attributes(sock):
    result = {}
    for name in ("family", "type", "proto"):
        value = getattr(sock, name, None)
        if isinstance(value, int):
            result[name] = {"value": int(value), "name": getattr(value, "name", None)}
        else:
            result[name] = None
    return result


def diagnostic(event, arguments, aliases=(), frames=None, source_directory=None):
    """Describe a denied event without inspecting request headers or locals."""
    row = {"event": event, "decision": "denied_before_socket_operation",
           "recorded_at_utc": datetime.now(timezone.utc).isoformat()}
    if event == "socket.getaddrinfo":
        row["arguments"] = bounded_value(arguments, aliases)
        row["socket"] = None
    else:
        row["socket"] = socket_attributes(arguments[0]) if arguments else None
        row["target_or_arguments_after_socket"] = bounded_value(arguments[1:], aliases)
    selected = frames if frames is not None else traceback.extract_stack(limit=24)[:-1]
    stack = []
    for frame in selected[-24:]:
        filename = frame.filename
        entry = {"filename": sanitized(filename, aliases, 512), "function": sanitized(frame.name, aliases, 128),
                 "line": int(frame.lineno)}
        path = Path(filename)
        if path.is_file() and path.suffix == ".py" and path.stat().st_size <= 1_000_000:
            raw = path.read_bytes()
            entry["source_sha256"] = hashlib.sha256(raw).hexdigest()
            entry["source_bytes"] = len(raw)
            lines = raw.decode("utf-8", "replace").splitlines()
            start, stop = max(0, frame.lineno - 3), min(len(lines), frame.lineno + 2)
            entry["sanitized_source_excerpt"] = [sanitized(line, aliases, 240) for line in lines[start:stop]]
            entry["excerpt_first_line"] = start + 1
            if source_directory is not None:
                target = source_directory / (entry["source_sha256"] + ".py")
                if not target.exists():
                    with target.open("xb") as handle:
                        handle.write(raw)
                        handle.flush()
                        os.fsync(handle.fileno())
                entry["retained_source"] = "diagnostic-source/" + target.name
        stack.append(entry)
    row["stack"] = stack
    row["stack_bound"] = 24
    row["locals_or_headers_captured"] = False
    return row


def make_guard(case, denied, aliases=()):
    source = case / "diagnostic-source"
    source.mkdir(exist_ok=False)
    journal = case / "audit-denials.jsonl"
    with journal.open("x", encoding="utf-8"):
        pass
    def guard(event, arguments):
        private = (event == "open" and isinstance(arguments[0], (str, bytes, os.PathLike))
                   and Path(os.fsdecode(arguments[0])).name == "evaluator.json")
        if event not in SOCKET_DENIALS and not private:
            return
        row = {"event": "private_evaluator_open"} if private else diagnostic(event, arguments, aliases, source_directory=source)
        denied.append(row)
        with journal.open("a", encoding="utf-8", newline="\n") as target:
            target.write(json.dumps(row, allow_nan=False) + "\n")
            target.flush()
            os.fsync(target.fileno())
        raise PermissionError("Private evaluator and native/provider socket operations are denied in the diagnostic App pilot")
    return guard
