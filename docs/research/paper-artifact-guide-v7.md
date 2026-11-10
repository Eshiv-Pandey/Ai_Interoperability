# Manuscript v7 artifact guide

[Manuscript v7](../../paper/working-draft-v7.md) adds the complete cache ablation,
the paired original AP2 payment-tool development matrix, and all original
AgentOps/AP2 candidate-reference allocations. The [claim ledger](../../paper/claim-ledger-v7.json)
binds every new result to retained files. The [v6 guide](paper-artifact-guide-v6.md)
documents inherited evidence and reproduction instructions.

| Result | Evidence |
| --- | --- |
| 1,584 cache-ablation cells; no additional certified cases over goal-pruned direct | [raw/source audit](../../runs/shared-cache-ablation/read-review-42879031721-1/result.json), [results](shared-cache-ablation-results-v3.md) |
| 65 AP2 cells; 36 purchase observations and 31 error-free owned-cell purchases | [numerical reconstruction](../../runs/ap2-reference-development/v5/retained-42881390576-2/numeric-peer-review-v1.json), [independent source/gate review](../../runs/ap2-reference-development/v5/retained-42881390576-2/independent-peer-review-v1.json) |
| 34 AgentOps candidates: 20 complete recipes, 10 partial, two unsupported and two failed | [raw/source/state census](../../runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/independent-raw-state-census-v1.json), [retention](../../runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/retention.json) |
| 34 AP2 candidates: 29 fresh ADK prefixes, 28 generic-status adverse processes, zero purchases | [allocation evaluation](../../runs/ap2-original-shopper-development/v7/retained-42886479185-1/extracted/independent-bank-evaluation/result.json), [independent raw review](../../runs/ap2-original-shopper-development/v7/retained-42886479185-1/independent-raw-peer-review-v1.json) |

These are authored development studies with declared deterministic models and
ASGI interventions. Candidate-prefix feasibility, finite admission, purchase
completion, and an error-free task are separate observations. Human gold,
untouched held-out independence, native/provider qualification and the full
original 96-task/three-path and 96-crossing study remain open. A negative
comparison is preserved as a research result; no superiority is inferred.

Recheck the manuscript and its retained evidence bindings using a fresh path:

```powershell
python -I -S -B paper/audit_draft_v7.py --output paper/draft-audit-v7-reproduction-1.json
```

The read-only manuscript audit invokes no solver, application or provider. The
upstream application workers and separate evaluators are described in the
[AP2 matrix guide](ap2-reference-development-v5.md), [AgentOps guide](agentops-governed-app-reference-v4.md),
and [ADK guide](ap2-original-shopper-development-v7.md). Preserve prior attempts;
use fresh prospective allocations for any new execution.

Independent AI checks remain assistance in the same research workflow, and do
not represent accountable final human scientific review or paper acceptance.
