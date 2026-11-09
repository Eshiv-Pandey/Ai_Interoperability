"""Independent retained-source/receipt audit. Standard library; no network/imports of acquired source."""
from __future__ import annotations

import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib


WORKSPACE = Path(__file__).resolve().parents[3]
CAPTURE = WORKSPACE / "docs/research/source-evidence/ap2-x402-dependency-screen-v1"
AP2 = WORKSPACE / "docs/research/source-evidence/ap2-procurement-screen-v1"
SOURCE = AP2 / "source"
PLAN = WORKSPACE / "docs/research/ap2-human-present-dependency-plan-v1.md"
OUT = Path(__file__).resolve().parent / "result.json"
PIN = "125db5526a965d2325459d1a9df2e274a7e42396"
API = "https://api.github.com/repos/google-agentic-commerce/a2a-x402"
checks = []
inputs = {}


def read(path):
    body = path.read_bytes()
    inputs[path] = hashlib.sha256(body).hexdigest()
    return body


def obj(path):
    return json.loads(read(path))


def check(name, passed, detail=None):
    row = {"name": name, "passed": bool(passed)}
    if detail is not None:
        row["detail"] = detail
    checks.append(row)


def git_sha(kind, body):
    envelope = f"{kind} {len(body)}".encode("ascii") + bytes([0])
    return hashlib.sha1(envelope + body).hexdigest()


v2_path = CAPTURE / "source-verification-v2.json"
v2 = obj(v2_path)
check("reviewed_v2_exact_identity", inputs[v2_path] == "a070e92809986420a56c96b4b11cc0a8cc55fb58ef0c3103e4ea2ae882996e56")
check("v2_declares_41_source_checks", len(v2["checks"]) == 41 and all(row["passed"] is True for row in v2["checks"]))
check("v2_has_34_unique_input_bindings", len(v2["input_bindings"]) == 34 and len({row["file"] for row in v2["input_bindings"]}) == 34)
for binding in v2["input_bindings"]:
    path = CAPTURE / binding["file"]
    check("v2_input:" + binding["file"], path.parent == CAPTURE and hashlib.sha256(read(path)).hexdigest() == binding["sha256"])

old_commit = obj(CAPTURE / "commit-identity.json")
old_review = obj(CAPTURE / "source-verification.json")
check("failed_commit_identity_preserved", old_commit["git_commit_sha_matches"] is False and old_commit["expected_git_commit_sha"] == PIN and old_commit["reconstructed_git_commit_sha"] != PIN)
failed_tree_checks = [row["name"] for row in old_review["checks"] if row["passed"] is False]
check("five_original_tree_failures_preserved", old_review["status"] == "failed" and len(failed_tree_checks) == 5 and all(name.startswith("tree_identity:") for name in failed_tree_checks), failed_tree_checks)
check("v2_references_original_failed_review", v2["original_verification"] == "source-verification.json")

capture = obj(CAPTURE / "capture-result.json")
followup = obj(CAPTURE / "followup-result.json")
all_records = capture["records"] + followup["records"]
by_label = {row["label"]: row for row in all_records}
check("capture_records_unique_labels", len(by_label) == len(all_records))
expected_urls = {
    "repository": API,
    "default-ref": API + "/git/ref/heads/main",
    "commit": API + "/git/commits/" + PIN,
    "tree": API + "/git/trees/bd16cd70aa86b4b561027d94c99591e17f0dcf46?recursive=1",
    "pyproject": API + "/contents/python/x402_a2a/pyproject.toml?ref=" + PIN,
    "license": API + "/contents/LICENSE?ref=" + PIN,
    "package-lock": API + "/contents/python/x402_a2a/uv.lock?ref=" + PIN,
    "package-license": API + "/contents/python/x402_a2a/LICENSE?ref=" + PIN,
    "package-readme": API + "/contents/python/x402_a2a/README.md?ref=" + PIN,
}
for label, url in expected_urls.items():
    receipt = obj(CAPTURE / (label + ".receipt.json"))
    body = read(CAPTURE / (label + ".body"))
    check("http_entity:" + label, receipt["status"] == 200 and receipt["label"] == label and receipt["url"] == receipt["final_url"] == url and receipt["body_file"] == label + ".body" and receipt["sha256"] == hashlib.sha256(body).hexdigest() and isinstance(receipt["headers"], dict))
    check("capture_receipt_binding:" + label, by_label[label] == receipt)

