"""Independent V5 source and real prepared-plan review; no live execution.

Only current owned stdlib plan/analyzer helpers are imported. No original
application, SDK, provider, solver, checker or network control is executed.
"""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "runs/ap2-native-shopper-provider-development/v5/preparation-1"
OUTPUT = Path(__file__).resolve().parent / "review.json"
CASE = "ap2-native-shopper-provider-v5-correct-human"


def need(value, reason):
    if not value:
        raise ValueError(reason)


def identity(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "regular_review_input_required")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(262144):
            digest.update(raw)
            size += len(raw)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function(source, name):
    tree = ast.parse(source)
    node = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    return ast.dump(node, include_attributes=False)


class PreparedRead:
    """Adapt actual prepared byte paths to the future archive's plan prefix."""
    def raw(self, name):
        need(name.startswith("plan/"), "prepared_plan_prefix_required")
        path = BASE / name.removeprefix("plan/")
        need(path.resolve().is_relative_to(BASE.resolve()), "prepared_read_leaves_allocation")
        return path.read_bytes()

    def json(self, name):
        return json.loads(self.raw(name))


def main():
    need(not OUTPUT.exists(), "exclusive_review_output_required")
    names = ["scripts/run_ap2_native_shopper_provider_v5.py", "scripts/ap2_native_shopper_provider_worker_v3.py",
        "scripts/ap2_native_shopper_actor_guard_v5.py", "scripts/analyze_ap2_native_shopper_provider_v5.py",
        "docs/research/ap2-native-shopper-provider-protocol-v5.md", ".github/workflows/ap2-native-shopper-provider-v5.yml",
        "tests/test_ap2_native_shopper_provider_v5.py", "tests/test_analyze_ap2_native_shopper_provider_v5.py",
        "tests/test_ap2_native_shopper_provider_v5_analysis_integration.py"]
    sources_before = [identity(ROOT / name) for name in names]
    prepared_before = [identity(path) for path in sorted(BASE.rglob("*")) if path.is_file()]
    runner = load("scripts/run_ap2_native_shopper_provider_v5.py", "_V5_independent_prepared_runner")
    analyzer = load("scripts/analyze_ap2_native_shopper_provider_v5.py", "_V5_independent_prepared_analyzer")
    plan = runner.check_plan(BASE)
    need(analyzer.check_plan(PreparedRead(), plan) == plan, "corrected_analyzer_does_not_accept_actual_preparation_schema")
    need(runner.CASE_ID == analyzer.CASE == runner.W.public_facts()["case_id"] == CASE, "case_literals_differ")
    limits = plan["limits"]
    expected = {"upstream_calls_including_smoke": 80, "minimum_interval_seconds": 6.0,
        "maximum_total_request_bytes": 200000, "maximum_observed_usage_tokens_before_stopping": 100000,
        "request_timeout_seconds": 120, "maximum_provider_drain_seconds": 150,
        "maximum_public_user_turns": 12, "maximum_ADK_events": 160, "maximum_event_bytes": 262144,
        "worker_timeout_seconds": 600, "screen_timeout_seconds": 900,
        "request_timeout_is_independent_whole_request_wall_cap": False}
    need(limits == expected, "reviewed_provider_or_lifecycle_bounds_changed")
    old_worker = (ROOT / "scripts/ap2_native_shopper_provider_worker_v2.py").read_text(encoding="utf-8")
    worker = (ROOT / "scripts/ap2_native_shopper_provider_worker_v3.py").read_text(encoding="utf-8")
    normalized_worker = worker.replace("ap2-native-shopper-provider-worker/3", "ap2-native-shopper-provider-worker/2")
    for name in ("public_price_check", "public_reply", "visible_final_text", "application"):
        need(function(old_worker, name) == function(normalized_worker, name), "public_actor_or_original_application_function_changed:" + name)
    old_runner = (ROOT / "scripts/run_ap2_native_shopper_provider_v4.py").read_text(encoding="utf-8")
    runner_source = (ROOT / "scripts/run_ap2_native_shopper_provider_v5.py").read_text(encoding="utf-8")
    normalized_runner = runner_source.replace("ap2-native-shopper-provider-result/5", "ap2-native-shopper-provider-result/4").replace(
        "ap2-native-shopper-v5-private-", "ap2-native-shopper-v4-private-")
    need(function(old_runner, "execute") == function(normalized_runner, "execute"), "execution_delta_exceeds_reviewed_schema_and_private_directory_version")
    controls_name = "runs/ap2-native-shopper-provider-development/v5/software-controls-v1/result.json"
    controls = json.loads((ROOT / controls_name).read_bytes())
    need(controls["status"] == "passed" and controls["returncode"] == 0
         and controls["historical_sources_before"] == controls["historical_sources_after"], "retained_loopback_controls_or_history_changed")
    for row in controls["historical_sources_after"]:
        need(identity(ROOT / row["path"]) == row, "historical_V4_file_changed")
    witness_name = "runs/ap2-native-shopper-provider-development/v5/software-controls-v1/real-loopback-transport.json"
    witness = json.loads((ROOT / witness_name).read_bytes())
    need(witness["application_calls"] == witness["provider_calls"] == 0
         and witness["loopback_listeners_closed"] is True
         and witness["denials"]["external_network"] == 3
         and witness["denials"]["network_diagnostics_logged"] == len(witness["diagnostics"]) == 3,
         "retained_real_loopback_witness_differs")
    need(sources_before == [identity(ROOT / name) for name in names]
         and prepared_before == [identity(path) for path in sorted(BASE.rglob("*")) if path.is_file()],
         "source_or_preparation_changed_during_review")
    need(not any(name == "roles" or name.startswith(("roles.", "google.adk", "google.genai")) for name in sys.modules),
         "original_application_or_SDK_imported_by_review")
    value = {"schema_version": "ap2-native-shopper-provider-V5-independent-prospective-source-review/1",
        "status": "reviewed_for_one_bounded_adaptive_development_allocation", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "prepared_plan": identity(BASE / "plan.json"), "prepared_files": prepared_before,
        "reviewed_sources": sources_before, "declared_case": CASE, "declared_case_denominator": 1,
        "limits": expected, "corrected_analyzer_accepts_actual_prepared_identity_dictionary_schema": True,
        "public_actor_and_original_application_function_AST_preserved": True,
        "runner_execute_AST_preserved_after_exact_schema_and_private_directory_version_normalization": True,
        "retained_zero_token_controls": identity(ROOT / controls_name), "retained_real_loopback_witness": identity(ROOT / witness_name),
        "historical_V4_sources_unchanged": True, "material_consistency_questions": [],
        "review_found_and_resolved_blocker": "Original V5 analyzer expected bare SHA strings while the real runner preparation writes exact bytes/SHA dictionaries. Root corrected strict schema/full digest checks and fixtures before this accepted actual-preparation check.",
        "scope_findings": [
            "V5 changes owned loopback address normalization and sanitized denied-address evidence, with plan/case/schema updates. It does not establish why V4's unrecorded socket arguments were denied.",
            "Exact declared loopback hosts/native ports plus allocated proxy port are admitted; other endpoints and malformed audit shapes remain denied. Recorded controls show real local transports only.",
            "Diagnostic records are bounded and omit socket objects, packet payloads and external host values. Dropped/write-failed diagnostics remain explicit missing evidence.",
            "Provider boundary remains serialized, paced and call/request-byte bounded; real credential stays in the parent, with synthetic proxy credentials in children and no redirects or ambient proxy.",
            "100000 is a known-token stop threshold, not a pre-request reservation or proven hard total-token maximum. Missing usage remains unknown and stops further admission.",
            "120 seconds is a transport sender option, not an independent whole-request wall cap; drain freezes unfinished allocations as unmeasured.",
            "Worker closes recorded original HTTP clients but preserves absent explicit Runner-close/full physical runtime/socket-inode witnesses as unresolved scope.",
            "Workflow places the real secret only in execution, pins actions/runtime requirements, runs controls first and retains failure outputs with private-key/environment exclusions.",
            "This read review qualifies a prospective one-case adaptive diagnostic, not task success, human gold, holdout, novelty or original full-study route fidelity. Root owns any dispatch."
        ],
        "new_application_SDK_provider_solver_checker_calls_by_review": 0,
        "new_network_or_transport_control_executions_by_review": 0,
        "live_dispatch_by_review": False, "human_scientific_review": False, "percentage_credit_claimed": False,
        "reviewer_source": identity(Path(__file__))}
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "prepared_sources": len(plan["owned_sources"]), "actual_plan_check": True,
        "new_application_provider_calls": 0}))


if __name__ == "__main__":
    main()
