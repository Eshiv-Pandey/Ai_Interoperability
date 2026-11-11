"""Record read-only V2 delta inspection and already completed control results."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
RUNNER = "scripts/run_ap2_original_native_provider_v2.py"
BINDER = "src/interoperability/ap2_public_original_binding_v2.py"
FILES = (RUNNER, BINDER, "scripts/ap2_public_scripted_continuation_v2.py",
         "src/interoperability/ap2_public_scripted_continuation_v2.py", "src/interoperability/ap2_public_task_read_v1.py",
         "tests/test_ap2_original_native_provider_v2.py", "tests/test_ap2_public_original_binding_v2.py")
EXPECTED_RUNNER = "ef6da20b1b499da44454371a40fd42807d9e7fe046ae2cd370d9499e20e2a35e"
EXPECTED_BINDER = "f5ecd810445c445b19cd6ce2cb99f714d47f137895b96a68b8c56c2d9cfc0787"


def record(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    if (OUT / "review.json").exists() or (OUT / "review.md").exists():
        raise ValueError("fresh_review_outputs_required")
    bindings = {name: record(ROOT / name) for name in FILES}
    assert bindings[RUNNER]["sha256"] == EXPECTED_RUNNER
    assert bindings[BINDER]["sha256"] == EXPECTED_BINDER
    v1_plan_path = ROOT / "runs/ap2-original-native-provider-development/v1/retained-42982595287-1/extracted/plan/plan.json"
    v1_plan = json.loads(v1_plan_path.read_bytes())
    for name, expected in v1_plan["owned_sources"].items():
        assert record(ROOT / name) == expected, "frozen_V1_owned_source_changed:" + name
    v1_archive = ROOT / "runs/ap2-original-native-provider-development/v1/retained-42982595287-1/artifact.zip"
    assert record(v1_archive)["sha256"] == "0b73d252058fe6d967a54e4cbe1646e1f08b0ac0d3711d82791b90dd445e6d0a"
    runner_text = (ROOT / RUNNER).read_text(encoding="utf-8")
    binder_text = (ROOT / BINDER).read_text(encoding="utf-8")
    caller_text = (ROOT / "src/interoperability/ap2_public_scripted_continuation_v2.py").read_text(encoding="utf-8")
    for name in FILES:
        ast.parse((ROOT / name).read_text(encoding="utf-8"))
    assert "MAX_CALLS, MIN_INTERVAL, MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES = 80, 6.0, 131072, 1048576" in runner_text
    assert "MAX_TOTAL_REQUEST_BYTES, MAX_TOTAL_USAGE_TOKENS = 200000, 100000" in runner_text
    assert "('correct-reply', {})" in runner_text and "('wrong-reply', {'otp_response': 'wrong-human-reply'})" in runner_text
    assert "('no-reply', {'otp_response': None})" in runner_text and "('foreign-context-recovery', {'fault': 'other_original_context'})" in runner_text
    assert "('repeat-completed', {'repeat_after_completed': True})" in runner_text
    assert "sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)" in runner_text
    assert "problem.errno != errno.EADDRINUSE" in runner_text
    assert "if not owned_listener(processes[index], port)" in runner_text
    assert "from .ap2_public_original_binding_v2 import verify_module" in caller_text
    assert "from .ap2_public_task_read_v1 import read_public_payment_task" in caller_text
    assert "struct.pack('!d', value)" in binder_text and "struct.pack('!d', value.real)" in binder_text and "struct.pack('!d', value.imag)" in binder_text
    tree = ast.parse(binder_text)
    fields = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "CODE_FIELDS" for target in node.targets)))
    assert len(fields) == 17 and {"co_code", "co_filename", "co_linetable", "co_exceptiontable", "co_qualname"} <= set(fields)
    assert "constant_fingerprint(code.co_consts)" in binder_text and "tuple(code.co_lines())" in binder_text and "tuple(code.co_positions())" in binder_text
    assert {name: record(ROOT / name) for name in FILES} == bindings
    report = {"schema_version": "ap2-original-native-provider-independent-V2-delta-review/1",
              "completed_at": datetime.now(timezone.utc).isoformat(), "status": "no_remaining_reviewed_delta_blocker_identified",
              "reviewer": "/root/native_v11_analysis", "review_source": record(Path(__file__)), "source_bindings": bindings,
              "frozen_V1_owned_sources_unchanged": True, "frozen_V1_owned_bindings": v1_plan["owned_sources"], "V1_retained_archive_unchanged": record(v1_archive),
              "V1_binder_current_bytes": record(ROOT / "src/interoperability/ap2_hp_original_binding_v1.py"),
              "reviewed_V2_source_bytes_stable": True,
              "controls": {"unique_completed_controls": 55, "runner_controls": 23, "binder_controls": 32,
                           "root_execution_provenance": "Parent /root reports 23 runner and 32 structural binder controls passed on the bound stable hashes; root requested no further repetition.",
                           "independent_peer_confirmation": {"agent": "/root/native_v11_analysis/v2_fingerprint_peer", "binder_controls": 32, "reported_seconds": 0.043, "passed": True,
                                "binder_sha256": EXPECTED_BINDER, "test_sha256": "e5b50878b8e9a8b1fc549b08221cf3ef2d2fa4f11a9ba7c86c0c3a31d7c7055a",
                                "timing_provenance": "Peer completed the already-started constructed suite before root's no-further-testing message arrived; no further tests ran."},
                           "new_suite_execution_by_this_reviewer": False},
              "closed_findings": [
                  "The V1 marshal-reference-sharing false-negative is replaced by 17 exact code fields, recursively typed co_consts and derived co_lines/co_positions; deprecated co_lnotab is derived from exact co_linetable.",
                  "Constructed controls accept marshal memo/reference-sharing differences only when structural attributes agree, and refuse opcode/constants/filename/line-table and other code-field mutations.",
                  "The reviewer demonstrated a pre-stable float.hex signed-NaN collision on constructed code constants. Final IEEE bytes now preserve NaN sign/payload and signed zero for float and complex components; relevant controls pass.",
                  "SO_REUSEADDR precedes bind-only preflight; only EADDRINUSE receives bounded preflight retries. Errno and sanitized messages are retained; probes do not contact a foreign listener.",
                  "Linux listening socket inode ownership is checked against the exact native PID before card requests; foreign/missing ownership suppresses requests.",
                  "V2 uses a new binder/caller/runner identity and keeps the original public read helper. All five case facts, original source/model, 80-call cap, six-second spacing, byte bounds and post-response token stop are unchanged."],
              "original_app_sdk_model_actor_solver_evaluator_checker_imports_or_executions": 0, "provider_requests_by_reviewer": 0,
              "scope": "Prospective V2 source and constructed-control delta review only; no V1 rerun, artifact mutation, regrading, Git or dispatch.",
              "limitations": ["Completed constructed controls and source inspection do not predict a V2 original-native/provider/task result.", "V1 remains five failed task attempts with zero business/public Task/receipt captures; only parent smoke generation and first-case native/card readiness were observed.", "No run.sh provisioning, unchanged ADK shopper, bridge, human gold, untouched holdout, exact wire attribution, whole-task, full-study or scientific checkpoint qualification is granted.", "The observed-token threshold is post-response stopping, not a hard token or cost ceiling."]}
    with (OUT / "review.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = """# Independent prospective V2 delta review

