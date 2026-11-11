# Original native AP2/provider V1 results

11 November 2026. Run [42982595287](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42982595287) at `365ec09c191bddb50f6e9bf50cf6f2a871c64686` retains **five failed task attempts and zero captured business calls, actor results, public Tasks, OTP challenges or receipts**. One parent provider smoke succeeded, and the first case reached three original native service cards. These are early-phase observations, not completed AP2 purchases or semantic task grades.

The [prospective protocol](ap2-original-native-provider-protocol-v1.md), [retention receipt](../../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/retention.json), [raw closing census](../../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/execution/result.json) and [independent raw review](../../runs/ap2-original-native-provider-development/v1/independent-raw-review-v2/review.json) remain separate artifacts. The workflow conclusion is `success` because the runner retained task failures; it does not mean the tasks passed. The raw review found zero integrity inconsistencies and made no original application/SDK/model imports or provider requests.

## Observed phases and failed cells

| Declared case | Raw parent disposition | Recorded children | Business/public Task capture |
|---|---|---:|---|
| Correct reply | Caller exited 1 after original card readiness | 4, all reaped | None |
| Wrong reply | Launch/readiness `OSError` | 0 | None |
| No reply | Launch/readiness `OSError` | 0 | None |
| Foreign context/recovery | Launch/readiness `OSError` | 0 | None |
| Repeat after completed | Launch/readiness `OSError` | 0 | None |

All five cases have started and finished parent ledger rows. The closing `unexecuted_count` is zero: all five parent task attempts started. That field must not be interpreted as five executed business workflows. There are zero actor results, business-call event captures or public Task observations, so there are no V1 correct/wrong/withheld-OTP, authority-recovery, repeat or receipt semantic grades.

The first case started unchanged `roles.merchant_agent`, `roles.credentials_provider_agent` and `roles.merchant_payment_processor_agent` entries. Their cards were read at `/a2a/merchant_agent`, `/a2a/credentials_provider` and `/a2a/merchant_payment_processor_agent`, on ports 8001, 8002 and 8003, with protocol `0.3.0` and the original required AP2 extension. The three service stdout files record started/finished PIDs and successful card GETs, with no POST request. The parent reaped those three services and the failed caller, with no recorded cleanup error.

The source construction path calls `genai.Client()` in [BaseServerExecutor](../../runs/ap2-environment-preparation/source-stage-v1/ap2/code/samples/python/src/common/base_server_executor.py) at line 69 before native service startup. Card readiness is consistent with that constructor completing. The later [FunctionCallResolver](../../runs/ap2-environment-preparation/source-stage-v1/ap2/code/samples/python/src/common/function_call_resolver.py) generation call at line 84 was not reached by the captured card GETs. No original service SDK generation is observed.

The [first caller traceback](../../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/execution/cases/ap2-native-provider-v1-correct-reply/caller.stdout.log) fails in `bind_original_modules` at `_verify_function`'s marshalled-code comparison: `BindingError: Loaded original callable code differs`. This occurs before construction and execution of the owned business caller. The four later records retain only the `OSError` class and empty process lists. Their errno and underlying cause were not captured; port conflict or TIME_WAIT explanations remain source-based inference. Empty lists are not failed reaps. Every V1 source, capture and failed cell remains preserved for a prospective successor.

## Provider access and bounds

The [raw provider ledger](../../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/execution/provider/ledger.jsonl) contains exactly one started/finished allocation, for the parent smoke. Its [356-byte request](../../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/execution/provider/000.request.json) asks for the forced `access_check` function using mode `ANY` and `maxOutputTokens: 64`. The [932-byte response](../../runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/execution/provider/000.response.json) is HTTP 200 and contains that function call. Usage is 35 prompt tokens, 10 candidate tokens and 45 total tokens.

The request path names `gemini-3.1-flash-lite-preview`; the returned `modelVersion` is `gemini-3.1-flash-lite`. Both strings are retained without treating them as identical. This proves one observed response to the requested pinned path, not an independently attested model revision. The generation belongs to the parent access smoke, not the original SDK or native service workflow.

No later allocation or locally refused provider retry is captured. The 80-call cap, 200,000 cumulative request-byte cap and 100,000 observed-token post-response stop were unexhausted. The 45-token result does not test application quota or capacity; one request cannot test six-second inter-request pacing. The observed-token threshold is not a hard token or cost ceiling, and no billing/free-tier qualification is inferred.

## Raw and runtime bindings

The 1,193,591-byte archive has SHA-256 `0b73d252058fe6d967a54e4cbe1646e1f08b0ac0d3711d82791b90dd445e6d0a`, matching the API artifact digest. All 27 raw archive members match their extracted bytes and the extraction manifest. The independent audit reconciles 136 original AP2 files, 24 x402 files and the four frozen owned sources with the prospective plan.

The captured Linux runtime reports Python 3.13.1, 185 actual distributions and all 182 required pinned versions. Its 184 pip install records agree with the captured distributions; `pip check` reports no broken requirements. The runtime inventory contains 14,728 files. The portable-runtime SHA-256 is `81f940a9f665d3d0bb8a8a3aae90f14f3a5b23b99ef07de26bc4c5e8af8509d2`; the 2,033,972-byte pip report SHA-256 is `9c6356bb6054546add8b977b5cd667a84ac80156245f43e7973c0a0ceed88995`. These are capture bindings, not post-run rehashes of the discarded hosted venv or inherited Windows wheel fidelity. The failed caller produced no imported-runtime result.

The plan declares offered cart/payment selection index zero, wallet consent, cart confirmation and explicit OTP choices. No actual offered selection or human reply was executed in this capture. The owned proxy, scripted business caller, added public SDK Task read and explicit human-fact intervention remain disclosed. V1 grants no original `run.sh` provisioning, autonomous ADK shopper, independent bridge, human gold, untouched holdout, whole-task, idempotency, full-study or checkpoint credit.
