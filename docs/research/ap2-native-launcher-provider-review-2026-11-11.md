# Original AP2 launcher and provider requirements

Source-only review, 2026-11-11. No application or SDK imports, application launches, model requests, network requests, Git operations, or changes to frozen V13/V14 evidence were performed for this review.

## Verified inputs

- Original AP2 commit: `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`.
- Source root: `runs/ap2-environment-preparation/source-stage-v1/ap2/` (abbreviated `AP2/` below).
- Source manifest: `runs/ap2-environment-preparation/source-stage-v1/manifest.json`; current SHA256 matches V13's pin `78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463`.
- Installed environment manifest: `runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json`; current SHA256 matches V13's pin `4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5`.
- Runtime package root: `runs/ap2-environment-preparation/installed-environment-v1/environment/Lib/site-packages/` (abbreviated `SITE/` below).
- The ten AP2 files covering the launcher, three module entrypoints, server, executor, resolver, catalog, shopper root, and retry agent were rehashed against the source manifest and matched.
- GenAI 1.66.0 METADATA and RECORD hashes matched the installed manifest. Inspected `SITE/google/genai/_base_url.py`, `client.py`, `_api_client.py`, and `SITE/google/adk/models/google_llm.py` also matched their recorded hashes. Package/version evidence: installed manifest lines 1851-1873; file evidence: lines 17637-17640, 32821-32824, 32837-32840, 33365-33368.

## Original launcher and native entrypoints

`AP2/code/samples/python/scenarios/a2a/human-present/cards/run.sh` is the original convenience launcher. It runs from the repository root, defaults to `PAYMENT_METHOD=CARD` (lines 10-25), loads root `.env` (35-39), and requires `GOOGLE_API_KEY` unless case-normalized `GOOGLE_GENAI_USE_VERTEXAI=true` (41-46).

It provisions/syncs dependencies (48-69, 92-99), clears `.logs/*`, recursively deletes and recreates `TEMP_DB_DIR`, and sets `AGENT_PROVIDER_PUBLIC_KEY_PATH` (101-112). Consequently, it must not be executed against frozen or existing evidence/state roots.

Its exact original entries, under `uv run --no-sync [--env-file .env] --package ap2-samples`, are:

| Entry | Listener/RPC | Source |
| --- | --- | --- |
| `python -m roles.merchant_agent` | `127.0.0.1:8001/a2a/merchant_agent` | launcher 128-130; `src/roles/merchant_agent/__main__.py` 24-36 |
| `python -m roles.credentials_provider_agent` | `127.0.0.1:8002/a2a/credentials_provider` | launcher 132-134; `src/roles/credentials_provider_agent/__main__.py` 26-40 |
| `python -m roles.merchant_payment_processor_agent` | `127.0.0.1:8003/a2a/merchant_payment_processor_agent` | launcher 136-138; `src/roles/merchant_payment_processor_agent/__main__.py` 26-38 |
| `adk web --host 0.0.0.0 code/samples/python/src/roles` | ADK web shopper interface | launcher 143-144 |

All `src/` paths above are relative to `AP2/code/samples/python/`. Original server code loads each adjacent `agent.json`, constructs the original executor and SDK handler/store/context builder, adds original middleware, and executes `uvicorn.run` with loopback host and keepalive 120 (`src/common/server.py` 51-93, 197-207). Agent-card URL is the RPC prefix plus `AGENT_CARD_WELL_KNOWN_PATH` (206). `.logs/watch.log` is relative to process CWD (`src/common/watch_log.py` 45-54). Shared key paths derive from `TEMP_DB_DIR` (`src/common/constants.py` 11-19).

A fresh isolated CWD with its own `.logs` and shared temp/key directory can therefore invoke the exact original modules without destructive resets. This would establish original module launch only; it must not be described as qualification of the full unmodified `run.sh` provisioning/deletion workflow.

## Original model dependence