No remaining blocker was identified in the reviewed V2 deltas. The completed 55 constructed controls comprise 23 runner controls and 32 structural-verifier controls. An independent peer also confirmed the 32 binder controls on the same final hashes; this repetition is not added to the unique count. The reviewer followed root's request to avoid further suite execution.

The replacement preserves 17 code fields, recursively typed constants and line/position mappings while excluding marshal reference memoization. Harmless sharing differences are accepted; code/constant/filename/line-table changes are refused. The reviewer's constructed signed-NaN collision is fixed by exact IEEE float/complex component bytes, with sign/payload/signed-zero controls.

The port delta applies SO_REUSEADDR before bind-only probing, retries only EADDRINUSE within a bounded preflight interval, records sanitized errno/message observations, and checks exact Linux native PID/socket-inode ownership before card reads. It does not contact a foreign service during preflight. Five cases, original source/model and the 80-call/six-second/byte/post-response-usage limits remain unchanged.

All four frozen V1 owned-source bindings and the V1 archive hash remain unchanged. V1 remains five failed task attempts with zero business/public Task/receipt captures; only the parent smoke generated a model response. V2 controls grant no live task/provider, original run.sh/ADK shopper, bridge, human gold, holdout or scientific gate qualification. No original application/SDK/model or provider call was executed by this reviewer. Exact hashes and control provenance are in review.json.
"""
    with (OUT / "review.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(summary)
    print(json.dumps({"status": report["status"], "unique_completed_controls": 55, "review_sha256": record(OUT / "review.json")["sha256"], "V1_source_and_archive_bindings_unchanged": True, "provider_requests": 0}))


if __name__ == "__main__":
    main()
