# Local relation summaries: concrete method reduction screen v1

30 October 2026. This is a source-grounded analytical screen, not a paper draft,
implementation, formal mechanization, performance trial or scientific review.
No solver, checker, completed trial, application or model was executed for this
screen. Frozen solver and benchmark files were read and left unchanged.

**Finding:** a concrete optimization missing from the current direct/shared
cache code is possible, but it supplies no additional operation beyond the
strong parameterized-summary comparator. Do not implement it as the missing
new-method contribution. This conclusion concerns the constructions below;
it does not establish that every possible new method is impossible.

## Exact input and target

Use the existing `recipe-continuation/1` profile: finite graph, fixed initial
bindings, finite declared literal/public-binding argument recipes, reviewed
expression trees, guarded atomic updates, runtime goal/invariants, transition
horizon, logical clock, freshness and coverage declarations. The target remains
existence of one invariant-safe known concrete completion within that horizon.
It is not a strategy against all environments or a uniform recipe for hidden
states. Source-to-profile fidelity and legal-interface coverage are assumptions
to discharge separately; a profile's provenance string does not discharge them.

The source-language screen preserves all exposed legal arguments, including
permitted string guesses. This recipe prototype itself accepts only its finite
declared recipe lists. No conclusion here promotes those lists into complete
coverage of an arbitrary-string source interface. Generated values are not
silently made caller-controlled, and no public input is converted into an
unnameable private atom.

## What the actual implementations already do

| Actual source location | Operation already supplied |
| --- | --- |
| `direct_goal_pruned_v2.py`, lines 54-102 | At each depth, merge identical `(graph state, canonical whole frame)` products; retain one legal witness history; prune targets outside the remaining-horizon safe may-goal cone; cache `(edge ID, whole frame)` relation results; stream the final goal edge until one feasible tuple succeeds. |
| `refinement_oracle.py`, `_topology`, lines 292-337 | Compute the conservative observable-uncertainty pass and safe possible-goal cone. Goal pruning does not erase unknown contracted observables on a reachable dead branch. |
| `refinement_shared_lift_v2.py`, `_start` and `_expand`, lines 128-215 | Reuse completed exact-prefix summaries and completed local relation expansions; both relation keys and stored before/after payloads retain whole frames. Early success does not publish a complete relation cache entry. |
| `refinement.py`, `_lift`, lines 266-313 | Enumerate the supplied argument recipes, construct requests, test guards, apply old-frame atomic updates and retain correlated successor frames. Definitely false guards dominate other unknown values. |
| `c1-callsite-factoring-screen-v1.md`, lines 120-147 | The equally informed comparator may use ordinary interprocedural parameterized summaries, shared symbolic call DAGs, substitution, caching and valid POR, preserving every residual guard, observation and original cost. |

The implemented shared method adds reuse within a path-first enumeration. It
does not add a new transition semantics, legal action or decision property.
The direct product already combines known-safe prefixes that reach the same
state, depth and whole frame. Replacing path enumeration with that quotient
would be adopting the existing direct comparator's operation.

For known-safe histories ending at the same `(s,d,b)`, the future accepted
suffix language is identical: legal assignments and local relations depend on
the supplied frame and edge, the graph determines subsequent control states,
and remaining horizon is `H-d`. Induction on the suffix length establishes this
claim. It relies on the accepted model retaining every relevant control/state
dependency. Prefixes with an unknown earlier invariant are not interchangeable
with known-safe prefixes: the former cannot support a fully known witness.
Conservative uncertainty flags and the mandated observable pass must therefore
remain separate. This is not a blanket claim that the two implementations have
identical budgeted abstention behavior.

## One additional operation absent from the current cache code

For each relation `e`, compute `Read_e`, a conservative syntactic set of public
binding names read anywhere in its argument recipes, emitted request, guards
or update expressions. Resolve `emit_path` dependencies through the emitted
expression, rather than considering only the final guard's field names. Include
all emission and update dependencies: an unknown uninspected request field or a
non-scalar/unknown update still makes the existing relation indeterminate.

Represent `project_e(b)` by the values **and presence** of the names in
`Read_e`, with type-sensitive canonical encoding. An absent name differs from
known null; booleans differ from integers. Key a local summary by
`(edge ID, project_e(b))`, instead of `(edge ID, whole b)`.

Store a local delta template containing legal args, exact emitted request,
updated-field values, and the existing known-success/known-rejection/unknown
disposition. Do not store another caller's complete before/after frame. On
reuse, set `before=b` and `after=b overridden atomically by delta.updates`, then
attach that concrete step to the current history. Thus a carried task/context
binding that is irrelevant to this edge is preserved for a later edge that
reads it. This operation can reduce repeated relation evaluation when full
frames differ only in bindings this relation does not inspect.

It does **not** authorize merging whole product states or forgetting those
carried bindings. Such a stronger state projection needs a separately proved
future-dependency closure and witness reconstruction obligation.

## Preservation obligation and argument

For one fixed accepted relation and enumerator, suppose

