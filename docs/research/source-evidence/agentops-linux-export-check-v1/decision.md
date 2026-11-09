# Parent-side Linux export checker

26 October 2026. No v5 attempt directory, result or live Windows WSL process was
observed in the current continuation. No WSL execution or unchanged installer
retry was attempted. The user-side v5 launch remains the execution prerequisite.

`scripts/check_agentops_linux_workspace_v5.py` now checks exported evidence from
the parent workspace without importing any exported script or running WSL,
AgentOps, an installer, a service or a request. It separates the parent controller
receipt namespace, replica-relative file records and original absolute Linux
paths. It requires the approved 442-file input seal, rejects missing/undeclared
or changed files, duplicate/case-colliding names, traversal, materialized links,
inconsistent roots and failed export references.

For reported native success it reuses trusted parent-side native/HTTP gate and
effect-checker code through rebased data readers, checks package lock membership,
critical packages, original editable URL, installed file records and native
fcntl snapshot. For reported HTTP success it binds the native prerequisite,
source/harness, runtime inventories and stage receipts, then recomputes the
existing raw-wire/effect semantic check. Failed or partial attempts can receive
an integrity result without being described as successful controls.

An existing timing limitation is handled explicitly: the original HTTP checker
hashes its own open stdout/stderr in `check.json.inputs` before printing. These
are capture-time hashes, not final stream seals. The new checker checks stable
inputs, relies on terminal `result.files` for final stream bytes and recomputes
HTTP semantics. It does not modify any original capture or silently promote the
older input list into a terminal seal.

[Validation](../../../../runs/agentops-native-eligibility/export-checker-validation-v1/result.json)
passes ten authored integrity/namespace/stage and trusted-reader tests on Windows.
These tests do not establish full successful-Linux-capture compatibility; no
complete captured v5 success is available yet. The existing semantic checks are
reused, not independently reimplemented. Hash/receipt consistency is not proof
of capture authenticity, a fresh experiment, complete runtime authentication,
independent scientific reproduction, human review or C1 novelty.

After v5 produces terminal evidence, a new parent audit can be written with:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/check_agentops_linux_workspace_v5.py --output runs/agentops-native-eligibility/linux-export-recheck-v1.json
```

The required execution command remains unchanged:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v5.ps1
```

Three context records are snapshotted under continuation-v12. All frozen v5
execution inputs and earlier evidence remain unchanged. No scientific gate
credit is added; CP2 stays open, CP7 pending and verified deliverable credit 5%.