- Every native executor constructs original `genai.Client()` (`src/common/base_server_executor.py` 69-73). Requests activate the payment extension before dispatch (85-96), then route from the first text part through `determine_tool_to_use` (134-147). Exceptions inside that handling path become original failed Task responses (149-153).
- `src/common/function_call_resolver.py` 52-68 supplies original function names/docstrings, instructions, disabled automatic calling and mode `ANY`; lines 84-88 call `gemini-3.1-flash-lite-preview`.
- `src/roles/merchant_agent/sub_agents/catalog_agent.py` 50, 60-78 constructs another original client and asks the same model for schema-parsed `list[PaymentItem]`; original code then writes carts/risk artifacts (80-96).
- Original ADK shopper root uses the same model and `max_retries=5` (`src/roles/shopping_agent/agent.py` 36-38). Required ordering is product choice, shipping, eligible payment selection, checkout, human confirmation, signed checkout/payment mandates, credential association, payment initiation, user OTP relay, `initiate_payment_with_otp`, and receipt (48-73). Raw JSON/tool/SD-JWT data stays internal (75-78).
- The retry class recursively retries failed ADK runs (`src/common/retrying_llm_agent.py` 42-89); that does not bound all successful model/tool/subagent turns. A prospective run needs its own explicit total request and turn accounting.
- Original human-present route does not use the `AGENT_MODEL` override from separate `shopping_agent_v2`.

Documented real-provider configuration is `GOOGLE_API_KEY`, or Vertex with `GOOGLE_GENAI_USE_VERTEXAI=true`, project/location and ADC/service-account authentication (`AP2/README.md` 78-124). Original mock OTP is `123` (scenario README 128-130). No credential presence, authentication, model access, quota or capacity was examined here.

## Supported source-preserving offline boundary

The pinned GenAI SDK supports an environment base-URL override without replacing `genai.Client`:

- `SITE/google/genai/_base_url.py` 34-50 documents precedence and reads `GOOGLE_GEMINI_BASE_URL` or `GOOGLE_VERTEX_BASE_URL`.
- `SITE/google/genai/client.py` 419-424 resolves that URL and supplies it through original `HttpOptions`.
- Gemini mode still requires a nonempty API key and adds `x-goog-api-key` (`SITE/google/genai/_api_client.py` 705-723).
- ADK constructs the same original Client with `HttpOptions(base_url=self.base_url)` (`SITE/google/adk/models/google_llm.py` 298-313); with the ADK field unset, the SDK environment override remains reachable.

The smallest disclosed offline candidate is Gemini mode with a conspicuous synthetic key and `GOOGLE_GEMINI_BASE_URL` pointing to a separately owned loopback Gemini HTTP fixture. Keep the original Client, SDK, model string, module entries, tools, stores, cards and RPC paths unchanged. The fixture must implement actual SDK wire responses for function calling and schema-parsed catalog output, reject unexpected requests and enforce explicit request bounds. Isolate provider credentials and proxy/endpoint configuration so the fixture route cannot become a real-provider route.

Important SDK detail: `Client()` resolves `get_base_url(vertexai or False)` before `BaseApiClient` reads `GOOGLE_GENAI_USE_VERTEXAI` (`client.py` 419; `_api_client.py` 565-570). Do not assume `GOOGLE_VERTEX_BASE_URL` alone redirects original no-argument constructors.

This candidate can qualify untouched native launch and SDK/provider traffic with synthetic responses. Predetermined fixture answers cannot qualify genuine model tool selection, real Gemini access, or autonomous original shopper behavior.

## Eligibility and claim limits

The frozen installed assessment itself records no original runtime/native application qualification (`environment-manifest.json` 3740, 64860, 64876-64878). V13 replaces `genai.Client` at `scripts/ap2_reference_development_v13.py` 519-582 and explicitly records `original_native_server_launch_qualification_established=False` at 705. Those receipts cannot establish the proposed original module launch or provider boundary.

Before a new offline native run is eligible: prospectively pin source/environment/boundary; allocate fresh stores/logs/keys; verify exact original entries, listener/card/RPC paths and owned cleanup; preserve original extension activation and business dispatch; bound and account for all synthetic provider requests; and exercise public same-task OTP-to-receipt continuation. Full shopper qualification additionally requires the original ADK route and human-confirmation sequence.

Real-provider qualification remains a separate gate requiring verified credentials, access/capacity, explicit request accounting, and actual original model decisions. Current no-model/no-application-call constraints prohibit attempting that gate during this review.
