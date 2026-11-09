# Source-case grading implementation: 30 October 2026

The 31 October supervisor review requires an implemented admission algorithm,
benchmark and runnable demonstration. No paper is required this week. This
page records grading software separately from live benchmark outcomes.

The [stronger-check implementation](agentops-stronger-grading-v1.md) adds
independently audited reply/dependency, sampled-state and client/server boundary
software. Its 41/24/16 synthetic test captures passed with zero failures or skips.
This successor work preserves the original configured metric described below.

The existing admission demonstration is implemented and rehearsed. The shared
solver remains experimental: its retained pilot establishes no consistent
coverage or speed advantage and does not establish scientific novelty. This
grading work does not change that result or the algorithm defaults.

## Original benchmark metric

[The stdlib trajectory matcher](../../src/interoperability/agentops_required_trajectory_v1.py)
realizes the original AgentOps `tool_trajectory_avg_score`, configured at
threshold 1.0. Original `evals/test_config.json` does not configure an answer
judge. Required calls must occur as an ordered subsequence with recursively
required argument values; extra actual calls are allowed. Same-event part-array
order can satisfy the original metric. Repeated partial events are accumulated,
without deduplication or UUID/time sorting.

The metric is separate from successful replies, awaited response dependencies,
business effects, memory effects, schema validity and answer grounding. The
[all-case obligations](upstream-agentops-grading-obligations-v1.md) preserve
these stronger requirements for all 21 source cases and 22 user turns. Passing
the original metric alone assigns no full task or native qualification grade.

## Original runtime evidence

[The passive runtime journal](../../scripts/agentops_runtime_stream_v1.py)
serializes each original bound `run_async` event before yielding the identical
event to the A2A converter. It preserves sends, recoverable throws and cleanup;
capture faults disable recording while preserving original delegation. The
recorder itself imports no SDK and installs no patch. Complete persisted root
and per-call receipts are required for ordered evidence.

[The memory reader](../../src/interoperability/agentops_memory_evidence_v1.py)
uses a read-only transaction over the exact original memory schema. It keeps
lazy absence distinct from a materialized empty store and preserves duplicate
notes and SQLite sequence state. It refuses unsupported schemas and journal
profiles before connecting. A live snapshot does not prove process closure,
continuous absence or cross-store atomicity.

[ASGI capture v2](../../scripts/agentops_asgi_capture_v2.py) inherits the frozen
v1 transport and business snapshots, then adds separate before/after memory
files. Unsupported or failed memory observations remain separate from original
application outcomes. The v1 public exporter has a five-file profile; v2 runner
integration must retain all original wire files and bind any exact-byte v1
projection explicitly.

[The journal validator](../../src/interoperability/agentops_runtime_stream_evidence_v1.py)
checks strict JSON, exact file and directory membership, every recorded digest,
root/call agreement, original input references, event identities and contiguous
recorder sequences. External receipt, observer-source and context bindings are
optional explicit inputs. Boolean, integer and floating-point substitutions in
evidence descriptors are rejected. The validator establishes recorded
publication order; process closure and tool-execution causality remain separate.

[Bootstrap v2](../../scripts/serve_upstream_agentops_cases_v2.py) binds only the
exact original runner instance after the original application factory. It
checks source/helper origins and resource gates, preserves original model and
tool objects, finalizes after serving and task settlement, and binds the
returned journal summary to persisted receipt bytes. Memory errors are retained
separately. Frozen v1 files remain unchanged.

## Retained software evidence

| Suite | Passing tests | Retained receipt | Independent audit |
| --- | ---: | --- | --- |
| Original trajectory metric | 16 | [trajectory-v1](../../runs/agentops-grading-software/trajectory-v1/result.json) | [verified](../../runs/agentops-grading-software/trajectory-v1-independent-review.json) |
| Read-only memory | 20 | [memory-v1](../../runs/agentops-grading-software/memory-v1/result.json) | [verified](../../runs/agentops-grading-software/memory-v1-independent-review.json) |
| Passive runtime journal | 37 | [stream-v1](../../runs/agentops-grading-software/stream-v1/result.json) | [verified](../../runs/agentops-grading-software/stream-v1-independent-review.json) |
| ASGI memory boundaries | 8 | [asgi-v2](../../runs/agentops-grading-software/asgi-v2/result.json) | [verified](../../runs/agentops-grading-software/asgi-v2-independent-review.json) |
| Bootstrap v2 | 65 | [bootstrap-v2](../../runs/agentops-grading-software/bootstrap-v2/result.json) | [verified](../../runs/agentops-grading-software/bootstrap-v2-independent-review.json) |
| Journal evidence validator | 26 | [stream-evidence-v1](../../runs/agentops-grading-software/stream-evidence-v1/result.json) | [verified](../../runs/agentops-grading-software/stream-evidence-v1-independent-review.json) |
| All-case configured-metric assessor | 21 | [case-assessment-v1](../../runs/agentops-grading-software/case-assessment-v1/result.json) | [verified](../../runs/agentops-grading-software/case-assessment-v1-independent-review.json) |
| Outer native runner v2 | 45 | [runner-v2](../../runs/agentops-grading-software/runner-v2/result.json) | [verified](../../runs/agentops-grading-software/runner-v2-independent-review.json) |
| Runnable evaluator CLI | 8 | [evaluator-cli-v1](../../runs/agentops-grading-software/evaluator-cli-v1/result.json) | [verified](../../runs/agentops-grading-software/evaluator-cli-v1-independent-review.json) |

Each listed capture runs frozen-copy stdlib software tests with `-I -S -B`,
zero failures/errors/skips and unchanged sources/captured bytes. All nine
independent audits verify membership, hashes, machine/text counts and exact
test selection without rerunning. Counts overlap legacy or preliminary suites
and must not be accumulated into a project-completion percentage.

The [source review](agentops-grading-source-review-v2.md) binds final component
hashes and the publication/type-comparison fixes. The all-case assessor, outer
runner v2 and runnable evaluator CLI are implemented and independently reviewed.

The [v2 runner guide](upstream-agentops-native-runner-v2.md) provides the next
native command. The separate evaluator command accepts a complete journal,
paired application/evaluator projections, exact case keys and actual native
user/session identities. It writes an exclusive evidence directory and assigns
only the configured metric. Failed receipt publication cannot leave an
eligible final report. Reference answers remain outside runtime inputs.

## Live boundary

There are zero original source-case native executions and zero original
source-case grades. `inventory-status-v1` was refused before staging and is a
consumed allocation. The final diagnostic observation at 18:55:10 UTC on
29 October found 14,868,480 available physical bytes (about 14 MiB) and
1,808,969,728 available commit bytes (about 1.68 GiB), below both unchanged
minimums of 1 GiB physical and 2 GiB commit. This is not a new
retained prospective gate or a native application result.

Gemini is privately configured. Provider smoke checks establish only their
recorded synthetic requests. The original AgentOps default model's availability
remains unverified; any supported explicit model selection must be disclosed.

The next useful work is to collect fresh resource gates before an unused native
allocation. Live admission, successful source-case effects,
a substantive second domain, contribution assessment and human/supervisor
acceptance remain open. Neither 70 percent completion nor an extension has
been established.
