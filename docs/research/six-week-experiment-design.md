# 45-day experiment design: continuation compatibility in heterogeneous agent interoperability

**Historical allocation — superseded by the student-budget revision.** The user can arrange approximately 1M tokens each for Astra/Sol, with Opus conditional. Use [the current main workflow](../../RESEARCH_WORKFLOW.md) and [student-budget experiment design](student-budget-experiment-design.md) for current scope/counts. The four-family, three-domain, 12,384-execution allocation and staffing below remain prior design analysis, not a current commitment.

Prepared 2026-10-23. Planning document only: implementation and inference experiments await workflow approval. The working horizon is 45 calendar days, approximately October 23–December 6, 2026; Day 1 is the first approved execution day, so later approval shifts the calendar. This design supersedes the earlier eight-day scope and free-endpoint planning assumptions in `design-review.md`; it does not certify novelty or guarantee conference acceptance.

## 1. Contribution to pursue

Pursue a **compositional continuation-compatibility gate**, evaluated on actual MCP/A2A paths and live heterogeneous LLM workflows. The gate maps a workflow's required observable operations through an adapter chain, distinguishes supported/unsupported/unknown continuations, and supplies a small auditable witness. Executable preservation contracts support that decision. Permitted schema mapping, evidence materialization, clarification or allowed native fallback are means of resolving compatibility; generic boundary repair is not the novelty claim. The benchmark and artifact support the method; measuring another handoff success matrix alone is unlikely to establish a substantial new contribution.

The candidate claim is deliberately bounded: a common contract can detect and localize specified state, capability and lifecycle incompatibilities before continuation; composing compatible checked mappings preserves the declared properties under explicit assumptions; a runtime-visible gate supplies useful compatibility decisions and improves the behavior/coverage trade-off on previously unseen evaluation workflows. No overall superiority is presumed, and eligibility does not establish that an LLM will successfully execute an eligible workflow. None of these claims is established before experiments and comparison with closest work.

