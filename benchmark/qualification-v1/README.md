# Candidate qualification proposals

11 November 2026. This folder contains concrete task/answer proposals and a retained-evidence qualification table for all 68 authored candidates. It uses the latest original governed-App AgentOps v4 and original ADK AP2 shopper v7 allocations. Source files are read as text; raw JSON and journal files are inspected without original imports or execution.

[The current table](proposal-2/candidate-table.md) joins every public task to proposed facts/order/state, legitimate alternatives, near misses and exact source citations in [private rows](proposal-2/evaluator-private.json). [The current review packet](proposal-2/human-review-packet.md) shows all 68 concrete proposed answers and decisions for human review. [Second-instance review rows](proposal-2/second-instance-review.md) show all 48 second-slot decisions, including 25 concrete proposed answers and 23 specific refusals. The source-derived bank is development exposure; no independent human gold or held-out qualification is claimed.

AgentOps preserves the historical 20 complete / 10 partial / 2 unsupported / 2 failed mechanical census. Its semantic disposition separately identifies 19 supported declared reference obligations and the d03 action-decision gap. AP2 retains eight observed early/source obligations, one reset pair, 19 unrealized later branches and six prior boundary-only controls. Zero original shopper purchases complete. A completed declared read-only/refusal/reset obligation is not evidence that a purchase completed.

[The current study allocation](proposal-2/study-allocation.json) preserves 96 task slots, 288 path cells and 96 additional crossing cells. All 48 second slots are explicit: 25 source-supported parameter/state recipes are authored and 23 are refused pending their original unsupported/unrealized obligation. No blocked slot has invented completion gold. All native/reference and independent bridge route bindings and crossing subset placements remain unqualified. The slots are disabled. They do not replace missing experiments or authorize a narrowed study.

`proposal-1` is historical authoring progress with 48 then-unauthored second slots. `proposal-2/preliminary-revision-v1` preserves the preliminary second-instance public-text revision. Neither is the current package; use `proposal-2/validation-v2.json` and the current answer/review rows.

The build, validation and public-only preparation tools use the Python standard library. Preparation reads only the public application projection and source application's public bank, and emits no evaluator material. It runs no original app/model/actor, creates no runtime state allocation and dispatches nothing. No Git or authoritative tracker edits are made here.

```powershell
python -B benchmark/qualification-v1/build_second_instances_v1.py --base-proposal benchmark/qualification-v1/proposal-1 --output-dir benchmark/qualification-v1/<fresh-instance-directory>
python -B benchmark/qualification-v1/build_qualification_v1.py --second-instance-dir benchmark/qualification-v1/instances-2 --output-dir benchmark/qualification-v1/<fresh-proposal-directory>
python -B benchmark/qualification-v1/validate_qualification_v1.py --proposal-dir benchmark/qualification-v1/proposal-2 --output benchmark/qualification-v1/proposal-2/<fresh-validation.json>
python -B benchmark/qualification-v1/test_validate_qualification_v1.py
python -B benchmark/qualification-v1/prepare_next_reference_v1.py --candidate ap2-dev-001 --proposal-dir benchmark/qualification-v1/proposal-2 --output benchmark/qualification-v1/proposal-2/<fresh-public-packet.json>
```

Do not use literal angle-bracket placeholders. Existing builder directories and audit/preparation outputs refuse overwrite. The current validator passed eight checks across 68 candidates, 50 cited source files and 448 bound files. Nineteen constructed negative/positive controls passed. These are artifact/source-binding controls, not observed scientific gold or original runtime/model experiments.
