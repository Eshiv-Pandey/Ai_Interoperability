"""Capture one public Google quota-policy page; never use credentials or APIs."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import ssl
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/source-evidence/gemini-quota-policy-v1"
URL = "https://ai.google.dev/gemini-api/docs/rate-limits"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip, self.data = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, value):
        if not self.skip and value.strip():
            self.data.append(value.strip())


def main():
    if OUTPUT.exists():
        raise ValueError("Exclusive public policy capture already exists; do not repeat")
    record = {"schema_version": "gemini-public-quota-policy-capture/1", "url": URL,
              "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "authenticated": False, "model_or_quota_api_called": False,
              "project_limits_obtained": False,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(urllib.request.Request(URL, headers={"Accept": "text/html"}), timeout=25) as response:
            body = response.read(2 * 1024 * 1024 + 1)
            record["http_status"] = response.status
        if len(body) > 2 * 1024 * 1024:
            raise ValueError("Document exceeds bounded capture")
        OUTPUT.mkdir(parents=True)
        with (OUTPUT / "rate-limits.html").open("xb") as target:
            target.write(body)
        record.update(status="public_policy_retained", bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        visible = Visible()
        visible.feed(body.decode("utf-8"))
        hits = []
        for index, value in enumerate(visible.data):
            if re.search(r"per project|per API key|Pacific|input token|Requests per day|AI Studio|active rate|Preview|capacity|rate limits depend", value, re.I):
                hits.append(" ".join(visible.data[max(0, index - 1):min(len(visible.data), index + 3)]))
        record["policy_excerpts"] = hits[:35]
        record["studio_links"] = sorted(set(re.findall(r'https://aistudio\.google\.com[^\s"<>]*', body.decode("utf-8"))))
    except Exception as error:
        if not OUTPUT.exists():
            OUTPUT.mkdir(parents=True)
        record.update(status="public_policy_unavailable", error_type=type(error).__name__)
    with (OUTPUT / "result.json").open("x", encoding="utf-8") as target:
        json.dump(record, target, indent=2)
        target.write("\n")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "public_policy_retained" else 1


if __name__ == "__main__":
    raise SystemExit(main())
