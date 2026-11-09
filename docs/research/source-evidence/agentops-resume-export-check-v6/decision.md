# Parent verification for the runtime-resume export

26 October 2026. `scripts/check_agentops_runtime_resume_v6.py` verifies a returned
v6 package without starting WSL, an installer, the application, a model, or a
network request. It does not modify the runner or any of its 453 sealed inputs.
The existing normal-PowerShell launch command remains unchanged.

The checker validates the v6 schema, exact input inventory, original failure
binding, unchanged prior export, Linux namespace, complete file inventory,
retained stage commands and stream hashes. Duplicate, ambiguous, missing,
undeclared, changed and linked files are rejected using the existing path and
file-record validators. Outer native/HTTP summaries must agree with the retained
inner results. A failed attempt can pass integrity verification without acquiring
a native or HTTP success claim.

Runtime verification binds the successful old locked-sync receipt to the failed
old inspection, requires corrected revalidation, checks original lock membership,
critical distributions, selected boundary sources and built-in/extension provider
bytes. The full managed capability command must match the source-owned probe.
Command operands and the recorded working directory must be present and correct.
Native preparation, execution and HTTP inventories must agree with revalidation.

Only trusted parent code is imported. Two native-gate receipt reads rebase
verified original Linux command operands into local export paths; the stored
bytes and their hashes are unchanged. The existing native gate recomputes the
separate boundary-effect check. The original wire checker recomputes HTTP
envelopes, task/context/confirmation binding, callback attribution and exact
database changes. Native and HTTP success also require matching successful
capture receipts and ordered outer stages. Archived Python is never imported.

The [current software validation](../../../../runs/agentops-native-eligibility/resume-export-validation-v6.3/result.json)
uses a complete **constructed** package, real unchanged application/input bytes,
synthetic interpreter and SDK bytes, and authored outcome records. Its 13 cases
cover full checker composition, unchanged raw receipt bytes, malformed commands,
missing working directories, schema/prior bindings, contradictory summaries,
native provider identity, omitted boundary sources, failed native captures,
stage overlap, a resealed network attempt and a resealed unrelated HTTP effect.
The new runtime bytes cannot execute; synthetic SDK modules raise if imported.
These fixtures and their success records are test data, not application results.

All validation attempts remain separate. The first failed before running cases
because a test class path attribute shadowed `unittest.TestCase.run`. The second
passed 11 cases and correctly rejected the network mutation, but its assertion
expected different error wording. Both test-harness fixes preserve the original
checker behavior. The third passed all 12 original cases. The fourth additionally
requires an explicit capture working directory and tests its omission. Reports,
process streams and exact source snapshots are retained under
`runs/agentops-native-eligibility/resume-export-validation-v6*`.

Once v6 produces terminal exported evidence, write a new audit with:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/check_agentops_runtime_resume_v6.py --output runs/agentops-native-eligibility/runtime-resume-recheck-v6.json
```

Existing audit paths are refused. The script is not run on a missing attempt;
absence is not a failed application trial. Full actual-Linux-capture compatibility
remains unverified until that package exists. Hash and receipt consistency do
not prove capture authenticity, complete interpreter/dependency authenticity,
fresh execution, independent reproduction or independent scientific review.
Existing semantic checkers are reused, not independently reimplemented.

The prior context is snapshotted under `snapshots/continuation-v14` before this
update. Original v6 inputs and all earlier results remain unchanged. Actual
native/HTTP results, installed-SDK confirmation-channel analysis, unchanged
bridge qualification, second-domain validity, C1 method advantage, full
evaluation and human review remain open. No scientific gate credit is added:
CP2 stays in progress, CP7 pending, verified deliverable credit 5%.
