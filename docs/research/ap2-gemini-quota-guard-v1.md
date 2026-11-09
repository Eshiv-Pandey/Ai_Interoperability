# Gemini quota evidence and fail-closed accounting

30 October 2026. **No usable quota or positive native reservation is verified.** The saved key and one successful synthetic request do not establish the project's tier, remaining allowance or safe native input/output bounds. No key value, model, provider quota API or original service was read/called for this work. One unauthenticated public documentation page was fetched.

## The nonsecret information needed from AI Studio

1. Open [AI Studio projects](https://aistudio.google.com/projects) and select the project belonging to the saved key. Show the project's tier/billing status. Keep the key hidden; do not send the API-key page or credential file.
2. Open [active rate limits](https://aistudio.google.com/rate-limit), select that same project and find **`gemini-3.1-flash-lite-preview`**. Capture the exact displayed RPM, input TPM, RPD and any other applicable limit. Copy what is shown, not a different model's row or a generic table.
3. Show current usage/remaining counters for the same project/model and the time range/date. If a counter is not displayed, say **not shown**. An advertised limit alone is not a remaining allowance.
4. Record when the capture was taken and its timezone. Identify other applications or keys using this project; their traffic shares its limits. Do not assume that a second key supplies a separate quota.

Google's current [rate-limit policy](https://ai.google.dev/gemini-api/docs/rate-limits) says limits apply per project, RPD resets at midnight Pacific, preview models have tighter restrictions, and active limits can change with account/tier status. It also says stated capacity is not guaranteed. The [public-page receipt](source-evidence/gemini-quota-policy-v1/result.json) retains this source; no authenticated account was inspected. Priority/batch tables on that page are not this free project's allowance.

The retained [tool smoke](../../runs/gemini-access/tool-smoke-v1/result.json) reports 45 prompt and 10 output tokens, 55 total, for one request on 29 October. This is real historical provider usage, not today's remaining quota. The [key wrapper](../../scripts/with_gemini_key.ps1) supplies the secret only to a child; it checks neither tier nor allowance.

## What still blocks original calls

The [workflow](../../RESEARCH_WORKFLOW.md) requires a verified per-model envelope, 20 percent kept untouched, conservative full-input plus maximum-output reservation before each request, and provider usage reconciliation afterward. RPM/input-TPM/RPD and the study's input-plus-output token envelope are different constraints. If the account has no displayed total-token pool, its finite study-envelope interpretation must be recorded and reviewed; do not manufacture one from context size, a pricing table or the 55-token smoke.

The original HP [router](../../runs/ap2-environment-preparation/source-stage-v1/ap2/code/samples/python/src/common/function_call_resolver.py) and [catalog](../../runs/ap2-environment-preparation/source-stage-v1/ap2/code/samples/python/src/roles/merchant_agent/sub_agents/catalog_agent.py) set no maximum-output-token cap. A safe bound must include the original system instructions, tool declarations/schema, prompt/history and provider output maximum. The smoke's 32-token cap cannot silently replace the original configuration. No verified full-input or output bound exists here.

GenAI 1.66.0's `_request` retries `_request_once`; default options allow four retries. Its async path also has an internal aiohttp reconnect request. A counter around `models.generate_content` or only the outer retry function misses attempts. Any later runtime hook must cover each actual HTTP attempt, including reconnects/redirects, and bind the exact SDK source. It must preserve original payloads and record outcomes without keys, headers, prompts or generated bodies.

The installed-source references are bound by the [environment manifest](../../runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json), SHA256 `4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5`:

- [google/genai/_api_client.py](../../runs/ap2-environment-preparation/installed-environment-v1/environment/Lib/site-packages/google/genai/_api_client.py), SHA256 `3f1a7c22fc01c870511880bb78f27b790d4c7104b2e8998611fa6547c72acce4`, contains the retry and async reconnect paths.
- [google/genai/types.py](../../runs/ap2-environment-preparation/installed-environment-v1/environment/Lib/site-packages/google/genai/types.py), SHA256 `ed16f181e4c8f6938a51aa0b92a2ca9e5241a6bef59c81360646798875641b41`, lines 7284-7331, declares prompt/candidate/tool-use/thought counts as total components and cached input as included in prompt.
- [google/genai/models.py](../../runs/ap2-environment-preparation/installed-environment-v1/environment/Lib/site-packages/google/genai/models.py), SHA256 `684bd02b8203a2230356411fc5d38219e04c927b0aa0f386cd0d6bdb97300d87`, passes the Gemini response's `usageMetadata` into `usage_metadata` in `_GenerateContentResponse_from_mldev`.

These are conservative code-reference relations, not authenticated real-provider counting or entitlement evidence. The generated type also contains a "not supported in Gemini API" note; a source inspection cannot resolve that provider-documentation ambiguity. The accounting checks enforce the known nonnegative component lower bound without assuming missing fields are zero or adding cached input twice.

## Executable software and integration API

[ap2_hp_gemini_usage_v1.py](../../src/interoperability/ap2_hp_gemini_usage_v1.py) is a standard-library accounting core:

- `validate_policy(policy, now=...)` requires explicit reviewed limits, counting/reset rules, scope, input/output bounds and hashed evidence. Unknown values have no numeric defaults. Hash checks establish file identity, not authenticated entitlement.
- `create_ledger(path, policy, now=...)` initializes one new shared SQLite ledger only after validation. It creates no native reservation receipt.
- `reserve_attempt(path, expected_policy_sha256=..., role=..., request_sha256=..., now=...)` uses an atomic transaction, keeps at least 20 percent untouched, and reserves the full input/output bound and one request. Call this before every actual attempt, including every retry. It does not dispatch anything.
- `record_provider_result(path, attempt_id, expected_policy_sha256=..., usage_metadata=..., http_status=...)` records allowlisted integer usage counts and explicit validation reasons. It uses consistent successful `totalTokenCount` literally, keeps at least full bounds for absent/malformed/contradictory/error usage, never refunds a request, and halts after any unknown/contradictory usage, 429 or an observed overrun. Contradictory usage retains the largest of the reserved bound, reported total and known component lower bound, using the larger of prompt/cached as the input lower bound when they conflict. Known prompt/candidate/thought/tool-use components cannot exceed the reported total; cached input is included in prompt and is not added again. Missing components are not inferred as zero. Contradictory reported counts remain visible without becoming a favorable refund.
- `install_guard(plan=..., service=..., configuration_sha256=...)` returns **`installed: false`** and `accounting_core_only_no_native_enablement`. This module is not a reviewed SDK transport interceptor and cannot satisfy the native runner's `enforce_before_every_provider_request` contract.

The [focused check driver](../../scripts/check_ap2_hp_gemini_usage_v1.py) uses synthetic limits and local test ledgers, with network/process launches denied. Those fixtures are not provider quota evidence. A successful software check cannot make the current policy/transport gaps pass. Source review is limited to accounting/refusal until a separate exact before-wire hook and real quota evidence exist.

The accounting/refusal source review closed on 30 October for module SHA256 `0475f889a5825626adaec6fc1b2477c15972a9c09138c795343538c3b391fe45` and focused-driver SHA256 `99f563ae934e5a30243f63e92810297113e5afadfbfde534ada8c04d4c1b3b14`. The review confirmed conservative unknown/contradictory charges and halting, prompt/cached lower bounds, floored 80-percent ceilings, atomic shared reservations, nonrefunded request slots and truthful native refusal. It did not certify exact SDK interception, entitlement, actual quota or native integration.

The once-only [core-v1 result](../../runs/ap2-gemini-usage-software/core-v1/result.json), SHA256 `9ac7c2d724c46f82e76b871fd88c03b7000170cbd96724d62f97391f5db12cb1`, reports **21 tests passed, zero failures, errors or skips**, using synthetic fixtures only. Its [test log](../../runs/ap2-gemini-usage-software/core-v1/stdout.txt) and frozen source/driver copies are retained. Captured copies match current source hashes. This run made zero provider requests and zero original-application imports, reserved no actual quota and enabled no native guard. The successful local tests establish accounting/refusal behavior only.

No automatic reset, reserve unlock, billing upgrade, quota purchase, provider probe or native attempt is authorized by these files. Current required inputs remain: the same project's actual limits/usage/tier, a reviewed finite envelope and full request bounds, and a reviewed exact SDK interception implementation.
