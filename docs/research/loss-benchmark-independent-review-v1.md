# Independent software review: fresh loss benchmark v1

12 November 2026. A separate reviewing agent inspected the fresh runner and
metric engine, ran their existing suites, and performed additional adversarial
checks without editing either implementation or its tests. This review excludes
the retained normalizer authored by that reviewing agent. It is AI-authored
software review, not human validation, scientific approval, or a new service/model
experiment.

The checked implementation supports the documented finite constructed diagnostic
scope. No blocking issue was found in the reviewed task grading, recovery,
capability invocation, context projection, or evidence grouping. The conclusions
below concern these exact source versions and the ten pinned development cases.

## Exact versions and execution

The audit used the workspace `.venv/Scripts/python.exe`, Python **3.13.1** on
Windows. Episode schema is `loss_benchmark_episode_v1`; summary schema is
`loss_benchmark_summary_v1`.

| Reviewed source / test / input | SHA-256 |
| --- | --- |
| `scripts/run_loss_benchmark_v1.py` | `519be16c0f33cc9c23bce225e56c25557a39f92b9c726e7014cbda415c15b4b8` |
| `src/interoperability/loss_benchmark_v1.py` | `6d3e7f1678300b84fe3c69094c82b3365bd58dcf2e0f3173881eceb480f64e4d` |
| `tests/test_loss_benchmark_runner_v1.py` | `eb7a56ab7f44c2851f046eea9acb91cf2094994ba41573617479b0bb6b2b1d93` |
| `tests/test_loss_benchmark_v1.py` | `2ea2ab0664338fec9735b8d2a4ce3a4366537b928e66c3057a895f191c7c7c8f` |
| `benchmark/loss-v1/development-cases.json` | `7ec2a84309aa5d02ad09ada7e0fd0df10a5adf52463edef9f9fe32ff5896c3ba` |

The hashes from the additional spot-check execution agree with a separate
post-test read. No reviewed source file was edited by the reviewer.

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_loss_benchmark_runner_v1.py -v
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_loss_benchmark_v1.py -v
```

Results: **10 runner tests and 22 engine tests passed**, with no failures,
errors, or skips. The engine suite's existing-output rejection intentionally
prints an argparse error before that test passes. The runner suite executes an
80-cell constructed matrix in an unused temporary directory, verifies its
artifact hashes, then checks that reusing the directory fails without replacing
the existing manifest. These are software controls, not 80 real bridge trials.

## Findings from code and adversarial checks

**Task completion is grounded in the task goal.** `grade` requires a completed
receiver result with canonical equality to the independently pinned expected
answer, the original task ID, the original target (including fixture reads),
absence of the declared forbidden effects, unchanged fixture content, and the
actual fixture's common read-only policy. Delivery acknowledgements and
capability metadata cannot independently produce a task pass. Additional
mutations to answer, task ID, target, forbidden effect, and content state all
failed grading.

**The deterministic policy does not receive private gold.** `make_sender` and
`source_truth` expose task, records, tool binding, policy, and budget; they do not
include the case's `gold` object. `receiver_decision` accepts only the converted
wire observation. In an additional check, poisoning the case's gold while
preserving task/records left the policy answer equal; changing the received
service record changed the policy answer while the independent gold stayed
equal. `gold_truth` checks the pinned gold separately before execution. This is
logical function/data separation within one authored Python program, not process
isolation from hostile code or proof of unbiased task design.

**Recovery cannot erase initial loss.** The `recovery` conversion omits the same
records as `dropped_fact`; the first receiver attempt remains `missing_fact` in
the raw event trace. A task-bound public fixture reread can supply records for a
second attempt under the common two-attempt/two-read budget. The final gold
grader decides recovery success. Normalized context still records the initial
converter output, including `records` with known absence, while repaired context
is separate metadata. The additional check observed successful task/recovery
with one initial conversion loss still counted. Recovery is a changed receiver
policy under the same omission profile, not a novel converter or an independent
task family.

**Capability usability is an actual scoped invocation.** `capability_probe`
creates an isolated fixture clone and invokes `read_snapshot` with the observed
task ID and tool binding. Wrong-task and capability-mismatch probes produced
actual rejected calls, while positive reference probes read successfully.
Requests/results and probe costs remain in the raw trace. These probes are
diagnostic clones outside the task episode state, budget, and reported episode
costs; they are not an extra action available to the receiver policy. The claim
is usability of `fixture.read_snapshot.v1` under the selected task binding, not
whole-interface capability of any real MCP/A2A bridge.

**The safe transformation has a narrow declared equivalence.** Only the snapshot
record list is canonical-sorted for context measurement, because all ten pinned
tasks explicitly disregard record order. Full records, duplicate multiplicity,
field values, and JSON types survive projection. Raw order changes remain in
the trace/metadata. Additional checks confirmed reversed lists match, while an
added field, a changed value, and boolean-versus-integer differences remain
unequal. The generic engine keeps array order and recursively compares JSON
types; this runner-specific normalization does not provide natural-language
semantic equality or apply to arbitrary future tasks.

**Mixed evidence is not pooled.** The engine leaves overview `scores=null` for
mixed evidence kinds and for unrelated retained families. Descriptive task
counts remain visible, with scores in evidence/family/route groups. Additional
grouping checks used explicitly synthetic retained-shaped records solely as
software controls, not as retained empirical observations. They confirmed both
non-pooling boundaries. The fresh overview may aggregate the authored finite
bank and profiles, so its family/profile groups must still be inspected.

**Unknown observations and units remain explicit.** Known absent payload fields
differ from uncaptured values; unknown source presence cannot produce a claimed
zero extraction loss. Boolean/integer aliases do not pass exact context equality.
Task completion uses all attempts in its main denominator and exposes observed
rate/coverage separately. Context, capability, fidelity, recovery, and each cost
unit are separate operational areas, with no composite loss percentage. Fresh
timing is local Python diagnostic wall time with a stated boundary; zero model
tokens reflects no model invocation. The engine validates source-hash syntax,
but verifying file bytes is an external artifact-verification responsibility.

## Limits of this review

The bank contains ten public authored development cases with injected faults,
one task per family, and no held-out cases. The receiver and grader are separate
authored deterministic implementations, not independently supplied natural
agents. The fixture represents in-memory reads and a fixed effect-record shape;
it is not a general untrusted-service verifier or a complete arbitrary-input
case-schema validator. Repetitions measure local timing variation and do not add
independent task families. No external protocol transport, native service,
provider/model efficacy, production remediation, scientific novelty, causal
advantage, or statistical generality was evaluated.

This audit does not independently review the retained normalizer or substitute
for the root artifact verifier and source/data snapshot checks. It supplies
bounded software evidence only, awards no checkpoint credit, and does not close
CP2 or establish human review.
