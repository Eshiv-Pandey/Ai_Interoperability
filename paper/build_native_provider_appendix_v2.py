"""Build an additive paper appendix from three immutable native/provider runs.

Reads archive-bound records only; no application, SDK, model or provider import.
Failed responses without usage metadata remain unknown, including HTTP 503.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/ap2-original-native-provider-development"
SPECS = (
    ("v1", 42982595287, "0b73d252058fe6d967a54e4cbe1646e1f08b0ac0d3711d82791b90dd445e6d0a", 5),
    ("v2", 42995902326, "5aa54a06193b25416e6d952fdee9be2af1760fd60fed596107906c5864bb2bf3", 5),
    ("v3", 43014447502, "b8f988d85bb47cb98ea8c2171125e6441323a338223b634aed4ab2bfc3af3f49", 1),
)


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def strict(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_json")))


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path, inputs):
    path = Path(path)
    need(not path.is_symlink() and path.resolve().is_relative_to(ROOT), "regular_workspace_input_required")
    raw = path.read_bytes()
    inputs[path.relative_to(ROOT).as_posix()] = digest(raw)
    return strict(raw)


def bind_run(version, run_id, archive_sha, count, inputs):
    base = BASE / version / f"retained-{run_id}-1"
    receipt = read(base / "retention.json", inputs)
    run = read(base / "github-run.json", inputs)
    api = read(base / "github-artifacts.json", inputs)
    inventory = read(base / "extracted-manifest.json", inputs)["files"]
    archive = base / "artifact.zip"
    need(not archive.is_symlink(), "symbolic_archive_refused")
    actual = digest(archive.read_bytes())
    inputs[archive.relative_to(ROOT).as_posix()] = actual
    need(actual == {"bytes": receipt["archive_bytes"], "sha256": archive_sha}
         and receipt["archive_sha256"] == archive_sha
         and receipt["api_digest"] == "sha256:" + archive_sha
         and receipt["run_id"] == run_id and run["id"] == run_id
         and run["status"] == "completed" and run["run_attempt"] == 1
         and receipt["head_sha"] == run["head_sha"], "immutable_run_archive_binding_changed")
    artifacts = [row for row in api["artifacts"] if row["id"] == receipt["artifact_id"]]
    need(len(artifacts) == 1 and artifacts[0]["digest"] == receipt["api_digest"]
         and artifacts[0]["size_in_bytes"] == actual["bytes"], "API_archive_binding_changed")
    manifest = {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in inventory}
    need(len(manifest) == len(inventory), "duplicate_manifest_member")
    with zipfile.ZipFile(archive) as zipped:
        members = [member for member in zipped.infolist() if not member.is_dir()]
        need(len(members) == len(manifest) == receipt["extracted_files"], "archive_member_count_changed")
        need(len({member.filename for member in members}) == len(members), "duplicate_zip_member")
        for member in members:
            need(member.filename in manifest and digest(zipped.read(member)) == manifest[member.filename],
                 "ZIP_manifest_bytes_changed")
            path = base / "extracted" / member.filename
            need(not path.is_symlink() and path.resolve().is_relative_to(base / "extracted"), "unsafe_member")
            raw = path.read_bytes()
            need(digest(raw) == manifest[member.filename], "extracted_bytes_changed")
            inputs[path.relative_to(ROOT).as_posix()] = digest(raw)
    capture = base / "extracted"
    closing = read(capture / "execution/result.json", inputs)
    need(closing["allocated_task_count"] == count and len(closing["cases"]) == count
         and closing["unexecuted_count"] == 0, "all_declared_parent_attempts_required")
    ledger_path = capture / "execution/provider/ledger.jsonl"
    ledger = [strict(line) for line in ledger_path.read_bytes().splitlines()]
    starts = [row for row in ledger if row["phase"] == "started"]
    finishes = [row for row in ledger if row["phase"] == "finished"]
    need([row["allocation"] for row in starts] == list(range(len(starts)))
         and [row["allocation"] for row in finishes] == list(range(len(starts))), "provider_terminal_census_changed")
    known_tokens, missing_usage, request_bytes, status_counts = 0, 0, 0, Counter()
    for start, finish in zip(starts, finishes):
        index = start["allocation"]
        request = (capture / f"execution/provider/{index:03d}.request.json").read_bytes()
        response = (capture / f"execution/provider/{index:03d}.response.json").read_bytes()
        need(digest(request) == start["request"] and digest(response) == finish["response"], "provider_payload_digest_changed")
        request_bytes += len(request)
        status_counts[str(finish["http_status"])] += 1
        usage = strict(response).get("usageMetadata", {}).get("totalTokenCount")
        if type(usage) is int and usage >= 0:
            known_tokens += usage
        else:
            missing_usage += 1
    provider = closing["provider"]
    need(provider["upstream_allocations"] == len(starts)
         and provider["successful_provider_responses"] == status_counts["200"]
         and provider["observed_usage_tokens"] == known_tokens
         and provider["cumulative_request_bytes"] == request_bytes, "raw_provider_closing_summary_mismatch")
    local_path = capture / "execution/provider/local-refusals.jsonl"
    local_refusals = len(local_path.read_bytes().splitlines()) if local_path.exists() else 0
    return {"version": version, "run_id": run_id, "head_sha": run["head_sha"], "parent_attempts": count,
            "archive": actual, "archive_members": len(manifest), "upstream_allocations": len(starts),
            "HTTP_status_counts": dict(status_counts), "known_reported_tokens": known_tokens,
            "responses_without_usage": missing_usage, "all_response_token_total_measured": missing_usage == 0,
            "request_bytes": request_bytes, "owned_local_refusals": local_refusals}


def build(output, provenance):
    need(output.is_relative_to(ROOT) and provenance.is_relative_to(ROOT)
         and not output.exists() and not provenance.exists(), "fresh_workspace_appendix_outputs_required")
    inputs = {}
    rows = [bind_run(*spec, inputs) for spec in SPECS]
    semantic2 = read(BASE / "v2/independent-semantic-analysis-v1/analysis.json", inputs)
    need(semantic2["expected_run_id"] == SPECS[1][1] and not semantic2["integrity_questions"]
         and semantic2["public_receipt_case_count"] == 2 and len(semantic2["cases"]) == 5,
         "reviewed_V2_semantic_census_required")
    raw3 = read(BASE / "v3/independent-raw-review-v1.json", inputs)
    need(raw3["run_id"] == SPECS[2][1] and not raw3["issues"]
         and raw3["receipt_count"] == raw3["repeat_attempt_count"] == 0
         and raw3["received_HTTP503_responses"] == 1, "reviewed_V3_partial_census_required")
    table = ["| Run | Parent attempts | Upstream requests | HTTP 200 / 503 | Request bytes | Known tokens | Responses missing usage | Owned refusals |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        statuses = row["HTTP_status_counts"]
        table.append(f"| {row['version'].upper()} / `{row['run_id']}` | {row['parent_attempts']} | {row['upstream_allocations']} | {statuses.get('200', 0)} / {statuses.get('503', 0)} | {row['request_bytes']:,} | {row['known_reported_tokens']:,} | {row['responses_without_usage']} | {row['owned_local_refusals']} |")
    text = """# Original native AP2 and Gemini development observations

