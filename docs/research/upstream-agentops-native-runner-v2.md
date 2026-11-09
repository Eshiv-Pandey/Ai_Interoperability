# Native AgentOps source-case runner v2

Updated 30 October 2026. The [versioned runner](../../src/interoperability/upstream_agentops_native_runner_v2.py)
adds complete original-yield journal binding and read-only memory evidence to
the frozen v1 execution path. The 31 October supervisor deliverables remain the
implemented admission algorithm, comparison benchmark and runnable software
demonstration. No paper is required this week.

V2 preserves v1's original case inputs, sample counts, source/dependency checks,
model disclosure, resource gates, connected-socket ownership, original factory
objects, confirmation behavior and owned shutdown. See the [v1 guide](upstream-agentops-native-runner-v1.md)
for those contracts and its consumed refusal evidence. V1 source files and
allocations remain unchanged.

## Added evidence path

[Bootstrap v2](../../scripts/serve_upstream_agentops_cases_v2.py) wraps only
`app.state.runtime.runner.run_async` after the original factory. It verifies
the original bound instance/class/method and source/helper origins. The
[journal](../../scripts/agentops_runtime_stream_v1.py) serializes each original
event before returning the identical event to the converter, retaining partial
events and actual invocation identities in explicit recorder order.

After clean owned process shutdown, the outer runner validates complete root
and per-call receipts using [the closed-journal reader](../../src/interoperability/agentops_runtime_stream_evidence_v1.py).
It binds the returned bootstrap summary to persisted receipt bytes, source
identity, expected native user/context and exact source text for every attempted
turn. A partial/missing journal cannot become complete evidence.

The ASGI observer adds separate before/after memory snapshots. Memory errors
remain separate from original application outcomes, but prevent a claim of
complete memory evidence. The outer runner also exports the retained closed
memory store, including explicit lazy absence.

The frozen v1 public exporter expects five files per exchange. V2 retains all
seven original files and creates an exclusive byte-identical five-file
projection, binding every original/copy digest and exact directory membership
before and after export. Memory files remain in the original archive; the v1
public export does not claim to contain them.

The runner returns `recorded_without_benchmark_grade` only after complete
transport, clean shutdown, journal, state retention, raw/public/binding/memory
exports and observed runtime identity checks. It assigns no benchmark grade.
The separate [source-case assessor](../../src/interoperability/agentops_source_case_assessment_v1.py)
implements only the configured original trajectory metric; successful replies,
dependencies, effects, schemas and answer grounding remain separate.

## Next native diagnostic

**Latest attempt, 30 October:** `inventory-status-v2` is now consumed. The
[retained timed gate](../../runs/upstream-agentops-native/inventory-status-v2/prestage-gate.json)
failed before staging at 15:58:38 and 15:58:48 UTC: available physical memory
was 82,698,240 and 134,684,672 bytes, below the fixed 1 GiB minimum. Both
commit samples passed. A preceding single diagnostic above the minimum did
not persist. The [terminal result](../../runs/upstream-agentops-native/inventory-status-v2/result.json)
records zero native launches, client attempts and grades. Its
[independent review](../../runs/upstream-agentops-native/inventory-status-v2-independent-review.json)
passed 26 retained-receipt checks with no rerun. Source/dependency baselines
were not reached; the false preservation fields are unassessed, not evidence
of mutation. Do not execute either consumed v1 or v2 allocation again.

The command below is retained as the historical v2 invocation. Any successor
needs sustained headroom and a fresh plan, including verified model-usage
constraints before model-bearing execution. No successor native allocation
has been executed.

The key is privately configured. Use the existing child-only injection helper;
no key belongs in chat or command arguments. Selecting the previously tested
`gemini-3.1-flash-lite-preview` is a disclosed supported model setting that
differs from the original `gemini-3.5-flash` default.

The v2 command executed on 30 October was:

```powershell
C:\Python313\python.exe -I -S -B scripts/run_upstream_agentops_cases_v2.py --model gemini-3.1-flash-lite-preview --case agentops_agent_core/inventory-status --samples 1 --output runs/upstream-agentops-native/inventory-status-v2
```

For future allocations, recheck that the output is unused. The fixed gates require
1 GiB available physical memory and 2 GiB commit, with two passing timed
observations and an immediate bootstrap check. `inventory-status-v1` and
`inventory-status-v2` are consumed and must not be rerun. Single diagnostic
observations do not replace bound timed gate receipts.
No original source case has run or received a grade.

## Validation

The [grading implementation guide](upstream-agentops-grading-implementation-v1.md)
links terminal captured suites and independent audits. Bootstrap v2 and the
journal validator passed 65 and 26 captured tests. The outer v2 runner passed
[45 captured mocked tests](../../runs/agentops-grading-software/runner-v2/result.json),
with [verified independent audit](../../runs/agentops-grading-software/runner-v2-independent-review.json)
and closed source review. The all-case assessor and evaluator CLI passed 21 and
8 captured tests with independent audits. These checks launch no original
application or model.

After a source instance records complete evidence, evaluate its configured
metric separately using actual retained native identities. This prepared
command has not been executed against an original source instance:

```powershell
$nativeCaseRoot = Resolve-Path 'runs/upstream-agentops-native/inventory-status-v2'
$nativeCaseResult = Get-Content (Join-Path $nativeCaseRoot 'instances/0001/result.json') -Raw | ConvertFrom-Json
if ($nativeCaseResult.status -ne 'recorded_without_benchmark_grade') { throw 'Complete original source-case evidence is required' }
C:\Python313\python.exe -I -S -B scripts/assess_upstream_agentops_case_v1.py --journal (Join-Path $nativeCaseRoot 'instances/0001/service/runtime-stream') --application runs/upstream-agentops-cases/v1/application/cases.json --expectations runs/upstream-agentops-cases/v1/evaluator/expectations.json --eval-set-id agentops_agent_core --eval-id inventory-status --native-user-id $nativeCaseResult.observed_runtime_identity.user_id --native-session-id $nativeCaseResult.observed_runtime_identity.session_id --output runs/upstream-agentops-grades/inventory-status-v1
```

The evaluator output must also be unused. It retains source/input/journal
bindings and original-metric results, with every stronger/native qualification
flag remaining separate. It does not replace response, effect or grounding
checks with reference-answer equality.

The [v2 integrated evaluator](agentops-stronger-grading-v1.md) now implements the
original metric plus separate reply/dependency, sampled-state and optional
answer/schema lanes. Its 13-test API and 7-test CLI captures passed; local static
and [independent peer receipt audits](agentops-grading-peer-audit-v6.md) verified.
For the next complete
retained source instance, the successor command replaces `--journal` with
`--instance` and derives the journal internally:

```powershell
C:\Python313\python.exe -I -S -B scripts/assess_upstream_agentops_case_v2.py --instance (Join-Path $nativeCaseRoot 'instances/0001') --application runs/upstream-agentops-cases/v1/application/cases.json --expectations runs/upstream-agentops-cases/v1/evaluator/expectations.json --eval-set-id agentops_agent_core --eval-id inventory-status --native-user-id $nativeCaseResult.observed_runtime_identity.user_id --native-session-id $nativeCaseResult.observed_runtime_identity.session_id --output runs/upstream-agentops-grades/inventory-status-v2
```

No original source-case instance exists yet. This command is a prepared successor,
not an executed native assessment. Preserve both unused grade allocations until
their inputs qualify, and keep semantic/sanitizer unknowns explicit.

Preserve every consumed allocation. Complete observed source-case assessment,
live admission, substantive second domain, method contribution and
human/supervisor acceptance remain open. Neither 70 percent completion nor an
extension has been established.
