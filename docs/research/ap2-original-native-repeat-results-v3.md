# Fresh AP2 native/provider repeat control V3

11 November 2026. The separate adaptive repeat case ran, but the original
catalog operation failed before the payment prerequisite. An actual upstream
Gemini response returned HTTP **503 UNAVAILABLE** with a high-demand message.
The same error text is retained in the original tool exception and actor error.
**No receipt, payment Task read or repeated OTP continuation was observed.**

This is one retained failed development attempt. It is separate from V2's
five-case allocation and cannot replace its partial fifth outcome.

## Allocation and reconstruction

| Item | Binding |
| --- | --- |
| Hosted run | [43014447502](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43014447502) |
| Frozen head | `b65a6767e21191314c27cdf50d3f5ff810d5a2ce` |
| Root retention | `runs/ap2-original-native-provider-development/v3/retained-43014447502-1` |
| API/archive SHA256 | `b8f988d85bb47cb98ea8c2171125e6441323a338223b634aed4ab2bfc3af3f49` |
| Archive bytes / members | 1,282,507 / 34 |
| Semantic output | `runs/ap2-original-native-provider-development/v3/independent-semantic-analysis-v1/analysis.json` |
| Semantic output SHA256 | `13cc9a43b8574ee5573a00d7d92a223a6496150db1b445a3d1527311001dac3e` |
| Analyzer source SHA256 | `e834d07d23a779a0733276d216bf07663b42d459d9c60e17c745a6d1b69b6877` |
| Unchanged V2 public helper SHA256 | `8901795494755665cd46ad278e15cd83e0da26cd7c1937b22894bbb06aaa61f9` |
| Control source SHA256 | `eea7acb862bebe7f7fb5bd1d505e27d1ef698da4a2fba310f72e537bbd93f121` |

The new offline semantic reconstruction verifies the retained archive's byte
count and digest, the singleton's exact prospective facts, and the root-manifest
digest of each captured member. It uses the unchanged V2 public semantic helpers
to reconcile the actor result with raw original-call, actor-event and public-read
censuses. Its status is `retained_public_observations_consistent`, with **zero
consistency questions**. Root's separate
[raw review](../../runs/ap2-original-native-provider-development/v3/independent-raw-review-v1.json)
owns native/runtime/provider provenance, archive-member reconstruction and full
accounting. Neither reviewer makes application or provider calls.

Five new constructed controls pass: propagated external error versus public
Task read, unrelated provider error, missing actor/unterminated call, a captured
repeat that prevents an early-failure disposition, and disagreement between
actor reads and raw terminal reads. They exercise interpretation and consistency;
they are not additional application observations or human gold.

## Original caller and provider observations

The one parent row is `executed_returned`, with caller exit code zero. The
caller records `actual_failed_or_partial_attempt_retained`: process return does
not mean application success. There is one original `find_products` start,
one catalog terminal `RuntimeError`, zero original business-call returns, and
three raw public-event rows (call start, call error and actor error).

The failed catalog Task/message appears inside the original tool exception as
an SDK representation with `TaskState.failed`. There is no separate public
`tasks/get` observation. No cart/payment choice, OTP request, explicit OTP reply,
payment prerequisite, receipt or repeat call/read is captured. The prospective
`otp_response="123"` is a declared fact; it was never submitted in this attempt.

| Provider allocation | Retained response | Reported total tokens |
| --- | --- | --- |
| 0: parent access smoke | HTTP 200; expected access function call | 45 |
| 1: original native function resolution | HTTP 200; `find_items_workflow` function call | 794 |
| 2: original catalog schema generation | HTTP 503; `UNAVAILABLE`, high demand | Unknown; no usage metadata |

The third request and response occur within the one case's captured time
window, and its exact error code/status/message appear in the original tool
error. This corroborates the propagated external failure. It differs from V2's
owned byte-budget refusal. There are three upstream allocations, 6,327 forwarded
request bytes and zero local refusal rows. The successful responses report **839
tokens**; the complete token/cost total is unmeasured because the 503 response
has no usage metadata. Missing usage is never assigned zero. The raw review
confirms that all four recorded child processes were reaped.

## Limits and next interpretation

The case is an exposed, adaptive development follow-up with a one-task
denominator. A repeated public response and any changed receipt remain
unobserved; no idempotence, hidden-effect uniqueness, durability or original
application non-support follows from this failed prerequisite. A later fresh
allocation would be a separate attempt and must preserve both V2 and V3.

The original module entries, model/SDK, owned public caller/read surface and
accounting proxy remain explicit treatments. No unchanged `run.sh` provisioning,
autonomous ADK shopper, independent bridge, human gold, untouched holdout,
whole-task grade, full-study result or scientific checkpoint qualification is
granted by this control.

```powershell
python -B tests/test_ap2_original_native_repeat_semantics_v3.py
python -B scripts/analyze_ap2_original_native_repeat_v3.py --retained-root runs/ap2-original-native-provider-development/v3/retained-43014447502-1 --output runs/ap2-original-native-provider-development/v3/<fresh-analysis-directory>
```

Use a fresh output directory name. The analyzer refuses overwrite; the angle
brackets above are a placeholder, not a literal command argument.
