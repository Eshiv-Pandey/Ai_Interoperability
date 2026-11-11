"""Write the additive V4 development result from bound independent read reviews."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = "runs/ap2-native-shopper-provider-development/v4/independent-raw-review-v2/review.json"
PROVIDER = "runs/ap2-native-shopper-provider-development/v4/provider-lifecycle-independent-review-v1.json"
BASE = "runs/ap2-native-shopper-provider-development/v4/retained-43074319113-1"
DRAFT_SHA = "967eccdc549a683053b814044ce7c4ed3b4de63e572eb72679082a602837f4b6"


def identity(path):
    raw = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(path, text):
    with (ROOT / path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


review = json.loads((ROOT / REVIEW).read_bytes())
provider = json.loads((ROOT / PROVIDER).read_bytes())
counter = provider["provider"]
if (review["run_id"] != 43074319113 or review["case_denominator"] != 1
        or review["consistency_questions"] or provider["material_consistency_questions"]
        or identity(PROVIDER) != review["provider_lifecycle_independent_review"]):
    raise ValueError("Independent V4 review binding differs")
draft = identity("paper/working-draft-v15.md")
if draft["sha256"] != DRAFT_SHA:
    raise ValueError("Sealed V15 manuscript changed before addendum")
numbers = {
    "cases": review["case_denominator"], "ADK_events": review["raw_ADK_events"],
    "session_events": review["session_events_including_initial_user"],
    "business_attempts": review["business_function_call_attempts"],
    "business_terminals": review["business_function_terminal_responses"],
    "visible_model_replies": review["visible_model_text_messages"],
    "actor_replies": review["public_actor_replies"], "receipts": review["canonical_public_receipt_records"],
    "upstream_allocations": counter["upstream_allocations"], "shopper_allocations": counter["shopper_generation_allocations"],
    "request_bytes": counter["request_bytes"], "known_tokens": counter["known_reported_tokens"],
    "missing_usage": counter["responses_with_missing_usage"],
    "owned_refusals": len(counter["owned_refusals_after_upstream_failure"]),
}
if numbers != {"cases": 1, "ADK_events": 10, "session_events": 11, "business_attempts": 2,
               "business_terminals": 0, "visible_model_replies": 0, "actor_replies": 0, "receipts": 0,
               "upstream_allocations": 5, "shopper_allocations": 4, "request_bytes": 23802,
               "known_tokens": 4081, "missing_usage": 1, "owned_refusals": 2}:
    raise ValueError("V4 factual template differs from the independent raw census")

guide = """# Original native AP2 shopper V4: tool attempts and retained failures

Run [43074319113](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43074319113)
at head `117daf284fe2758746369f0abe06e03870077c31` captures one adaptive
development case. Its 1,255,530-byte ZIP has SHA256
`b051d089a19b489fc758b96b714bd56f6718bf662e09ab6a17c846494511d908`,
matching the retained GitHub API digest. Both independent read reviews verify all
48 ZIP/extracted members. Workflow success and shopper exit code zero do not
qualify a successful purchase.

| Retained observation | Count |
| --- | ---: |
| Allocated cases | 1 |
| Raw ADK events / session events including initial user | 10 / 11 |
| Original business function-call attempts / terminal responses | 2 / 0 |
| Visible model replies / actual actor replies | 0 / 0 |
| Canonical public receipt records | 0 |
| Upstream allocations, including access smoke | 5 |
| Shopper generation allocations | 4 |
| HTTP 200 / upstream HTTP 503 | 4 / 1 |
| Cumulative request bytes | 23,802 |
| Known reported tokens / responses lacking usage | 4,081 / 1 |
| Owned proxy refusals after upstream failure | 2 |

The original root emits `transfer_to_agent` to `shopper`; its matching ADK
function response completes that control-flow transfer. The actual shopper
then emits two `find_products` calls with the same public catalog query and
different call IDs. Captured provider responses match all three ADK call IDs,
names, exact arguments, model versions and reported token totals. Neither
business call has a terminal `functionResponse` or a returned catalog Task.

Both attempts produce `A2AClientHTTPError` at original merchant agent-card
acquisition, with `owned_user_actor_external_network_denied`. Stack traces
reach the pinned original shopper `tools.py:55`, where `find_products` awaits
the original merchant client. The native watcher and each native service log
contain one preparation card GET and no business POST. This is an owned actor
guard failure during actual original tool execution, not an observed merchant
business refusal or an absence of a model function call.

The bound worker guard allows only string loopback host names and configured
native/proxy ports. The rejected socket/getaddrinfo arguments were not retained;
the exact host/port representation mismatch is unproven. Source diagnosis must
not present a guessed bytes-host or IPv6 cause as a measured fact.

A later upstream response is HTTP 503 `UNAVAILABLE`, reporting high demand and
no usage metadata. Two subsequent owned local refusals carry the prior-failure
message, followed by the original retry-layer exhaustion event. Proxy source
and remaining call/byte/token allowance support the prior-failure branch;
these refusals are not measured quota exhaustion. The 4,081 known-token sum
includes 45 smoke tokens; the failed response's usage remains unknown rather
than zero. There are six raw error events: two owned card-network denials,
one upstream 503, two owned prior-failure refusals and one final retry exhaustion.

The public conversation contains only the initial user request. The actor's
sole decision has a null reply and the SHA256 of empty visible text. The worker
stops as `public_actor_stopped_without_unambiguous_unseen_question`; the session
state is empty and no receipt is retained. Predetermined OTP/confirmation facts
were not submitted during this case. No complete payment, human semantic grade,
real settlement or hidden-effect claim is granted.

