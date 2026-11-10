# Manuscript v7 fresh-checkout evidence reproduction

Hosted run 42891705471 passed on revision
`5c4f6b9db47dc112c9b768b8cdcb112bc24e7a11`. Its retained artifact matches the
GitHub API SHA-256. The [fresh audit](../../runs/ci-manuscript-v7/retained-42891705471-1/extracted/audit.json)
reproduces the local manuscript/ledger/guide hashes and all inherited/new
evidence checks after restoring nine exact public archives into a clean
Ubuntu checkout. The [restoration receipt](../../runs/ci-manuscript-v7/retained-42891705471-1/extracted/restore.json)
records existing files and each newly restored member.

The manuscript hash is
`fc21a040f56cbeeb984841562d983805efdc996f696bdd395ecd37670b73b743`.
The audit preserves 1,584 cache cells, AP2 purchase totals 11/3/10/3/9,
31 error-free owned-cell purchases, AgentOps20/10/2/2 complete/partial/
unsupported/failed recipes, and ADK29prefixes/28generic adverse/0purchases.
No application, solver, certificate checker or provider was newly executed.
This reproduces manuscript evidence bindings and the read-only audit; it is
not a fresh scientific application trial or accountable human review.

The first fresh attempt, 42891103476, restored the archives but failed because
two inherited evidence files had not been included in Git. Its
[failure stderr](../../runs/ci-manuscript-v7/retained-42891103476-1/extracted/audit.stderr)
and retained metadata remain unchanged. Adding the two existing files did
not alter any experimental outcome or manuscript hash. The successful run
is a separate successor allocation.

Reproduce from the published checkout:

```powershell
python -I -S -B scripts/restore_retained_paper_evidence_v2.py --restore
python -I -S -B paper/audit_draft_v7.py --output paper/draft-audit-v7-fresh-checkout-1.json
```
