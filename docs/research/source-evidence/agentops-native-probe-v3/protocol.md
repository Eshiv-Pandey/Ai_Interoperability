# AgentOps recovery-runtime native control v3

25 October 2026. This is a prospective continuation of the [v2 protocol](../agentops-native-probe-v2/protocol.md).
It preserves the same original test, passive observer, independent effect checker,
strict upstream pytest configuration, seed, four snapshot boundaries, offline model
double, network guard and 300-second limit. No upstream code or dependency is changed.
It is one in-process development control; real HTTP, bridge qualification, task
validity, C1 advantage and human review remain separate unfinished obligations.

The original dependencies-v2 receipt records failure. A separate recovery environment
now exists under `external/runtime-agentops-v2-recovery-2/venv`. v2's launcher cannot
use it: it requires both the failed path and a successful sync receipt. v3 directly
inspects this installed environment instead of inventing an installation receipt.
Python 3.13, all critical versions, every installed distribution/version's membership
in the source lock, distribution isolation, duplicate names and the editable original
AgentOps source URL are checked. Installed METADATA/RECORD/direct-URL files and selected
SDK/test boundary modules are hashed before preparation and again before execution.
This establishes the stated local inventory only: it does not reconstruct the install,
independently resolve the dependency closure or authenticate all installed file bytes.

`prepare` verifies 421 original files and the seed, hashes all inherited/new harness
files, captures runtime metadata and checks whether this process can write/read a
fresh directory created with pytest's mode 0700. That capability probe imports no
application or pytest code. Its binary output, error, exit status and untouched test
directory are retained. A preparation failure cannot be replaced. A permission failure
does not imply an AgentOps failure and does not launch the application test.

Once prepared, `run` exclusively reserves `execution.json`, verifies the complete
prepared inventory and runs the unchanged original node once. There is no replacement
fixture, permission change or alternate test. The original source is rehashed after
execution. All three pytest phase reports must pass. The original fixture's copied
seed must match the immutable seed across all database content/schema fields. The
separately authored v2 checker then checks the captured original-task completion,
exactly one attributed inventory effect/audit, and no unrelated boundary changes.
Its result is separate from pytest success. Failed tests or checks remain failed.

Preparation:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/agentops_native_probe_v3.py prepare
```

Execution, from the research workspace in the user's normal PowerShell when the
sandbox's directory capability probe fails:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_native_v3.ps1
```

The launcher installs nothing, uses no provider credential, calls no live model,
changes no source/seed and starts no HTTP server, cloud resource or cluster. The
unchanged upstream test uses its normal throwaway dataset. A result under
`runs/agentops-native-eligibility/native-probe-v3/result.json` records the actual
outcome. Do not repeat the command after an attempt; inspect its retained receipts.

No preparation or inventory check counts as application success or checkpoint credit.
Boundary snapshots do not prove absence of transient intermediate changes or all
transaction, authentication, concurrency or durability properties.
