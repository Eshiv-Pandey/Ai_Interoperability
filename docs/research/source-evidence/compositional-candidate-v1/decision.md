# Compositional continuation summaries: candidate rejection v1

Prepared 25 October 2026 by a separately assigned AI research agent. **Decision:
generic compositional summary reuse does not establish the missing C1 step. No
performance trial is selected.** The useful result is a precise admissible
construction, a proof obligation for joining its summaries, and counterexamples
to cheaper unsound variants. This is analytical research, not independent human
review, an application experiment, a new theorem claim, or a checkpoint pass.
The original bounded may-completion objective and 5% verified credit remain.

## Candidate examined

The proposed candidate caches relations for source-defined route segments and
combines them for each new task contract, updating only summaries affected by a
profile or evidence change. It would return the existing supported/unsupported/
unknown decisions and independently checked witnesses. This explores a concrete
form of compositional reuse rather than giving ordinary caching a new name.

Inputs are: a pinned finite transition model; the exact runtime goal/invariants;
the original transition horizon H; legal caller actions; accepted initial public
evidence; source/model fidelity assumptions; a decomposition into segments; and
the evidence dependencies used to justify each segment. No evaluator-private
answer, guessed lease, or hidden future update is an input. Original-task,
principal, token, namespace and timing relationships remain part of the state.

For this analysis, a segment has defined entry/exit points and includes all
intermediate transitions relevant to safety and allowed interleavings. A claimed
decomposition must cover every route trace of interest, including alternatives,
loops, callbacks and goals reached before a normal segment exit. A partial
inventory is inadequate for a complete-negative decision. This condition is not
currently proved for either full bridge interface.

For complete boundary states x and y and an exact transition count n, define:

```text
R_i[n](x,y) iff segment i has a concrete n-transition execution
                from x to y, safe at every visited state.

D_0 = {(initial,0)}
D_i = {(y,h+n) : (x,h) in D_(i-1), R_i[n](x,y), h+n <= H}
```

Take the union over the permitted segment schedules. Goal exits must include
safe prefixes ending inside a segment; zero-transition initial success remains
possible. A protocol crossing is not substituted for a finite-model transition.
Time, service expiry and action-count budget are separate dimensions. When time
affects guards, its relevant value belongs to x/y; n still charges the specified
transition count. For arbitrary graphs, introducing a phase/monitor component is
ordinary product construction, and its cost must be counted.

The simple procedure is to validate dependency bindings, fetch or build each
needed summary, join on matching boundary states while adding n, and inspect
safe goal exits. The corresponding lower-summary search may return supported
only with a concrete joinable witness. An upper-summary search may return
unsupported only after complete coverage, freshness and absence of relevant
indeterminacy are justified. Otherwise it returns unknown. A fresh summary is
not itself a proof of source fidelity or service stability.

## Exactness and the extra obligation created by projection

With full boundary states, exact R_i, complete scheduling/goal exits and all
intermediate invariants preserved, relational joining is equivalent to the
supplied bounded reachability problem. The forward direction cuts a concrete
execution at its segment boundaries. The reverse direction concatenates the
stored segment witnesses: the end state of each witness is exactly the start of
the next, and the summed transition length is at most H. This is a standard
relational-composition argument, not a novel interoperability theorem.

A smaller interface projection alpha creates the actual difficulty. It is not
enough that every projected summary edge has some concrete witness. Consecutive
edges must admit one *joint* choice of concrete boundary states consistent with
the same execution, public-evidence world, path constraints and resource state.
Existentially choosing a different hidden representative at each join is unsound
for a positive certificate. Merely checking equal projected names does not
establish that joint choice.

Three standard remedies are available: retain the necessary boundary state;
join symbolic constraints with shared variables and solve their conjunction; or
validate a candidate trace concretely and refine an invalid abstraction. A proved
quotient/lifting relation can also justify a smaller interface. The proof must
preserve this task's goal, safety, horizon and legal actions. Calling each edge a
locally realizable lower summary is insufficient without this compositional
property. No new remedy or representation beyond these is identified here.

The upper/lower directions must remain distinct. Existential projection of
concrete edges can over-approximate paths; its *absence* of a goal may support a
negative claim when the coverage and predicate abstraction are sound. Its
presence of a goal cannot alone support a positive claim. An under-approximate
path set may establish a witness after lifting but cannot establish absence of
every legal continuation. Unknown is retained when either required argument is
missing. The frozen v1 conservative treatment of unknown predicate values is
not silently strengthened by this proposal.

## Four analytical counterexamples

These are authored mathematical examples, not captured bridge failures, a
held-out corpus, a performance run, or evidence of real-world prevalence.

1. **Incompatible hidden endpoints.** Let the only edges be s -> m0 and
   m1 -> g, and let alpha(m0) = alpha(m1) = m. Both summary edges have real
   witnesses, and the projected graph has s -> m -> g. The concrete graph has
   no s-to-g path. A one-bit boundary distinction repairs the example. A
   cryptographic assumption is unnecessary: m0/m1 can be different ordinary
   task, principal or mutable-state bindings.
2. **Locally valid horizons.** Two necessary segments each require exactly two
   transitions. Each is reachable within H = 3 when assessed separately, but
   their composition needs four transitions. A Boolean reachable summary loses
   the resource accounting. Indexing by n and summing it rejects correctly.