repo = obj(CAPTURE / "repository.body")
ref = obj(CAPTURE / "default-ref.body")
commit = obj(CAPTURE / "commit.body")
tree = obj(CAPTURE / "tree.body")
check("repository_identity_and_default_branch", repo["full_name"] == "google-agentic-commerce/a2a-x402" and repo["default_branch"] == "main")
check("default_ref_commit_membership", ref["ref"] == "refs/heads/main" and ref["object"]["type"] == "commit" and ref["object"]["sha"] == commit["sha"] == PIN and commit["url"] == API + "/git/commits/" + PIN)
attestation = commit["verification"]
check("github_signature_attestation_only", attestation["verified"] is True and attestation["reason"] == "valid")
headers, separator, message = attestation["payload"].partition("\n\n")
signature_lines = attestation["signature"].split("\n")
signed_lines = headers.split("\n") + ["gpgsig " + signature_lines[0]] + [" " + line for line in signature_lines[1:]]
signed_commit = ("\n".join(signed_lines) + separator + message).encode("utf-8")
reconstructed_commit = git_sha("commit", signed_commit)
check("independent_signed_commit_reconstruction", separator == "\n\n" and reconstructed_commit == PIN, reconstructed_commit)
check("tree_root_bound_to_commit", tree["sha"] == commit["tree"]["sha"] and tree.get("truncated") is False and tree["url"] == commit["tree"]["url"])
entries = tree["tree"]
entry_map = {entry["path"]: entry for entry in entries}
check("tree_paths_unique_and_relative", len(entry_map) == len(entries) and all(not entry["path"].startswith("/") and all(part not in ("", ".", "..") for part in entry["path"].split("/")) for entry in entries))
directories = [("", tree["sha"])] + [(entry["path"], entry["sha"]) for entry in entries if entry["type"] == "tree"]
for parent, expected in directories:
    children = []
    for entry in entries:
        components = entry["path"].split("/")
        if "/".join(components[:-1]) == parent:
            children.append((components[-1], entry))
    children.sort(key=lambda pair: (pair[0] + ("/" if pair[1]["type"] == "tree" else "")).encode("utf-8"))
    binary = bytearray()
    for name, child in children:
        binary.extend((format(int(child["mode"], 8), "o") + " " + name).encode("utf-8"))
        binary.append(0)
        binary.extend(bytes.fromhex(child["sha"]))
    check("independent_tree_identity:" + (parent or "/"), git_sha("tree", bytes(binary)) == expected)

blob_rows = []
for label in ("pyproject", "license", "package-lock", "package-license", "package-readme"):
    entity = obj(CAPTURE / (label + ".body"))
    decoded = base64.b64decode(entity["content"])
    expected_path = expected_urls[label].split("/contents/", 1)[1].split("?", 1)[0]
    member = entry_map.get(expected_path)
    check("selected_blob_membership:" + label, entity["path"] == expected_path and entity["type"] == "file" and entity["encoding"] == "base64" and member is not None and member["type"] == "blob" and entity["sha"] == member["sha"] == git_sha("blob", decoded) and entity["size"] == len(decoded))
    check("selected_blob_decoding:" + label, read(CAPTURE / (label + ".verified-source")) == decoded)
    blob_rows.append({"label": label, "path": expected_path, "git_blob_sha": entity["sha"], "sha256": hashlib.sha256(decoded).hexdigest()})

ap2_manifest = obj(AP2 / "source-result.json")
ap2_files = {row["path"]: row for row in ap2_manifest["files"]}
ap2 = tomllib.loads(read(SOURCE / "pyproject.toml").decode("utf-8"))
samples = tomllib.loads(read(SOURCE / "code/samples/python/pyproject.toml").decode("utf-8"))
x402 = tomllib.loads(read(CAPTURE / "pyproject.verified-source").decode("utf-8"))
lock = tomllib.loads(read(CAPTURE / "package-lock.verified-source").decode("utf-8"))
check("ap2_source_commit", ap2_manifest["commit"] == "e1ea56db72a6385bce3e5c1112b3a56ce60acb43")
for relative in ("pyproject.toml", "code/samples/python/pyproject.toml"):
    check("ap2_original_packaging_identity:" + relative, inputs[SOURCE / relative] == ap2_files[relative]["sha256"])
