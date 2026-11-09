# Candidate admission v0: bounded evidence-query planning

Prepared **24 October 2026**. This is one concrete, implementable candidate and comparator specification, **not a claim of novelty or a passed research gate**. The source audit has not identified a defensible new algorithmic gap. Its next purpose is to discriminate whether task-dependent observation and revalidation on the actual routes creates a substantive problem beyond established reachability, active testing and dependency caching. It preserves the approved 45-day method study; an applied-only fallback or reduced bridge scope requires a separate explicit decision.

The user is the sole confirmed researcher. Separately authored agent implementations supply an independence check on code, not an independent human scientific review. Supervisor/mentor review is a potential later step and has not occurred.

**Post-specification feasibility result:** the [source/wire audit](candidate-query-feasibility.md) finds that a strong correctly cached checker already attains the one-query lower bound on the known-task text fragment. The 20% request-saving screen below cannot pass there. No candidate performance run has been fabricated or scaled; locate a genuinely richer dependency and a defensible new contribution before using this pilot to support an efficiency claim. The original specification is retained for traceability.

The next [source-backed reference continuation probe](reference-continuation-probe-v0.md) investigates a genuine application's action-construction requirement, not a claimed advantage for this observation planner. Its original runtime is A2A 0.3, while the bridges are A2A 1.0; compatibility and any disclosed port must be validated first. Raw sending is a permitted task action when exposed, and strong comparators receive it equally. This does not revive the rejected 192-episode efficiency pilot or establish a new C1 method.

## Concrete question and present evidence

For an already specified task contract and pinned route, can a small deterministic planner obtain enough **current, correctly bound evidence** for a bounded continuation certificate using fewer observation requests than a strong lazy checker, while charging planning, caching and revalidation costs?

The [existing bridge evidence](bridge-eligibility.md) establishes two source-independent mappings with development wire smoke tests. Their modern MCP Tasks versus legacy stdio profiles are documented differences, not defects or new findings. The current fixture/assertions are upstream-authored and shared across routes; they are not independently authored gold. Use only operations actually exposed by each pinned profile. A route may expose A2A task continuation through ordinary MCP tools without implementing the MCP Tasks extension.

The mgcrea wire record includes a documented local task mirror and an explicit refresh option. The other converter source has a documented agent-card cache TTL. These are plausible **observation boundaries** to instrument, not discoveries of broken interoperability or novelty. Do not substitute a local mirror for authoritative status without recording its status and age.

## Inputs and the evidence boundary

Keep [finite model v1](finite-model-v1.md) unchanged as the reference reachability/checking interface. Add an outer development wrapper, proposed `evidence-continuation/0`, which is not yet implemented or frozen:

| Field | Required meaning |
| --- | --- |
| `template` | Bounded transition skeleton, runtime contract, explicit initial state and continuation horizon. Source/profile completeness is separately declared and justified. |
| `obligations` | Finite evidence atoms guarding transition realizability or predicates; at most **8 unresolved Boolean atoms** in this pilot. Each identifies its exact task/handle/resource/principal/profile binding. |
| `queries` | At most **8 read-only query bundles** with operation/wire mapping, returned atoms, allowable outcomes, timeout, declared duration bound and request cost. One RPC returning five facts costs one RPC to every arm. |
| `receipts` | Accepted observation values plus exact query/context key, source response hash, provenance, observation time and justified validity interval. A self-chosen TTL is an assumption, not a service guarantee. |
| `clock` | Logical integer ticks for finite replay, separated from measured real elapsed time. Query durations and expiry rules are frozen equally for every arm. |
| `change_events` | Explicitly visible changes, or bounded possible changes supplied by the public evidence model; never evaluator-private future outcomes. |
| `budget` | Shared maximum requests and planning deadline. Requests, initialization and checks are all metered; no model calls. |

