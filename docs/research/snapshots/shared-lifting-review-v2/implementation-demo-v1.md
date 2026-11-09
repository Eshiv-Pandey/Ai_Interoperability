# Run the admission candidate and development benchmark

The original ten-command demonstration below remains useful for inspecting the
algorithm's request witness, negative certificate and abstention. For the
stronger three-method comparison, use the versioned command below. Its direct
comparator prunes definitely off-goal relations; the
[fairness review](direct-goal-pruning-fairness-v2.md) explains why the original
two-method comparison cannot establish a candidate advantage.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'runs/refinement-scaling/v2/source'
python -B -m interoperability.direct_comparison_v2 run --suite runs/refinement-scaling/v2/inputs/suite.json --work-budget 100000 --timeout-seconds 30 --output runs/admission-demo/comparison-supervisor-1
python -B -m interoperability.direct_comparison_v2 verify runs/admission-demo/comparison-supervisor-1
```

`comparison-supervisor-1` is a new demonstration allocation. The command uses
the captured v2 package and all 66 frozen development profiles. Existing output
directories are refused. The three arms are `baseline` (legacy direct),
`direct_pruned` (corrected direct) and `candidate` (refinement). Reference
decisions still come from the legacy solver; compare candidate outcomes with
`direct_pruned` directly when assessing the corrected comparison. To replay a
v2 bundle into a fresh directory, use this versioned entrypoint's `replay`
command; the original CLI does not register the new negative-certificate kind.

**Rehearsed 29 October:** the [latest supervisor run](../../runs/admission-demo/supervisor-1/result.json)
passed all ten commands with unchanged inputs. It records 11/11 candidate/direct
decision agreements, 7/7 valid conclusive certificates per method and a passing
captured-code replay. The four unknown cases remain visible. The
[independent audit](../../runs/admission-demo/supervisor-1/independent-audit.json)
verified the retained results without rerunning the benchmark.

## Launch the complete demonstration

From the project root, run the following with a new output directory:

```powershell
python -B scripts/run_admission_demo.py --output runs/admission-demo/supervisor-2 --replay
```

This single command records its source/input hashes and execution plan before
running the three decision examples, direct comparison, eleven-case benchmark,
four-case finite smoke suite, verification and captured-code replay. Read
`result.json` for command status, `supported.json` for the request witness and
`benchmark/summary.json` for actual measurements. Command stdout/stderr and
failures are retained. An existing output directory is refused; `supervisor-1`
already contains the completed rehearsal.

For the recorded run, open the [positive witness](../../runs/admission-demo/supervisor-1/supported.json),
[negative certificate](../../runs/admission-demo/supervisor-1/unsupported.json),
[unknown result](../../runs/admission-demo/supervisor-1/unknown.json) and
[comparison summary](../../runs/admission-demo/supervisor-1/benchmark/summary.json).
The detailed commands below allow running these parts separately.

This is the implementation walkthrough for the three-day supervisor target.
It runs Python code, constructs request witnesses and compares admission
decisions. It does not start the historical Linux applications or replay a
consumed application experiment. Python 3.11 or later is required; no package
installation or model API is needed.

The implemented candidate uses witness lifting and context-specific prefix
refinement over supplied finite public-recipe relations. It is a research
prototype based on established refinement ideas. Scientific novelty,
source-to-model fidelity and comparative advantage remain open. The
[algorithm specification](admission-refinement-v1.md) defines the exact claim.

## Run a decision and inspect its witness

From the project root in PowerShell, use a fresh output name:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
python -m interoperability admit --input examples/refinement-development/04-correlated-prefix-refinement.json --method refinement --now 100 --output runs/admission-demo/manual-1/decision.json
```

The authored case contains different histories leading into a shared action.
The candidate must keep task/context/call/target bindings together and scope a
refutation to the failed prefix. In `decision.json`, inspect the result's
decision, reason, work counters and certificate. A supported certificate lists
the transition IDs, chosen public arguments, emitted JSON requests and binding
frames before/after each step. The separate checker must accept the witness.

For an independent direct comparison of that same input:

```powershell
python -m interoperability admit --input examples/refinement-development/04-correlated-prefix-refinement.json --method direct --now 100 --output runs/admission-demo/manual-1/direct.json
```

The direct reference searches a memoized finite relational product. It receives
the same public recipes, binding information, graph, contract and horizon.
Running the original baseline on only the inner abstract graph would answer a
weaker question, so it is not the decisive comparator here.

