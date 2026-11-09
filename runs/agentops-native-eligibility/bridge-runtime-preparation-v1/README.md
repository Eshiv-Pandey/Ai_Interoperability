# Pinned bridge runtime preparation

Prepared 27 October 2026 without package installation, building, application
requests or inference. Original bridge checkouts and installed dependencies are
unchanged. This is a runtime preparation, not an AgentOps/bridge experiment.

`graph.json` identifies 15 physical packages, 20 resolved dependency/peer edges,
10 absent optional dependencies and 2,938 regular files (38,172,079 bytes).
Root package source, built distribution, licenses and lock files are included;
only each package's top-level `.git` and `node_modules` directories are omitted.
The dependency graph recreates `node_modules` links explicitly. Physical nodes
with equal package names/versions remain separate when original resolution used
different roots. This preserves the two SDK/server/core/zod version families.

`runtime.zip` contains `graph.json` and every graph file. `archive.json` binds its
9,094,376 bytes to SHA-256
`c4567dc405e74d664921f038e6c5acb454c66fd85f42f21c04a10c8e75305864`.
The archive contains no symlink entries. The materializer validates names,
entry sets, sizes and hashes before creating internal relative package links.

The new Linux runtime is
`/var/tmp/agentops-research-v7-gs9r5her/external/runtime-agentops-bridges-v1`.
Its `external/a2a-to-mcp` and `external/mcp-a2a` aliases expose the original
`dist/cli.js`, `dist/index.js` and dependency paths. The exact copied
`materialization.json` lists all 22 internal symlinks and both CLI paths.
Do not install into or otherwise modify this runtime.

`runtime-verification.json` verifies all file bytes and links, actual package
resolution, absent optional dependencies, passive bridge imports and the
mgcrea `StdioServerTransport` export. It pins Linux `/usr/bin/node` v22.23.2 to
SHA-256 `3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327`.
`runtime-bytes-verification.json` separately checks the reusable Python live
runtime validator. Neither check starts a bridge or application service.

## Before and after experimental execution

Import `verify_runtime` from `scripts/agentops_bridge_runtime_archive_v1.py`
and pass the runtime path plus graph and materialization objects loaded from
externally sealed inputs. Do not trust only the runtime's own copies. The
function checks exact package bytes, metadata, link targets and complete
file/link enumeration. It is read-only and returns
`status: runtime_bytes_and_links_verified`. Keep experimental state/output
outside this runtime. The Node verifier adds actual dependency-resolution and
passive-import checking when needed, writing to a new output path outside it.

The archive can be regenerated from the same still-pinned installed source with
the new preparer/packer in a new destination; the existing receipts and runtime
must not be overwritten. On Linux, the materializer's exact original-target
guard intentionally prevents accidental replacement. Independent reconstruction
elsewhere requires an explicitly versioned destination change and fresh checks.

## Limits

This graph covers declared runtime dependencies, installed optional
dependencies and installed peers, not arbitrary undeclared dynamic imports.
Passive imports cover the selected entry points; later execution and source
inspection must establish any additional loading behavior. Original byte
integrity, Git HEAD/lock correspondence and installed resolution are distinct
from authenticated capture, build reproducibility and scientific review.
Node's Linux patch version differs from the historical Windows v22.13.0 runs;
the new version is explicit. No novelty or benchmark gate credit follows.
