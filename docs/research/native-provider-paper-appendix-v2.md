# Native/provider paper appendix and offline reproduction

11 November 2026. The [additive appendix](../../paper/original-native-provider-v2-appendix.md) supplements the frozen V14 development manuscript with all three separately allocated original native AP2/Gemini runs. [Its provenance](../../paper/original-native-provider-v2-appendix.provenance.json) binds every inspected archive member and rederives request bytes, HTTP statuses, known usage and missing-usage counts from raw provider payloads and ledger hashes.

V1 retains five failed parent attempts. V2 retains five public-caller cases with two completed demo receipt observations, an incorrect-reply refusal, no-reply waiting and an owned-byte-budget stop before repetition. V3 retains one adaptive attempt that failed on an upstream HTTP 503 before catalog completion. No repeated continuation was observed in any of the three allocations. The denominators are not pooled, and no human-gold or full-study completion is claimed.

Each retained ZIP is published in one bounded archive part. Restore the three exact archives and their inspected members from a fresh checkout with these commands. `--restore-missing` first verifies every existing member against the saved complete inventory, then creates only absent members; changed bytes are refused.

```powershell
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-original-native-provider-development/v1/retained-42982595287-1 --index runs/ap2-original-native-provider-development/v1/retained-42982595287-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-original-native-provider-development/v2/retained-42995902326-1 --index runs/ap2-original-native-provider-development/v2/retained-42995902326-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-original-native-provider-development/v3/retained-43014447502-1 --index runs/ap2-original-native-provider-development/v3/retained-43014447502-1/archive-parts-v3/index.json --restore-missing
```

The builder requires fresh output paths and runs only the Python standard library. It opens no provider connection and imports no application, SDK, actor, model, solver, checker or evaluator. Rebuild into GUID-named files to preserve the published appendix:

```powershell
$appendixRun = [guid]::NewGuid().ToString('N')
python -I -S -B paper/build_native_provider_appendix_v2.py --output "paper/native-provider-recheck-$appendixRun.md" --provenance "paper/native-provider-recheck-$appendixRun.provenance.json"
```

The regenerated Markdown should have the same SHA-256 as the published appendix. The provenance differs in its output-path field. All three original archives, run identities, raw payloads and observed counts must remain identical. A failed response with absent or invalid usage metadata is counted as unknown; it contributes no claim of zero tokens. Reported known usage is neither a complete cost total nor proof of free-tier billing.

The [V3 semantic analysis](../../runs/ap2-original-native-provider-development/v3/independent-semantic-analysis-v1/analysis.json) and its five constructed controls are a separate public-observation check. The [raw/native review](../../runs/ap2-original-native-provider-development/v3/independent-raw-review-v1.json) and [source/runtime peer](../../runs/ap2-original-native-provider-development/v3/independent-native-binding-peer-v1.json) preserve provenance limits. Their consistency does not supply independent human review or original autonomous shopper qualification.
