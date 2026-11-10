# Disposition of the user-supplied pilot review

Received 10 November 2026: [shared-lifting-pilot-final-review.md](../../src/shared-lifting-pilot-final-review.md),
dated 9 November and referring to repository commit `d543135`.
SHA256 `bf16de1a87e7573d7e11959d34bc638b6b2372039f6ab9a58bcc51f2df5b87ac`.
The submitted file is preserved unchanged.

Its stated scope is numerical reconciliation and document consistency. It did
not run solvers, checkers, replay or tests, validate the 23/3/5 test counts, or
assess the full 66-case v2 result. No reviewer name, supervisor role, independent
task/gold review or novelty/feasibility approval is inferred from its receipt.

| Review item | Action and evidence | Disposition |
| --- | --- | --- |
| Name the fair comparator | [Comparison specification](shared-lifting-comparison-v3.md) names `direct_pruned` as the mandatory same-input memoized goal-cone comparator; `baseline` is a relation-aware historical control/reference. | Corrected |
| Abstraction-only BFS | Specification and [pilot results](shared-lifting-pilot-results-v1.md) state that the separate weaker control was not run among the four arms. | Omission disclosed; no invented run |
| Demonstration coverage | Pilot results map seven requirements to retained inputs/outcomes and identify missing typed/raw API, task/context identity and native generated-value evidence. | Map added; partial requirements remain open |
| Sixth schema field | [Prototype specification](admission-refinement-v1.md) includes `schema_version` in the top-level table. | Corrected |
| Four bundles | Pilot prose says four budget bundles. | Corrected |
| Speed caveat placement | Timing table has the single-observation, fixed-order, constrained-host caveat beside it. | Corrected |
| Absolute recorded paths | Historical paths/hashes stay unchanged. Future auxiliary analysis can use project-relative paths; retained-record normalization is not claimed. | Historical preservation retained |

The twelve existing numerical table rows in the three documents were preserved.
Scoped link and whitespace checks passed. The additional full-pilot replay gap
is now closed by the [captured-source reproduction](shared-lifting-pilot-reproduction-v1.md):
four budgets, 192 matching algorithm evaluations, 109 accepted certificate checks
and unchanged original allocation files.

The [four-method scaling experiment](shared-lifting-scaling-plan-v3.md) uses the
existing 66 development profiles without adding favorable cases. Its results
will be recorded after actual execution and verification.

Task/gold validity, qualified domains, source-to-model fidelity, a substantive
method distinction and the full rubric remain separate requirements. This
review supports the cautious engineering-pilot interpretation; it does not
establish candidate superiority or scientific novelty.
