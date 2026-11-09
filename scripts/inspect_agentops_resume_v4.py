"""Revalidate a prepared, unexecuted native control after a session handoff."""
from __future__ import annotations

import json
from pathlib import Path

import agentops_native_probe_v3 as native


def main() -> None:
    original = native.original
    prepared = native.RUNS / "native-probe-v3"
    output = native.RUNS / "session-resume-v4"
    output.mkdir(exist_ok=False)
    (output / "temp").mkdir()
    result = {"schema_version": "agentops-session-resume/4",
              "started_at_utc": original.now(), "status": "failed",
              "application_requests": 0, "model_calls": 0}
    try:
        plan = original.load_json(prepared / "plan.json")
        result["execution_reserved"] = (prepared / "execution.json").exists()
        result["result_exists"] = (prepared / "result.json").exists()
        result["source_matches_plan"] = original.source_inventory() == plan["source_files"]
        result["harness_matches_plan"] = native.harness() == plan["harness_files"]
        environment = original.clean_environment(output)
        runtime = native.runtime_inspection(output, "current-runtime", environment)
        result["runtime_matches_plan"] = runtime == json.loads(
            (native.ROOT / plan["runtime_inventory"]["path"]).read_bytes())
        code = ("from pathlib import Path; import sys; "
                "p=Path(sys.argv[1]); p.mkdir(mode=0o700); "
                "(p/'probe.txt').write_text('directory capability probe',encoding='utf-8'); "
                "assert (p/'probe.txt').read_text(encoding='utf-8')=='directory capability probe'; "
                "print('mode0700 write/read passed')")
        receipt = original.capture(
            [str(native.RUNTIME), "-I", "-c", code, str(output / "mode0700")],
            output=output, label="directory-capability", cwd=output,
            environment=environment, timeout=30)
        result["directory_capability"] = receipt["returncode"] == 0
        result["normal_terminal_required"] = not result["directory_capability"]
        if not all(result[key] for key in
                   ("source_matches_plan", "harness_matches_plan", "runtime_matches_plan")):
            raise ValueError("Prepared source, harness or runtime changed")
        result["status"] = "prepared_control_revalidated"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    result["finished_at_utc"] = original.now()
    original.write_json(output / "result.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
