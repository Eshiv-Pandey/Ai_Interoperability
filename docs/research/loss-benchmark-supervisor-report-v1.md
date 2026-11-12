# Interoperability benchmark development results

Supervisor update 12 November 2026

We have built a working benchmark to check what survives when one program hands an AI task to another. It measures six areas and saves the evidence behind each score. The package contains 80 fresh Python diagnostic episodes and 13 separately labelled historical records. The full publication study remains incomplete.

In ten prepared tasks, deleting required records caused all ten to fail. A receiver allowed to reread the source recovered all ten. These results check that the benchmark detects the faults we deliberately inserted. They do not measure how often real AI agents lose information.

## Purpose and measurements

An agent is an AI program. MCP is an interface for using tools; A2A is an interface for passing work between agents. A bridge connects these interfaces. We compare the original source, the message before conversion, the message after conversion and the final outcome. Receiving a message does not mean the task succeeded. These initial diagnostics use a Python receiver, with no language model.

| Measurement area | What is counted |
| --- | --- |
| Task completion TCR | Confirmed successes / all attempts, including unknown outcomes. |
| Context retention | Kept / measurable captured facts at extraction, conversion and end to end. |
| Required capability usability | Usable / measured required operations; advertisement remains separate. |
| Constraint and tool fidelity | Passed / measured required identity, policy, binding and availability checks. |
| Recovery success | Successful / observed eligible recovery attempts; retain all eligible attempts and coverage. |
| Overhead vector | Time, messages, bytes, calls and model tokens reported separately. |

Captured absence differs from an unobserved fact. Measurements report denominators, unknowns and coverage; empty or ineligible measurements are N/A. TCR retains all attempts. Context, capability and fidelity are item weighted. No combined information loss percentage, significance test or causal effect is inferred.

<!-- Page break -->

## Initial controlled results

Ten authored decision types cover filtering, triage, selection, joining, arithmetic, counting and graph traversal. Each has one case under eight conditions: 80 episodes, not 80 independent tasks. Every episode resets a read-only fixture. The deterministic receiver sees only the converted observation; separate answer and state checks grade the original task and target.

| Condition | Task passes | Initial facts | Read usable | Checks pass | Recovery |
| --- | --- | --- | --- | --- | --- |
| Reference | 10/10 | 80/80 | 10/10 | 60/60 | N/A |
| Placebo annotation | 10/10 | 80/80 | 10/10 | 60/60 | N/A |
| Dropped records | 0/10 | 70/80 | 10/10 | 50/60 | N/A |
| Wrong tool binding | 0/10 | 70/80 | 0/10 | 50/60 | N/A |
| Wrong task and target | 0/10 | 60/80 | 0/10 | 50/60 | N/A |
| Removed constraints | 0/10 | 70/80 | 10/10 | 50/60 | N/A |
| Harmless record reorder | 10/10 | 80/80 | 10/10 | 60/60 | N/A |
| Dropped records and reread | 10/10 | 70/80 | 10/10 | 60/60 | 10/10 |

Ten attempts per condition provide eight groups and six fidelity checks each, fully observed. Extraction retained 80/80 groups per condition. Initial facts use the first converter output. Records count as ONE group: 70/80 does not mean 87.5% of all knowledge survived. Declared normalization preserves duplicates and harmless reordering, not general meaning.

Read usability uses actual task-bound invocations on separately reset diagnostic clones, not advertised names. Wrong task and wrong binding fail the probes. Probe requests, results and costs are saved separately and excluded from episode budgets and overhead. Usable access can coexist with missing-fact or constraint-driven failure.

Recovery applies a different receiver policy to the same dropped-record observation: reread the original snapshot and retry. Both conditions permit two attempts and two reads, but ordinary dropped records stops after one. The 10/10 result demonstrates that fixture policy, not a gain under unchanged policy. Initial 70/80 retention remains visible.

<!-- Page break -->

## Historical evidence kept separate

