# Sealed observer correction and Linux resume v8

Prospective version, 26 October 2026. The v7 setup succeeded; native-v6 pytest
passed, but its independent effect checker failed on `offline observer
boundaries`. The profile records one `socket.bind` without address or stack.
The separate import-only diagnostic reproduced the blocked urllib3 IPv6
initialization probe. This supports the correction but cannot retroactively
identify the event in the original run. Original failures remain failures.

The reviewed installed source is urllib3 2.8.0 `util/connection.py`, 4,444 bytes,
SHA256 `2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74`.
Policy v1 checks these bytes and compares the live Python code objects for both
`_has_ipv6` and its immediate module caller. Only its IPv6 TCP `::1:0` bind at
initialization is classified separately, and it still raises the original
RuntimeError. The pinned source catches that exception and reports no IPv6.
Calls after import and changed code, address, family, operation or socket type
are not excused. No application/SDK function is replaced. New data-only checks
validate the metadata in addition to all original native/HTTP effect conditions.

The new coordinator reuses the recorded `/var/tmp/agentops-research-v7-*`
workspace. It checks the prior failure, all prior exported bytes in both parent
and live workspace, all original parent inputs and the new launch seal. It adds
newly named files only; it never reinstalls or overwrites a prior attempt.
Missing/changed workspace or inputs stop execution for inspection.

From normal PowerShell in the project, execute once:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v8.ps1
```

Parent output: `runs/agentops-native-eligibility/linux-socket-resume-v8`.
Stages: native-v7 preparation, native-v7 execution, HTTP-v5 preparation,
HTTP-v5 execution. Native preparation/execution independently compare the
current installed runtime with its successful setup. HTTP requires the new
native result and rechecks its hashes and effects. Stop on any stage failure;
always retain partial exports and result. Existing attempt paths forbid repeats.
No unchanged attempt may be retried solely because a poll timed out.

The managed Codex shell currently returns `Wsl/Service/E_ACCESSDENIED` on Ubuntu
access. This preparation does not claim Linux execution. After the run, verify
the export manifest, command/runtime provenance and native/HTTP semantics before
claiming eligibility. Human validity, two unchanged bridge routes, a substantive
candidate advantage and the full benchmark/paper gates remain open. Deliverable
credit stays 5%; no model inference or scientific gate credit is added.
