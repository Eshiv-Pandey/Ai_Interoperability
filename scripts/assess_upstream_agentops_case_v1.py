"""Evaluate one source-case trajectory from a retained complete passive journal.

This evaluator process reads references; the application process never does.
Output is a new exclusive evidence directory, including failures. No SDK,
credential, model, tool or original runtime is imported or executed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import stat
import sys


SCHEMA = "upstream-agentops-case-evaluator/1"
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("scripts/assess_upstream_agentops_case_v1.py", "src/interoperability/__init__.py",
           "src/interoperability/agentops_runtime_stream_evidence_v1.py",
           "src/interoperability/agentops_source_case_assessment_v1.py",
           "src/interoperability/agentops_required_trajectory_v1.py")


def _need(value, reason):
    if not value:
        raise ValueError(reason)


def _regular(path, directory=False):
    path = Path(path).absolute()
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
              "linked/reparse evaluator path is unsupported")
    _need(path.is_dir() if directory else path.is_file(), "nonregular evaluator path")
    return path


def _digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _read(path, maximum=16 * 1024 * 1024):
    path = _regular(path)
    _need(path.stat().st_size <= maximum, "evaluator input exceeds byte bound")
    raw = path.read_bytes()
    _need(len(raw) <= maximum, "evaluator input grew beyond byte bound")
    return raw


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, "duplicate evaluator JSON member")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("nonfinite evaluator JSON")
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)
    json.dumps(result, allow_nan=False)
    return result


def _write(path, raw):
    _regular(path.parent, True)
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("evaluator evidence short write")


def _write_json(path, value):
    _write(path, (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def _publish_result(path, value):
    """Qualifying final JSON appears only after pending write/flush/fsync/close.

    A failed publication retains an empty owned final reservation and any
    pending bytes. Neither is a usable final receipt. Directory-entry crash
    durability and filesystem authentication are not established here.
    """
    _regular(path.parent, True)
    pending = path.with_name(path.name + ".pending")
    _need(not path.exists() and not path.is_symlink() and not pending.exists() and not pending.is_symlink(),
          "preserve existing final/pending evaluator receipt")
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        placeholder = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    with pending.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("evaluator receipt short write")
        stream.flush()
        os.fsync(stream.fileno())
    _need(_read(pending) == raw, "pending evaluator receipt bytes differ")
    final = _regular(path).stat()
    _need((final.st_dev, final.st_ino, final.st_size) == (placeholder.st_dev, placeholder.st_ino, 0)
          and path.read_bytes() == b"", "owned final receipt placeholder changed")
    os.replace(pending, path)


def _inventory(directory):
    directory = _regular(directory, True)
    files, directories, total = {}, [], 0
    for path in sorted(directory.rglob("*")):
        _regular(path, path.is_dir())
        relative = path.relative_to(directory).as_posix()
        if path.is_dir():
            directories.append(relative)
        else:
            _need(len(files) < 8193, "journal inventory file count exceeds bound")
            raw = _read(path, 4 * 1024 * 1024)
            total += len(raw)
            _need(total <= 68 * 1024 * 1024, "journal inventory aggregate bytes exceed bound")
            files[relative] = _digest(raw)
    return {"files": files, "directories": directories}


def _select(raw, schema, eval_set_id, eval_id):
    document = _json(raw)
    _need(type(document) is dict and set(document) == {"schema_version", "provenance", "cases"}
          and document["schema_version"] == schema and type(document["provenance"]) is dict
          and type(document["cases"]) is list and all(type(case) is dict for case in document["cases"]),
          "unsupported source projection document")
    selected = [case for case in document["cases"]
                if case.get("eval_set_id") == eval_set_id and case.get("eval_id") == eval_id]
    _need(len(selected) == 1, "source case is missing or not unique")
    return selected[0]


def _evaluators():
    # Only these frozen pure stdlib helpers enter the evaluator import route.
    helper_src = str((ROOT / "src").resolve())
    sys.path[:] = [helper_src, *[item for item in sys.path if item != helper_src]]
    modules = {}
    for name in ("interoperability", "interoperability.agentops_runtime_stream_evidence_v1",
                 "interoperability.agentops_source_case_assessment_v1", "interoperability.agentops_required_trajectory_v1"):
        module = import_module(name)
        relative = "src/interoperability/__init__.py" if name == "interoperability" else "src/" + name.replace(".", "/") + ".py"
        _need(type(getattr(module, "__file__", None)) is str and Path(module.__file__).resolve() == (ROOT / relative).resolve(),
              "evaluator helper module origin differs")
        modules[name] = module
    return (modules["interoperability.agentops_runtime_stream_evidence_v1"].read_closed_journal,
            modules["interoperability.agentops_source_case_assessment_v1"].assess_source_case)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("journal", "application", "expectations", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("eval-set-id", "eval-id", "native-user-id", "native-session-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    for name in ("journal", "application", "expectations", "output"):
        setattr(args, name, getattr(args, name).absolute())
    return args


def main(argv=None):
    args = parse_args(argv)
    phase, allocated = "exclusive_output_allocation", False
    result = {"schema_version": SCHEMA, "status": "failed", "metric_status": None,
              "assessment": None, "source_authentication_proven": False, "native_authentication_proven": False,
              "native_qualification_established": False, "native_source_case_qualification": False,
              "process_exit_proven": False, "public_raw_binding_checked": False, "state_effects_proven": False,
              "benchmark_grade_proven": False, "full_task_grade_assigned": False,
              "continuous_input_immutability_proven": False, "caller_native_ids_are_authenticated": False,
              "assessment_eligible": False, "input_bindings": {}, "evaluator_source_bindings": {}, "journal_binding": None,
              "directory_entry_crash_durability_proven": False,
              "final_receipt_publication_protocol": "exclusive pending fsync/close; owned empty final reservation; atomic replacement",
              "started_at_utc": datetime.now(timezone.utc).isoformat()}
    before_inputs, before_sources, before_journal = {}, {}, None
    try:
        _need(not args.output.exists() and not args.output.is_symlink(), "preserve existing evaluator output")
        _regular(args.output.parent, True)
        for protected in (args.journal, args.application, args.expectations, ROOT / "src", ROOT / "scripts"):
            _need(not args.output.resolve().is_relative_to(protected.resolve())
                  and not protected.resolve().is_relative_to(args.output.resolve()), "evaluator output overlaps input/source")
        args.output.mkdir(exist_ok=False)
        allocated = True
        _write_json(args.output / "plan.json", {"schema_version": SCHEMA, "arguments": {name: str(value) for name, value in vars(args).items()},
                    "runtime_requests": 0, "model_calls": 0, "credential_reads": 0,
                    "references_loaded_only_in_evaluator_process": True})
        phase = "capture_read_only_input_bindings"
        for name in ("application", "expectations"):
            before_inputs[name] = _read(getattr(args, name))
            result["input_bindings"][name] = {"path": str(getattr(args, name)), **_digest(before_inputs[name])}
        for relative in SOURCES:
            before_sources[relative] = _read(ROOT / relative)
            result["evaluator_source_bindings"][relative] = _digest(before_sources[relative])
            target = args.output / "source" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            _write(target, before_sources[relative])
        before_journal = _inventory(args.journal)
        result["journal_binding"] = {"path": str(args.journal), **before_journal}
        _write_json(args.output / "bindings.before.json", {key: result[key] for key in ("input_bindings", "evaluator_source_bindings", "journal_binding")})
        phase = "select_source_case"
        application = _select(before_inputs["application"], "upstream-agentops-application-cases/1", args.eval_set_id, args.eval_id)
        expectation = _select(before_inputs["expectations"], "upstream-agentops-evaluator-expectations/1", args.eval_set_id, args.eval_id)
        phase = "validate_closed_journal"
        read_journal, assess = _evaluators()
        validation = read_journal(args.journal, expected_receipt_identity=before_journal["files"].get("result.json"))
        result["validated_journal_receipt_identity"] = validation["receipt_identity"]
        result["validated_journal_observer_identity"] = validation["observer_identity"]
        phase = "assess_configured_source_metric"
        result["assessment"] = assess(validation, application, expectation, expected_native_user_id=args.native_user_id,
                                      expected_native_session_id=args.native_session_id)
        result["metric_status"] = result["assessment"]["configured_metric"]["overall_eval_status"]
        result["status"] = "assessed_configured_metric_only"
    except BaseException as error:
        result.update(status="failed", error_type=type(error).__name__, failure_phase=phase)
    finally:
        if allocated:
            try:
                result["input_bytes_unchanged_at_boundary_checks"] = len(before_inputs) == 2 and all(_read(getattr(args, name)) == raw for name, raw in before_inputs.items())
                result["evaluator_source_bytes_unchanged_at_boundary_checks"] = len(before_sources) == len(SOURCES) and all(_read(ROOT / relative) == raw for relative, raw in before_sources.items())
                result["journal_membership_hashes_unchanged_at_boundary_checks"] = _inventory(args.journal) == before_journal if before_journal is not None else False
                if result["status"] != "failed" and not all(result[key] is True for key in (
                        "input_bytes_unchanged_at_boundary_checks", "evaluator_source_bytes_unchanged_at_boundary_checks",
                        "journal_membership_hashes_unchanged_at_boundary_checks")):
                    result.update(status="failed", error_type="ValueError", failure_phase="postassessment_identity_check", metric_status=None)
                result["assessment_eligible"] = result["status"] == "assessed_configured_metric_only"
                result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                _publish_result(args.output / "result.json", result)
            except BaseException as error:
                result.update(status="failed", error_type=type(error).__name__, failure_phase="retain_failure_or_identity_checks", metric_status=None,
                              assessment_eligible=False)
                # A failed identity read may precede any final reservation.
                if not (args.output / "result.json").exists():
                    try:
                        _publish_result(args.output / "result.json", result)
                    except BaseException:
                        pass
                # Keep failures separate from incomplete final/pending evidence.
                try:
                    _write_json(args.output / "publication.failure.json", result)
                except BaseException:
                    pass
    print(json.dumps({"schema_version": SCHEMA, "status": result["status"], "metric_status": result["metric_status"],
                      "output": str(args.output), **{key: result[key] for key in ("error_type", "failure_phase") if key in result}}, sort_keys=True))
    return 0 if result["status"] == "assessed_configured_metric_only" and result["metric_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
