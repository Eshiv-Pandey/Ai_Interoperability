# Original native AP2 shopper: retained development observation V1

Run [43038234376](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43038234376) reached the original ADK shopper and three original native services, but its first shopper generation timed out before any shopping tool or visible response. This is one retained failed development case. It supplies no whole-task success score, semantic gold grade, receipt or settlement evidence.

The run used frozen head `f8bc3028fd936490bef80de89efe57e4e4fcf6eb`. The root-retained artifact contains 37 files and 1,226,464 archive bytes. Its SHA-256, independently recomputed and matched to the GitHub API digest, is `9276a05ffd1dbc29e732fe42f4a116bf64653df54d5555b71a6e6ae189f761b2`. The offline analyzer also joined every ZIP member to the extracted manifest, then checked the extracted bytes of its 26 inspected members.

| Observed measure | Retained result |
| --- | --- |
| Allocated development cases | 1 |
| Native merchant, credentials and processor readiness cards | 3 |
| Original ADK events | 6, all error events from `root_agent` |
| Original business function calls / responses | 0 / 0 |
| Visible final model messages | 0 |
| Public user messages | 1 initial request |
| Actor replies proposed / delivered | 0 / 0 |
| Receipt records with the original success shape | 0 |
| Upstream allocations, including smoke | 2 |
| Known reported provider tokens | 45, entirely from smoke |
| Allocations with unmeasured usage | 1, the timed-out shopper request |
| Local refusal records after the timeout | 4 |
| Reaped native / shopper processes | 3 / 1 |
| Offline integrity / consistency questions | 0 |

The first allocation was the declared access smoke. It returned HTTP 200 and a forced `access_check` function call after 19.220809 seconds between its recorded allocation and terminal timestamps. The requested endpoint was `gemini-3.1-flash-lite-preview`; the retained successful response reports `modelVersion: gemini-3.1-flash-lite`. This establishes access-smoke response behavior only.

The second allocation was the original shopper's first model request, containing 7,557 retained request bytes. After 45.068243 seconds between its recorded allocation and terminal timestamps, the parent recorded `TimeoutError` and its owned HTTP 502 transport-failure response. The ledger contains no actual upstream response body or reported usage for that allocation. Its usage is unknown; the reported 45-token partial sum cannot be treated as the full run's consumption. The two requests total 7,913 bytes and have a recorded allocation timestamp gap of 24.201628 seconds. Recorded allocation timestamps do not independently establish exact network-send timestamps.

The original `RetryingLlmAgent` emitted one 502 error event, then four 429 events corresponding to the owned proxy's refusal after the adverse result, and finally a maximum-retries-exhausted event. Those four refusals made no additional upstream allocation. The original retry logic was preserved. Its terminal error event has no model content, so the public actor had no visible question and supplied no reply. The worker's `public_actor_stopped_without_unambiguous_unseen_question` and zero process exit code describe the controller's orderly return; they do not establish a successful shopping task. This case failed before rendering could be evaluated.

The retained original-root binding records the original `common.retrying_llm_agent.RetryingLlmAgent`, the three declared original subagents, the original tool names, official ADK runner, unchanged GenAI client and `gemini-3.1-flash-lite-preview` model. Its imported root-source hash matches the frozen plan. The runtime manifest's own hash and all recorded required/installed versions match the plan, including Python 3.13.1, ADK 1.28.0 and GenAI 1.66.0. The manifest inventories 14,728 runtime files; those installed package bytes are not separately archived by this artifact.

Native stdout records merchant PID 2529, credentials PID 2530 and processor PID 2531. Parent cleanup records those PIDs and shopper PID 2532 as reaped. Listener ownership before card requests is a retained parent assertion from the source's `/proc` ownership check; separate socket-inode snapshots are absent. Source-copy and original-source immutability are also retained parent observations. Full original A2A Task/wire exchanges, hidden effects, signature validation and real settlement are outside this result's evidence.

The frozen public actor still requires consecutive ordinal product rows, independently checked USD prices within the USD 100 budget, separate wallet consent and checkout confirmation, and a visible explicit OTP question. The offline analyzer can join the first displayed Cart ID to a preceding original `find_products` SDK return and later original `select_cart` argument/return/session state, without assuming displayed order equals catalog order. That branch was unreached in this run.

Reconstruction and 21 constructed offline controls are retained in [offline-analysis-43038234376-2](../../runs/ap2-native-shopper-provider-development/v1/offline-analysis-43038234376-2/analysis.json), including exact source snapshots and control stdout/stderr. Earlier analysis directory `offline-analysis-43038234376-1` remains retained. The second output adds the explicit ADK-error outcome, provider timing/path records and native-card/source joins.

The analyzer SHA-256 is `fd07c3609400f951d8500ce97f1cc655fc4ed654b7836597c30d26262ef930ab`; its analysis JSON SHA-256 is `0861c3fbf0bcb5f53692d146167cae42c4d65408b8f6c03b33847f1a1cf2b6a1`. The 21 controls passed under `python -I -S -B`. They exercise observation integrity, forced-final visible text, error events, tool identity/order, proposed versus delivered replies, OTP timing, visible price reconstruction, original empty-issuer receipt shape, Cart ID joins, failed/unknown provider usage, response hashes, runtime joins and ZIP/manifest binding. They do not execute original applications, SDKs, native services or providers and do not replace human task grading.

A prospective successor may evaluate a longer, newly frozen owned sender timeout if the unchanged downstream SDK permits it. This V1 result remains one failed allocation and cannot be repaired or replaced by a later run. Whole-task grade remains `null`; human gold, held-out study and original `run.sh` provisioning qualification remain false.
