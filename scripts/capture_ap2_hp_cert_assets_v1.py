"""Capture the two original public HP certificate assets at the AP2 pin."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "docs/research/source-evidence/ap2-procurement-screen-v1/tree-response.json"
TREE_SHA256 = "2561c5c884c5f020f479a9138c297cd8b61adc7a1278f3c4259b638fc85c11f5"
PIN = "e1ea56db72a6385bce3e5c1112b3a56ce60acb43"
OUTPUT = ROOT / "docs/research/source-evidence/ap2-hp-cert-assets-v1"
ASSETS = {
    "code/samples/certs/ds_cert_sdjwt.pem": ("b2b717529196fc44f1191b1aeedec64822505b3d", 1066),
    "code/samples/certs/issuer_cert_sdjwt.pem": ("dd1e7ba01972cf3ca5c566e4572294606d2992b4", 1005),
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write("\n")


def main():
    raw_tree = TREE.read_bytes()
    if sha(raw_tree) != TREE_SHA256:
        raise RuntimeError("Pinned source tree input changed")
    tree = json.loads(raw_tree)
    if tree["sha"] != "948843cae3e6423e744a556fe0967bf395aa2ac5" or tree["truncated"] is not False:
        raise RuntimeError("Complete selected AP2 tree required")
    entries = {row["path"]: row for row in tree["tree"]}
    for name, (blob, size) in ASSETS.items():
        entry = entries[name]
        if (entry["type"], entry["mode"], entry["sha"], entry["size"]) != ("blob", "100644", blob, size):
            raise RuntimeError("Original certificate blob identity differs")
    OUTPUT.mkdir(exist_ok=False)
    (OUTPUT / "source-tree.json").write_bytes(raw_tree)
    driver = Path(__file__).read_bytes()
    (OUTPUT / "capture-driver.py").write_bytes(driver)
    write_json(OUTPUT / "plan.json", {"schema_version": "ap2-hp-public-cert-capture-plan/1",
               "created_at_utc": utc(), "commit": PIN, "tree_file": str(TREE), "tree_sha256": TREE_SHA256,
               "driver_sha256": sha(driver), "assets": ASSETS, "max_attempts_per_asset": 1,
               "timeout_seconds_per_asset": 30, "original_source_imported": False})
    records = []
    for index, (name, (blob, size)) in enumerate(ASSETS.items(), 1):
        url = f"https://raw.githubusercontent.com/google-agentic-commerce/AP2/{PIN}/{name}"
        record = {"source_path": name, "request_url": url, "started_at_utc": utc(), "attempts": 1}
        write_json(OUTPUT / f"request-{index}.json", record)
        entity, status, final_url, headers, error = b"", None, None, [], None
        request = urllib.request.Request(url, headers={"User-Agent": "AiInteroperability-SourceCapture/1", "Accept-Encoding": "identity"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                entity, status, final_url, headers = response.read(), response.status, response.url, list(response.headers.items())
        except urllib.error.HTTPError as exc:
            entity, status, final_url, headers = exc.read(), exc.code, exc.url, list(exc.headers.items())
            error = {"type": type(exc).__name__, "message": str(exc)}
        except (urllib.error.URLError, OSError) as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
        entity_path = OUTPUT / f"response-{index}.bin"
        entity_path.write_bytes(entity)
        actual_blob = hashlib.sha1(f"blob {len(entity)}\0".encode("ascii") + entity).hexdigest()
        verified = status == 200 and final_url == url and len(entity) == size and actual_blob == blob
        record.update({"finished_at_utc": utc(), "http_status": status, "final_url": final_url,
                       "response_headers": headers, "error": error, "bytes": len(entity), "sha256": sha(entity),
                       "expected_git_blob": blob, "actual_git_blob": actual_blob, "verified": verified,
                       "response_entity": entity_path.name})
        if verified:
            source = OUTPUT / "source" / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(entity)
            record["source_copy"] = source.relative_to(OUTPUT).as_posix()
        write_json(OUTPUT / f"response-{index}.json", record)
        records.append(record)
    unchanged = sha(TREE.read_bytes()) == TREE_SHA256
    success = all(row["verified"] for row in records) and unchanged
    manifest = {"schema_version": "ap2-hp-public-cert-capture/1", "commit": PIN,
                "status": "both_pinned_public_certificate_assets_captured" if success else "capture_incomplete",
                "finished_at_utc": utc(), "source_tree_sha256": TREE_SHA256, "source_tree_unchanged": unchanged,
                "driver_sha256": sha(driver), "assets": records, "network_requests": 2,
                "original_source_imported": False, "source_built": False, "environment_installed": False,
                "native_application_executed": False, "model_requests": 0,
                "claim_limit": "Public original asset identity only; no certificate parse, application import or native qualification."}
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "assets_verified": sum(row["verified"] for row in records), "source_tree_unchanged": unchanged}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
