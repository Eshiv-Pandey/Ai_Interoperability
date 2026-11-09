# AP2 dependency preparation independent source review v1

30 October 2026. A separate AI agent independently recomputed the retained
x402 source identities and reviewed the packaging selection in
[the dependency plan](ap2-human-present-dependency-plan-v1.md). The
[new review record](../../runs/ap2-dependency-source-review/v1/result.json)
passed 153 bounded receipt/source checks with zero discrepancies. All 79 read
inputs were byte-identical before and after the review. These are source audit
checks, not runtime tests, dependency resolution or checkpoint credit.

The [independent review script](../../runs/ap2-dependency-source-review/v1/review.py)
uses only Python standard-library parsing, Git object reconstruction, hashing,
TOML and AST inspection. It does not execute the captured verifier or import the
acquired application. No network request, installation, resolver, wheel build,
source import, native process or model call occurred.

The reviewed
[source-verification-v2.json](source-evidence/ap2-x402-dependency-screen-v1/source-verification-v2.json)
has exact SHA256
`a070e92809986420a56c96b4b11cc0a8cc55fb58ef0c3103e4ea2ae882996e56`.
The review rechecked all 34 unique declared input bindings, its 41 source-check
membership and the retained HTTP entities against their capture receipts.

## Source selection verified at its stated scope

The retained repository/default-ref responses identify
`google-agentic-commerce/a2a-x402`, default branch `main` and commit
`125db5526a965d2325459d1a9df2e274a7e42396`. The independently reconstructed signed
Git commit has that same SHA. Its recursive tree root is
`bd16cd70aa86b4b561027d94c99591e17f0dcf46`; all 27 root/subtree identities and
the five selected packaging/readme/license blobs recompute exactly. The tree
response is nontruncated and its paths are unique. HTTP entity URLs, HTTP 200
status, body hashes and capture-record binding matched the named public
repository and immutable selected ref.

GitHub's retained commit response reports a valid verified signature. This
review checks the response and exact Git object identity; it does not perform
independent signing-key cryptographic verification or establish live runtime
authentication.

The first failed commit reconstruction remains
[commit-identity.json](source-evidence/ap2-x402-dependency-screen-v1/commit-identity.json).
The original
[source-verification.json](source-evidence/ap2-x402-dependency-screen-v1/source-verification.json)
still records five failed tree checks from incorrect dotted-path normalization.
Both files and the original scripts matched v2's preserved input hashes. The
review's independent tree reconstruction uses path components directly and
preserves literal dots; it does not rerun or replace either failed record.

## Packaging and remaining installation work

The original AP2 root/sample pyprojects matched the retained acquisition at
`e1ea56db72a6385bce3e5c1112b3a56ce60acb43`. The root builds `ap2==0.1` from
`code/sdk/python`, with setuptools and Python `>=3.11`. The sample builds
`ap2-samples==0.1` from its `src`, links the workspace SDK and unconditionally
declares the floating x402 Git dependency. The SDK build declaration belongs to
the AP2 root; no separately assumed SDK pyproject is needed.

The selected x402 package declares `x402-a2a==0.1.0`, Hatchling, Python `>=3.10`
and broad lower bounds for A2A SDK, x402, eth-account, HTTPX and Pydantic. Its own
retained lock instead selects x402-a2a `1.0.0`, A2A SDK `0.3.1` and Pydantic
`2.11.7`. AP2 explicitly pins A2A SDK `0.3.24` and Pydantic `2.12.5`. That lock
must remain evidence of a mismatch, not be adopted as a combined AP2 lock.

Independent AST inspection of the same 40 source-bound HP/common Python files
found no direct external x402/x402_a2a imports. This supports the plan's limited
import statement; it neither proves transitive/runtime absence nor authorizes
deleting an original declared dependency.

The source selection is suitable as a disclosed, immutable input to the next
isolated preparation step. It is a preparation-time selection of an originally
floating requirement, not an AP2-authored historical lock. Current captures
contain selected packaging blobs, not the complete x402 source package or a
complete AP2 environment. Next work remains complete pinned staging, combined
dependency resolution preserving original exact pins, frozen build/wheel/runtime
provenance, isolated installation and source-faithful imports. Native execution
still requires the unchanged prospective physical/commit resource gate and
bootstrap checks. This review establishes none of those outcomes, a qualified
second domain, purchase success, novelty or human acceptance.

Review record SHA256:
`d6c349dd7ea50462ab9c1b0a0293d683fb313b8affc1a2218b634b8c9db13a79`.
Independent script SHA256:
`0aaf1825a2e6419cf90c53fb2379fa6e04370adb5afd62f213592acbd2784388`.
