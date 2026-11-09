"""Acquire pinned packaging/lock/license entities without executing them."""
from __future__ import annotations
import base64
import datetime
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "https://api.github.com/repos/google-agentic-commerce/a2a-x402"
commit = json.loads((ROOT / "commit.body").read_bytes())
sha = commit["sha"]
records = []
for label, path in (("package-lock", "python/x402_a2a/uv.lock"),
                    ("package-license", "python/x402_a2a/LICENSE"),
                    ("package-readme", "python/x402_a2a/README.md")):
    url = BASE + "/contents/" + path + "?ref=" + sha
    record = {"label": label, "url": url,
              "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ap2-dependency-reproducibility-screen/1", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read(5 * 1024 * 1024 + 1)
            if len(body) > 5 * 1024 * 1024:
                raise ValueError("Response exceeded bounded capture")
            record.update(status=response.status, final_url=response.url,
                          headers=dict(response.headers), body_file=label + ".body")
        with (ROOT / record["body_file"]).open("xb") as target:
            target.write(body)
        record["sha256"] = hashlib.sha256(body).hexdigest()
        item = json.loads(body)
        decoded = base64.b64decode(item["content"])
        decoded_file = label + ".source"
        with (ROOT / decoded_file).open("xb") as target:
            target.write(decoded)
        blob_sha = hashlib.sha1(b"blob " + str(len(decoded)).encode("ascii") + b"\0" + decoded).hexdigest()
        record.update(decoded_file=decoded_file, decoded_sha256=hashlib.sha256(decoded).hexdigest(), git_blob_sha=blob_sha, git_blob_matches=(blob_sha == item["sha"]))
    except Exception as error:
        record.update(error_type=type(error).__name__, error=str(error))
    records.append(record)
    with (ROOT / (label + ".receipt.json")).open("x", encoding="utf-8") as target:
        json.dump(record, target, indent=2, sort_keys=True)
    print(json.dumps({key: record[key] for key in ("label", "status", "git_blob_matches", "error") if key in record}), flush=True)

verification = commit["verification"]
payload = verification["payload"]
signature = verification["signature"]
headers, message = payload.split("\n\n", 1)
sig_lines = signature.rstrip("\n").split("\n")
signed = (headers + "\n" + "gpgsig " + sig_lines[0] + "\n" + "\n".join(" " + line for line in sig_lines[1:]) + "\n\n" + message).encode("utf-8")
git_sha = hashlib.sha1(b"commit " + str(len(signed)).encode("ascii") + b"\0" + signed).hexdigest()
identity = {"expected_git_commit_sha": sha, "reconstructed_git_commit_sha": git_sha, "git_commit_sha_matches": sha == git_sha, "github_signature_verified": verification["verified"], "github_signature_reason": verification["reason"], "scope": "Git object identity recomputation and HTTPS GitHub signature attestation; no independent signing-key cryptographic verification"}
with (ROOT / "commit-identity.json").open("x", encoding="utf-8") as target:
    json.dump(identity, target, indent=2, sort_keys=True)
print(json.dumps(identity), flush=True)
with (ROOT / "followup-result.json").open("x", encoding="utf-8") as target:
    json.dump({"commit": identity, "records": records}, target, indent=2, sort_keys=True)
