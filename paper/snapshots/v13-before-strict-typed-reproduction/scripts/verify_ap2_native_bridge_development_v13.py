"""Read-only successor verification of an existing source-bound V13 analysis.

The preserved analyzer reconstructs retained artifacts without actor, evaluator,
solver, checker or provider execution. Only its new analysis timestamp differs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "scripts/analyze_ap2_native_bridge_development_v13.py"


def same_analysis_except_creation_timestamp(saved, derived):
    if type(saved) is not dict or type(derived) is not dict:
        return False
    if type(saved.get("created_at_utc")) is not str or type(derived.get("created_at_utc")) is not str:
        return False
    return {key: value for key, value in saved.items() if key != "created_at_utc"} == {
        key: value for key, value in derived.items() if key != "created_at_utc"}


def verify_existing(base, analysis_path):
    analysis_path = Path(analysis_path)
    if analysis_path.is_symlink():
        raise ValueError("existing_analysis_link_refused")
    analysis_path = analysis_path.resolve()
    if (not analysis_path.is_relative_to(ROOT / "runs/ap2-native-bridge-development/v13")
            or analysis_path.name != "result.json" or not analysis_path.is_file()):
        raise ValueError("existing_actual_V13_analysis_required")
    before = analysis_path.read_bytes()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_existing_analysis_JSON_key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("nonfinite_existing_analysis_JSON_value")
    saved = json.loads(before, object_pairs_hook=unique, parse_constant=invalid)
    source = ANALYZER.read_bytes()
    expected = {"path": ANALYZER.relative_to(ROOT).as_posix(), "bytes": len(source),
                "sha256": hashlib.sha256(source).hexdigest()}
    bindings = [row for row in saved["evidence"] if row["path"] == expected["path"]]
    if bindings != [expected]:
        raise ValueError("preserved_analyzer_source_identity_changed")
    # Check the bound bytes before loading them. Compile the exact checked
    # source to avoid writing bytecode or loading a different cached revision.
    spec = importlib.util.spec_from_file_location("_preserved_ap2_v13_analysis", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, str(ANALYZER), "exec"), module.__dict__)
    derived = module.analyze(Path(base))
    module.need(analysis_path.parent.name == f"analysis-{derived['run_id']}-{derived['run_attempt']}",
                "actual_run_and_attempt_analysis_path_required")
    module.need(same_analysis_except_creation_timestamp(saved, derived),
                "existing_V13_analysis_differs_from_reconstructed_evidence")
    module.need(analysis_path.read_bytes() == before, "existing_analysis_changed_during_readonly_verification")
    return {"status": "existing_V13_analysis_verified_without_writes", "run_id": derived["run_id"],
            "run_attempt": derived["run_attempt"], "analysis_identity": module.identity(before),
            "ignored_comparison_fields": ["created_at_utc"],
            "preserved_analyzer_identity": expected,
            "new_actor_evaluator_solver_checker_or_provider_calls": 0}


def self_check():
    original = {"created_at_utc": "old", "run_id": 1, "evidence": [{"sha256": "a"}],
                "totals": {"verified": 104}, "cells": [{"status": "retained"}]}
    changed = deepcopy(original)
    changed["created_at_utc"] = "new"
    if not same_analysis_except_creation_timestamp(original, changed):
        raise ValueError("constructed_timestamp_only_comparison_rejected")
    mutations = [
        lambda value: value.__setitem__("run_id", 2),
        lambda value: value["evidence"][0].__setitem__("sha256", "b"),
        lambda value: value["totals"].__setitem__("verified", 103),
        lambda value: value["cells"][0].__setitem__("status", "missing"),
        lambda value: value.__setitem__("unexpected_field", True),
        lambda value: value.pop("created_at_utc"),
    ]
    for mutate in mutations:
        changed = deepcopy(original)
        mutate(changed)
        if same_analysis_except_creation_timestamp(original, changed):
            raise ValueError("constructed_non_timestamp_change_accepted")
    return {"constructed_controls_passed": 1 + len(mutations), "actual_analysis_claimed": False,
            "new_actor_evaluator_solver_checker_or_provider_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-existing", action="store_true")
    mode.add_argument("--self-check", action="store_true")
    parser.add_argument("--base", type=Path)
    parser.add_argument("--analysis", type=Path)
    args = parser.parse_args()
    if args.self_check:
        if args.base is not None or args.analysis is not None:
            parser.error("self-check takes no retained artifact paths")
        result = self_check()
    else:
        if args.base is None or args.analysis is None:
            parser.error("--verify-existing requires --base and --analysis")
        result = verify_existing(args.base, args.analysis)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
