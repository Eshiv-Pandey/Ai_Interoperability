# Retained input reanalysis for the loss benchmark v1

12 November 2026. This benchmark-only ingestion reanalyses exact retained bytes.
It launches no application, SDK service, bridge, model, paid API, or token-using
experiment. The historical observations retain their original development
provenance. Rebuilding these JSON rows is new software/data analysis, not a new
experimental capture or a held-out evaluation.

The [106-file input manifest](../../benchmark/loss-v1/retained-manifest.json)
selects exactly the four Carol bridge captures cited in
[reference-bridge-results-v1.md](reference-bridge-results-v1.md), the three
version-matched [native port controls](reference-port-native-results-v1.md),
the three [unchanged original native controls](reference-continuation-results-v0.md),
and N11/B6/B7 from [the original-double v12 diagnostic](agentops-bridge-diagnostic-results-v12.md).
Other similarly named captures and archive contents are not selected.

## Cases and collection provenance

| Separate family | Episodes | Strict task goal from retained raw data |
| --- | ---: | --- |
| Disclosed authored Carol A2A 1.0 port through pinned bridges | R1-R4 | R1/R2/R3 original task/context remain waiting; R4 original task/context complete |
| Disclosed authored Carol A2A 1.0 port over native SDK/HTTP | P1-P3 | P1 original completes; P2/P3 original remain waiting |
| Unchanged original Carol application on A2A 0.3 | N1-N3 | N1 original completes; N2/N3 original remain waiting |
| Original deterministic confirmation double and simulated SQLite, v12 diagnostic | N11/B6/B7 | N11/B7 original complete with exactly one attributed inventory restart; B6 original waits, no restart, no continuation |

There are 13 episodes with five achieved goals and eight bounded non-completions.
These counts are inventory accounting, not a pooled performance rate. The metric
engine reports scores by evidence kind, family, and executed route. Mixed
families have no overall score. The Carol native controls are deliberately
selected reference/near-miss interventions, not samples of natural faults.

R4 selects the bridge's existing raw alternative directly from its public
prefix. No failed typed answer precedes it. Recovery eligibility is false and
recovery status is `not_applicable`. The same applies to the selected AgentOps
raw-confirmation profiles: their records are not post-failed-answer recovery
trials. B7 explicitly configures `A2A-Version: 1.0` at its local origin.
R4's missing raw version header succeeds under the authored port's disclosed
default-1.0 policy. Neither establishes generic stock raw compatibility.

## What is independently recomputed

The builder checks pinned SHA-256 hashes before reading input content, rejects
duplicate JSON keys and nonfinite numbers, and reconstructs requests/responses
from base64 or actual `.body.bin` files. It verifies exact byte counts, recorded
entity hashes, parsed/raw agreement, RPC correlation, retained capture identity,
and source identity where the capture records it. AgentOps ASGI response chunks
are checked against their own byte hashes. Each episode lists all consumed raw
files and positive native witness files with their exact path and SHA-256.

Task completion requires the ID and context of the **original** native task plus
its completed state in an authoritative final `GetTask`/`tasks/get` response.
It never uses stored `goal_achieved`, `strict_success`, `outcome`, or checker pass
labels to decide success. For bridges, independently decoded public final
responses also check association and agreement with native state. Modern MCP
`resultType: complete` alone supplies no task-completion evidence.

AgentOps additionally compares the initial and terminal database rows: inventory
changes from down to operational; other services and all incidents stay equal;
exactly one audit row records `restart_service` on inventory, the original
session/context, approver, supplied rationale, reconstructed domain context,
and an invocation attributable to the original task's returned artifacts.
The pre-continuation snapshot must preserve all initial domain rows, proving
that the recorded effect has not occurred before the confirmation response.
Zero effects, duplicates, another target, or another session cannot pass.
This is an effect check on the simulated retained domain, not real service
remediation or LLM efficacy.

