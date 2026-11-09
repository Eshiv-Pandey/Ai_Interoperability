# AgentOps grading software source review v2

Review series: 29–30 October 2026. This is an implementation review record for the supervisor demo, not a paper draft.

The sources below have no remaining source-level blocker within their declared finite JSON, lifecycle and evidence-retention interfaces. The reviewer read source and test bodies without importing SDKs, executing tests or graders, launching an application, calling a model, or reading credentials. Separate isolated standard-library audit programs verified retained software-capture bytes and wrote exclusive sibling review receipts.

## Reviewed final bytes

| Component | Source SHA256 | Test SHA256 |
|---|---|---|
| `scripts/agentops_runtime_stream_v1.py` | `547f904e7ff073035a3128592751a72ea4727fa978d1a43c7e16963170f896ed` | `a5d642fe2d9cf9ab0a76a5352642effdb35eaf3fa2b6a4e09d01535699d2debe` |
| `scripts/agentops_asgi_capture_v2.py` | `3b010e6c393cebe81e623bba4d77ccd5d07b9039dfcec66dedd15faceec389bf` | `37e45f571643e8edb5b7431cf5b5c675443206bec69f9cd491908dabde94dd51` |
| `scripts/serve_upstream_agentops_cases_v2.py` | `132bb5b464eb1d0077a9a44ece99c48316076623d716a3bbfde49caaec760386` | `47519bc549edc79ab70099d0f0746b07ab6b9f23df759e18a68788591644f856` |
| `src/interoperability/agentops_runtime_stream_evidence_v1.py` | `0bc4002cf726f0df6ce719102a0c7bee1049a39f2f9239a1ccc76cf887e51d49` | `ebeb44c4a6f79a43c7543b32d7119e94ea13e83c9f744bcea106d2ec97071a0e` |
| `src/interoperability/agentops_source_case_assessment_v1.py` | `996173207112b97c3e9b6ec72d01bb32232684a2de4efcd36e65c85f5461b769` | `cd43527df12b627340e59557e36823086ad0bc361676b9e72f9284d8afe8a21e` |
| `src/interoperability/upstream_agentops_native_runner_v2.py` | `fbc4f2f7334298669ce1a33e6d99c7c81139703282079061e1ccf0d5873baa59` | `9660f2283464a120162846628df24d805312a550ce3030ece8ef814d427c6f11` |
| `scripts/assess_upstream_agentops_case_v1.py` | `e2401c03dfde733f08c30e8b4a6f852a67eb41e7d969d728155c14378cbeb48e` | `f01cece4453b79d53d55e90a344ac919c0c93046cc8f9cbb20d3be85d01137d5` |

The corresponding runner CLI `scripts/run_upstream_agentops_cases_v2.py` is `ead8739c4df0ac319f1f814e7e3b8f72758c7a82148d259da6c7fc37a952bfae`. Test files use each component's matching `test_*.py` name; the runner uses `tests/test_upstream_agentops_native_runner_v2.py`.

## Findings and scope

- The recorder preserves the original bound invocation, supplied objects and async-generator send/throw values. Full immutable JSON bytes are captured before yielding the identical event. Original cleanup stays in the same task and context. Capture faults disable observation without retrying the business invocation.
- A reviewed receipt-publication gap was fixed: qualifying JSON is written and synced to an exclusive pending file before replacing the recorder's unchanged, identity-checked empty placeholder. Failed writes retain nonqualifying evidence. Directory-entry crash durability remains explicitly unproven.
- ASGI v2 inherits the frozen v1 transport/business observer. Live memory boundaries and memory errors remain separate; absence, an empty materialized store and unsupported evidence stay distinct. Boundary reads do not establish continuous absence, closed writers or cross-store atomicity.
- Bootstrap v2 binds the exact original runner instance/class/method/code origin and installs only its instance observer. Full snake_case serializers use `model_dump_json(exclude_none=True, by_alias=False)`. Imports follow resource checks. Finalization follows settled serve tasks; active calls defer it, lifecycle faults keep the outer summary partial, and missing/empty/mismatched persisted receipts cannot qualify.
- The closed-journal loader requires strict finite JSON, complete root/call receipts, exact file and directory membership, all manifests, supplied input bindings and contiguous global publication sequences. A concrete `True == 1` / integer-versus-float comparison gap was fixed using recursive type-aware equality for summaries, all identity descriptors and expected input trees; six resealed regression cases cover it.
- The pure assessor binds application/evaluator case identities and ordered source labels, exact user text and native user/session context. Native generated IDs remain distinct from source evaluator labels. Only null/false thought and null/empty metadata defaults are allowed on text parts. The original required-trajectory metric is scored separately per turn at threshold 1.0. Response, dependency, state, schema and answer assessments remain separate and pending or unavailable.
- Runner v2 requires clean owned shutdown before reading complete, receipt/source/context-bound journal evidence. Stream or memory faults stop successful export and preserve closed partial state. Its original seven-file wire profile and exact five-file v1 public projection are rechecked after copies and exports, including empty directories. Archived memory export is separate. Source/model/ownership/resource/repetition gates remain inherited from v1; evaluator reference bytes enter hash verification, not runtime staging or model input.
- The runnable assessment CLI retains exclusive source/input/journal bindings, selects one paired source case, checks boundary identities again after scoring, and preserves failed assessments without repairing inputs. A final-report close/flush failure could originally leave stale eligible JSON; review required the same pending-write/sync/close and owned-placeholder publication discipline as the recorder. The corrected CLI also checks pending bytes and retains a separate noneligible publication-failure receipt. Directory-entry crash durability and continuous immutability remain unproven.

These closures establish software behavior within the stated interfaces. They assign no original case grade, native qualification, causal tool execution proof, source authentication, model result, full task grade or project completion percentage. The assessor consumes caller-supplied validation JSON and does not independently authenticate or reopen its filesystem evidence.

## Retained software audit evidence

Under `runs/agentops-grading-software`, independent sibling receipts verify `trajectory-v1` (16 tests), `memory-v1` (20), `stream-v1` (37), `asgi-v2` (8), `bootstrap-v2` (65), `stream-evidence-v1` (26), `case-assessment-v1` (21), `runner-v2` (45), and `evaluator-cli-v1` (8): 246 software tests, zero failures, errors, skips or alternate successes. All retained manifests, source copies, current frozen source bytes, selected test files, isolated commands and machine/text log summaries agree. CRLF normalization occurred only in memory.

The frozen v1 reviewer is `4e5048015f07894bbd9a0330b3c20cf713f8d26cda139684e47e2feb586700a0`; its original four actual captures also received a read-only spot check confirming integer descriptors/counts and exact directory sets. The stricter v2 reviewer is `9ae3946bb2a45bc544b5a7ae70a2b947733b8f889e197d594727f4f677bb8163`, and records type-aware descriptors/counts and exact directory membership directly. No tests were rerun by these audits.

The v3 and v4 reviewers retain the same stricter checks for the case-assessor and runnable CLI captures and bind their matching frozen drivers; runner v2 was checked through the unchanged v2 reviewer against frozen driver v2. Every allocation has a fresh `<capture>-independent-review.json` sibling receipt binding its exact bytes and reviewer source. Frozen component sources and consumed captures remain preserved.

This source-review and software-capture audit is complete. Live admission behavior, original benchmark effects, substantive second-domain evidence and contribution acceptance remain separate work; additional software-review generations earn no native result or project-percentage credit.