A query key includes the pinned adapter/profile digest and all applicable endpoint, protocol/extension, task root/ID, handle namespace, principal/scope, resource and credential/policy epoch fields. Mark non-applicable fields explicitly. A receipt from another task, principal or profile cannot answer the atom. A changed URI or alias must not inherit access evidence just because a display name matches.

Allowable outcomes come from explicit specification/source constraints and the declared finite development model. They are **possible outcomes**, not the hidden fixture's actual next answer. Query failures, unmodeled results, contradictory receipts or unverifiable bindings leave the affected atom unresolved. Preserve failures and costs. Do not infer impossibility from a single failed probe.

The finite pilot starts with truthful, deterministic read-only observations and declared duration bounds. Failure/timeout cases are separate abstention checks. Arbitrary mutable remote services need stronger evidence/snapshot/lease assumptions; safe probing cannot establish their future behavior.

## Decision and certificate procedure

At time `t`, discard stale receipts and receipts whose exact dependency binding has changed. Build two ordinary projected graphs:

- **Lower graph:** only transitions and predicate values whose required evidence is known and current. A safe path of at most the fixed continuation horizon to the runtime goal can establish supported.
- **Upper graph:** includes every transition/predicate possibility not excluded by accepted current evidence. An independently checked no-path closure can establish unsupported **only** with a justified complete relevant profile/model. Otherwise abstain.

The projection uses explicit guarded obligations in the wrapper; it does not conceal extra guards in a v1 manifest. Generated v1 manifests contain fully projected transitions. Preserve correlations between atoms returned by the same snapshot rather than inventing independently satisfiable values. A model inconsistency is an input/evidence error, not a successful admission.

The supported outer certificate carries the selected v1 path certificate, runtime-contract/template digest, query/profile/binding digests, observation dependencies and validity limits. Every path transition's required evidence must be established. The unsupported outer certificate carries the complete bounded closure and all evidence/profile dependencies required to exclude every upper path. **An unsupported certificate can depend on more evidence than a single supported path.** Unknown has no proof certificate.

Use an independent outer checker to replay the projection, receipts, path/closure and expiry. v1's existing full-manifest digest remains unchanged. Selective evidence reuse produces a **new** projected manifest and newly checked certificate; it never makes a changed manifest's old certificate valid.

Immediately before continuation, validate dependency keys and observation intervals again. Refresh expired or changed dependencies, recompute the decision and check the new certificate. Every comparator gets the same reuse facility. If the service offers no atomic snapshot/lease covering the action, the certificate is conditional on the explicit no-intervening-change assumption; it cannot promise that state remains fixed between the final query and execution. A real time-of-check/time-of-use guarantee must not be invented.

## Implementable planner

Use **finite dynamic programming over evidence and time** for v0, with no claim of a new recurrence or scalable algorithm. Evidence-query planning and continuation reachability have different horizons: observation requests consume the query budget and time; task actions consume the continuation horizon. They must not be silently interchanged.

For the available-query, bounded-duration pilot, define `V(E,t,b)` as the smallest worst-case additional query cost required to obtain one checked path or complete cut, where `b` is the remaining integer request-cost allowance. Every query has positive integer cost. Return zero when the procedure above can certify a decision after the declared checker-duration bound; expire receipts through that bound first. Otherwise evaluate each admissible query's modeled response branches at `t + duration(q)`, including receipt expiry, and choose:

```text
V(E,t,b) = min_q [cost(q) + max_o V(expire(update(E,q,o), t+d(q)), t+d(q), b-cost(q))]
```

Only queries with `cost(q) <= b` and a modeled completion within the deadline are admissible. An unfinished leaf, deadline overrun or no admissible query has infinite cost. The decreasing allowance makes the tree finite and permits a repeat query when refresh is needed; repeating a query is never free. Tie-break by smaller modeled elapsed time, then query ID. If no finite policy fits the request budget/deadline, return unknown; otherwise execute the first query and replan from the actual response. No actual future answer is exposed to the planner. Logical durations are declared modeling assumptions; actual planning/checking time and expired-at-execution results are measured separately and can falsify those assumptions.

