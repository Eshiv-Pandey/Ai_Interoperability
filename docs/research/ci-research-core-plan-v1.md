# Hosted core reproduction plan v1

This prospective run evaluates the current tracked checkout on a fresh GitHub
Ubuntu 24.04 runner with Python 3.13.1. It requires only the Python standard
library. The experiment makes zero model calls and zero application calls and
uses no API keys, SDK installation or experiment network requests.

## Fixed comparison

The complete 66-profile authored development suite is
`runs/refinement-scaling/v2/inputs/suite.json`, with every profile bound by the
existing `manifest.json`. Every case remains in the denominator. Evaluation
clock is 100. Budgets are 32, 256, 4096 and 100000, with the same budget per
algorithm and a 30-second worker timeout. The independent certificate checker
retains its existing 2000000 work-unit allowance. Algorithm work counters are
implementation-defined deterministic units; equal limits do not imply equal
CPU work.

| Arm | Existing module |
| --- | --- |
| baseline | `interoperability.refinement_oracle` |
| direct_pruned | `interoperability.direct_goal_pruned_v2` |
| candidate | `interoperability.refinement` |
| shared_lift | `interoperability.refinement_shared_lift_v2` |

`interoperability.shared_lifting_comparison_v3` captures the current package and
dispatches fresh resource-instrumented workers for every algorithm, reference
and required certificate check. Its verifier reconciles input/source hashes,
dispatches, replies, retained result flags, certificates and resource summaries.

## Verification and reconciliation

The driver first captures current package files, existing Python tests, required
development fixtures, the generator and this plan. It runs ten existing test
modules covering correlated frames, contextual refinement, caching, budget
interruptions, forged certificates, fairness, input mutation, worker failures,
timeouts, immutable allocations, captured replay and adversarial verifier
tampering. Failed or skipped tests fail this run.

Each of the four fresh benchmark bundles is separately verified. Fresh outputs
are compared against the SHA256-pinned Windows four-arm results in
`runs/shared-lifting-scaling/v3-20261110-1/budget-*/results.jsonl`. Comparison
requires identical case membership, families, clocks, semantic input hashes,
reference validity, complete solver results and certificates, deterministic
solver statistics, input integrity, validity/agreement flags and independent
checker results. This gives 1056 algorithm comparisons plus all reference and
required checker comparisons.

Excluded from cross-machine equality are only internal `stats.elapsed_ns` and
execution-level timing, process and resource observations. All of those raw
observations remain retained. Linux memory uses `resource.getrusage().ru_maxrss`
converted from KiB to bytes; Windows uses
`GetProcessMemoryInfo.PeakWorkingSetSize`. Both include interpreter/import/input
overhead but are different OS meters. There is no claim that their timings or
memory are equal, and overlapping timing fields must not be added.

## Evidence and limits

Each run/attempt consumes an exclusive new output directory. Existing frozen
allocations are read-only and never reused. A sealed plan binds original and
captured inputs, runtime and GitHub revision. Before and after execution,
original/captured inventories must remain unchanged. The artifact retains all
worker dispatches, replies, certificates, command argv/process receipts, binary
stdout/stderr streams, verifications, differences, failures and a final hashed
manifest. A failed budget does not prevent later budgets from being attempted.

Workflow: `.github/workflows/research-core-reproduction.yml`.

```text
python -I -S -B scripts/ci_research_core_v1.py --check-inputs
python -I -S -B scripts/ci_research_core_v1.py --execute --output runs/ci-research-core/NEW-RUN-ATTEMPT
```

This is a software reproduction of authored development results. It establishes
neither independent human task/gold review, held-out application performance,
algorithm novelty nor superiority. The retained Windows result is that shared
lifting adds zero certified cases beyond goal-pruned direct at every budget;
the prospective hosted run must reproduce this or retain the differences.
