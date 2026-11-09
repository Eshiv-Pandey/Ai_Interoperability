# AP2 human-present dependency plan v1

30 October 2026, source-only preparation. The original unpinned x402 dependency
now has a concrete public-origin source selection. **No environment was
installed, resolved or imported, and no AP2/model workflow ran.** Runtime
compatibility and a complete AP2 lock remain open.

## Workspace and source selection

The retained original AP2 pin is
`e1ea56db72a6385bce3e5c1112b3a56ce60acb43`. Its root
[`pyproject.toml`](source-evidence/ap2-procurement-screen-v1/source/pyproject.toml)
defines `ap2==0.1`, Python `>=3.11`, setuptools `>=61.0`, package discovery under
`code/sdk/python` and the uv workspace member `code/samples/python`.
The original
[sample declaration](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/pyproject.toml)
defines `ap2-samples==0.1`, Python `>=3.11`, packages under `src`, and a workspace
source for `ap2`. Install/build the SDK and samples from those exact sources,
not a same-named package found on an index. Keep original source files unchanged.

The sample's `x402-a2a` requirement names the public repository and
`python/x402_a2a` subdirectory but no commit or tag. Bounded public HTTPS capture
at 21:13:57 UTC on 29 October resolves its default branch `main` to
**`125db5526a965d2325459d1a9df2e274a7e42396`**. This is a disclosed preparation-time
selection of the original floating source, not an AP2-authored historical lock.
Use this immutable selection in a separate future dependency manifest:

```text
x402-a2a @ git+https://github.com/google-agentic-commerce/a2a-x402.git@125db5526a965d2325459d1a9df2e274a7e42396#subdirectory=python/x402_a2a
```

