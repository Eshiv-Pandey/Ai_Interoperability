# Run the admission candidate and development benchmark

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
python -m interoperability admit --input examples/refinement-development/04-correlated-prefix-refinement.json --method refinement --now 100 --output runs/admission-demo/review-1/decision.json
```

The authored case contains different histories leading into a shared action.
The candidate must keep task/context/call/target bindings together and scope a
refutation to the failed prefix. In `decision.json`, inspect the result's
decision, reason, work counters and certificate. A supported certificate lists
the transition IDs, chosen public arguments, emitted JSON requests and binding
frames before/after each step. The separate checker must accept the witness.

For an independent direct comparison of that same input:

```powershell
python -m interoperability admit --input examples/refinement-development/04-correlated-prefix-refinement.json --method direct --now 100 --output runs/admission-demo/review-1/direct.json
```

The direct reference searches a memoized finite relational product. It receives
the same public recipes, binding information, graph, contract and horizon.
Running the original baseline on only the inner abstract graph would answer a
weaker question, so it is not the decisive comparator here.

## Run the comparison benchmark

```powershell
python -m interoperability benchmark --suite examples/benchmark-development/recipe-v1.json --algorithm candidate=interoperability.refinement:evaluate --work-budget 100000 --timeout-seconds 30 --output runs/admission-demo/review-1/benchmark
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
python -m interoperability benchmark --suite examples/benchmark-development/suite.json --timeout-seconds 30 --output runs/admission-demo/review-1/finite
```

That command does not evaluate the recipe candidate. The recipe wrapper adds
request-construction relations that the old finite input format does not carry.

## Verify or reproduce the software run

```powershell
python -m interoperability benchmark --verify runs/admission-demo/review-1/benchmark
python -m interoperability benchmark --replay runs/admission-demo/review-1/benchmark --output runs/admission-demo/review-2/benchmark
```

Verification checks the bundle's inventory, case accounting and summary; it is
not a new algorithm execution. Replay executes the captured benchmark code and
copied inputs into a new directory. It reproduces a software development run,
not a live bridge experiment. Existing outputs are never overwritten.

## What to demonstrate and what remains

Show an accepted concrete request witness, a rejected fully covered finite
recipe, and an unknown caused by incomplete or stale evidence. Then show all
eleven comparison cases, including adverse outcomes. The inputs are authored
development fixtures inspired by the protocol obligations; they are not a
qualified two-domain corpus, independently authored held-out tasks or measured
natural bridge failures.

The [implementation status](implementation-status-v1.json) separates working
software from unproved novelty, missing domain qualification, real-route
admission integration and supervisor acceptance. The paper is deferred this week.
