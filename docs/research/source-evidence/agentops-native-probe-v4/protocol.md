# Native AgentOps Linux recovery v4

26 October 2026. Prospective environment correction, not a replacement result.

The Windows native v3 attempt failed at collection: `agent.state` imports
`fcntl`, which Windows CPython does not provide. Preserve every v3 byte. The
upstream `SUPPORT.md` identifies Linux x86_64 release verification. v4 therefore
uses glibc Linux x86_64 with real interpreter-provided `fcntl`, the original 421
source files and unchanged upstream confirmation test, passive v2 observer and
separate v2 effect checker. No Windows shim or application port is used.

## Setup and execution

Use Linux bootstrap Python 3.11 or newer and a writable complete workspace.
On WSL Ubuntu, from this project's PowerShell working directory:

```powershell
wsl --exec python3 scripts/run_agentops_linux_v4.py
```

Or, from the same project directory in a Linux terminal:

```bash
python3 scripts/run_agentops_linux_v4.py
```

This downloads uv 0.12.0 using the exact Linux archive URL and SHA-256 in the
retained upstream `mise.lock`, selects CPython 3.13.1 (the previous Windows
patch version, recorded as a separate platform), and syncs the unchanged lock
and default dev group. Python, packages, cache and logs stay in the workspace.
It does not install an operating system or change system packages. Installation
uses network access; the subsequent native test is offline. Allow time and disk
for the original dependency set. No model, cloud resource or benchmark runs.

Setup has a separate exclusive receipt directory, retained binary process
streams, bounded download/subprocess timeouts and owned process-group cleanup
for timed-out setup children. Tool extraction accepts only the regular `uv`
member after the archive hash passes. Existing setup/runtime/native directories
stop the command; an interrupted or failed attempt must be inspected rather than
repeated. For setup alone, append `--setup-only`; later prepare/run the native
controller explicitly, without rerunning setup.

After setup succeeds, the default command prepares and runs native v4 once.
Preparation verifies source/seed, installed distribution versions against the
lock, runtime locations, native `fcntl`, relevant boundary module hashes and a
fresh mode-0700 write/read. Execution requires successful preparation, unchanged
inventories and exactly one passed setup/call/teardown phase for the selected
node. The original seed must match the isolated fixture seed. The separate
checker must confirm original-task completion, one attributed inventory/audit
effect and no unrelated changes at the captured boundaries.

Results are saved under `runs/agentops-native-eligibility/dependencies-linux-v4`
and `runs/agentops-native-eligibility/native-probe-v4`. Platform checks happen
before reserving either attempt. A future Linux result is not byte-identical
reproduction of the Windows runtime. Runtime metadata/source hashing does not
authenticate every installed file or independently resolve dependency closure.

## Interpretation

Software validation of the runner is authored harness testing, not an observed
AgentOps result. Linux setup and native execution have not occurred in this
session. The old HTTP v1 plan remains bound to failed native v3 and must not run;
after native v4 succeeds, a separately versioned Linux HTTP plan is required.
HTTP/version fidelity, bridge qualification, second-domain task validity, C1
novelty, frozen evaluation and human review remain open. No gate credit is added.
