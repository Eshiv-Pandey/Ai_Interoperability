# Additional source screen: a2acode v0.8.0

Screened **24 October 2026**. This lead is separate from the closed official
sample screen. Its release points to commit
`edddb318a4dcf9a424672cdac79cb3d52fac9021`.

**Decision:** eligible to investigate as an upstream-authored offline permission
control; **not selected as a substantive second application domain or C1 method
advantage**. No source checkout, dependency installation, model inference or
native/bridge trial for this application has occurred in this screen.

The [release](https://github.com/kanywst/a2acode/releases/tag/v0.8.0) identifies
the pin. Its [license](https://raw.githubusercontent.com/kanywst/a2acode/edddb318a4dcf9a424672cdac79cb3d52fac9021/LICENSE)
is Apache-2.0. The inspected
[README](https://raw.githubusercontent.com/kanywst/a2acode/edddb318a4dcf9a424672cdac79cb3d52fac9021/README.md)
documents the local echo backend, explicitly for wiring checks/tests.

The original [echo backend](https://raw.githubusercontent.com/kanywst/a2acode/edddb318a4dcf9a424672cdac79cb3d52fac9021/src/a2acode/backends/echo.py)
pauses for permission when input contains `sudo`, then echoes the input or
reports denial. It executes no command and calls no model. It emits neither
structured question gates nor successive permission requests. Adding those
would create authored control behavior and cannot establish a natural defect.

The shared [executor](https://raw.githubusercontent.com/kanywst/a2acode/edddb318a4dcf9a424672cdac79cb3d52fac9021/src/a2acode/executor.py)
publishes request metadata and rejects a **supplied mismatching** request ID.
Absence of that metadata is allowed and falls back to duplicate-message
checking. Therefore metadata omission alone does not establish typed echo
non-support: plain `allow` can be a source-valid answer. A candidate cannot
invent mandatory binding or deny the comparator this permitted text path.

A separate AI source assessment found that the pinned project advertises modern
and legacy JSONRPC/HTTP+JSON interfaces and resolves Python A2A SDK 1.1.2.
Full pinned source checkout, byte-level source manifests and local runtime
compatibility are still unverified. The saved retrievals are **tool-formatted
primary-page excerpts**, not full original source bytes or an installed runtime.
The unsuccessful initial GitHub tree retrieval is preserved in 01-tool-response.
The direct tag excerpts and later commit-pinned source/license/release retrievals
remain distinct. No independent human review is implied.

If this control becomes useful for a specified fidelity question, first acquire
the complete licensed pinned source and dependencies and freeze native controls
for correct, incorrect and absent request IDs. The predicted outcomes are
completion, continued waiting and completion; none is an observed result here.
Its demonstration scope and all permitted raw/text alternatives must remain
explicit. Running another familiar guard alone would not supply C1 novelty.

Exact guarded reachability already models these dependencies. Existing
CONTINUITY/PC2-informed binding and replay checks remain fair comparators.
The screen yields **no demonstrated new algorithm or scientific gate credit**.
Continue the full method research by identifying a concrete technical distinction
and a genuinely discriminating source case before scaling. CP2 remains open;
verified project progress remains **5%**.
