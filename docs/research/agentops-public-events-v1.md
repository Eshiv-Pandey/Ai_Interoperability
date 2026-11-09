# Normalize archived AgentOps public protocol captures

29 October 2026. The [public-event exporter](../../src/interoperability/agentops_public_events_v1.py)
preserves original server-side ASGI captures and projects A2A task artifacts,
messages and function parts. It runs without AgentOps/SDK imports, application
requests, credentials or model calls. It supplies evidence for the
[source-grounded grading contract](upstream-agentops-grading-contract-v1.md).

The captured bytes are **server-observed public protocol evidence**. They do
not prove that the client received every response, that all ADK events were
published, or that an upstream benchmark case ran. Exchange sequence records
request-start order; it is not response-arrival or ADK causal order. The
separate [raw ADK exporter](agentops-raw-events-v1.md) retains evaluator-private
events for comparison without inventing those guarantees.

## Input and command

Use an archived, stopped capture directory. Each six-digit exchange directory
must contain exactly `exchange.json`, `request.body.bin`, `response.body.bin`,
`before.snapshot.json` and `after.snapshot.json`. Metadata must declare
`agentops-asgi-exchange/1`; body completeness and byte counters are checked.
Snapshots are retained as original bytes and are not effect-graded here.

For another archive, select a new output outside the wire tree:

```powershell
python -B src/interoperability/agentops_public_events_v1.py --wire-root PATH_TO_ARCHIVED_WIRE --output NEW_OUTPUT
```

The command refuses an existing output. Source paths must be regular and have
the declared membership. After capture it checks source bytes/membership,
implementation bytes and captured files before writing the receipt. Failure
allocations retain the plan, implementation sources and captured evidence.
Per-file and collection limits are 32 MiB and 256 MiB respectively.

## Retained semantics

- A2A 1.0 `SendMessage` wrapped Tasks and `GetTask` direct Tasks are understood,
  including `ROLE_*` and `TASK_STATE_*` enums. Recognized legacy method aliases
  remain explicitly bound to the recorded version header.
- Agent cards and JSON-RPC errors are retained separately. Incomplete bodies,
  message-only/unbound results, unknown states and unsupported operations remain
  explicit; partial normalization does not become task success.
- Artifact parts use task/context, protocol header, ADK event identity and part
  index. Repeated cumulative observations are deduplicated; changed artifact
  content/count/metadata is rejected. Distinct confirmation-required and
  executed replies sharing the original action ID remain distinct parts.
- Request, status and history messages use their own message-ID namespace.
  An empty working message remains present. A long-running confirmation without
  ADK event metadata does not acquire an invented ADK event ID. An embedded
  `originalFunctionCall` is retained inside its confirmation payload, rather
  than counted as another issued action.
- Every exact message and part representation and capture location is retained.
  Deduplication permits assigned task/context IDs and known optional text/plain
  transport decoration to differ between request and history. Changed semantic
  content, part count, role or other metadata is rejected.

This version is a bounded archived-evidence normalizer. General partial/chunked
artifact replacement, streaming completeness and full protocol qualification
remain outside its supported projection.

| Output | Meaning |
| --- | --- |
| `wire/NNNNNN/*` | All original exchange, body and snapshot bytes. |
| `observations.json` | Exact decoded envelopes; task/context associations; distinct parts/messages with all retained representations. |
| `source/*.py`, `plan.json` | Both implementation sources and prospective input/hash selection. |
| `result.json` | Counts, unsupported exchanges, file hashes and preservation result. No task grades. |

## Completed validation

The [captured focused validation](../../runs/agentops-public-event-evidence/software-v1/result.json)
passed **17 tests with zero skips**, using copied implementation/helper/package
and test sources. Original and captured sources stayed byte-identical. Tests
cover real envelope shapes, history enrichment, empty messages, repeated phases,
identity/count/metadata conflicts, duplicate JSON, partial results, byte counters,
source mutation, failure retention and output exclusivity. These are temporary
format fixtures, with no native or model execution.

The once-only [archived N11 export](../../runs/agentops-public-event-evidence/native-v12-N11-v1/result.json)
passed: **9 exchanges, 8 task replies, 7 distinct parts, 4 messages, 2 calls and
3 responses**. Twenty-six repeated part observations were retained as
representations of the seven parts. All 45 wire files and both implementation
sources passed preservation checks. This output allocation is consumed.

The [independent AI audit](../../runs/agentops-public-event-evidence/native-v12-N11-v1-independent-review.json)
passed 160 checks with zero failures. It reconstructed every message and part
representation from the original request/status/history envelopes, verified
all 49 manifest entries and the receipt, and confirmed the software results.
All 108 monitored files and directory membership remained unchanged. It ran
no exporter, SDK, application or model code. This is evidence review, not human
acceptance or protocol qualification.

Its original prompt remains `Restart inventory.` under
`confirmation_test_agent`. This is historical extractor-development evidence;
native executions of the 21 upstream cases remain zero. A task/effect grader,
fresh source-case runner, faithful live admission, method advantage, substantive
second domain and human assessment remain open. This week's supervisor review
requires the algorithm, benchmark and runnable demo; no paper is required.

The [cross-view binder](agentops-event-binding-v1.md) now independently checks
these function projections against the private export. Its historical comparison
is audited; it does not add client identity or causal-order guarantees.