The exact V4 worker/public facts and all six owned-source snapshots bind to the
plan. Required 182 versions match 185 recorded distributions, while hosted venv
physical files are unavailable for independent post-run rehashing. Four recorded
children are reaped, with native start/finish PIDs matching cleanup records and
both recorded remote HTTP clients closed. No explicit official Runner-close
receipt or raw `/proc` socket-inode ownership snapshot is retained.

This is direct original ADK with native peers, an owned public-only user actor
and an owned provider accounting proxy. Original root/subagent tool and model
declarations are separately source-bound; complete capture/runtime authentication
and unchanged `run.sh` provisioning remain unqualified. The earlier V1 timeout,
V2 interpreter-preflight failure and V3 public-facts mismatch remain unchanged
in their separate one-case denominators. V4 is not merged into the scripted V2
two-receipt cohort or the registered held-out study.

The [independent raw review](../../runs/ap2-native-shopper-provider-development/v4/independent-raw-review-v2/review.json)
and [provider/runtime/lifecycle review](../../runs/ap2-native-shopper-provider-development/v4/provider-lifecycle-independent-review-v1.json)
contain identities and witnesses. Their standard-library sources execute no
original application, SDK or provider. Recheck retained shopper evidence into an
unused output directory:

```powershell
python -I -S -B scripts/review_ap2_native_shopper_provider_v4.py --retained runs/ap2-native-shopper-provider-development/v4/retained-43074319113-1 --provider-review runs/ap2-native-shopper-provider-development/v4/provider-lifecycle-independent-review-v1.json --output runs/ap2-native-shopper-provider-development/v4/your-unused-raw-review
```

The [additive paper note](../../paper/ap2-native-shopper-v4-development-addendum-v1.md)
binds the unchanged V15 manuscript and this result; it does not replace any
sealed manuscript or historical result.
"""
note = """# Additive original native AP2 shopper V4 development observation

This note is additive to the frozen V15 manuscript and preserves its numerical
sections, original-study qualifications and earlier denominators. It reports one
separately allocated adaptive development case from run `43074319113` at head
`117daf284fe2758746369f0abe06e03870077c31`.

The actual original root/ADK emits ten events, including a completed transfer
to the shopper and two original `find_products` attempts. Neither business
attempt returns a terminal function response: both fail during merchant native
agent-card lookup at the owned actor socket guard. A later actual provider
response is HTTP 503 high demand, followed by two owned prior-failure refusals
and retry exhaustion. Exact rejected socket arguments were not captured.

All five upstream allocations remain counted, including one access smoke:
four HTTP 200, one HTTP 503, 23,802 request bytes, 4,081 known reported tokens
and one response lacking usage. Failed-response usage is unknown rather than
zero. Four recorded children are reaped and both recorded remote clients close;
full runtime authentication, Runner-close and socket-inode witnesses are absent.

The public conversation has only the initial user request; there is no visible
model reply, actor reply, returned catalog Task, payment completion or receipt.
Shopper exit zero reflects the owned actor's honest stop, not purchase success.
This profile adds actual original tool-attempt failure evidence, with no human
gold, untouched holdout, settlement or general method-advantage qualification.

The earlier V1 timeout, V2 interpreter-preflight failure and V3 public-facts
mismatch remain unchanged. The V4 result is separate from scripted native AP2
V2's two completed public receipt cases and the original registered full study.

See [the complete V4 result guide](../docs/research/ap2-native-shopper-provider-development-results-v4.md)
and [the independent raw review](../runs/ap2-native-shopper-provider-development/v4/independent-raw-review-v2/review.json).
The [provenance](ap2-native-shopper-v4-development-addendum-v1.provenance.json)
binds this note, frozen V15, raw archive, current read reviews and source.
"""
guide_path = "docs/research/ap2-native-shopper-provider-development-results-v4.md"
note_path = "paper/ap2-native-shopper-v4-development-addendum-v1.md"
save(guide_path, guide)
save(note_path, note)
if identity("paper/working-draft-v15.md") != draft:
    raise ValueError("Sealed V15 manuscript changed while constructing addendum")
provenance = {
    "schema_version": "ap2-native-shopper-V4-additive-paper-provenance/1",
    "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "addendum": identity(note_path), "result_guide": identity(guide_path), "sealed_V15": draft,
    "builder": identity("paper/build_ap2_native_shopper_v4_addendum_v1.py"),
    "inputs": [identity(path) for path in (REVIEW, PROVIDER, BASE + "/retention.json",
        BASE + "/extracted-manifest.json", BASE + "/artifact.zip",
        "scripts/review_ap2_native_shopper_provider_v4.py",
        "runs/ap2-native-shopper-provider-development/v4/review_provider_lifecycle_v1.py")],
    "derived_counters": numbers,
    "new_application_SDK_provider_solver_evaluator_checker_executions": 0,
    "historical_or_sealed_artifacts_modified": False,
    "whole_task_grade": None, "human_scientific_review": False,
    "untouched_holdout_qualification": False, "publication_ready": False,
    "whole_original_study_complete": False,
}
save("paper/ap2-native-shopper-v4-development-addendum-v1.provenance.json",
     json.dumps(provenance, indent=2, sort_keys=True) + "\n")
print(json.dumps({"guide": identity(guide_path), "addendum": identity(note_path),
                  "provenance": identity("paper/ap2-native-shopper-v4-development-addendum-v1.provenance.json")}))
