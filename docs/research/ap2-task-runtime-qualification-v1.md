# Executed AP2 source-boundary qualification v1

On 10 November 2026, `runs/ap2-task-qualification/v1-20261110-2/result.json`
completed six AP2 source-boundary cases in two fresh fixed-actor passes.
**Both passes scored 6/6 against a separate private evaluator.** The evaluator
also rejected all six forged-output controls and a missing-case attempt.

| Candidate | Actual original operation | Observed boundary |
| --- | --- | --- |
| ap2-ho-019 | merchant `create_checkout` | SDK failed event for absent requested cart; no checkout artifact |
| ap2-ho-020 | merchant `initiate_payment` | SDK failed event for absent PaymentMandate |
| ap2-ho-021 | merchant `initiate_payment` | SDK failed event for missing risk_data before peer construction |
| ap2-ho-022 | merchant `dpc_finish` | SDK failed event for absent checkout_mandate |
| ap2-ho-023 | original `message_utils` | First null preserved; all-occurrence lookup separately returns both values |
| ap2-ho-024 | original processor error helpers | Ordered nonempty TextParts preserved in actual ValueError |

These are 12 case executions, not 12 completed purchases or a count of every
nested Python function call. The retained field
`original_imported_invocations_total` names this case-execution count.
The actor fully imports the original merchant and processor tool modules and
common message helpers from the hash-pinned source/runtime. It changes no
original function body and uses actual SDK updater/events/models. No module
extraction is used. It drives only already-immediate original SDK coroutines;
external waits are refused. This is a declared development intervention, not
an original server/executor/shopper integration run.

The missing-risk case uses the exact retained original development signer
output from the earlier AP2 capture. That output may now be expired; this run
claims neither signature freshness nor payment completion. Its original guard
does not verify the PaymentMandate before refusing missing risk_data. No JWT
string, live credential or receipt was invented to obtain this result.

The public actor input contains public task records, typed operational inputs,
source hashes and runtime locations. It contains no evaluator expectations.
Evaluator JSON and evaluator/coordinator code remain outside the actor input.
Each isolated actor's attempted read of the evaluator file was denied and
recorded. Network and descendant-process audit guards remained active; no such
operation was attempted. Provider credentials were excluded from the worker
environment. Both outside-workspace private profiles were removed. These are
source-bound process/audit boundaries, not a hostile-code OS sandbox.

The first allocation, `v1-20261110-1`, remains failed. Windows asyncio's loop
constructor attempted its loopback self-pipe before any case executed and the
offline guard refused it. The successor uses the immediate-coroutine path;
no network restriction was relaxed and no favorable task outcome was retried.
The failed allocation and its raw streams/process/cleanup receipt remain
retained.

The complete bank structurally validates at **68 records**: 34 AgentOps and
34 AP2, each with 6/4/24 prospective split counts. The source/citation and
public/private structure receipt is
`runs/task-bank-review/complete-68-v1.json`. The six AP2 boundary records are
explicitly mixed-scope developmental candidates; the count does not establish
68 comparable full workflows, human-approved gold or untouched independent
held-out tasks.

Executable files are
[run_ap2_task_qualification_v1.py](../../scripts/run_ap2_task_qualification_v1.py),
[ap2_task_qualification_actor_v1.py](../../scripts/ap2_task_qualification_actor_v1.py)
and the private
[ap2_task_qualification_evaluator_v1.py](../../scripts/ap2_task_qualification_evaluator_v1.py).
The private gold file is `benchmark/tasks-v1/ap2/qualification-private-v1.json`.
Use a new exclusive allocation when reproducing:

```text
python -I -S -B scripts/run_ap2_task_qualification_v1.py --output runs/ap2-task-qualification/NEW-ALLOCATION
```

All public inputs, plans, raw actor/reference streams, original result/event
objects, process/cleanup receipts, private-evaluator outcomes, forged-output
checks and final file hashes are retained in the successful allocation. Every
case stays in the denominator. Human review, independent holdout sealing and
complete original shopper/runtime qualification remain unclaimed.
