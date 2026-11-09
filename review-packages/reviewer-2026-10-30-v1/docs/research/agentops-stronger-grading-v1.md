# Stronger source-case benchmark checks

Date: 30 October 2026. The supervisor review requires the admission algorithm,
implemented benchmark and runnable demonstration. No paper is required this
week. These checks extend the evaluator without changing the admission defaults,
the retained comparison outcomes or the original benchmark metric.

## Implemented observation checks

[Reply and dependency assessment](../../src/interoperability/agentops_reply_dependencies_v1.py)
covers all 21 original source cases and 22 turns. It keeps duplicate calls and
response phases, distinguishes successful replies, missing resources and
approval pauses, and requires uniquely attributed successful replies in an
earlier original yield for stronger value-consistency checks. Same-event array
order can still pass the original required-trajectory metric. Observed reply
and value consistency does not establish causal execution or persistence.

[Sampled state assessment](../../src/interoperability/agentops_source_case_effects_v1.py)
checks the original business schema, rows, keys and sequence at every supplied
boundary. All source cases end without approval, so business data must remain
unchanged. Only the memory-note case permits one new INC-010 note for the actual
user in turn one, preserved through recall and retained close. Existing users,
duplicates and sequence gaps remain intact. Structural insertion, intended note
text, displayed save/recall replies and sanitizer fidelity have separate results.
An absent original sanitizer fixture leaves sanitizer fidelity pending.

[The boundary collector](../../src/interoperability/agentops_case_boundary_evidence_v1.py)
reads a complete retained v2 instance. It binds source, bootstrap and client
plans; exact original user text and context; complete prepared HTTP requests;
unique matching server entities; every public task observation; and all sampled
before/after states. A successful original readiness response supplies a distinct
post-startup baseline before source requests. Polling after a terminal state or
confirmation pause is rejected. Archived store reads reject WAL/sidecars before
connecting and verify stable bytes and directories. The business reader executes
the exact hashed source bytes, without using cached bytecode.

These are consistency checks on retained observations. They establish no source
authentication, process exit, continuous mutation absence, cross-store atomicity,
full task pass or native qualification.

## Captured software validation

| Suite | Tests | Receipt | Independent audit |
| --- | ---: | --- | --- |
| Reply/dependencies | 41 | [reply-dependencies-v1](../../runs/agentops-grading-software/reply-dependencies-v1/result.json) | [Verified](../../runs/agentops-grading-software/reply-dependencies-v1-independent-review.json) |
| Source-case state effects | 24 | [source-case-effects-v1](../../runs/agentops-grading-software/source-case-effects-v1/result.json) | [Verified](../../runs/agentops-grading-software/source-case-effects-v1-independent-review.json) |
| Client/server state boundaries | 16 | [case-boundaries-v1](../../runs/agentops-grading-software/case-boundaries-v1/result.json) | [Verified](../../runs/agentops-grading-software/case-boundaries-v1-independent-review.json) |
| Answer/schema projections | 35 | [answer-schema-v1](../../runs/agentops-grading-software/answer-schema-v1/result.json) | [Verified](../../runs/agentops-grading-software/answer-schema-v1-independent-review.json), with preserved local static audit |
| Integrated v2 assessor | 13 | [case-assessment-v2](../../runs/agentops-grading-software/case-assessment-v2/result.json) | [Verified](../../runs/agentops-grading-software/case-assessment-v2-independent-review.json), with preserved local static audit |
| Integrated v2 CLI | 7 | [evaluator-cli-v2](../../runs/agentops-grading-software/evaluator-cli-v2/result.json) | [Verified](../../runs/agentops-grading-software/evaluator-cli-v2-independent-review.json), with preserved local static audit |

All six terminal captures passed with zero failures, errors or skips. They
execute frozen copies in isolated stdlib Python (`-I -S -B`) using synthetic
observations and temporary fixture stores. No original application, SDK or model
runs in these suites. Their captured sources and output membership were unchanged.
The [bounded source review](agentops-grading-source-review-v3.md) records the final
bytes and review scope. All six captures now have verified independent retained-
receipt audits. The [v6 peer audit note](agentops-grading-peer-audit-v6.md)
supersedes the earlier dated pending observation; the newest three local static
audits remain preserved. Audits verify source, driver, file/directory membership
and exact primary test identities/counts without rerunning. The frozen capture
drivers and these consumed allocations must remain unchanged.

## Answer and integrated evaluator work

The [answer/schema specification](agentops-answer-schema-assessment-design-v1.md)
preserves exact source obligations and all 21/22 mappings. Deterministic report
checks use observed JSON and attributed successful replies. Workflow outputs are
prose; no formal workflow output schema is invented. Ambiguous output selection,
semantic adequacy, paraphrase, action suitability and actual workflow handoff
correctness remain separate from deterministic checks.

[The answer/schema module](../../src/interoperability/agentops_answer_schema_v1.py)
implements conservative answer extraction, strict report JSON, declared schema
projection and direct bindings to actual successful incident replies. It preserves
unknown workflow stage identity and pending semantic/prose judgments.

[The integrated v2 assessor](../../src/interoperability/agentops_source_case_assessment_v2.py)
keeps the original metric, replies, dependencies, arguments, sampled effects and
optional answer/schema results separately named. Unique complete memory save and
recall replies can be compared to the sampled inserted row; duplicates and partial
observations cannot be selected as unique complete evidence.

[The runnable v2 evaluator](../../scripts/assess_upstream_agentops_case_v2.py)
reads one complete retained v2 instance and its passive journal. It binds the
instance/bootstrap receipts to the journal, pins source projections and design,
executes exact pre-read helper bytes and checks all input membership/hashes before
publishing a new exclusive result. Optional answer extraction and original
sanitizer observations are evaluator-only inputs. No SDK, key or model is read.
Its command interface is available now:

```powershell
C:\Python313\python.exe -I -S -B scripts/assess_upstream_agentops_case_v2.py --help
```

An actual assessment requires `--instance`, `--application`, `--expectations`,
`--eval-set-id`, `--eval-id`, `--native-user-id`, `--native-session-id` and a new
`--output`. The journal is derived from the retained instance. No complete native
source-case instance currently exists; the 7-test capture uses synthetic retained
instances and includes an isolated invocation of the actual CLI.

## Live execution and review

Original source-case native executions and grades remain zero. The latest
read-only memory observation at 11:06:13 UTC on 30 October found 575,496,192
available physical bytes (about 549 MiB) and 2,239,348,736 available commit bytes
(about 2.09 GiB). The unchanged 1 GiB physical minimum fails; the 2 GiB commit
minimum passes.
This observation is not a retained prospective resource
gate or a new allocation. No live application was launched.

The [rehearsed admission demonstration](supervisor-package-v1.md) remains the
main supervisor evidence. Its retained engineering comparison establishes no
consistent candidate advantage or scientific novelty. Live admission, a
substantive second domain, semantic/sanitizer evidence and supervisor acceptance
remain open. The user-confirmed [full research-project rubric](research-progress-target-v1.md)
records 5 percent verified progress; 70 percent and any extension remain unverified.