3. **Unsafe interior.** A segment is s -> u -> g with safe s and g but unsafe u.
   An endpoint-only summary incorrectly accepts the safe-goal claim. R_i must
   already enforce the invariant at u or expose that internal state to the
   checker. Hashing the endpoint relation cannot repair the omitted obligation.
4. **Inconsistent observation times.** A service always satisfies a XOR b. One
   read observes a = 1, then an update flips the service, then a second read
   observes b = 1. Pooling both observations into a = b = 1 invents a state.
   Correct keys alone do not create an atomic snapshot or a validity interval.
   A dynamics/history model, genuine snapshot/lease, or explicit conditional
   assumption is needed. The example establishes no actual bridge race.

## Primary comparator check

The following sources were opened and inspected in this run. Their retrieved
passages and the PMC browser-check response are preserved in five exact
query/result records. No complete paper PDF was downloaded or redistributed.

| Source | Inspected scope and consequence |
| --- | --- |
| [SMASH, POPL 2010](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/popl004-godefroid.pdf), Sections 4.1-4.3, Figures 8-10 | It stores and composes context-sensitive positive and negative reachability summaries, allowing either kind to assist the other. Section 4 explicitly retains shared global state across calls. Its program may/must terminology differs from this project's may-completion label. It is a required close comparator for alternating positive/negative summary reuse; no claim is made that the original tool implements MCP/A2A semantics. |
| [Asadi et al., summary repair](https://link.springer.com/article/10.1007/s10703-023-00423-0), Sections 2.1-2.2 and 4.1 | UpProver represents bounded behavior using SMT summaries, checks old summaries against changed function bodies, and propagates/repairs invalid ones. Its incremental formulation assumes the safety properties remain fixed; changing our runtime contract requires revalidation, not a transfer of that guarantee. A goal/safety/horizon monitor reduction is an analytical adaptation here, not the authors' claimed implementation. Generic profile-summary repair supplies no extra C1 step. |
| [Berendsen and Vaandrager, compositional abstraction](https://sws.cs.ru.nl/publications/papers/fvaan/BV07.pdf), introduction and Sections 2-3 framing | The framework covers shared-variable communication, synchronization and committed transitions under explicit semantic restrictions. Source-specific concurrency and time cannot simply be omitted at a bridge boundary. Its timed simulation relation is not automatically an exact quotient for our bounded transition-count property. |

These are scoped overlap findings, not evidence that all potential specialized
methods are already known. In particular, computability by a general exact
solver does not rule out a new efficient representation. This candidate fails
because it identifies no additional representation, algorithm or justified cost
advantage beyond the standard procedures, not because exact solving exists.

## Cost, certificates and selection decision

Every fair comparator receives the same accepted source summaries, legal
alternatives, evidence bindings and workload; the strongest arms include demand-
driven positive/negative summaries, symbolic/backward solving and dependency-
aware incremental revalidation. Unwinding or a monitor adaptation must be
disclosed equally. UpProver/SMASH-inspired implementations would be adaptations,
not the original systems. Contract quotient/Pacti and the existing PC2/
AgentThread-related obligations remain in force.

Charge source extraction, separator validation, summary construction, relation
size, symbolic solving, dependency checks, invalidation, recomputation, all
observation bundles and certificate generation/checking. A useful structural
speedup needs a bound or measured advantage that survives these costs. Comparing
one warm summary cache with a cold baseline does not discriminate the proposal.
Neither current real-route workload nor a meaningful performance threshold is
frozen for this construction. No performance numbers were collected.

The frozen v1 certificate binds the full projected manifest. Reusing an internal
summary after a valid update must still create and check a certificate for the
new manifest. A digest over selected fields cannot make an old whole-manifest
certificate valid. Compact local certificates need a separate independently
checked composition/fidelity obligation; adding their hashes is not that proof.

**Do not implement or benchmark generic compositional caching as the next C1
candidate.** This would repeat mechanisms already covered by the acquisition
review, now with a directly relevant compositional may/must predecessor.

The next materially different *investigation* should move from caching an
already accepted graph to determining whether a concrete source/runtime
fragment admits a checkable, small separator in the first place. In the pinned
AgentOps lead, examine whether its application transaction, confirmation state,
ADK callback/session behavior and task association can be partitioned while
preserving the exact same-task effect/safety property. This requires actual
installed-runtime/native evidence before a wire/compiler claim. It may fail
because shared state or reentrancy destroys the proposed boundary. The result
should be an explicit separator plus proof/lifting checker and a cost argument,
or a minimal source-backed counterexample. A standard slicing or symbolic
execution implementation alone would remain baseline work. This is a specific
selection condition, not a selected novel method, an application experiment
authorization, or a contribution-route change.

## Record and limits

No application, service, model, dependency installation, experiment, performance
measurement or existing archive replay ran during this screen. No shared
workflow/checkpoint/manuscript or implementation was edited. The ordinary source
read attempted a nonexistent recipe-screen decision filename; that error is
retained in `read-failure-note.json`, with no absence inference. Retrieval 02
contains the PMC access-check page; the separately accessible publisher body
supports the UpProver passages. No failed access was replaced or described as a
successful read. Correctness proofs above are informal and await independent
technical/human review. This screen closes only the generic-compositional-reuse
selection question.
