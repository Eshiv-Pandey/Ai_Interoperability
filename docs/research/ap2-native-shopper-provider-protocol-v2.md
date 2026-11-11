# Prospective original native shopper development V2

V2 evaluates one additive development case using the unchanged original AP2 shopper, subagents, tools, GenAI client, native entrypoints and public actor. It changes the owned parent sender's transport timeout option from 45 to 120 seconds and adds bounded handler drain before proxy shutdown. It preserves run 43038234376 as one failed V1 case with unknown usage for its timed-out allocation. No V2 provider or original application execution occurred during this preparation.

The declared case is `ap2-native-shopper-provider-v2-correct-human`. All public human facts and actor grammar match V1; only the case identifier changes. The unchanged original root uses `gemini-3.1-flash-lite-preview`. Model payloads pass through byte for byte, with the inherited secret redaction applied only to retained bytes. No new SDK `Client`, model adapter, instructions, tools or source edits are introduced.

The owned limits remain 80 upstream calls including smoke, 200,000 cumulative request bytes, six seconds between allocations, a 100,000 known-reported-token stopping threshold, 600 seconds for the shopper worker, 12 public turns, 160 ADK events and a 900-second screen deadline. The token threshold remains a stop after a response; it is not a hard total consumption cap. Unknown successful, failed and unclosed allocations remain explicitly unmeasured. Original SDK/application retry policies stay unchanged and every request reaching the owned proxy shares its existing accounting budget.

The 120-second urllib option is a transport wait option. It is not claimed as an independently enforced whole-request wall-clock cap. Handler drain is separately bounded by the smaller of 150 seconds and the remaining screen time. It closes admission before waiting. A close during pacing cannot allocate a following call. Completed outcomes are written and counted before a stable final usage census. If the drain deadline expires, a separate short capture lock freezes payload, ledger and counter updates; the opening records of unfinished consumed allocations remain unclosed and their usage remains unknown. Late daemon sender completion cannot change the retained capture. Proxy shutdown follows that drain/freeze and census, so the final result and artifact cannot race with late provider file writes.

The source audit of the retained V1 runtime establishes that the unchanged downstream permits a 120-second parent response wait:

| Pinned source | Relevant behavior |
| --- | --- |
| ADK 1.28.0, `google/adk/models/google_llm.py:299–312` | Original Client construction sets tracking headers, retry options and base URL, with no timeout setting. |
| GenAI 1.66.0, `google/genai/types.py:2071–2072` | `HttpOptions.timeout` defaults to `None`; configured values use milliseconds. |
| GenAI `_api_client.py:212–222,1157–1169` | Configured milliseconds convert to seconds; unset timeout remains `None`. |
| GenAI `_api_client.py:985–993,1317–1323` | Installed aiohttp is selected and nonstreaming calls receive `ClientTimeout(total=None)`. |
| aiohttp 3.14.5, `client.py:252–256,694–700`, `helpers.py:655–663` | Supplied timeout object has unset fields and no timeout timer is installed. |
| Original catalog `catalog_agent.py:50,69–75`; GenAI `_api_client.py:1207–1212`; HTTPX `_config.py:78,127–130` | Original synchronous catalog uses an unmodified Client whose explicit `timeout=None` disables the HTTPX request timeout. |
| Original `common/payment_remote_a2a_client.py:30,54–55` | Original A2A wrapper has a 600-second timeout. |

The independent source reviewer matched GenAI, ADK and aiohttp source member hashes to the retained runtime inventory, and original root/retry/A2A source hashes to the retained plan. The artifact inventories installed runtime bytes; those installed bytes themselves are not all archived. Source timeout behavior establishes compatibility, not an observed V2 provider response or model capability.

Original `common/retrying_llm_agent.py:42–44,49–83,89` retains its five configured attempts including the initial attempt, catches exceptions, emits error events and recursively retries without an added sleep. ADK `google_llm.py:117` defaults its retry-options object to `None`; GenAI `_api_client.py:487–488` then permits one API-status attempt. GenAI aiohttp source at `_api_client.py:1327–1347` separately retains its original connection-reconnect behavior. V2 adds no retries and does not repeat until success.

Implementation is additive in [run_ap2_native_shopper_provider_v2.py](../../scripts/run_ap2_native_shopper_provider_v2.py) and [ap2_native_shopper_provider_boundary_v2.py](../../scripts/ap2_native_shopper_provider_boundary_v2.py), reusing byte-unchanged V1 preparation/source-copy helpers, original V3 provider/source constants and the V1 worker. The new prepared plan retains all five owned source files and hashes and checks them before execution. Source-copy isolation, original native listener ownership checks, cleanup and public-key-only retention remain inherited.

Fifteen constructed controls in [test_ap2_native_shopper_provider_v2.py](../../tests/test_ap2_native_shopper_provider_v2.py) pass without importing original SDKs, applications, native listeners or providers. They cover the actual 120-second sender option and unchanged request identity; call, byte, pace and usage guards; adverse/unknown responses; normal drain; bounded incomplete drain with unknown usage; prevention of late ledger/response writes; queued-handler and pacing-close races; and frozen source/timeout/public-fact fields. Constructed controls are software verification, not semantic gold or task results.

Root review and a newly frozen workflow/head precede any V2 dispatch. V2 remains an adaptive development follow-up with one declared case, whole-task grade `null`, no human gold, no held-out-study credit and no original `run.sh` provisioning qualification. The existing V1 result and its analysis outputs remain retained without edits.
