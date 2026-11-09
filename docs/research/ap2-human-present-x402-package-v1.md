# Complete pinned x402 package source capture v1

30 October 2026. The missing complete x402 source package identified in the
[dependency plan](ap2-human-present-dependency-plan-v1.md) is now retained in a
new source allocation. The
[manifest](source-evidence/ap2-x402-package-v1/manifest.json) covers **all 23
files, 672,591 bytes**, in `python/x402_a2a` at selected commit
`125db5526a965d2325459d1a9df2e274a7e42396`, plus the supplementary repository
root LICENSE. Total captured source is 24 files and 683,948 bytes.

The capture followed the
[independent source-selection audit](ap2-human-present-dependency-independent-review-v1.md).
It used the exact retained Git tree to select package paths. Each path received
one public HTTPS GET from the immutable raw GitHub commit URL; all returned
HTTP 200 with matching final URL, expected byte size and recomputed Git blob
SHA. SHA256 and HTTP headers/entities are retained per file under
[`ap2-x402-package-v1`](source-evidence/ap2-x402-package-v1/). No retry, prior
capture replacement or source edit occurred. All 35 files in the earlier
dependency-screen allocation remained byte-identical, including the two failed
checker records and original verifier scripts.

The complete selected package contains its original pyproject, README, LICENSE,
all `src/x402_a2a` modules, the zero-byte `py.typed`, original test, `.gitignore`
and `uv.lock`. All selected files have original Git mode `100644`; no submodule
or symlink needs unresolved external source for this package subtree. The
subtree Git identity remains `490c32161e645a1447906fe6c14e618914d93a16`.

A separate read-only
[postcapture verification record](../../runs/ap2-dependency-source-review/package-v1/result.json)
recomputed source/receipt membership, all seven package/subtree identities,
the declared local README/LICENSE/build paths and prior capture preservation.
Its 69 checks passed with zero discrepancies. This is a postcapture check by
the capture agent, not an independent human or separate-agent package audit.

## Exact scope for the next build step

The retained source is sufficient to attempt a source-bound x402 package build
after external build inputs are resolved. It does not prove that the build or
combined AP2 environment works. Hatchling remains an unpinned external build
backend. Runtime requirements remain the original broad lower bounds:
`a2a-sdk>=0.1.0`, `x402>=0.2.0`, `eth-account>=0.13.7`, `httpx>=0.28.1` and
`pydantic>=2.0.0`; their platform-specific transitive closure is unresolved.
Keep AP2's explicit exact pins when resolving the combined environment.

The captured upstream `uv.lock` remains an original source artifact with the
already documented AP2/package version mismatch. Do not adopt it as an AP2
lock. Repository examples, protocol specifications, CI and other files outside
`python/x402_a2a` are excluded, except the supplementary root LICENSE. That
exclusion does not remove any file in the selected package or any declared
local README/LICENSE/wheel source input.

No resolver, wheel build, installation, acquired-source import, original AP2
application staging, native process or model request occurred. A complete
AP2-specific dependency/build lock, isolated installation and source-faithful
bootstrap validation are still next steps. Native qualification continues to
require the unchanged prospective resource gate and original workflow/grade
evidence. Source-package completeness earns no domain, novelty, full-task or
checkpoint-percentage credit.

Manifest SHA256:
`74db7661df834b7d05371d84aa4a6f0e6d9d243f344204923cef65e15b449d07`.
Capture plan SHA256:
`b8b984bbc8cf9e03bc8180febb82e0afff8c1df9bb75b45fb96b5ed0fd4900e3`.
Capture script SHA256:
`793838fdac9e6ba4011ae5c2972d13bea545f2798334f818c2b68ce7d059f258`.
Postcapture verification SHA256:
`76e31f53bcf7cadd31efe6b2b62b2f61cb0d28bba0ee2edbe1dad0cbb5b8bc32`.
