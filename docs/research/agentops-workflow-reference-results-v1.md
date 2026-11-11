# Original AgentOps Workflow reference V1: retained binding failure

The actual 11 November 2026 allocation did not complete either read-only task.
Both original candidate IDs remain in the denominator. Official stage entry and
exit observations alone do not establish completed task obligations.

The retained GitHub run is `43036777469`, attempt 1, at research head
`aada0365b1fe2fd270e254dba56ebc3fa68b02e7`. Its archive has 25,115,647 bytes,
151 extracted files and SHA-256
`83632c16b0f58598aff659bccf48374f73104c64a1558aee0ac7d8c1b9989e70`, matching
the GitHub artifact digest. Evidence is retained under
`runs/agentops-workflow-reference-development/v1/retained-43036777469-1/`.

| Actual case | Ordered stage entries/exits | Owned fixture responses | Tool calls | Raw events | Denied loopback connects | Task obligation |
|---|---|---:|---:|---|---:|---|
| `agentops-h09-workflow-select-target` | All four stages | 0 | 0 | Four `MODEL_UNAVAILABLE` | 12 | Unrealized |
| `agentops-h10-workflow-override-conflict` | All four stages | 0 | 0 | Four `MODEL_UNAVAILABLE` | 12 | Unrealized |

Each worker entered and exited `plan`, `investigate`, `evidence_review` and
`recommend`, returned from the official Runner and closed it. Each emitted zero
owned model-journal records and zero observed tool calls. Every raw event was
`MODEL_UNAVAILABLE`, for eight error events across the original two-case
denominator. Complete before/after `incidents.db` rows and the copied inputs
were unchanged. Each private-evaluator audit probe was denied. No action, note,
source-derived selection or final recommendation was observed.

The actual denial records identify twelve attempted `socket.connect` operations
per case to `127.0.0.1:11434`. These were rejected before the socket operation.
Actual worker stderr shows the original OpenAI-compatible implementation at
`google/adk/integrations/openai/_openai_llm.py:499`. V1 assigned deterministic
models to the exported node objects, but those assignments did not bind the
models used by the compiled Workflow. This is an owned fixture-binding failure;
it does not establish an external Gemini or OpenAI service outage.

The historical worker receipt's `official_original_workflow_observed` status
describes returned execution and cleanup. The retained analyzer correctly
reports `retained_development_workflow_partial_or_inconsistent`, with four
questions: missing per-stage owned model census and missing final recommendation
in each case. A green GitHub workflow conclusion is transport/orchestration
status and does not override those individual scientific outcomes.

The source-diagnosis allocation separately acquired the exact locked
`google-adk` 2.10.0 wheel without importing the SDK or running an application.
The wheel has 4,792,014 bytes and SHA-256
`7550fecbb428a8a6de15ab88ba3c1d4704c752fe0b5594dc6d67ff440f370886`.
Its plugin-manager source exactly matches the actual V1 installed source:
14,341 bytes, SHA-256
`857e523348b777ea4d076f0165d8be1b2b47b233e5ada19c292f26bb1df10f7b`.
The acquisition and selected sources are retained under
`runs/agentops-workflow-reference-development/v1/pinned-sdk-source-diagnosis-v1/`.

V1 source, archives, denominator and outcomes are preserved. A separately
versioned prospective fixture binding may address this engineering failure;
constructed software checks or a future successful attempt cannot rewrite V1.
The current reference remains direct official ADK with author-exposed tasks. It
does not qualify original A2A, provider model quality, human gold, independent
holdout or the full three-path study.
