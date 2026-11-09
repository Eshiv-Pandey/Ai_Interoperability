"""Acquire exact pinned x402 package bytes over public HTTPS, without executing them."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEST = Path(__file__).resolve().parent
WORKSPACE = DEST.parents[3]
SCREEN = DEST.parent / "ap2-x402-dependency-screen-v1"
AUDIT = WORKSPACE / "runs/ap2-dependency-source-review/v1/result.json"
PIN = "125db5526a965d2325459d1a9df2e274a7e42396"
PREFIX = "python/x402_a2a/"
MAX_ENTITY_BYTES = 4 * 1024 * 1024


def digest(kind, body):
    return hashlib.sha1(f"{kind} {len(body)}".encode("ascii") + b"\0" + body).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, sort_keys=True)


if any(path.name != "capture.py" for path in DEST.iterdir()):
    raise SystemExit("This new namespace has already been allocated; do not rerun it.")
old_files = sorted(path for path in SCREEN.iterdir() if path.is_file())
old_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in old_files}
tree_bytes = (SCREEN / "tree.body").read_bytes()
commit_bytes = (SCREEN / "commit.body").read_bytes()
ref_bytes = (SCREEN / "default-ref.body").read_bytes()
review_bytes = AUDIT.read_bytes()
tree, commit, ref, review = [json.loads(body) for body in (tree_bytes, commit_bytes, ref_bytes, review_bytes)]
if not (commit["sha"] == ref["object"]["sha"] == PIN and tree["sha"] == commit["tree"]["sha"] and tree.get("truncated") is False and review["status"] == "verified_bounded_source_receipts_only" and review["source_selection"]["commit"] == PIN and all(row["passed"] is True for row in review["checks"])):
    raise SystemExit("Pinned retained source/audit preconditions are not met.")
audit_bindings = {row["file"]: row["sha256"] for row in review["input_preservation"]}
for name, body in (("tree.body", tree_bytes), ("commit.body", commit_bytes), ("default-ref.body", ref_bytes)):
    relative = (SCREEN / name).relative_to(WORKSPACE).as_posix()
    if audit_bindings.get(relative) != hashlib.sha256(body).hexdigest():
        raise SystemExit("Pinned source bytes differ from the independent review.")
entries = tree["tree"]
selected = [row for row in entries if row["path"].startswith(PREFIX) and row["type"] != "tree"]
package_paths = [row["path"] for row in selected]
if len(package_paths) != 23 or len(set(package_paths)) != len(package_paths) or any(row["type"] != "blob" or row["mode"] != "100644" for row in selected):
    raise SystemExit("Unexpected complete-package selection; no acquisition started.")
root_license = next(row for row in entries if row["path"] == "LICENSE" and row["type"] == "blob")
selected.append(root_license)
for row in selected:
    components = row["path"].split("/")
    if row["path"].startswith("/") or any(component in ("", ".", "..") for component in components):
        raise SystemExit("Invalid source path; no acquisition started.")

plan = {"schema_version": "ap2-x402-package-source-plan/1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "repository": "google-agentic-commerce/a2a-x402", "commit": PIN, "tree": tree["sha"], "package_subdirectory": PREFIX.rstrip("/"), "package_file_count": 23, "package_bytes": sum(row["size"] for row in selected if row["path"].startswith(PREFIX)), "supplementary_source": ["LICENSE"], "selection": selected, "http_attempt_policy": "One bounded GET per selected file; no retries and no overwriting allocations", "concurrency": 4, "timeout_seconds": 30, "scope": "Public pinned source byte acquisition only; no resolution, installation, acquired-source imports, native application or model execution", "retained_screen_inputs": old_hashes, "independent_review": str(AUDIT.relative_to(WORKSPACE)).replace("\\", "/"), "independent_review_sha256": hashlib.sha256(review_bytes).hexdigest()}
write_json(DEST / "plan.json", plan)
for name, body in (("reference-tree.body", tree_bytes), ("reference-commit.body", commit_bytes), ("reference-default-ref.body", ref_bytes), ("independent-source-review.json", review_bytes)):
    with (DEST / name).open("xb") as target:
        target.write(body)
(DEST / "source").mkdir()
(DEST / "receipts").mkdir()


def fetch(index_entry):
    index, entry = index_entry
    path = entry["path"]
    url = "https://raw.githubusercontent.com/google-agentic-commerce/a2a-x402/" + PIN + "/" + quote(path, safe="/.")
    record = {"path": path, "url": url, "expected_git_blob": entry["sha"], "expected_bytes": entry["size"], "mode": entry["mode"], "started_at_utc": datetime.now(timezone.utc).isoformat(), "attempts": 1}
    body = None
    try:
        request = Request(url, headers={"User-Agent": "Ai-Interoperability-source-acquisition/1", "Accept-Encoding": "identity"})
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            record.update({"http_status": response.status, "final_url": response.geturl(), "headers": dict(response.headers.items())})
            body = response.read(MAX_ENTITY_BYTES + 1)
        if len(body) > MAX_ENTITY_BYTES:
            raise ValueError("HTTP entity exceeded the fixed acquisition limit")
        source_path = DEST / "source" / Path(path)
        source_path.parent.mkdir(parents=True, exist_ok=True)
        with source_path.open("xb") as target:
            target.write(body)
        actual_blob = digest("blob", body)
        record.update({"body_file": source_path.relative_to(DEST).as_posix(), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "git_blob": actual_blob})
        record["status"] = "acquired_exact_pinned_blob" if record["http_status"] == 200 and record["final_url"] == url and len(body) == entry["size"] and actual_blob == entry["sha"] else "retained_http_or_identity_failure"
    except Exception as error:
        record.update({"status": "acquisition_error", "error_type": type(error).__name__, "error": str(error)})
        if body is not None and "body_file" not in record:
            failure_path = DEST / "receipts" / f"{index:03d}.failure.body"
            with failure_path.open("xb") as target:
                target.write(body)
            record["failure_body_file"] = failure_path.relative_to(DEST).as_posix()
            record["failure_body_sha256"] = hashlib.sha256(body).hexdigest()
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(DEST / "receipts" / f"{index:03d}.json", record)
    return record


with ThreadPoolExecutor(max_workers=4) as executor:
    records = list(executor.map(fetch, enumerate(selected, 1)))
preservation = [{"file": name, "sha256": before, "after_sha256": hashlib.sha256((SCREEN / name).read_bytes()).hexdigest()} for name, before in old_hashes.items()]
unchanged = all(row["sha256"] == row["after_sha256"] for row in preservation)
success = all(row["status"] == "acquired_exact_pinned_blob" for row in records) and unchanged
manifest = {"schema_version": "ap2-x402-complete-package-source-manifest/1", "status": "complete_selected_package_source" if success else "partial_or_discrepant_source_acquisition", "finished_at_utc": datetime.now(timezone.utc).isoformat(), "repository": "google-agentic-commerce/a2a-x402", "commit": PIN, "tree": tree["sha"], "package_subdirectory": PREFIX.rstrip("/"), "package_file_count": 23, "package_file_bytes": 672591, "supplementary_source": ["LICENSE"], "files": records, "package_file_coverage_complete": success and {row["path"] for row in records if row["path"].startswith(PREFIX)} == set(package_paths), "prior_screen_preservation": preservation, "prior_screen_unchanged": unchanged, "source_package_built": False, "complete_ap2_dependency_lock": False, "environment_installed": False, "acquired_source_imported": False, "native_application_executed": False, "model_requests": 0, "exclusions": ["Repository examples, protocol specs, CI and files outside python/x402_a2a except supplementary root LICENSE are not part of this selected package capture", "Build backend Hatchling, runtime lower-bound dependencies and their transitive closure are external unresolved inputs", "The upstream x402 uv.lock remains a source artifact and is not an AP2 combined lock"], "independent_review_sha256": hashlib.sha256(review_bytes).hexdigest(), "capture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
write_json(DEST / "manifest.json", manifest)
print(json.dumps({"status": manifest["status"], "package_files": manifest["package_file_count"], "total_captured_files": len(records), "package_bytes": manifest["package_file_bytes"], "failed_paths": [row["path"] for row in records if row["status"] != "acquired_exact_pinned_blob"], "prior_screen_unchanged": unchanged}))
