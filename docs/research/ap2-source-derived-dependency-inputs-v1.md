# Source-derived AP2 dependency inputs v1

30 October 2026. The reviewed
[exporter](../../scripts/prepare_ap2_dependency_inputs_v1.py) completed one
exclusive export into
[`runs/ap2-dependency-resolution/input-v1`](../../runs/ap2-dependency-resolution/input-v1/).
The [terminal export record](../../runs/ap2-dependency-resolution/input-v1/result.json)
contains **25 indexed runtime requirement rows, two separately source-bound
local dependency edges and three separate build-backend rows**. The five parsed
source/manifest inputs remained byte-identical. No resolver, network request,
wheel build, installation, acquired-source import, application or model call
occurred.

## What the prospective indexed dry-run will resolve

The
[runtime requirements](../../runs/ap2-dependency-resolution/input-v1/indexed-runtime-requirements.txt)
are the exact original-order union of AP2 SDK root `project.dependencies`,
sample `project.dependencies` and selected x402 package `project.dependencies`.
Duplicate cryptography pins and exact/broad A2A SDK, HTTPX and Pydantic overlap
remain visible. AP2's original runtime-declared pytest remains included;
x402's optional development/lint groups are outside this runtime union.

Only the original sample's local `ap2` workspace edge and floating direct
x402 Git edge are excluded from indexed resolution. Their original strings and
selected source identities are preserved in
[source-descriptors.json](../../runs/ap2-dependency-resolution/input-v1/source-descriptors.json).
The three local packages remain separate source-bound wheel/build obligations:

| Local project | Declared version | Original source selection | Separate backend requirement |
| --- | --- | --- | --- |
| AP2 SDK | `0.1` | AP2 `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`, root pyproject, package discovery under `code/sdk/python` | `setuptools>=61.0`, `setuptools.build_meta` |
| AP2 samples | `0.1` | Same AP2 commit, `code/samples/python` | `setuptools>=61.0`, `setuptools.build_meta` |
| x402-a2a | `0.1.0` | a2a-x402 `125db5526a965d2325459d1a9df2e274a7e42396`, `python/x402_a2a` | `hatchling`, `hatchling.build` |

The
[build requirements](../../runs/ap2-dependency-resolution/input-v1/separate-build-requirements.txt)
retain both original setuptools declarations and the Hatchling declaration.
They are not silently added to the indexed runtime resolver or treated as
already frozen tools. The previous x402 upstream lock remains outside this
derived runtime input because it conflicts with the selected package/AP2 pins.

## Target and unexecuted command

The export recorded native Windows CPython 3.13.1, AMD64, 64-bit pointers and
`win32`. Prospective binary-wheel resolution explicitly targets `win_amd64`,
implementation `cp`, Python `3.13` and ABI `cp313`. Its exact argv is in the
source descriptor. It uses interpreter `-I`, pip `--isolated`, `--dry-run`,
`--ignore-installed`, `--only-binary=:all:` and explicit
`https://pypi.org/simple`. Interpreter isolation precedes importing pip; pip
isolation alone does not control Python startup module lookup.

That prospective command has not run as part of this export. It names a fresh
separate `windows-cp313-dry-run-v1` allocation. The root agent must verify that
allocation remains unused and retain either the complete report or exact
resolution failure. A failure must not justify relaxing original pins,
dropping x402 or replacing a source-bound local package with an index package.

Independent source inspection found and corrected startup-isolation and
manifest operand/snapshot binding before this first export. The retained
snapshots are the exact pre-read bodies used to parse/validate both manifests
and all three pyprojects. No consumed export was rerun.

## Remaining build and runtime evidence

A successful indexed dry-run would establish only an index-selected binary
dependency closure for these declared requirements and target. It would still
leave separate backend/tool freezing, complete AP2 build-asset staging, exact
source builds of all three local wheels, wheel metadata agreement with the
original declarations, build/installer provenance and isolated installation
open. The complete pinned x402 package source is now captured; that fact does
not establish its wheel compatibility. Original role imports/bootstrap and
native same-task payment still require fresh evidence and the unchanged
prospective resource gate. This export awards no environment, domain,
full-task, novelty or checkpoint credit.

Exporter SHA256:
`290acf02c2ccb8ee666f1d74e99b0a0d376ffaa448dc5e31491ed2d503d527a8`.
Export result SHA256:
`c18051856084954d1d08b24701d7ab2fc981ed9f9a44441e7fef84c8890ab12d`.
Source descriptor SHA256:
`3d871894e37fa591ed78c51970bb30d22a71f86d2fe66eecd12b5b5a3f121e3b`.
Runtime requirements SHA256:
`46b609b3a68bf63c67987107936846992362e559b9db310256ae33ee15cacf50`.
Separate build requirements SHA256:
`dcf3b9ee279fa4fa7b1dfdcb1204e924479e6f226e73d5d5097940ed68bf2b2f`.
