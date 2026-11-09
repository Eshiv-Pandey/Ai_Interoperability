# Eight-day feasibility and novelty gate

Prepared 2026-10-23 for a finish-before-2026-11-01 target. This is a preparatory recommendation, not an implemented study. Primary sources were inspected online; their reported experiments were not independently reproduced.

## Recommended dependable core

For eight days and no paid API budget, the dependable study core is a differential evaluation of existing MCP-A2A bridges using deterministic agents and real SDK/wire paths. The candidate question is:

> When a bridge passes wire/schema checks, can it still silently change whether a task can be resumed, cancelled, retrieved, or correctly interpreted?

This focuses on externally observable workflow preservation across independent implementations. It differs from HandoffBench's generated boundary-state/receiver experiments and AI-NativeBench's application/framework comparisons. Conformance and bridge fidelity are already established concepts: novelty needs new reproducible findings or demonstrated value in separating schema validity, disclosed loss and recoverable behavior. A new test suite alone is not enough to establish high novelty.

An optional small two-model single-hop experiment can retain the original LLM research aim. Gate it on actual endpoint access and a prespecified meaningful precision target. Use the identical task, frozen upstream artifact, receiver model, tools and budget across raw two-agent and bridged conditions; include same-model controls where the available calls permit. Record it as exploratory if sample size or provider stability is inadequate. Its availability must not determine whether the deterministic core finishes. Do not claim general vendor-product interoperability from two model backends in a shared scaffold.

## Specification correction

