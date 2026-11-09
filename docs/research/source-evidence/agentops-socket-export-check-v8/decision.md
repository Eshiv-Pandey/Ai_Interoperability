# Parent verification for socket resume v8

26 October 2026. This is verifier preparation and data-only checking. No new
Linux application, HTTP, bridge or model execution occurred. Verified project
credit remains **5%**; the full method/artifact/paper scope is unchanged.

`scripts/check_agentops_socket_resume_v8.py` checks the v8 export without
executing archived source. It verifies the original 460 launch inputs, the
launch seal, prior-attempt/export bindings, exact exported file inventory,
original Linux paths, setup commands and streams, installed metadata and native
interpreter provider. Native success additionally requires unchanged source,
runtime and harness bindings, exact pytest command/phases, effect-check records
and recomputed boundary effects. HTTP success requires that native result,
the exact service command/readiness paths, ordered captures, clean shutdown,
and recomputed five-exchange/six-boundary wire/effect semantics.

Nested captures must occur inside their owning controller stages. Native
observations must occur inside captured pytest execution; HTTP boundaries must
occur between service readiness and shutdown, before the wire checker runs.
Both socket-policy records must identify the selected installed runtime. A
successful record cannot excuse an allowed capability probe or other network
attempt, fabricate a different service command, or silently omit a domain write.

The checker binds selected installed modules to the preserved distribution
`RECORD` hashes, including the HTTP handlers and urllib3 capability source.
The original v7 export did not contain five HTTP modules because its HTTP stage
never ran. Five accessible local recovery-runtime copies match those retained
Linux distribution hashes byte-for-byte; `sources/` and `source-bindings.json`
retain their actual bytes and origins. They are source inputs, not new Linux
observations. The untouched setup compatibility check identifies 166 installed
distributions and all 421 application source files.

Validation history is retained:

- `socket-export-validation-v8`: fixture setup failed before any tests because
  the earlier export lacked an HTTP handler source file. Raw error streams remain.
- `socket-export-validation-v8.1`: 13 constructed-export tests passed with
  explicitly inert, never-executed placeholders for missing HTTP sources.
  The tested checker/test versions are retained. This version did not establish
  correspondence between those sources and installed package RECORDs.
- `socket-export-validation-v8.2`: 17 tests passed using the actual hash-matched
  source copies. Four additional controls reject a handler changed together
  with its harness hashes, an allowed probe relabeled as exempt, observations
  outside pytest, and a changed HTTP service command. Tested source bytes and
  raw stdout/stderr are retained.

All successful *new native/HTTP outcomes inside the test fixture* are constructed
under `tmp/authored-*`, with an explicit authored-data marker. They are not
experimental results. The fixture also preserves genuine earlier failure/setup
records, keeping their identity separate. Passing verifier tests does not prove
compatibility with a not-yet-captured real v8 result.

The prepared execution command remains unchanged:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v8.ps1
```

Once that attempt finishes and exports its evidence, run a new parent audit:

```powershell
python -B scripts\check_agentops_socket_resume_v8.py --output runs\agentops-native-eligibility\socket-resume-parent-check-v8.json
```

If either output already exists, inspect it; do not rerun an existing attempt or
overwrite an audit. The audit can verify retained failure integrity without
reporting native/HTTP semantic success. It cannot create missing captures or
replace the blocked runtime launch. This session's managed shell cannot access
Ubuntu; normal-PowerShell execution was requested in the preceding continuation.

Limits remain explicit: these checks establish consistency against sealed
inputs and retained records, not capture authenticity, complete authentication
of every installed file, independent human review, method novelty or a qualified
benchmark domain. Actual native/HTTP v8 compatibility, unchanged bridge
qualification, a distinct fair-comparator advantage and the later research
gates remain open. No gate credit or paper result is added.
