"""Read-only evaluator for one complete retained v2 source-case instance.

References are loaded only in this evaluator. No SDK, original application,
credential, model or native request is executed. Output is a fresh exclusive
directory; separate observation lanes never become an aggregate task grade.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import stat
import types


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "upstream-agentops-case-evaluator/2"
LEGACY_PATH = ROOT / "scripts/assess_upstream_agentops_case_v1.py"
for _part in (*reversed(LEGACY_PATH.parents), LEGACY_PATH):
    _info = _part.lstat()
    if stat.S_ISLNK(_info.st_mode) or getattr(_info, "st_file_attributes", 0) & 0x400:
        raise ValueError("linked/reparse frozen evaluator helper path is unsupported")
if not LEGACY_PATH.is_file() or LEGACY_PATH.stat().st_size > 16 * 1024 * 1024:
    raise ValueError("unsupported frozen evaluator helper file")
LEGACY_RAW = LEGACY_PATH.read_bytes()
if hashlib.sha256(LEGACY_RAW).hexdigest() != "e2401c03dfde733f08c30e8b4a6f852a67eb41e7d969d728155c14378cbeb48e":
    raise ValueError("frozen publication helper bytes differ before execution")
legacy = types.ModuleType("frozen_v1_evaluator_helpers")
legacy.__file__ = str(LEGACY_PATH)
exec(compile(LEGACY_RAW, str(LEGACY_PATH), "exec"), legacy.__dict__)
_need, _regular, _digest, _read, _json = legacy._need, legacy._regular, legacy._digest, legacy._read, legacy._json
_write, _write_json, _publish_result, _select = legacy._write, legacy._write_json, legacy._publish_result, legacy._select

SOURCES = ("scripts/assess_upstream_agentops_case_v2.py", "scripts/assess_upstream_agentops_case_v1.py",
           "scripts/agentops_runtime_stream_v1.py", "scripts/agentops_native_probe_v2.py",
           "src/interoperability/__init__.py", "src/interoperability/agentops_runtime_stream_evidence_v1.py",
           "src/interoperability/agentops_source_case_assessment_v1.py",
           "src/interoperability/agentops_required_trajectory_v1.py",
           "src/interoperability/agentops_reply_dependencies_v1.py",
           "src/interoperability/agentops_source_case_effects_v1.py",
           "src/interoperability/agentops_source_case_assessment_v2.py",
           "src/interoperability/agentops_answer_schema_v1.py",
           "src/interoperability/agentops_case_boundary_evidence_v1.py",
           "src/interoperability/upstream_agentops_client_v1.py",
           "src/interoperability/agentops_memory_evidence_v1.py",
           "docs/research/agentops-answer-schema-assessment-design-v1.md")
PINNED_INPUT_SHA256 = {
    "application": "3b58d64163533a9ddec2a68438b22a9fc1c43e7d5e50e8579fd7d766270bc146",
    "expectations": "8eb1fb24858bdd491319544973f9197a9fcbc436d82c8a017d96d3fdbaaa478f",
    "obligations": "e3d9a2cd1a755c1207dd3927697ee0f56c4171737dd6d08d2f3c137176800558",
    "answer_schema_design": "0f9f6e78a5c8a23f51923e5dc469bfafd174e9fc6549e6513eaa3018fd21a189",
}
FROZEN_SOURCE_SHA256 = {
    "scripts/assess_upstream_agentops_case_v1.py": "e2401c03dfde733f08c30e8b4a6f852a67eb41e7d969d728155c14378cbeb48e",
    "src/interoperability/agentops_runtime_stream_evidence_v1.py": "0bc4002cf726f0df6ce719102a0c7bee1049a39f2f9239a1ccc76cf887e51d49",
    "src/interoperability/agentops_source_case_assessment_v1.py": "996173207112b97c3e9b6ec72d01bb32232684a2de4efcd36e65c85f5461b769",
    "src/interoperability/agentops_required_trajectory_v1.py": "ad41fd029c1111ad4b2d933fd42e8d9ea8183bee7c99e088a57d219d9d574ed5",
    "src/interoperability/agentops_reply_dependencies_v1.py": "ae70b1a5dd901d3e1b298e30258fd7b12f51cc3f461a3be5880da9c26eb102e3",
    "src/interoperability/agentops_source_case_effects_v1.py": "ea1a88f1e062c332b2ebd7e0c9360deae75b9c46397b5ee71e84d7c0a805f7dd",
    "docs/research/agentops-answer-schema-assessment-design-v1.md": "7daaf1bb060405373b4f560b0a659c890b3cc4d4fea35aaafb5b9bccaa32c238",
}


def _inventory(directory):
    directory = _regular(directory, True)
    files, directories, total = {}, [], 0
    for path in sorted(directory.rglob("*")):
        _regular(path, path.is_dir())
        relative = path.relative_to(directory).as_posix()
        if path.is_dir():
            directories.append(relative)
        else:
            _need(len(files) < 16384, "instance inventory file count exceeds bound")
            raw = _read(path, 32 * 1024 * 1024)
            total += len(raw)
            _need(total <= 512 * 1024 * 1024, "instance inventory aggregate bytes exceed bound")
            files[relative] = _digest(raw)
    return {"files": files, "directories": directories}


def _source_path(relative):
    _need(type(relative) is str and relative and ":" not in relative and "\\" not in relative
          and not PurePosixPath(relative).is_absolute() and ".." not in PurePosixPath(relative).parts
          and PurePosixPath(relative).as_posix() == relative, "unsupported source dependency path")
    path = ROOT / relative
    _need(path.resolve().is_relative_to(ROOT.resolve()), "source dependency escapes project")
    return path


def _evaluators(source_bytes):
    # Compile the already captured exact bytes in dependency order. Existing
    # module objects and timestamp-valid cached bytecode are never consulted.
    helper_src = str((ROOT / "src").resolve())
    sys.path[:] = [helper_src, *[item for item in sys.path if item != helper_src]]
    names = ("interoperability", "interoperability.agentops_required_trajectory_v1",
             "interoperability.agentops_runtime_stream_evidence_v1", "interoperability.agentops_source_case_assessment_v1",
             "interoperability.agentops_reply_dependencies_v1", "interoperability.agentops_source_case_effects_v1",
             "interoperability.agentops_memory_evidence_v1", "interoperability.upstream_agentops_client_v1",
             "interoperability.agentops_case_boundary_evidence_v1", "interoperability.agentops_answer_schema_v1",
             "interoperability.agentops_source_case_assessment_v2")
    modules = {}
    for name in names:
        relative = "src/interoperability/__init__.py" if name == "interoperability" else "src/" + name.replace(".", "/") + ".py"
        _need(relative in source_bytes, "missing pre-read evaluator helper bytes")
        module = types.ModuleType(name)
        module.__file__ = str(ROOT / relative)
        module.__package__ = name if name == "interoperability" else "interoperability"
        if name == "interoperability": module.__path__ = [helper_src + "/interoperability"]
        sys.modules[name] = module
        if name != "interoperability": setattr(modules["interoperability"], name.rsplit(".", 1)[1], module)
        exec(compile(source_bytes[relative], module.__file__, "exec"), module.__dict__)
        modules[name] = module
    return (modules["interoperability.agentops_runtime_stream_evidence_v1"].read_closed_journal,
            modules["interoperability.agentops_case_boundary_evidence_v1"].collect_case_boundaries,
            modules["interoperability.agentops_source_case_assessment_v2"].assess_source_case)


def _closed_stream_binding(instance, inventory, validation, application):
    """Recheck the frozen runner/bootstrap declared journal bindings."""
    def control(name):
        raw = _read(instance / name)
        _need(_digest(raw) == inventory["files"].get(name), "instance control bytes differ from initial binding")
        value = _json(raw)
        _need(type(value) is dict, "instance control receipt must be an object")
        return value
    result, exited = control("result.json"), control("service/bootstrap.exit.json")
    closed, stream = result.get("closed_runtime_stream"), exited.get("runtime_stream")
    _need(type(closed) is dict and closed.get("schema_version") == "upstream-agentops-closed-stream-binding/1"
          and closed.get("status") == "validated" and closed.get("closed_owned_process_gate_checked_by_caller") is True,
          "instance closed stream binding is missing or unsupported")
    _need(type(stream) is dict and stream.get("status") == "recorded"
          and stream.get("receipt") == "runtime-stream/result.json", "bootstrap recorded stream receipt is missing")
    for flag in ("finish_called", "capture_complete", "eligible_for_ordered_evidence_checks", "lifecycle_succeeded",
                 "serve_tasks_settled", "original_serve_returned", "persisted_receipt_matches_returned"):
        _need(stream.get(flag) is True, "bootstrap stream closure/completeness flag absent or false")
    identity = {"bytes": stream.get("receipt_bytes"), "sha256": stream.get("receipt_sha256")}
    same = sys.modules["interoperability.agentops_source_case_assessment_v1"]._same
    _need(same(identity, validation["receipt_identity"]) and same(closed.get("receipt_identity"), identity)
          and same(closed.get("files"), validation["files"]), "instance/bootstrap journal receipt or complete file bindings differ")
    observer = _digest(_read(ROOT / "scripts/agentops_runtime_stream_v1.py"))
    _need(same(validation["observer_identity"], observer)
          and same(closed["files"].get("source/agentops_runtime_stream_v1.py"), observer),
          "instance closed stream observer identity differs from frozen evaluator observer")
    events, calls = validation["ordered_events"], validation["calls"]
    expected = {"source_turns_bound": len(application["conversation"]), "native_call_count": len(calls), "original_event_count": len(events)}
    _need(all(type(closed.get(key)) is int and closed[key] == value for key, value in expected.items())
          and same(closed.get("event_ids"), [event["id"] for event in events])
          and same(closed.get("invocation_ids_in_event_order"), [event["invocation_id"] for event in events]),
          "instance closed stream turn/event identities differ")
    root = control("service/runtime-stream/result.json")
    keys = ("schema_version", "status", "calls_seen", "active_calls", "capture_disabled", "durable_receipt_written",
            "capture_complete", "eligible_for_ordered_evidence_checks")
    _need(same(stream.get("returned"), {key: root.get(key) for key in keys}), "bootstrap returned/persisted journal subset differs")
    return {"receipt_identity": identity, "observer_identity": observer, **expected,
            "instance_bootstrap_and_validated_journal_agree": True, "source_authentication_proven": False}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("instance", "application", "expectations", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--obligations", type=Path, default=ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json")
    parser.add_argument("--answer-schema-design", type=Path, default=ROOT / "docs/research/agentops-answer-schema-assessment-design-v1.json")
    for name in ("original-sanitizer-fixture", "answer-extraction-bindings"):
        parser.add_argument("--" + name, type=Path)
    for name in ("eval-set-id", "eval-id", "native-user-id", "native-session-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    for name, value in vars(args).items():
        if isinstance(value, Path): setattr(args, name, value.absolute())
    args.journal = args.instance / "service/runtime-stream"
    return args


def main(argv=None):
    args = parse_args(argv)
    phase, allocated = "exclusive_output_allocation", False
    result = {"schema_version": SCHEMA, "status": "failed", "metric_status": None, "assessment": None,
              "assessment_eligible": False, "aggregate_task_pass_assigned": False,
              "source_authentication_proven": False, "native_authentication_proven": False,
              "native_qualification_established": False, "native_source_case_qualification": False,
              "process_exit_proven": False, "public_raw_binding_checked": False, "state_effects_proven": False,
              "benchmark_grade_proven": False, "full_task_grade_assigned": False,
              "continuous_input_immutability_proven": False, "caller_native_ids_are_authenticated": False,
              "input_bindings": {}, "evaluator_source_bindings": {}, "instance_binding": None,
              "directory_entry_crash_durability_proven": False,
              "final_receipt_publication_protocol": "exclusive pending fsync/close; owned empty final reservation; atomic replacement",
              "started_at_utc": datetime.now(timezone.utc).isoformat()}
    before_inputs, before_sources, before_instance = {}, {}, None
    input_names = tuple(PINNED_INPUT_SHA256) + tuple(name for name in ("original_sanitizer_fixture", "answer_extraction_bindings") if getattr(args, name) is not None)
    try:
        _need(not args.output.exists() and not args.output.is_symlink(), "preserve existing evaluator output")
        _regular(args.output.parent, True)
        for protected in (args.instance, *(getattr(args, name) for name in input_names), ROOT / "src", ROOT / "scripts", ROOT / "docs", ROOT / "external"):
            _need(not args.output.resolve().is_relative_to(protected.resolve())
                  and not protected.resolve().is_relative_to(args.output.resolve()), "evaluator output overlaps input/source")
        args.output.mkdir(exist_ok=False); allocated = True
        _write_json(args.output / "plan.json", {"schema_version": SCHEMA, "arguments": {name: str(value) if value is not None else None for name, value in vars(args).items()},
                    "runtime_requests": 0, "model_calls": 0, "credential_reads": 0, "references_loaded_only_in_evaluator_process": True})
        phase = "capture_read_only_input_bindings"
        for name in input_names:
            before_inputs[name] = _read(getattr(args, name))
            digest = _digest(before_inputs[name])
            result["input_bindings"][name] = {"path": str(getattr(args, name)), **digest}
            _need(name not in PINNED_INPUT_SHA256 or digest["sha256"] == PINNED_INPUT_SHA256[name], "frozen source projection/obligation/design bytes differ")
        design = _json(before_inputs["answer_schema_design"])
        _need(type(design) is dict and design.get("schema_version") == "agentops-answer-schema-assessment-design-v1"
              and type(design.get("source_artifacts")) is list, "unsupported pinned answer/schema design")
        required_sources = {name: None for name in SOURCES}
        for item in design["source_artifacts"]:
            _need(type(item) is dict and type(item.get("bytes")) is int and type(item.get("sha256")) is str,
                  "unsupported design source binding")
            _source_path(item.get("path"))
            _need(required_sources.get(item["path"]) in (None, {"bytes": item["bytes"], "sha256": item["sha256"]}), "conflicting design source dependency")
            required_sources[item["path"]] = {"bytes": item["bytes"], "sha256": item["sha256"]}
        for relative, expected in required_sources.items():
            raw = _read(_source_path(relative)); digest = _digest(raw)
            _need(expected is None or digest == expected, "pinned original design source dependency differs")
            _need(relative not in FROZEN_SOURCE_SHA256 or digest["sha256"] == FROZEN_SOURCE_SHA256[relative], "frozen evaluator dependency differs")
            _need(relative != "scripts/assess_upstream_agentops_case_v1.py" or raw == LEGACY_RAW, "loaded frozen publication helper differs")
            before_sources[relative] = raw; result["evaluator_source_bindings"][relative] = digest
            target = args.output / "source" / relative; target.parent.mkdir(parents=True, exist_ok=True); _write(target, raw)
        before_instance = _inventory(args.instance)
        result["instance_binding"] = {"path": str(args.instance), **before_instance}
        _write_json(args.output / "bindings.before.json", {key: result[key] for key in ("input_bindings", "evaluator_source_bindings", "instance_binding")})
        phase = "select_source_case"
        application = _select(before_inputs["application"], "upstream-agentops-application-cases/1", args.eval_set_id, args.eval_id)
        expectation = _select(before_inputs["expectations"], "upstream-agentops-evaluator-expectations/1", args.eval_set_id, args.eval_id)
        obligations = _json(before_inputs["obligations"])
        _need(type(obligations) is dict and type(obligations.get("case_obligations")) is list, "unsupported frozen obligations document")
        selected = [item for item in obligations["case_obligations"] if type(item) is dict and item.get("eval_set_id") == args.eval_set_id and item.get("eval_id") == args.eval_id]
        _need(len(selected) == 1, "source obligation is missing or not unique")
        phase = "validate_closed_journal"
        reader, collector, assessor = _evaluators(before_sources)
        validation = reader(args.journal, expected_receipt_identity=before_instance["files"].get("service/runtime-stream/result.json"),
                            expected_observer_identity=_digest(before_sources["scripts/agentops_runtime_stream_v1.py"]))
        phase = "bind_instance_bootstrap_and_closed_journal"
        result["closed_stream_binding"] = _closed_stream_binding(args.instance, before_instance, validation, application)
        phase = "collect_instance_source_boundaries"
        boundaries = collector(args.instance, application)
        _need(sys.modules["interoperability.agentops_source_case_assessment_v1"]._same(
              boundaries.get("business_reader_identity"), _digest(before_sources["scripts/agentops_native_probe_v2.py"])),
              "executed retained business reader differs from pre-read evaluator source binding")
        result["boundary_collection"] = boundaries
        phase = "assess_separate_source_observation_lanes"
        result["assessment"] = assessor(validation, application, expectation, selected[0], boundaries,
            expected_native_user_id=args.native_user_id, expected_native_session_id=args.native_session_id,
            original_sanitizer_fixture=_json(before_inputs["original_sanitizer_fixture"]) if "original_sanitizer_fixture" in before_inputs else None,
            source_extraction_bindings=_json(before_inputs["answer_extraction_bindings"]) if "answer_extraction_bindings" in before_inputs else None)
        result["metric_status"] = result["assessment"]["configured_metric"]["overall_eval_status"]
        result["status"] = "assessed_separate_source_observation_lanes"
    except BaseException as error:
        result.update(status="failed", error_type=type(error).__name__, failure_phase=phase)
    finally:
        if allocated:
            try:
                result["input_bytes_unchanged_at_boundary_checks"] = len(before_inputs) == len(input_names) and all(_read(getattr(args, name)) == raw for name, raw in before_inputs.items())
                result["evaluator_source_bytes_unchanged_at_boundary_checks"] = set(SOURCES) <= set(before_sources) and all(_read(_source_path(relative)) == raw for relative, raw in before_sources.items())
                result["instance_membership_hashes_unchanged_at_boundary_checks"] = _inventory(args.instance) == before_instance if before_instance is not None else False
                if result["status"] != "failed" and not all(result[key] is True for key in ("input_bytes_unchanged_at_boundary_checks", "evaluator_source_bytes_unchanged_at_boundary_checks", "instance_membership_hashes_unchanged_at_boundary_checks")):
                    result.update(status="failed", error_type="ValueError", failure_phase="postassessment_identity_check", metric_status=None)
                result["assessment_eligible"] = result["status"] == "assessed_separate_source_observation_lanes"
                result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                _publish_result(args.output / "result.json", result)
            except BaseException as error:
                result.update(status="failed", error_type=type(error).__name__, failure_phase="retain_failure_or_identity_checks", metric_status=None, assessment_eligible=False)
                if not (args.output / "result.json").exists():
                    try: _publish_result(args.output / "result.json", result)
                    except BaseException: pass
                try: _write_json(args.output / "publication.failure.json", result)
                except BaseException: pass
    print(json.dumps({"schema_version": SCHEMA, "status": result["status"], "metric_status": result["metric_status"], "output": str(args.output),
                      **{key: result[key] for key in ("error_type", "failure_phase") if key in result}}, sort_keys=True))
    return 0 if result["status"] == "assessed_separate_source_observation_lanes" else 1


if __name__ == "__main__":
    raise SystemExit(main())
