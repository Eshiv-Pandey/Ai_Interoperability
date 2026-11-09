"""Acquire pinned official wheels for source inspection only; never import them."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
PACKAGES = (("google-adk", "1.28.0"), ("a2a-sdk", "0.3.24"))


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def download(url, path):
    digest, size = hashlib.sha256(), 0
    request = urllib.request.Request(url, headers={"User-Agent": "AP2-source-review/1"})
    with urllib.request.urlopen(request, timeout=40) as response, path.open("xb") as stream:
        for block in iter(lambda: response.read(65536), b""):
            stream.write(block)
            digest.update(block)
            size += len(block)
        final_url, status = response.geturl(), response.status
    return {"url": url, "final_url": final_url, "http_status": status,
            "path": str(path.relative_to(ROOT)), "bytes": size, "sha256": digest.hexdigest()}


def selected(package, name):
    if ".dist-info/" in name and (name.endswith("/METADATA") or name.endswith("/WHEEL")
                                  or "license" in name.lower() or name.endswith("/RECORD")):
        return True
    if package == "google-adk":
        return (name.startswith("google/adk/a2a/") and name.endswith(".py")
                or name in {"google/adk/cli/fast_api.py", "google/adk/tools/function_tool.py",
                            "google/adk/tools/long_running_tool.py", "google/adk/tools/base_tool.py",
                            "google/adk/flows/llm_flows/functions.py"})
    return (name.startswith("a2a/server/") and name.endswith(".py")
            or name in {"a2a/types.py", "a2a/utils/task.py"})


def main():
    plan = {"schema_version": "ap2-adk-task-source-acquisition/1", "created_at_utc": now(),
            "packages": [{"name": name, "version": version,
                          "metadata_url": f"https://pypi.org/pypi/{name}/{version}/json"}
                         for name, version in PACKAGES],
            "scope": "Official wheel bytes, package metadata/license and selected adapter/server/tool sources only.",
            "maximum_attempts_per_request": 1, "source_imports": 0, "installations": 0,
            "application_or_model_calls": 0,
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_new(ROOT / "plan.json", plan)
    results = []
    for name, version in PACKAGES:
        item = {"name": name, "version": version, "started_at_utc": now(), "status": "failed"}
        directory = ROOT / name
        directory.mkdir(exist_ok=False)
        try:
            item["metadata"] = download(f"https://pypi.org/pypi/{name}/{version}/json",
                                        directory / "pypi-version.json")
            metadata = json.loads((directory / "pypi-version.json").read_bytes())
            if metadata["info"]["version"] != version:
                raise ValueError("PyPI metadata version differs")
            choices = [row for row in metadata["urls"] if row["packagetype"] == "bdist_wheel"
                       and row["filename"].endswith("-py3-none-any.whl")]
            if len(choices) != 1:
                raise ValueError("Expected exactly one universal Python wheel")
            wheel = choices[0]
            if urllib.parse.urlsplit(wheel["url"]).hostname != "files.pythonhosted.org":
                raise ValueError("Wheel URL is not the official PyPI file host")
            filename = PurePosixPath(wheel["filename"])
            if len(filename.parts) != 1 or filename.name != wheel["filename"]:
                raise ValueError("Unsafe wheel filename")
            item["declared_wheel"] = {key: wheel[key] for key in
                                      ("filename", "url", "size", "digests", "upload_time_iso_8601")}
            write_new(directory / "wheel-request.json", item["declared_wheel"])
            item["wheel"] = download(wheel["url"], directory / wheel["filename"])
            if (item["wheel"]["sha256"] != wheel["digests"]["sha256"]
                    or item["wheel"]["bytes"] != wheel["size"]):
                raise ValueError("Downloaded wheel differs from official PyPI size/SHA256")
            item["files"] = []
            with zipfile.ZipFile(directory / wheel["filename"]) as archive:
                infos = archive.infolist()
                write_new(directory / "wheel-inventory.json", [
                    {"path": info.filename, "bytes": info.file_size, "crc32": info.CRC}
                    for info in infos])
                if len({info.filename for info in infos}) != len(infos):
                    raise ValueError("Duplicate archive member")
                for info in infos:
                    if info.is_dir() or not selected(name, info.filename):
                        continue
                    path = PurePosixPath(info.filename)
                    if (path.is_absolute() or ".." in path.parts or str(path) != info.filename
                            or any(char in info.filename for char in ("\\", ":", "\0"))
                            or stat.S_ISLNK(info.external_attr >> 16)):
                        raise ValueError("Unsafe selected wheel member")
                    raw = archive.read(info)
                    target = directory / "source" / Path(*path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as stream:
                        stream.write(raw)
                    item["files"].append({"path": str(target.relative_to(ROOT)), "bytes": len(raw),
                                          "sha256": hashlib.sha256(raw).hexdigest()})
            item["status"] = "acquired_selected_sources"
            print(name + ": " + str(item["wheel"]["bytes"]) + " wheel bytes; "
                  + str(len(item["files"])) + " selected files", flush=True)
        except Exception as error:
            item["error"] = type(error).__name__ + ": " + str(error)
        item["finished_at_utc"] = now()
        write_new(directory / "result.json", item)
        results.append(item)
    result = {"schema_version": "ap2-adk-task-source-result/1", "finished_at_utc": now(),
              "status": "acquired" if all(row["status"] == "acquired_selected_sources"
                                          for row in results) else "failed_or_partial",
              "packages": results, "source_imports": 0, "installations": 0,
              "application_or_model_calls": 0}
    write_new(ROOT / "result.json", result)
    print(json.dumps({"status": result["status"], "packages": len(results)}), flush=True)
    return 0 if result["status"] == "acquired" else 1


if __name__ == "__main__":
    raise SystemExit(main())
