# Original native AP2/provider development V1 appendix

The prospective five-case original native AP2/provider screen, run `42982595287` at commit `365ec09c191bddb50f6e9bf50cf6f2a871c64686` on 11 November 2026, yielded five failed task attempts and no captured business calls, actor results, public Tasks, OTP challenges or payment receipts. Its positive observations are limited to one parent provider access smoke and three original native service/card starts in the first case. No task-level semantic grade can be assigned from this capture.

| Raw observation | Count or value | Evidential scope |
|---|---:|---|
| Declared, started and closed parent task attempts | 5 | One caller failure, four launch/readiness failures |
| Actor/business/public Task captures | 0 | No OTP, authority-recovery or receipt semantic result |
| Original native cards read | 3 | First case; original RPC paths and protocol 0.3.0 |
| Recorded child processes reaped | 4 | Three native services and failed caller; no cleanup errors |
| Provider allocations | 1 | Parent forced-tool smoke only |
| Provider request/response bytes | 356 / 932 | One retained raw request/response pair |
| Provider prompt/candidate/total tokens | 35 / 10 / 45 | Raw positive usage metadata for the smoke |
| Completed public receipt cases | 0 | No purchase-completion claim |

The parent smoke requested `/v1beta/models/gemini-3.1-flash-lite-preview:generateContent`, forced the parameterless `access_check` tool with mode `ANY`, and used `maxOutputTokens: 64`. The response was HTTP 200 and returned that function call, while reporting `modelVersion: gemini-3.1-flash-lite`. The requested preview string and returned stable string remain distinct. This establishes one access observation for the requested pinned path; it does not independently identify a model revision, verify application capacity or establish billing/free-tier status. No original service SDK generation is captured.

The unchanged native module entries reached card readiness in the first case. Original executor source constructs `genai.Client()` before startup; later tool resolution performs generation. The captured successful card GETs and process logs are consistent with SDK client construction, but do not exercise that later generation path. The first caller exited 1 during original-source binding when marshalled callable-code equality was rejected, before the owned business caller was constructed. The remaining four parent attempts record only launch/readiness `OSError` and no child processes. Their errno and causes were not captured; proposed port/TIME_WAIT explanations remain inference.

All five failed cells and all missing semantic captures are retained. The closing `unexecuted_count: 0` denotes five started parent attempts and does not establish five executed business workflows. Workflow success reflects successful failure retention, not task success. The absence of public Tasks prevents any conclusion about correct/wrong/withheld OTP, authority recovery, repeat effects or payment-receipt semantics.

An independent stdlib-only raw audit reconciled the API digest, archive, all 27 extracted members, source/owned-byte bindings, provider opening/closing allocation records, usage, native cards/PIDs/reaps and the five-case parent census without integrity inconsistencies. Archive SHA-256 is `0b73d252058fe6d967a54e4cbe1646e1f08b0ac0d3711d82791b90dd445e6d0a`. Captured Linux Python 3.13.1 reports all 182 required versions among 185 actual distributions, 184 pip install records and a 14,728-file runtime inventory. Runtime and pip bytes are bound by retained hashes; the discarded hosted venv cannot be independently rehashed after execution, and no caller imported-runtime result exists.

The treatment explicitly uses an owned HTTP accounting proxy, scripted calls to original business functions, an added public SDK `get_task` read and prospectively supplied public choices. Offered cart/payment index zero, wallet consent, cart confirmation and OTP choices were declared but never exercised in this capture. The 80-call and 200,000-request-byte limits were unexhausted; the 100,000 observed-token threshold is post-response stopping, not a hard token or cost ceiling. One request does not verify inter-request pacing. This development observation grants no original `run.sh` provisioning, autonomous ADK shopper, bridge, human gold, untouched holdout, whole-task, idempotency, full-study or checkpoint qualification.

Evidence: [results note](../docs/research/ap2-original-native-provider-results-v1.md), [raw retention](../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/retention.json), [independent raw reconstruction](../runs/ap2-original-native-provider-development/v1/independent-raw-review-v2/review.json), and [raw provider response](../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/execution/provider/000.response.json). The reviewer imported no original application/SDK/model and made no provider request.
