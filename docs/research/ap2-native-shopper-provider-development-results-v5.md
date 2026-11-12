# Original native shopper V5: returned catalog, public actor stop

12 November 2026. One prospective adaptive development case ran at
[`43161674908`](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43161674908),
head `b7bbe86f00a6c590f56bf7d9bb994756b1a07bf7`. The retained 1,271,535-byte ZIP
contains 53 members and matches the GitHub API SHA256
`5c133aebfa5bddbf23c38ce782c6eaa5b3d3674ccf04015521d99a51b0b51e58`.
The original root/ADK/native peers use the owned visible-text public actor and
provider-accounting proxy disclosed in the [prospective protocol](ap2-native-shopper-provider-protocol-v5.md).
The [source review and final binding](../../runs/ap2-native-shopper-provider-development/v5/independent-prospective-review-v2/review.json)
accepted one bounded allocation before dispatch. Earlier cases remain separate.

| Actual retained observation | Count |
| --- | ---: |
| Allocated cases | 1 |
| Raw ADK events | 5 |
| Original business call attempts / matching terminal responses | 1 / 1 |
| Visible model messages / delivered actor replies | 1 / 0 |
| Sample Success receipt records | 0 |
| Upstream allocations / HTTP 200 responses, including smoke | 6 / 6 |
| Cumulative request bytes | 24,465 |
| Known reported tokens / allocations with unknown usage | 5,612 / 0 |
| Recorded network/private/process denials | 0 / 0 / 0 |
| Recorded children reaped / remote HTTP clients closed | 4 / 2 |

The original `find_products` call returns a catalog with three USD offers. The
shopper displays a bullet list priced at $45.99, $62.50 and $89.00 and asks which
item the user wants to purchase. The fixed actor proposes no reply. Its worker
stops as `public_actor_stopped_without_unambiguous_unseen_question`; it neither
selects a cart nor proceeds through payment. This is a returned catalog tool
call and visible display, with zero purchase receipts and no whole-task grade.
Workflow success and worker exit zero do not change that outcome.

V5 records no network denial, no original ADK error event and no provider
refusal. Its reserved denial stream is empty and all logging counters reconcile.
This observed route result does not establish the exact cause of the unrecorded
V4 rejected socket arguments. V4's two failed tool attempts, later upstream 503,
missing usage and zero receipts stay unchanged.

The [retained-byte analyzer](../../runs/ap2-native-shopper-provider-development/v5/analysis-43161674908-v1.json)
has zero consistency questions. It joins exact provider function calls to ADK
events, matches sessions and public facts, separates incomplete calls from
receipts, checks diagnostic counters and bounds, and retains known versus unknown
usage. Fifteen helper controls and sixteen constructed integration controls
validate evidence joins; eleven guard controls include real local IPv4/IPv6,
bytes-host/numeric-service and UDP operations. These controls are not additional
original application trials. The
[independent provider/runtime/lifecycle review](../../runs/ap2-native-shopper-provider-development/v5/provider-lifecycle-independent-review-v1.json)
also passes with zero material consistency questions and independently verifies
all 53 archive members. Its scope preserves the missing runtime and wire witnesses.

No human gold, untouched holdout, full task oracle, original `run.sh` provisioning,
full physical runtime authentication, explicit Runner-close witness or real
settlement is qualified. The registered full study and the approximately 80%
whole-project work estimate are unchanged. The completed V1 release is preserved.

Reanalyze the retained evidence without application or provider execution:

```powershell
python -I -S -B scripts/analyze_ap2_native_shopper_provider_v5.py --retained runs/ap2-native-shopper-provider-development/v5/retained-43161674908-1 --run-id 43161674908 --head-sha b7bbe86f00a6c590f56bf7d9bb994756b1a07bf7 --frozen-plan runs/ap2-native-shopper-provider-development/v5/preparation-1/plan.json --frozen-plan-sha256 3bee8a4653206a425d9b8a26c59f566023bb0ff19258fadfbddca358e5452ac7 --output runs/ap2-native-shopper-provider-development/v5/your-unused-analysis.json
```

The next adaptive actor change must freeze a separate visible-list grammar and
case before allocation. Changing the actor after this observation cannot turn
the retained V5 stop into a successful purchase or a confirmatory result.
