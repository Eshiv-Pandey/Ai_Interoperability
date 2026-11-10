# Manuscript v6 artifact guide

[Manuscript v6](../../paper/working-draft-v6.md) preserves the v5 method,
five-method results and bibliography, and adds the separately executed checked
AP2 continuation in Section 8.5. Its [ledger](../../paper/claim-ledger-v6.json)
binds the new evidence; the [v5 guide](paper-artifact-guide-v5.md) documents
all inherited results and reproduction commands.

| New result | Retained evidence |
| --- | --- |
| Actual original admitted AP2 sequence | [fresh semantic analysis](../../runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/fresh-semantic-analysis/result.json) |
| Separate signature, task, receipt and admission-to-wire audit | [final independent receipt](../../runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/fresh-signature-admission-review-2.json), [scope note](ap2-reference-development-v4-independent-signature-review.md) |
| Independently downloaded artifact copies | [exact copy correspondence](../../runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/canonical-copy-correspondence.json) |
| Intervention and fresh execution commands | [v4 runner guide](ap2-reference-development-v4.md) |

The one-step witness uses 427 declared work units and a 10,710-byte certificate.
It has no cache hits. Its checked 114-event evidence prefix precedes the actual
continuation at global event 115. The same original merchant/processor tasks
reach a corresponding demo Success receipt. These observations do not add
benchmark gold tasks or establish a performance benefit, native provider route,
financial settlement or complete action-space coverage.

Audit all inherited values and the new manuscript bindings using a fresh path:

```powershell
python -I -S -B paper/audit_draft_v6.py --output paper/draft-audit-v6-reproduction-1.json
```

The paper audit invokes no solver, checker, application or model. It validates
the inherited v5 audit, the preserved-v5 manuscript transformation and the new
already executed audit records. Fresh certificate and signature rechecking are
separately described in the independent result note. Independent AI checks
remain assistance in the same workflow; final human scientific review and the
full held-out application study remain open.