Model a timeout/unavailable response explicitly when the profile gives it as a possibility. If that makes every worst-case policy unable to certify, report that fact instead of assigning a favorable probability. The available-query experiment is conditional; the failure suite verifies honest unknown behavior. Do not use a distribution silently to turn the minimax recurrence into an expected-cost claim.

This is standard finite contingent planning. The candidate is worthwhile to implement only as a bounded discriminating prototype: it can identify which query timing/bundle constraints matter and how large the planning cost is. If it reduces to ordinary static decision-tree planning plus cache invalidation, the algorithmic novelty claim still fails.

## Fair comparators

All arms use the same source-derived skeleton, contract, evidence receipts, clock/change schedule, query bundles, completeness assumptions, cache key rules, budget and independent checker. All can stop as soon as a valid certificate exists. They receive no evaluator-private answers or goal additions.

| Arm | Frozen procedure |
| --- | --- |
| **Eager whole-route reference** | Query each required bundle once in query-ID order, then exact bounded reachability. It may reuse still-valid cached receipts and must revalidate changed/expired dependencies. This is a weaker observation baseline, not the decisive novelty comparator. |
| **Lazy task-cone checker with caching** | Compute the backward syntactic cone of the runtime goal/invariants; retain source-declared cross-edge dependencies. Try known feasible paths first. Otherwise query the cheapest bundle on the shortest still-possible path; after contradiction recompute. Use the same correctly bound receipt/certificate cache and invalidate affected dependencies. Include a cut-directed variant for negative cases; take the better prespecified variant by stratum, not retrospectively per episode. |
| **Static active-testing comparator** | On the same finite hypotheses/query bundles, select tests to identify a certificate decision region, with nonuniform request costs. Use an explicitly scoped implementation of decision-region testing, not an alleged new algorithm. Revalidate expired evidence after each step using the same rules. |
| **Temporal finite planner v0** | The recurrence above accounts for query duration/expiry during selection. Its exact schedule oracle is an independently implemented exhaustive query-tree enumeration over the same possible outcomes. The oracle is a correctness/cost reference, not a new method the candidate can claim to outperform on the identical problem. |