These 13 historical bounded attempts remain in four separate families. They were reanalysed from saved bytes, not newly executed services. Task shows successes / attempts; CAP shows observed selected-profile usability. Unknown usability does not establish infeasibility. No rate is pooled across families or native and bridge evidence.

| Case | Task | Facts E C A | CAP | Fidelity |
| --- | --- | --- | --- | --- |
| R1 | 0/1 | 1/1 U1; 1/1 N1; 1/1 U1 | U1 | 2/2 |
| R2 | 0/1 | 1/1 U1; 1/1 N1; 1/1 U1 | U1 | 2/2 |
| R3 | 0/1 | 3/3 U1; 3/3 N1; 3/3 U1 | U1 | 2/2 |
| R4 | 1/1 | 3/3 U1; 4/4; 3/3 U1 | 1/1 | 2/2 |
| P1 | 1/1 | U3; 3/3; U3 | 1/1 | 1/1 |
| P2 | 0/1 | U3; 2/3; U3 | U1 | 1/1 |
| P3 | 0/1 | U3; 1/3; U3 | U1 | 1/1 |
| N1 | 1/1 | U3; U3; U3 | 1/1 | 1/1 |
| N2 | 0/1 | U3; U3; U3 | U1 | 1/1 |
| N3 | 0/1 | U3; U3; U3 | U1 | 1/1 |
| Ops N11 | 1/1 | 5/5; 5/5; 5/5 | 1/1 | 4/4 |
| Ops B6 | 0/1 | U5; U5; U5 | U1 | 2/3 U1 |
| Ops B7 | 1/1 | 5/5; 5/5; 5/5 | 1/1 | 4/4 |

Facts are kept/measured in extraction E, conversion C and end-to-end A order. U combines unknown outcomes and unknown baseline eligibility; N means known ineligible. Coverage is measured/(measured+U), excluding N. An all-unknown stage shows U only. For example, R1 extraction 1/1 U1 has coverage 1/2. All 13 recovery measurements are N/A.

R1-R4 use pinned upstream Amir and mgcrea bridges on a disclosed authored Carol A2A 1.0 port: R1 ordinary Amir typed, R2 Amir tasks update, R3 mgcrea typed, R4 upfront raw. P1-P3 use that port directly; N1-N3 use unchanged original Carol 0.3 directly. P1/N1 are positive controls; P2/P3/N2/N3 are deliberate near misses. Original task and context must complete in the authoritative final read; acknowledgements and passing association checks cannot establish success.

Ops N11/B6/B7 use the original deterministic confirmation double and simulated SQLite. N11 is native raw; B6 is bridge passthrough; B7 configures A2A-Version: 1.0. N11/B7 require original-task completion, one attributed inventory restart and no effect before approval. B6 retains a read error, no continuation and no effect: bounded goal fails while historical whole-case status stays partial. R4 and these raw profiles were selected upfront, not measured recovery trials.

Historical facts cover captured fields only; missing observations remain unknown and opaque handles retain their own namespaces. Checks differ by family. Retained latency/tokens are null. Cost comparisons require matched boundaries.

<!-- Page break -->

## Verification and limitations

Final verification reports 68 passing tests: 22 metric, 10 runner, 23 retained-input, 4 verifier and 9 exporter passes. One additional exporter symlink-creation test was skipped because symlink creation was unavailable in the test environment. Verification regrades 80 fresh episodes, rebuilds 13 retained rows, checks 170 bundle files and verifies a portable mirror of 106 raw inputs, totaling 2,866,511 bytes. Checks cover identity, effects, boundaries, capability probes, costs and summary regeneration. Hashes establish consistency, not external authenticity or scientific independence. The same 68 passes and one skip were obtained in a temporary checkout containing only the portable raw inputs, with all original raw-input paths absent.

The bank and software are single-author, AI-assisted development material, awaiting independent human review. Untouched held-out cases number 0. Authored faults and expected outcomes support review and replay, not claims of population prevalence, causality, novelty or generalization.

