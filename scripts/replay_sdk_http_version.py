"""Archive and replay HTTP control evidence; never rerun services or the SDK."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


WORKER = r'''
import copy, importlib.util, json, pathlib, sys
root = pathlib.Path(sys.argv[1]); report_path = sys.argv[2]
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, root / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
current = load("scripts/check_sdk_http_version.py", "corrected_checker")
original = current.decode((root / report_path).read_text(encoding="utf-8"))
entry = next(e for e in original["source_hashes"] if e["path"] == "scripts/check_sdk_http_version.py")
frozen = load(entry["snapshot"], "pre_execution_checker")
try:
    frozen.check_archive(root, report_path)
except ValueError as error:
    frozen_failure = str(error)
else:
    raise ValueError("Original checker failure did not reproduce")
if frozen_failure != "Unexpected HTTP status":
    raise ValueError("Unexpected frozen checker failure")
result = current.check_archive(root, report_path)
def reencode(entity):
    import base64, hashlib
    raw = json.dumps(entity["json"], separators=(",", ":")).encode()
    entity.update(raw=raw.decode(), base64=base64.b64encode(raw).decode(), bytes=len(raw),
                  sha256=hashlib.sha256(raw).hexdigest())
def wrong_answer_binding(r):
    request = r["cases"][6]["request"]
    request["json"]["params"]["message"]["referenceTaskIds"] = ["different-task"]
    reencode(request)
    r["ingress"][6]["body"] = {k:request[k] for k in ("raw", "base64", "bytes", "sha256")}
def wrong_artifact(r):
    response = r["cases"][2]["response"]
    response["json"]["result"]["task"]["artifacts"][0]["parts"][0]["text"] = "[]"
    reencode(response)
def wrong_completed_context(r):
    response = r["cases"][7]["response"]
    response["json"]["result"]["contextId"] = "different-context"
    reencode(response)
def wrong_error_status(r):
    r["cases"][0]["response"]["status"] = 200
    r["ingress"][0]["response_status"] = 200
mutations = [
    ("wrong-public-answer-reference", wrong_answer_binding),
    ("wrong-initial-source-artifact", wrong_artifact),
    ("completed-different-context", wrong_completed_context),
    ("wrong-but-consistent-http-error-status", wrong_error_status),
    ("missing-case", lambda r:r["cases"].pop()),
    ("reordered-cases", lambda r:r["cases"].reverse()),
    ("wrong-request-cost", lambda r:r["costs"].update(http_requests=0)),
    ("server-left-open", lambda r:r["cleanup"].update(server_listening=True)),
    ("invented-custom-default", lambda r:r.update(default_context_builder=False)),
    ("wrong-server-header", lambda r:r["ingress"][0]["headers"].update({"a2a-version":"1.0"})),
    ("different-private-ingress", lambda r:r["ingress"][0]["body"].update(raw="{}")),
    ("wrong-frozen-case-input", lambda r:r["case_plan"][4].update(version_query=None)),
    ("network-boundary-changed", lambda r:r.update(remote_network_requests=1)),
]
checks=[]
for name, mutate in mutations:
    candidate=copy.deepcopy(original);mutate(candidate)
    try:current.check_semantics(candidate)
    except (ValueError,KeyError,TypeError,IndexError) as error:
        checks.append({"name":name,"rejected":True,"reason":str(error)})
    else:checks.append({"name":name,"rejected":False})
result.update(frozen_checker_failure_reproduced=frozen_failure, mutation_checks=checks,
              mutation_checks_passed=all(e["rejected"] for e in checks), sdk_imported=False,
              service_requests=0, model_calls=0)
print(json.dumps(result));sys.exit(0 if result["mutation_checks_passed"] else 1)
'''


def sha(filename):
    return hashlib.sha256(filename.read_bytes()).hexdigest()


def inventory(root):
    return [{"path": p.relative_to(root).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size}
            for p in sorted(root.rglob("*")) if p.is_file()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = (root / args.report).resolve()
    output = (root / args.output).resolve()
    if not report.is_relative_to(root) or not output.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    if output.exists():
        raise FileExistsError(output)
    archive = output.with_suffix(".sources")
    archive.mkdir(parents=True, exist_ok=False)
    shutil.copytree(report.parent, archive / report.parent.relative_to(root))
    (archive / "scripts").mkdir()
    for name in ("check_sdk_http_version.py", "replay_sdk_http_version.py"):
        shutil.copyfile(root / "scripts" / name, archive / "scripts" / name)
    for name in ("check-v1.failed.json", "check-v1.1.json"):
        shutil.copyfile(root / "runs/sdk-http-control" / name, archive / "runs/sdk-http-control" / name)
    before = inventory(archive)
    with output.with_suffix(".manifest.json").open("x", encoding="utf-8") as stream:
        json.dump({"files": before, "report_sha256": sha(report),
                   "corrected_checker_sha256": sha(root / "scripts/check_sdk_http_version.py")}, stream, indent=2)
        stream.write("\n")
    worker = subprocess.run([sys.executable, "-I", "-B", "-c", WORKER, str(archive), args.report],
                            cwd=archive, capture_output=True, text=True, timeout=60)
    after = inventory(archive)
    result = json.loads(worker.stdout) if worker.returncode == 0 else None
    checked = {"valid": worker.returncode == 0 and before == after,
               "checked_at": datetime.now(timezone.utc).isoformat(), "archive_files": len(before),
               "archive_unchanged": before == after, "worker_exit_code": worker.returncode,
               "worker_stderr": worker.stderr, "worker_stdout": worker.stdout, "result": result,
               "driver_sha256": sha(Path(__file__)),
               "claim_limit": "Same retained HTTP controls and checker correction; no new service execution or human review"}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(checked, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"valid": checked["valid"], "archive_files": len(before),
                      "mutations_rejected": len(result["mutation_checks"]) if result else None,
                      "frozen_checker_failure_reproduced": result["frozen_checker_failure_reproduced"] if result else None}))
    return int(not checked["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
