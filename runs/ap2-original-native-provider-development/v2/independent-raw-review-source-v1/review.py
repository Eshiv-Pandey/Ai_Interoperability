"""Read retained AP2 native/provider V2 evidence using only the Python stdlib.

No original app, SDK, actor, model, solver, evaluator or checker is imported.
The five-case census is fixed; missing/failed/partial observations stay visible.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit
import zipfile


ROOT = Path(__file__).resolve().parents[4]
EXPECTED_HEAD = "5f8ef7c8948c0a4a89b665810968cc4d5a734cda"
EXPECTED_RUN = 42995902326
STAGE_SHA = "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463"
ENV_SHA = "4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5"
MODEL = "gemini-3.1-flash-lite-preview"
API_PATH = "/v1beta/models/" + MODEL + ":generateContent"
CASE_NAMES = ("correct-reply", "wrong-reply", "no-reply", "foreign-context-recovery", "repeat-completed")
ENTRIES = (
    {"module": "roles.merchant_agent", "port": 8001, "rpc_path": "/a2a/merchant_agent"},
    {"module": "roles.credentials_provider_agent", "port": 8002, "rpc_path": "/a2a/credentials_provider"},
    {"module": "roles.merchant_payment_processor_agent", "port": 8003, "rpc_path": "/a2a/merchant_payment_processor_agent"},
)
SERVICE_NAMES = ("merchant", "credentials", "processor")


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key:" + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_json:" + value)))


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def record(path):
    return {"path": str(path), **digest(path.read_bytes())}


def equal(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def source_literal(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("source_literal_missing:" + name)


def receipts(task):
    if type(task) is not dict:
        return []
    return [part["data"]["ap2.PaymentReceipt"]
            for artifact in task.get("artifacts") or [] for part in artifact.get("parts") or []
            if type(part.get("data")) is dict and "ap2.PaymentReceipt" in part["data"]]


def challenge(task):
    if type(task) is not dict:
        return None
    values = [part["data"]["challenge"] for part in (task.get("status", {}).get("message") or {}).get("parts") or []
              if type(part.get("data")) is dict and "challenge" in part["data"]]
    if task.get("status", {}).get("state") == "input-required" and len(values) == 1 and type(values[0]) is dict and values[0].get("type") == "otp" and type(values[0].get("display_text")) is str:
        return values[0]
    return None


class Audit:
    def __init__(self, capture):
        self.capture = capture
        self.issues, self.evidence = [], {}

    def need(self, condition, reason):
        if not condition:
            self.issues.append(reason)
        return bool(condition)

    def json(self, path, required=True):
        if not path.is_file():
            if required:
                self.issues.append("missing_file:" + str(path))
            return None
        raw = path.read_bytes()
        self.evidence[str(path)] = digest(raw)
        try:
            return strict(raw)
        except (ValueError, UnicodeDecodeError) as error:
            self.issues.append("invalid_json:" + str(path) + ":" + type(error).__name__)
            return None

    def lines(self, path, required=True):
        if not path.is_file():
            if required:
                self.issues.append("missing_file:" + str(path))
            return []
        raw = path.read_bytes()
        self.evidence[str(path)] = digest(raw)
        result = []
        for index, line in enumerate(raw.splitlines()):
            try:
                result.append(strict(line))
            except (ValueError, UnicodeDecodeError):
                self.issues.append("invalid_jsonl:" + str(path) + ":" + str(index + 1))
        return result

    def raw(self, path):
        if not path.is_file():
            return None
        raw = path.read_bytes()
        self.evidence[str(path)] = digest(raw)
        return raw

    def binding(self, path, expected):
        raw = self.raw(path)
        return self.need(raw is not None and digest(raw) == {key: expected.get(key) for key in ("bytes", "sha256")}, "file_binding_mismatch:" + str(path))

    def source(self, plan):
        stage_path = ROOT / "runs/ap2-environment-preparation/source-stage-v1/manifest.json"
        env_path = ROOT / "runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json"
        stage, env = self.json(stage_path), self.json(env_path)
        self.need(record(stage_path)["sha256"] == STAGE_SHA, "source_manifest_sha_mismatch")
        self.need(record(env_path)["sha256"] == ENV_SHA, "environment_manifest_sha_mismatch")
        self.need(plan.get("source_stage_sha256") == STAGE_SHA and plan.get("original_windows_environment_sha256") == ENV_SHA, "plan_original_manifest_bindings_mismatch")
        counts = {}
        for project, directory, key, count in (("ap2", "ap2", "sources", 136), ("a2a-x402", "a2a-x402", "x402_sources", 24)):
            wanted = {row["path"]: {k: row[k] for k in ("bytes", "sha256")} for row in stage["files"] if row["project"] == project}
            tree = stage_path.parent / directory
            actual = {p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file() and p.suffix != ".pyc" and "__pycache__" not in p.parts}
            self.need(len(wanted) == count and actual == set(wanted), "original_tree_membership_mismatch:" + project)
            self.need(equal(plan.get(key), wanted), "plan_source_census_mismatch:" + project)
            for name, expected in wanted.items():
                self.binding(tree / name, expected)
            counts[project] = len(wanted)
        excluded = {"ap2", "ap2-samples", "x402-a2a", "pywin32", "pywin32-ctypes", "wmi"}
        versions = {normalized(name): row["version"] for name, row in env["all_distributions"].items() if name.lower() not in excluded}
        self.need(equal(plan.get("versions"), versions), "plan_required_versions_mismatch")
        self.need(len(versions) == 182, "required_versions_count_mismatch")
        owned = plan.get("owned_sources", {})
        expected_owned = {"scripts/run_ap2_original_native_provider_v2.py", "scripts/ap2_public_scripted_continuation_v2.py", "src/interoperability/ap2_public_scripted_continuation_v2.py", "src/interoperability/ap2_public_task_read_v1.py", "src/interoperability/ap2_public_original_binding_v2.py"}
        self.need(set(owned) == expected_owned, "plan_owned_membership_mismatch")
        for name, expected in owned.items():
            if name in expected_owned:
                self.binding(ROOT / name, expected)
        return {"source_census": counts, "required_versions": len(versions), "owned_sources": owned,
                "verification_limit": "Current retained local source bytes match frozen plan; capture/runtime authenticity is not independently attested."}

    def runtime(self, plan, execution, result):
        path = execution / "portable-runtime.json"
        runtime = self.json(path, required=False)
        if runtime is None:
            return {"status": "not_captured", "original_runtime_executed_by_reviewer": False}
        self.need(record(path)["sha256"] == result.get("portable_runtime_sha256"), "closing_portable_runtime_sha_mismatch")
        self.need(runtime.get("source_stage_sha256") == STAGE_SHA and runtime.get("original_windows_environment_sha256") == ENV_SHA, "portable_runtime_original_binding_mismatch")
        self.need(equal(runtime.get("required_original_versions"), plan.get("versions")), "portable_required_versions_mismatch")
        actual = runtime.get("distributions", {})
        for name, version in plan.get("versions", {}).items():
            self.need(actual.get(name) == version, "actual_distribution_version_mismatch:" + name)
        report_path = self.capture / "pip-install-report.json"
        self.binding(report_path, runtime.get("pip_report", {}))
        pip = self.json(report_path)
        install = pip.get("install", []) if pip else []
        for row in install:
            name = normalized(row["metadata"]["name"])
            version = row["metadata"]["version"]
            self.need(actual.get(name) == version, "pip_report_actual_distribution_mismatch:" + name)
            if name in plan.get("versions", {}):
                self.need(plan["versions"][name] == version, "pip_report_pinned_version_mismatch:" + name)
        pip_check = self.raw(self.capture / "pip-check.txt")
        self.need(pip_check is not None and b"No broken requirements found" in pip_check, "pip_check_missing_or_adverse")
        return {"status": "captured", "python_executable": runtime.get("python_executable"), "python_version": runtime.get("python_version"),
                "runtime_root": runtime.get("root"), "actual_distribution_count": len(actual), "required_distribution_count": len(plan.get("versions", {})),
                "runtime_inventory_file_count": len(runtime.get("files", {})), "pip_report_install_count": len(install),
                "pip_report_bytes": record(report_path), "inventory_hash": record(path),
                "compiled_windows_wheel_hashes_apply_to_linux": runtime.get("compiled_windows_wheel_hashes_apply_to_linux"),
                "verification_limit": "Actual distributions and imported hashes are reconstructed from captures; the hosted venv physical files are not retained for independent post-run rehashing."}, runtime

    def provider(self, execution, result):
        folder = execution / "provider"
        ledger = self.lines(folder / "ledger.jsonl", required=False)
        local = self.lines(folder / "local-refusals.jsonl", required=False)
        if not ledger:
            self.need(result.get("provider", {}).get("upstream_allocations", 0) == 0, "provider_summary_has_allocations_without_raw_ledger")
            return {"allocations": 0, "ledger_rows": 0, "local_refusals": len(local), "responses": []}
        starts = [row for row in ledger if row.get("phase") == "started"]
        finished = [row for row in ledger if row.get("phase") == "finished"]
        self.need([r.get("allocation") for r in starts] == list(range(len(starts))), "provider_allocation_order_or_identity_mismatch")
        self.need(len(starts) <= 80, "provider_hard_call_cap_exceeded")
        rows, request_bytes, usage_sum, unknown, accepted200 = [], 0, 0, 0, 0
        previous_sticky = False
        for index, start in enumerate(starts):
            terminal = [row for row in finished if row.get("allocation") == index]
            self.need(len(terminal) == 1, "provider_allocation_missing_or_duplicate_finish:" + str(index))
            self.need(start.get("provider_mode") == "live" and start.get("path") == API_PATH and start.get("retry") is False and start.get("upstream_call_consumed") is True, "provider_started_authority_or_mode_mismatch:" + str(index))
            request_path, response_path = folder / f"{index:03d}.request.json", folder / f"{index:03d}.response.json"
            raw_request = self.raw(request_path)
            self.need(raw_request is not None and len(raw_request) <= 131072, "provider_request_missing_or_oversize:" + str(index))
            if raw_request is None:
                continue
            request_bytes += len(raw_request)
            self.binding(request_path, start.get("request", {}))
            request = self.json(request_path)
            self.need(type(request) is dict and "contents" in request, "provider_request_payload_invalid:" + str(index))
            if not terminal:
                rows.append({"allocation": index, "status": "unfinished_raw_allocation"})
                continue
            finish = terminal[0]
            self.need(finish.get("upstream_call_consumed") is True, "provider_finish_not_consumed:" + str(index))
            body = self.raw(response_path)
            self.need(body is not None and len(body) <= 1048576, "provider_response_missing_or_oversize:" + str(index))
            self.binding(response_path, finish.get("response", {}))
            status, problem = finish.get("http_status"), finish.get("transport_error_type")
            parsed, decoding = None, None
            try:
                parsed = strict(body) if body is not None else None
            except (ValueError, UnicodeDecodeError):
                decoding = "non_json_received_body"
            total = parsed.get("usageMetadata", {}).get("totalTokenCount") if type(parsed) is dict and type(parsed.get("usageMetadata", {})) is dict else None
            self.need(not previous_sticky, "provider_send_after_sticky_failure_unknown_usage_or_token_stop:" + str(index))
            if status == 200 and problem is None:
                accepted200 += 1
                if type(total) is not int or total <= 0:
                    unknown += 1
                    total_for_sum = 0
                    previous_sticky = True
                else:
                    total_for_sum = total
            elif type(total) is int and total >= 0:
                total_for_sum = total
            else:
                total_for_sum = 0
            usage_sum += total_for_sum
            if status != 200 or problem is not None or usage_sum >= 100000:
                previous_sticky = True
            self.need(finish.get("observed_cumulative_usage_tokens") == usage_sum, "provider_raw_usage_running_sum_mismatch:" + str(index))
            calls = [part.get("functionCall") for candidate in (parsed or {}).get("candidates", []) for part in candidate.get("content", {}).get("parts", []) if type(part) is dict and "functionCall" in part] if type(parsed) is dict else []
            rows.append({"allocation": index, "ledger_start": start.get("time"), "ledger_finish": finish.get("time"),
                         "http_status": status, "transport_error_type": problem, "body_decoding": decoding,
                         "requested_model_path": API_PATH, "returned_model_version": parsed.get("modelVersion") if type(parsed) is dict else None,
                         "raw_usage_metadata": parsed.get("usageMetadata") if type(parsed) is dict else None,
                         "raw_reported_total_tokens": total, "recomputed_cumulative_usage_tokens": usage_sum,
                         "request_bytes": len(raw_request), "response_bytes": len(body) if body is not None else None,
                         "function_call_names": [call.get("name") for call in calls if type(call) is dict],
                         "response_observation": "received_body_retained" if problem is None else "failure_or_received_adverse_body_with_owned_transport_disposition"})
        expected = result.get("provider", {})
        for key, actual in (("upstream_allocations", len(starts)), ("cumulative_request_bytes", request_bytes), ("observed_usage_tokens", usage_sum), ("responses_with_unknown_usage", unknown), ("successful_provider_responses", accepted200)):
            self.need(expected.get(key) == actual, "provider_closing_summary_mismatch:" + key)
        self.need(request_bytes <= 200000, "provider_hard_total_request_byte_cap_exceeded")
        self.need(len(ledger) == len(starts) + len(finished) and len(finished) == len(starts), "provider_ledger_census_mismatch")
        physical = {p.name for p in folder.glob("*.request.json")} | {p.name for p in folder.glob("*.response.json")}
        wanted = {f"{index:03d}.{kind}.json" for index in range(len(starts)) for kind in ("request", "response")}
        self.need(physical == wanted, "provider_raw_file_membership_mismatch")
        gaps = [(datetime.fromisoformat(b["time"]) - datetime.fromisoformat(a["time"])).total_seconds() for a, b in zip(starts, starts[1:])]
        return {"allocations": len(starts), "ledger_rows": len(ledger), "local_refusals": len(local), "request_bytes": request_bytes,
                "observed_usage_tokens": usage_sum, "successful_provider_responses": accepted200, "unknown_usage_responses": unknown,
                "http_status_counts": dict(Counter(str(row.get("http_status")) for row in rows)), "minimum_recorded_start_gap_seconds": min(gaps) if gaps else None,
                "usage_threshold_is_post_response_not_hard_token_or_cost_ceiling": True, "provider_attribution": "global allocation ledger; no unsupported per-case assignment", "responses": rows}

    def case(self, facts, parent, execution, runtime):
        case_id = facts["case_id"]
        folder = execution / "cases" / case_id
        row = {"case_id": case_id, "declared_public_facts": facts, "parent_status": parent.get("status", "missing_closing_case"),
               "parent_reason": parent.get("reason"), "parent_error": parent.get("error"), "case_directory_present": folder.is_dir(), "whole_task_grade": None}
        if not folder.is_dir():
            row.update(disposition="unexecuted_or_missing_capture", public_receipts=[], public_otp_challenge=None)
            return row
        public = self.json(folder / (case_id + ".public-human-facts.json"), required=False)
        self.need(equal(public, facts), "case_public_facts_binding_mismatch:" + case_id)
        native = self.json(folder / "native-launch.json", required=False)
        preflight = self.lines(folder / "native-port-preflight.jsonl", required=False)
        for entry in preflight:
            self.need(entry.get("foreign_service_contacted") is False, "native_port_probe_foreign_contact_claim:" + case_id)
            self.need(entry.get("status") in {"bind_only_reuseaddr_preflight_passed", "bind_only_reuseaddr_preflight_refused"}, "native_port_probe_unknown_status:" + case_id)
            if entry.get("status") == "bind_only_reuseaddr_preflight_passed":
                self.need(entry.get("ports") == [8001, 8002, 8003], "native_port_probe_success_census_mismatch:" + case_id)
            else:
                error = entry.get("error")
                self.need(entry.get("port") in {8001, 8002, 8003} and type(error) is dict and type(error.get("type")) is str and bool(error.get("type")) and (error.get("errno") is None or type(error.get("errno")) is int), "native_port_probe_refusal_observation_invalid:" + case_id)
        row["native_port_preflight_receipts"] = preflight
        cards = []
        if native:
            self.need(bool(preflight) and preflight[-1].get("status") == "bind_only_reuseaddr_preflight_passed", "native_launch_without_recorded_passed_port_preflight:" + case_id)
            self.need(equal(native.get("entries"), list(ENTRIES)), "native_entrypoint_census_mismatch:" + case_id)
            self.need(native.get("original_entrypoints") is True and native.get("original_genai_client_replaced") is False and native.get("secret_in_children") is False, "native_treatment_flag_mismatch:" + case_id)
            self.need(native.get("exact_native_pid_listener_ownership_verified_before_card_requests") is True, "native_pid_listener_ownership_declaration_missing:" + case_id)
            row["native_pid_listener_ownership_declared"] = native.get("exact_native_pid_listener_ownership_verified_before_card_requests")
            row["native_pid_listener_ownership_evidence_limit"] = "Source-bound declaration and stdout/card/reap reconciliation; no live /proc FD/inode snapshot is retained."
            for name, expected in zip(SERVICE_NAMES, ENTRIES):
                path = folder / (name + ".agent-card.json")
                card = self.json(path)
                self.binding(path, native.get("public_cards", {}).get(name, {}))
                endpoint = urlsplit(card.get("url", "")) if card else urlsplit("")
                valid = card is not None and card.get("protocolVersion") == "0.3.0" and endpoint.scheme == "http" and endpoint.hostname in {"localhost", "127.0.0.1"} and endpoint.port == expected["port"] and endpoint.path == expected["rpc_path"] and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment
                self.need(valid, "native_public_card_endpoint_mismatch:" + case_id + ":" + name)
                extensions = card.get("capabilities", {}).get("extensions", []) if card else []
                self.need(any(extension.get("uri") == "https://github.com/google-agentic-commerce/ap2/v1" and extension.get("required") is True for extension in extensions), "native_card_original_extension_missing:" + case_id + ":" + name)
                cards.append({"service": name, "name": card.get("name") if card else None, "url": card.get("url") if card else None, "protocol_version": card.get("protocolVersion") if card else None, "endpoint_valid": valid, "extensions": extensions})
        row["native_public_cards"] = cards
        cleanup = parent.get("process_cleanup", [])
        row["process_cleanup"] = cleanup
        row["all_recorded_processes_reaped"] = all(entry.get("reaped") is True for entry in cleanup) if cleanup else None
        row["recorded_process_count"] = len(cleanup)
        row["process_cleanup_status"] = "no_child_processes_recorded" if not cleanup else ("all_recorded_children_reaped" if all(entry.get("reaped") is True for entry in cleanup) else "unreaped_recorded_child_or_cleanup_failure")
        row["native_watch_bytes"] = digest(self.raw(folder / "original-watch.log")) if (folder / "original-watch.log").is_file() else None
        launches = []
        for name in (*SERVICE_NAMES, "caller"):
            raw = self.raw(folder / (name + ".stdout.log"))
            if name in SERVICE_NAMES and raw is not None:
                text = raw.decode("utf-8", errors="replace")
                started = re.findall(r"Started server process \[(\d+)\]", text)
                finished = re.findall(r"Finished server process \[(\d+)\]", text)
                card_gets = re.findall(r'"GET ([^ ]+) HTTP/1.1" 200 OK', text)
                launches.append({"service": name, "server_started_pids": [int(pid) for pid in started], "server_finished_pids": [int(pid) for pid in finished], "successful_public_card_get_paths": card_gets, "logged_post_request_count": len(re.findall(r"\bPOST\b", text))})
                for pid in started:
                    self.need(any(entry.get("pid") == int(pid) and entry.get("reaped") is True for entry in cleanup), "native_stdout_pid_missing_successful_reap:" + case_id + ":" + pid)
        row["native_service_stdout_observations"] = launches
        caller = self.json(folder / "caller/result.json", required=False)
        log = self.lines(folder / "caller/actor-public-events.jsonl", required=False)
        if not caller:
            caller_log = self.raw(folder / "caller.stdout.log")
            traceback = caller_log.decode("utf-8", errors="replace") if caller_log else None
            binding_failure = bool(traceback and "BindingError:" in traceback and "bind_original_modules" in traceback)
            starts = [entry for entry in log if entry.get("kind") == "original-call-start"]
            terminals = [entry for entry in log if entry.get("kind") in {"original-call-return", "original-call-error"}]
            task_terminals = [entry for entry in log if entry.get("kind") in {"public-task-read-return", "public-task-read-error"}]
            observed_tasks = [entry.get("public_observation") or entry.get("refused_public_observation") for entry in task_terminals]
            observed_tasks = [entry["task"] for entry in observed_tasks if type(entry) is dict and type(entry.get("task")) is dict]
            initial = next((entry["public_observation"]["task"] for entry in task_terminals if entry.get("phase") == "initial-payment-task" and "public_observation" in entry), None)
            final_raw = next((entry["public_observation"]["task"] for entry in reversed(task_terminals) if entry.get("phase") in {"waiting-payment-task", "after-original-otp"} and "public_observation" in entry), None)
            final_receipts = receipts(final_raw)
            completed = type(final_raw) is dict and final_raw.get("status", {}).get("state") == "completed" and len(final_receipts) == 1
            row.update(disposition="native_ready_then_caller_structural_binding_failure_before_business_capture" if native and binding_failure else ("failed_launch_attempt_before_any_recorded_child" if not native and not cleanup and parent.get("status") == "executed_launch_or_readiness_failure_retained" else ("partial_raw_business_or_public_task_capture_without_terminal_actor_result" if starts or observed_tasks else "started_attempt_without_terminal_public_capture")), caller_status=None, caller_traceback=traceback, caller_failed_at_source_binding_before_construction=binding_failure,
                       business_call_capture_count=len(starts), original_business_call_phases=[entry.get("phase") for entry in starts],
                       raw_business_call_starts=starts, raw_business_call_terminals=terminals,
                       raw_business_calls_without_terminal=[entry for entry in starts if not any(other.get("index") == entry.get("index") for other in terminals)],
                       original_business_call_errors=[entry for entry in terminals if entry.get("kind") == "original-call-error"],
                       actor_result_present=False, public_task_capture_count=len(observed_tasks), raw_public_task_terminals=task_terminals,
                       public_pending_task=initial, public_final_task=final_raw, public_receipts=final_receipts,
                       actual_completed_public_receipt_observed=completed, public_otp_challenge=challenge(initial), raw_public_event_count=len(log),
                       repeated_public_observations=[entry for entry in log if entry.get("kind") == "public-repeat-observation"],
                       later_launch_failure_cause_limit="Retained sanitized errno/message observations are reported without inferring an unrecorded underlying socket state." if parent.get("reason") == "OSError" and not cleanup else None)
            return row
        self.need(caller.get("case_id") == case_id and equal(caller.get("public_human_facts"), facts), "caller_case_facts_mismatch:" + case_id)
        self.need(caller.get("grade") is None and caller.get("evaluator_or_private_journal_inputs") == [], "caller_gold_or_grade_claim_changed:" + case_id)
        self.need(caller.get("owned_caller_and_public_read_intervention") is True and caller.get("unchanged_adk_root_tool_qualification") is False, "caller_intervention_flags_mismatch:" + case_id)
        imports = caller.get("imported_environment", {})
        for name, sha in imports.items():
            self.need(runtime.get("files", {}).get(name, {}).get("sha256") == sha, "caller_imported_runtime_hash_mismatch:" + case_id + ":" + name)
        if runtime:
            self.need(caller.get("environment_sha256") == record(execution / "portable-runtime.json")["sha256"], "caller_portable_environment_binding_mismatch:" + case_id)
        modules = source_literal(ROOT / "src/interoperability/ap2_public_scripted_continuation_v2.py", "MODULES")
        for name, source in caller.get("source_records", {}).items():
            wanted = ROOT / "runs/ap2-environment-preparation/source-stage-v1/ap2/code/samples/python/src" / modules[name]
            self.need(source.get("sha256") == record(wanted)["sha256"] and source.get("original_function_bodies_verified") is True, "caller_original_source_binding_mismatch:" + case_id + ":" + name)
        self.need(set(caller.get("source_records", {})) == set(modules), "caller_original_source_membership_mismatch:" + case_id)
        row["structural_source_binding_status"] = "ten_source_bound_modules_report_original_function_bodies_verified"
        row["structural_binding_evidence_limit"] = "Original module hashes and source-bound verifier status are retained; per-function code-object fingerprints are not dumped."
        calls, events, reads = caller.get("original_business_calls", []), caller.get("actor_public_events", []), caller.get("public_task_reads", [])
        for call in calls:
            terminal = [entry for entry in log if entry.get("kind") in {"original-call-return", "original-call-error"} and entry.get("index") == call.get("index")]
            self.need(len(terminal) == 1 and equal({k: v for k, v in terminal[0].items() if k != "kind"}, call), "caller_raw_call_terminal_mismatch:" + case_id + ":" + str(call.get("index")))
        for event in events:
            self.need(any(equal(event, entry) for entry in log), "caller_raw_actor_event_missing:" + case_id + ":" + str(event.get("index")))
        terminals = [{k: v for k, v in entry.items() if k != "kind"} for entry in log if entry.get("kind") in {"public-task-read-return", "public-task-read-error"}]
        self.need(equal(terminals, reads), "caller_raw_public_read_census_mismatch:" + case_id)
        for read in reads:
            observation = read.get("public_observation") or read.get("refused_public_observation")
            if observation:
                task, query = observation.get("task", {}), observation.get("query", {})
                self.need(task.get("id") == query.get("id") and query.get("historyLength") == 100, "public_get_task_query_reply_id_mismatch:" + case_id + ":" + read.get("phase", ""))
        pending, final = caller.get("public_pending_task"), caller.get("public_final_task")
        public_tasks = [read.get("public_observation", {}).get("task") for read in reads if "public_observation" in read]
        if pending is not None:
            self.need(any(equal(pending, task) for task in public_tasks), "caller_pending_not_in_raw_public_reads:" + case_id)
        if final is not None:
            self.need(any(equal(final, task) for task in public_tasks), "caller_final_not_in_raw_public_reads:" + case_id)
        for event in events:
            if event.get("kind") == "human-cart-selection":
                offered = event.get("offered", [])
                self.need(len(offered) > facts["cart_index"] and equal(event.get("selected"), offered[facts["cart_index"]]), "human_cart_offered_index_selection_mismatch:" + case_id)
            if event.get("kind") == "human-payment-selection":
                offered = event.get("offered", {}).get("payment_method_aliases", [])
                self.need(len(offered) > facts["payment_method_index"] and equal(event.get("selected"), offered[facts["payment_method_index"]]), "human_payment_offered_index_selection_mismatch:" + case_id)
        ch, final_receipts = challenge(pending), receipts(final)
        completed = type(final) is dict and final.get("status", {}).get("state") == "completed" and len(final_receipts) == 1
        repeats = [event for event in events if event.get("kind") == "public-repeat-observation"]
        if caller.get("status") == "completed_with_public_receipt":
            self.need(completed, "caller_completion_status_without_actual_completed_public_receipt:" + case_id)
        for event in events:
            if event.get("kind") == "recover-from-prior-public-task":
                self.need(type(pending) is dict and event.get("task_id") == pending.get("id") and event.get("context_id") == pending.get("contextId"), "authority_recovery_not_bound_to_prior_public_task:" + case_id)
            if event.get("kind") == "adverse-read-disposition":
                adverse = [read for read in reads if read.get("phase") == "adverse-authority-read"]
                if event.get("disposition") == "owned_caller_context_check_refused_actual_public_task":
                    self.need(len(adverse) == 1 and adverse[0].get("error_type") == "PublicTaskAuthorityError" and "refused_public_observation" in adverse[0], "authority_refusal_without_actual_public_context_mismatch:" + case_id)
                elif event.get("disposition") == "original_merchant_task_store_returned_task_not_found":
                    self.need(len(adverse) == 1 and adverse[0].get("public_rpc_error", {}).get("code") == -32001, "authority_refusal_without_actual_task_not_found:" + case_id)
                else:
                    self.issues.append("unexpected_classified_authority_disposition:" + case_id)
        row.update(caller_status=caller.get("status"), caller_error=caller.get("error"), raw_public_event_count=len(log),
                   actor_result_present=True, business_call_capture_count=len(calls), public_task_capture_count=len(public_tasks),
                   original_business_call_count=len(calls), original_business_call_phases=[call.get("phase") for call in calls],
                   original_business_call_errors=[{key: call.get(key) for key in ("index", "phase", "error_type", "error")} for call in calls if "error_type" in call],
                   public_task_read_count=len(reads), public_task_read_errors=[read for read in reads if "error_type" in read],
                   public_pending_task=pending, public_final_task=final, public_otp_challenge=ch,
                   public_receipts=final_receipts, actual_completed_public_receipt_observed=completed,
                   repeated_public_observations=repeats, authority_events=[event for event in events if event.get("kind") in {"received-public-authority-fault", "adverse-read-disposition", "recover-from-prior-public-task", "unexpected-adverse-read-error", "adverse-original-rpc-error"}],
                   imported_environment_file_count=len(imports), denials=caller.get("denials"), audit_probes=caller.get("audit_probes"),
                   public_selection_events=[event for event in events if event.get("kind") in {"human-cart-selection", "human-payment-selection", "human-wallet-consent", "human-cart-confirmation", "explicit-human-otp"}],
                   disposition=("failed_or_partial_case_with_prior_completed_public_receipt" if completed and caller.get("error") else "completed_public_receipt_observed") if completed else ("waiting_for_explicit_human_reply_observed" if facts["otp_response"] is None and ch else "actual_failed_or_partial_original_attempt_retained"))
        return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--run-json", type=Path)
    parser.add_argument("--gate-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh_review_output_directory_required")
    capture = args.capture_root.resolve(strict=True)
    archive = args.archive.resolve(strict=True)
    if record(archive)["sha256"] != args.archive_sha256:
        raise ValueError("root_retained_archive_sha256_binding_mismatch")
    audit = Audit(capture)
    opening = audit.json(capture / "execution/opening.json", required=False)
    result = audit.json(capture / "execution/result.json", required=False) or {}
    plan = audit.json(capture / "plan/plan.json")
    if not plan:
        raise ValueError("retained_prospective_plan_required")
    expected_ids = ["ap2-native-provider-v2-" + name for name in CASE_NAMES]
    facts = plan.get("facts", [])
    audit.need([row.get("case_id") for row in facts] == expected_ids, "fixed_five_case_plan_identity_mismatch")
    audit.need(plan.get("model") == MODEL and plan.get("provider_path") == API_PATH and plan.get("provider_origin") == "https://generativelanguage.googleapis.com", "fixed_provider_authority_model_mismatch")
    audit.need(plan.get("schema_version") == "ap2-original-native-provider-screen/2" and plan.get("linux_native_pid_listener_ownership_required") is True, "V2_frozen_schema_or_listener_ownership_requirement_mismatch")
    audit.need(plan.get("limits", {}).get("upstream_calls_including_smoke") == 80 and plan.get("limits", {}).get("minimum_interval_seconds") == 6.0 and plan.get("limits", {}).get("maximum_total_request_bytes") == 200000 and plan.get("limits", {}).get("maximum_observed_usage_tokens_before_stopping") == 100000, "fixed_provider_bounds_mismatch")
    if opening:
        audit.binding(capture / "plan/plan.json", opening.get("plan", {}))
        audit.need([row.get("case_id") for row in opening.get("prospective_tasks", [])] == expected_ids, "opening_five_case_census_mismatch")
    source = audit.source(plan)
    runtime_value = audit.runtime(plan, capture / "execution", result)
    runtime_summary, runtime = runtime_value if type(runtime_value) is tuple else (runtime_value, {})
    provider = audit.provider(capture / "execution", result)
    smoke = audit.json(capture / "execution/provider-access-smoke.json", required=False)
    if smoke and provider.get("responses"):
        first = provider["responses"][0]
        forced = first.get("http_status") == 200 and "access_check" in first.get("function_call_names", [])
        audit.need(smoke.get("forced_tool_observed") is forced and smoke.get("http_status") == first.get("http_status"), "raw_provider_smoke_summary_mismatch")
    closing_cases = result.get("cases", [])
    if result:
        audit.need([row.get("case_id") for row in closing_cases] == expected_ids and result.get("allocated_task_count") == 5, "closing_five_case_census_mismatch")
        audit.need(result.get("unexecuted_count") == sum(row.get("status") == "unexecuted" for row in closing_cases), "closing_unexecuted_count_mismatch")
    parent = {row["case_id"]: row for row in closing_cases}
    cases = [audit.case(row, parent.get(row["case_id"], {}), capture / "execution", runtime) for row in facts]
    task_ledger = audit.lines(capture / "execution/task-ledger.jsonl", required=False)
    for row in closing_cases:
        if row.get("status") != "unexecuted":
            entries = [entry for entry in task_ledger if entry.get("case_id") == row["case_id"]]
            audit.need(len(entries) == 2 and entries[0].get("status") == "started" and equal(entries[-1], row), "task_started_finished_ledger_mismatch:" + row["case_id"])
    archive_members = {}
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            if member.is_dir():
                continue
            if member.filename in archive_members:
                audit.issues.append("duplicate_archive_member:" + member.filename)
            raw = zipped.read(member)
            archive_members[member.filename] = digest(raw)
            member_path = Path(member.filename)
            audit.need(member_path.suffix.lower() not in {".pem", ".key"} and member_path.name != ".env" and b"PRIVATE KEY-----" not in raw, "private_key_or_credential_file_in_retained_archive:" + member.filename)
    for name, expected in archive_members.items():
        canonical = PurePosixPath(name)
        if canonical.is_absolute() or ".." in canonical.parts or "\\" in name or ":" in name:
            audit.issues.append("noncanonical_archive_member:" + name)
            continue
        path = capture / name
        if not path.is_file():
            suffix = list(capture.glob("*/" + name))
            path = suffix[0] if len(suffix) == 1 else path
        audit.binding(path, expected)
    run_metadata = audit.json(args.run_json) if args.run_json else None
    if run_metadata:
        head = run_metadata.get("head_sha") or run_metadata.get("headSha")
        run_id = run_metadata.get("id") or run_metadata.get("databaseId")
        audit.need(head == EXPECTED_HEAD and int(run_id) == EXPECTED_RUN, "hosted_run_head_or_identity_mismatch")
    retention = audit.json(archive.parent / "retention.json", required=False)
    api_artifacts = audit.json(archive.parent / "github-artifacts.json", required=False)
    manifest = audit.json(archive.parent / "extracted-manifest.json", required=False)
    if retention:
        audit.need(retention.get("archive_sha256") == args.archive_sha256 and retention.get("archive_bytes") == archive.stat().st_size and retention.get("head_sha") == EXPECTED_HEAD and retention.get("run_id") == EXPECTED_RUN and retention.get("extracted_files") == len(archive_members), "root_retention_binding_or_census_mismatch")
    if api_artifacts:
        artifacts = api_artifacts.get("artifacts", [])
        matches = [entry for entry in artifacts if entry.get("digest") == "sha256:" + args.archive_sha256 and entry.get("size_in_bytes") == archive.stat().st_size and entry.get("workflow_run", {}).get("id") == EXPECTED_RUN and entry.get("workflow_run", {}).get("head_sha") == EXPECTED_HEAD]
        audit.need(len(matches) == 1 and len(artifacts) == 1, "api_artifact_digest_run_identity_or_census_mismatch")
    if manifest:
        listed = {entry["path"]: {key: entry[key] for key in ("bytes", "sha256")} for entry in manifest.get("files", [])}
        audit.need(equal(listed, archive_members), "root_extracted_manifest_vs_raw_zip_member_mismatch")
    gate = audit.json(args.gate_report) if args.gate_report else None
    report = {"schema_version": "ap2-original-native-provider-independent-raw-review/2",
              "completed_at": datetime.now(timezone.utc).isoformat(), "expected_hosted_run_id": EXPECTED_RUN, "expected_head_sha": EXPECTED_HEAD,
              "root_retained_archive": record(archive), "archive_member_count": len(archive_members), "capture_root": str(capture),
              "review_source": record(Path(__file__)), "run_metadata_present": run_metadata is not None,
              "root_retention": retention, "api_artifact_binding_checked": api_artifacts is not None,
              "status": "raw_evidence_consistent_with_explicit_observed_failures_and_limits" if not audit.issues else "raw_review_integrity_questions_retained",
              "integrity_issues": audit.issues, "source_and_version_bindings": source, "runtime": runtime_summary,
              "provider": provider, "provider_access_smoke": smoke, "opening_present": opening is not None, "closing_present": bool(result),
              "actual_returned_model_version_counts": dict(Counter(str(row.get("returned_model_version")) for row in provider.get("responses", []))),
              "closing_failure_type": result.get("failure_type"), "five_declared_cases": cases,
              "case_disposition_counts": dict(Counter(row["disposition"] for row in cases)),
              "failed_task_attempt_count": sum(row.get("parent_status") in {"executed_nonzero_retained", "executed_launch_or_readiness_failure_retained", "executed_timeout_retained"} for row in cases),
              "captured_original_business_call_count": sum(row.get("business_call_capture_count", 0) for row in cases),
              "actor_result_capture_count": sum(row.get("actor_result_present", False) for row in cases),
              "public_task_capture_count": sum(row.get("public_task_capture_count", 0) for row in cases),
              "recorded_child_process_count": sum(row.get("recorded_process_count", 0) for row in cases),
              "actual_public_completed_receipt_case_count": sum(row.get("actual_completed_public_receipt_observed", False) for row in cases),
              "gate_report_present": gate is not None, "gate_report_schema": gate.get("schema_version") if gate else None,
              "captured_evidence": audit.evidence, "original_app_sdk_model_actor_solver_evaluator_checker_imports_or_executions": 0, "provider_requests_by_reviewer": 0,
              "interventions": ["Owned HTTP base URL accounting proxy and upstream credential/transport handling.", "Owned scripted caller invokes source-bound original business functions instead of autonomous ADK shopper.", "Prospective public offered cart/payment option index zero, wallet consent, cart confirmation and OTP replies are supplied by the owned caller.", "Owned original public SDK get_task read surface and authority recovery from prior returned public Task; no private journal/evaluator answer.", "Fresh original native state/keys/CWD per case; fixed native ports and explicit service readiness/cleanup."],
              "limitations": ["Consistency of retained raw captures does not independently authenticate provider/service provenance.", "Provider allocations are global unless raw evidence supports individual attribution.", "Native PID/socket ownership and original code verification are source-bound declarations; live /proc snapshots and per-function code-object fingerprints are not retained.", "A completed public receipt is an observed original Task artifact, not human-qualified gold or a whole-task semantic grade.", "Repeated continuation does not establish idempotency, durability or absence of duplicate hidden effects.", "Actual runtime inventory/pip/import bindings do not establish Windows wheel fidelity or permit post-run rehashing of the discarded hosted venv.", "No original run.sh provisioning, unchanged ADK shopper, bridge, untouched holdout, human gold, full-study or scientific checkpoint qualification is granted.", "The observed-token threshold is post-response stopping and is not a hard token/cost ceiling."]}
    args.output.mkdir(parents=True)
    with (args.output / "review.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "issues": len(audit.issues), "cases": len(cases), "provider_allocations": provider["allocations"], "completed_public_receipt_cases": report["actual_public_completed_receipt_case_count"], "review_path": str(args.output / "review.json")}))


if __name__ == "__main__":
    main()
