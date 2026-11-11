"""Independent retained-byte V4 provider/runtime/lifecycle review; stdlib only.

No original App, SDK, provider, solver or downloaded source is imported/executed.
The report is conditional on the supplied retained archive and metadata.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE = ROOT / "runs/ap2-native-shopper-provider-development/v4/retained-43074319113-1"
EXPECTED_RUN = 43074319113
EXPECTED_HEAD = "117daf284fe2758746369f0abe06e03870077c31"
EXPECTED_ARCHIVE = "b051d089a19b489fc758b96b714bd56f6718bf662e09ab6a17c846494511d908"
CASE = "ap2-native-shopper-provider-v4-correct-human"


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def review(base):
    evidence = {}

    def raw(name):
        path = base / name
        need(path.is_file() and not path.is_symlink(), "regular_retained_file_required:" + name)
        value = path.read_bytes()
        evidence[name] = digest(value)
        return value

    def obj(name):
        return json.loads(raw(name))

    retention = obj("retention.json")
    run = obj("github-run.json")
    artifacts = obj("github-artifacts.json")["artifacts"]
    need(retention["run_id"] == run["id"] == EXPECTED_RUN, "run_binding_differs")
    need(retention["head_sha"] == run["head_sha"] == EXPECTED_HEAD, "head_binding_differs")
    need(run["run_attempt"] == 1 and run["status"] == "completed", "terminal_run_attempt_required")
    archive_raw = raw("artifact.zip")
    archive_identity = digest(archive_raw)
    need(archive_identity == {"bytes": 1255530, "sha256": EXPECTED_ARCHIVE}, "archive_identity_differs")
    selected = [item for item in artifacts if item["id"] == retention["artifact_id"]]
    need(len(selected) == 1, "one_API_artifact_required")
    artifact = selected[0]
    need(artifact["digest"] == "sha256:" + EXPECTED_ARCHIVE
         and artifact["size_in_bytes"] == archive_identity["bytes"]
         and artifact["workflow_run"]["id"] == EXPECTED_RUN
         and artifact["workflow_run"]["head_sha"] == EXPECTED_HEAD, "API_artifact_binding_differs")
    manifest = obj("extracted-manifest.json")["files"]
    names = {item["path"] for item in manifest}
    need(len(names) == len(manifest) == retention["extracted_files"] == 48, "48_unique_manifest_files_required")
    with zipfile.ZipFile(base / "artifact.zip") as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        need({info.filename for info in members} == names and len(members) == 48, "ZIP_manifest_membership_differs")
        for item in manifest:
            value = archive.read(item["path"])
            expected = {"bytes": item["bytes"], "sha256": item["sha256"]}
            need(digest(value) == expected, "ZIP_member_identity_differs:" + item["path"])
            need(raw("extracted/" + item["path"]) == value, "extracted_member_differs:" + item["path"])
    plan = obj("extracted/plan/plan.json")
    root_plan = obj("plan.json")
    need(root_plan["run_id"] == EXPECTED_RUN and root_plan["artifact_name"] == retention["artifact_name"]
         and root_plan["application_rerun"] is False, "root_retention_plan_binding_differs")
    opening = obj("extracted/execution/opening.json")
    need({k: opening["plan"][k] for k in ("bytes", "sha256")} == digest(raw("extracted/plan/plan.json")), "opening_plan_identity_differs")
    need(plan["schema_version"] == "ap2-native-shopper-provider-plan/4"
         and plan["allocated_task_count"] == 1, "V4_one_case_scope_required")
    for name, expected in plan["owned_sources"].items():
        need(digest(raw("extracted/plan/owned-source/" + name)) == expected, "owned_source_snapshot_differs:" + name)
    worker_name = plan["selected_worker_relative_path"]
    worker_raw = raw("extracted/plan/owned-source/" + worker_name)
    tree = ast.parse(worker_raw)
    facts_func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "public_facts")
    worker_facts = ast.literal_eval(next(node for node in facts_func.body if isinstance(node, ast.Return)).value)
    prefix = "extracted/execution/cases/" + CASE + "/"
    public_facts = obj(prefix + "public-human-facts.json")
    need(worker_facts == public_facts == plan["public_human_facts"], "exact_typed_public_facts_differs")
    preflight = obj("extracted/execution/worker-public-facts-preflight.json")
    need(preflight["selected_worker"] == worker_name
         and preflight["selected_worker_source_identity"] == digest(worker_raw)
         and preflight["exact_public_field_agreement"] is True
         and preflight["before_provider_smoke"] is True, "worker_preflight_differs")
    old = raw("extracted/plan/owned-source/scripts/ap2_native_shopper_provider_worker_v1.py")
    changed = old.replace(b"ap2-native-shopper-provider-v1-correct-human", b"ap2-native-shopper-provider-v4-correct-human").replace(
        b"ap2-native-shopper-provider-worker/1", b"ap2-native-shopper-provider-worker/2")
    need(worker_raw == changed, "worker_delta_exceeds_case_and_schema")
    result = obj("extracted/execution/result.json")
    runtime_raw = raw("extracted/execution/portable-runtime.json")
    runtime = json.loads(runtime_raw)
    need(result["portable_runtime_sha256"] == digest(runtime_raw)["sha256"], "runtime_result_binding_differs")
    need(runtime["python_version"] == "3.13.1"
         and runtime["required_original_versions"] == plan["versions"], "runtime_plan_versions_differs")
    need(all(runtime["distributions"].get(name) == version for name, version in plan["versions"].items()), "actual_required_distribution_differs")
    need(runtime["source_stage_sha256"] == plan["source_stage_sha256"]
         and runtime["original_windows_environment_sha256"] == plan["original_windows_environment_sha256"], "runtime_stage_reference_differs")
    pip_raw = raw("extracted/pip-install-report.json")
    need({k: runtime["pip_report"][k] for k in ("bytes", "sha256")} == digest(pip_raw), "pip_report_binding_differs")
    pip = json.loads(pip_raw)
    normalize = lambda name: re.sub("[-_.]+", "-", name).lower()
    installed = {normalize(row["metadata"]["name"]): row["metadata"]["version"] for row in pip["install"]}
    need(all(runtime["distributions"].get(name) == version for name, version in installed.items()), "pip_actual_distribution_differs")
    binding = obj(prefix + "shopper/original-root-binding.json")
    launch = obj(prefix + "native-launch.json")
    root_relative = "code/samples/python/src/roles/shopping_agent/agent.py"
    need(binding["original_root_source_sha256"] == plan["sources"][root_relative]["sha256"], "root_source_plan_binding_differs")
    need(binding["original_root_import_file"] == launch["original_source_copy_roots"]["ap2"] + "/" + root_relative, "private_root_import_path_differs")
    need(binding["root_model"] == plan["model"]
         and [item["name"] for item in binding["subagents"]] == ["shopper", "shipping_address_collector", "payment_method_collector"], "original_root_model_subagents_differs")
    ledger = [json.loads(line) for line in raw("extracted/execution/provider/ledger.jsonl").splitlines()]
    started = {row["allocation"]: row for row in ledger if row["phase"] == "started"}
    finished = {row["allocation"]: row for row in ledger if row["phase"] == "finished"}
    need(len(ledger) == 10 and set(started) == set(finished) == set(range(5)), "five_closed_provider_allocations_required")
    rows, known, request_bytes = [], 0, 0
    models = Counter()
    for index in range(5):
        request = raw(f"extracted/execution/provider/{index:03d}.request.json")
        response = raw(f"extracted/execution/provider/{index:03d}.response.json")
        need(digest(request) == started[index]["request"] and digest(response) == finished[index]["response"], "provider_payload_ledger_binding_differs")
        request_bytes += len(request)
        body = json.loads(response)
        usage = body.get("usageMetadata", {}).get("totalTokenCount")
        measured = type(usage) is int and usage >= 0
        if measured:
            known += usage
        if body.get("modelVersion"):
            models[body["modelVersion"]] += 1
        need(finished[index]["observed_cumulative_usage_tokens"] == known, "known_cumulative_usage_differs")
        rows.append({"allocation": index, "http_status": finished[index]["http_status"],
                     "request_bytes": len(request), "known_reported_tokens": usage if measured else None,
                     "unknown_usage_reason": None if measured else "missing_usage",
                     "upstream_error": body.get("error"), "model_version": body.get("modelVersion")})
    statuses = Counter(row["http_status"] for row in rows)
    missing = sum(row["known_reported_tokens"] is None for row in rows)
    need(statuses == {200: 4, 503: 1} and request_bytes == 23802 and known == 4081 and missing == 1, "raw_provider_census_differs")
    summary = result["provider"]
    all_usage = summary["all_response_usage"]
    need(summary["upstream_allocations"] == 5 and summary["cumulative_request_bytes"] == request_bytes
         and summary["observed_usage_tokens"] == known and summary["successful_provider_responses"] == 4,
         "closing_provider_summary_differs")
    need(all_usage["known_reported_tokens"] == known
         and all_usage["allocations_with_unmeasured_usage"] == missing
         and all_usage["fully_measured"] is False and all_usage["unknown_usage_is_zero"] is False,
         "all_response_usage_unknown_boundary_differs")
    refusals = [json.loads(line) for line in raw("extracted/execution/provider/local-refusals.jsonl").splitlines()]
    need(len(refusals) == 2 and all(row["time"] > finished[4]["time"] for row in refusals), "owned_refusal_order_differs")
    need(summary["failed"] is True and summary["stopped"] is True, "upstream_failure_stop_not_retained")
    limits = plan["limits"]
    need(5 < limits["upstream_calls_including_smoke"] and request_bytes < limits["maximum_total_request_bytes"]
         and known < limits["maximum_observed_usage_tokens_before_stopping"], "unexpected_budget_exhaustion")
    drain = obj("extracted/execution/provider-drain.json")
    need(drain == result["provider_drain"] and drain["active_handlers_at_capture_freeze"] == 0
         and drain["unclosed_allocation_ids"] == [] and drain["all_handlers_completed"] is True,
         "provider_drain_incomplete_or_differs")
    case = result["cases"][0]
    cleanup = case["process_cleanup"]
    need(len(cleanup) == 4 and all(row["reaped"] and row["cleanup_error_type"] is None for row in cleanup), "recorded_child_cleanup_incomplete")
    service_logs = []
    for service in ("merchant", "credentials", "processor"):
        text = raw(prefix + service + ".stdout.log").decode()
        starts = [int(value) for value in re.findall(r"Started server process \[(\d+)\]", text)]
        stops = [int(value) for value in re.findall(r"Finished server process \[(\d+)\]", text)]
        need(len(starts) == 1 and starts == stops and starts[0] in {row["pid"] for row in cleanup}, "native_service_PID_lifecycle_differs")
        card = raw(prefix + service + ".agent-card.json")
        need(digest(card) == launch["public_cards"][service], "native_public_card_hash_differs")
        service_logs.append({"service": service, "started_PID": starts[0], "finished_PID": stops[0],
                             "logged_card_GET_200_count": len(re.findall(r'GET .*agent-card\.json HTTP/1\.1" 200 OK', text)),
                             "logged_POST_count": len(re.findall(r'"POST ', text))})
    worker = obj(prefix + "shopper/worker-result.json")
    need(worker["original_remote_http_clients_closed"] == [True, True], "original_remote_client_close_not_retained")
    separation = obj(prefix + "shopper/actor-input-separation.json")
    need(separation["denials"] == {"private_reads": 0, "external_network": 2, "descendants": 0}, "actor_denial_count_differs")
    port_preflight = [json.loads(line) for line in raw(prefix + "native-port-preflight.jsonl").splitlines()]
    return {
        "schema_version": "ap2-native-shopper-v4-provider-lifecycle-independent-review/1",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "retained_provider_runtime_lifecycle_consistent_at_stated_scope",
        "run_id": EXPECTED_RUN, "head_sha": EXPECTED_HEAD, "archive_identity": archive_identity,
        "API_digest_matches_reconstructed_archive": True, "archive_and_extracted_files_verified": 48,
        "provider": {"upstream_allocations": 5, "access_smoke_allocation_included": 0,
                     "shopper_generation_allocations": 4, "HTTP_status_counts": dict(statuses),
                     "request_bytes": request_bytes, "known_reported_tokens": known,
                     "responses_with_missing_usage": missing, "unknown_usage_is_zero": False,
                     "observations": rows, "returned_model_version_counts": dict(models),
                     "owned_refusals_after_upstream_failure": refusals,
                     "owned_refusal_reason": "Prior failure branch inferred from bound proxy code and available call/byte/token budget, separately from the captured upstream503.",
                     "drain": drain},
        "runtime": {"python_version": runtime["python_version"], "actual_distribution_count": len(runtime["distributions"]),
                    "required_versions_checked": len(plan["versions"]), "pip_report_install_count": len(pip["install"]),
                    "runtime_inventory_file_count": len(runtime["files"]), "actual_required_versions_match": True,
                    "runtime_physical_files_independently_rehashed": False,
                    "verification_limit": "Bound recorded inventory/version metadata and pip report; actual hosted venv files are not retained for post-run physical rehashing."},
        "worker_public_facts": {"selected_worker": worker_name, "snapshot_identity": digest(worker_raw),
                              "all_exact_typed_fields_match_plan_and_actual_public_facts": True,
                              "delta_from_prior_worker": "Exact changes to case ID and result schema only",
                              "source_derived_preflight_order": "Before provider smoke; receipt itself has no timestamp"},
        "source_binding": {"owned_source_snapshots_checked": len(plan["owned_sources"]),
                           "original_AP2_source_hash_declarations": len(plan["sources"]),
                           "original_x402_source_hash_declarations": len(plan["x402_sources"]),
                           "root_import_matches_private_copy_path_and_plan_hash": True,
                           "original_source_physical_bytes_independently_rehashed": False,
                           "full_installed_runtime_or_capture_authentication_claimed": False},
        "lifecycle": {"recorded_children": cleanup, "all_recorded_children_reaped": True,
                      "native_services": service_logs, "remote_HTTP_clients_closed": [True, True],
                      "explicit_official_Runner_close_recorded": False,
                      "port_preflight": port_preflight,
                      "native_PID_listener_ownership": "Source-bound declared check plus public-card/stdout/reap reconciliation; no retained /proc FD/socket-inode snapshot for independent post-run reconstruction."},
        "owned_actor_guard": {"recorded_denials": separation["denials"],
                            "source_behavior": "Audits socket connect/getaddrinfo/sendto against str loopback hosts and native/proxy ports; rejects other values.",
                            "denied_socket_argument_values_retained": False,
                            "exact_argument_mismatch_established": False,
                            "claim_limit": "Two owned actor socket denials are separate from upstream503 and proxy429; Python audit controls are not an OS hostile-code sandbox."},
        "material_consistency_questions": [],
        "whole_task_grade": None, "human_gold_qualified": False,
        "workflow_success_implies_task_success": False,
        "original_application_SDK_provider_execution_by_reviewer": 0,
        "Git_actions_by_reviewer": 0, "evidence_identities": evidence,
        "reviewer_source": {"path": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"), **digest(Path(__file__).read_bytes())},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_BASE.parent / "provider-lifecycle-independent-review-v1.json")
    args = parser.parse_args()
    report = review(args.base.resolve())
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "provider_allocations": 5, "known_tokens": 4081,
                      "unknown_usage_responses": 1, "request_bytes": 23802, "recorded_children_reaped": 4}))
