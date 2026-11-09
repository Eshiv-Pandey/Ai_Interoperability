# Design review: handoff interoperability benchmark

Prepared 2026-10-23. Preparatory research and workflow only; no implementation or live API experiments authorized yet.

## Verified protocol facts

- Official MCP versioning lists 2026-07-28 as current. Its architecture page explicitly describes the **protocol requests** as stateless and self-contained, with per-request version/capability metadata. This does not mean all MCP implementations, host conversations, tools, or application workflows are stateless. Earlier 2025-11-25 architecture explicitly describes a stateful session protocol; implementations may still support that revision. Pin and report the negotiated revision rather than treating lifecycle properties as timeless.
  - https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning
  - https://modelcontextprotocol.io/specification/2026-07-28/architecture
  - https://modelcontextprotocol.io/specification/2025-11-25/architecture
- Official A2A released version is 1.0.0. Discovery, task lifecycle, multimodal messages, streaming/asynchronous interactions and opaque execution are supported.
  - https://a2a-protocol.org/v1.0.0/specification/
- MCP and A2A serve complementary roles: tool/resource access and delegation between independent agents. An A2A agent may use MCP internally. MCP delegation should be described as an explicit agent-as-tool wrapper implementation, not universal native agent-to-agent coordination.
  - https://a2a-protocol.org/v1.0.0/topics/a2a-and-mcp/
- MCP tools have input JSON Schema and optional output schema. A2A AgentSkill is largely descriptive (abilities, examples, media modes, security), not a universal typed tool schema. Capability preservation needs a benchmark-level capability/task contract and functional invocation probes.
  - https://modelcontextprotocol.io/specification/2026-07-28/server/tools
  - A2A specification section 4.4.5 at the URL above.
- A2A already has protocol conformance and interoperability tooling. TCK validates implementations across gRPC, JSON-RPC and HTTP+JSON. ITK checks cross-SDK/version interoperability by sending nested instructions through multi-hop agents and checking returned traces. Therefore claims that nothing measures interoperability or vendor specs provide no measurement are too broad. Distinguish these checks from LLM semantic/behavioral task preservation.
  - https://github.com/a2aproject/a2a-tck
  - https://github.com/a2aproject/a2a-itk

SDK source note, not a recommendation to install before approval: official release pages currently list MCP Python SDK v2.3.0 (released October 2) and A2A Python SDK v1.2.3 (released October 19, changelog dated 2026-10-17). Verify required optional features and lock versions at implementation time.

- https://github.com/modelcontextprotocol/python-sdk/releases
- https://github.com/a2aproject/a2a-python/releases
- https://github.com/a2aproject/a2a-samples

## Controlled comparison and causal limits

Primary comparison: the **same task, same pre-boundary packet, same receiving model, same tools, reset state and budget**, delivered through direct in-process execution, Raw HTTP/JSON handoff, A2A handoff, and MCP delegate-task wrapper / explicitly defined MCP-to-A2A bridge.

Direct in-process versus Raw isolates networking overhead. Raw versus A2A tests a particular adapter/lifecycle implementation. MCP wrapper versus bridge tests that wrapper. Keep downstream MCP tool access constant where possible. A full-context single-agent baseline is useful as a deployment utility reference but cannot by itself identify interoperability loss: decomposition, context availability, model calls and budget also change.

Use three manageable studies rather than a giant initial factorial:

1. Transport/adapter study with a scripted sender or frozen natural sender packet and the same receiving model across paths.
2. Representation study comparing full context, natural summary and structured semantic contract under declared equal token budgets; report actual sizes.
3. Heterogeneity study with ordered same-model and different-model sender/receiver pairs under a fixed runtime and transport. When agents are our wrappers around model APIs, describe model-provider heterogeneity rather than claiming vendor-supplied autonomous agents were tested.

Capture original context, sender output, adapter-decoded/model-visible receiver input, and receiver actions/final state. Separately measure sender summarization loss, adapter loss, and receiver failure to use preserved information. If model-visible inputs and tools are identical, nonzero task differences need explanation involving lifecycle/state, rendering, capability exposure or API noise. Deliberate fault injection validates diagnosis/recovery; it is not evidence that real protocols inherently lose meaning. Retain zero loss and gains as valid findings.

