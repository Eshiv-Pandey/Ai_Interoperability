"""Import-only diagnosis under the existing socket-denial rule; no AgentOps run."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import socket
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Retain the existing diagnostic")
    result = {"schema_version": "agentops-urllib3-import-diagnostic/1", "status": "failed",
              "started_at_utc": datetime.now(timezone.utc).isoformat(), "events": [],
              "application_imports": 0, "application_requests": 0, "model_calls": 0}

    def audit(event, arguments):
        if event not in {"socket.connect", "socket.bind"}:
            return
        sock, address = arguments[:2]
        stack = []
        frame = sys._getframe(1)
        while frame is not None:
            stack.append({"path": frame.f_code.co_filename, "function": frame.f_code.co_name,
                          "line": frame.f_lineno})
            frame = frame.f_back
        result["events"].append({"event": event, "address": list(address) if isinstance(address, tuple) else str(address),
                                  "family": int(sock.family), "socket_type": int(sock.type), "stack": stack})
        raise RuntimeError("The in-process offline control forbids socket connections/listeners")

    sys.addaudithook(audit)
    try:
        module = importlib.import_module("urllib3.util.connection")
        path = Path(module.__file__).resolve()
        raw = path.read_bytes()
        result.update(status="import_completed_with_connections_and_binds_denied",
                      distribution_version=importlib.metadata.version("urllib3"),
                      has_ipv6=module.HAS_IPV6,
                      source={"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
