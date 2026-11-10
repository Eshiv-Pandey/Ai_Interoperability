# Implementation acceptance audit: 10 November 2026

The algorithm implementation, four-method benchmark engine and AgentOps native
admission route **pass the implementation criteria below**. This audit evaluates
working code and retained execution evidence. Project percentage is owned by the
separate implementation status tracker.

The focused source review found no unresolved material defect. A fresh run of
`test_refinement_shared_lift_v2`, `test_shared_admission_v1`,
`test_direct_goal_pruned_v2`, `test_shared_lifting_comparison_v3` and
`test_pending_admission` passed **79 tests in 15.963 seconds**, with no failures
or skips. The comparison tests include actual isolated-worker execution and a
captured-source replay. No application or model was launched by these tests.

## Algorithm and certificate acceptance

Pass criteria are: explicit finite input/clock/budget; supported witnesses and
complete-coverage unsupported certificates accepted by the independent checker;
unknown without a certificate for uncertainty, stale evidence or exhausted
budget; correlated frames/history preserved; only complete call-local cache
entries published; malformed inputs and rejected certificates retained as failures.

The reviewed [shared solver](../../src/interoperability/refinement_shared_lift_v2.py)
keeps exact prefix histories and keys relation reuse by edge plus complete typed
binding frame. Its cache is local to one evaluation. Interrupted expansions are
not published. A negative decision still requires complete model and relation
coverage. The [command](../../src/interoperability/shared_admission_v1.py) checks
each conclusive result using
`direct_goal_pruned_v2.check_certificate`; unknown has no certificate. The checker
uses preserved independent recipe checks and independently reconstructs the
corrected comparator's negative product closure.

The tests reject forged witnesses/cuts, cross-history binding combinations,
Boolean/integer key conflation, cache publication after interruption, malformed
results and non-Boolean checker acceptance. The retained
[standalone rehearsal](../../runs/admission-demo/shared-rehearsal-1/inspection.json)
also contains supported, unsupported, opaque-unknown and budget-unknown receipts.
These decisions are conditional on the supplied finite recipe model.

## Four-method benchmark acceptance

Pass criteria are: four declared modules receive the same profile bytes, clock
and per-solver budget; isolated workers retain actual dispatch/reply/source
records; every conclusive result gets an independent certificate worker; all
planned cases and unknowns remain in the denominator; verification derives flags
from retained replies and rejects tampering even after manifest rehashing.

The [v3 engine](../../src/interoperability/shared_lifting_comparison_v3.py) meets
these criteria. Fresh read-only verification passed all four preserved budget
bundles: **2,003 worker jobs and 683 certificate jobs**, with 66 profiles at each
budget. Worker/checker failures, timeouts, rejected certificates and source/input
mutations are absent in this matrix. Tests also verify configuration restoration,
immutable allocations and dispatch/validity/checker-flag tampering rejection.

| Work budget | Legacy direct | Goal-pruned direct | Original refinement | Shared lifting |
|---:|---:|---:|---:|---:|
| 32 | 12/66 | 20/66 | 24/66 | 2/66 |
| 256 | 52/66 | 54/66 | 50/66 | 39/66 |
| 4,096 | 54/66 | 54/66 | 53/66 | 53/66 |
| 100,000 | 54/66 | 54/66 | 54/66 | 54/66 |

Cells count accepted conclusive certificates. Shared lifting adds no certified
case beyond the fair direct comparator and loses coverage at smaller budgets.
Passing engine acceptance does not require a favorable candidate result.

## Native admission-route acceptance

Pass criteria are: actual original service/task execution, native prerequisite
before bridge dispatch, public identity binding, independently valid certificate
bound to actual wire, exactly the intended effect and clean source/runtime and
process lifecycle checks.

[Run 42808110286](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42808110286)
passes these criteria. The trusted local audit reran the native/admitted/service,
raw ASGI, startup, asyncio, interpreter-exit and process validators. N11 and B7
completed their original tasks and each made exactly one expected inventory
effect/audit row. B7's valid certificate matched one actual continuation, using
33 of 100,000 work units. All 1,138 exported files and 864 staged inputs matched
their hashes. Both client/service exits were zero with empty owned groups and no
forced cleanup. See the [native review](../../runs/ci-agentops-native/download-42808110286-independent-review.json).

The executed B7 adapter uses `pending_admission -> refinement.evaluate`, the
original witness/refine candidate. **Shared-lifting v2 was not executed in this
application route.** The shared solver's implementation and benchmark acceptance
are separate from the native route's acceptance.

The [machine-readable audit](../../runs/implementation-acceptance/audit-v1.json)
records criteria, hashes and evidence. These accepted implementation packages
do not assert algorithmic novelty, held-out generalization, a second qualified
application or completion of a research paper.
