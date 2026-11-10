# Versioned core coordinator timeout cleanup

The executed `ci_research_core_v1.py` remains unchanged. Version 2 reuses its
comparison, tests, capture and deterministic reconciliation methods, replacing
command invocation with an explicitly owned Linux POSIX session/process group.
Windows execution is rejected before allocation or subprocess launch.

Each command uses direct `Popen(start_new_session=True)`. A temporary Linux
child-subreaper setting makes orphaned worker children reapable by this process.
On timeout, the entire owned group receives SIGTERM and, if needed, SIGKILL.
The direct coordinator and adopted children are reaped before invocation returns.
The prior subreaper state is restored after confirmed cleanup. Normal successful
commands preserve their actual stdout, stderr and return code; an unexpected
surviving child after normal coordinator exit is a retained failure.

Cleanup records the initial/final group membership, signals and adopted-child
wait statuses. An unconfirmed group blocks further commands and retained-manifest
sealing. Every command records the preserved v1 and invoked v2 source hashes
before and after invocation. Timeout tests also retain unchanged copies of both
coordinators, the test module, workflow and this plan. Cleanup exceptions retain
a failure receipt and leave ownership unconfirmed, blocking sealing. The CLI and
test import share the same ownership registry even under isolated Python.
The helpers are scoped to the original coordinator/worker group; the
preserved workers inherit that group and do not create detached sessions. The
temporary v1 module configuration is for a single CLI coordinator, not concurrent
caller threads.

The timeout-only workflow runs five focused tests. Two create an actual stdlib
Python coordinator with a child that would write a delayed marker. Both coordinator
and child must appear in the captured group; timeout must reap both; waiting past
the original marker deadline must leave no marker. One child/group ignores
SIGTERM and must require SIGKILL. Other tests verify unchanged normal output,
blocked sealing while ownership is uncertain, and refusal of Windows execution.
Each delayed-marker test retains a separate post-wait marker and group check.
No application, SDK, model or full comparison matrix is launched.

The standard Ubuntu workflow is bounded at five minutes and retains raw test
streams, process receipts, source hashes and a manifest for seven days. Root
owns source review, push and dispatch. Before a successful hosted run is inspected,
the Linux timeout tests remain unverified locally because this workspace is Windows.
Local AST checks, the single portable platform-guard test and the read-only
v2 input check passed on 2026-11-10. The preserved v1 source has no working-tree diff.

Future full reproduction command:

```text
python -I -S -B scripts/ci_research_core_v2.py --execute --output runs/ci-research-core/<new-allocation>
```

Timeout-only validation command:

```text
python -I -S -B scripts/ci_research_core_v2.py --test-timeouts --output runs/core-timeout-check/<new-allocation>
```
