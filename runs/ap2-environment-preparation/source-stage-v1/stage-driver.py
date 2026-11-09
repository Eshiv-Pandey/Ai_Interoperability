"""Create pristine original AP2/x402 build and HP runtime source trees."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runs/ap2-environment-preparation/source-stage-v1"
INPUTS = {
    "ap2": ("docs/research/source-evidence/ap2-procurement-screen-v1/source-result.json", "ce0ffdd5503fddfe78ccb13d9c88e673ca2fdc3227e4ae460d3da10b2dc9406c"),
    "tree": ("docs/research/source-evidence/ap2-procurement-screen-v1/tree-response.json", "2561c5c884c5f020f479a9138c297cd8b61adc7a1278f3c4259b638fc85c11f5"),
    "certs": ("docs/research/source-evidence/ap2-hp-cert-assets-v1/manifest.json", "ee7016f043e5334bfd08dc65cc61cda503d233b9c455382e4f055cf6c970f105"),
    "x402": ("docs/research/source-evidence/ap2-x402-package-v1/manifest.json", "74db7661df834b7d05371d84aa4a6f0e6d9d243f344204923cef65e15b449d07"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or ".." in path.parts or ":" in value or "\\" in value:
        raise RuntimeError("Invalid source-relative path")
    return Path(*path.parts)


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def main():
    bodies = {key: (ROOT / path).read_bytes() for key, (path, expected) in INPUTS.items()}
    if any(sha(bodies[key]) != expected for key, (_, expected) in INPUTS.items()):
        raise RuntimeError("Selected immutable source receipt changed")
    docs = {key: json.loads(body) for key, body in bodies.items()}
    original, certs, x402, tree = (docs[key] for key in ("ap2", "certs", "x402", "tree"))
    if original["commit"] != "e1ea56db72a6385bce3e5c1112b3a56ce60acb43" or original["status"] != "acquired" or original["acquired_files"] != 134:
        raise RuntimeError("Original AP2 source receipt incomplete")
    if tree["sha"] != "948843cae3e6423e744a556fe0967bf395aa2ac5" or tree["truncated"] is not False:
        raise RuntimeError("Complete selected AP2 tree required")
    tree_rows = {row["path"]: row for row in tree["tree"] if row["type"] == "blob"}
    expected_ap2 = {name for name in tree_rows if name in {"pyproject.toml", "README.md", "LICENSE"}
                    or name.startswith("code/sdk/python/") or name.startswith("code/samples/python/")}
    if {row["path"] for row in original["files"]} != expected_ap2 or len(expected_ap2) != 134:
        raise RuntimeError("AP2 selected build inputs differ from complete pinned subtree")
    expected_certs = {"code/samples/certs/ds_cert_sdjwt.pem", "code/samples/certs/issuer_cert_sdjwt.pem"}
    if certs["commit"] != original["commit"] or certs["status"] != "both_pinned_public_certificate_assets_captured" or {row["source_path"] for row in certs["assets"]} != expected_certs:
        raise RuntimeError("Exact supplementary original certificate assets required")
    if x402["commit"] != "125db5526a965d2325459d1a9df2e274a7e42396" or x402["package_file_count"] != 23 or x402["package_file_coverage_complete"] is not True or len(x402["files"]) != 24:
        raise RuntimeError("Complete pinned x402 package and root license required")
    sources = []
    for row in original["files"]:
        sources.append(("ap2", row["path"], ROOT / Path(INPUTS["ap2"][0]).parent / "source" / relative(row["path"]), row["bytes"], row["sha256"], row["expected_git_blob"]))
    for row in certs["assets"]:
        if row["verified"] is not True:
            raise RuntimeError("Certificate identity not verified")
        sources.append(("ap2", row["source_path"], ROOT / Path(INPUTS["certs"][0]).parent / relative(row["source_copy"]), row["bytes"], row["sha256"], row["expected_git_blob"]))
    for row in x402["files"]:
        body_file = row["body_file"]
        if not body_file.startswith("source/"):
            raise RuntimeError("x402 body outside retained source tree")
        sources.append(("a2a-x402", body_file.removeprefix("source/"), ROOT / Path(INPUTS["x402"][0]).parent / relative(body_file), row["bytes"], row["sha256"], row["expected_git_blob"]))
    payloads, identities = [], set()
    for project, name, origin, size, expected, blob in sources:
        relative(name)
        if (project, name) in identities or origin.is_symlink():
            raise RuntimeError("Duplicate or linked original source file")
        identities.add((project, name))
        data = origin.read_bytes()
        actual_blob = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
        if (len(data), sha(data), actual_blob) != (size, expected, blob):
            raise RuntimeError(f"Original source bytes changed: {name}")
        if project == "ap2" and tree_rows[name]["sha"] != blob:
            raise RuntimeError("AP2 original file differs from pinned tree")
        payloads.append((project, name, origin, data, expected, blob))
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=False)
    snapshots = OUTPUT / "input-snapshots"
    snapshots.mkdir()
    for key, body in bodies.items():
        (snapshots / f"{key}.json").write_bytes(body)
    driver = Path(__file__).read_bytes()
    (OUTPUT / "stage-driver.py").write_bytes(driver)
    records = []
    for project, name, origin, data, expected, blob in payloads:
        target = OUTPUT / project / relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append({"project": project, "path": name, "origin": origin.relative_to(ROOT).as_posix(),
                        "bytes": len(data), "sha256": expected, "git_blob": blob,
                        "staged_copy_matches": sha(target.read_bytes()) == expected,
                        "original_unchanged": sha(origin.read_bytes()) == expected})
    inputs_unchanged = {key: sha((ROOT / path).read_bytes()) == expected for key, (path, expected) in INPUTS.items()}
    success = all(inputs_unchanged.values()) and all(row["original_unchanged"] and row["staged_copy_matches"] for row in records)
    manifest = {"schema_version": "ap2-hp-pristine-source-stage/1", "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "pristine_source_stage_created" if success else "source_stage_not_established",
                "inputs": INPUTS, "inputs_unchanged": inputs_unchanged, "driver_sha256": sha(driver),
                "ap2_commit": original["commit"], "x402_commit": x402["commit"], "files": records,
                "ap2_files": sum(row["project"] == "ap2" for row in records),
                "x402_files": sum(row["project"] == "a2a-x402" for row in records),
                "build_roots": {"ap2": "ap2", "ap2-samples": "ap2/code/samples/python", "x402-a2a": "a2a-x402/python/x402_a2a"},
                "network_requests": 0, "source_built": False, "environment_installed": False,
                "original_source_imported": False, "native_application_executed": False, "model_requests": 0,
                "claim_limit": "Pristine source layout only. Build from separate copies; original wheel JSON inclusion and all environment/runtime qualification remain unverified."}
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps({key: manifest[key] for key in ("status", "ap2_files", "x402_files", "inputs_unchanged")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
