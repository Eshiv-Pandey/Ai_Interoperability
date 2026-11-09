"""Bounded HTTP/1.1 capture and strict decoding for local research controls.

No SDK, application imports, retries, proxy use or inferred transport evidence.
The socket request and response bytes include HTTP framing. TCP packets/timing
and traffic outside this one connection are not captured.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import time


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError("Duplicate JSON member: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Nonfinite JSON value: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def decode_response(raw: bytes) -> tuple[int, dict[str, str], bytes]:
    head, sep, body = raw.partition(b"\r\n\r\n")
    if not sep:
        raise ValueError("Incomplete HTTP headers")
    lines = head.decode("iso-8859-1").split("\r\n")
    version, status, *_ = lines[0].split(" ")
    if version != "HTTP/1.1" or len(status) != 3 or not status.isdigit():
        raise ValueError("Expected one HTTP/1.1 response")
    headers = {}
    for line in lines[1:]:
        name, colon, value = line.partition(":")
        name = name.lower()
        if not colon or not name or name.strip() != name or name in headers:
            raise ValueError("Malformed or duplicate response header")
        headers[name] = value.strip()
    if "content-encoding" in headers and headers["content-encoding"] != "identity":
        raise ValueError("Encoded response outside this control")
    if "transfer-encoding" in headers:
        if headers["transfer-encoding"].lower() != "chunked" or "content-length" in headers:
            raise ValueError("Ambiguous or unsupported HTTP framing")
        chunks = []
        while True:
            size_line, sep, body = body.partition(b"\r\n")
            size_text = size_line.split(b";", 1)[0]
            if not sep or not size_text or any(c not in b"0123456789abcdefABCDEF" for c in size_text):
                raise ValueError("Invalid chunk length")
            size = int(size_text, 16)
            if size == 0:
                # Uvicorn does not emit trailers for these responses. Fail closed
                # on additional bytes; never silently discard a second response.
                if body != b"\r\n":
                    raise ValueError("Unexpected trailers or trailing bytes")
                body = b"".join(chunks)
                break
            if len(body) < size + 2 or body[size:size + 2] != b"\r\n":
                raise ValueError("Truncated or malformed chunk")
            chunks.append(body[:size])
            body = body[size + 2:]
    elif "content-length" in headers:
        length = headers["content-length"]
        if not length.isdigit() or len(body) != int(length):
            raise ValueError("HTTP content length mismatch")
    else:
        raise ValueError("Unframed response outside this control")
    return int(status), headers, body


def rpc_results(body: bytes, rpc_id: str) -> list[dict]:
    """Parse complete SSE events; retain order and reject RPC errors/misbindings."""
    content = body.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if not content.endswith("\n\n"):
        raise ValueError("SSE stream ends inside an event")
    lines = content.split("\n")
    results, data = [], []
    for line in lines:
        if line == "":
            if data:
                event = strict_json("\n".join(data))
                if (not isinstance(event, dict) or event.get("jsonrpc") != "2.0"
                        or event.get("id") != rpc_id or "error" in event
                        or not isinstance(event.get("result"), dict)):
                    raise ValueError("Unexpected JSON-RPC SSE envelope")
                results.append(event["result"])
                data = []
        elif not line.startswith(":"):
            field, sep, value = line.partition(":")
            if field == "data":
                data.append(value[1:] if value.startswith(" ") else value)
            elif field not in {"event", "id", "retry"}:
                raise ValueError("Unexpected SSE field")
    if data or not results:
        raise ValueError("Incomplete or empty SSE response")
    return results


def exchange(output: Path, label: str, port: int, method: str, path: str,
             payload: dict | None = None, *, timeout: float = 45) -> dict:
    if not 1024 <= port <= 65535 or method not in {"GET", "POST"}:
        raise ValueError("Only the frozen local HTTP control is supported")
    if not path.startswith("/") or any(c in path for c in "\r\n "):
        raise ValueError("Invalid request target")
    body = b"" if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False,
                                                 separators=(",", ":")).encode("utf-8")
    headers = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{port}",
               "Connection: close", "Accept-Encoding: identity",
               "Accept: application/json, text/event-stream", f"Content-Length: {len(body)}"]
    if payload is not None:
        headers.append("Content-Type: application/json")
    request = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + body
    with (output / f"{label}.request.bin").open("xb") as stream:
        stream.write(request)
    record = {"label": label, "method": method, "path": path, "port": port,
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "request_fully_sent": False, "response_eof": False, "status": "failed"}
    deadline = time.monotonic() + timeout
    try:
        with (output / f"{label}.response.bin").open("xb") as stream:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout) as connection:
                connection.sendall(request)
                record["request_fully_sent"] = True
                total = 0
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("HTTP control deadline")
                    connection.settimeout(remaining)
                    chunk = connection.recv(65536)
                    if not chunk:
                        record["response_eof"] = True
                        break
                    stream.write(chunk)
                    total += len(chunk)
                    if total > 32 * 1024 * 1024:
                        raise ValueError("HTTP control byte limit")
        record["status"] = "captured"
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    with (output / f"{label}.exchange.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
    if record["status"] != "captured":
        raise ValueError(f"HTTP exchange failed; retained {label} bytes and receipt")
    return record
