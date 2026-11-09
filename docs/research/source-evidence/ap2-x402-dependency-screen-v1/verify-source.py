"""Verify retained source identities; no acquired module is imported."""
from __future__ import annotations
import ast
import base64
import hashlib
import json
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT.parent / "ap2-procurement-screen-v1" / "source"
checks = []
def check(name, value):
    checks.append({"name": name, "passed": bool(value)})

def git_digest(kind, body):
    return hashlib.sha1(kind.encode() + b" " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()

commit = json.loads((ROOT / "commit.body").read_bytes())
ref = json.loads((ROOT / "default-ref.body").read_bytes())
tree = json.loads((ROOT / "tree.body").read_bytes())
check("default_ref_matches_commit", ref["object"]["sha"] == commit["sha"])
check("github_signature_attestation_valid", commit["verification"]["verified"] and commit["verification"]["reason"] == "valid")
headers, message = commit["verification"]["payload"].split("\n\n", 1)
signed = (headers + "\ngpgsig " + commit["verification"]["signature"].replace("\n", "\n ") + "\n\n" + message).encode("utf-8")
actual_sha = git_digest("commit", signed)
check("corrected_git_commit_identity", actual_sha == commit["sha"])
check("recursive_tree_not_truncated", tree.get("truncated") is False)
entries = tree["tree"]
for parent, expected in [("", commit["tree"]["sha"])] + [(entry["path"], entry["sha"]) for entry in entries if entry["type"] == "tree"]:
    children = [entry for entry in entries if str(pathlib.PurePosixPath(entry["path"]).parent).replace(".", "", 1) == parent]
    children.sort(key=lambda entry: (pathlib.PurePosixPath(entry["path"]).name + ("/" if entry["type"] == "tree" else "")).encode())
    body = b"".join((entry["mode"].lstrip("0") + " " + pathlib.PurePosixPath(entry["path"]).name).encode() + b"\0" + bytes.fromhex(entry["sha"]) for entry in children)
    check("tree_identity:" + (parent or "/"), git_digest("tree", body) == expected)

blobs = []
for label in ("pyproject", "license", "package-lock", "package-license", "package-readme"):
    item = json.loads((ROOT / (label + ".body")).read_bytes())
    decoded = base64.b64decode(item["content"])
    check("git_blob_identity:" + label, git_digest("blob", decoded) == item["sha"])
    check("git_tree_membership:" + label, any(entry["path"] == item["path"] and entry["sha"] == item["sha"] for entry in entries))
    file = label + ".verified-source"
    with (ROOT / file).open("xb") as target:
        target.write(decoded)
    blobs.append({"label": label, "file": file, "path": item["path"], "git_blob_sha": item["sha"], "sha256": hashlib.sha256(decoded).hexdigest()})

import_records = []
selected = [SOURCE / "code/samples/python/src/common"] + [SOURCE / "code/samples/python/src/roles" / name for name in ("merchant_agent", "merchant_payment_processor_agent", "credentials_provider_agent", "shopping_agent")]
for directory in selected:
    for file in sorted(directory.rglob("*.py")):
        body = file.read_bytes()
        syntax = ast.parse(body, filename=str(file))
        imports = []
        for node in ast.walk(syntax):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        import_records.append({"file": str(file.relative_to(SOURCE)).replace("\\", "/"), "sha256": hashlib.sha256(body).hexdigest(), "imports": imports})
direct_x402 = [record["file"] for record in import_records if any(name == "x402" or name.startswith("x402.") or name == "x402_a2a" or name.startswith("x402_a2a.") for name in record["imports"])]
check("no_direct_external_x402_import_in_inspected_hp_common", not direct_x402)
ap2 = tomllib.loads((SOURCE / "pyproject.toml").read_text())
samples = tomllib.loads((SOURCE / "code/samples/python/pyproject.toml").read_text())
x402 = tomllib.loads((ROOT / "pyproject.verified-source").read_text())
lock = tomllib.loads((ROOT / "package-lock.verified-source").read_text())
summary = {
    "status": "verified_source_only" if all(item["passed"] for item in checks) else "failed",
    "commit_sha": commit["sha"], "corrected_reconstructed_commit_sha": actual_sha,
    "prior_failed_reconstruction": "commit-identity.json", "checks": checks,
    "blobs": blobs, "hp_static_import_records": import_records, "direct_x402_import_files": direct_x402,
    "packaging": {"ap2": ap2["project"], "samples": samples["project"], "x402": x402["project"], "x402_lock_selected": {package["name"]: package["version"] for package in lock["package"] if package["name"] in {"x402-a2a", "x402", "a2a-sdk", "pydantic", "httpx", "eth-account", "pytest"}}},
    "scope": "Git identity/tree/blob and static source inspection; no independent signing-key cryptographic verification, installer/solver/runtime imports, native workflow or model requests"
}
with (ROOT / "source-verification.json").open("x", encoding="utf-8") as target:
    json.dump(summary, target, indent=2, sort_keys=True)
print(json.dumps({"status": summary["status"], "checks": len(checks), "failed": [item["name"] for item in checks if not item["passed"]], "hp_python_files": len(import_records), "commit_sha": commit["sha"]}))