The [default ref](https://api.github.com/repos/google-agentic-commerce/a2a-x402/git/ref/heads/main)
and [commit object](https://api.github.com/repos/google-agentic-commerce/a2a-x402/git/commits/125db5526a965d2325459d1a9df2e274a7e42396)
were retained as HTTP entities, including status, final URL and headers.
GitHub reports a valid verified commit signature. Local reconstruction matches
the Git commit SHA; all recursive tree identities and selected blob identities
also match. This establishes public-origin identity and GitHub's signature
attestation, not independent cryptographic verification of a signing key.

The selected [package pyproject](https://github.com/google-agentic-commerce/a2a-x402/blob/125db5526a965d2325459d1a9df2e274a7e42396/python/x402_a2a/pyproject.toml)
declares `x402-a2a==0.1.0`, Python `>=3.10`, Hatchling, and runtime dependencies:

| Requirement | Consequence for AP2 preparation |
| --- | --- |
| `a2a-sdk>=0.1.0` | Preserve AP2's explicit `0.3.24`, subject to actual resolver and import verification. |
| `x402>=0.2.0` | Still broad; freeze the selected release and its transitive closure before execution. |
| `eth-account>=0.13.7` | Resolve with AP2's pinned `web3==7.15.0`; binary/transitive compatibility is unverified. |
| `httpx>=0.28.1` | AP2 explicitly selects `0.28.1`. |
| `pydantic>=2.0.0` | AP2 explicitly selects `2.12.5`. |

The package's own [uv lock](https://github.com/google-agentic-commerce/a2a-x402/blob/125db5526a965d2325459d1a9df2e274a7e42396/python/x402_a2a/uv.lock)
is retained. It selects `a2a-sdk==0.3.1`, `pydantic==2.11.7`, and the local
`x402-a2a==1.0.0`; these differ from AP2's explicit pins and the selected
package's own `0.1.0` declaration. It is not an AP2 workspace lock and must not
be adopted as one. Its Python `>=3.10`/3.13 resolution markers are not proof that
the combined AP2 environment works on Python 3.13.

## Is x402 mandatory for human-present card imports?

The dependency is **unconditionally declared by `ap2-samples`**. Its presence
does not imply that the human-present card flow imports it. A static AST read
of all 40 retained Python files in `common`, `merchant_agent`,
`merchant_payment_processor_agent`, `credentials_provider_agent` and
`shopping_agent` found no direct import of external `x402` or `x402_a2a`.
The credentials provider defines its own Pydantic mock x402 payload structures;
the HP card-selection branch uses local account structures. A broader text
scan finds Web3 imports in the separate x402 MCP servers, which are different
scenario roles.

This is a source statement about inspected imports. Installed transitive
libraries, plugin loading and runtime behavior were not inspected here. Keep
the original sample dependency closure in the faithful setup; deleting the
declared x402 requirement based on this scan would be a disclosed dependency
change, not the unchanged original installation.

## Prospective installation and verification sequence

1. Allocate a fresh isolated preparation namespace and venv. Stage the complete
   pinned AP2 build inputs, SDK, original samples, readmes/licenses and scenario
   assets with a manifest. Stage the complete x402 package at the selected Git
   pin, verifying its source tree. Current captures retain selected packaging
   blobs, not the complete x402 package or AP2 environment.
2. Keep a separate dependency input derived from the original root/sample
   declarations. Record the selected x402 pin explicitly without editing the
   retained original pyproject files. SDK/sample wheels must come from the
   staged AP2 source; the x402 wheel must come from its pinned source. Record
   exact build backend/tool versions and wheel hashes. Build isolation and
   build requirements are also part of reproducibility.
3. Resolve the complete combined runtime closure for the chosen interpreter and
   platform, preserving all original exact AP2 pins. Freeze wheel/source
   provenance and hashes, markers and build inputs in a new AP2-specific lock.
   An installer source override or explicit derived requirements file must be
   verified to select the immutable x402 source; the original floating URL
   must not be silently resolved again. No exact resolver/override invocation
   is represented as tested by this note.
4. Install only that frozen environment into the isolated venv and retain the
   complete installer report. Check installed metadata, dependency consistency,
   source/wheel identity and original role import/bootstrap behavior. Metadata
   lower bounds alone do not prove Python 3.13 compatibility or the existence
   of compatible wheels for every dependency.
5. Only after dependency/software preparation and independent review pass,
   perform the unchanged timed 1 GiB physical/2 GiB commit prospective resource
   gate and immediate bootstrap checks before a fresh native scenario
   allocation. Source selection is not a resource pass, installed readiness,
   model quota result or domain qualification.

The current actionable gain is a stable x402 source selection and explicit
packaging/lock mismatch, removing ambiguity before resolution. A complete
transitive lock, wheel availability, platform compatibility, source-faithful
imports, native same-task payment and independent domain validity remain open.

## Retained verification and disclosed corrections

[Source verification v2](source-evidence/ap2-x402-dependency-screen-v1/source-verification-v2.json)
records 41 bounded source identity/static-import checks passing, binding 34
inputs. This is local source verification, not tests or an independent peer
audit. Its SHA256 is
`a070e92809986420a56c96b4b11cc0a8cc55fb58ef0c3103e4ea2ae882996e56`.
The first commit reconstruction omitted the signature's trailing continuation
line and did not match; `commit-identity.json` is preserved. The first tree
checker incorrectly removed literal dots from directory names and failed five
tree checks; `source-verification.json` and its script remain preserved. V2
corrects only parent-path normalization and uses the corrected exact signature
reconstruction already retained in the first source-verification file. No
network capture or original source was rerun to change those records.

Original AP2 root/sample pyproject SHA256 values remain
`78656cfd88b01d10c693a7fdffdf9d789dc4ddfbb57c208b583e13986fd44b63` and
`0121f705c05aa3836cff7a7fb4d967b9e3af7a3983a4e78f3cb0f19747b7fbf1`.
The retained x402 pyproject SHA256 is
`fe10d8e08f5787d943b521cc9ec94cb76ad07bdd80e24a0eb68eef8a525b9e46`;
its own lock SHA256 is
`7c5db01b9fe3b9fce5796ec5b1439cf78e304062cbac6c623318a6224aabd5b9`.
