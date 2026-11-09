# Independent original-native reference checking

Prepared **24 October 2026** by a separately tasked AI checker author. This is an independent software implementation and agent-assisted source review, **not independent human scientific validation, a native-compatible A2A 1.0 bridge witness or a novel method**. Human novelty/feasibility review remains pending.

## Checked record and interface

The input is the saved [original Carol native record](../../runs/native-reference-continuation/carol-run-20261023T204701107557Z-24356/report.json), interpreted under the [prospective probe](reference-continuation-probe-v0.md). The pure interface is:

```python
from interoperability.reference_checker import check_reference_trace
valid = check_reference_trace(explicitly_loaded_report)
```

The checker reads no filesystem, environment, private sidecar or network state. It imports no capture driver, application handler, baseline, finite oracle or wire projector. It independently validates the body encodings, chronology, native schemas, phase sequence, supplied control summaries and request/body-byte cost accounting. False or insufficient evidence returns `False`; this interface does not classify arbitrary tasks as supported/unsupported.

## What the actual bytes establish

The record has **14 local HTTP exchanges: one Agent Card discovery and 13 old-version JSON-RPC calls**, with **2,555 request-body bytes and 11,200 response-body bytes**. These body counts exclude HTTP framing/headers, dependency setup and process diagnostics. Each request/reply is paired by its exact recorded JSON-RPC ID and exchange/phase identity. All three controls have a native input-required task receipt before the fixed answer.

| Control | Checked observations |
| --- | --- |
| N1, original IDs and own-task reference | The answer is `Well done!` with original task/context and `referenceTaskIds=[original ID]`; both answer result and subsequent original-task get report completed with those same IDs. |
| N2, original IDs with empty references | The same answer targets that control's original task/context with empty references; answer and original-task get retain input-required and the same IDs. |
| N3, context only with empty references | The answer contains its original context and no task ID; it creates a different task in that context. The original-task get remains input-required and the separate new-task get matches the answer's ID/context and input-required state. |

Controls use separate newly created original tasks and identical one-entry shuffle payload/answer text. The deliberately omitted references in N2 and task association in N3 are **authored near-miss interventions**. They are not naturally observed bridge faults. This record ran the unchanged external application's own **A2A 0.3.0** runtime; no A2A 1.0 port or MCP bridge execution is present.

The completion goal concerns task state and original association, rather than a newly delivered artifact. The checker does not require an artifact on a completed acknowledgement, and a regression explicitly accepts omission of those completed artifact fields. This must not be confused with the earlier text-artifact projection's different delivery goal. Likewise, rejecting another task's reference in the N1 record checks the prespecified own-reference control; it does not assert that Carol validates referential integrity. The source dispatch tests only whether references are nonempty.

## Independent integrity checks

- Strict UTF-8 native bodies must agree with canonical base64, SHA-256 and independently parsed JSON. Duplicate keys, non-finite JSON constants, malformed/deep bodies and raw/parsed disagreement are rejected. JSON comparison distinguishes Boolean and integer values.
- Recorded UTC and monotonic intervals must describe serial request/reply observations between process readiness and cleanup. This validates recorded ordering, not a service freshness lease or causal attribution of advancement to a get request.
- The discovery card and report must identify the original 0.3 JSON-RPC profile. The loopback endpoint, native `message/send`/`tasks/get` names, task/context namespaces, task schemas and expected control order are checked. The validator deliberately covers this text-only Carol fragment, not every legal A2A Part or arbitrary protocol conformance.
- Controls' pending/answer/final/new-task summaries must equal their actual raw response objects. A summary cannot replace a missing decisive get or override a conflicting task/context/status/reference. Error responses, HTTP failures, failed controls and unverified cleanup cannot establish a checked positive record.
- Byte totals and request counts are recomputed from the checked body bytes. The original SDK-import receipt states `a2a-sdk==0.3.0` and `uvicorn==0.35.0`. The recorded original runtime is **Python 3.12.7**, according to the actual report.

The original Carol PID is recorded as **10852**, with terminal cleanup observed in the record. Its process exit code **1** follows explicit Windows termination after the successful observations; the capture driver exits 0 and the controls are observed. The checker therefore does not mislabel that cleanup code as a startup/control failure. It checks the recorded terminal flag and ordering, rather than querying whether the process is currently alive.

## Tests and limits

The owned test suite has **31 methods**, including multi-case mutation subtests. Tests use explicitly labelled derivatives kept in memory, never overwrite the captured record, and exercise deleted evidence, rehashed identity/context/reference/status changes, native errors/empty task views, false summaries, invalid encodings, duplicate keys, wrong protocol, chronology, cost tampering and malformed inputs. They also preserve the status-only goal and valid Windows cleanup interpretation. The observed native record passes this independently authored checker.

Run only this suite with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_reference_checker.py -v
```

Self-consistent body hashes are **not authentication or proof of complete logging**. The pure checker cannot prove that the named source/dependencies were the executed software, that the report omitted no external activity, that metadata hashes match archived files, or that no model call occurred. Its source/hash/version fields are checked for the declared profile and structural consistency; an external verification runner must compare actual archived source/dependency ledgers and preserve every attempt. The parent owns that independent archive/replay evidence.

These checks establish the three recorded native development observations under explicit capture/source assumptions. They do not establish future completion, broad A2A interoperability, absence of other application paths, natural failure prevalence, field-erasure causality on either current bridge, candidate superiority, conference acceptance or a C1 novelty result. An exact solver with the same correctly derived guards/actions already expresses this example; CP2's scientific and human gates remain open.
