"""Unpack pinned original cached packages for the isolated SDK HTTP control.

No networking, package scripts, SDK execution or edits to original dependencies.
The cache-copy ledger selects original releases satisfying dependency ranges;
this installer preserves that graph, including nested conflicting versions.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "external/sdk-http-control-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ledger_path = ROOT / "runs/sdk-http-control/cache-copy-ledger-v1.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    cache = Path(ledger["target"])
    records = {r["key"]: r for r in ledger["records"]}

    def read(key):
        record = records[key]
        algorithm, encoded = record["integrity"].split("-", 1)
        expected = base64.b64decode(encoded)
        hexadecimal = expected.hex()
        filename = cache / "content-v2" / algorithm / hexadecimal[:2] / hexadecimal[2:4] / hexadecimal[4:]
        data = filename.read_bytes()
        if hashlib.new(algorithm, data).digest() != expected or digest(data) != record["sha256"]:
            raise ValueError(f"Cached original package bytes changed: {key}")
        return data

    selections = {(s["name"], s["range"]): s["selected_original_release"] for s in ledger["selections"]}
    primary = {}
    for selection in ledger["selections"]:
        primary.setdefault(selection["name"], selection["selected_original_release"])
    modules = ENV / "node_modules"
    modules.mkdir(exist_ok=False)
    packages = ENV / "original-package-tarballs"
    packages.mkdir(exist_ok=False)
    metadata = {}
    for name in primary:
        key = "make-fetch-happen:request-cache:https://registry.npmjs.org/" + name
        data = read(key)
        metadata[name] = json.loads(data)
        (packages / (name.replace("/", "__") + "-metadata.json")).write_bytes(data)
    installed = []

    def unpack(name, version, destination):
        release = metadata[name]["versions"][version]
        key = "make-fetch-happen:request-cache:" + release["dist"]["tarball"]
        data = read(key)
        publisher_integrity = release["dist"]["integrity"]
        algorithm, encoded = publisher_integrity.split("-", 1)
        if hashlib.new(algorithm, data).digest() != base64.b64decode(encoded):
            raise ValueError(f"Publisher integrity mismatch: {name}@{version}")
        tarball = packages / f"{name.replace('/', '__')}-{version}.tgz"
        if tarball.exists():
            if tarball.read_bytes() != data:
                raise ValueError("Conflicting original release")
        else:
            tarball.write_bytes(data)
        destination.mkdir(parents=True, exist_ok=False)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                relative = Path(member.name)
                if not relative.parts or relative.parts[0] != "package":
                    raise ValueError("Unexpected npm tar root")
                target = (destination / Path(*relative.parts[1:])).resolve()
                if not target.is_relative_to(destination.resolve()):
                    raise ValueError("Archive path escapes package")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as stream:
                        stream.write(archive.extractfile(member).read())
                else:
                    raise ValueError("Unsupported link or special archive member")
        actual = json.loads((destination / "package.json").read_text(encoding="utf-8"))
        if actual["name"] != name or actual["version"] != version:
            raise ValueError("Installed package identity differs from original metadata")
        installed.append({"name": name, "version": version, "path": destination.relative_to(ENV).as_posix(),
                          "source_url": release["dist"]["tarball"], "publisher_integrity": publisher_integrity,
                          "tarball_sha256": digest(data)})

    for name, version in primary.items():
        unpack(name, version, modules / name)

    def nested_dependencies(name, version, destination, ancestors=()):
        identity = (name, version)
        if identity in ancestors:
            raise ValueError("Unexpected cached dependency cycle")
        release = metadata[name]["versions"][version]
        for dependency, requirement in release.get("dependencies", {}).items():
            wanted = selections[(dependency, requirement)]
            if primary[dependency] != wanted:
                child = destination / "node_modules" / dependency
                unpack(dependency, wanted, child)
                nested_dependencies(dependency, wanted, child, ancestors + (identity,))

    for name, version in primary.items():
        nested_dependencies(name, version, modules / name)
    for folder, name in [("sdk", "@a2a-js/sdk"), ("jose", "jose")]:
        shutil.copytree(ENV / "vendor" / folder, modules / name)
    trees = [{"path": p.relative_to(ENV).as_posix(), "bytes": p.stat().st_size,
              "sha256": digest(p.read_bytes())} for p in sorted(modules.rglob("*")) if p.is_file()]
    result = {"kind": "LOCAL PINNED DEPENDENCY SETUP; NO SERVICE EXECUTION",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "installer_sha256": digest(Path(__file__).read_bytes()),
              "cache_copy_ledger_sha256": digest(ledger_path.read_bytes()),
              "installed_cached_packages": installed, "installed_files": trees,
              "copied_sdk_version": "1.1.0", "copied_jose_version": "6.2.12",
              "network_requests": 0, "package_scripts_executed": 0}
    with (ENV / "environment-lock.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"installed_cached_packages": len(installed), "installed_files": len(trees),
                      "network_requests": 0, "package_scripts_executed": 0}))


if __name__ == "__main__":
    main()
