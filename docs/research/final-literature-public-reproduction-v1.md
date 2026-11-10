# Reproducing the literature evidence v1

The public bibliography records factual titles, authors, inspected versions,
publication metadata and primary URLs in
[references-v3.json](../../paper/references-v3.json). The
[signed AI literature assessment](final-literature-review-v1.md) states the method
comparisons and their limits. It does not claim human review or reproduction of
another system's experiments.

Full publisher paper copies, scanned page images, extracted bodies and long tool
excerpts are retained locally as research evidence. The public package supplies
factual metadata, retrieval code and hashes; those retained full copies are not
required to be committed. Follow each entry's primary URL and exact manuscript
version rather than substituting a current revision.

The [bounded retrieval program](source-evidence/final-literature-review-v1-20261110/retrieve_primary_v1.py)
downloads the original CEGAR, memo-functions and BMC paper copies plus the Nature
metadata page. It also retains the failed constraint-paper retrieval. Run a copy
in a new directory: the program deliberately refuses to overwrite its evidence
allocation. It uses Python, `requests` and `pypdf`, with three concurrent requests,
a 5 MB response limit and bounded network timeouts. A new response that differs
from a retained hash is a new capture, not a reproduction of the exact bytes.

| Source | Primary download | Retained SHA256 |
| --- | --- | --- |
| CEGAR original CAV 2000 copy | [Stanford course-hosted original PDF](https://web.stanford.edu/class/cs357/cegar.pdf) | `1de34eb4dc77fc47f1aa0381cec9447b162f52ed4d5311ff6299f5dce413086c` |
| Memo functions, Nature 1968 | [Original paper copy](https://www.cs.utexas.edu/~hunt/research/hash-cons/hash-cons-papers/michie-memo-nature-1968.pdf) | `399575cd9e7b91aaaca522a9432f17f038041ecead5403eeb33e5e8dce877d8c` |
| BMC original TACAS 1999 copy | [Author-hosted original PDF](https://fmv.jku.at/papers/BiereCimattiClarkeZhu-TACAS99.pdf) | `13a6f14d2d2eb84c6f612702172d5abe9130477bc5c92fc8b06b3a32433be18b` |
| Memo-functions publisher metadata | [Nature article page](https://www.nature.com/articles/218019a0) | `bbca673a15f359af0f2c69df916c056d0eee67d7f345b7832e47caa93f7a3459` |

HTTP HTML can change between requests. The quoted Nature hash identifies this
capture only; its citation tags can be checked independently against the title,
author, journal, volume, issue, pages and DOI. The scanned memo paper exposes
almost no useful extracted text. The original page images must be inspected to
check the body; the first physical page contains the end of a preceding article
and the beginning of Michie's paper on printed page 19.

The factual [contract-quotient footer receipt](source-evidence/final-literature-public-v1/quotient-publication-footer.json)
records the refreshed title, printed authors and IEEE 2018 footer. It does not
infer a proceedings page range from physical PDF pages. Mackworth's
[primary author metadata](https://www.cs.ubc.ca/~mack/Publications/b2hd-AI77.html)
supports title, author, journal, volume, issue, year and pages. The new full-body
fetch failed; this review does not claim a fresh full-body AC-3 inspection.

For the software entries, query the exact commit and license revisions in the
[source lock](../../external/source-lock.json). The retained
[software receipt](source-evidence/final-literature-review-v1-20261110/software-pin-review/receipt.json)
records account, UTC author/committer date, SPDX license and decoded Git license
blob hash. A reviewer can call `gh api` on its recorded endpoints and decode the
license content. The Git blob SHA1 includes the `blob <byte-count>` header and
one zero byte before the license bytes. Commit identity, account identity and
license verification do not establish personal legal identity or authorship of
an algorithmic idea.

The local [retrieval manifest](source-evidence/final-literature-review-v1-20261110/manifest.json)
distinguishes formatted search/open receipts from raw HTTP bodies and gh API
output bodies. It also records the unchanged paper v4 hashes. Missing full-copy
files in a public checkout can be fetched from their primary URLs; their absence
must not be presented as a passed local byte audit. The read-only audit describes
which locally retained bytes were actually checked.