## Concrete next steps

1 Have a human check the tasks, expected answers, scoring rules, fact definitions and required operations.

2 Confirm that real agents and bridges can complete the reference task and that both sides of each handoff can be recorded. Record unsupported operations and missing observations.

3 Set aside new test cases and lock the rules, budgets, message formats and scoring before examining evaluation results.

4 Run the qualified agents and bridges, replay controlled changes, and compare with the closest existing work using matching evidence and cost boundaries.

## Artifacts and replay

Definitions: [docs/research/loss-benchmark-metrics-v1.md](loss-benchmark-metrics-v1.md). Fresh results: [runs/loss-benchmark-v1/fresh-development-003/fresh-results.json](../../runs/loss-benchmark-v1/fresh-development-003/fresh-results.json). Retained rows: [runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json](../../runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json). Verification: [runs/loss-benchmark-v1/root-verification-003/verification.json](../../runs/loss-benchmark-v1/root-verification-003/verification.json). Portable inputs: [benchmark/loss-v1/retained-inputs/inventory.json](../../benchmark/loss-v1/retained-inputs/inventory.json). Inputs and traces are preserved; use an unused output path for replay.

```powershell
.venv/Scripts/python.exe -B scripts/run_loss_benchmark_v1.py --output runs/loss-benchmark-v1/supervisor-replay-new --retained runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json
```

<!-- Page break -->

## Appendix scoped overhead for every result

Fresh totals cover ten episodes per condition. Median time measures local Python reset, source/boundary capture, conversion, receiver attempts and state capture; it excludes startup, grading, probes and artifact writing. Bytes are serialized diagnostic transfers; calls are successful episode fixture reads. All fresh model calls and tokens are 0. One timing replicate supports neither a stable ranking nor network latency.

| Condition | Median ms | Request B | Response B | Messages | Calls |
| --- | --- | --- | --- | --- | --- |
| Reference | 0.52210 | 12832 | 1245 | 30 | 10 |
| Placebo annotation | 0.57270 | 13512 | 1245 | 30 | 10 |
| Dropped records | 0.57930 | 10622 | 933 | 30 | 10 |
| Wrong tool binding | 0.50040 | 12852 | 1003 | 30 | 10 |
| Wrong task and target | 0.59230 | 12952 | 1365 | 30 | 10 |
| Removed constraints | 0.57335 | 12413 | 1343 | 30 | 10 |
| Harmless record reorder | 0.58320 | 12832 | 1245 | 30 | 10 |
| Dropped records and reread | 0.71520 | 18018 | 4398 | 70 | 20 |

Retained costs cover one prefix per row. R1-R4 count MCP setup, entities and tool calls; P/N rows count case HTTP and task RPCs, excluding shared discovery. Ops bridges count MCP logs; Ops N11 includes native discovery and evaluator reads. Calls have different scopes; fresh diagnostic probes are separately traced and excluded.

| Case | Request B | Response B | Messages | Calls |
| --- | --- | --- | --- | --- |
| R1 | 2174 | 8642 | 12 | 4 |
| R2 | 3144 | 8904 | 16 | 3 |
| R3 | 1125 | 19515 | 13 | 4 |
| R4 | 1451 | 20150 | 13 | 4 |
| P1 | 929 | 3320 | 8 | 4 |
| P2 | 869 | 3442 | 8 | 4 |
| P3 | 923 | 3246 | 10 | 5 |
| N1 | 855 | 3332 | 8 | 4 |
| N2 | 817 | 3476 | 8 | 4 |
| N3 | 883 | 3312 | 10 | 5 |
| Ops N11 | 1497 | 21033 | 18 | 8 |
| Ops B6 | 1345 | 21244 | 17 | 6 |
| Ops B7 | 1945 | 29237 | 19 | 7 |

B means bytes. Counts cover stated boundaries; retained latency and tokens remain unknown. These inventories are not comparable performance estimates.
