# Actual first native/provider screen: source diagnostic

Run [42982595287](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42982595287)
completed at frozen revision `365ec09c191bddb50f6e9bf50cf6f2a871c64686`.
Workflow success means the runner and retention completed. It does not mean
the application tasks completed. The original archive is retained by root at
`runs/ap2-original-native-provider-development/v1/retained-42982595287-1`,
with API SHA-256 `0b73d252058fe6d967a54e4cbe1646e1f08b0ac0d3711d82791b90dd445e6d0a`.
This document reads that capture and original source; it changes no allocation,
runtime, result or source code and makes no new model/application request.

## Actual observations

The single access smoke received HTTP 200 and an `access_check` function call
from the exact original `gemini-3.1-flash-lite-preview` model. Its durable ledger
contains one started and one finished allocation, 356 request bytes, 932 response
bytes and 45 recorded total tokens. No unknown-usage response or upstream retry
was observed. This establishes one real-provider generation/access observation;
it does not establish current quota or original application model routing.

The first case launched all three exact original module entries and read their
original v0.3 public cards. Native entrypoints and original Client construction
were therefore observed under the declared base-URL treatment. The caller
returned 1 before its first business function. All four spawned processes were
reaped. There is no original application generation request or completed task.

| Declared case | Actual retained outcome | Application evidence |
| --- | --- | --- |
| Correct reply | Caller exit 1 after native card readiness | Source/function binding failed before business calls |
| Wrong reply | Launch preflight `OSError`; no spawned process | Required wrong-OTP branch missing |
| No reply | Launch preflight `OSError`; no spawned process | Required waiting branch missing |
| Foreign-context recovery | Launch preflight `OSError`; no spawned process | Required adverse/recovery branch missing |
| Repeated completed call | Launch preflight `OSError`; no spawned process | Required receipt/repeat branch missing |

All five bootstrap allocations were attempted, so the runner's mechanical
`unexecuted_count` is zero. All five substantive application-task observations
remain unavailable. These are different denominators. No whole-task gold,
near-miss qualification or complete-purchase claim follows from this run.

## Exact source blockers

The first retained caller traceback ends at
`src/interoperability/ap2_hp_original_binding_v1.py:209`:
`marshal.dumps(function.__code__) == marshal.dumps(code)` fails with
`BindingError: Loaded original callable code differs`. This establishes the
exact comparison failure, not a proven original-source modification. Marshal
serialization can reflect reference sharing; the actual capture does not
identify the first mismatching code attribute. A separately versioned verifier
must inspect typed recursive code identity and retain attribute-level evidence
before claiming the function body is unchanged. The earlier V13 structural
fingerprint is a source-supported lead, not a reproduction of this failure.

The four later rows record only the exception type `OSError`. They contain no
errno or message and no subprocesses. Source execution reaches
`require_free_ports()` before launching each service; its ordinary temporary
socket bind lacks the original Uvicorn listener's reuse setting. TIME_WAIT is
a plausible source-level explanation after the first service group's shutdown,
but the retained evidence does not prove that cause. A prospective successor
must retain safe errno/type and verify listener ownership using the intended
listener semantics. It must not suppress a real occupied port or terminate
an unrelated process.

Any repair belongs to a new version/allocation with fresh state. The original
five outcomes and one consumed provider allocation remain immutable.

## Bound inputs

| Input within retained extraction | SHA-256 |
| --- | --- |
| `execution/result.json` | `66d279445c3a3eb4517109a9715da173bc7d353a3f698ad243f05e6d3dc010f9` |
| `execution/provider-access-smoke.json` | `f7622e0e801623e6f589f04e0ab5ad49e7cc291eef86c12c7a60b45a8079b46a` |
| `execution/cases/ap2-native-provider-v1-correct-reply/caller.stdout.log` | `a07040a97a231d9de13cc645bf525cb78c1d5e5a3d7bbfe3ce479173353359d2` |

The provider response and request are separately bound by their original
ledger. Root's retained archive identity and independent raw review remain the
authority for publication; this source diagnostic is a narrower reading.