B6's public raw read error is preserved. No public confirmation binding or
continuation payload exists. Its bounded task goal fails from terminal waiting
state and zero effect; its historical strict whole-case status stays partial.
Missing public confirmation is unknown fidelity and missing sent/received
payloads are unknown context observations. Clean shutdown does not fill these
gaps.

## Measurements and missingness

Context measurements cover only captured values. Carol bridge rows include the
prospectively fixed answer text and, where public UUID fields exist, original
task/context UUIDs across the chosen request and native wire request. Amir opaque
handles are not compared literally against native UUIDs. An absent reference
field is `present=false`, while an uncaptured source reference requirement is
`present=null`; neither is silently replaced by `[]`. Explicit SDK empty lists
and optional empty IDs remain explicit input values when actually captured.
Their protobuf wire omission is retained as a presence change, without claiming
protocol nonconformance. The unchanged original 0.3 record has no independently
captured SDK sent payload, so source/sent stages remain unknown.

AgentOps continuation facts include captured original UUIDs, public confirmation
call ID/name, and approval rationale. B6's missing values are unknown. The data
do not support comprehensive fact retention, source-document provenance
retention, broad memory quality, or model extraction accuracy. Any context score
is restricted to the named captured items; it is not a score for all task facts.

The required capability is the strict goal under the named executed selected
profile. Its positive reference usability is recomputed from the exact native
P1, N1, or N11 witness, which is included among that row's hashed inputs. Successful
executions demonstrate observed usability. Non-completions retain
`observed_usable=null`: incomplete trajectories do not prove whole-interface
non-support, and no advertised tool/card claim supplies usability.

| Cost boundary | Counted data | Exclusions / separate counters |
| --- | --- | --- |
| Carol bridge | MCP request and response entities, setup RPCs, tool calls, initialized notification | Separate native HTTP counters in metadata; no TCP framing or implicit headers |
| Carol native controls | Case-specific HTTP requests/responses, native task RPC count | One shared card discovery excluded from individual cases |
| AgentOps bridge | Exact MCP log messages/entities and `tools/call` requests | Native HTTP and evaluator final GetTask reported separately in metadata |
| AgentOps N11 native | All captured service HTTP exchanges/entities and task RPCs | Includes one card discovery and evaluator final GetTask; not comparable to bridge-only costs without matching boundary |

Carol MCP entity totals are recomputed as 7,894 request bytes and 57,211 response
bytes. Its 26 RPC requests and two initialized notifications are separately
counted. Native port case sums are 2,721/10,008 bytes, plus the shared card's
0/1,428 bytes; original 0.3 case sums are 2,555/10,120 bytes, plus its shared
card's 0/1,080 bytes. These checks reconcile the historical complete-native
totals without allocating shared setup repeatedly.

Latency is null because retained diagnostic boundaries and instrumentation
timestamps do not provide a comparable defensible latency experiment. Model
tokens are null because no credible inference-token capture exists. The
historical no-model provenance is recorded separately; null is not zero.

## Rebuild and verification

```powershell
.venv/Scripts/python.exe -B scripts/build_loss_benchmark_retained_v1.py
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_loss_benchmark_retained_v1.py -v
```

The builder allocates a new timestamp/UUID directory beneath
`runs/loss-benchmark-retained-v1/` containing `episodes.json` and `result.json`.
An explicit `--output` must identify a nonexistent path. Reanalysis cannot
overwrite the original input records or an earlier output allocation.

The retained-input tests check corrupt body/hash/length/JSON rejection, pinned
source mismatch, unmanifested or escaping paths, changed capture identity,
changed original task/context, false success-summary mutations, missing versus
absent values, modern outer acknowledgement, upfront alternative recovery N/A,
and duplicate/wrong-attribution effect rejection. These are labelled software
controls, not additional service observations.

This package does not prove loaded-module fidelity for unobserved code, complete
protocol conformance, independent human validation, source-to-world equivalence,
scientific novelty, natural failure prevalence, reliability, or generalization.
It preserves the distinct authored port, unchanged A2A 0.3 application, original
deterministic double, configured bridge deployment, partial captures, and
missing measurements. It awards no checkpoint credit and does not close CP2.
