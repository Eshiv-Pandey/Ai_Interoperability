"""Fetch once the report-frozen AP2 runtime/backend wheels and verify bytes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runs/ap2-environment-preparation/wheel-store-v1"
LOCKS = {
    "runtime": ("runs/ap2-dependency-resolution/indexed-wheel-lock-v1/manifest.json", "d1ed29b81ae3dfd6bc4d89d95d2130e88c0e287a320c77032cbf80888abde106", 184),
    "backends": ("runs/ap2-dependency-resolution/build-backend-wheel-lock-v1/manifest.json", "d304cf5a3c8671bccd52fa3c4d5a7b357792aa25c5973a2ae8c2f24946da4078", 7),
}
MAX_BYTES = 512 * 1024 * 1024


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def publish(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def fetch(row):
    filename = row["wheel_filename"]
    target = OUTPUT / "wheels" / filename
    record = {"name": row["normalized_name"], "version": row["version"], "wheel_filename": filename,
              "url": row["wheel_url"], "expected_sha256": row["sha256"], "scopes": row["scopes"],
              "started_at_utc": utc(), "attempts": 1, "bytes": 0, "http_status": None,
              "final_url": None, "response_headers": [], "error": None, "verified": False}
    publish(OUTPUT / "requests" / f"{filename}.request.json", record)
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(row["wheel_url"], headers={"User-Agent": "AiInteroperability-FrozenWheelCapture/1", "Accept-Encoding": "identity"})
        with urllib.request.urlopen(request, timeout=60) as response:
            record.update({"http_status": response.status, "final_url": response.url, "response_headers": list(response.headers.items())})
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > MAX_BYTES:
                raise ValueError("Frozen wheel exceeds per-artifact size limit")
            with target.open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    record["bytes"] += len(chunk)
                    if record["bytes"] > MAX_BYTES:
                        raise ValueError("Frozen wheel exceeds per-artifact size limit")
                    digest.update(chunk)
                    stream.write(chunk)
            record["sha256"] = digest.hexdigest()
            record["verified"] = response.status == 200 and response.url == row["wheel_url"] and record["sha256"] == row["sha256"]
    except (urllib.error.URLError, OSError, ValueError) as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
    record["finished_at_utc"] = utc()
    record["retained_wheel_file"] = target.relative_to(OUTPUT).as_posix() if target.exists() else None
    publish(OUTPUT / "requests" / f"{filename}.response.json", record)
    return record


def main():
    bodies, selections = {}, {}
    for scope, (path, expected, count) in LOCKS.items():
        body = (ROOT / path).read_bytes()
        if sha(body) != expected:
            raise RuntimeError("Frozen report-derived artifact lock changed")
        bodies[scope] = body
        manifest = json.loads(body)
        if manifest["schema_version"] != "ap2-report-derived-wheel-artifact-lock/1" or manifest["status"] != "frozen_report_derived_indexed_artifacts" or manifest["distribution_count"] != count or len(manifest["wheels"]) != count:
            raise RuntimeError("Incomplete frozen wheel selection")
        for row in manifest["wheels"]:
            filename, url = row["wheel_filename"], row["wheel_url"]
            parsed = urlsplit(url)
            if Path(filename).name != filename or "/" in filename or "\\" in filename or ":" in filename or not filename.endswith(".whl") or any(c.isspace() for c in filename):
                raise RuntimeError("Invalid immutable wheel filename")
            if parsed.scheme != "https" or parsed.netloc != "files.pythonhosted.org" or parsed.query or parsed.fragment:
                raise RuntimeError("Unexpected frozen wheel origin")
            if row["normalized_name"] in {"ap2", "ap2-samples", "x402-a2a"}:
                raise RuntimeError("A source-bound package is shadowed by an indexed wheel")
            if filename in selections:
                previous = selections[filename]
                if any(previous[key] != row[key] for key in ("wheel_url", "sha256", "normalized_name", "version")):
                    raise RuntimeError("Conflicting artifact identities across runtime/backend scopes")
                previous["scopes"].append(scope)
            else:
                selections[filename] = {**row, "scopes": [scope]}
    if len(selections) != 189:
        raise RuntimeError("Unexpected immutable union membership")
    OUTPUT.mkdir(exist_ok=False)
    for name in ("wheels", "requests", "input-snapshots"):
        (OUTPUT / name).mkdir()
    for scope, body in bodies.items():
        (OUTPUT / "input-snapshots" / f"{scope}.json").write_bytes(body)
    driver = Path(__file__).read_bytes()
    (OUTPUT / "capture-driver.py").write_bytes(driver)
    publish(OUTPUT / "plan.json", {"schema_version": "ap2-frozen-wheel-fetch-plan/1", "created_at_utc": utc(),
            "locks": LOCKS, "driver_sha256": sha(driver), "unique_artifacts": 189,
            "maximum_parallel_requests": 4, "maximum_attempts_per_artifact": 1,
            "timeout_seconds_per_socket_operation": 60, "maximum_bytes_per_artifact": MAX_BYTES,
            "source_built": False, "environment_installed": False, "resolver_executed": False})
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, selections.values()))
    unchanged = {scope: sha((ROOT / path).read_bytes()) == expected for scope, (path, expected, _) in LOCKS.items()}
    success = all(row["verified"] for row in records) and all(unchanged.values())
    manifest = {"schema_version": "ap2-frozen-wheel-byte-capture/1", "finished_at_utc": utc(),
                "status": "all_frozen_wheel_bytes_verified" if success else "frozen_wheel_capture_incomplete",
                "locks": LOCKS, "inputs_unchanged": unchanged, "driver_sha256": sha(driver),
                "artifacts": records, "unique_artifacts": len(records), "network_requests": len(records),
                "verified_artifacts": sum(row["verified"] for row in records),
                "total_bytes": sum(row["bytes"] for row in records), "resolver_executed": False,
                "source_built": False, "environment_installed": False, "original_application_imported": False,
                "native_application_executed": False, "model_requests": 0,
                "claim_limit": "Exact indexed runtime/backend wheel bytes only; three source wheels, dynamic backend hooks, installed metadata and original runtime compatibility remain open."}
    publish(OUTPUT / "manifest.json", manifest)
    print(json.dumps({key: manifest[key] for key in ("status", "unique_artifacts", "verified_artifacts", "total_bytes", "inputs_unchanged")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
