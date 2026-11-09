"""Audit retained software captures without importing or executing their tests."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/agentops-grading-software"
CAPTURES = {'answer-schema-v1': ('answer-schema', 35),
 'case-assessment-v2': ('case-assessment-v2', 13),
 'evaluator-cli-v2': ('evaluator-cli-v2', 7)}
DRIVER = ROOT / "scripts/capture_agentops_grading_validation_v6.py"
# Local static audit of exact primary test and fixture memberships.
EXPECTED_SUITES = {'answer-schema': ('src/interoperability/__init__.py',
                   'src/interoperability/agentops_required_trajectory_v1.py',
                   'src/interoperability/agentops_reply_dependencies_v1.py',
                   'src/interoperability/agentops_answer_schema_v1.py',
                   'tests/test_agentops_answer_schema_v1.py',
                   'tests/test_agentops_reply_dependencies_v1.py',
                   'docs/research/upstream-agentops-grading-obligations-v1.json',
                   'runs/upstream-agentops-cases/v1/application/cases.json'),
 'case-assessment-v2': ('src/interoperability/__init__.py',
                        'src/interoperability/agentops_required_trajectory_v1.py',
                        'src/interoperability/agentops_reply_dependencies_v1.py',
                        'src/interoperability/agentops_answer_schema_v1.py',
                        'src/interoperability/agentops_runtime_stream_evidence_v1.py',
                        'src/interoperability/agentops_source_case_assessment_v1.py',
                        'src/interoperability/agentops_source_case_effects_v1.py',
                        'src/interoperability/agentops_source_case_assessment_v2.py',
                        'scripts/agentops_runtime_stream_v1.py',
                        'tests/test_agentops_source_case_assessment_v2.py',
                        'tests/test_agentops_source_case_assessment_v1.py',
                        'tests/test_agentops_source_case_effects_v1.py',
                        'docs/research/upstream-agentops-grading-obligations-v1.json',
                        'runs/upstream-agentops-cases/v1/application/cases.json',
                        'runs/upstream-agentops-cases/v1/evaluator/expectations.json'),
 'evaluator-cli-v2': ('scripts/assess_upstream_agentops_case_v2.py',
                      'scripts/assess_upstream_agentops_case_v1.py',
                      'scripts/agentops_runtime_stream_v1.py',
                      'scripts/agentops_native_probe_v2.py',
                      'src/interoperability/__init__.py',
                      'src/interoperability/agentops_runtime_stream_evidence_v1.py',
                      'src/interoperability/agentops_source_case_assessment_v1.py',
                      'src/interoperability/agentops_required_trajectory_v1.py',
                      'src/interoperability/agentops_reply_dependencies_v1.py',
                      'src/interoperability/agentops_source_case_effects_v1.py',
                      'src/interoperability/agentops_source_case_assessment_v2.py',
                      'src/interoperability/agentops_answer_schema_v1.py',
                      'src/interoperability/agentops_case_boundary_evidence_v1.py',
                      'src/interoperability/upstream_agentops_client_v1.py',
                      'src/interoperability/agentops_memory_evidence_v1.py',
                      'docs/research/agentops-answer-schema-assessment-design-v1.md',
                      'external/agentops-c806b7f1/agents/python/src/agent/models.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/report.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/workflow.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/composition.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/tools.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/memory.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/domain.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/longterm.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/pii.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/skills.py',
                      'external/agentops-c806b7f1/agents/python/src/agent/actions.py',
                      'external/agentops-c806b7f1/agents/python/evals/test_config.json',
                      'external/agentops-c806b7f1/agents/python/evals/report_eval.py',
                      'external/agentops-c806b7f1/agents/python/evals/groundedness_eval.py',
                      'external/agentops-c806b7f1/agents/python/evals/mlflow_eval.py',
                      'external/agentops-c806b7f1/agents/python/evals/required_trajectory.py',
                      'external/agentops-c806b7f1/agents/data/sql/seed.sql',
                      'external/agentops-c806b7f1/agents/data/skills/remediation/SKILL.md',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/events/event.py',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/workflow/_llm_agent_wrapper.py',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/workflow/_node_runner.py',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/workflow/_workflow.py',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/tools/skill_toolset.py',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/skills/prompt.py',
                      'external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/tools/function_tool.py',
                      'runs/upstream-agentops-cases/v1/application/cases.json',
                      'runs/upstream-agentops-cases/v1/evaluator/expectations.json',
                      'docs/research/upstream-agentops-grading-obligations-v1.json',
                      'external/agentops-c806b7f1/agents/data/runbooks/service-down.md',
                      'external/agentops-c806b7f1/agents/data/runbooks/memory-leak.md',
                      'external/agentops-c806b7f1/agents/data/runbooks/high-latency.md',
                      'external/agentops-c806b7f1/agents/data/runbooks/cascade-failure.md',
                      'external/agentops-c806b7f1/agents/python/evals/ops.evalset.json',
                      'external/agentops-c806b7f1/agents/python/evals/triage-report.evalset.json',
                      'external/agentops-c806b7f1/agents/python/evals/workflow.evalset.json',
                      'external/agentops-c806b7f1/agents/data/logs/cache.log',
                      'external/agentops-c806b7f1/agents/data/logs/checkout.log',
                      'external/agentops-c806b7f1/agents/data/logs/database.log',
                      'external/agentops-c806b7f1/agents/data/logs/inventory.log',
                      'tests/test_assess_upstream_agentops_case_v2.py',
                      'tests/test_agentops_case_boundary_evidence_v1.py',
                      'docs/research/agentops-answer-schema-assessment-design-v1.json')}
EXPECTED_TEST_FILES = {'answer-schema': ('tests/test_agentops_answer_schema_v1.py',),
 'case-assessment-v2': ('tests/test_agentops_source_case_assessment_v2.py',),
 'evaluator-cli-v2': ('tests/test_assess_upstream_agentops_case_v2.py',)}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(same(value, right[key]) for key, value in left.items())
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def descriptor(value):
    need(type(value) is dict and set(value) == {"bytes", "sha256"}
         and type(value["bytes"]) is int and value["bytes"] >= 0
         and type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
         "invalid typed byte/hash descriptor")
    return value


def directory_inventory(path):
    directories = set()
    for item in path.rglob("*"):
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "linked/reparse capture directory")
        if item.is_dir():
            directories.add(item.relative_to(path).as_posix())
    return directories


def regular(path):
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "linked/reparse input is unsupported")
    need(path.is_file(), "expected regular audit input")
    return path.read_bytes()


def relative(value):
    need(type(value) is str and value and ":" not in value and "\\" not in value,
         "invalid relative capture member")
    path = PurePosixPath(value)
    need(not path.is_absolute() and ".." not in path.parts and path.as_posix() == value,
         "capture member escapes its allocation")
    return value


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON member")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON value")
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    json.dumps(result, allow_nan=False)
    return result


def inventory(path):
    result = {}
    for item in sorted(path.rglob("*")):
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "linked/reparse capture member")
        need(item.is_file() or item.is_dir(), "nonregular capture member")
        if item.is_file():
            result[item.relative_to(path).as_posix()] = regular(item)
    return result


def driver_constants(raw):
    values = {}
    application = None
    tree = ast.parse(raw.decode("utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "APPLICATION"
                                               for target in node.targets):
            application = ast.literal_eval(node.value)
    class LiteralApplication(ast.NodeTransformer):
        def visit_Name(self, node):
            need(node.id == "APPLICATION" and type(application) is str, "unknown dynamic driver suite member")
            return ast.copy_location(ast.Constant(application), node)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"SUITES", "TEST_PROGRAM", "TEST_FILES"}:
                    values[target.id] = ast.literal_eval(LiteralApplication().visit(node.value))
    need(set(values) == {"SUITES", "TEST_PROGRAM", "TEST_FILES"}, "frozen driver constants unavailable")
    return values


def review(name, suite, expected_count):
    capture = BASE / name
    output = BASE / (name + "-static-review.json")
    need(not output.exists() and not output.is_symlink(), "static review allocation already consumed")
    reviewer_raw = regular(Path(__file__).resolve())
    report = {"schema_version": "agentops-grading-static-review/1", "status": "failed",
              "capture": str(capture), "suite": suite, "reviewer_source": digest(reviewer_raw),
              "reviewer_path": str(Path(__file__).resolve()), "test_runs_by_reviewer": 0,
              "sdk_imports_by_reviewer": 0, "application_processes_launched_by_reviewer": 0,
              "direct_model_calls_by_reviewer": 0, "graded_upstream_cases": 0,
              "native_qualification_established": False, "source_authentication_proven": False, "independent_peer_audit_completed": False,
              "performed_locally_by_capture_agent": True,
              "scope": "Local static byte and receipt audit only; separate peer audit remains pending"}
    inputs = {}
    try:
        files = inventory(capture)
        directories = directory_inventory(capture)
        inputs.update({capture / key: raw for key, raw in files.items()})
        result, plan, execution = (strict(files[key]) for key in ("result.json", "plan.json", "execution.json"))
        driver_raw = regular(DRIVER)
        inputs[DRIVER] = driver_raw
        constants = driver_constants(driver_raw)
        need(same(constants["SUITES"], EXPECTED_SUITES), "v6 literal source membership differs from local reviewed scope")
        selected = list(constants["SUITES"][suite])
        need(same(constants["TEST_FILES"], EXPECTED_TEST_FILES), "v6 primary test membership differs")
        tests = list(constants["TEST_FILES"][suite])
        need(result["schema_version"] == "agentops-grading-validation/1" and result["suite"] == suite,
             "capture result schema/suite differs")
        need(plan["schema_version"] == "agentops-grading-validation-plan/1" and plan["suite"] == suite,
             "capture plan schema/suite differs")
        need(plan["source_membership"] == selected and plan["test_files"] == tests,
             "planned source/test membership differs from frozen driver")
        need(same(plan["source_files"], result["source_files"]) and set(plan["source_files"]) == set(selected),
             "source manifests differ")
        source_checks = {}
        for name_in_source in selected:
            relative(name_in_source)
            current = regular(ROOT / name_in_source)
            inputs[ROOT / name_in_source] = current
            copied = files["workspace/" + name_in_source]
            need(current == copied and same(digest(current), descriptor(plan["source_files"][name_in_source])),
                 "captured source differs from current frozen input")
            source_checks[name_in_source] = digest(current)
        driver_member = "source/" + DRIVER.name
        need(files[driver_member] == driver_raw and same(descriptor(plan["driver_digest"]), digest(driver_raw)),
             "captured driver differs from current frozen source")
        expected_members = {"result.json", "plan.json", "execution.json", "stdout.txt", "stderr.txt", driver_member,
                            *("workspace/" + value for value in selected)}
        need(set(files) == expected_members, "unexpected or missing capture member")
        expected_directories = {parent.as_posix() for member in files for parent in PurePosixPath(member).parents
                                if parent.as_posix() != "."}
        need(directories == expected_directories, "unexpected or missing capture directory")
        rows = result["files"]
        manifest = {}
        for row in rows:
            member = relative(row["path"])
            need(set(row) == {"path", "bytes", "sha256"} and member not in manifest,
                 "duplicate or malformed manifest entry")
            manifest[member] = descriptor({key: row[key] for key in ("bytes", "sha256")})
        need(set(manifest) == expected_members - {"result.json"}, "terminal manifest membership differs")
        need(all(same(manifest[key], digest(files[key])) for key in manifest), "captured manifest digest differs")
        command = plan["command"]
        need(type(command) is list and len(command) == 9 and command[1:5] == ["-I", "-S", "-B", "-c"],
             "captured child command is not explicitly isolated")
        need(command[5] == constants["TEST_PROGRAM"] and strict(command[7].encode("utf-8")) == tests,
             "captured child program/test selection differs from frozen driver")
        need(Path(command[6]).resolve() == (capture / "workspace").resolve()
             and Path(command[8]).resolve() == (capture / "execution.json").resolve()
             and Path(plan["cwd"]).resolve() == (capture / "workspace").resolve(),
             "captured command allocation/cwd differs")
        need(Path(command[0]).is_absolute() and Path(command[0]).is_file(), "recorded interpreter unavailable")
        need(same(execution, result["execution"]) and execution["executed_test_files"] == tests,
             "machine result or executed file membership differs")
        need(all(execution[key] is True for key in ("successful", "isolated_python", "site_disabled", "bytecode_disabled")),
             "machine success/isolation flags differ")
        counts = {key: execution[key] for key in ("tests_run", "failures", "errors", "skips", "expected_failures", "unexpected_successes")}
        need(all(type(value) is int and value >= 0 and type(result[key]) is int and result[key] == value for key, value in counts.items()),
             "typed machine/top-level counts differ")
        need(counts["tests_run"] == expected_count and all(value == 0 for key, value in counts.items() if key != "tests_run"),
             "unexpected count, failure, error, skip or alternate success")
        stderr = files["stderr.txt"]
        lines = stderr.decode("utf-8").splitlines()
        summary_counts = [int(match[1]) for line in lines if (match := re.fullmatch(r"Ran (\d+) tests? in .+", line))]
        success_lines = [line for line in lines if re.fullmatch(r"OK(?: \([^\r\n]*\))?", line)]
        test_headings = [line for line in lines if re.match(r"^test_[^\r\n]* \([^)]+\) \.\.\. ", line)]
        expected_test_names = set()
        for test_index, relative_test in enumerate(tests):
            primary_tree = ast.parse(files["workspace/" + relative_test].decode("utf-8"))
            for class_node in primary_tree.body:
                if isinstance(class_node, ast.ClassDef):
                    for method in class_node.body:
                        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_"):
                            expected_test_names.add("captured_validation_test_" + str(test_index) + "." + class_node.name + "." + method.name)
        observed_test_names = [re.fullmatch(r"test_[^\r\n]* \(([^)]+)\) \.\.\. ok", line).group(1) for line in test_headings]
        need(len(expected_test_names) == expected_count and set(observed_test_names) == expected_test_names
             and len(observed_test_names) == len(set(observed_test_names)), "imported fixture or unexpected primary test executed")
        need(summary_counts == [expected_count] and success_lines == ["OK"] and len(test_headings) == expected_count,
             "retained text summary/test headings differ from machine count")
        need(same(result["summary_test_counts"], summary_counts) and result["summary_success"] is True,
             "receipt text summary differs")
        need(same(descriptor(result["stdout"]), digest(files["stdout.txt"]))
             and same(descriptor(result["stderr"]), digest(stderr)),
             "raw log digest differs")
        need(result["status"] == "passed" and type(result["exit_code"]) is int and result["exit_code"] == 0 and result["error"] is None,
             "capture did not record an uncomplicated successful exit")
        need(all(result[key] is True for key in ("original_sources_unchanged", "captured_sources_unchanged",
                                                 "driver_unchanged", "captured_files_unchanged")),
             "recorded preservation flags differ")
        need(all(result[key] == 0 and type(result[key]) is int for key in ("application_processes_launched", "direct_model_calls",
                    "sdk_imports_by_driver", "original_archives_exported", "graded_upstream_cases"))
             and result["native_qualification_established"] is False, "capture scope exceeds software evidence")
        need(regular(Path(__file__).resolve()) == reviewer_raw and all(regular(path) == raw for path, raw in inputs.items())
             and inventory(capture) == files and directory_inventory(capture) == directories,
             "audit input bytes or membership changed during review")
        report.update(status="verified", tests_run=expected_count, counts=counts, current_sources_match_captured=True,
                      exact_capture_membership_verified=True, exact_directory_membership_verified=True,
                      typed_counts_and_descriptors_verified=True, manifest_digests_verified=True,
                      machine_and_text_logs_agree=True, frozen_driver_matches_current=True,
                      driver_literal_suite_membership_reviewed=True, primary_test_names_verified=True, imported_fixture_tests_excluded=True, selected_source_membership=selected,
                      inputs_unchanged_during_review=True, source_files=source_checks,
                      driver_digest=digest(driver_raw), capture_result_digest=digest(files["result.json"]),
                      capture_files={key: digest(raw) for key, raw in sorted(files.items())},
                      capture_directories=sorted(directories),
                      stderr_line_endings={"crlf": stderr.count(b"\r\n"),
                          "bare_lf": stderr.count(b"\n") - stderr.count(b"\r\n"),
                          "normalized_only_in_memory": True},
                      recorded_interpreter=command[0], software_test_files=tests)
    except (OSError, ValueError, TypeError, KeyError, SyntaxError) as error:
        report.update(error_type=type(error).__name__, reason=str(error))
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    raw = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with output.open("xb") as stream:
        stream.write(raw)
    return {"capture": name, "status": report["status"], "tests_run": report.get("tests_run"),
            "review": str(output), "review_digest": digest(raw), "reason": report.get("reason")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture")
    parser.add_argument("--suite")
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    if any(value is not None for value in (args.capture, args.suite, args.expected_count)):
        need(all(value is not None for value in (args.capture, args.suite, args.expected_count))
             and args.expected_count > 0 and re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.capture),
             "explicit capture, suite and positive expected count are all required")
        selected = {args.capture: (args.suite, args.expected_count)}
    else:
        selected = CAPTURES
    summaries = [review(name, suite, count) for name, (suite, count) in selected.items()]
    print(json.dumps(summaries, sort_keys=True))
    raise SystemExit(0 if all(row["status"] == "verified" for row in summaries) else 1)
