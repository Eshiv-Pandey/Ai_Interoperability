# Fresh loss benchmark runner v1

This is a **FRESH CONSTRUCTED software diagnostic**. It executes deterministic Python fixtures and authored conversion faults. It is not a real MCP/A2A conversion experiment, an LLM experiment, production AgentOps evidence, or a held-out confirmation study. Model calls and model tokens are zero.

The runnable suite is `scripts/run_loss_benchmark_v1.py`, with ten public development cases in `benchmark/loss-v1/development-cases.json`. Each case has its own task decision: service health filtering, incident triage, latency maximum selection, incident/service ownership join, capacity subtraction and thresholding, scoped deployment timestamp selection, alert counting, incident duration arithmetic, bounded dependency graph traversal, and snapshot age/version selection. There is one case per family. Profiles and timing replicates do not create more independent tasks.

Run from the workspace using a fresh output path:

```powershell
.\.venv\Scripts\python.exe -B scripts/run_loss_benchmark_v1.py --output runs/loss-benchmark-v1/fresh-development-new
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_loss_benchmark_runner_v1.py -v
```

An existing output path is refused, including an empty directory. `--seed` controls randomized cell order only. `--replicates` repeats the same deterministic cases to examine local Python timing variation; the default is one. `--profiles` can restrict the matrix. `--retained path/to/normalized-episodes.json` combines previously normalized retained episodes with the new run while preserving evidence kinds. `normalized-episodes.json` contains fresh rows only, and `combined-episodes.json` contains both kinds. The metric engine separates evidence kinds in its summaries. The retained input must already satisfy its strict episode schema; the runner does not fill missing measurements with successes or zero costs.

## Pipeline and controls

Every cell resets a new in-memory read-only fixture, records independent pre-sender source truth from the full pinned case, reads the task snapshot, forms a sender message, converts it, runs the receiver, and captures the final fixture state. Source truth is constructed independently of the sender output so that a later sender extraction fault can be measured. The receiver sees the converted observation only. It cannot see the case gold answer. The gold grader separately checks the final answer, original task identifier, correct target, forbidden effects, unchanged fixture contents, and the common runtime policy. A separate truth evaluator validates the pinned gold against the complete original records and constraints; it never calls the receiver or converter. These checks reduce circular grading but do not establish independence from the authors of this development software.

All profiles for a case have byte-identical sender information, the same original required binding (`fixture.read_snapshot.v1`), the same enforced read-only runtime policy, and the same initial state. Seven profiles use `single_attempt_no_recovery_v1`. The recovery profile combines the same dropped-fact conversion with `missing_fact_public_snapshot_reread_v1`, a different declared receiver policy that can use the common episode budget. This is a conversion-plus-policy treatment and is labeled with both `conversion_profile` and `receiver_policy_id` in episode metadata. The finite suite contains these profiles:

| Profile | Conversion and intended diagnostic |
| --- | --- |
| `reference` | Identity conversion. |
| `placebo_identity` | Adds an ignored annotation while preserving the task payload. |
| `dropped_fact` | Removes the records field; the receiver reports a missing fact. |
| `capability_mismatch` | Replaces the advertised read binding with a restart binding; the receiver cannot use its required capability. The fixture still enforces the original read binding. |
| `wrong_task` | Changes the receiver task identifier and target; a correct-looking answer is rejected by the independent task grader. |
| `constraint_loss` | Removes selection constraints; the receiver makes a different task decision. The original runtime policy is still enforced. |
| `safe_equivalent` | Reverses snapshot record order; every task answer and declared fidelity check remains correct. A raw representation diagnostic records the permutation, while task-specific fact-group normalization preserves context equality. |
| `recovery` | Starts with the same missing-fact observation as `dropped_fact`, requests a reread for that original task, and retries once. |

The common episode budget is two receiver attempts and two fixture snapshot reads. Reference and ordinary fault profiles stop after their first result. Recovery uses the same initial state and budget, preserves its first failed attempt in the raw trace, and obtains the missing records through a declared reread. It is triggered by the receiver's missing-fact status, not by access to a gold failure label. Its recovery denominator contains only the declared recovery profile. Other cells are explicitly `not_applicable`.

Context retention uses the initial converter output as `received`, so successful recovery cannot erase the original conversion loss. The repaired context remains in `metadata.post_recovery_context` and the raw recovery trace. Its units are eight explicit task-specific fact groups, not natural-language meanings. Each bank task explicitly declares record order irrelevant. The records fact group is sorted by canonical full-record JSON while preserving duplicates and field types; harmless record permutation therefore preserves this task-specific context. The metric engine retains generic type-sensitive equality and makes no broad semantic equivalence claim.

The suite has complete observation access to its own in-memory values. A known missing field is represented with `observed.received=true`, `present.received=false`, and `received=null`. This means observed absence, not missing measurement. Retained unknown observations remain unknown in the separate normalization/schema workflow.

Capability usability is qualified by actual read invocations using the reference and receiver task identifiers and tool bindings on two separately reset diagnostic clones. The wrong-task and wrong-binding profiles fail these probes even when a required tool name is advertised. Each raw trace retains exact probe requests, results, hashes, clone state and diagnostic costs. These calls do not consume the policy episode budget, alter its state, or count toward its messages, bytes, reads or time. The probes measure this fixture's task-bound read capability, not external MCP/A2A capability execution.

