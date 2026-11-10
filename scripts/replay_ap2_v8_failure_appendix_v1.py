"""Replay the frozen failure-appendix audit to a fresh evidence output."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "runs") or output.exists():
        raise ValueError("fresh_workspace_run_output_required")
    spec = importlib.util.spec_from_file_location(
        "_frozen_failure_appendix_auditor_v1",
        ROOT / "paper/audit_ap2_v8_native_smoke_failure_appendix_v1.py")
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    result = auditor.audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "checks": len(result["checks"]),
                      "output": output.relative_to(ROOT).as_posix(),
                      "new_application_or_provider_calls": 0}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
