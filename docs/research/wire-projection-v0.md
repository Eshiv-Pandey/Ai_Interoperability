# Historical wire projection v0

Prepared 2026-10-24 before the new observation captures. This interface validates **recorded development executions**, not prospective continuation admission, model completeness, protocol conformance, natural-defect prevalence or a novel method. Probe-only evidence remains incomplete. Full application runtime/gold separation and human review remain open.

## Input boundary

Public/runtime input `runtime-wire-observation/1` contains `run_id`, `route_id`, pinned `source_commit`, `protocol`, `exchanges`, outcome and provenance. Each exchange has a unique `exchange_id`, phase, `request` (exact raw MCP JSON, parsed `json`, `started_at_utc`), `response` (exact raw MCP JSON, parsed `json`, `observed_at_utc`, SHA-256 over UTF-8 raw bytes), and measured elapsed time. HTTP status/headers and notification records may additionally be present. The projector uses successful request/reply pairs with matching JSON-RPC IDs; unpaired/error/notification records remain in source evidence but cannot become successful transitions.

Raw MCP handles and IDs are ordinarily visible and remain runtime-visible. Raw native HTTP traffic is a **separate evaluator-private sidecar**. Native IDs already present in an MCP reply (mgcrea) are ordinary evidence; a native ID learned only through the sidecar (opaque AmirK-S handles) must not be inserted into the runtime model. The independent checker can inspect both sides without passing private IDs/future answers to the projector or candidate.

Validate raw/parsed agreement, SHA-256, unique exchange/request IDs, chronological serial request/reply intervals and JSON-RPC correlation. Do not silently pair a response to a different request, merge separate executions, or invent an ordering during overlapping calls. JSON duplicate keys are invalid. Raw HTTP bytes and raw MCP bytes have separate namespaces; an A2A error is not an MCP error.

## Public events and contract

Root owns `interoperability.wire_projection.project_trace(trace, expected_artifact_text)`. It returns `observed-trace-projection/0`, a source canonical digest, explicit configuration, event provenance, analysis clock and a finite v1 manifest. Independent review owns `interoperability.projection_checker.check_projection(trace, projection)` and must not import projector extraction/transition logic.

Supported public formats are pinned explicitly:

- AmirK-S ordinary tool envelope: `structuredContent.kind='task'`, `taskHandle`, `contextHandle`, `status`/`a2aState`, artifact refs plus receiver-visible artifact text blocks labelled with the artifact ID. Modern `tasks/get` can expose a task ID/status/input request; `tasks/update` may be an acknowledgement. Preserve those different evidentiary meanings.
- mgcrea: tool text contains JSON, or equivalent structured content; send can contain `task` summary, get contains native public `id`, `context_id`, state, artifacts and history. Artifacts, rather than history or acknowledgement text, establish delivery of the configured output.

An acknowledgement cannot imply completed/canceled state. A get operation observes asynchronous advancement; it does not itself cause that advancement. Local-mirror reads and authoritative peer reads are tagged separately from the actual request/configuration and separately retained native evidence. Absence of a queried principal, lease or access grant remains missing, not an invented default.

Modern MCP task `completed` means result delivery finished. In the pinned source, a failed/rejected/auth-required A2A result can legitimately appear inside that completed delivery with a nested failed/error envelope. Use the disclosed ordinary task status for the logical completion goal; outer completed alone is unknown. V0 rejects nested error records pending a separately specified recovery projection. This is a documented semantic distinction, not an adapter contradiction or newly discovered defect.

The historical runtime contract asks whether the recorded sequence produces the expected artifact while returning the original public task/context references. Initial expected references come from the first complete ordinary task view available in the runtime prefix, not private native traffic. Project from that view onward; the omitted setup prefix remains linked source evidence.

Every modeled state is one actual paired response, with a run/exchange-specific ID. A transition is the next serialized **observational macrostep**: the actual intervening request and returned response, including any explicitly recorded asynchronous advancement. No transition is extrapolated to an unobserved action, other execution or future branch. Mandatory request-target validity is an invariant; actual returned task/context equality and artifact delivery are goal predicates. Missing returned state/reference/artifact evidence stays indeterminate. An omitted field is not automatically false.

After the selected initial view, a task-related operation must explicitly target the original task; a missing target is an invalid continuation request. The initial ordinary send may establish its task without a target. V0 refuses task-error sequences rather than silently removing attempted calls from the horizon; those raw records remain in evidence for a future declared recovery model.

V0 likewise rejects a cancellation action after the selected task prefix. Cancellation needs its own declared goal/state projection; silently skipping it would invent a continuation through an unmodeled task mutation. Read-only discovery/setup observations remain in full source evidence and request-cost accounting; the finite horizon counts the selected task-observation macrosteps.

The task/context namespace is explicit (`bridge-handle` or `public-native-a2a-id`); comparing bare strings from different namespaces is invalid. The first task view and subsequent response references must be compared in the same route/execution. Do not mask a changed reference by assigning every reply the alias `task-1`.

## Historical analysis clock and limits

Set finite `evidence.complete=False`. Analyze at a **single fixed archival record clock** after the final captured response, with `observed_at=valid_until=analysis_clock`. This zero-width interval validates the immutable historical observation model only; it is not a service lease, task freshness guarantee or invented TTL. Re-evaluation at a later clock returns unknown. Actual observation times remain in event metadata.

The horizon counts observed request/reply macrosteps from the selected prefix, not hidden agent actions or abstract state changes. All graph states/edges are backed by exact source exchange IDs and response hashes. The baseline and independent finite oracle evaluate the identical runtime manifest; all conclusive certificates are checked. A successful recorded path is an existence witness under its explicit historical abstraction, never a claim that the gate predicted success before the answer was sent.

## Required validation

Check each captured route's pending view, answer acknowledgement, local/authoritative reads and final artifact against raw MCP bytes; independently correlate private native traffic for same underlying task/context when available. The final artifact must carry the actual supplied answer and preserve the intended task. Keep local stale observations as observations, not fabricated failures.

Controlled test derivatives are labelled **projection mutations**, not natural bridge bugs: wrong response ID, altered raw/parsed data or hash, substituted public task/context reference, omitted required observable, changed namespace, history text substituted for artifact, removed continuation and attempted cross-run merge. Invalid byte/correlation evidence is rejected; insufficient observations produce unknown. A partial trace cannot justify unsupported, and a bare answer/cancel acknowledgement cannot satisfy the ordinary completion goal.

This checks the wire-to-model foundation only. Prospective evidence-query planning still needs actual source-derived query bundles, justified completeness/freshness assumptions, strong same-evidence comparators and a defensible new contribution. The current one-query plain-text continuation fragment does not by itself promise a query advantage.
