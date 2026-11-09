# Supervisor implementation review: 31 October 2026

Updated 29 October. The **admission candidate, comparison benchmark and software demonstration are implemented**. This week's deliverables are the algorithm and benchmark; a draft paper is deferred. Overall 70% completion and an extension have not been established. The [three-day checklist](three-day-implementation-plan-v2.md) separates demonstrated components from remaining work without assigning an invented percentage.

## What to show in eight minutes

1. **Algorithm, two minutes.** Open the [positive witness](../../runs/admission-demo/supervisor-1/supported.json), [negative certificate](../../runs/admission-demo/supervisor-1/unsupported.json) and [unknown result](../../runs/admission-demo/supervisor-1/unknown.json). In the positive example, a failed prefix is refuted before the valid correlated `call-B`/`B` request path is found. Show the [implementation](../../src/interoperability/refinement.py) and [algorithm specification](admission-refinement-v1.md). It is an implemented refinement adaptation; scientific novelty is still open.
2. **Fair comparison, three minutes.** Show the [three-method result report](refinement-scaling-results-v2.md) and the captured [high-budget summary](../../runs/refinement-scaling/v2/budget-100000/summary.json). The same 66 authored profiles and four allowances are evaluated by legacy direct, goal-pruned direct and the candidate. The [fairness correction](direct-goal-pruning-fairness-v2.md) explains why the original direct solver did unnecessary off-goal work. Compare the candidate with the corrected direct arm, including adverse cases, unknowns and certificate-check costs. These are development variants, not independent application workloads or a qualified study.
3. **Controller integration, two minutes.** Follow the public [snapshot](../../runs/pending-admission-development/v2/snapshot.json), [checked witness](../../runs/pending-admission-development/v2/admission.json) and [historical dispatch comparison](../../runs/pending-admission-development/v2/result.json). Request equivalence is verified retrospectively. The [latest live attempt](pending-admission-live-results-v2.md) failed readiness before client launch; B7 was skipped. It has coherent forced cleanup, but no fresh admitted request, task completion or effect.
4. **Progress and next steps, one minute.** Review the [component status](implementation-status-v1.json) and the checklist with the supervisor. Record their assessment of this week's implementation deliverables, the remaining live integration and research work, and any extension actually granted.

## Run or inspect the implemented software

The original ten-command demonstration, including the eleven-case suite and captured-code replay, passed in `supervisor-1`; see its [receipt](../../runs/admission-demo/supervisor-1/result.json) and [independent audit](../../runs/admission-demo/supervisor-1/independent-audit.json). The [walkthrough](implementation-demo-v1.md) provides the individual commands.

To run the algorithm examples and original smoke demonstration into the next unused directory:

```powershell
python -B scripts/run_admission_demo.py --output runs/admission-demo/supervisor-2 --replay
```

To run the stronger comparison with the frozen v2 source and inputs:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'runs/refinement-scaling/v2/source'
python -B -m interoperability.direct_comparison_v2 run --suite runs/refinement-scaling/v2/inputs/suite.json --work-budget 100000 --timeout-seconds 30 --output runs/admission-demo/comparison-supervisor-1
python -B -m interoperability.direct_comparison_v2 verify runs/admission-demo/comparison-supervisor-1
```

Both run commands refuse existing outputs; verification reads an existing bundle. `supervisor-2` and `comparison-supervisor-1` are unused review allocations. Python 3.11 or later is sufficient; these software demonstrations need no API key, network connection or model calls. The recorded four-budget matrix is already allocated; do not execute its once-only driver again. Read-only verification of one retained bundle uses:

```powershell
python -B -m interoperability.direct_comparison_v2 verify runs/refinement-scaling/v2/budget-100000
```

V2 replay must use `interoperability.direct_comparison_v2 replay BUNDLE --output NEW`. That entrypoint imports captured code and registers the new negative-certificate checker; the legacy CLI does not support this proof kind.

## Validation and limits

The latest frozen Linux validation passed **146 Python tests plus 26 Node tests**. The [retained logs](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-admission-live-v1/phase-software/result.json) and [independent export audit](../../runs/agentops-admission-execution/v3/independent-review/result.json) establish that scope. A further **15 comparator tests and 6 comparison-harness tests passed**, covering old/new proof kinds and captured replay; their [receipt](../../runs/direct-comparison-software/windows-v1/result.json) explicitly transcribes the observed tool outputs. Test counts from overlapping historical suites must not be added together.

The [independent matrix audit](../../runs/refinement-scaling/v2/independent-review/result.json) verified all 8,451 files and 1,591 worker invocations, including 535 accepted certificate checks and unchanged legacy outcomes. The [startup diagnostic addition](agentops-startup-diagnostics-v1.md) passed 11 focused tests with raw logs; it is not yet a deployed live result.

The latest native prerequisite timed out before readiness. Its service received SIGTERM and exited -15; the owned child was reaped before an empty-group check with no cleanup errors. Only observer-installation and asyncio-entry markers exist. The absent service result makes the interpreter-exit check incomplete, and the earlier post-asyncio stall remains unexplained. The temporary WSL setting was restored to its original bytes. The [live-results report](pending-admission-live-results-v2.md) retains these distinctions.

A successful fresh live admission, qualified second domain, independently reviewed evaluation corpus, demonstrated contribution against strong comparators and supervisor acceptance remain open. The historical 5% research tracker uses a full research-and-paper rubric; it is not an implementation percentage. The candidate's finite certificates establish supplied-model results, not automatic fidelity to an application's behavior. No paper work is scheduled for this week's review.

## Latest readiness for the next live attempt

The [versioned startup pipeline](pending-admission-live-plan-v3.md) is implemented and independently reviewed. Its initial Windows run recorded 62 passes and three platform-specific skips; the final changed plan/phase/chain suites passed 20 tests. The next `v4` application allocation has not been staged or launched.

A [WSL resource probe](../../runs/agentops-admission-execution/v4-resource-probe/result.json) failed before any application import, with `HCS/0x800705aa` (insufficient system resources) while Windows reported 99% memory use. The original WSL configuration stayed unchanged. Freeing host resources is the next prerequisite; no new live outcome or project percentage follows from this probe. The algorithm/benchmark demonstration remains available independently of WSL.
