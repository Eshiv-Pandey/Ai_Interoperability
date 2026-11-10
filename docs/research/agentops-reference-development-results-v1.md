# AgentOps original-component development references

The six existing development tasks now have retained reference receipts. Five
contain actual original read-tool outputs; the note task remains unexecuted.
This is component evidence for the task/gold bank, with **0 of 6 original App
tasks passed and 6 of 6 unknown**. It is not an AgentOps application benchmark,
a model success rate, or independent human gold qualification.

| Existing development task | Actual original evidence | Unexecuted obligations |
| --- | --- | --- |
| d01 health/active incidents | Inventory normalization, down status, exact unresolved incident membership | Governed App request and grounded final answer |
| d02 dependent diagnosis | Incident-derived checkout/high-latency identifiers; status; unfiltered logs; linked runbook; subsequent pool filter | Original same-user recall, model plan, final observations versus hypotheses |
| d03 restart pause | Exact incident, status, unfiltered log and linked runbook decision-context reads | Actual guarded call/SDK confirmation, suspended application task, human proposal feasibility |
| d04 same-session note | Initial absent note store and unchanged business state retained; no note tool invoked | Original PII-backed save, actual same-session subsequent recall, completed first application task |
| d05 structured report | Original incident/log/runbook outputs and original TriageReport JSON schema | Original structured-report App and generated grounded report |
| d06 keyword retrieval | Original keyword result and bounded candidates; exact rank/text independently recomputed from pinned runbooks | Governed App final answer, human relevance judgment and diagnosis restraint |

Private evaluation accepts 3 complete component recipes, 2 partial read
recipes, and 1 unexecuted component recipe. These labels describe the narrow
reference recipes above, not completed development tasks. Its 95/95 checks
include metadata, ordering, state and explicit unknowns; the d04 checks do not
constitute a successful note write. Ten deliberately forged component-output
controls are rejected. They are software controls, not ten task trials.

## Retained execution and verification

- Main supplement: `runs/agentops-reference-development/v1-20261110-5-postcapture/`
- Read audit: `runs/agentops-reference-development/v1-20261110-5-postcapture-audit.json`
- Original first-five minimal captures, including the failed evaluator result:
  `runs/agentops-reference-development/v1-20261110-4/`
- Existing installed dependency snapshot:
  `runs/agentops-reference-development/v1-20261110-3/dependency-manifest.json`

The supplement reuses the first five actual captures with explicit hashes and
per-case provenance, and executes only d06 afresh. An evaluator correction was
necessary: Pydantic's JSON schema does not emit a `default: []` for the original
model's `default_factory=list`. The original failed capture/result remains
unchanged. No task was rerun to improve that result.

The fresh read audit verifies all 73 supplement files (530,435 bytes), the raw
JSONL streams against actor observations, all original source/seed bindings,
the 95 private checks, and all ten forged-output controls. Each minimal actor
verified eight original imported source files and 91 frozen imported dependency
files. Original source data, services, incidents and audit rows remain unchanged.
No note store was created, no network operation was attempted, and no child
process was launched by these six minimal actors. The sole private-evaluator
read probe was blocked in every actor.

## Scope and prior failures

The fixed public controller invokes fully imported original functions against
fresh exclusive copies of the pinned data and state. It bypasses original read
resilience wrappers, never runs the governed App/model, and reports no observed
SDK identity when a context was not constructed. The original structured report
entrypoint is not selected. No hand-written or generated report is substituted.
The actor is denied access to the private evaluator and private seed gold; the
separate evaluator uses direct seed SQL, log bytes and runbook arithmetic rather
than importing the original tools.

The first two AP2-profile attempts failed during imports: missing explicit
isolated pywin32 paths, then missing Presidio. The third broad native-profile
attempt imported/executed d01 but observed a blocked networking attempt during
SDK/PII import and was rejected by the private evaluator. These failures remain
in `v1-20261110-1`, `v1-20261110-2` and `v1-20261110-3`. No source or PII stubs
were introduced. Low available memory led to the narrower minimal-read profile;
the actual PII-backed note initialization and SDK confirmation are unknown.

The reused dependency snapshot is of the already installed Windows runtime,
including Google ADK 2.10.0, MCP 2.2.0 and the paired Presidio 2.2.364 packages.
Minimal actors import neither SDK nor PII/model modules. This snapshot establishes
file bindings for the components actually imported, not native application
qualification or equivalence to the AP2 dependency environment. The evaluator and
controller share AI authorship; human feasibility/relevance and independently
authored held-out validation remain pending. Existing bank-v1 JSON files were
not modified.

Implementation files: `scripts/agentops_reference_actor_v1.py`,
`scripts/agentops_reference_evaluator_v1.py`, and
`scripts/run_agentops_reference_development_v1.py`.
