"""Pure AP2 caller planning CLI; native execution deliberately unavailable.

This file never imports AP2/ADK/A2A, reads a key, starts a client or calls a
model. The multi-service source/environment/usage/bootstrap contract described
in the design is not yet implemented. --execute fails before loading inputs.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


def _strict(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key in planning input.")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Nonfinite JSON number in planning input.")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Pure planning input JSON; no native/source execution.")
    parser.add_argument("--message-id", help="Explicit fresh message ID for the next public message plan.")
    parser.add_argument("--inspect-source-footprint", type=Path, help="Retained sample src root; reads/hashes/parses four files, never imports them.")
    parser.add_argument("--execute", action="store_true", help="Refuses: source-bound native bootstrap/usage contract is not implemented.")
    args = parser.parse_args(argv)
    if args.execute:
        print(json.dumps({"schema_version": "ap2-hp-reference-client/1", "status": "refused_before_original_import",
                          "reason": "Native source/environment/usage/prospective-resource/bootstrap contract is not implemented.",
                          "original_imports": 0, "key_accesses": 0, "client_attempts": 0, "model_attempts": 0,
                          "native_execution_enabled": False}, sort_keys=True))
        return 3
    root = Path(__file__).resolve().parents[1]
    helper = root / "src/interoperability/ap2_hp_reference_plan_v1.py"
    spec = importlib.util.spec_from_file_location("_ap2_hp_pure_reference_plan", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plan = None
    try:
        if args.inspect_source_footprint is not None:
            files = {name: (args.inspect_source_footprint / name).read_bytes() for name in module.CALLER_FILES}
            result = module.inspect_caller_footprint(files)
        else:
            if args.input is None:
                parser.error("--input or --inspect-source-footprint is required in pure planning mode")
            value = _strict(args.input.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or set(value) != {"contract", "observations"} or not isinstance(value["observations"], list):
                raise ValueError("Exact contract/observations planning fields are required.")
            plan = module.ReferencePlan(value["contract"])
            for observation in value["observations"]:
                if not isinstance(observation, dict) or set(observation) != {"phase", "value"}:
                    raise ValueError("Exact phase/value supplied observation fields are required.")
                plan.observe(observation["phase"], observation["value"])
            result = plan.report()
            result["next_action"] = plan.next_action(message_id=args.message_id)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, SyntaxError) as error:
        print(json.dumps({"schema_version": "ap2-hp-reference-client/1", "status": "planning_input_refused",
                          "reason": str(error), "refused_phase": plan.phase if plan is not None else None,
                          "accepted_supplied_phases": len(plan.observations) if plan is not None else 0,
                          "native_execution_enabled": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