```text
project_e(b) = project_e(c).
```

Then the same legal argument assignments are generated, including the same
handling of absent binding recipes. For each corresponding assignment, emitted
request, guard truth values, update values and the ternary relation disposition
are identical. Consequently the same local delta templates are valid for both
frames, while their untouched bindings are carried separately.

The argument is structural induction on the existing expression constructors:
constants/args are fixed, binding reads agree by projection, object/array
children preserve equality, and emitted-path lookup preserves its exact
type/presence behavior. Guard equality/presence and full request/update knownness
then agree. False-guard dominance is unchanged; updates use the original old
frame atomically. No condition uses another history's carried state.

Applying the templates with each actual frame therefore preserves that edge's
known successor relation and unknown disposition. Induction over a concrete
path preserves its legal requests, full frames, original transition count and
safety/goal checks. This is an exact local-summary substitution argument,
not a newly proved or mechanized theorem. It makes no performance claim.

Complete memo entries still require the whole corresponding declared argument
domain to have been evaluated. An early witness or budget interruption cannot
publish a complete entry. Existing negative certificates must be checked from
the original input relation, without trusting the cache. Missing coverage,
freshness, or indeterminate relevant facts retain their current restrictions.

## Decisive reduction to the strong comparator

The proposed cache is precisely ordinary free-variable parameterization of a
relation summary. Its inputs are the relation's read bindings, its outputs are
the updated fields/request, and untouched caller state is a frame-rule style
pass-through. The comparator already receives those same expression trees and
is allowed parameterized source summaries. It can compute exactly `Read_e`,
construct the same delta and apply it at each caller. No additional inference,
evidence or decision procedure is needed in the candidate arm.

This is stronger than saying that an SMT encoding exists. The allegedly new
operation itself has an operation-for-operation translation into the granted
summary construction. Restricting the comparator to the current whole-frame
key while advertising a read-projected key as novel would remove an ordinary
applicable optimization from the decisive comparison.

The coarser alternatives remain unsafe. In the existing source fixture
`tests/test_refinement.py:64`, two edges reach `ready` with
`{call:call-A,target:B}` and `{call:call-B,target:B}`. `finish` requires both
`call-B` and `B`; rejecting it globally after the first prefix discards a legal
witness. Changing the second target to `A` makes both paths fail, while pooling
the second call with the first target forges a witness. The projection above
retains both names because `finish` reads both. Removing this correlation cannot
be used to obtain a checking-cost or coverage advantage.

## Comparison that would actually be required

A future engineering experiment could compare whole-frame and read-projected
summary memoization, but must give both candidate and strong direct/symbolic
arms that same optimization. Keep inputs, all legal actions, source/fidelity
assumptions, freshness, horizon and original goal/invariants identical. Charge
read-set analysis, key construction, delta creation, rehydration, allocation,
witness materialization, negative proof/checking, input acquisition and
invalidation to every arm. Include empty hits, unknowns, interruptions and cold
as well as reused execution; method-specific ticks are not interchangeable
hardware cost. No completed matrix is rerun by this screen.

An actual method candidate still needs an operation beyond these granted
summaries/product/cone mechanisms, with a preservation or sound-approximation
obligation and a prespecified advantage after that full accounting. Switching
to universal hidden-state strategies, inventing generated-atom restrictions,
dropping safety/knownness checks or omitting source-coverage obligations would
change the problem instead of providing the missing distinction.

## Inspected-source pins

The following SHA256 values were read on 30 October 2026 for this screen; they
identify inspected local bytes, not authenticated source/runtime fidelity.

| File | SHA256 |
| --- | --- |
| `finite-model-v1.md` | `b22c01783e34d34d2f0e486f1a17b1c05181bf16987277d985d8d4b657bd4b22` |
| `shared-lifting-design-v2.md` | `bcfdf80420f371fed1d6b31fdc602fe6e09c0eb856af33afc861708a41ff4b86` |
| `direct-goal-pruning-fairness-v2.md` | `85ea7a752dfe3da4dd186b1d64fa679e1de25abe78a3d8d1f80d9acb947adec1` |
| `c1-callsite-factoring-screen-v1.md` | `92b913829bf84fb78acaa5bb6ee9c5b32a16582564573936fc4c3bb4b8a6bcb5` |
| `source-recipe-baseline-v0.md` | `9095da49ac46a478ad2faeefc0a2d9e290fba3eac7ac7dc34df4c60d42c5d050` |
| `refinement.py` | `11175edcb99dbec231390ae767ba97dce2e919810844ed544a1ddd109f4b5b3b` |
| `refinement_oracle.py` | `b17feac87ed2972cd1a2c34557b653bdf231345e75a9ab8a919c0b4f1520477e` |
| `refinement_shared_lift_v2.py` | `927538f7ddcb21120913c6c4257754b65a45703db384eec8cd6a28ba9e9b280b` |
| `direct_goal_pruned_v2.py` | `1fba2d0bd747f965056279bbda40b9c28f50f1200b7e9a6869f343ab6f64de51` |
