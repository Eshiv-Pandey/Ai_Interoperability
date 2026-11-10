# AP2 V8 native smoke failure: appendix to manuscript V7

Research evidence appendix, version 1, 11 November 2026.

This appendix supplements [manuscript V7](working-draft-v7.md) with the actual
[V8 hosted attempt](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42897325489).
It records a bootstrap/guard feasibility failure and adds no native performance
result. The original study scope, prior outcome tables and unresolved scientific
claims remain as stated in V7. The intended V8 matrix builder remains prepared;
this failure appendix does not replace a completed native matrix manuscript.

The retained conventional smoke used case `human_demo_otp`. Its worker returned
code **3** with `PermissionError` and reason
`actor_private_evaluator_or_saved_credential_read_denied`. Both stdout and stderr
were empty. The worker failure handler retained only the exception type and
message: **the exact denied path and traceback were not retained**. The exception
must not be relabeled as a source-code mismatch, an original application error,
or a demonstrated payment failure.

| Retained smoke indicator | Value |
| --- | ---: |
| Worker return code | 3 |
| Private reads denied, including the declared evaluator probe | 2 |
| Operations classified as external and denied by the guard | 1 |
| Allowed owned loopback operations | 0 |
| Allowed allocated bridge client processes | 0 |
| Provider requests reported by the worker result | 0 |

The external-operation counter does not identify a host, operation, caller or
provider; its exact cause remains unknown. There is no retained first-callable
identity report, runtime manifest, original tool invocation, native server-start,
wire or cleanup record, original application state, or durable raw observation
journal. Consequently this smoke establishes no captured original SDK payment
execution, original application response, legal bridge initiation, native
transport qualification or provider utility.

The matrix was preallocated before smoke execution. Its finalized dispatch
history retains all **104** cells on 13 authored cases: 65 planned payment-tool
cells and 39 planned repeated bridge initiation slots. Every cell retains
`not_executed_before_workflow_finalization`, a null return code and
`missing_or_pre_execution_failure_retained` in the independent evaluation.

| Arm | Allocated cells | Executed matrix cells | Verified captures | Verified purchase observations |
| --- | ---: | ---: | ---: | ---: |
| reference | 13 | 0 | 0 | 0 |
| conventional | 13 | 0 | 0 | 0 |
| recovery | 13 | 0 | 0 | 0 |
| shared | 13 | 0 | 0 | 0 |
| recovery_shared | 13 | 0 | 0 | 0 |
| amir_typed | 13 | 0 | 0 | 0 |
| mg_typed | 13 | 0 | 0 | 0 |
| mg_raw | 13 | 0 | 0 | 0 |

Zero verified purchases here denotes absence of matrix execution and capture,
not a measured zero-percent task success rate. All 65 planned ASGI/TCP pairs
remain non-evaluable. No transport equality, superiority, overhead or bridge
non-support comparison can be inferred from this attempt. The one failed smoke
is separate from these 104 unexecuted matrix cells.

The [independent failure peer](../docs/research/ap2-v8-actual-smoke-failure-peer-audit-v1.md)
identifies a deterministic source/guard obstruction, distinct from the omitted
actual failure path. In the exact retained runner, `source_contract` at line 452
calls the source inventory before the runtime inventory. That inventory reads
every pinned original file. The guard at lines 698 and 709 permits only two
installed CA bundle paths outside the private profile, so it rejects these
required original public certificates if the source-verification statement is
reached:

| Pinned original public certificate | Bytes | SHA-256 |
| --- | ---: | --- |
| `code/samples/certs/ds_cert_sdjwt.pem` | 1066 | `a4b92cd66960d4ddcdcb8ca8b2887dafdec06cbcd42bc10fcc8ede41ffef1306` |
| `code/samples/certs/issuer_cert_sdjwt.pem` | 1005 | `120abde3087907911c3c9de00c536657a6a503a88849a24653f6c35030c982ba` |

Both snapshots contain a public certificate marker and no private-key marker;
their identities match the original source manifest. The peer reconstructs
only the exact guard decisions, without executing the original applications.
This proves the obstruction if that statement is reached. It does not recover
the smoke's omitted denied path or explain its unlocated network denial.

A successor needs narrowly source-bound public certificate handling and bounded
non-secret denial diagnostics, followed by a fresh retained smoke and matrix.
Those are remaining work, not results of V8. The V8 attempt and V7 evidence
remain frozen; no human-gold validation, publication approval or full research
checkpoint credit is supplied by this appendix.

The [claim provenance](ap2-v8-native-smoke-failure-appendix-v1.json) identifies
the retained allocation, execution, evaluation, smoke, source and peer inputs.
The [independent appendix audit](ap2-v8-native-smoke-failure-appendix-v1.audit.json)
checks these claims directly against the archived bytes and every allocated cell.
