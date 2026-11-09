# Linux filesystem recovery decision

26 October 2026. The user resumed after the explicit Ubuntu launcher ran.
The retained Linux-v4 installer result is terminal `failed` at `locked-sync`.
Its uv stderr identifies permission denial renaming a temporary cache directory
for websockets 15.0.1 under `/mnt/p/.../runtime-agentops-linux-v4/cache`.
The seven receipt files, original 421 source files and downloaded Linux uv
archive/executable still match their recorded hashes. The installer did not
reach runtime inspection or reserve native-v4 execution. No native test,
application request, HTTP control or model call ran.

A direct, explicit Ubuntu read-only probe from the sandbox still returned
`Wsl/Service/E_ACCESSDENIED`. This is an execution boundary, not evidence that
Ubuntu is missing. The failed installer and all its cache/runtime contents are
preserved. No unchanged retry, mount-option change, permission repair or
application shim was attempted.

The [v5 protocol](protocol.md) specifies a fresh exact replica on Ubuntu's native
disk filesystem, with preflight rename/mode/symlink/lock checks. Its original
source and Linux-v4 controllers are unchanged. A new Linux HTTP-v2 controller
binds to actual passed native-v4 evidence and resolves packages from the verified
Linux runtime. A single wrapper can install and run the native control, then
prepare/run HTTP only if the native/effect gates pass. It exports exact inputs,
receipts, referenced runtime bytes and labeled terminal converter/compatibility
source snapshots into its own parent namespace. It preserves Linux originals.

[Filesystem software validation](../../../../runs/agentops-native-eligibility/software-validation-filesystem-v5.1/result.json)
passes 13 authored tests. The earlier ten-test result and earlier helper bytes
remain retained. A separate AI review caught pytest convenience symlinks and
insufficient outer deadlines; the final wrapper records symlinks inertly and
uses outer deadlines longer than nested controls. Symlink-policy tests use
constructed filesystem answers on Windows, not observed Linux links.
[HTTP-v2 software validation](../../../../runs/agentops-http-control/software-validation-linux-v2/result.json)
passes 12 new tests plus seven existing HTTP and three effect-checker tests:
22 tests, for **35 current software tests** across the two components. No actual
Linux installer or application is covered by those Windows software checks.

The [replica input review](../../../../runs/agentops-native-eligibility/replica-input-review-v5/result.json)
checks 442 exact copied files, including 421 original application files, eight
native harness inputs and the HTTP direct inputs. It imports only coordinator
modules in a disposable Windows copy; it installs no runtime and imports no
AgentOps app. The v5 PowerShell launcher passed syntax parsing. These checks
support preparation, not end-to-end execution success.

Run once from normal PowerShell in the project directory:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v5.ps1
```

The new output is `runs/agentops-native-eligibility/linux-filesystem-v5`. Its
`result.json` gives separate native, HTTP and export outcomes. Do not interpret
relative paths inside its `workspace` export against the parent failed-v4 tree.
No v5 execution directory exists at the time this decision is recorded.

Parallel read-only C1 review found no currently justified algorithmic distinction
beyond the previously screened strong comparators. The concrete next analysis
is complete public-operation serializer/ADK-converter/guard composition on the
actual Linux runtime, retaining raw alternatives, arbitrary legal guesses,
identity, original-task effect and continuous state/history obligations.
The exporter preserves relevant installed sources for this purpose. Ordinary
symbolic preimage/reachability is the comparator; a typed/raw contrast alone
is not novel. No change to the approved method route is asserted.

Three context records are saved under continuation-v11 before this update.
Earlier Windows/Linux failures, v4/v1 sources and manuscripts remain unchanged.
The original full contribution/artifact/paper objective remains active. C1,
bridge/domain qualification, complete evaluation and human review remain open;
CP2 is in progress, CP7 pending and verified deliverable credit stays 5%.