## Metrics to freeze before confirmatory evaluation

The proposal and presentation disagree on metric scope and objective versus LLM judging. Define constructs before choosing acronyms or forcing six measures.

- Task success: execution or reset-environment goal-state oracle. Check forbidden intermediate actions as well as final state.
- Fact fidelity: structured fact/value preservation at each checkpoint. Use semantic rubrics only when the content genuinely requires linguistic evaluation.
- Constraint preservation: scope, conditions, precedence, units, validity, permissions. Separate transmitted rule preservation from behavioral compliance.
- Capability preservation: permitted skills/tools remain discoverable and functionally usable with valid inputs. Record false advertisements, mapping limitations and authorization changes.
- Tool fidelity: correct tool identity, arguments/types, outputs and relevant action/state sequence.
- Efficiency: wall-clock latency, bytes/messages, tokens, API cost. Separate setup/cold and steady-state execution.
- Recovery: success, additional cost/time, clarification and duplicate-action prevention under specified faults.

Primary effect: signed difference in task success in percentage points, averaged over paired tasks. Do not clip negative values (gains). Relative loss is secondary and needs baseline performance and a zero-baseline rule. Direct-success-conditioned loss is a secondary diagnostic, not the sole headline.

## Initial task scope

Three locally simulated resettable workflow families:

1. Constrained purchase/travel scheduling: budgets, units, availability, mandatory versus preferred requirements, approval conditions.
2. Data analysis/reporting: provenance, date validity, aggregation rules, uncertainty, prohibited inferences and evidence references.
3. Service operations: permissions, tool selection, argument schemas, idempotency, conditional state updates and recovery.

Ground scenarios in realistic workflows, generate independent instances and obtain human validity review. Include distractors, conflicting constraints, irrelevant facts, schema variation and one versus multiple handoffs. Avoid a task set that merely tests copying JSON. Start with synthetic data/local state; no live purchases or production changes.

Timestamps alone do not establish contamination resistance. Separate development tasks from sealed evaluation families/instances, refresh instances, track provenance/release dates, exclude pilot instances from confirmation and acknowledge generator/template exposure.

## Stages and gates

| Stage | Deliverables | Advance only when |
| --- | --- | --- |
| 0. Evidence and novelty audit | Verified bibliography, claim ledger, closest-work comparison, bounded contribution statement | Unsupported first claims removed; distinguish prior handoff studies and A2A tooling |
| 1. Freeze specification | RQs/hypotheses, task contract, metrics, primary contrast, task distribution, analysis plan | Team/supervisor review; estimands and limits declared |
| 2. Offline harness | Python CLI, provider interface, adapters, trace schema, resettable tools and deterministic agents | Packets round-trip unchanged; oracles/fault tests pass; relevant conformance checks pass |
| 3. Task/scorer validation | Three families, development set, holdout strategy, known correct/incorrect traces | Human validity review; missing rules/forbidden actions detected; floor/ceiling effects acceptable |
| 4. Limited pilot | Small model/path matrix, cost/latency observations and paired variance | Endpoint feasibility and budget established; sample size selected; prompts/scorers frozen |
| 5. Confirmatory experiments | Versioned configs, randomized/block-interleaved runs, repeated trials, sealed holdout, ablations | No silent reruns/exclusions; failures retained under declared rules |
| 6. Independent verification | Paired CIs, robustness checks, blinded trace audit, clean-environment/second-operator reproduction | Headline findings regenerate from evidence |
| 7. Paper/artifact | Complete paper, limitations, documentation, reproducible figures, licenses and venue fit | Team/supervisor author review and explicit approval before public upload/submission |

Implementation begins only after workflow approval. Start offline. Paid API work requires a declared spending cap before execution; publication/submission requires concrete artifact approval. No issue or PR is needed for this planning stage. If one is prepared later, follow the user's local contribution rules.

## Statistics, budget and calendar

A pilot of approximately 30-60 development instances with 3-5 repetitions in a limited matrix is an engineering/variance pilot, not publication-grade evidence. Choose confirmatory counts using a minimum relevant effect and measured paired variance. At 80% power and 5% two-sided significance, a rough independent-task calculation is:

