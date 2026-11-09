# Human task/gold review form

Make one copy per reviewer, for example `reviewer-feedback-v1-reviewer-1.md`. Complete it independently and return that copy. Do not fill another person's name or decision. This form reviews the listed development material; the incomplete 12/8/48-template bank remains unqualified and CP3 remains open.

## Reviewer and actual scope

- Reviewer name:
- Role/relevant experience:
- Review date:
- Files/versions actually read (include the JSON export hashes or identify the copies received):
- Case IDs and turns actually reviewed:
- Source files/lines actually checked:
- Items not reviewed:
- Was this review completed before discussion with the other reviewer? Yes / No. If no, describe:
- Tools or AI assistance used, and which judgments you personally checked:

Use **adequate**, **needs changes** or **not reviewed / insufficient evidence** for judgments below. Explain each adverse or uncertain judgment with an exact case/file reference. Duplicate the case block for every case you review.

## Per-case review

- `eval_set_id` / `eval_id` / turn, or AP2 proposed check/example name:
- **Task intent and clarity:** judgment; ambiguity or missing instruction:
- **Expected behavior / proposed gold:** judgment; source-backed facts and allowed actions; legitimate alternative answers or trajectories:
- **Reference trajectory and replies:** judgment; required dependencies, successful/missing replies, call identity, session continuity and ordering:
- **Near misses:** judgment; which almost-correct, wrong-binding, stale, unauthorized or incomplete-evidence outcome should fail or remain unknown; source support:
- **State and reset:** judgment; initial fixture, user/session/transaction identity, permitted changes, unrelated rows to preserve, and what must reset before another instance:
- **Grader adequacy:** judgment; false-pass/false-fail risk, unsupported gold, missing semantic checks or unobserved runtime evidence:
- Exact file/case/turn/source lines supporting the review:
- Required correction or additional evidence:

Check these distinctions where applicable:

- A reference final response or tool list is not observed execution. Grounded paraphrases and extra permitted reads may be valid; do not invent a stricter source rule.
- AgentOps approval cases end at the confirmation pause. They supply no approval, so they do not permit a business mutation. The memory case's intended note write and later recall must refer to its actual common user/session.
- Missing-incident/service/log results can be the correct task outcome. Preserve missing `api-gateway` log evidence rather than inventing a successful retrieval.
- AP2 correct OTP alone does not prove completion or credential/mandate validity. Wrong OTP should preserve the documented retry behavior. A changed valid mandate needs an explicit original-intent judgment; upstream rejection is not assumed. Receipt/reference consistency is separate from authority, reset and real-world payment effects.
- An algorithm's supported/unsupported certificate is relative to its declared model. Unknown is an abstention. Supplied coverage/provenance labels do not prove a real bridge's complete legal action space.

## Overall task/gold assessment

- Which listed development cases are adequate after this review?
- Which need correction, and why?
- What missing task, gold, near-miss, domain or reset evidence prevents a qualified benchmark?
- Are the described metric, stronger checks and pending human semantic judgments kept separate? Judgment and references:
- Possible leakage or overlap among public development, future calibration and future held-out items:
- Disagreements with another reviewer (complete after independent review):
- Proposed resolution and whether a fresh review is needed:

## Optional algorithm/contribution assessment

Complete only if you actually reviewed the algorithm and comparison files and have relevant expertise. Otherwise mark this section **not reviewed**.

- Exact candidate/code and comparison versions reviewed:
- Technical distinction from the strongest same-evidence comparator: adequate / needs changes / not reviewed; reasons:
- Are evidence, legal actions, bounds, pruning, memoization and construction/checking costs fairly matched? Judgment and references:
- Is substantive advantage actually demonstrated? Demonstrated / not demonstrated / not reviewed; evidence and limits:
- Objections and the next source-supported discriminator or measurement needed:
- If acting as the supervisor/mentor, record that role and your actual novelty/feasibility decision; otherwise leave this field unreviewed:

## Reviewer confirmation

- I personally reviewed the items listed above: Yes / No.
- Name and date of confirmation:

No reviewer identity, approval, full-bank coverage, checkpoint pass or extension is recorded until an actual person completes and returns this form. Keep both reviewers' original returns and later corrections separately.
