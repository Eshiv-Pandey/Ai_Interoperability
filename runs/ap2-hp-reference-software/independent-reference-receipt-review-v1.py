"""Retained-byte audits only; never imports/reruns original or captured code."""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "runs/ap2-hp-reference-software"
HELPER = "src/interoperability/ap2_hp_reference_plan_v1.py"
CLI = "scripts/ap2_hp_reference_client_v1.py"
CALLER_BASE = "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/"
CALLERS = (
    "roles/shopping_agent/tools.py",
    "roles/shopping_agent/subagents/shopper/tools.py",
    "roles/shopping_agent/subagents/shipping_address_collector/tools.py",
    "roles/shopping_agent/subagents/payment_method_collector/tools.py",
)
SUITES = (
    ("reference-plan-v1", "ap2-hp-reference-software-validation/1", "tests/test_ap2_hp_reference_plan_v1.py", "ReferencePlanTests", 24, True),
    ("reference-cli-v1", "ap2-hp-reference-cli-validation/1", "tests/test_ap2_hp_reference_cli_v1.py", "ReferencePlanningCliTests", 3, False),
)

def descriptor(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

def inventory(capture):
    return {file.relative_to(capture).as_posix(): descriptor(file.read_bytes())
            for file in sorted(capture.rglob("*")) if file.is_file()}

for label, schema, test, owner, count, has_callers in SUITES:
    capture = BASE / label
    output = BASE / (label + "-independent-review.json")
    pending = output.with_suffix(".json.pending")
    if output.exists() or pending.exists():
        raise FileExistsError("Independent review allocation consumed")
    checks = []
    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})
    before = inventory(capture)
    result = json.loads((capture / "result.json").read_bytes())
    copied = {HELPER, CLI, test}
    expected = copied | {CALLER_BASE + path for path in CALLERS} if has_callers else copied
    check("result_schema", result.get("schema_version") == schema)
    check("recorded_terminal_pass", result.get("status") == "passed" and type(result.get("returncode")) is int and result["returncode"] == 0)
    check("result_has_exact_recorded_source_set", set(result["source_sha256_before"]) == set(result["source_sha256_after"]) == expected)
    check("exact_six_capture_files", set(before) == {"result.json", "tests.stdout.bin", "tests.stderr.bin"} | {"sources/" + name for name in copied})
    check("recorded_original_executions_zero", type(result.get("original_native_executions")) is int and result["original_native_executions"] == 0)
    check("recorded_model_attempts_zero", type(result.get("model_attempts")) is int and result["model_attempts"] == 0)
    check("recorded_key_accesses_zero", type(result.get("key_accesses")) is int and result["key_accesses"] == 0)
    check("recorded_preservation_true", result.get("inputs_unchanged") is True)
    current_sources = {}
    for name in sorted(expected):
        current = descriptor((ROOT / name).read_bytes())
        current_sources[name] = current
        check("current_recorded_source:" + name, current["sha256"] == result["source_sha256_before"][name] == result["source_sha256_after"][name])
        if name in copied:
            check("captured_current_source:" + name, descriptor((capture / "sources" / name).read_bytes()) == current)
    check("stdout_digest", before["tests.stdout.bin"]["sha256"] == result["stdout_sha256"])
    check("stderr_digest", before["tests.stderr.bin"]["sha256"] == result["stderr_sha256"])
    check("stdout_empty", before["tests.stdout.bin"]["bytes"] == 0)
    check("recorded_tests_exact_count", type(result.get("tests_expected")) is int and type(result.get("tests_observed")) is int and result["tests_expected"] == result["tests_observed"] == count)
    check("recorded_exact_isolated_python_flags", result.get("argv") == ["C:\\Python313\\python.exe", "-I", "-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", Path(test).name, "-v"])
    check("recorded_wall_clock_order", datetime.fromisoformat(result["started_at_utc"]) <= datetime.fromisoformat(result["finished_at_utc"]))
    check("recorded_elapsed_nonnegative", type(result.get("elapsed_seconds")) in (int, float) and result["elapsed_seconds"] >= 0)
    syntax = ast.parse((capture / "sources" / test).read_bytes())
    classes = [node for node in syntax.body if isinstance(node, ast.ClassDef)]
    owners = [node for node in classes if node.name == owner]
    check("one_exact_primary_class", len(classes) == len(owners) == 1)
    primary = sorted(node.name for cls in owners for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    check("primary_ast_exact_unique_count", len(primary) == len(set(primary)) == count)
    lines = (capture / "tests.stderr.bin").read_bytes().decode("utf-8", errors="strict").splitlines()
    observed, unmatched = [], []
    pattern = r"(test_\w+) \(" + re.escape(Path(test).stem + "." + owner) + r"\.(test_\w+)\) \.\.\. ok"
    for line in lines:
        if line.startswith("test_"):
            match = re.fullmatch(pattern, line)
            if match and match[1] == match[2]:
                observed.append(match[1])
            else:
                unmatched.append(line)
    check("logged_exact_primary_ast_membership", sorted(observed) == primary)
    check("logged_primary_unique_exact_count", len(observed) == len(set(observed)) == count)
    check("no_unmatched_test_status_lines", not unmatched)
    summaries = [re.fullmatch(r"Ran (\d+) tests in ([0-9]+(?:\.[0-9]+)?)s", line) for line in lines if line.startswith("Ran ")]
    check("one_exact_reported_summary", len(summaries) == 1 and summaries[0] is not None and int(summaries[0][1]) == count)
    check("one_exact_terminal_ok", lines[-1:] == ["OK"] and lines.count("OK") == 1)
    check("no_logged_fail_error_skip", not any(token in "\n".join(lines) for token in ("... FAIL", "... ERROR", "... skipped", "FAILED (", "Traceback (most recent call last)")))
    helper_ast = ast.parse((capture / "sources" / HELPER).read_bytes())
    imports = []
    for node in ast.walk(helper_ast):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    check("pure_helper_only_reviewed_stdlib_imports", set(imports) == {"__future__", "ast", "base64", "copy", "hashlib", "math", "re"})
    review = ROOT / "docs/research/ap2-human-present-reference-plan-source-review-v1.md"
    review_before = descriptor(review.read_bytes())
    check("source_review_note_exact_identity", review_before["sha256"] == "618922a474cce76161978ddd5d15f7e5b4d5c3361d300f4ae08f61ce759bd8fc")
    after = inventory(capture)
    check("all_capture_files_preserved_during_audit", before == after)
    for name, expected_descriptor in current_sources.items():
        check("current_source_preserved_during_audit:" + name, descriptor((ROOT / name).read_bytes()) == expected_descriptor)
    check("source_review_note_preserved_during_audit", descriptor(review.read_bytes()) == review_before)
    report = {
        "schema_version": "ap2-hp-reference-retained-receipt-independent-review/1",
        "status": "verified_bounded_retained_receipt" if all(item["passed"] for item in checks) else "failed",
        "reviewer": "separate_AI_agent_method_next_step", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "capture": str(capture), "capture_result_digest": before["result.json"], "capture_files": before,
        "current_recorded_source_files": current_sources, "captured_source_file_count": len(copied),
        "recorded_original_caller_source_hash_count": 4 if has_callers else 0,
        "original_caller_source_copies_retained": False, "capture_driver_or_plan_retained": False,
        "isolated_captured_code_replay_proven": False,
        "primary_ast_tests": primary, "logged_primary_tests": observed, "test_count": count,
        "checks_passed": sum(item["passed"] for item in checks), "checks": checks,
        "discrepancies": [item["name"] for item in checks if not item["passed"]],
        "source_review_note_digest": review_before, "reviewer_script_digest": descriptor(Path(__file__).read_bytes()),
        "test_reruns_by_reviewer": 0, "captured_or_original_module_imports_by_reviewer": 0,
        "original_native_executions_by_reviewer": 0, "model_attempts_by_reviewer": 0, "key_accesses_by_reviewer": 0,
        "native_qualification_established": False, "aggregate_task_grade": None,
        "scope": "Independent current/captured bytes, exact primary AST/log membership, recorded return/count, before/after source hash bindings and preservation audit only. Three implementation/test source copies are retained; the planner receipt additionally records four original caller source hashes without copies. No capture driver/plan is retained, no isolated captured-code execution is proven, and execution/zero original-model-key counters remain recorder assertions corroborated only by inspected pure source. No rerun/import or source authenticity, causal native workflow, credential/effect state, independent human task validity or scientific upgrade."
    }
    with pending.open("xb") as stream:
        stream.write((json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, output)
    pending.unlink()
    print(json.dumps({"suite": label, "status": report["status"], "checks_passed": report["checks_passed"], "discrepancies": report["discrepancies"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}), flush=True)
