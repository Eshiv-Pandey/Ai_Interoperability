# AgentOps Windows failure and Linux recovery

26 October 2026. This supersedes the prior native-v3 execution request.

The [retained v3 result](../../../../runs/agentops-native-eligibility/native-probe-v3/result.json)
records failure. Its stdout identifies collection-time `ModuleNotFoundError:
No module named 'fcntl'` at `agent/state.py:12`; pytest collected zero tests and
exited 4. Phase reports and passive helper observations are empty. The existing
wrapper's `application_test_started: true` means the pytest process launched;
it does not establish execution of the application test. The observer also
retained one blocked `socket.bind` attempt during import. No native completion,
effect-check result, HTTP observation or bridge qualification follows.

`SUPPORT.md:18` identifies Linux x86_64 for upstream release verification.
`state.py:222,225` uses real `fcntl.flock` for state locking; substituting an
empty Windows module would alter that behavior and cannot establish unchanged
native eligibility. The original 421 application files, eight v3 harness files
and 19 v3 receipts match their retained hashes. The failure remains intact.

Read-only platform probes are retained under
[platform-diagnosis-v1](../../../../runs/agentops-native-eligibility/platform-diagnosis-v1/capabilities.json).
WSL enumeration returned `Wsl/EnumerateDistros/Service/E_ACCESSDENIED`; this does
not establish that no Linux distribution is installed. Docker client 29.6.2
reported no server and an unavailable `dockerDesktopLinuxEngine` pipe. No WSL
distribution, Docker engine, container or OS installation was started.

The [Linux v4 protocol](protocol.md), separate runner and runtime inspector are
now implemented. They use the original source/test/observer/effect checker, the
upstream-checksummed Linux uv tool, a separate CPython 3.13.1 environment and
locked dependencies. Windows and unsupported platforms fail before reservation;
native fcntl, setup receipts, source/runtime hashes, mode-0700 capability and
three distinct passed pytest phases are required. Existing attempts are never
overwritten. Setup captures process output and retains failures without retry.

[Software validation](../../../../runs/agentops-native-eligibility/software-validation-linux-v4/result.json)
passes 11 Linux-runner checks, three effect-checker tests and seven HTTP checker
tests: **21 tests** total. These are authored harness/evidence tests run on
Windows, including platform rejection, pinned-source lookup, archive validation,
no-overwrite behavior, setup-evidence mutation and phase-report rejection.
They do not test a running Linux installer, service or application. Linux setup
and native v4 have not run; actual platform and dependency behavior remain open.

The next action, if WSL Ubuntu with Python >=3.11 is available in the user's
normal terminal, is `wsl --exec python3 scripts/run_agentops_linux_v4.py` from
this workspace. The same script runs directly with `python3` from a Linux
workspace. It installs dependencies and then attempts the original offline test
once. Inspect all receipts before continuing. HTTP v1 remains bound to failed
Windows v3; a passing Linux native result needs a new Linux HTTP plan.

Three prior context records are snapshotted under `continuation-v9` before the
handoff/status update. Earlier evidence, manuscripts, bibliography and claim
ledgers remain unchanged. This resolves the next execution design, not native
eligibility, a second domain or C1 novelty. CP2 remains open, CP7 pending and
verified deliverable credit 5%. No live model calls or research-gate credit.