The active-testing lineage is especially close: [Golovin, Krause and Ray, NIPS 2010](https://papers.nips.cc/paper_files/paper/2010/hash/1e6e0a04d20f50967c64dac2d639a577-Abstract.html) covers costly tests and equivalence-class identification; [Javdani et al., AISTATS 2014](https://proceedings.mlr.press/v33/javdani14.html) covers overlapping decision regions and Hyperedge Cutting. Distinct feasible path certificates can define overlapping regions. Read and implement the relevant formulation faithfully before retaining observation-efficiency claims. Do not transfer their Bayesian/approximation guarantees to this minimax, expiring-evidence setting without proof.

## What must differ for a substantive claim

| Existing mechanism | What v0 adds operationally | Missing evidence for novelty |
| --- | --- | --- |
| Exact reachability/weakest-precondition analysis | Chooses and refreshes observations before invoking established analysis. | A new useful evidence problem/representation or procedure, rather than the same analysis with renamed task fields. |
| PC2's obligations, visible-state uncertainty and bounded intervening controls | Targets a constructive bounded completion path or complete refusal cut, using concrete protocol observation bundles. | A comparison showing which actual requirement cannot be represented or handled at comparable cost by the applicable PC2 fragment; different quantifiers alone do not establish superiority. |
| Cached/incremental analysis | Tracks receipt dependencies and refreshes affected evidence. | More than ordinary keyed memoization, TTL checks and recomputation. Give the strong cached baseline identical invalidation and source inputs. |
| Active decision-region testing/finite planning | Adds measured bridge query durations, evidence expiry and revalidation constraints. | A source/wire-grounded temporal dependency with demonstrable cost/coverage consequences and a technical treatment beyond direct finite time expansion or standard scheduling. |

**No defensible gap has yet been demonstrated.** Meeting the efficacy screen below would justify further method work, not automatically pass G1/CP2 or guarantee publication. Do not silently change C1 into an applied-only claim because the prototype behaves correctly.

## Small prespecified experiment without model tokens

Before candidate measurements, freeze **4 task contracts × 2 real bridge profiles × 6 evidence regimes = 48 episodes per arm**. Two contracts are development inputs and two are sealed until the code/settings are fixed. Use four arms, hence **192 deterministic admission episodes**; the independent finite query-tree oracle checks only the small public evidence models and receives the same allowed outcomes. All materials remain local.

Contracts cover same-task poll/result retrieval, an input-required continuation when exposed, artifact/result access under the declared receiving scope, and one explicit modern-MCP-Tasks requirement as a documented profile/non-support control. Where a profile does not expose the requested operation, retain that case as known non-support or unknown according to the normative evidence. Do not make each bridge appear eligible for every contract by weakening the contract.

The six regimes are cold, valid warm cache, changed task/handle binding, changed relevant observation, changed unrelated observation, and expired evidence. Freeze one deterministic event schedule per regime and the same initial state for all arms. Change injections and deliberately delayed queries are labeled authored development interventions. They do not estimate natural failure prevalence. Record which supported cases replay successfully over real wire; finite disagreement can be diagnosed locally without fabricating a wire defect.

Primary pilot measurements are incorrect binary decisions, independent certificate failures, correctly decided coverage, observation requests and bytes. Secondary costs are profile construction, planning/projection/checking CPU, cache setup/update, refresh requests, total elapsed time and memory. Report cold, warm and changed cases separately, then total stream cost with warm-up charged once per arm. A bundle's facts are never charged differently across arms. No LLM-generated contracts, paid judge, model API or GPU is needed.

Prespecified candidate efficacy screen:

1. **Zero** unexplained wrong supported/unsupported decisions and certificate acceptance errors on all modeled completions and mutation cases. Every unsupported result needs the same justified completeness as its comparator.
2. No loss of correctly decided coverage against the best applicable cached/lazy or active-testing comparator at the same budget. Unknown remains an abstention, not completion.
3. On **each bridge**, at least **20% fewer total observation requests** across cold, changed-binding and changed-relevant regimes than the stronger practical comparator, with equal or lower total profile/planning/checking/refresh elapsed cost. Compare whole frozen strata, not selected winning episodes.
4. Exact finite query-tree enumeration agrees with the planner's modeled worst-case value and decisions. The certificate checker rejects wrong identity/profile/receipt, stale time and changed contract/model. No approximation or optimality claim survives a mismatch.

These numbers are a prospective engineering screen chosen for a tiny pilot, not a scientific definition of novelty or a powered population estimate. If source-faithful query bundles cannot produce a nontrivial contrast, do not add invented latency, independence or failure assumptions to force a win. Record the null result and use the next observation below. The human novelty review remains pending.

## Next discriminating source/wire observation

Instrument both bridge paths and the native A2A fixture for **one returned pending task**, then record local versus authoritative task status, the exact task/context IDs, caller scope, artifact/result response bundle, card/profile revision and each observation's legitimate freshness basis. Observe the subsequent same-task continuation under one source-valid change or fixture event. Compare what is available before continuation with what a full, correctly cached checker would already read.

The useful question is whether there is a **necessary relational dependency across observations** that cannot safely be omitted or reused and costs an additional query, or whether one existing task/status response already supplies all required bindings. The latter would weaken the proposed gap. A delayed mirror or documented missing Tasks extension alone is replication. If neither route exposes independently checkable freshness/snapshot semantics, do not invent those semantics: use explicit conditional assumptions and test whether enough meaningful admission evidence remains.

Place this probe and the 48-case discriminating pilot inside days 1–7. Do not extend the 45-day horizon, spend the live budget, or scale a novel-method claim before resolving the gap and the required review. A negative result calls for explicit redesign within the approved objective, not silent abandonment of it.
