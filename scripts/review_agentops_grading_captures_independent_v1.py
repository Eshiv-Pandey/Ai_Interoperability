"""Audit retained software captures without importing or executing their tests."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/agentops-grading-software"
CAPTURES = {"trajectory-v1": ("trajectory", 16), "memory-v1": ("memory", 20),
            "stream-v1": ("stream", 37), "asgi-v2": ("asgi-v2", 8)}
DRIVER = ROOT / "scripts/capture_agentops_grading_validation_v1.py"


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


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
    for node in ast.parse(raw.decode("utf-8")).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"SUITES", "TEST_PROGRAM"}:
                    values[target.id] = ast.literal_eval(node.value)
    need(set(values) == {"SUITES", "TEST_PROGRAM"}, "frozen driver constants unavailable")
    return values


def review(name, suite, expected_count):
    capture = BASE / name
    output = BASE / (name + "-independent-review.json")
    need(not output.exists() and not output.is_symlink(), "independent review allocation already consumed")
    reviewer_raw = regular(Path(__file__).resolve())
    report = {"schema_version": "agentops-grading-independent-review/1", "status": "failed",
              "capture": str(capture), "suite": suite, "reviewer_source": digest(reviewer_raw),
              "reviewer_path": str(Path(__file__).resolve()), "test_runs_by_reviewer": 0,
              "sdk_imports_by_reviewer": 0, "application_processes_launched_by_reviewer": 0,
              "direct_model_calls_by_reviewer": 0, "graded_upstream_cases": 0,
              "native_qualification_established": False, "source_authentication_proven": False,
              "scope": "Independent static byte and receipt audit of focused captured software tests only"}
    inputs = {}
    try:
        files = inventory(capture)
        inputs.update({capture / key: raw for key, raw in files.items()})
        result, plan, execution = (strict(files[key]) for key in ("result.json", "plan.json", "execution.json"))
        driver_raw = regular(DRIVER)
        inputs[DRIVER] = driver_raw
        constants = driver_constants(driver_raw)
        selected = list(constants["SUITES"][suite])
        tests = [value for value in selected if value.startswith("tests/") and value.endswith(".py")]
        need(result["schema_version"] == "agentops-grading-validation/1" and result["suite"] == suite,
             "capture result schema/suite differs")
        need(plan["schema_version"] == "agentops-grading-validation-plan/1" and plan["suite"] == suite,
             "capture plan schema/suite differs")
        need(plan["source_membership"] == selected and plan["test_files"] == tests,
             "planned source/test membership differs from frozen driver")
        need(plan["source_files"] == result["source_files"] and set(plan["source_files"]) == set(selected),
             "source manifests differ")
        source_checks = {}
        for name_in_source in selected:
            relative(name_in_source)
            current = regular(ROOT / name_in_source)
            inputs[ROOT / name_in_source] = current
            copied = files["workspace/" + name_in_source]
            need(current == copied and digest(current) == plan["source_files"][name_in_source],
                 "captured source differs from current frozen input")
            source_checks[name_in_source] = digest(current)
        driver_member = "source/" + DRIVER.name
        need(files[driver_member] == driver_raw and plan["driver_digest"] == digest(driver_raw),
             "captured driver differs from current frozen source")
        expected_members = {"result.json", "plan.json", "execution.json", "stdout.txt", "stderr.txt", driver_member,
                            *("workspace/" + value for value in selected)}
        need(set(files) == expected_members, "unexpected or missing capture member")
        rows = result["files"]
        manifest = {}
        for row in rows:
            member = relative(row["path"])
            need(set(row) == {"path", "bytes", "sha256"} and member not in manifest,
                 "duplicate or malformed manifest entry")
            manifest[member] = {key: row[key] for key in ("bytes", "sha256")}
        need(set(manifest) == expected_members - {"result.json"}, "terminal manifest membership differs")
        need(all(manifest[key] == digest(files[key]) for key in manifest), "captured manifest digest differs")
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
        need(execution == result["execution"] and execution["executed_test_files"] == tests,
             "machine result or executed file membership differs")
        need(all(execution[key] is True for key in ("successful", "isolated_python", "site_disabled", "bytecode_disabled")),
             "machine success/isolation flags differ")
        counts = {key: execution[key] for key in ("tests_run", "failures", "errors", "skips", "expected_failures", "unexpected_successes")}
        need(all(type(value) is int and value >= 0 and result[key] == value for key, value in counts.items()),
             "typed machine/top-level counts differ")
        need(counts["tests_run"] == expected_count and all(value == 0 for key, value in counts.items() if key != "tests_run"),
             "unexpected count, failure, error, skip or alternate success")
        stderr = files["stderr.txt"]
        lines = stderr.decode("utf-8").splitlines()
        summary_counts = [int(match[1]) for line in lines if (match := re.fullmatch(r"Ran (\d+) tests? in .+", line))]
        success_lines = [line for line in lines if re.fullmatch(r"OK(?: \([^\r\n]*\))?", line)]
        test_headings = [line for line in lines if re.match(r"^test_[^\r\n]* \([^)]+\) \.\.\. ", line)]
        need(summary_counts == [expected_count] and success_lines == ["OK"] and len(test_headings) == expected_count,
             "retained text summary/test headings differ from machine count")
        need(result["summary_test_counts"] == summary_counts and result["summary_success"] is True,
             "receipt text summary differs")
        need(result["stdout"] == digest(files["stdout.txt"]) and result["stderr"] == digest(stderr),
             "raw log digest differs")
        need(result["status"] == "passed" and result["exit_code"] == 0 and result["error"] is None,
             "capture did not record an uncomplicated successful exit")
        need(all(result[key] is True for key in ("original_sources_unchanged", "captured_sources_unchanged",
                                                 "driver_unchanged", "captured_files_unchanged")),
             "recorded preservation flags differ")
        need(all(result[key] == 0 and type(result[key]) is int for key in ("application_processes_launched", "direct_model_calls",
                    "sdk_imports_by_driver", "original_archives_exported", "graded_upstream_cases"))
             and result["native_qualification_established"] is False, "capture scope exceeds software evidence")
        need(regular(Path(__file__).resolve()) == reviewer_raw and all(regular(path) == raw for path, raw in inputs.items())
             and inventory(capture) == files, "audit input bytes or membership changed during review")
        report.update(status="verified", tests_run=expected_count, counts=counts, current_sources_match_captured=True,
                      exact_capture_membership_verified=True, manifest_digests_verified=True,
                      machine_and_text_logs_agree=True, frozen_driver_matches_current=True,
                      inputs_unchanged_during_review=True, source_files=source_checks,
                      driver_digest=digest(driver_raw), capture_result_digest=digest(files["result.json"]),
                      capture_files={key: digest(raw) for key, raw in sorted(files.items())},
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
    summaries = [review(name, suite, count) for name, (suite, count) in CAPTURES.items()]
    print(json.dumps(summaries, sort_keys=True))
    raise SystemExit(0 if all(row["status"] == "verified" for row in summaries) else 1)
