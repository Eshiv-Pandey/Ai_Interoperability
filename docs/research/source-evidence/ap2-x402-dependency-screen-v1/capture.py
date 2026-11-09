"""Read-only public-origin dependency screen; never executes acquired code."""
from __future__ import annotations
import datetime
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "https://api.github.com/repos/google-agentic-commerce/a2a-x402"
records = []

def acquire(label: str, url: str):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={
        "User-Agent": "ap2-dependency-reproducibility-screen/1",
        "Accept": "application/vnd.github+json",
    })
    record = {"label": label, "url": url, "started_at_utc": started}
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read(5 * 1024 * 1024 + 1)
            if len(body) > 5 * 1024 * 1024:
                raise ValueError("Response exceeded bounded capture")
            record.update(status=response.status, final_url=response.url,
                          headers=dict(response.headers), body_file=f"{label}.body")
        with (ROOT / record["body_file"]).open("xb") as target:
            target.write(body)
        record["sha256"] = hashlib.sha256(body).hexdigest()
        data = json.loads(body)
    except Exception as error:
        record.update(error_type=type(error).__name__, error=str(error))
        data = None
    records.append(record)
    with (ROOT / f"{label}.receipt.json").open("x", encoding="utf-8") as target:
        json.dump(record, target, indent=2, sort_keys=True)
    print(json.dumps({key: record[key] for key in ("label", "status", "error") if key in record}), flush=True)
    return data

metadata = acquire("repository", BASE)
if metadata:
    branch = metadata["default_branch"]
    ref = acquire("default-ref", BASE + "/git/ref/heads/" + branch)
    if ref:
        sha = ref["object"]["sha"]
        commit = acquire("commit", BASE + "/git/commits/" + sha)
        if commit:
            acquire("tree", BASE + "/git/trees/" + commit["tree"]["sha"] + "?recursive=1")
            acquire("pyproject", BASE + "/contents/python/x402_a2a/pyproject.toml?ref=" + sha)
            acquire("license", BASE + "/contents/LICENSE?ref=" + sha)
with (ROOT / "capture-result.json").open("x", encoding="utf-8") as target:
    json.dump({"scope": "Public HTTPS source metadata/entities only; no clone, install, import or native/provider request", "records": records}, target, indent=2, sort_keys=True)
