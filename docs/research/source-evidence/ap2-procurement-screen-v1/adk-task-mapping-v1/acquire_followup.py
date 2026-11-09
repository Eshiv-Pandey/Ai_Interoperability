"""Extract additional retained-wheel sources and fetch three pinned AP2 client files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
PIN = "e1ea56db72a6385bce3e5c1112b3a56ce60acb43"
WHEEL_PATHS = ("google/adk/agents/llm_agent.py", "google/adk/tools/mcp_tool/mcp_tool.py",
               "google/adk/tools/mcp_tool/mcp_toolset.py", "google/adk/sessions/state.py")
CLIENT_PATHS = ("code/web-client/src/a2aClient.ts", "code/web-client/src/hooks/useChat.ts",
                "code/web-client/src/App.tsx")


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def save(relative, raw):
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    write_new(ROOT / "followup-plan.json", {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "wheel_paths": WHEEL_PATHS, "client_paths": CLIENT_PATHS, "git_pin": PIN,
        "maximum_attempts_per_request": 1, "source_imports": 0, "installations": 0,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    tree = json.loads((ROOT.parent / "tree-response.json").read_bytes())
    entries = {row["path"]: row for row in tree["tree"] if row["type"] == "blob"}
    records, errors = [], []
    wheel_result = json.loads((ROOT / "google-adk/result.json").read_bytes())
    wheel = ROOT / wheel_result["wheel"]["path"]
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != wheel_result["wheel"]["sha256"]:
        raise ValueError("Retained wheel changed")
    with zipfile.ZipFile(wheel) as archive:
        for name in WHEEL_PATHS:
            try:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unsafe selected name")
                records.append(save("followup-source/" + name, archive.read(name)))
            except Exception as error:
                errors.append({"path": name, "error": type(error).__name__ + ": " + str(error)})
    for name in CLIENT_PATHS:
        item = {"source_path": name, "url": f"https://raw.githubusercontent.com/google-agentic-commerce/AP2/{PIN}/{name}",
                "expected_git_blob": entries[name]["sha"]}
        try:
            request = urllib.request.Request(item["url"], headers={"User-Agent": "AP2-source-review/1"})
            with urllib.request.urlopen(request, timeout=40) as response:
                raw = response.read()
                item["final_url"], item["http_status"] = response.geturl(), response.status
            item.update(save("client-source/" + name, raw))
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
            item["git_blob"] = blob
            if blob != item["expected_git_blob"] or len(raw) != entries[name]["size"]:
                raise ValueError("Pinned Git tree blob mismatch")
            item["status"] = "acquired"
        except Exception as error:
            item.update(status="failed", error=type(error).__name__ + ": " + str(error))
            errors.append({"path": name, "error": item["error"]})
        records.append(item)
    result = {"status": "acquired" if not errors else "failed_or_partial", "files": records,
              "errors": errors, "source_imports": 0, "installations": 0,
              "finished_at_utc": datetime.now(timezone.utc).isoformat()}
    write_new(ROOT / "followup-result.json", result)
    print(json.dumps({"status": result["status"], "files": len(records), "errors": errors}), flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
