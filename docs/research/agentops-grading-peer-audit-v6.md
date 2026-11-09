# Independent grader capture audit v6

30 October 2026. Peer review resumed after the earlier availability failure.
The three newest terminal captures now have **verified independent AI receipt
audits**, in addition to their preserved local static audits. No tests were
rerun and no original application, SDK, database or model was executed.

| Capture | Tests | Independent audit | Audit receipt SHA256 |
| --- | ---: | --- | --- |
| Answer/schema | 35 | [Verified](../../runs/agentops-grading-software/answer-schema-v1-independent-review.json) | `e48de1789d0b5297dd3eb67cd68c69396224df8854cd7860c1a3ca7acfaab599` |
| Integrated v2 assessor | 13 | [Verified](../../runs/agentops-grading-software/case-assessment-v2-independent-review.json) | `88733ea91e33ae459f75b5eef27e29e24ce221cae51c08b620466c4929df39d6` |
| Integrated v2 CLI | 7 | [Verified](../../runs/agentops-grading-software/evaluator-cli-v2-independent-review.json) | `a292340843cde47d9dfcd58b2919d90f2109f895f13a7a306b60d7a2cf738bef` |

The new [independent reviewer](../../scripts/review_agentops_grading_captures_independent_v6.py)
is frozen at SHA256
`1d6c4ba4cd4dd6c17adc6bd335b47ed3385c2b3dbe4ab0cd28114b68c706dc2d`.
It reviewed the literal source/primary-test membership, exact logged primary
test identities, fixture-suite exclusion, typed descriptors/counts, manifests,
file/directory membership, captured/current source agreement and unchanged audit
inputs. The capture driver, static reviewer and static receipts are unchanged.

This note supersedes the *pending peer receipt audit* observation in the earlier
[source review v3](agentops-grading-source-review-v3.md), without editing that
dated hash-bound record. All six stronger-check captures now have independent
receipt audits. Native source-case execution, semantic/sanitizer evidence,
source-authenticated workflow mapping, method contribution, second-domain
qualification and actual human/supervisor acceptance remain separate open work.
No new research checkpoint credit or native qualification is granted.