`n ~= (1.96 + 0.84)^2 * Var(task-level paired differences) / effect^2`

Adjust for shared scenario/template clusters. Repeated trials estimate stochastic behavior; related generated variants are not automatically independent tasks. Predeclare primary contrasts, multiplicity, confidence interval method, retries/exclusions and practical equivalence margin. Lack of statistical significance is not equivalence. Declare pass@k and pass^k carefully; they answer different questions.

- Paired task differences, clustered errors and prospective power: https://arxiv.org/html/2411.00640v1
- Cost, holdouts and reproducibility: https://arxiv.org/abs/2407.01502
- Goal-state grading and repeated-trial reliability: https://arxiv.org/abs/2406.12045

Estimate spend from `instances * conditions * repeats * observed mean per-episode cost`, adding sender generation, judges if any, pilot and declared contingency. Three providers/nine ordered pairs/four paths/three encodings already produces a large matrix; narrow primary comparisons and separate secondary ablations.

The proposal's one-year scope conflicts with the presentation's December 13, 2026 milestone. Roughly seven weeks remain from the environment date. A verified specification, functioning harness, validated initial tasks and pilot may be achievable; a completed defensible conference study depends on sample requirements, budget and team availability. Confirm whether December 13 is a prototype deadline or final research deadline.

Suggested approval inputs: endorse staged research-first workflow; clarify milestone and team effort; specify API access/spending ceiling. Novelty and conference acceptance cannot be promised in advance. They are evaluated through literature, evidence and review.

## Access and accelerated deadline update (2026-10-23)

The user subsequently tightened the deadline to the complete project, experimental study and paper draft **before November 1, 2026**, replacing the original calendar assumptions. They report Sol 6.1/5.6 access and free GLM 5.3 Flash / DeepSeek V4.1 Flash through an OpenCode extension. Root is independently auditing the OpenAI access claim. No credentials, local auth configurations or model-inference endpoints were used during this review.

### Verified free-model identities and provider distinctions

- OpenRouter's official model page lists `z-ai/glm-5.3-flash:free` with zero prompt/completion price. This is distinct from the paid `z-ai/glm-5.3-flash` and `glm-5.3-flashx` variants.
  - https://openrouter.ai/z-ai/glm-5.3-flash:free
- OpenRouter's official page verifies the paid `deepseek/deepseek-v4.1-flash-1017`, explicitly the October 17 snapshot. The `deepseek/deepseek-v4.1-flash:free` page was not accessible via the web tool. This does not prove no free endpoint exists, but no V4.1 free OpenRouter access was established. Older `deepseek/deepseek-v4-flash-0731:free` is a different model.
  - https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017
  - https://openrouter.ai/deepseek/deepseek-v4-flash-0731:free
- **OpenCode Console** (formerly Zen) official current model documentation lists both `glm-5.3-flash-free` and `deepseek-v4.1-flash-free`, with zero token prices and temporary availability. Its docs describe zero retention/no model training for these two specific free models. Other free models have different retention/training policies.
  - https://opencode.ai/v2/docs/console/models/
- Read-only live public catalog GET on https://opencode.ai/inference/v1/models returned both exact free IDs. This confirms advertised catalog presence as of this review, not successful inference or sustained capacity.
- OpenCode Console's official Inference API docs list `https://opencode.ai/inference/openai/v1/chat/completions` for these free chat models and explicitly state free chat models can be called without authentication; paid models require a Console personal/service-account key. The extension therefore need not be treated as the only possible access route. No credential extraction is necessary for a documented unauthenticated free route.
  - https://opencode.ai/v2/docs/console/api/inference/
- OpenCode and OpenRouter are separate provider integrations. The official OpenCode provider guide tells users to connect an OpenRouter key separately. An extension displaying a model name does not establish which endpoint or price is used.
  - https://opencode.ai/docs/providers/
- OpenCode supports programmatic CLI runs and JSON session export, but evaluating through its coding-agent runtime adds agent prompts/tools/compaction/session behavior. Use that only when the OpenCode runtime is intentionally the system under test; otherwise use the verified direct inference route after approval and permitted-use checks.
  - https://opencode.ai/docs/cli/
  - https://opencode.ai/v2/docs/models

### Limits and reliable automation

