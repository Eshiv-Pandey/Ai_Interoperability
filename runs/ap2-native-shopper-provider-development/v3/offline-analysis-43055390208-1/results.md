# Original native AP2 shopper: retained development observation V3

Run [43055390208](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43055390208) passed runtime preflight and provider access smoke, launched three original native services, then failed the owned shopper worker's public-facts guard before original shopper ADK/SDK execution. The single case is retained as `executed_nonzero_retained`, with shopper exit code 1. No public conversation, original shopper tool call or receipt was reached.

The frozen head is `04dfdf2a3b1d1c75ad991e610df61815a329669e`. The root-retained artifact contains 30 ZIP members and 1,224,011 archive bytes, SHA-256 `921d50f1b5e5554e5a0366eefd9269bba9dcf5ddb497d71e96fbf35573e59c31`, matched to the GitHub API digest. Offline reconstruction validated archive/member identity, the reviewed V3 template, all five owned source snapshots, runtime/card hashes, provider ledger and capture-freeze records, with zero integrity/consistency questions. That consistency result describes retained evidence; the task itself failed.

| Observed measure | Retained result |
| --- | --- |
| Allocated development cases | 1 |
| Case / shopper exit status | `executed_nonzero_retained` / 1 |
| Actual selected Python | V3 virtual-environment `bin/python`, Python 3.13.1 |
| Required installed versions matching the runtime manifest | 182 / 182 |
| Original native readiness cards | 3 |
| Upstream allocations / successful responses | 1 / 1, access smoke only |
| Known reported tokens | 45, access smoke only |
| Allocations with unmeasured usage | 0 in this V3 capture |
| Original shopper ADK events / business function calls | 0 / 0 |
| Public actor replies / receipt records | 0 / 0 |
| Active handlers at capture freeze / unclosed allocations | 0 / 0 |
| Native / shopper processes reaped | 3 / 1 |
| Whole-task semantic grade | `null` |

The retained runtime manifest records `/home/runner/work/_temp/ap2-native-shopper-provider-v3-environment/bin/python` and that virtual environment's root, with every required version matching the frozen plan. This is direct selected-interpreter evidence for the launcher path corrected after V2. The runtime manifest hash is `d0c0662cdb2d05ce2f7462926e6daac8ad87c6edc21e7182004745bcc18dd161`. Installed package bytes are inventoried rather than independently archived in this artifact.

The access-smoke response contains the declared `access_check` function call and reports `modelVersion: gemini-3.1-flash-lite`, 35 prompt tokens, 10 candidate tokens and 45 total tokens. The requested endpoint remains the original `gemini-3.1-flash-lite-preview`. There was no later shopper generation allocation. The 120-second sender option and frozen capture records are present, but this run has no in-flight drain or shopper-generation observation.

The actual shopper stdout terminates with `ValueError: only_frozen_public_human_facts_allowed` at inherited worker V1 line 301. That guard compares the entire supplied dictionary with its local `public_facts()` before creating the worker output directory or calling the application that imports the original ADK/SDK. Independent standard-library AST inspection of the frozen worker's literal facts and comparison with the retained supplied facts finds exactly one differing field:

| Field | Frozen worker expects | V3 supplies |
| --- | --- | --- |
| `case_id` | `ap2-native-shopper-provider-v1-correct-human` | `ap2-native-shopper-provider-v3-correct-human` |

All non-case public facts, including budget, selections, consent and OTP, match exactly. V2 introduced the changed case metadata while retaining the original owned worker's whole-dictionary guard; its earlier runtime failure hid this incompatibility. V3 exposed it after passing runtime/smoke. The source failure lies in the owned harness's metadata wiring, before visible actor grammar or original shopper model/tool behavior could be evaluated.

The native merchant, credentials and processor stdout PIDs are 2793, 2794 and 2795; shopper PID 2796 returned 1. All four appear as reaped in parent cleanup. Native entrypoint/card identity, source-copy immutability and listener ownership remain retained parent/source observations. The artifact supplies no separate socket-inode snapshots or full original A2A Task/wire capture. Three native services starting does not supply original shopper business-flow or settlement evidence.

The frozen V2 boundary closes admission, records zero active handlers at capture freeze and has no unclosed allocations; standalone/result drain records match the single raw terminal smoke observation. All-response usage is fully measured for that one captured smoke allocation. Earlier V1's unknown timed-out usage remains unknown, and V2's unexecuted preflight failure remains preserved; this new V3 result replaces neither history.

Actual reconstruction and source diagnosis are retained in [offline-analysis-43055390208-1](../../runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/analysis.json). [source-diagnosis.json](../../runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/source-diagnosis.json) joins the exact stdout failure, frozen worker facts, supplied facts, runtime identity and usage counts without executing SDKs or applications. The additive analyzer's seven schema/source/preflight controls pass and reuse the unchanged V2/V1 observation and drain helpers.

An additive V4 correction can align the owned worker's frozen case metadata with the actual launched worker and reject incompatibility before provider smoke. V1-V3 execution bytes and these failed records remain frozen. Human semantic gold, held-out-study credit, original `run.sh` qualification, hidden-effect/signature validation and real settlement proof remain absent.
