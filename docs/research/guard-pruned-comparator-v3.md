# Constraint-pruned direct comparator v3

[The implementation](../../src/interoperability/direct_guard_pruned_v3.py) adds
conventional finite constraint pruning to the goal-pruned direct solver. It is
a stronger-comparator experiment, not a new-algorithm or superiority claim.

The solver resolves each legal argument domain without pooling binding frames.
It computes conservative expression dependencies and enumerates argument prefixes.
Only a fully assigned guard with a definitely false value can remove a prefix.
An emitted-path guard waits for all argument dependencies of the emitted request.
Missing bindings, explicit unknowns and unknown guard values never prune a prefix.
Every retained complete tuple uses the unchanged exact relation interpreter.
Atomic updates and type-sensitive boolean/integer/null/absence distinctions stay
unchanged. The full contracted-observable uncertainty pass and goal cone remain.

Positive and negative certificates retain their existing schemas. The unchanged
v2 checker exhaustively reconstructs the negative product; it does not trust
the new pruning code. Dependency traversal, domain recipes/keys, prefix choices
and partial guard checks have explicit additional work charges. These counters
remain method-specific operations and cannot establish a CPU speed advantage.

Thirteen [adversarial tests](../../tests/test_direct_guard_pruned_v3.py) passed,
including 120 seeded differential relations. An [independent AI source/challenge
review](../../runs/guard-pruned-review/v3-20261110-2/result.json) separately passed
those checks and challenged 200 further three-argument relations: 4,688 original
tuples, 1,407 retained tuples and 3,281 omitted tuples. Every omitted tuple was
definitely false under the unchanged exact step interpreter. This is bounded
software evidence, not a general mechanized proof, human approval or novelty.

The first Windows [supplemental matrix attempt](../../runs/guard-pruned-comparison/v3-20261110-1/failure.json)
is retained. All 66 baseline and guard evaluations at budget 32 returned valid
results; the guard arm had 7 supported, 7 unsupported and 52 unknown outcomes,
with 14 accepted checks and no rejected certificate. The independent reference
worker for `scale-0065` timed out under the initial 10-second allowance. The parent
therefore failed and did not execute its remaining three budgets. This is not a
completed four-budget comparison and supplies no speed or coverage superiority.

The [successor driver](../../scripts/run_guard_pruned_comparison_v3.py) declares
30 seconds per worker before execution, retaining the same four budgets and all
66 original profiles. A [fresh hosted workflow](../../.github/workflows/guard-pruned-comparison-v3.yml)
will execute this separate supplement with the original baseline/reference bytes,
fresh captured sources and the unchanged exhaustive checker. Earlier four-arm
results and the failed Windows allocation are preserved.