- OpenRouter official pricing states free models are limited to **20 requests/minute and 50 requests/day**, increasing to **1,000/day after at least $10 lifetime credits purchased**. Failed attempts count. Limits apply globally; creating extra accounts/keys is not a workaround. A free model is free inference, not guaranteed availability or unlimited benchmark traffic.
  - https://openrouter.ai/pricing
  - https://openrouter.ai/docs/api_reference/limits
- OpenCode member `neriousy` stated on October 21 in the official repository issue that free limits deliberately change with available capacity and the service does not publish a fixed number. The exact experimental throughput is therefore unresolved. Reports/bot responses in another official-repository issue document gateway restrictions and false positives, including an "only within OpenCode" message in official clients; this is operational evidence, not a normative policy statement overriding the direct-API docs.
  - https://github.com/anomalyco/opencode/issues/55816
  - https://github.com/anomalyco/opencode/issues/56822
- OpenCode Go is a separate **paid subscription**, not the free route. Its guide expects typical coding-agent traffic, a truthful client user agent and stable session identifier. Do not assume a general benchmark workload fits that plan or disguise traffic to gain access.
  - https://opencode.ai/v2/docs/console/go/
- OpenRouter supports provider selection, requiring parameters, disabling fallback and zero-data-retention selection, but capabilities/plan eligibility must be checked for the actual account/endpoint. Without provider pinning and logging, provider load balancing can confound latency and model behavior.
  - https://openrouter.ai/docs/guides/routing/provider-selection
  - https://openrouter.ai/docs/guides/features/zdr

### Access gate before experiments

1. Obtain the exact nonsecret provider/model selection from the user or permitted model inventory, without reading stored auth files. Distinguish an API key from subscription/OAuth access and distinguish OpenRouter from OpenCode Console.
2. Freeze a no-cost allowlist of exact free IDs; no automatic fallback to paid IDs, no auxiliary paid web/search tools and no silent promotion change. If paid access is needed, require a numeric spending ceiling first.
3. After workflow approval, run a very small bounded free connectivity/tool-schema pilot using documented endpoints and truthful client identification. Record status, returned model identifier, tool support, token accounting, rate-limit/error behavior, latency and actual billable cost. Public catalog presence alone is not this gate.
4. Establish a permitted automation route and capacity sufficient for the predeclared matrix. Honor rate limits; never spoof OpenCode headers, rotate identities or bypass gateway restrictions. If a documented endpoint rejects research traffic, use an authorized alternative or rescope.
5. Save exact model IDs, timestamps, public metadata, request parameters, raw request/response payloads, environment and adapter versions. Avoid `latest`, auto routers and mixed fallback models in a confirmatory condition. OpenCode free IDs do not expose dated immutable snapshots in the inspected catalog, so report mutable hosted-endpoint reproducibility limits rather than promising exact reproduction.

### Before-November-1 implications

There are approximately eight remaining calendar days. OpenRouter's standard zero-spend limit offers at most roughly 400 calls over eight days, less existing use and failed calls. Multi-call agents and paired paths/repeats can reduce this to only tens of task instances. OpenCode's temporary dynamic free capacity cannot be relied upon for a complete larger study without passing the access gate.

The accelerated plan should narrow to a **completed bounded study**: two clearly identified model providers, one fixed agent runtime, one handoff, two core paths (raw/direct packet delivery versus native A2A) and one explicitly defined MCP wrapper/bridge ablation if validated early; two task families, deterministic state grading, preservation/use separation and one predeclared primary paired comparison. Extensive cross-framework/protocol coverage and multi-hop generalization should be deferred or honestly excluded from the contribution. A paper draft and verified artifact can be scheduled by October 31; a claim of broad, highly novel, fully verified conference readiness cannot be guaranteed under these unresolved access and power constraints.

Front-load literature and specification plus access on October 23-24; validate the offline harness/tasks on October 24-26; freeze the design after a bounded pilot on October 26; run the sealed evaluation October 27-29 only if gates pass; independently audit/reproduce and finish the paper/artifact October 30-31. The actual number of confirmatory tasks must follow pilot precision/capacity, not an arbitrary deadline. If insufficient evidence is obtained, label the result a pilot rather than using a completed paper draft to imply a completed defensible experimental claim.
