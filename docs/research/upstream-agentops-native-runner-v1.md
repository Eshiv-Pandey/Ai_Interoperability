# Native AgentOps source-case runner v1

Updated 29 October 2026. The runner, client, bootstrap, owned-process helper and evidence-retention pipeline are implemented. Software validation and a prospective resource decision are listed below. No original source case has executed, and this runner assigns no benchmark grade.

The existing [admission demonstration](supervisor-package-v1.md) remains the primary 31 October deliverable. No paper draft is required this week. This runner adds the native execution path needed for the source-derived benchmark; it does not establish scientific novelty or 70% completion.

## Implemented execution path

[The outer runner](../../src/interoperability/upstream_agentops_native_runner_v1.py) validates the retained [21 application cases and 22 turns](../../runs/upstream-agentops-cases/v1/application/cases.json) against their export receipt, and verifies all 421 original regular files against ingestion. It hashes original evaluator files solely for source preservation. Evaluator response texts and trajectories are never parsed as answers, supplied to the model, or staged with runtime inputs.

The default schedule mirrors the source sample counts: core once, report three times and workflow three times. This is **33 isolated case/sample instances and 34 user turns**. Counts come from inert TOML/AST inspection of the original wrappers; the A2A runner does not execute or reproduce those wrappers' evaluation metrics. An explicit subset/sample override is recorded and cannot be reported as all-case execution.

Every sample receives fresh state and context. Both turns of the memory case keep the same prospective user/context/session, and each completed next turn requests a new task. Nonempty source session state is rejected. Actual retained session, task, event and invocation identities are checked separately after clean shutdown; expected identities alone establish no observed mapping.

[The bootstrap](../../scripts/serve_upstream_agentops_cases_v1.py) embeds the unchanged original objects: default `create_app()` for core, and original `triage_report_agent`/`triage_workflow` through explicit `create_app(agent=...)` for report/workflow. The original prompt and full tool surface remain in use. The unmaterialized acquisition link `agents/python/agent -> src/agent` is recorded; importing original `agents/python/src` avoids materializing or altering it.

The native interpreter uses `-I -S -B`. Only after the bound resource checks pass does the bootstrap add the staged original source, captured observer and executable-derived venv library paths. It executes no `.pth` or `sitecustomize`. Dependency metadata and file identities are retained; intersecting installed/locked versions and missing declared dependencies are checked. Matching that intersection is explicitly **not** an exact lock-equivalence claim.

## Transport and process ownership

[The client](../../src/interoperability/upstream_agentops_client_v1.py) sends exact source user text through native JSON-RPC `SendMessage`/`GetTask`, with explicit `A2A-Version: 1.0`. It preserves prepared requests, raw received HTTP/body bytes, task observations, timing and partial failures. It neither answers confirmation prompts nor retries failed tasks automatically.

The original card omits interface `protocolVersion` and includes a global legacy `0.3` compatibility field. The client retains that card and records **unresolved version advertisement**, separately from the source-supported requested 1.0 attempt. There is no rewritten card, invented version default or legacy fallback.

Before any HTTP request bytes are sent, [the accepted-socket guard](../../src/interoperability/windows_tcp_ownership_v1.py) matches the server side of the established loopback connection to the constructed original Python PID inside the owned Job. It checks exact local/remote endpoints and membership before and after the read-only Windows TCP-table query. An ownership rejection stops the case before request dispatch. This is observed process membership, not source authentication.

[The Windows Job helper](../../src/interoperability/windows_owned_job_v1.py) creates the wrapper suspended, assigns it before resuming, and uses only owned handles for cleanup. No unrelated process is searched for or terminated. Empty-group observation requires the signaled exact main handle, independent `ActiveProcesses=0` accounting and an empty PID list. Forced termination remains a failed clean qualification across retries. Failed cleanup retains live handles; the owner process keeps retrying until it can close them, including through output-pipe and Python-interruption faults.

## Resource gates and retention

The fixed minimums are **1 GiB available physical memory and 2 GiB available commit**. Two observations must be 10–30 seconds apart on UTC and monotonic clocks. A prelaunch receipt is bound to source/service paths, family, provider/model, listener, interpreter, bootstrap digest and stop token; it must be at most 60 seconds old when the bootstrap enters. The bootstrap independently checks current headroom before heavy imports. Source staging also has a separate gate after identity hashing. A refusal creates no native application or SDK launch.

The original `/healthz` response must be exactly `{"status":"ready"}`, with the bound construction receipt and guarded connected socket. A ready port alone is insufficient.

