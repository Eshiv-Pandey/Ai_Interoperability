"""Correct only the dated tree verifier's dotted-path normalization error."""
from __future__ import annotations
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
original = json.loads((ROOT / "source-verification.json").read_bytes())
tree = json.loads((ROOT / "tree.body").read_bytes())
commit = json.loads((ROOT / "commit.body").read_bytes())
entries = tree["tree"]
checks = [item for item in original["checks"] if not item["name"].startswith("tree_identity:")]
for parent, expected in [("", commit["tree"]["sha"])] + [(entry["path"], entry["sha"]) for entry in entries if entry["type"] == "tree"]:
    children = []
    for entry in entries:
        actual_parent = str(pathlib.PurePosixPath(entry["path"]).parent)
        if actual_parent == ".":
            actual_parent = ""
        if actual_parent == parent:
            children.append(entry)
    children.sort(key=lambda entry: (pathlib.PurePosixPath(entry["path"]).name + ("/" if entry["type"] == "tree" else "")).encode())
    body = b"".join((entry["mode"].lstrip("0") + " " + pathlib.PurePosixPath(entry["path"]).name).encode() + b"\0" + bytes.fromhex(entry["sha"]) for entry in children)
    actual = hashlib.sha1(b"tree " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()
    checks.append({"name": "tree_identity:" + (parent or "/"), "passed": actual == expected, "expected_sha": expected, "actual_sha": actual})
bindings = []
for file in sorted(ROOT.iterdir()):
    if file.is_file():
        bindings.append({"file": file.name, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
result = {"status": "verified_source_only" if all(item["passed"] for item in checks) else "failed", "checks": checks, "input_bindings": bindings, "commit_sha": commit["sha"], "original_verification": "source-verification.json", "correction": "Normalize only the root parent represented as a single dot. Preserve literal dots in .github and version directory names.", "scope": original["scope"]}
with (ROOT / "source-verification-v2.json").open("x", encoding="utf-8") as target:
    json.dump(result, target, indent=2, sort_keys=True)
print(json.dumps({"status": result["status"], "checks": len(checks), "failed": [item["name"] for item in checks if not item["passed"]], "bound_inputs": len(bindings)}))
