# Source-bound AgentOps evaluator v3

30 October 2026. The frozen v2 command could count a partial tool call or reply
as supported in a stronger observation lane. The new
[v3 command](../../scripts/assess_upstream_agentops_case_v3.py) integrates the
[corrected reply v2 and assessment v3 APIs](agentops-partial-observation-correction-v2.md)
while preserving the original configured trajectory metric, sampled state and
memory checks. This is benchmark implementation, not a paper draft.

## Command behavior

The command requires one complete retained v2 source-case instance. It preserves
the existing closed-journal, bootstrap, native-context, exact source/user-text,
state-boundary and type-aware receipt comparisons. It reads and hashes its
source closure before executing the exact pre-read helper bytes in dependency
order. The earlier CLI v2 and its helpers remain unchanged; the corrected reply
and assessment helpers have additional fixed hash bindings.

Selected partial calls/replies and their dependent support stay unknown.
Optional answer/schema extraction is conservatively withheld when any projected
tool call/reply is partial, because the frozen answer reader still delegates to
the earlier reply helper. Complete extraction retains its observed answers and
pending semantic judgments. The original calls-only metric remains separate.

Outputs are exclusive and cannot overlap the instance, references or sources.
After assessment, source/input bytes and full instance membership/hashes must
still match. Final publication preserves v1's pending-file flush/close and owned
empty final reservation protocol. Any failure remains noneligible; no result is
promoted to an aggregate task pass or native qualification.

The optional `--create-grade-parent` flag creates only this checkout's named
`runs/upstream-agentops-grades` directory if absent. It checks overlap before
creation and regular paths afterward. Existing files are preserved. Other
parent directories are never created by the flag.

## Prepared invocation after a complete original instance exists

Original source-case executions remain zero at this update. The command below
is a prepared example and has not graded an original instance. The actual
runtime identity must come from the completed retained instance, not from the
source evaluator's labels.

```powershell
$completedCaseRoot = Resolve-Path 'runs/upstream-agentops-native/inventory-status-v3'
$completedInstance = Join-Path $completedCaseRoot 'instances/0001'
$completedCase = Get-Content (Join-Path $completedInstance 'result.json') -Raw | ConvertFrom-Json
if ($completedCase.status -ne 'recorded_without_benchmark_grade') { throw 'A complete retained original source case is required' }
C:\Python313\python.exe -I -S -B scripts/assess_upstream_agentops_case_v3.py --instance $completedInstance --application runs/upstream-agentops-cases/v1/application/cases.json --expectations runs/upstream-agentops-cases/v1/evaluator/expectations.json --eval-set-id agentops_agent_core --eval-id inventory-status --native-user-id $completedCase.observed_runtime_identity.user_id --native-session-id $completedCase.observed_runtime_identity.session_id --output runs/upstream-agentops-grades/inventory-status-v3 --create-grade-parent
```

Recheck the native and grade output names before any allocation. Consumed native
v1/v2 allocations remain preserved. Fresh physical/commit gates and verified
provider usage constraints are separate prerequisites for model-bearing runs.
The evaluator itself imports no SDK, application or credential and sends no
runtime/model requests.

## Constructed validation

The [new test file](../../tests/test_assess_upstream_agentops_case_v3.py) declares
ten focused methods. Its frozen boundary fixture supplies builders only; the
old test suite is not executed. Journals set partial flags before initial
capture. Tests invoke the actual isolated v3 command for complete/partial
observations, original metric preservation, optional extraction abstention,
copied-helper tamper refusal and bootstrap type mismatch. Separate tests retain
post-assessment identity and final-publication failures, and bound parent
creation.

The [once-only driver](../../scripts/capture_agentops_cli_v3_validation_v1.py)
captures its complete source/reference/fixture closure, exact binary streams,
per-test outcomes and constructed instance/CLI files. It runs only the ten new
methods in `-I -S -B` Python, denies network in the test parent and permits only
the hash-bound read-only v3 CLI subprocess. That parent's module inventory alone
does not prove every child environment; the reviewed child source closure is
also required. These remain synthetic software checks, not native task grades.

The first [retained capture](../../runs/agentops-grading-software/evaluator-cli-v3-1/result.json)
failed: ten methods ran, with nine fixture errors and one passing method. The
blanket socket guard rejected Windows asyncio's internal socket pair before
the constructed journal existed. All 62 original and captured inputs stayed
unchanged. The failed binary streams and checkout are preserved.

The fixture now drives its finite, nonsuspending constructed coroutine once,
checks that it completes, and fails on any suspension. It does not create an
event loop or grant a socket exception. This validates a constructed journal
producer only; it establishes no asynchronous native/runtime behavior.

The [fresh successor capture](../../runs/agentops-grading-software/evaluator-cli-v3-2/result.json)
also failed: ten methods ran, with seven errors and three passing methods.
Windows reports `executable=None` and a serialized command line to the
subprocess audit hook; its vector-only guard raised `TypeError` before the
isolated CLI launches. The in-process post-assessment mutation, final-publication
failure and named-parent checks passed. All 62 original and captured inputs
stayed unchanged, and the socket guard remained unchanged. At that capture the
executable complete/partial CLI integration was still unvalidated. Neither
failed allocation will be rerun or overwritten.

The capture driver now validates each original argument vector, interpreter,
exact `-I -S -B` flags and CLI hash before launching. It explicitly selects that
interpreter and registers the exact platform audit representation: the Windows
`list2cmdline` serialization or the original vector on other platforms. The
audit hook permits only that registered equality, rechecks the CLI bytes and
checks the same working directory/environment. Registration is cleared in
`finally`. It parses no command text and leaves the blanket socket guard intact.

The [fresh v3-3 capture](../../runs/agentops-grading-software/evaluator-cli-v3-3/result.json)
passed all ten methods with zero failures, errors, skips, expected failures or
unexpected successes. The [per-test outcomes](../../runs/agentops-grading-software/evaluator-cli-v3-3/test-outcomes.json)
and [binary test output](../../runs/agentops-grading-software/evaluator-cli-v3-3/tests.stderr.bin)
are retained with all constructed instances and CLI receipts. Declared method
membership, isolated/site-disabled/bytecode-disabled execution flags and all
62 original/captured source/reference/fixture inputs were verified unchanged.
The seven isolated CLI methods executed; the three in-process methods checked
post-assessment mutation, final-publication failure and named-parent creation.
The original calls-only metric still passes the constructed partial-call/reply
inputs while the stronger response lane returns unknown. Optional answer/schema
extraction remains withheld for partial tool evidence and observed for complete
evidence. This is corrected CLI software integration over constructed inputs,
with zero original application/native execution, model requests or credential
reads, and no native case qualification or checkpoint credit.
