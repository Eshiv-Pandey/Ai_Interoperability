# Live admission integration: v4 allocation, 29 October 2026

The new startup diagnostics locate the latest incomplete attempt **inside dependency import and module initialization, before service readiness**. Native N11 again exceeded the fixed 65-second readiness allowance and was stopped with SIGTERM. B7 was skipped. There was no client launch, task-completion evidence or application-effect evidence, and there are still zero fresh candidate application runs.

Unlike the preceding attempt, this allocation retained **16 completed stack samples**, spanning 5.002 to 82.581 seconds after observer installation. The observations locate the phase; they do not establish a specific SDK defect, deadlock or causal resource diagnosis. The earlier post-asyncio exit stall was not reached or reproduced.

## Executed software and retained evidence

The [independent audit](../../runs/agentops-admission-execution/v4/independent-review/result.json) returned `verified_recorded_outcome` with no discrepancies. It reconciled 850 exported workspace files totaling 11,417,982 bytes, all 726 staged/prepared inputs, the source archive, source identities, exact phase commands, return codes, stream hashes and unchanged export inventories. The export contains 853 files including its manifest, result and captured exporter source. These checks establish evidence integrity, not application success.

The frozen Linux software phase passed **188 Python tests, with zero skips, plus 26 Node tests**. These overlap earlier suites and must not be added to them as disjoint tests.

| Python suite | Passed |
| --- | ---: |
| `test_agentops_admitted_client_v1` | 17 |
| `test_agentops_admission_live_plan_v3` | 13 |
| `test_agentops_admission_chain_v3` | 7 |
| `test_export_agentops_admission_v3` | 21 |
| `test_pending_admission` | 25 |
| `test_refinement` | 32 |
| `test_agentops_owned_child_v1` | 8 |
| `test_agentops_interpreter_exit_diagnostics_v1` | 12 |
| `test_check_agentops_interpreter_exit_v2` | 19 |
| `test_agentops_startup_diagnostics_v1` | 11 |
| `test_check_agentops_startup_v1` | 13 |
| `test_refinement_scaling_generator_v1` | 10 |

All software, preparation, preflight and after-inspection phases passed. The launch phase recorded the failed native outcome and skip. Parent status `recorded` and successful phase return codes deliberately do not imply `strict_success` for an application.

## Actual startup and cleanup

The isolated workspace was `/var/tmp/agentops-admission-live-v1-7d775396bb624173`. The unchanged original application source ran through wrapper v4 with two explicitly pinned five-second diagnostic intervals. Service PID 3101 never produced `service-ready.json` or `service-result.json`.

The startup journal contains 34 events: installation, monitor start, and 16 paired capture-start/capture-completion events. All captures completed without diagnostic errors. Readiness and monitor-stop events are absent because the process was terminated before readiness. The startup checker classifies the evidence as valid but incomplete. The asyncio observer recorded only entry, and the interpreter-exit check remains invalid/incomplete because the service result is absent.

The latest sample remains in Python import loading called from `google/adk/skills/_utils.py`. Earlier samples show different initialization locations, including Rich/HTTPX, Google GenAI, Pydantic, Thinc/spaCy, NumPy, regex and cryptography. The [complete sample summary](../../runs/agentops-admission-execution/v4/startup-analysis-v1.json) preserves all 16 observations. Some deep stacks hit faulthandler's 100-frame limit; the summary identifies the same thread using entrypoint-bearing samples and explicitly marks where the entrypoint frame is truncated.

After the readiness failure and existing graceful wait, the service required SIGTERM and exited **-15**. The actual owned child was reaped before group inspection; the group was empty, with no cleanup errors. This is coherent cleanup of a failed startup, not a normal accepted service exit. The original-task/effect chain and admitted certificate-to-wire check remain unexecuted because B7 was skipped.

## Resources and interpretation

The initial no-op WSL probe failed with insufficient system resources. A later, separately retained no-op probe succeeded after measured memory availability improved, allowing this new allocation to run. The original `.wslconfig` remained byte-identical throughout; no host setting was changed in this attempt.

The parent recorded severe Windows memory pressure. A read-only process observation during export also showed an automatically started Kubernetes server and Docker services, and the exporter waiting in `p9_client_rpc` while accessing the Windows-mounted output. That observation explains the export's immediate wait location; it does not prove the cause of the earlier readiness failure. No unrelated editor, Kubernetes or Docker service was stopped. The user was asked about temporarily stopping Kubernetes because it may support other workloads; no decision has been received.

## Evidence index and next step

- [Outer invocation](../../runs/agentops-admission-execution/v4-invocation/result.json) and [stage plan](../../runs/agentops-admission-execution/v4/stage-plan.json).
- [Prepared plan](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-admission-live-v1/preparation/plan.json) and [software receipts](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-admission-live-v1/phase-software/result.json).
- [Attempt result](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-admission-live-v1/attempt/result.json), [N11 result](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-http-control/admission-live-v1-N11/result.json), and [B7 skip](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-admission-live-v1/attempt/B7.skipped.json).
- [Raw startup stacks](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-http-control/admission-live-v1-N11/service/startup-diagnostics/startup-stacks.txt), [startup check](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-http-control/admission-live-v1-N11/startup-check.json), and [after-inspection](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-admission-live-v1/phase-after/result.json).
- [Export result](../../runs/agentops-admission-execution/v4/export/result.json); manifest SHA256 `b4329b4c681bd93a2de37f0301c7150df2ce0b6c9ce4f5c67c38901cf117546e`.
- [Independent audit](../../runs/agentops-admission-execution/v4/independent-review/result.json), SHA256 `681939a9520c6f63b4f7f95baac653600842aaba26a64768e9cd837a47774bfa`.

Do not rerun the consumed v4 stage, phase chain, application allocation or audit. A further attempt needs a new allocation and an explicit prospective resource plan, keeping the existing readiness and N11-before-B7 requirements. The prior [v3 allocation](pending-admission-live-results-v2.md), older exit-stall evidence and all adverse outcomes remain preserved. The admission algorithm/benchmark software demonstration remains available; no scientific novelty, second-domain qualification, 70% completion or extension is established by this result.
