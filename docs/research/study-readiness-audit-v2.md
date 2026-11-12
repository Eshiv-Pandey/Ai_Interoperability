# Original-study readiness audit V2

12 November 2026. Additive post-V1 research work. The accepted V1 release, manuscript, global tracker and [initial incomplete checkpoint](study-readiness-audit-v2-work-in-progress.md) are preserved. No percentage is assigned by this audit.

The [successor inventory](../../runs/study-readiness-audit/v2-20261112-2/inventory-successor.json) binds the original 68-candidate inventory and all new code, test and qualification receipts. The original confirmatory study remains unqualified: zero qualified candidates, held-out tasks, base path cells or additional crossing cells. All 96 task slots, 288 base cells and 96 extra cells remain present and disabled.

## Implemented controls and actual results

The [standard-library validator](../../scripts/validate_study_readiness_v2.py) passed [six grouped source/snapshot checks](../../runs/study-readiness-audit/v2-20261112-2/validation-v2.json), hashing all 103 checkpoint inputs and verifying 51 distinct cited source files and ranges. It checks current public/private joins, original splits and obligations, semantic versus mechanical reference dispositions, source-binding freshness, second-instance refusals, disabled allocations, implementation pins, bridge direction, and human/holdout limits. Original Workflow V2's later execution remains an insufficient result alongside its preserved historical classification.

The [retained test receipt](../../runs/study-readiness-audit/v2-20261112-2/tests-40.json) records 40 passing constructed controls: 28 readiness/topology tests and 12 independent read-fragment tests. Negative controls reject development-to-holdout relabelling, AI-to-human review promotion, boundary-to-shopper promotion, stale source hashes, removed denominators, enabled unqualified cells, invented inverse conversion, altered crossing counts, missing grounded reads/results, foreign task/context identities and business writes. They are software controls, not additional study episodes.

## Independently implemented read-only fragment

The [owned reference oracle](../../scripts/qualify_agentops_read_fragment_v1.py) instantiated pinned schema/seed SQL only in a private in-memory SQLite database. Its complete business tables equal the retained initial state of development case `agentops-d01-health-active`. A separate Python projection computes service identity/status/owner and ordered unresolved incident identity/severity/status. It does not reuse the application's tool implementation or its evaluator's expected answer text.

The [actual qualification receipt](../../runs/study-readiness-audit/v2-20261112-2/agentops-d01-read-fragment-v3.json) passes 28 declared input worlds: three spellings for each of eight services, three invalid slugs and one absent service. For the single retained original development case, `" INVENTORY "` normalizes to `inventory`; the observed terminal reports `down` and active `INC-002`, `SEV1`, `open`. The emitted read and terminal share the actual call ID, precede the final answer, and bind to the episode's original public Task/context. Business state is unchanged. Every consumed raw case member matches the digest-bound original ZIP.

**Oracle completeness is limited to those 28 static read inputs. The full task oracle is incomplete.** Free-text grounding/relevance, allowed alternative trajectories, incidental durable-note policy, broader action continuations, runtime/capture authentication and human semantic gold remain outside the proved fragment. This is a new owned reference computation and a regrade of retained development evidence; it is not a fresh original application trial. New application/SDK/provider calls: zero.

## Four-stage crossing prerequisites

The [source-bound next controls](../../runs/study-readiness-audit/v2-20261112-2/next-crossing-controls-v2.json) check two prospective outgoing placement grammars, with one/two/three bridge edges among the same three edges of four fixed illustrative scripted stages. Remaining edges use reference delivery. Six grammar variants do not constitute six qualified original routes or episodes; execution remains disabled and no inverse conversion is invented.

The captured V4 original 421-file source manifest binds three additional inspected AgentOps source files. `server.py` requires `AGENT_ENTRYPOINT=agent`, so its original Workflow nodes cannot simply become four A2A roots. `composition.py` routes a configured MCP endpoint through `ops_mcp_toolset`; `mcp_client.py` permits exactly six operations read-tool names, excluding the generic A2A bridge delegation tools. This blocks a construction that assumes the original conversational agent automatically sees those bridge tools. A supplied scripted SDK caller is a disclosed construction requiring its own source-bound stages, actions, packet and task identity.

The next original crossing controls must bind actual receiving/sending surfaces, source application entrypoints, task/state/action horizon, converter revisions and native-matched headers/polling/streaming/representation. They must freeze the 24-task subset before confirmation outcomes and retain all one/two/three counts together. Configured mgcrea B7 is an explicit header treatment; B4-B7 remain one converter implementation. Original AP2 still lacks an eligible two-converter 0.3 profile pair. A new original compatible API is required for direct DataParts, extension headers, discovery/methods and task/context continuation; adding a shim or inverse mapping would require a separate disclosed route.

## Scope still open

All 68 candidates remain author/AI-exposed. The 48 second slots preserve 25 source-authored recipes and 23 specific refusals, with six authored AP2 boundary-only second recipes. Actual two-human task/contract/gold/reference/near-miss review and defensible independent holdout remain missing. None of the new checks promotes these candidates to confirmatory eligibility.

The gate must use ordinary `C_runtime`; private `C_gold` belongs to the independent grader. The read-fragment check does not implement or validate the practical extraction pipeline. Complete source-to-model abstraction, complete task oracles, two eligible independent routes per required domain, original SDK/wire confirmations and independent reproduction remain work for the prescribed full study.

Recheck into fresh output paths:

```powershell
python -I -S -B scripts/validate_study_readiness_v2.py --inventory runs/study-readiness-audit/v2-20261112-1/inventory.json --output runs/study-readiness-audit/your-unused-validation.json
python -I -S -B scripts/qualify_agentops_read_fragment_v1.py --output runs/study-readiness-audit/your-unused-fragment.json
python -I -S -B tests/test_validate_study_readiness_v2.py
python -I -S -B tests/test_qualify_agentops_read_fragment_v1.py
```

Existing outputs refuse overwrite. Initial tool versions and earlier receipts remain beside the successor. No paper/status/Git mutation or live dispatch was performed by this work.
