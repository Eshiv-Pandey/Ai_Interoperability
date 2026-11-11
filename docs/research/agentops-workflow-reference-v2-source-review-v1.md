# Independent AgentOps Workflow V2 source review, V1

Status: corrections required before dispatch. This AI source and constructed review imports no original SDK or application and makes no provider calls.

The reviewed worker hash is `8443cb109e1345f6ead2f8d2008a1532dd199d7fd05ba8886dc17c6e66cc4336`; the reviewed V2 analyzer hash is `9d81fe9bad9d544b55536d4f7c21f04c36edc09ccaf62c2cc0961724631fff20`. The original source remains pinned to `c806b7f1cd0042c9817c0a4c46d80a9a95a24293`, and the retained ADK 2.10.0 wheel and eight diagnosis source members match their exact declared hashes. Four further wheel members were independently read to verify model-call bypass, invocation enrichment and official confirmation fields. Their hashes are in the JSON.

The worker string-indexes `selected.graph.nodes` at lines 169 and 219. Pinned ADK declares this field as a list. Evaluating the actual source AST expressions against a constructed list shape raises `TypeError: list indices must be integers or slices, not str` at both sites. The SDK resolves a node by iterating the list and matching its name. V2 needs one validated name map for preflight and the actual compiled-agent observer.

The independent analyzer peer retained a positive two-case baseline and 14 separate invalid mutations that were also accepted with zero questions. The mutations cover overlapping stage lifecycles, mismatched callback/stage/raw invocation IDs, a terminal before its matching raw call, four alternate denied socket operations, failed worker/data-invariance receipt, governed/exported model disagreement, an SDK error message without code, and raw requested tool confirmation. Exact mutations and replay source are in [the peer review](agentops-workflow-reference-v2-analyzer-peer-review-v1.md). Corrections belong in V2; V1 and its failed actual run must remain preserved.

Pinned source establishes the required order: original policy, owned before-model fixture, observer. A non-None fixture response is yielded and the model-call routine returns before backend lookup. Original after-tool policy can skip the observer, so raw official function responses remain terminal authority. BaseAgent and Context copies preserve invocation ID, and NodeRunner writes that same ID to raw events. For this fresh one-turn allocation, stage entries/exits, fixture callbacks, tool contexts and raw events must share one nonempty actual invocation ID.

The existing 39 constructed checks and the 421-source-file input check passed independently before corrections. Those checks do not exercise the faulty worker node lookup and do not reject the peer's 14 mutations. Fresh post-correction controls and review remain required.

This review proves source contracts and constructed failures only. It does not establish original application success, live-model behavior, A2A support, human gold or final scientific qualification.
