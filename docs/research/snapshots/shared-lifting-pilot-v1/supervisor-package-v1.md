# Supervisor implementation review: 31 October 2026

Updated 29 October. The **admission candidate, comparison benchmark and software demonstration are implemented**. This week's deliverables are the algorithm and benchmark; a draft paper is deferred. Overall 70% completion and an extension have not been established. The [three-day checklist](three-day-implementation-plan-v2.md) separates demonstrated components from remaining work without assigning an invented percentage.

## What to show in eight minutes

1. **Algorithm, two minutes.** Use the original [positive witness](../../runs/admission-demo/supervisor-1/supported.json), [negative certificate](../../runs/admission-demo/supervisor-1/unsupported.json) and [unknown result](../../runs/admission-demo/supervisor-1/unknown.json) to explain the decision contract. Then show the [new shared-lifting source](../../src/interoperability/refinement_shared_lift_v2.py) and [design](shared-lifting-design-v2.md): completed exact prefixes and whole-frame relation evaluations are reused within one invocation, with current-path witness history.
2. **Comparison, three minutes.** Show the verified [66-case v2 results](refinement-scaling-results-v2.md), including the original candidate's adverse comparison with corrected direct. These results cover the original three methods. Show the [new four-arm harness and measurement guide](shared-lifting-comparison-v3.md), then the planned 12-case pilot only if it has executed and passed checking; otherwise show its pending status and the focused software receipts below. Keep conclusive coverage, unknowns and solver-plus-checker costs visible.
3. **Controller integration, two minutes.** Trace the public [snapshot](../../runs/pending-admission-development/v2/snapshot.json), [checked witness](../../runs/pending-admission-development/v2/admission.json) and [historical dispatch comparison](../../runs/pending-admission-development/v2/result.json). This verifies retrospective request equivalence. Present the latest live summary below and its remaining dependency.
4. **Progress and next steps, one minute.** Review the [component status](implementation-status-v1.json) and [checklist](three-day-implementation-plan-v2.md) with the supervisor. Record the actual assessment, remaining implementation/research work and any extension granted.

Pre-open retained evidence; perform any new rehearsal before the meeting. This is the single eight-minute schedule used by the linked plan and walkthrough.

## Run or inspect the implemented software

The new four-arm demonstration uses current source and all eleven original recipe examples:

~~~powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
python -B -m interoperability.shared_lifting_comparison_v3 run --suite examples/benchmark-development/recipe-v1.json --work-budget 100000 --timeout-seconds 30 --output runs/admission-demo/shared-supervisor-1
python -B -m interoperability.shared_lifting_comparison_v3 verify runs/admission-demo/shared-supervisor-1
~~~

The proposed shared-supervisor-1 allocation was unused when this guide was updated; it has not run. This command is distinct from the **planned 12-case, four-budget engineering pilot** (all eleven original examples plus motivating scale-0031). Use the [v3 guide](shared-lifting-comparison-v3.md) for captured replay and measurement scope.

**Legacy demonstrations follow.** They execute the original refinement candidate, and the frozen v2 package contains none of the new shared-lifting modules.

The original ten-command demonstration, including the eleven-case suite and captured-code replay, passed in `supervisor-1`; see its [receipt](../../runs/admission-demo/supervisor-1/result.json) and [independent audit](../../runs/admission-demo/supervisor-1/independent-audit.json). The [walkthrough](implementation-demo-v1.md) provides the individual commands.

To run the algorithm examples and original smoke demonstration into the next unused directory:

```powershell
python -B scripts/run_admission_demo.py --output runs/admission-demo/supervisor-2 --replay
```

To run the original three-method comparison with the frozen v2 source and inputs:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'runs/refinement-scaling/v2/source'
python -B -m interoperability.direct_comparison_v2 run --suite runs/refinement-scaling/v2/inputs/suite.json --work-budget 100000 --timeout-seconds 30 --output runs/admission-demo/comparison-supervisor-1
python -B -m interoperability.direct_comparison_v2 verify runs/admission-demo/comparison-supervisor-1
```

All run commands refuse existing outputs; verification reads an existing bundle. `supervisor-2` and `comparison-supervisor-1` are unused review allocations. Python 3.11 or later is sufficient; these software demonstrations need no API key, network connection or model calls. The recorded four-budget matrix is already allocated; do not execute its once-only driver again. Read-only verification of one retained bundle uses:

```powershell
python -B -m interoperability.direct_comparison_v2 verify runs/refinement-scaling/v2/budget-100000
```

V2 replay must use `interoperability.direct_comparison_v2 replay BUNDLE --output NEW`. That entrypoint imports captured code and registers the new negative-certificate checker; the legacy CLI does not support this proof kind.

## Validation and latest live status

The new solver passed [23 focused tests](../../runs/refinement-shared-lift-software/v2/validation-1/result.json). The resource observer and four-arm harness passed [3 and 5 focused tests respectively](../../runs/shared-lifting-comparison-software/validation-1/result.json), including an actual two-profile temporary run and captured replay. Independent source reviews found no remaining blocker in the [solver](../../runs/refinement-shared-lift-software/v2/source-review-v1.json) or [comparison/resource code](../../runs/shared-lifting-comparison-software/source-review-v1.json). These receipts establish software validation; the 12-case pilot and any new 66-case matrix remain unexecuted.

The earlier [v2 matrix audit](../../runs/refinement-scaling/v2/independent-review/result.json) verified 8,451 files and 1,591 worker invocations, including 535 accepted certificate checks and unchanged legacy outcomes. Its [21 focused comparator/harness tests](../../runs/direct-comparison-software/windows-v1/result.json) remain separately scoped transcribed evidence.

The [latest v4 live allocation](pending-admission-live-results-v3.md) failed N11 readiness before client launch; B7 was skipped and there were zero candidate live calls. It retained 16 startup samples in dependency imports/module initialization, without establishing a root cause or reaching the older post-asyncio stall. SIGTERM/-15 was followed by reaping and an empty process group without cleanup errors. Its frozen software phase passed **188 Python and 26 Node tests**, and the [independent audit](../../runs/agentops-admission-execution/v4/independent-review/result.json) verified 850 workspace files and 726 staged inputs. Configuration remained unchanged during v4; no unrelated service was stopped. The consumed allocation cannot be rerun. A further live attempt requires a fresh plan and the pending resource decision, including permission before stopping the unrelated cluster.

Test counts from overlapping suites must not be added together. These are authored development cases and supplied-model certificates; comparative advantage, scientific novelty, source fidelity, qualified domains and human acceptance remain open. The historical 5% research tracker is separate from implementation completeness.