11 November 2026. This additive paper appendix preserves all three separately allocated development runs. It supplements the frozen V14 manuscript; it does not replace earlier failures or establish the qualified full study.

""" + "\n".join(table) + """

V1 retained five failed parent attempts before business or public Task capture. One parent access smoke returned the requested function call, and the first case read three original service cards. The first caller failed the owned callable binder; four later launch failures did not retain their errno. Their missing business outcomes remain missing.

V2 retained five scripted public-caller cases under original native services and actual SDK generation. Correct reply and foreign-context recovery each ended with one completed public Task and one demo Success receipt. Wrong reply remained input-required with the original incorrect-challenge message. No reply remained waiting with no OTP submission. The fifth case failed its prerequisite payment after the owned cumulative request-byte boundary refused a later call; no repeated continuation occurred. These are two observed receipt cases out of five declared development cases, not a human-gold pass rate. The all-200 upstream ledger rules out an observed upstream quota failure for that owned refusal.

V3 is one fresh adaptive repeat control selected after V2. Its original catalog request received an upstream HTTP 503 UNAVAILABLE high-demand response. The catalog prerequisite failed before payment or repeat: zero payment Task reads, receipts and repeat attempts. The 839 known tokens cover only the two successful responses; failed-response usage is unknown. A closing successful-response unknown-usage counter of zero does not make failed-response usage zero. All four recorded children were reaped. Workflow success reports evidence retention, not application task success.

All requests used the pinned `gemini-3.1-flash-lite-preview` generation path. Successful responses reported `gemini-3.1-flash-lite`; no provider revision identity or billing-tier claim follows. Original service modules, SDK and business functions ran with an owned accounting proxy, scripted public caller and owned public Task reader. The user choices were prospective actor inputs. This is not the original autonomous ADK shopper/public-user route, unchanged `run.sh` provisioning, independent bridge qualification, real settlement, hidden-effect idempotence, human gold or untouched holdout. The 100,000 observed-token threshold is post-response stopping, not a hard token or cost ceiling.

Each run keeps its own denominator and intervention profile. V3 neither replaces V2's partial fifth case nor creates an observed repeat result. No pooled efficacy estimate or full-study completion credit is assigned.

Source results: [V1](../docs/research/ap2-original-native-provider-results-v1.md), [V2](../docs/research/ap2-original-native-provider-results-v2.md), and [V3](../docs/research/ap2-original-native-repeat-results-v3.md). Archive hashes, raw reconstruction and exact input bindings are in the accompanying provenance JSON. The builder reads archive-bound bytes without importing or executing any application, SDK, actor, model, evaluator, solver or checker.
"""
    source_path = Path(__file__).resolve()
    inputs[source_path.relative_to(ROOT).as_posix()] = digest(source_path.read_bytes())
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    report = {"schema_version": "native-provider-paper-appendix/2", "paper": output.relative_to(ROOT).as_posix(),
              "paper_identity": digest(output.read_bytes()), "runs": rows, "inputs": inputs,
              "full_study_qualified": False, "human_gold_qualified": False, "repeat_observed": False,
              "new_application_or_provider_calls": 0}
    with provenance.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return {"status": "all_three_immutable_run_ledgers_reconstructed", "runs": len(rows),
            "known_V3_tokens_only": rows[2]["known_reported_tokens"], "V3_missing_usage_responses": rows[2]["responses_without_usage"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve(), args.provenance.resolve()), sort_keys=True))
