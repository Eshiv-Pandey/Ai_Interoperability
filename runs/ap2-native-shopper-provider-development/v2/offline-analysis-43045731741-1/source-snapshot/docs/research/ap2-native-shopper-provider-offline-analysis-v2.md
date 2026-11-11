# Offline analysis of retained original native shopper V2

The additive [V2 analyzer](../../scripts/analyze_ap2_native_shopper_provider_v2.py) evaluates an actual root-retained V2 archive with explicit expected run and full head inputs. It reuses the unchanged, hash-pinned V1 public/ADK/provider reconstruction helpers. It does not alter V1 observations or the frozen V2 execution boundary, runner or tests. Its constructed controls are separate from actual application or provider results.

The expected template is the root-reviewed V2 [preparation-2 plan](../../runs/ap2-native-shopper-provider-development/v2/preparation-2/plan.json), SHA-256 `3c47d565091c3ac1b0842df35c56ecc1c12c1965e99cfe564456b71a7b399cda`. The analyzer requires that exact template hash, then compares every actual plan field except the preparation timestamp. It checks V2 schema, one-case denominator, case identity, original source/runtime pins, all public facts, model route, 120-second sender option, unchanged budgets and all five owned source snapshots. A V1 schema is rejected; no virtual schema rewrite or synthetic result substitutes for retained evidence.

Root supplies the actual run/head and retained path after terminal retention:

```text
python -I -S -B scripts/analyze_ap2_native_shopper_provider_v2.py --retained <actual-retained-directory> --output <fresh-analysis-directory> --expected-run <actual-run-id> --expected-head <full-40-character-head> --frozen-plan runs/ap2-native-shopper-provider-development/v2/preparation-2/plan.json
```

The inherited retention reader recomputes the archive hash against the root receipt and GitHub API digest, checks the expected run/head and completed status, joins ZIP membership and each archived member to the extracted manifest, and hashes extracted inspected members. Analysis output must be fresh and additive. The helper dependency is V1 analyzer SHA-256 `fd07c3609400f951d8500ce97f1cc655fc4ed654b7836597c30d26262ef930ab`.

V2 drain analysis joins the standalone `provider-drain.json`, its identical parent-result record, parent provider summary and raw request/response ledger. Admission and capture must be frozen; captured allocation/request-byte counts, unclosed identities and unknown-usage counts must match raw retained observations. Completed-handler assertions with unclosed consumed allocations, increasing handler counts after freeze, post-freeze ledger timestamps, missing records, altered timeout/bounds and changed source snapshots are recorded as inconsistencies.

Handler census and consumed allocation census are separate. Some handlers can be queued before allocation. An active sender may finish after capture freeze and reduce the parent summary's handler count without a captured terminal response. That consumed allocation remains unclosed and its usage remains unknown even if the later summary says zero active handlers. A file without a matching terminal ledger digest cannot provide measured usage. Unknown successful, failed and unclosed allocations are never converted to zero.

The recorded drain wait can slightly exceed the requested wait due to return/recording overhead; this comparison is reported separately. Neither those elapsed records nor urllib's transport timeout proves an independent whole-request network wall-clock cap. Frozen source policy and stable raw records support capture consistency; there is no retained observation of actual late upstream completion after a capture freeze.

Inherited public reconstruction retains original ADK errors, distinguishes visible final text from thoughts/tool parts, checks function identity/order, separates proposed and delivered actor replies, verifies visible USD prices, consent and explicit OTP timing, and joins Cart selection to preceding original SDK return and later argument/return/session state. Actor rendering stops, original tool errors, provider errors and unreached branches remain separate. Parent process/source/ownership assertions, runtime manifest identity and receipt shape do not supply human semantic gold, full original A2A wire, hidden effects or settlement proof.

Eighteen [constructed analyzer controls](../../tests/test_analyze_ap2_native_shopper_provider_v2.py) cover frozen schema/source/template binding, exact denominator, normal and incomplete capture, queued handler census, late handler completion with unknown consumption, contradictory completed-capture assertions, post-freeze timestamps, altered counts, timeout/wait records, runtime-preflight exceptions and measurement claims with inconsistent provider summaries. They execute only owned standard-library analysis against declared constructed fixtures, with no original SDK, application, listener, provider, download or dispatch.

Whole-task grade remains `null`; human gold, held-out-study credit, original `run.sh` qualification and settlement proof remain false. Actual V2 conclusions are produced only after root supplies retained terminal evidence.
