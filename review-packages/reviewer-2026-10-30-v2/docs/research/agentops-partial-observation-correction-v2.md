# Partial tool observations: conservative stronger assessment

30 October 2026. This correction changes stronger evaluator software only.
No original source case, service, SDK, model or native grading was executed.
The original metric and every frozen source/capture remain unchanged.

The original installed `google/adk/models/llm_response.py` defines `partial`
as an incomplete streaming fragment. It says fragment content may be truncated,
repeated or contain unfinished function-call arguments, and cannot justify tool
execution, event persistence or turn completion. Its reviewed SHA256 is
`00c4ebffbbd3db3c6507a46cfd2507c1dbb8d929e2ef81b69998a650ced4e348`.
This is inspected source, not proof that a native instance loaded these bytes.

The frozen reply v1 projector retains the partial flag, but a sole partial
call/reply could receive `supported`, and a sole partial error could receive
`inconsistent`. Its dependency and diagnostic helpers could also use incomplete
fragments. The original calls-only trajectory metric can legitimately still
score its required call as present; that metric is distinct from complete replies.

The new [reply assessor](../../src/interoperability/agentops_reply_dependencies_v2.py)
derives from frozen v1 SHA256
`ae70b1a5dd901d3e1b298e30258fd7b12f51cc3f461a3be5880da9c26eb102e3`.
It keeps required reply assessment unknown when the selected call or an
attributed reply is partial. This guard precedes confirmation contradictions
and expected-class comparisons. All calls, replies, classifications and phases
remain diagnostic observations. Complete supporting replies and consumers are
required for dependencies; partial diagnostic calls and unfiltered replies
cannot justify stronger argument support. Duplicates are not collapsed and the
earliest required-call selection is unchanged.

The new [v3 evaluator API](../../src/interoperability/agentops_source_case_assessment_v3.py)
independently computes corrected replies, then delegates original metric,
sampled effects and memory checking to frozen v2. It rechecks case, journal and
native-turn agreement before replacing response/dependency/argument lanes.
It preserves supplied observations and every false qualification flag.

Optional answer extraction is conservatively withheld whenever any projected
tool call/reply is partial. The frozen answer reader uses the old reply
assessor for direct report fields, so those fields cannot always be preserved
as unaffected. The v3 API instead retains pending answer/schema and an explicit
withholding reason. This trigger applies across all tools in the supplied
journal, not just a selected report producer. Complete optional extraction
retains the frozen reader's ordinary observations and pending semantics.

## Validation and provenance

The [reply regression file](../../tests/test_agentops_reply_dependencies_v2.py)
passed **11 tests** once with `C:\Python313\python.exe -I -S -B`, and the
[integration regression file](../../tests/test_agentops_source_case_assessment_v3.py)
passed **five tests** on its final source with the same interpreter flags. Both had zero
failures, errors or skips. They reuse frozen synthetic fixture builders;
earlier test suites and consumed captures were not rerun. The existing 21-case,
22-turn complete fixture parity check ran once in the new reply suite.

These are direct terminal test results, not a retained source-copy capture or
independently reviewed replay. Current SHA256 bindings:

| New source | SHA256 |
| --- | --- |
| `agentops_reply_dependencies_v2.py` | `0475d55ba2a4aa84d0dacd77fefaa357440f35c27020d43d747879e3df39d2b3` |
| `test_agentops_reply_dependencies_v2.py` | `fe1c4e13ab2929800c26c9c6cd643a106b1e16fb7349f716b2933fe4a07fcda6` |
| `agentops_source_case_assessment_v3.py` | `3b6b1ec0a7c274590562ddd6a66bd06bf9ad5b79f78baecdaa58f1f07d175aa3` |
| `test_agentops_source_case_assessment_v3.py` | `1114129fadb19d2a5ef688c44a42b75fb4175d8a48659aea197347d687b4a16a` |

## Native and CLI boundary

The frozen `assess_upstream_agentops_case_v2.py` does **not** use this successor
API. Its stronger partial-observation lanes are not corrected by adding these
new files. A source-bound CLI successor remains required before claiming the
correction is integrated into native retained-instance grading. That successor
must retain its closed-journal, bootstrap, source, state and publication checks;
changing an import in the frozen CLI would break its provenance contract.

`inventory-status-v2` is consumed after its timed physical-memory refusal,
with zero staging, native launches, model calls or grades. The smallest next
original instance remains the existing v2 native runner selecting
`agentops_agent_core/inventory-status`, one sample and the disclosed
`gemini-3.1-flash-lite-preview` model, in a fresh unused allocation. The current
next name is `runs/upstream-agentops-native/inventory-status-v3`, unused at this
review. The unchanged timed resource gates must pass inside that runner.
Verified provider capacity, per-attempt usage constraints and a fresh prospective
plan are also required before any model-bearing successor execution.

For inventory status, the original tool returns the current database service
and unresolved incidents. Reply shape/target consistency does not establish
that the answer reports inventory's actual status. Dependency and extra-argument
lanes are not applicable for this single lookup. The normal evaluator command
leaves answer/schema pending without extraction bindings; core semantic and
quotation judgments stay pending even with extraction. The evaluator output
parent `runs/upstream-agentops-grades` was absent at this review and must exist
before a fresh CLI assessment can allocate an output.