[MCP latest](https://modelcontextprotocol.io/specification/2026-07-28) currently includes per-request negotiation and an optional [Tasks extension](https://modelcontextprotocol.io/extensions/tasks/overview) with working/input_required/completed/failed/cancelled statuses, polling, mid-flight input, durable handles and cooperative cancellation. The study must not rely on the stale assertion that MCP has no task lifecycle. Pin the protocol versions actually supported by each bridge and client.

## Practical core matrix

Target two or three independently implemented public bridges, approximately four capability profiles, and 24-40 bounded workflows. This is a scope estimate, not a guarantee; finalize it after installations and the pilot. A deterministic A2A agent is exercised directly as the reference and through each eligible bridge. Never score explicit non-support as if the bridge advertised that feature. Legacy and modern MCP results must be labeled separately.

| Workflow | Observable requirement | Existing coverage and claim limits |
| --- | --- | --- |
| Interrupted authorization versus ordinary input | Preserve the distinction, a usable task handle, safe out-of-band credential flow and autonomous resumption; a caller can finish the original task. | [AmirK-S/a2a-to-mcp](https://raw.githubusercontent.com/AmirK-S/a2a-to-mcp/main/README.md) and [aarushitandon0/a2a-mcp-bridge](https://raw.githubusercontent.com/aarushitandon0/a2a-mcp-bridge/main/README.md) already document state mappings and auth/input differences. Enum differences are known; an undocumented stranded-task or unsafe continuation is a potential empirical finding. |
| Cancellation racing completion | Script both legal orders and observe actual final state, artifacts and errors. Repeated cancellation must not create new side effects where its contract is idempotent. | Both [A2A](https://a2a-protocol.org/latest/specification/) and [MCP Tasks](https://modelcontextprotocol.io/extensions/tasks/overview) describe cooperative cancellation. Work continuing after a cancel request is not automatically a violation. |
| Chunked artifacts and retrieval | Interleave two artifact IDs, append to one and replace another, emit final chunks, and compare exact final identity/content/media type/retrievability. Include long text and structured data. | A2A defines append and lastChunk semantics. Some bridges explicitly disclose preview truncation/non-inlined parts. Known limits are not discoveries; undisclosed mixing, corruption or unavailable promised retrieval may be. |
| Task continuation across capability profiles and restart | Pause, reconnect with Tasks/without Tasks/legacy MCP, and restart only implementations claiming resumability. The original task remains reachable and does not become a second task. | aarushitandon0 already has cross-instance restart/key-rotation tests. Independent-client or capability-negotiation compositions can extend coverage; merely copying its own tests is replication. |
| Duplicate sends after ambiguous timeout (secondary) | A reference server explicitly implements message-ID deduplication. Check whether bridge/client preserves that ID, correctly reports uncertainty and avoids an unintended duplicate side effect. | A2A SendMessage idempotency is optional. This tests an explicit implementation contract; do not claim that A2A universally guarantees exactly-once sending. |
| Discovery versus executable capability (secondary) | Check whether a bridge's exposed MCP tool promises exceed the remote agent's actual calling contract. | [a2a-rust bridge documentation](https://a2a-rust.com/examples/mcp-bridge.html) already explains that A2A skills have no tool-like argument schema or mandatory skill selector. Do not fabricate schema loss where no schema existed. |

Candidate existing implementations inspected:

- [AmirK-S/a2a-to-mcp](https://github.com/AmirK-S/a2a-to-mcp): current and legacy MCP routes; task extension; explicit state/part/error mapping; its README records preserved metadata and deliberate non-support. Apache-2.0 is stated in the README; verify repository license when reusing.
- [aarushitandon0/a2a-mcp-bridge](https://github.com/aarushitandon0/a2a-mcp-bridge): Python modern MCP facade, official A2A types, sealed task handles, explicit auth handling, artifact previews. Verify exact commit/license/installability before inclusion.
- [GongRzhe/A2A-MCP-Server](https://github.com/GongRzhe/A2A-MCP-Server): existing public bridge exposing agent and task operations. Protocol revisions and actual dependency support need an admission check.
- [a2a-rust bridge](https://a2a-rust.com/examples/mcp-bridge.html): documents skill projection, long-running tasks, cooperative cancellation and input-required not bridged; useful comparator if its build is feasible.

No need to use all four. Admission should prefer independent implementations and supported common workflows, not repositories selected because they appear likely to fail.

## Scoped authority is secondary

[A2A section 7.6.4](https://a2a-protocol.org/latest/specification/) states that auth-required is not itself authorization and that credential scope/representation/validity/revocation are defined outside the base protocol. Our invented budget/consent fields would therefore test an application or negotiated extension, not intrinsic A2A semantics. HandoffBench and [Lost in Translation](https://www.teleperson.com/resources/lost-in-translation-cross-protocol-interoperability) already treat scoped authority. Avoid a claim that an author-created authority contract reveals a novel protocol flaw.

## Reporting that adds value

For each workflow report separately:

1. Direct reference workflow succeeds.
2. Bridge emits schema-valid wire messages.
3. Required behavior remains possible through exposed operations.
4. Any lost distinction is explicitly disclosed to the caller.
5. A standard caller can recover and complete the original workflow.

This can distinguish valid transport plus disclosed state plus unavailable continuation from either a JSON-valid check or a generic task-failed score. The semantics of each category must be executable and reviewed independently. Count over the fixed finite suite with feature coverage; do not treat repeated deterministic runs as independent statistical observations or use their error bars to imply a population-wide failure rate. Repetitions are for reproducibility and race schedules, not sample-size inflation.

For optional LLM experiments use paired task-family inference, retain failures and negative effects, and report achieved interval width. If access permits only a small sample, label conclusions exploratory. Set the precision decision before viewing effects; do not keep collecting until significant.

## Deadline gates

| Date | Concrete deliverable and gate |
| --- | --- |
| Oct 23 | Lock narrowed question, prior-art comparison, bridge eligibility, versions and observable success predicates. Confirm at least two independent bridges install. Inventory optional model access. Stop broad implementation if no viable independent comparison. |
| Oct 24 | Direct deterministic reference and six core workflows execute over real SDK/wire paths. Independently review expected behavior. Reject predicates not supported by the pinned specification/bridge contract. Optional model smoke check only after user authorization. |
| Oct 25 | Run the pilot on all admitted bridges. Compare outcomes with their documentation/tests. Go/no-go: require an undocumented reproducible failure or a clear gap revealed by the reporting decomposition beyond existing checks. Otherwise reframe as verified replication/conformance report. Gate optional LLM experiment on actual access, cost ceiling and precision feasibility. |
| Oct 26 | Freeze task suite, predicates, dependency/model manifests, exclusions, planned comparisons and reporting. Add independent validity review. Stop design changes prompted by confirmatory outputs. |
| Oct 27 | Execute the complete frozen deterministic matrix and any admitted model matrix. Retain passes, explicit unsupported cases, unexpected failures and environment failures. |
| Oct 28 | Reproduce strongest witnesses in a clean environment; minimize traces and validate a second client/implementation when feasible. Assess achieved optional-model precision without promoting exploratory findings. |
| Oct 29-30 | Generate tables from retained traces; write short paper, related work and limitations; audit every factual claim/source/result. Release scope and venue choice depend on actual evidence. |
| Oct 31 | Final reproduction, source/result integrity and artifact-paper consistency review. Deliver code, trace corpus, analysis and complete manuscript draft before Nov 1. |

## Primary prior art to acknowledge

- [HandoffBench manuscript](https://raw.githubusercontent.com/kexinchu/HandoffBench-AAAI/master/paper/main.tex): evaluator-private atomic state, fixed receiver oracle comparison, deterministic action and representation factorial. Public draft, not established AAAI acceptance.
- [AI-NativeBench](https://arxiv.org/html/2601.09393v1): native/framework/MCP/A2A/H-A2A application comparisons, distributed traces, tool fidelity, outcomes, latency and token economics.
- [ProtocolBench v3](https://arxiv.org/html/2510.17149v3): native adapter comparisons, cross-protocol router and round-trip/streaming/lifecycle/error conformance checks; MCP out of scope.
- [Facts Without Rules](https://arxiv.org/html/2608.29028v1): facts versus boundary constraints, handoff representations and no-handoff controls.
- [Model Switching](https://arxiv.org/html/2603.03111v1): ordered cross-provider handoff vs same-receiver no-switch baseline, paired bootstrap.
- [The Handoff Tax](https://arxiv.org/html/2608.24358v1): handoff direction/timing/interface with fixed scaffold and executable success/cost.
- [Lost in Translation](https://www.teleperson.com/resources/lost-in-translation-cross-protocol-interoperability): formal project white paper covering state aliasing, authority distortion, capability loss, fault masking and asynchrony mismatch. It explicitly makes no empirical claims.

## Honest delivery boundary

This plan can plausibly deliver a complete, reviewable artifact and manuscript by Oct 31 after approval. It cannot guarantee a novel finding, adequate evidence for a broad cross-vendor LLM benchmark, conference acceptance, or publication before Nov 1. If the pilot yields only known documented limits, publishability must be reassessed and the deliverable presented as a verified replication/conformance study rather than a highly novel benchmark.