check("ap2_original_root_build", ap2["project"]["name"] == "ap2" and ap2["project"]["version"] == "0.1" and ap2["project"]["requires-python"] == ">=3.11" and ap2["build-system"] == {"requires": ["setuptools>=61.0"], "build-backend": "setuptools.build_meta"} and ap2["tool"]["setuptools"]["packages"]["find"]["where"] == ["code/sdk/python"] and ap2["tool"]["uv"]["workspace"]["members"] == ["code/samples/python"])
floating_x402 = "x402-a2a @ git+https://github.com/google-agentic-commerce/a2a-x402.git#subdirectory=python/x402_a2a"
check("original_sample_dependency_and_workspace", samples["project"]["name"] == "ap2-samples" and samples["project"]["version"] == "0.1" and samples["project"]["requires-python"] == ">=3.11" and floating_x402 in samples["project"]["dependencies"] and samples["tool"]["uv"]["sources"]["ap2"] == {"workspace": True} and samples["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"])
check("x402_original_package_build", x402["project"]["name"] == "x402-a2a" and x402["project"]["version"] == "0.1.0" and x402["project"]["requires-python"] == ">=3.10" and x402["build-system"] == {"requires": ["hatchling"], "build-backend": "hatchling.build"} and x402["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/x402_a2a"])
check("x402_runtime_lower_bounds", x402["project"]["dependencies"] == ["a2a-sdk>=0.1.0", "x402>=0.2.0", "eth-account>=0.13.7", "httpx>=0.28.1", "pydantic>=2.0.0"])
selected_lock = {row["name"]: row["version"] for row in lock["package"] if row["name"] in {"a2a-sdk", "pydantic", "x402-a2a"}}
check("x402_lock_mismatch_not_ap2_lock", selected_lock == {"a2a-sdk": "0.3.1", "pydantic": "2.11.7", "x402-a2a": "1.0.0"} and "a2a-sdk==0.3.24" in samples["project"]["dependencies"] and "pydantic==2.12.5" in ap2["project"]["dependencies"] and selected_lock["x402-a2a"] != x402["project"]["version"], selected_lock)

hp_dirs = [SOURCE / "code/samples/python/src/common"] + [SOURCE / "code/samples/python/src/roles" / role for role in ("merchant_agent", "merchant_payment_processor_agent", "credentials_provider_agent", "shopping_agent")]
hp_paths = sorted(path for directory in hp_dirs for path in directory.rglob("*.py"))
direct_x402 = []
for path in hp_paths:
    body = read(path)
    relative = path.relative_to(SOURCE).as_posix()
    check("hp_source_identity:" + relative, hashlib.sha256(body).hexdigest() == ap2_files[relative]["sha256"])
    imports = []
    for node in ast.walk(ast.parse(body, filename=relative)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imports.append(node.module or "")
    if any(name.split(".", 1)[0] in {"x402", "x402_a2a"} for name in imports):
        direct_x402.append(relative)
check("bounded_40_hp_files_no_direct_external_x402_import", len(hp_paths) == 40 and not direct_x402)
plan = read(PLAN).decode("utf-8")
check("plan_discloses_derived_pin_not_original_lock", PIN in plan and "not an AP2-authored historical lock" in plan and "No environment was" in plan and "not the complete x402 package" in plan and "not an AP2 workspace lock" in plan)
check("plan_keeps_original_closure_and_runtime_gates", "deleting the" in plan and "declared x402 requirement" in plan and "1 GiB physical/2 GiB commit" in plan and "complete combined runtime closure" in plan)
unchanged = []
for path, before_hash in sorted(inputs.items(), key=lambda pair: str(pair[0])):
    after_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    row = {"file": path.relative_to(WORKSPACE).as_posix(), "sha256": before_hash, "after_sha256": after_hash, "unchanged": before_hash == after_hash}
    unchanged.append(row)
check("all_read_input_bytes_preserved", all(row["unchanged"] for row in unchanged))
result = {"schema_version": "ap2-dependency-independent-source-review/1", "status": "verified_bounded_source_receipts_only" if all(row["passed"] for row in checks) else "failed_bounded_review", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "reviewer": "separate_ai_agent_ap2_reassessment", "checks": checks, "source_selection": {"repository": "google-agentic-commerce/a2a-x402", "ref": "refs/heads/main", "commit": PIN, "reconstructed_commit": reconstructed_commit, "package_subdirectory": "python/x402_a2a"}, "selected_blobs": blob_rows, "original_failed_tree_checks": failed_tree_checks, "packaging": {"ap2": ap2["project"], "samples": samples["project"], "x402": x402["project"], "x402_lock_mismatch": selected_lock}, "hp_static_files": len(hp_paths), "direct_external_x402_import_files": direct_x402, "input_preservation": unchanged, "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "claim_limits": ["Retained public HTTPS receipt/Git source identity and packaging selection only", "GitHub signature attestation not independent signing-key cryptographic verification", "Selected packaging blobs are not a complete x402 package or AP2 environment", "No complete AP2 dependency lock, dependency resolution, wheel build, installation, source import, native workflow or model request", "No resource eligibility, domain qualification, full-task grade, novelty or checkpoint credit"]}
with OUT.open("x", encoding="utf-8") as target:
    json.dump(result, target, indent=2, sort_keys=True)
print(json.dumps({"status": result["status"], "checks": len(checks), "failed": [row["name"] for row in checks if not row["passed"]], "preserved_inputs": len(unchanged), "result": str(OUT)}))
