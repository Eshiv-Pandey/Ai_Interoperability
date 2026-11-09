# Independent effect check for the original AgentOps confirmation test

25 October 2026. The integrating agent authored the checker independently of
the separate agent's passive collector. Both use the original source test and
the declared snapshot format. This is separate software authorship, not human
scientific review. No application outcome is inferred from authored fixtures.

`scripts/check_agentops_effect_v2.py` imports only the standard library. Its
seed reader requires SHA-256
`957ae8da4e1d174b9ff349acfca7ce4c204020a572fbeb7245783285d49d455b`, opens SQLite
in read-only/query-only mode, and closes it explicitly. It does not import
the observer, application, SDK, pytest or their decision functions.

The checker binds the initial request, original task/context, nonterminal
confirmation pause, returned confirmation identifier, exact DataPart response,
completed event association and original test locals. It compares the complete
services, incidents, audit and SQLite sequence rows, columns, schema and user
version at all four captured request boundaries. Before approval the domain
database must equal the original seed. After completion, only inventory's
status may change from down to operational; exactly one complete attributed
audit row and its sequence increment may appear. The audit invocation must
match both original callback observations. Its UTC timestamp must fall in
the approval interval with the source's whole-second precision preserved.

The retained [software verification](../../../../runs/agentops-native-eligibility/checker-validation-v2/result.json)
records three tests: a constructed positive profile, 29 altered evidence
cases, and five CLI malformed/missing-input cases. All pass. Binary stdout
and stderr, exact command and source hashes are retained beside that report.
These are checker tests; the constructed successful profile is not an observed
AgentOps execution, native reference or benchmark result.

The first expanded CLI test exposed a Windows sandbox failure when Python
TemporaryDirectory created a directory with mode 0700. Writing the first input
failed with PermissionError, then automatic cleanup failed with WinError 5.
The original `tmp/agentops-checker-pzblgwfs` remains untouched. That attempt also
reported an unclosed SQLite connection; explicit closing fixes the code issue.
The checker test now uses a fresh ordinary directory and retains its small
diagnostic files. The final verification treats ResourceWarning as an error.
This account of the earlier attempt is a visible-output narrative, not an
original binary capture.

The installed pytest `tmpdir.py` also uses `mkdir(mode=0o700)` for both its
base temporary directory and test directories (lines 139, 141 and 158).
No upstream fixture or pytest implementation is changed to accommodate this
sandbox. If the native test requires the user's normal terminal, use the
same reviewed harness and preserve its normal process receipts.

A passing checker establishes consistency at the saved boundaries only. It
cannot authenticate a fabricated capture, exclude a transient write restored
between snapshots, validate all session databases, prove transaction durability,
or establish all forbidden intermediate-action properties. Source/runtime
provenance, original pytest outcomes and task validity remain separate checks.
The in-process helper values are not raw HTTP bytes. Real HTTP, unchanged
bridge controls, the original C1 distinction and accountable human review
remain required before the corresponding research milestones can pass.