## Run the comparison benchmark

```powershell
python -m interoperability benchmark --suite examples/benchmark-development/recipe-v1.json --algorithm candidate=interoperability.refinement:evaluate --work-budget 100000 --timeout-seconds 30 --output runs/admission-demo/manual-1/benchmark
```

The suite includes all eleven authored recipe profiles, using logical clock
100. Each solver receives an isolated copy of the same input and the same work
budget. The benchmark retains worker errors, timeouts, mutation failures,
abstentions and failed certificates. It captures the code, input files, source
hashes, result records and summary. The reference and certificate checks are
separate jobs; the direct baseline and reference use the same disclosed module.

Inspect `summary.json` for decision agreement, false support/refusal, unknown
and certified coverage, certificate failures and measured cost. Inspect
`results.jsonl` and the worker records for each underlying outcome. Reference
agreement is not ground-truth accuracy when the reference itself abstains.
Work units are method-specific operations; function and worker/checking timings
are reported separately. No speedup or general reliability claim follows from
one development run.

The four original finite-contract examples remain available as a separate
schema-specific baseline smoke suite:

```powershell
python -m interoperability benchmark --suite examples/benchmark-development/suite.json --timeout-seconds 30 --output runs/admission-demo/manual-1/finite
```

That command does not evaluate the recipe candidate. The recipe wrapper adds
request-construction relations that the old finite input format does not carry.

## Verify or reproduce the software run

```powershell
python -m interoperability benchmark --verify runs/admission-demo/supervisor-1/benchmark
python -m interoperability benchmark --replay runs/admission-demo/supervisor-1/benchmark --output runs/admission-demo/replay-2/benchmark
```

Verification checks the bundle's inventory, case accounting and summary; it is
not a new algorithm execution. Replay executes the captured benchmark code and
copied inputs into a new directory. It reproduces a software development run,
not a live bridge experiment. Existing outputs are never overwritten.

## Show the controller chain and the fresh integration result

The adapter, guarded controller, standalone client, independent admitted-client
verifier and fresh coordinator are implemented. To demonstrate their retained
request evidence, open these three artifacts in order:

1. [Public pending snapshot](../../runs/pending-admission-development/v2/snapshot.json): tools, advertised endpoint, task/context/call bindings and explicit deployment configuration.
2. [Admission profile and certificate](../../runs/pending-admission-development/v2/admission.json): a conditional completion profile and independently checked concrete request witness.
3. [Historical dispatch comparison](../../runs/pending-admission-development/v2/result.json): exact equality with the previously observed B7 request, checked after candidate evaluation.

This is a retrospective chain. It does not send a continuation to the old task.
The [controller report](pending-admission-results-v1.md) separates checked public
facts from the remaining service-history, identity, domain and effect assumptions.

The [latest integration attempt](pending-admission-live-results-v3.md) timed out
before fixture readiness and before client launch. SIGTERM stopped the service;
the owned child was reaped before group inspection, which found an empty group
and no cleanup errors. The service result and task/effect evidence are absent.
B7 was skipped; there are zero fresh candidate application runs. The earlier
post-asyncio exit stall remains unexplained because this attempt never reached
that boundary.

The [independent exported-evidence audit](../../runs/agentops-admission-execution/v4/independent-review/result.json)
verified the partial outcome across 850 exported workspace files and 726 staged
inputs, with zero discrepancies. It confirmed **188 Python plus 26 Node passing
tests** and restoration of the original host configuration. Those suites overlap
prior receipts. Validation and coherent cleanup do not establish successful
live admission.

## What to demonstrate and what remains

Show an accepted concrete request witness, a rejected fully covered finite
recipe, and an unknown caused by incomplete or stale evidence. Then show all
eleven comparison cases, including adverse outcomes. The inputs are authored
development fixtures inspired by the protocol obligations; they are not a
qualified two-domain corpus, independently authored held-out tasks or measured
natural bridge failures.

The [implementation status](implementation-status-v1.json) separates working
software from unproved novelty, missing domain qualification, unverified fresh
live admission and supervisor acceptance. The original
[review-1 results and audit](admission-benchmark-results-v1.md) remain supporting
evidence. Neither the rehearsed benchmark nor the partial live attempt establishes
70% project completion or an extension. The paper is deferred this week.