The distinction requiring proof is **operation-level continuation eligibility across composed real protocol mappings, repairable versus unrepresentable requirements, non-oracle negotiation and downstream heterogeneous-agent validation**. Formal properties, information contracts, handoff-state benchmarks and MCP/A2A system benchmarks already exist. [BRIDGE](https://arxiv.org/html/2610.17805v1), posted October 13, 2026, is particularly close: selective boundary repair, provenance/dependency evidence, calibrated counterfactual continuations and checked execution substantially overlap broad contract-and-repair ideas. [AgentAsk](https://aclanthology.org/2026.acl-long.1294/) already addresses minimal edge clarification and capability gaps; [PACT](https://arxiv.org/abs/2606.05304) already transmits compact public action-state records. These must be named and compared, not treated as missing research.

Also compare directly against [Formalizing the Safety, Security, and Functional Properties of Agentic AI Systems](https://arxiv.org/abs/2510.14133), [AI-NativeBench](https://arxiv.org/html/2601.09393v1), [Facts Without Rules](https://arxiv.org/html/2608.29028v1), the [public HandoffBench manuscript/repository](https://github.com/kexinchu/HandoffBench-AAAI), [Precept](https://raw.githubusercontent.com/gianpremrajaram/precept/main/README.md), [CORDspec](https://cordspec.org/transport-bindings), and the [Lost in Translation white paper](https://www.teleperson.com/resources/lost-in-translation-cross-protocol-interoperability). Publication and validation status differ across these sources. See `related-work.md` for the audited scope and status distinctions. Novelty will require an externally grounded incompatibility or validated diagnostic value beyond those systems; adding protocols/vendors to an existing repair gate is insufficient by itself.

[AgentThread: Formal Security Analysis of Agent Protocol Composition](https://arxiv.org/html/2606.28690v1), a June 27, 2026 preprint, is another mandatory comparator. It already connects source-linked protocol requirements, typed intermediate representations, TLA+ composition checks and counterexample replay against real SDKs/reference servers. Its author-reported composition-only failures make first bounded composition verification or first executable protocol counterexample claims untenable. Our candidate difference is task-relative continuation admission/refusal and calibration against an independent reachability oracle with live heterogeneous-agent consequences. That difference needs demonstration, including lifecycle/resource availability rather than a renamed security checker.

[CONTINUITY: Security-Context Contracts for Composable LLM Agent Controls](https://arxiv.org/html/2609.05269v1), a September 2026 preprint, already supplies assume-guarantee component contracts, provenance/context manifests, checked transformation witnesses and effect-bound execution permits. Its evaluation is deterministic cross-layer conformance under a declared trusted-computing-base model, and it does not claim production integration with MCP/A2A. Therefore generic compositional contracts and checked continuation context are insufficient novelty. The distinction to investigate is task-relative eligibility across actual native operation/lifecycle projections, independently checked may-reachability, and live mixed-model behavior/coverage; do not restate its effect-integrity theorem as our contribution.

The first week must produce a property-by-property gap table, not a generic first-ever claim. If a closest system already implements and validates the same contract/composition/repair behavior, change the contribution before scaling experiments.

## 2. Common contract and the limits of a guarantee

MCP and A2A serve complementary roles. MCP tool schemas and A2A descriptive skills are not equivalent capability declarations. Define a benchmark-level contract for the observable workflow, and explicitly specify its projection onto each interface. Do not score A2A as defective simply because it does not expose an MCP input schema. [MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [A2A specification](https://a2a-protocol.org/v1.0.0/specification/).

Use a finite contract `C = (information, rules, capabilities, lifecycle, evidence)`:

| Component | Required semantics | Executable check examples |
| --- | --- | --- |
| Information | Values, units, identity, uncertainty/unknowns, freshness and source references | Currency and time-zone distinctions; missing versus explicitly unknown fields; artifact accessibility under receiver permissions |
| Rules | Hard versus preferred constraints, scope, conditions, precedence, audience and authority | A conditional approval cannot become an unconditional permission; a preference cannot replace a hard limit |
| Capabilities | Discoverable operations, allowed inputs/outputs, preconditions, postconditions, authorization and error semantics | A dry-run reservation exposes a usable operation, honors required arguments and does not imply authority to commit |
| Lifecycle | Correlated workflow/task identity, pending input, completion/error, reconnect/retry and side-effect status | Input-required remains resumable; an acknowledgement is not falsely reported as completed; retries do not duplicate commits |
| Evidence | Source provenance, sender attestations, declared assumptions and unsupported mappings | Missing supported source is distinguished from a fabricated value; an unrepresentable requirement is reported rather than silently omitted |

Keep **runtime contract `C_runtime`** and **evaluator gold `C_gold`** separate. Runtime contracts are extracted from ordinary sender-visible documents, tool results and negotiated manifests. Gold contracts come from private authored task specifications and are used only for grading and labeled oracle diagnostics. The practical method must be evaluated with imperfect runtime extraction; otherwise it assumes away the hardest missing-information problem.

For each adapter, specify an encoding/decoding map and a relation between source/target observable states and event traces. A mapping preserves a declared assertion only if the assertion remains recoverable with its conditions and the trace mapping does not broaden authorized behavior. Preserve unknowns and provenance rather than guessing. Check content integrity, functional capability probes and lifecycle trace refinement separately; a parseable JSON object is insufficient.

Composition has a narrow proof target: if each mapping satisfies its declared preservation relation, adjacent contracts are compatible, required capabilities remain supported, and the assumptions hold, then the composition preserves those finite properties. A finite-state lifecycle model can establish properties of that model; model-based tests establish coverage of tested implementations. Neither establishes universal correctness of unrestricted natural language, arbitrary LLM policies or all future executions. Passing checks does not imply task success. Liveness additionally requires stated fairness, timeout and service-availability assumptions.

The gate's three outcomes have explicit meanings. **Supported** means the declared required continuation has a checked realizable mapping relative to a pinned tested/profile abstraction and explicit state/time/availability assumptions; **unsupported** has a witness of a required operation/state transition that the route cannot provide or is not permitted to provide; **unknown** means evidence is insufficient, checks time out, or assumptions are unverified or stale. Unknown is not silently converted to supported. Safe finite probes of an opaque live endpoint cannot certify every future behavior. A minimal witness may be a required pending-input transition, source/target capability mismatch and the first adapter where no allowed projection exists. Minimal means small under a declared reduction procedure, not a claim of global minimum proof size.

Construct an evaluator-private finite continuation oracle over the resettable domain state machine, bounded action horizon, legal capabilities, authority and adapter operation semantics. It determines whether at least one allowed continuation exists through the route. This is independent of whether the receiving LLM finds it. Derive compatible/incompatible cases from actual supported operations and declared limitations; manually verify reference paths and counterexamples. Evaluate gate false acceptance, false rejection and unknown outcomes against this oracle. The proposed runtime gate sees only public manifests, safe probes and ordinary sources; the complete reachability state/gold stays private.

Author the oracle independently of the gate, with reference action traces and observed implementation behavior rather than copying the gate's internal mapping table or proof rules. Otherwise agreement can merely reproduce a shared mistake. Test both with independently authored positive/negative cases and cross-review any disagreement. Compatibility is existential reachability under the specified horizon: it does not mean every LLM action sequence is lawful or successful. An unsupported witness must rule out the allowed mapping alternatives in the declared route; absence of an advertisement alone may instead justify unknown. Resource/liveness assertions need bounded service and fairness assumptions, not a claim of guaranteed future endpoint availability.

Evaluate algorithm correctness against an independent oracle for the exact runtime contract supplied to the gate, and evaluate extraction plus admission against evaluator gold separately. Omitted gold requirements are pipeline/extraction failures, not automatically gate unsoundness on the supplied contract. Supported output needs a constructive bounded continuation certificate or an independently checked sufficient condition; an empty residual list alone is insufficient. Bounded no-path certification requires relevant model/profile completeness. Freeze horizon units, initial state, legal actions, principal/resource scope and timing assumptions consistently across gate and oracle.

Distinguish missing generic advertisement from an explicitly negative capability rule. Under pinned A2A Section 3.3.4, absent/false optional streaming, push-notification or extended-card capabilities require specified unsupported responses; that normative rule can establish non-support for the corresponding operation. Without such a rule or complete profile, absence may instead justify unknown.

Name the primary finite existential target **may-compatibility**, and separately state/test the selected safety invariants of the mapping/lifecycle model. A may-compatible route can still have unsafe or nonterminating schedules; no universal progress guarantee follows from reachability alone. Must-compatibility strategy/environment games and a must-progress theorem are excluded from the 45-day primary scope and may be future work. The paper should distinguish route feasibility, modeled mapping preservation and realized LLM compliance in every theorem and result; resource/availability assumptions remain explicit.

One candidate implementation propagates task-relative residual operations/obligations backward through adapter projections, reports the first unmet requirement and compares permitted alternatives. Investigate it during specification rather than assuming it is novel. Weakest-precondition, interface-automata and assume-guarantee composition ideas are established formal-methods foundations and need an explicit lineage/comparison before naming a new method.

A sender-supplied integrity manifest can detect a transport change relative to what the sender declared. It cannot prove that the sender extracted every original rule, or that an external service truthfully implements advertised behavior. Functional probes and behavioral evaluation address different parts of this gap.

Pin MCP revision, A2A version, SDK commits and optional extensions. Current MCP request semantics do not imply stateless applications. The [MCP Tasks extension](https://modelcontextprotocol.io/extensions/tasks/overview) supports durable handles and mid-flight input, but cooperative cancellation does not guarantee work stops. Contracts requiring stronger cancellation or idempotency must report those requirements as unsupported or implement and test an explicit application-level guarantee. Do not treat a capability missing from an optional extension as a core-protocol violation.

## 3. Research questions and estimands

Freeze three main questions before the final evaluation:

1. **Compatibility and attribution:** Does the operation-level gate classify continuation eligibility and identify the first incompatible projection beyond schema validity, payload size and descriptive capability matching?
2. **Practical intervention:** Does compatibility gating with permitted resolution improve strict workflow success or the violation/coverage trade-off compared with unguarded execution and a strong generic repair/clarification policy with the same evidence access and budget?
3. **Composition and heterogeneity:** Do the conclusions transfer across separately implemented adapters, one/two/three protocol-crossing edges, and a fixed diverse model panel on the three held-out evaluation domains?

Use two linked experimental modes:

- **Boundary attribution study:** Freeze the sender packet and pre-boundary environment, receiver model, prompt rendering, available tools and continuation budget; compare reference/native delivery with actual adapter/bridge delivery. Freeze the full relevant state, not just text. This identifies the effect of the tested boundary implementation conditional on that packet.
- **Live workflow study:** Run fresh LLM continuations, tool calls, negotiation and repair through complete workflows. Upstream sender branches may be shared before treatment activation, but every post-treatment continuation executes live. This estimates deployment behavior of the complete policy. It must not be replaced by scoring logged outputs.

Separately record `original source → sender packet → adapter-decoded receiver view → actions/final state`. Report producer omission, mapping/presentation/lifecycle loss, and failure to use correctly delivered information as different categories. When native/reference and bridge receiver views are identical, outcome differences require an explanation involving tools, lifecycle, budgets, rendering or stochastic variation; do not automatically attribute them to protocols.

The primary outcome is binary **strict workflow success**: all required goals achieved and no forbidden intermediate or terminal actions. A blocked/abstained run is not successful, even when refusal is safer. The primary estimand is the paired, signed percentage-point difference between the compatibility gate and generic repair, averaged with equal weights over the declared domain/hop/model-pair distribution. Gate versus no repair is the other main contrast. The reference-versus-bridge effect is a separate boundary-attribution estimand. Model-pair cells and high-order interactions are secondary unless separately powered.

Report forbidden-action probability independently of success, together with valid completion, supported coverage, fallback use and legitimate abstention. Plot risk against coverage and unconditional success; report results on all tasks and oracle-eligible/ineligible strata. A policy that refuses everything must not appear useful. A correct rejection is a correct eligibility decision but still not task completion. Report signed effects, including gains from bridges and zero losses. Direct-success-conditioned loss is diagnostic; it must not replace the unconditional primary result.

## 4. Held-out workflows and validation

Use three realistic, locally simulated evaluation domains. All state changes stay inside resettable sandboxes:

| Evaluation domain | Live roles and decisions | Contract pressures |
| --- | --- | --- |
| Procurement and approval | Request interpretation, supplier/inventory checks, approval routing, reservation/commit | Currency/unit conversion, hard budget versus preference, authority scope, stale quotes, duplicate purchase prevention |
| Analytics and audit reporting | Source selection, query/aggregation, evidence review, report assembly | Provenance and dataset version, missing values, denominator/date definitions, prohibited disclosure, uncertainty and inaccessible artifacts |
| Service operations | Incident triage, capability selection, plan approval, job execution/recovery | Permission and tool mismatch, pending approval, task correlation, timeout/reconnect, partial results and idempotent side effects |

Each workflow requires several reasoning and tool steps: consultation of policy and changing state, clarification of at least some ambiguity, and an executable action/report decision. Include straightforward positive controls as well as conflicting constraints, distractors and genuine unsupported capabilities. Avoid designing every task around a known adapter fault or making success equivalent to copying the contract.

Development and calibration use small abstract fixture worlds and independently authored templates that are excluded from confirmation. Target-domain tool schemas may be inspected for engineering, but monitor parameters, repair policy and prompts must not be tuned on target-domain task outcomes. Freeze the three target-domain task instances and gold before execution. Describe the result precisely as transfer to held-out evaluation domains/tasks with no outcome-based domain tuning; it is not proof of generalization to arbitrary real organizations.

Provisional dataset target:

- 36 development templates and 24 calibration templates, with separately generated instances.
- 144 held-out templates: 48 per domain; three instances per template, totaling 432 confirmatory tasks.
- In the main allocation, each of three domains × sixteen ordered model pairs × three crossing counts has one distinct held-out template and three instances.

Templates must contain independently authored decision structures and constraint combinations. Renaming entities or paraphrasing a sentence creates an instance, not a new independent template. If several templates share a common authored decision structure, cluster them at that higher level and report the reduced effective diversity.

Two reviewers inspect each held-out template for realism, unambiguous gold, attainable goals, no hidden authority requirement, and agreement between prose and deterministic scorer. Review all correct reference trajectories and designed near-miss trajectories. Evaluate final database/report state and event logs so that a forbidden temporary action cannot be erased by a correct final state. [τ-bench](https://arxiv.org/html/2406.12045v1) provides relevant precedent for resettable domain APIs and goal-state grading; its metrics do not become novel by adoption.

LLM-generated tasks may accelerate drafting, but human authors must verify sources, constraints and execution gold. Maintain task provenance and a generation log. A benchmark timestamp and fresh instances limit exposure; they cannot establish contamination freedom for opaque training corpora.

## 5. Deployable compatibility resolution without gold leakage

The practical policy uses only information available in a real deployment:

1. Extract a contract from normal sender-visible sources and current tool/task state, recording uncertainty and source references.
2. Map required observable operations through the intended adapter chain, public capability declarations and safe non-mutating functional probes; compare required lifecycle transitions with negotiated support.
3. Return supported/unsupported/unknown with assumptions and a small witness; validate accessible evidence and observable progress against the sender declaration.
4. Resolve only permitted representational/evidence gaps: apply a declared schema mapping, materialize an authorized referenced artifact, retrieve a cited source, request the missing condition, or resume using a valid handle. Use native fallback/rerouting only if the route is explicitly allowed and available to comparison policies. Do not invent a missing operation, infer unavailable authority or manufacture a success/cancellation guarantee. Unresolved requirements remain unsupported or unknown.

Select repair and abstention thresholds using development/calibration data only. No policy may query evaluator-private task specifications, hidden correct actions or future labels. A scripted clarification responder may answer from a private user specification only through a declared interface, disclose only the requested user-known information, and be available equally to competing repair policies. The monitor must not bypass that interface.

The generic repair baseline gets the same packet, tools, sources, safe probes, clarification interface, allowed fallback and maximum repair calls/tokens. Implement a strong, explicitly attributed AgentAsk/BRIDGE-inspired or faithful adapted baseline selected on development tasks, rather than an intentionally weak generic prompt. State every adaptation needed for native protocol operations; code unavailability or failed faithful replication is a disclosed comparison limitation. It inspects compatibility and recovers using the same available evidence, but lacks the proposed operation-level compatibility proof/three-valued gate. Compare at equal repair budgets; additionally plot success/violations versus actual calls, tokens and latency. Restrict proposed resolutions to the same available actions so privileged retrieval, fallback or extra compute cannot explain the result by itself.

Measure runtime extraction recall/precision against private gold, boundary-detection false positives/false negatives, and end-to-end repair harm as well as repair success. Missing original rules can be invisible to a faithfully transmitted but incomplete manifest. Those misses count against the deployed method. The gold-derived allowlist in [Facts Without Rules](https://arxiv.org/html/2608.29028v1) is explicitly an upper-bound diagnostic; follow that separation rather than calling oracle repair practical.

Run probes in a separate diagnostic branch where possible. Mutating probes cannot secretly change the task environment. If a preflight probe or clarification is part of the practical policy, include its behavioral effect, latency and cost in the live arm.

## 6. Baselines and selective experimental matrix

Keep four agent roles and their tools constant across the main workflow arms. One/two/three hops mean one/two/three **protocol-crossing edges** among the same three role transitions; remaining edges use reference/native delivery. Predeclare edge placement and alternate or block its location in focused analyses. Otherwise increasing hops also increases agent count, decomposition and compute. A crossing-count result applies to the tested edge placements and model schedule.

The sparse main allocation assigns different templates to different model-pair/crossing-count cells. It supports the pooled paired policy contrast, but not a paired causal crossing-count effect or defensible model-pair rankings. Add a mandatory **paired crossing-count subset**: choose 96 task IDs before outcomes, preferably one instance from each of 96 distinct templates, balanced across domains/model schedules. Run each identical task, initial state, model schedule and four-role pipeline at all three crossing counts in the conventional-bridge and proposed-gate arms. Reuse the corresponding count already run in the main matrix; execute the two extra counts live. Keep tools, task policy, role prompts, sources, ordinary action budget and total repair budget fixed. This estimates the paired effect of the tested crossing placements and the gate-by-crossing interaction, not a universal law of hop degradation.

Use one episode-level repair/clarification/token budget, not a separate full allowance per crossing edge; otherwise three crossings buy three times the intervention compute. Give comparison policies the same evidence/probe/clarification/fallback access. Account for additional contract checks/messages in wall-clock and token reporting. Hold ordinary reasoning/tool opportunities constant across crossing counts; the path change is the intervention.

Use four model families/developers in one shared agent runtime, with fixed snapshot IDs where available. For a declared ordered pair `(sender, receiver)`, use a predeclared four-role schedule such as `sender → receiver → sender → receiver`; state that multi-hop chains contain both directions. All sixteen ordered initiating pairs, including same-model diagonals, appear in the balanced main allocation. This does not make each ordered-pair estimate precise: each pair has only 27 tasks across nine authored templates in the provisional main study.

Main live arms use the same runtime-generated structured starting packet:

| Arm | Behavior | Purpose |
| --- | --- | --- |
| Reference/native | Semantically faithful direct delivery; same agents, decomposition and tools | Deployment reference; not a different single-agent topology |
| Conventional bridge A | Strong version-pinned standard adapter/wrapper, selected using development results and verified supported features | Measure a credible real implementation baseline |
| Schema-only guard | Same bridge; type/presence validation with predeclared handling, no property-specific repair | Distinguish syntax checking from behavioral contracts |
| Generic bounded repair | Same bridge and evidence/budget, generic compatibility checking and recovery | Control for extra reasoning, clarification and compute |
| Compatibility gate | Proposed operation-level preflight, three-valued decision/witness and permitted resolution | Test the method |

A full-context single-agent result is an optional utility reference, not the causal baseline for protocol loss.

For the deterministic C1 claim, the mandatory strong comparator is bounded product may-reachability using the same runtime-visible route profiles, extracted contract, evidence and horizon. Compare symbolic/backward predecessor analysis and appropriate cached/incremental variants if checking cost is claimed. Keep evaluator gold inaccessible to this comparator and separate from the private oracle. Standard backward relational preimage composition already propagates task predicates containing handle/principal/expiry state; a weak-feature counterexample alone does not establish algorithmic novelty. Compare quotient-based residual contracts on any shared representable fragment, with quantifiers and adaptation limits explicit. See the main workflow's linked classical sources.

The minimum credible package contains the following focused studies. Counts are **planning examples**, to be revised from the pilot and then frozen:

| Study | Provisional allocation | Planned executions |
| --- | --- | ---: |
| Primary live policy study | 432 tasks × 3 trials × 5 arms | 6,480 full workflows |
| Adapter transfer | 120 preselected held-out tasks × 3 trials × 3 arms on bridge B: conventional, generic repair, gate | 1,080 full workflows |
| Representation controls | 108 preselected tasks × 3 trials × 2 additional bridge/no-repair representations: full history and free summary; reuse corresponding structured baseline | 648 full workflows |
| Paired crossing-count subset | 96 identical tasks/schedules × 3 trials × 2 extra crossing counts × 2 arms: conventional bridge and gate; reuse the main count | 1,152 full workflows |
| Frozen boundary attribution | 144 preselected tasks × 3 receiver trials × 6 paths: in-process, raw JSON, native A2A, MCP agent-as-tool wrapper, bridge A, bridge B | 2,592 live suffix continuations |
| Gold-state upper bound | 144 preselected tasks × 3 trials with canonical gold at the boundary | 432 diagnostic suffix continuations |

Total: 9,360 full-workflow evaluation attempts plus 3,024 suffix continuations, or 12,384 heterogeneous experimental executions before pilot, extra ablations, sender-packet creation and independent reruns. Full-workflow attempts include early termination and are not successful-completion counts. Provision baseline capacity for at least 37,440 role-level model turns when all four-role schedules execute, plus tool loops, repair and suffix experiments. Early gate rejection can reduce actual role calls; record actual usage rather than assuming four calls occurred in every attempted workflow. Do not present the execution count as an API-call estimate. Pilot/calibration might add roughly 720 workflows, but its final allocation should target engineering questions rather than duplicate the full confirmatory matrix.

Preselect adapter/representation/crossing/replay subsets by task IDs before outcomes, balanced as closely as possible across domain, model pairs and crossing count. Match structured versus free-summary budgets and report actual lengths; full history is an information-rich, often more expensive reference, not an information-matched control. Include the proposed method's contract metadata in its token accounting. Gold-state diagnostics are not a production arm and not the primary denominator.

Bridge B must have an independently implemented mapping layer, not merely call a second transport library around bridge A's converter. Prefer an independently maintained public bridge after a source audit. If none supports the declared features, a second person can implement the mapping from the specification without reusing converter code and use a different SDK/language where feasible. Report this as independently authored within the team, not externally validated production coverage. Use version-pinned official clients/reference servers and relevant conformance checks as additional controls. The existing [A2A Integration Testing Kit](https://github.com/a2aproject/a2a-itk) already tests multi-hop interoperability; the proposed scientific contribution must extend beyond those checks.

For a held-out-adapter claim, exclude bridge B outcome traces and mapping-specific threshold tuning from method development/calibration. Engineering conformance validation is permitted but must be logged. Randomize model/hop allocation to independently authored templates before outcomes, subject to balance; do not deliberately assign easier templates to a preferred pair. Sparse pair-level findings remain exploratory.

This selective design does not identify every model × adapter × representation × lifecycle × hop interaction. Only the declared main effects and focused contrasts support confirmatory claims. Additional model panels, bindings, frameworks, multimodal workflows and router learning are optional expansions after the core study passes its gates.

## 7. Natural mechanisms and causal diagnosis

First catalog naturally occurring limitations and failures in compliant, normally configured implementations. Candidate pressure points to investigate include tool/skill projection, typed results rendered as text, optional/unknown data fields, artifact URI accessibility, task-context correlation, pending-input representation and reconnect/retry behavior. These are hypotheses, not verified defects of MCP or A2A. Some mappings can preserve them correctly or declare them unsupported.

Use three distinct evidence classes:

- **Natural observations:** normal adapters, realistic tasks and unmodified endpoint configurations. Record prevalence and uncertainty; retain cases with perfect preservation.
- **Mechanism interventions:** on a preselected diagnostic subset, alter one runtime-visible mapping/preflight choice, restore an accessible source, or use a compatible route while holding the frozen packet/receiver/state fixed. Check whether the predicted violation and outcome change together. Do not restore evaluator gold and then call the result deployable repair.
- **Synthetic fault injections:** known field omission, stale handle, timeout, duplicate event or malformed result. Use these to establish detector sensitivity, localization and recovery behavior. Label them explicitly; they do not estimate natural protocol failure rates.

Minimize representative failing witnesses while preserving the failure, and rerun them through independent adapters/reference SDKs. Save successful counterexamples as well. Distinguish specification-permitted information limitations, implementation defects, application-wrapper choices, producer omission and receiver noncompliance. If standard adapters are lossless, the paper must say so and center any validated representation/capability/lifecycle finding instead of inventing a protocol-loss narrative.

Compare replay and live effects on a predeclared shared subset. Measure effect direction/magnitude, diagnostic agreement and identified disagreements. Report their different estimands rather than requiring identical results. Live continuation matters because routing/repair changes later inputs and actions; [Handoff Curves](https://arxiv.org/html/2610.15993v1) is relevant precedent. Ordered-model and paired-baseline methodology also overlaps [Evaluating Performance Drift from Model Switching](https://arxiv.org/html/2603.03111v1) and needs attribution.

## 8. Calibration, inference and sample-size gate

Primary grading should be deterministic wherever the task admits exact checks. For linguistic judgments that remain necessary, use blinded human annotation and a separately validated judge. Annotators must not see treatment/model labels. Report agreement by property, disagreements and adjudication rules; do not rely on a single unvalidated aggregate score.

For compatibility decisions, report the complete supported/unsupported/unknown confusion table against finite-oracle eligibility, false-accept rate among accepted routes, false-reject rate among eligible routes, unknown fraction, supported coverage and witness correctness/localization. Define denominators explicitly; an unknown on an eligible route is a loss of coverage, not a correct rejection. Include first-incompatible-edge accuracy and held-out-adapter transfer. State finite horizon and oracle assumptions in every guarantee claim.

Size the admission study for rare false acceptance as well as mean success. Under independent trials, zero errors in about 300 accepted decisions gives an approximate one-sided 95% upper bound near 1% by the rule of three; 60 gives roughly 5%. These are illustrative binomial calculations, not a safety certification. Accepted coverage, shared templates and repeated trials may make the effective denominator much smaller. A 432-task matrix cannot justify a sub-1% error claim if only a minority are independently accepted. Predeclare a coarser target or expand independent eligibility cases after the pilot and before confirmation.

For any additional probabilistic risk monitor, predeclare target labels and which evidence exists at decision time. Fit thresholds or a small interpretable risk estimator on development/calibration only. Evaluate probability calibration with Brier score and reliability plots, discrimination with a precision-recall curve when violations are rare, and the chosen operating point with precision/recall, false-alarm rate and action cost. Compare to schema-only, payload length and a simple missing-required-field baseline. Incremental prediction beyond model, domain and hop descriptors supports a measurement claim; predictive correlation alone does not prove a mechanism. A learned risk model is optional if it would displace validation of the core compatibility decision.

A prediction label for downstream violations must be measured in an unguarded diagnostic branch: successful repair changes the observed outcome and cannot be used to label that original prediction as false. Freeze all calibration before confirmatory data. A leave-one-evaluation-domain-out diagnostic is exploratory unless its training/fitting procedure was frozen in advance; it cannot replace the genuinely held-out main evaluation.

Average repeated trials within a task, then account for related instances within independently authored templates. Domain is a stratum, not the only cluster: three domains cannot support reliable three-cluster inference. Use domain-stratified paired template bootstrap intervals with all arms/instances/trials of a template resampled together, and sensitivity analysis at any higher shared decision-structure cluster. Equal-weight domain/model/hop estimates should match the declared sampling target. Do not pool all API responses as independent observations.

For the crossing subset, compute within-task differences across one/two/three counts separately for conventional bridge and gate, then the paired difference of those effects. Keep all counts, arms and trials together in the template bootstrap. A 96-task subset drawn one per template has at most 96 independent scenario clusters; repetitions and extra counts do not increase that diversity. Report intervals and practical limits; sparse four-way model/domain/placement interactions remain exploratory.

Pilot on development tasks to estimate variance of the paired **template-mean** differences after averaging nested instances/trials, as well as those nested variance components. For a simple independent-template approximation at 80% power, two-sided 5% significance:

`n_templates ≈ (1.96 + 0.84)^2 × Var(paired template-mean differences) / δ^2`.

For a target 95% interval half-width `h`:

`n_templates ≈ 1.96^2 × Var(paired template-mean differences) / h^2`.

The following are **hypothetical calculations, not measured effects or guaranteed sample requirements**:

| Paired template-mean variance | Power for 5-point effect | Power for 3-point effect | Precision ±5 points | Precision ±3 points |
| ---: | ---: | ---: | ---: | ---: |
| 0.09 | 283 independent templates | 784 | 139 | 385 |
| 0.16 | 502 independent templates | 1,394 | 246 | 683 |

The provisional 432-task study has 144 authored templates, not 432 independent scenario units. With hypothetical paired template-mean variance 0.09, 144 templates give a simple 95% half-width of about 4.9 points. That can support a roughly ±5-point pooled precision target, conditional on the pilot variance and declared weighting, but does not provide 80% power for a five-point effect: the illustrative power requirement is 283 templates before multiplicity adjustments. The 96-template crossing subset would have a half-width around 6.0 points at the same hypothetical variance; its actual paired-crossing variance may differ. Real variance, unequal cluster sizes, multiplicity and sparse violation outcomes change these values. Simulation using pilot variance components and the exact allocation is preferable to applying the table mechanically.

Predeclare the pilot decision between the base 144-template/432-task design and a maximum 192-template/576-task design, with three instances per template and three trials. Choose the final count from development-pilot variance/throughput before confirmation; do not expand because confirmatory outcomes are unfavorable. At variance 0.09, 192 templates give a simple half-width around 4.2 points, still not 80% power for a five-point effect. Increasing only main N to 192 templates raises its five-arm workflow count to 8,640; keeping focused subsets fixed gives 11,520 full workflows plus 3,024 suffixes, or 14,544 executions before pilot/reruns. Balance extra templates prospectively rather than overfilling favored cells. If more independent scenarios are required than the calendar can validate, report the attainable precision and narrower claim.

If the plausible relevant effect is three points, do not silently keep a 144- or 192-template study and promise detection. Choose an honest coarser precision target or narrow the paper's claim; a powered small-effect study may require a longer horizon. More repetitions reduce stochastic variance but do not supply new task diversity. These principles follow [Adding Error Bars to Evals](https://arxiv.org/html/2411.00640v1); the illustrative numbers here are this plan's arithmetic.

Freeze two main superiority contrasts with family-wise control, such as Holm correction, and specify any hierarchy for strict-success versus forbidden-action outcomes. Declare practical equivalence margins before testing them; nonsignificance does not establish equivalence. Freeze N, repetition count, exclusions, API retry policy and missingness treatment after the pilot. Do not stop confirmation when a favorable p-value appears or selectively rerun failed tasks. If sequential analysis is necessary, specify the procedure before collecting confirmatory outcomes.

Report API outages and policy/framework errors separately while retaining the declared deployment outcome. Infrastructure-only reattempts must follow a predeclared rule independent of success. Keep immutable raw records for every attempt. Randomize/interleave paired arms within task/time blocks, record request timestamps, and maintain anchor tasks to detect endpoint drift. A new model snapshot or a scorer/prompt bug fix creates a new experiment version; rerun the affected experiment consistently rather than overwriting selected failures.

## 9. Ideal model roles and reproducibility

Select models for scientific coverage, not just availability. The ideal primary panel contains strong tool-capable models from OpenAI, Anthropic and Google plus a strong open-weight family such as Qwen or DeepSeek. These are role/family recommendations; exact currently available IDs, immutable snapshots, supported parameters and permissible hosting routes must be verified at the execution gate. Use direct documented model APIs in a shared runtime; subscription access or a coding extension is not automatically equivalent to a programmable inference endpoint.

| Role | Selection principle |
| --- | --- |
| Four-model primary agents | Distinct model families, reliable tool calling and context capacity; same runtime and declared action/token/timeout budgets |
| One open-weight reproducibility anchor | Pinned model weights/tokenizer, inference-server version, quantization and decoding configuration; independently rerunnable |
| Development assistance | Strong reasoning/coding models may draft contracts, tasks and code; human verification and task provenance remain required |
| Optional linguistic judge | Different family from the main generators where feasible, blinded, human-calibrated, frozen; no hidden repair channel |

At least one open-weight anchor is advisable for artifact defensibility; hosted snapshot behavior can remain subject to provider changes. Distinguish model developer, API hosting provider and agent framework in the paper. Four API-wrapped models support claims about mixed-model agents within our scaffold; they do not establish interoperability of arbitrary proprietary autonomous-agent products.

Fix context and output-token limits, reasoning settings, sampling parameters, retries and tool-format adapters. Equal call budgets do not necessarily mean equal cost or internal compute; report actual usage and known limitations. Avoid alias-only `latest`, automatic provider fallback and silently substituted models. Budget planning should use observed pilot cost/throughput for the full request count, but funding assumptions must not drive a scientifically weak main contrast.

## 10. Three-person critical path over 45 days

Provisional team assumption: three contributors with roughly 25–30 focused hours each per week, approximately 480–580 person-hours over the 45 days, plus scheduled supervisor/domain-review time. If effort is substantially lower, reduce optional expansion first and revisit sample feasibility early. Assign person A to runtime/contracts/gate, B to domain tasks/private gold and independently authored bridge B, and C to source audit/statistics/independent oracle/reproduction/paper coordination. The oracle may consume independently reviewed domain specifications from B but must not copy A's gate implementation. Cross-review work; no contributor alone signs off their own headline result.

| Days / approximate dates | Person A | Person B | Person C | Gate/deliverable |
| --- | --- | --- | --- | --- |
| 1–7 / Oct 23–29 | Tiny offline gate prototype, two paths and bounded contract semantics | Domain specifications and positive/negative oracle fixtures | Closest-work property table, independent finite oracle and initial hypotheses | Novelty/construct gate after approval; concrete distinguishing continuation example, not just proposed terminology |
| 8–14 / Oct 30–Nov 5 | Full runtime, trace checkpoints, reference/bridge paths and baselines | Resettable domains, scorer, development/calibration tasks and independent bridge | Adversarial scorer validation, blinded annotation and analysis skeleton | Offline properties/conformance pass; gold/runtime separation and strong baselines verified |
| 15–21 / Nov 6–12 | Bounded live pilot and method development on nonconfirmatory tasks | Held-out template authoring and human/reference-trace review | Variance/dependence/throughput pilot, calibration, model checks and prospective N choice | Select 144 or at most 192 templates, achievable precision and fixed budgets before confirmation |
| 22–28 / Nov 13–19 | Resolve pilot bugs; freeze executable policy/prompts; begin interleaved study | Finish and seal held-out instances/gold and witness trajectories | Freeze local preregistration, paired-crossing subset and balanced allocation; dry-run analysis | No known scoring/reset leaks; held-out calibration/thresholds immutable; begin fixed study |
| 29–35 / Nov 20–26 | Main live study and paired crossing-count runs; immutable records | Bridge transfer/representation and natural witness validation | Boundary replay, eligibility evaluation and drift/error checks | Complete predeclared matrix; no result-dependent task or route selection |
| 36–42 / Nov 27–Dec 3 | Clean-environment rerun and reproducibility fixes | Independent trace audit, negative controls and domain validity review | Clustered intervals/robustness, figures, paper results and limitations | Headline findings regenerate; failures, zero effects and precision limits retained |
| 43–45 / Dec 4–6 | Final artifact documentation and release-package checks | Benchmark documentation, licenses and witness appendix | Complete manuscript, closest-work refresh and claim-to-evidence audit | Concrete paper/artifact ready for author/supervisor review and later submission approval |

Writing starts in week one: introduction/gap after audit, methods after specification, reproducibility/limitations while building. Keep a running claim-to-figure/table/source ledger. Public preregistration or artifact upload is a separate outward publication action; prepare an immutable local preregistration at freeze and obtain explicit authorization before external posting. This planning document does not authorize an issue, PR, paid execution or conference submission.

Evaluator-private gold is inaccessible to runtime policies during testing; it is not permanently undisclosed grading. Make the grading criteria, reference specifications and evaluation evidence reviewer-accessible at submission, with appropriate anonymous artifact preparation.

The critical path is **validated gold and independent scenario diversity → stable practical method → pilot-derived sample decision → sealed live evaluation → independent reproduction**. A polished dashboard is optional and should not displace that path.

Six-week feasibility is a pilot decision, not an inference from API access. Measure human template-authoring/review time, oracle/scorer disagreement resolution, sustained allowed request capacity, whole-workflow duration and resumable execution overhead. Reserve the final week for independent review and writing. The base design needs capacity for the 37,440-turn full four-role schedule plus suffixes and tool/repair loops; do not assume it finishes merely because token costs are affordable. Freeze counts/budgets for mandatory targeted ablations and independent reruns at the pilot gate instead of leaving them outside the throughput forecast. If 192 independently validated templates cannot fit the measured person-hour budget, retain an honest lower-precision 144-template study and omit optional extensions rather than relabeling generated variants as independent scenarios.

## 11. Mandatory package, optional expansion and stop/pivot rules

Mandatory for the intended paper: a precise closest-work distinction including BRIDGE, AgentAsk, AgentThread and CONTINUITY; bounded task-relative operation/composition statement; executable supported/unsupported/unknown gate and witness; independently authored private finite-may-continuation oracle with separately stated safety; non-oracle resolution with a strong compute/evidence/action-matched baseline; imperfect runtime extraction measured; two independently implemented mappings with explicit provenance; three held-out evaluation domains; real heterogeneous LLM continuations; the identical-task paired crossing-count subset; reference and replay attribution; deterministic state/event grading; pilot-derived precision justification for success and admission errors; sealed analysis; independent reproduction; a complete paper and evidence artifact.

Optional after the main package: larger model panels, cross-framework agents, additional A2A bindings, older protocol revisions, multimodal artifacts, real external enterprise tools, learned routers, training a specialized repair model and a public benchmark website. Do not advertise these as completed coverage if they are omitted.

Use explicit decision gates:

- If closest work covers the proposed mechanism, redesign or narrow the contribution before large experiments.
- If runtime extraction misses most task-critical rules, address extraction on development data or make the limitation central; do not substitute gold in the practical arm.
- If natural adapters preserve the contract, report the zero effect and focus only on supported representation/lifecycle/repair findings. Deliberately breaking fields is not a substitute for a natural mechanism.
- If required capability/lifecycle mappings are unsupported, report preflight rejection and lost utility; do not force a misleading equivalence between protocols.
- If sample requirements exceed the calendar, simplify secondary analyses or set an honest precision target. Preserve negative results and do not invent a stronger novelty claim to compensate.
- If clean reruns cannot reproduce the headline result or the scorer has material false positives/negatives, resolve the cause before describing the work as verified.

By day 45, the deliverable is a fully documented bounded study and paper ready for review, with claims proportional to the actual evidence. Conference acceptance, universal correctness and exhaustive prior-art absence remain outside what a 45-day workflow can guarantee.