## Costs and artifacts

`wall_ms` uses `perf_counter_ns` around fixture reset, pre-sender source capture, sender snapshot read, conversion, all receiver attempts, state capture, and boundary serialization. It excludes Python process startup, gold grading, isolated diagnostic capability probes, context projection, metric scoring, and artifact I/O. This is measured Python pipeline time, including boundary capture overhead; it cannot estimate network, provider, or native protocol latency. `messages` counts the explicit transferred payloads, `request_bytes` and `response_bytes` sum their canonical UTF-8 serialized sizes, and `tool_calls` counts actual successful reads of the controlled fixture in the policy episode. These are not external provider tool calls. `model_tokens=0` means no model was invoked, not free inference.

Each cell retains `raw-trace.json` with every boundary payload, serialized byte size, SHA-256, explicit transfers, final receiver output, gold assessment, and measured costs. A matching normalized episode uses the metric engine's strict schema. The output also contains the case snapshot, code snapshots and SHA-256 identities, randomized allocation, normalized/combined episodes, combined metrics, per-profile results, an execution receipt, and a hashed artifact manifest.

The development result can demonstrate that injected loss is detected, task success is graded separately from payload equality, and a same-budget reread can recover a missing observation. It cannot close a real-route eligibility gate, prove novelty, establish general task success, justify a claim of measured MCP-to-A2A conversion overhead, or support confirmation-study statistics.

## First fresh execution

`runs/loss-benchmark-v1/fresh-development-001` retains the first successful 80-cell execution: ten distinct decision families, eight profiles, one timing replicate, no retained episodes and zero held-out cases. Its earlier implementation inferred capability usability from the descriptor, used the final repaired observation for recovery context, and treated a record permutation as representation loss. This snapshot is retained for audit and is superseded for current measurements by the corrected run described below. Its task grader outcomes remain as recorded. These expected outcomes are diagnostic controls authored with the fault profiles, not research estimates from unseen tasks.

| Profile | Task grader passes | Median scoped Python pipeline time (ms) |
| --- | ---: | ---: |
| reference | 10 / 10 | 0.26895 |
| placebo_identity | 10 / 10 | 0.26910 |
| dropped_fact | 0 / 10 | 0.26405 |
| capability_mismatch | 0 / 10 | 0.25450 |
| wrong_task | 0 / 10 | 0.27010 |
| constraint_loss | 0 / 10 | 0.26875 |
| safe_equivalent | 10 / 10 | 0.27430 |
| recovery | 10 / 10 | 0.37750 |

Reference transferred 12,832 request bytes and 1,245 response bytes over 30 declared messages with ten controlled snapshot reads. Recovery transferred 18,018 request bytes and 4,398 response bytes over 70 messages with twenty snapshot reads. These totals cover ten tasks per profile; the raw traces provide the exact per-cell accounting. A single local timing replicate provides no stable performance ranking.

Ten runner controls now pass, covering all fault/task combinations, independent gold rejection of target/task/effect mistakes, independently constructed pre-sender source truth, order normalization that preserves duplicate records, actual isolated task-bound capability invocation, unchanged sender and reset state, observed absence, same initial recovery failure and budget, preserved initial conversion loss after recovery, binding/read budget enforcement, exact serialized byte identities, schema/manifest roundtrip, and refusal to overwrite output.

## Corrected execution and retained integration

`runs/loss-benchmark-v1/fresh-development-002` is a corrected fresh-only run. `runs/loss-benchmark-v1/fresh-development-003` is the corrected combined run, using `runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json` as its retained input. Both preserve the original run directory. The combined run contains 80 fresh constructed episodes and 13 normalized retained episodes, for 93 total. Its evidence kinds are `fresh_constructed`, `retained_bridge`, and `retained_native`; the engine leaves heterogeneous combined scores unset and summarizes the evidence groups separately.

The corrected run still grades reference, placebo, record permutation, and recovery at 10/10 task passes each; the other four fault profiles remain 0/10. Actual isolated receiver capability probes pass for ten tasks in every profile except `wrong_task` and `capability_mismatch`, which each have zero usable task-bound read invocations. Initial records are absent in all ten `dropped_fact` and all ten `recovery` conversion observations, so recovery success preserves rather than erases that conversion loss. The safe record permutation changes the raw array representation and preserves all eight declared fact groups.

The combined run's median scoped Python times are 0.52210 ms for reference and 0.71520 ms for recovery. These are one local timing replicate across ten different decisions; they include source/boundary capture and exclude isolated probes. The retained and fresh measurements must not be pooled into a common performance or success estimate.

To reproduce the corrected combined suite into a new directory, use an unused output name:

```powershell
.\.venv\Scripts\python.exe -B scripts/run_loss_benchmark_v1.py --output runs/loss-benchmark-v1/fresh-development-new-combined --retained runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json
```

The executed output is `fresh-development-003`; using that name again is intentionally refused. Its `execution-receipt.json`, `allocation.json`, `sources/`, cell traces, normalized episodes, per-profile results and manifest retain the exact execution inputs and code identities.
