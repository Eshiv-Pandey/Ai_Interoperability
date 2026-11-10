# AgentOps task-bank AI source crossreview v1

10 November 2026. A different task-bank author in the same AI agent system reviewed the 34 AgentOps candidates against pinned original source. One missing source obligation was reported to the author, corrected by the author, and checked in the current evaluator. No confirmed source blocker remains in the inspected mappings. This is AI source crossreview, not independent human scientific review, validated gold, task execution or CP3 credit.

[The machine-readable receipt](../../runs/task-bank-review/agentops-v1.json) binds the exact current application/evaluator hashes, every reviewed record ID, source checks and fixed finding. [The bank](agentops-task-bank-v1.md) remains prospective with human review/runtime/gold qualification pending.

## Fixed finding

`agentops-h01-active-priority-skill` loads the full incident-triage skill. The original skill's line 14 requires reporting the most urgent incident's current service state, including when no severity/age tie exists. The earlier expected order stopped after discovery/load/list/rank and allowed status reads as an optional alternative. `list_incidents` returns incident severity/status/age but no current service health.

The author added an actual matching `get_service_status` observation before any leading-incident current-health claim and updated alternatives so that observation is required. The current record was re-read after the correction. Original citations: `agents/data/skills/incident-triage/SKILL.md:14` and `agents/python/src/agent/tools.py:21-55,82-103`, beneath `external/agentops-c806b7f1/`. Exact hashes/ranges are in the receipt.

## Inspected source behavior

| Area | Source conclusion and review limit |
| --- | --- |
| ranking and health ties | The read-only seed query independently confirms INC-002, INC-001, INC-009, INC-005, INC-010 active order. The declared h02 severity/age edit ties inventory/down with search/operational. Leading current service health needs an actual status response even without a tie. |
| confirmation and rationale | Approval requires confirmed is True, nonempty user/session/invocation identity and a stripped string rationale, accepting dict or bare-string payload. The 500-character checks occur before and after persistence redaction. Guarded proposal is distinct from function execution. |
| mock mutation and audit isolation | Restart changes the targeted service status and appends its attributable audit in one transaction; resolution changes the target unresolved incident status/resolved_at and audit, without changing service health or unrelated incidents. Actual recovery sufficiency stays human judgment. |
| replay vs new invocation | The action key is invocation_id/action/target. Existing-key lookup returns the original audit before mutation; a distinct invocation can create a new same-service audit. Bank correctly requires observed native same-key delivery and does not invent replay feasibility or global exactly-once effects. |
| notes ownership duplicates recall | Notes insert on each valid explicit save without action dedup. Recall filters actual user/optional incident before id-descending LIMIT 20 and uses a read-only existing-store path. Same-user new-session and other-user isolation need actual runtime identity, not fixture label text. |
| action and note kill switches | The governed action validator refuses writes before confirmation construction; action bodies repeat the switch. Note save separately checks its body switch before insert; recall remains a read. The two refusal layers are properly distinguished. |
| structured report and workflow tool limits | The report App exposes incident/log/exact-runbook reads only, with TriageReport output schema; memory/service-status tools are not silently added. The workflow remains four constrained read-only stages. request_triage_report retry/fallback is a separate programmatic path, not assumed App behavior. |
| retrieval missing logs and injection transformations | Keyword rank/slug tie-break, exact linked runbook, missing gateway-log error, historical/current separation and data-contained approval are scoped correctly. Sanitizer fences can change line-array length while retaining original count; exact PII behavior and causal sufficiency remain unvalidated. |

The seed database was opened using read-only immutable SQLite access, with query-only mode. Its SHA256 remained `957ae8da4e1d174b9ff349acfca7ce4c204020a572fbeb7245783285d49d455b` before/after. The independent query confirmed active rank `INC-002, INC-001, INC-009, INC-005, INC-010` and original inventory/down, search/operational, checkout/degraded health. This verifies the retained seed contents, not a native runtime state or successful task.

All 321 current citation instances matched file hashes and in-bounds ranges across 24 original source files. That check validates source byte binding; it does not authenticate acquisition history or a runtime capture.

## Current reviewed bytes

| File | SHA256 |
| --- | --- |
| `benchmark/tasks-v1/agentops/application.json` | `3eb5cb7a0ebcc5203d7e1c0edd6d5f13b503b9f908a3491670ea0ae95ec4607d` |
| `benchmark/tasks-v1/agentops/evaluator.json` | `2091981ecb2b1e84c30f52563c7dedee8764eef2a545d6cdb69aaaecd5f65ab7` |

The earlier evaluator hash, before the author applied the h01 correction, was `5b90e931fa0464c68f869752c638dbeaa7181c35cc45c7c7343d110f8a6ed81c`. Public tasks/family membership did not change in that correction.

## Remaining qualification work

Actual original App/tool/confirmation/task identity, bounded same-key replay feasibility, cross-session stable user binding, conditional second-action sufficiency, fixture initialization/reset, exact persisted/transformed data, reference trajectories and semantic grounding still need execution and independent human review. Unknown or unrealized lanes must not become invented successes. A reasoned source refusal is distinct from a validated positive continuation.

No original SDK/application module was imported or invoked for this review. No model/provider/native call, source/seed mutation, task-bank edit or Git action was performed by the reviewer. The author owns the reported correction. Only this note and `runs/task-bank-review/agentops-v1.json` were written for the crossreview.
