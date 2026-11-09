"""Refresh bibliographic evidence without storing or redistributing paper bodies.

Run from any directory with Python 3 (stdlib only). The output records primary
response hashes and citation metadata, not verification of research results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ARXIV_IDS = (
    "2606.28690", "2609.05269", "2610.17805", "2610.28484",
    "2606.04104", "2608.21159", "2607.05397", "1606.09035", "2303.17751",
)
OTHER_URLS = (
    "https://aclanthology.org/2026.acl-long.1294/",
    "https://www.ietf.org/archive/id/draft-samal-vap-00.html",
    "https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD472.html",
    "https://eskang.github.io/assets/papers/memocode18.pdf",
    "https://osq.cs.berkeley.edu/pastprojects.htm",
    "https://people.eecs.berkeley.edu/~necula/pcc.html",
)


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metadata: dict[str, list[str]] = {}
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        if tag == "meta":
            name = fields.get("name") or fields.get("property")
            content = fields.get("content")
            if name and content and (name.startswith("citation_") or name == "og:title"):
                self.metadata.setdefault(name, []).append(content)

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def retrieve(url: str) -> dict:
    item: dict = {"requested_url": url}
    try:
        request = Request(url, headers={"User-Agent": "ContinuationStudy-SourceAudit/1.0"})
        with urlopen(request, timeout=25) as response:
            data = response.read()
            item.update(
                final_url=response.url,
                http_status=response.status,
                content_type=response.headers.get("Content-Type"),
                bytes=len(data),
                response_sha256=hashlib.sha256(data).hexdigest(),
            )
        if "html" in (item["content_type"] or ""):
            parser = MetadataParser()
            parser.feed(data.decode("utf-8", errors="replace"))
            item["citation_metadata"] = parser.metadata
            plain = " ".join(" ".join(parser.parts).split())
            history = re.search(r"Submission history(.+?)Full-text links", plain)
            if history:
                item["submission_history_as_reported"] = history.group(1).strip()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        item["retrieval_error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, HTTPError):
            item["http_status"] = error.code
    return item


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("retrieval-manifest.json"))
    arguments = parser.parse_args()
    urls = [f"https://arxiv.org/abs/{identifier}" for identifier in ARXIV_IDS]
    urls.extend(OTHER_URLS)
    # Sequential requests avoid placing a burst of concurrent load on arXiv.
    records = [retrieve(url) for url in urls]
    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Python stdlib HTTPS; citation meta tags and literal submission histories",
        "limitations": [
            "A response hash fingerprints the fetched page, not the paper's truth or authorship.",
            "Abstract-page hashes may change when navigation or citation metadata changes.",
            "Paper mechanisms are separately reviewed in the dated Markdown evidence note.",
            "Missing metadata or retrieval failure does not prove a source is nonexistent.",
        ],
        "sources": records,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(arguments.output), "sources": len(records), "failed": sum("retrieval_error" in r for r in records)}))


if __name__ == "__main__":
    main()
