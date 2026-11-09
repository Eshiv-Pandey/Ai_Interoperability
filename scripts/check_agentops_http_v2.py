"""Unchanged HTTP/effect semantics plus the versioned socket observer check."""
import argparse
import hashlib
import json
from pathlib import Path

import check_agentops_http_v1 as previous
from check_agentops_socket_policy_v1 import check_policy


def check(run, seed):
    result = previous.check(run, seed)
    service = previous.strict_json((run / "service-result.json").read_bytes())
    previous.require(service.get("observer_version") == 2, "HTTP socket observer version")
    plan = previous.strict_json((run / "plan.json").read_bytes())
    previous.require(plan.get("controller_version") == "agentops-http-control/5", "HTTP controller version")
    policy = check_policy(service["socket_policy"], listener_port=plan["port"])
    previous.require(service["network_errors"] == service["socket_policy"]["unexpected"], "HTTP network record binding")
    return dict(result, socket_policy=policy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Retain existing check")
    report = {"schema_version": "agentops-http-check/2", "status": "failed"}
    try:
        report.update(check(args.run, previous.seed_snapshot(previous.ROOT / "external/agentops-c806b7f1/agents/data/incidents.db")))
        report["inputs"] = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                            for path in sorted(args.run.iterdir()) if path.is_file()]
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "inputs"}))
    raise SystemExit(0 if report["status"] == "passed" else 1)
