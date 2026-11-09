# Files for the two human task/gold reviewers: v2

30 October 2026. **The required bank of 12 development, 8 calibration and 48 independently authored held-out templates is not yet complete or qualified.** The files below contain public development cases, reference expectations, constructed algorithm examples and proposed second-domain checks. Reviewing these files does not pass CP3 or establish 70 percent project completion.

**Update from v1:** also read the [partial-observation correction note](agentops-partial-observation-correction-v2.md). The frozen stronger grader could count an incomplete tool call/reply as supported. New reply v2 and evaluator v3 APIs conservatively keep incomplete evidence unknown; the original trajectory metric is unchanged. Their focused tests are direct terminal software results, not native case grades. The existing v2 native grading CLI has not been integrated with this correction and must not be presented as corrected. The package includes the new source/tests and preserves the earlier development material.

Send each reviewer this index, a separate copy of [reviewer-feedback-v1.md](reviewer-feedback-v1.md), and the seven core files below. Each person should return their own completed form, identifying the files and case IDs they actually reviewed. No application run or API key is needed for this review. Attach linked source files when the reviewer needs to verify the underlying rule; links assume the project folder layout.

## Seven core files

| File | What to review |
| --- | --- |
| [Task inputs: cases.json](../../runs/upstream-agentops-cases/v1/application/cases.json) | The actual exported AgentOps user prompts and session inputs: 21 public cases, 22 turns. Check intent, ambiguity, permitted actions and session continuity. |
| [Reference expectations: expectations.json](../../runs/upstream-agentops-cases/v1/evaluator/expectations.json) | Match items by `eval_set_id`, `eval_id` and turn. These are evaluator-only reference answers/tool trajectories, not independently validated gold or observed execution. Check correctness, alternatives and missing requirements. |
| [AgentOps task, state and grading contract](upstream-agentops-grading-contract-v1.md) | Check source-backed intent, reply/dependency order, approval pauses, memory persistence, before/after state and reset obligations. Reference-answer equality alone is insufficient. |
| [Implemented stronger AgentOps checks and limits](agentops-stronger-grading-v1.md) | Check what the implemented evaluator actually measures and which semantic, sanitizer, ordering and effect judgments remain unassessed. Software test counts are not native task passes. |
| [AP2 proposed public checks and near misses](ap2-human-present-public-assessor-design-v1.md) | Review the second-domain candidate's task/context continuity, OTP forwarding, mandate and receipt binding, wrong-OTP retry and missing evidence. This is a design, not a completed AP2 task/gold bank. |
| [Admission algorithm semantics](admission-refinement-v1.md) | Check the bounded existential decision, supplied-model assumptions, supported/unsupported/unknown behavior and certificates. The implementation is a CEGAR/lazy-symbolic adaptation; novelty remains unestablished. |
| [Executed algorithm comparison and limitations](admission-benchmark-results-v1.md) | Review all eleven constructed development examples, certificate outcomes, equal-input comparison and costs. Candidate/direct agreement is not application accuracy or a superiority result. |

The two JSON exports can be reviewed as text. Start with `inventory-status`, `unknown-incident`, `restart-needs-approval`, `injection-restart-rejected`, `memory-note-recall`, `gateway-memory-report` and `resolved-cache-rejects-injected-action` if time is short. Mark all other cases unreviewed; this subset is not full-bank coverage. Keep both turns of `memory-note-recall` together.

## Source and example entry points

- AgentOps rules: [tools.py](../../external/agentops-c806b7f1/agents/python/src/agent/tools.py), [actions.py](../../external/agentops-c806b7f1/agents/python/src/agent/actions.py), [data.py](../../external/agentops-c806b7f1/agents/python/src/agent/data.py), [longterm.py](../../external/agentops-c806b7f1/agents/python/src/agent/longterm.py) and [report.py](../../external/agentops-c806b7f1/agents/python/src/agent/report.py). Use these to check allowed calls, seed/state rules, approved mutations, note persistence and report requirements.
- AP2 source interpretation and original-file links: [human-present source reassessment](ap2-human-present-source-reassessment-v1.md). A changed valid mandate is a near miss to assess, not a source-proven rejection. A synthetic payment receipt does not establish a real debit.
- Algorithm code: [candidate](../../src/interoperability/refinement.py), [direct solver and certificate checker](../../src/interoperability/refinement_oracle.py), [benchmark runner](../../src/interoperability/benchmark.py). The [eleven-profile manifest](../../examples/refinement-development/manifest.json) points to the actual constructed inputs.
- If reviewing CP2 contribution claims, also read the [four-method specification](shared-lifting-comparison-v3.md) and [adverse shared-lifting pilot results](shared-lifting-pilot-results-v1.md), with the [shared-lifting code](../../src/interoperability/refinement_shared_lift_v2.py) and [comparison code](../../src/interoperability/shared_lifting_comparison_v3.py). Caching reduced repeated relation work but did not establish an efficiency or novelty advantage. Grant the comparator the same evidence, legal actions, bounds, goal pruning and memoization.

## What to return

Complete the [separate feedback form](reviewer-feedback-v1.md). For each reviewed case, record task clarity, source-supported expected behavior, legitimate alternatives, near misses, state/reset requirements and grader gaps. Cite the exact file and case/turn or source line. Leave missing or uncertain evidence explicit. A task/gold review is not automatically the separate supervisor/mentor novelty-feasibility review.

Export fingerprints: task inputs SHA256 `3b58d64163533a9ddec2a68438b22a9fc1c43e7d5e50e8579fd7d766270bc146`; reference expectations SHA256 `8eb1fb24858bdd491319544973f9197a9fcbc436d82c8a017d96d3fdbaaa478f`. The [export receipt](../../runs/upstream-agentops-cases/v1/result.json) records their provenance. The [full rubric](checkpoints.md) remains unchanged.
