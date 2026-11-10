"""Extend the preserved v5 paper with independently audited AP2 admission execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC = "runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/fresh-semantic-analysis/result.json"
SIGNATURE = "runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/fresh-signature-admission-review-2.json"


def record(name):
    data = (ROOT / name).read_bytes()
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def build():
    text = (ROOT / "paper/working-draft-v5.md").read_text(encoding="utf-8")
    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("Expected one preserved fragment: " + old[:70])
        text = text.replace(old, new, 1)
    replace("Research manuscript, version 5", "Research manuscript, version 6")
    replace("original AP2 application development execution. The registered", "original AP2 application development execution and a separately audited\nshared-lifting admission-to-application continuation. The registered")
    replace("These results establish reproducible adverse evidence", "A subsequent shared-lifting-gated AP2 continuation is checked before its actual\nsend and reaches a separately verified demo receipt. These results establish\nreproducible adverse evidence")
    replace("The successful v3 sequence has zero provider requests and no admission gate.\nThe v4 successor adds shared-lifting admission before the original OTP send;\nconstructed controls exist, but no original v4 execution is claimed here.",
            "The successful v3 sequence has zero provider requests and no admission gate.\nA separate successful v4 allocation adds checked shared-lifting admission before\nthe original OTP send; Section 8.5 reports its actual raw and application evidence.")
    replace("The six AgentOps\ndevelopment receipts currently validate original read components only: none\ncompletes its governed App task, and all six whole-task outcomes remain unknown.",
            "The earlier six AgentOps component receipts validate original read components\nonly. A subsequent [governed-App addendum](agentops-governed-app-addendum-v1.md)\nreports a completed health task and an unconfirmed restart pause. Both strict\nprofiles fail a recorded blocked-bind check, retaining aggregate 0/2 acceptance;\nno whole-bank task/gold qualification is inferred.")
    section = """### 8.5. Shared-lifting admission before the original AP2 continuation

The subsequent hosted run
[42858644500](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42858644500)
at commit `36ba3e3c232a30c31526cfabc6c4c4dc32dbeab3` executes the same original
application with the disclosed offline-model, ASGI and owned-adapter
interventions. Immediately before the merchant OTP continuation, the owned
coordinator reads the actual public pending task and the unchanged original
builder message. The coordinator keeps merchant and processor task references
distinct in the pending input/raw-binding envelope. Its one-edge, horizon-one
profile binds the merchant task and context, permitting only the public demo OTP recipe.
Its coverage and evidence are explicitly incomplete, so only a supported
positive witness can dispatch; failure cannot prove whole-route non-support.

Shared lifting returns a recipe-path certificate using 427 of 100,000 declared
solver work units. Its canonical certificate is 10,710 bytes. It performs one
relation check and has zero prefix/relation cache hits. This is evidence of
admission integration, not a cache-reuse or application performance advantage.
The unchanged independent checker accepts at both the extraction and dispatch
clock, 1794329502, before expiry 1794329517. These values implement the declared
15-second evidence interval rather than an authenticated service lease.

A retained 114-event journal prefix of 234,600 bytes binds the pre-send evidence.
The original raw continuation begins at global event 115 and merchant exchange
4. The actual raw bytes, message/task/context identifiers, signed mandates and
OTP match the certified original-builder request. Admission files and the
journal prefix retain their pre-send hashes; no second continuation is sent.
Both the same original merchant and processor tasks complete. Their demo Success
receipt matches the caller and credential-provider delivery, and its transaction
reference is independently recomputed from the retained mandate bytes.

Two independently downloaded copies have exactly matching 182-file inventories
and the same digest for the 1,694,552-byte artifact. A fresh semantic analyzer checks all
168 durable events, 17 raw exchanges, 12 RPC requests, 136 original source files,
task/receipt correspondence and cleanup. A separately authored AI audit rechecks
both buyer-root ES256 signatures/disclosures, positive certificates at both
clocks, and the admission-to-wire relation. Altered-signature/unrelated-key,
tampered-task-witness and expired-clock controls are rejected. Five clients
close. The absent merchant public key still prevents independent checking of
its checkout signature.

This one successful admitted development sequence remains separate from the
ungated v3 allocation and earlier failures. It does not establish native TCP,
original provider routing, financial settlement, full original shopper-policy
qualification or independent held-out gold. The actual outcome supplies
separate evidence after a conditional model witness; neither implies complete
real-route coverage or a universal completion guarantee.

"""
    marker = "## 9. Discussion"
    text = text.replace(marker, section + marker, 1)
    text = text.replace("paper-artifact-guide-v5.md", "paper-artifact-guide-v6.md")
    replace("The separate fifth comparator reinforces the adverse aggregate result.",
            "A subsequent shared-lifting-gated AP2 development sequence also reaches\na separately observed demo receipt after independently checked pre-send admission.\nThe separate fifth comparator reinforces the adverse aggregate result.")
    return text


if __name__ == "__main__":
    with (ROOT / "paper/working-draft-v6.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(build())
    now = datetime.now(timezone.utc).isoformat()
    files = ["paper/working-draft-v5.md", "paper/claim-ledger-v5.json", "paper/draft-audit-v5-5.json",
             SEMANTIC, SIGNATURE, "runs/ap2-reference-development/v4/independent-capture-42858644500-20261110T165858Z/canonical-copy-correspondence.json",
             "docs/research/ap2-reference-development-v4-independent-signature-review.md"]
    ledger = {"schema_version": "working-paper-claim-ledger/6", "created_utc": now,
              "draft": record("paper/working-draft-v6.md"), "builder": record("paper/build_draft_v6.py"),
              "artifact_guide": record("docs/research/paper-artifact-guide-v6.md"),
              "inherited_claim_ledger": "paper/claim-ledger-v5.json", "human_scientific_review_claimed": False,
              "new_claim": "One observed positive shared-lifting admission before the original AP2 demo continuation, followed by actual task/receipt success.",
              "evidence": [record(name) for name in files],
              "limits": ["Offline model/ASGI/owned-adapter interventions", "Incomplete model coverage; no real-route negative inference",
                         "No native/provider/settlement/held-out qualification", "No cache performance benefit in this one-edge witness"]}
    status = {"schema_version": "working-paper-draft-status/6", "created_utc": now,
              "document": "paper/working-draft-v6.md", "prior_version": "paper/working-draft-v5.md",
              "full_manuscript_drafted": True, "publication_ready": False, "original_research_validity_gates_complete": False,
              "human_scientific_review_claimed": False, "AP2_v4_original_admitted_development_execution_claimed": True,
              "claim_ledger": "paper/claim-ledger-v6.json", "verification": "pending",
              "new_application_or_model_calls_for_drafting": 0}
    for name, value in (("paper/claim-ledger-v6.json", ledger), ("paper/draft-status-v6.json", status)):
        with (ROOT / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"status": "built", "draft": ledger["draft"]}))
