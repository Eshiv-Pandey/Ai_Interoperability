# Verified Linux core timeout cleanup, version 2

The first timeout-only hosted run passed all five focused tests in 4.283 seconds
on Linux with Python 3.13.1: no failures, errors or skips. This verifies the new
owned-process-group cleanup path for actual stdlib coordinators and their delayed
child writers. It adds no full comparison matrix or application/model execution.

Run: <https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42823294717>
at commit `bee78c1214333de70e63eaa3f1e4ac2635ef3391`, attempt 1. The job ran
2026-11-10 13:18:21 to 13:18:45 UTC. No favorable retry or full-matrix rerun was
performed.

## Actual process evidence

| Case | Coordinator / child PID | Sent signals | Coordinator exit / adopted-child wait status | Cleanup before return |
| --- | --- | --- | --- | --- |
| Normal SIGTERM timeout | 2447 / 2448 | SIGTERM | -15 / 15 | Coordinator reaped; group empty |
| SIGTERM-ignoring timeout | 2444 / 2445 | SIGTERM, SIGKILL | -9 / 9 | Coordinator reaped; group empty |

Both timeout receipts capture the live coordinator and child in the newly owned
session/group before termination, stable process start ticks throughout the
snapshots, and final empty groups. The ignoring coordinator and child are still
alive in the snapshot immediately before SIGKILL. Each child is adopted and
reaped by the test coordinator, with its actual POSIX signal wait status retained.

The original subreaper state is zero and the tests verify its restoration. The
separate post-return marker checks occur 1.504537 seconds after the normal timeout
returns and 1.504978 seconds after the ignoring timeout returns, beyond the child
writer's original 1.4-second delay. Both checks report no marker, no group members
and no open ownership entries; the downloaded artifacts contain no marker files.

The normal command retains exactly `normal-output\n` on stdout,
`normal-error\n` on stderr and return code zero, with no cleanup signal. The
remaining two passing tests verify blocked command/manifest allocation for a
mocked unconfirmed ownership entry, and Windows execution rejection before
allocation under a mocked platform. These guard tests are distinguished from the
two actual Linux timeout process tests.

## Independently checked retained evidence

The independent audit hashes every one of the 19 manifest-listed files, totaling
71,342 bytes, and verifies that the manifest describes every extracted regular
file except itself. All five retained source copies, including both coordinators,
the test module, workflow and plan, match the exact Git blobs of the executed
commit. Their original and captured before/after bindings match. All three
invocation receipts separately bind unchanged v1 and v2 coordinator source.

Artifact `core-timeout-42823294717-1` has a retained 25,633-byte raw ZIP whose SHA256
matches GitHub's published digest:

```text
001b21084faabec891952e117a4f85e0141bfc9b5f5d57ba3dd1132acf81e5e3
```

All 20 ZIP file entries are byte-identical to the extracted files, including the
manifest. The audit also binds stdout/stderr to each process receipt, reconciles
raw passing test names with the result summary, and refreshes the live successful
workflow conclusion and commit binding.

Evidence:

- Extracted artifact: `runs/core-timeout-check/download-42823294717/`
- Raw ZIP: `runs/core-timeout-check/core-timeout-42823294717-1.zip`
- Independent audit: `runs/core-timeout-check/download-42823294717-independent-review.json`

## Scope

The preserved successful v1 full reproduction remains separate evidence. This
focused run qualifies v2's owned inherited-process-group timeout cleanup, normal
output preservation and guard behavior. It does not establish v2 full-matrix
reproduction, containment of descendants that deliberately detach into new
sessions, application-level admission integration, model behavior or scientific
superiority. The workflow is bounded at five minutes with seven-day hosted
artifact retention; the raw ZIP is retained locally for longer-term provenance.