Graceful shutdown uses an atomic, token-bound file request. The bootstrap waits for Uvicorn's started state, then requests original lifespan drain. The outer process waits 20 seconds before an owned forced cleanup. A stop acknowledgment alone establishes neither lifespan completion nor process exit.

After corroborated terminal cleanup, the runner retains all state files, including lazy memory stores and any sidecars. It runs the existing read-only raw exporter, public normalizer and binder only from closed evidence. Unsupported sidecars/schema or incomplete exports remain explicit partial outcomes. Business snapshots around HTTP exchanges are captured by the passive ASGI observer. General memory-effect and trajectory grading remain separate work.

## Run the first diagnostic

The Gemini key is already encrypted under the current Windows account and injected by the existing local helper inside the owned native wrapper. Do not paste it into chat or command arguments. The outer process never reads the key or clipboard.

The tested provider identifier differs from AgentOps's original default `gemini-3.5-flash`; selecting it through supported `AGENT_MODEL` is a disclosed configuration change. The earlier synthetic provider probe establishes no original AgentOps result.

Use a fresh allocation after checking that it is unused:

```powershell
C:\Python313\python.exe -I -S -B scripts/run_upstream_agentops_cases_v1.py --model gemini-3.1-flash-lite-preview --case agentops_agent_core/inventory-status --samples 1 --output runs/upstream-agentops-native/inventory-status-v2
```

The first allocation, [inventory-status-v1](../../runs/upstream-agentops-native/inventory-status-v1/result.json), is consumed. It was refused before staging: the two [resource observations](../../runs/upstream-agentops-native/inventory-status-v1/prestage-gate.json) at 16:50:31 and 16:50:41 UTC had 684,273,664 and 769,675,264 available physical bytes (about 653 and 734 MiB). Both commit observations passed; both physical observations failed. Zero native applications and zero case requests were attempted. The [independent refusal audit](../../runs/upstream-agentops-native/inventory-status-v1-independent-review.json) passed 67 checks, without another measurement or run. Do not rerun v1. The v2 path above was unused at this update and requires sustained resource improvement and a fresh unused-path check.

The runner itself retains the resource decision and refuses staging/launch if it fails. Omitting `--case` and `--samples` selects the complete 33-instance schedule. Expansion requires a qualified first path; the scheduler stops on an unqualified instance and records the remaining instances as unattempted.

## Validation and limits

- [Client final capture](../../runs/upstream-agentops-native-software/client-v1/result.json): 30 tests passed, zero failures/errors/skips; [independent audit](../../runs/upstream-agentops-native-software/client-v1-independent-review.json) passed 51 checks. Guard-refusal fixtures observed zero request bytes across card, send and polling exchanges.
- [Bootstrap final capture](../../runs/upstream-agentops-native-software/bootstrap-v2/result.json): 51 tests passed, zero failures/errors/skips; [independent audit](../../runs/upstream-agentops-native-software/bootstrap-v2-independent-review.json) passed 44 checks. The failed 51-test bootstrap-v1 capture is preserved. A stale mocked Uvicorn signature caused its three failures; source behavior was unchanged and the mock was corrected.
- [Owned-process final capture](../../runs/upstream-agentops-native-software/owned-job-v2/result.json): 23 mocked tests passed, zero failures/errors/skips; [independent audit](../../runs/upstream-agentops-native-software/owned-job-v2-independent-review.json) passed 48 checks. Earlier owned-job-v1 is preserved. The final version attaches cleanup authority before cleanup itself can raise.
- [Runner final capture](../../runs/upstream-agentops-native-software/runner-v3/result.json): 33 tests passed, zero failures/errors/skips; [independent audit](../../runs/upstream-agentops-native-software/runner-v3-independent-review.json) passed 84 checks. Runner-v1/v2 are preserved intermediate captures. Final tests cover quarantine output, wait, cleanup and snapshot interruptions as well as resource refusal, source/reference isolation and accepted-socket ownership.
- [Independent source review](../../runs/upstream-agentops-native-software/source-review-v1.json): 49 checks passed, zero outstanding source blockers within the declared software scope. It binds the terminal sources and captures; it executes no tests, SDK, model or native application. External hard termination and source authentication are outside these checks.

The [authoritative component index](implementation-status-v1.json) binds these receipts and the refused resource decision. Intermediate captures are retained and overlapping test counts are not added.

All these tests use temporary loopback or mocked ownership/runtime fixtures. These new runner captures contain **no native original case, SDK/model execution, new upstream grade or admitted natural-triage run**. Historical fixture execution remains separate. Raw/public consistency does not prove causal completeness, source authentication, general effects, a second domain, a new scientific contribution or human acceptance. The goal remains active; the next independent implementation is the reviewed general trajectory/effect grader.
