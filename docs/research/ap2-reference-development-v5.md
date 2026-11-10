# AP2 original payment-tool paired development matrix v5

This prospective extension retains 13 cases across five arms, for 65 original
application development cells. It executes the unchanged
`shopping_agent.tools.initiate_payment` and `initiate_payment_with_otp` functions,
the original merchant, payment processor and credentials-provider executors,
original message builders, AP2 HTTP extension, SDK handlers and task stores.
The prefix still uses owned public decisions, offline model fixtures and an
in-process ASGI transport. It is not the full original ADK shopper conversation,
native transport qualification, actual MCP bridge execution or human gold.

The natural source boundary is retained: the original shopper tools test for
`challenge`, while the actual SDK Task reports `input-required`. Their returned
string therefore omits the challenge DataPart. The conventional arm consumes
that actual generic return. Other arms explicitly inspect the captured public
Task; recovery arms additionally make one original SDK `get_task` query. Every
read, repair, source exception, refusal and raw continuation is retained.

The ordered public manifest is
`benchmark/ap2-application-development-v5/application.json`. Private authored
expectations live in its separate `evaluator.json`, which the actor and
orchestrator never read. The five arms are source-reference equivalent,
conventional original-tool continuation, informed public recovery, shared
admission, and public recovery plus shared admission. Source reference retains
the valid sender values instead of applying receiver faults; this upper-bound
intervention is disclosed and is not equal-information blind performance.

Cases retain natural hint loss, explicit correct and wrong demo replies, no
human reply, an actual earlier catalog Task ID, an actual nested processor ID,
another original catalog context, a missing caller mandate, an actual checkout
mandate in the payment slot, an omitted original credential association,
recipient PaymentMandate DataPart loss, a duplicate original OTP invocation,
and a real dispatch delay past a one-second finite-model interval. Wrong or
absent human replies are never repaired. Missing caller mandate raises the
unchanged original source exception before message construction. Recipient
loss is a separately retained owned transport perturbation, with original
sender and actual received bytes kept independently.

Shared admission checks the actual received request against canonical public
source observations. The finite relation has incomplete coverage; a failed
guard produces `unknown` and refusal, never whole-route non-support. A positive
certificate is checked by the unchanged generic independent checker and
checked again immediately before the original ASGI handler. Business completion
is evaluated separately from actual original merchant/processor Tasks and
matching receipts, including the exact closed-mandate receipt reference.

Each cell gets a fresh subprocess and temporary private signing state. The
bounded allocation reuses one newly installed pinned runtime. Each cell has a
180-second process bound and the whole matrix has a 1,500-second bound. Cells
left unexecuted, timed out, blocked by memory, errored or refused remain in the
65-cell denominator. The original 34 AP2 task-bank candidates, previous captures,
v4 files and full-task/human-gold qualification requirements remain unchanged.

Run the matrix and independent evaluator in separate processes:

```bash
python -I -S -B scripts/run_ap2_application_matrix_v5.py \
  --output "$RUNNER_TEMP/ap2-v5/matrix" \
  --site-packages "$RUNNER_TEMP/ap2-v5-environment/lib/python3.13/site-packages"
python -I -S -B scripts/evaluate_ap2_application_matrix_v5.py \
  --matrix "$RUNNER_TEMP/ap2-v5/matrix" \
  --output "$RUNNER_TEMP/ap2-v5/independent-evaluation" \
  --site-packages "$RUNNER_TEMP/ap2-v5-environment/lib/python3.13/site-packages"
```

The dedicated workflow also retains separate conventional and shared smoke
cells before the scored matrix. Source capture success does not label either
the smoke or matrix worker a successful purchase. No prospective document
contains a hosted runtime ID or future execution outcome.
