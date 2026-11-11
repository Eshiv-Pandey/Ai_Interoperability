"""Independent, constructed pre-dispatch review. No original app/provider calls."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
RUNNER = "scripts/run_ap2_original_native_provider_v1.py"
FILES = (
    RUNNER,
    "tests/test_ap2_original_native_provider_v1.py",
    "scripts/ap2_public_scripted_continuation_v1.py",
    "src/interoperability/ap2_public_scripted_continuation_v1.py",
    "src/interoperability/ap2_public_task_read_v1.py",
    "tests/test_ap2_public_scripted_continuation_v1.py",
    "tests/test_ap2_public_task_read_v1.py",
    "tests/ap2_public_control_support_v1.py",
    "docs/research/ap2-original-native-provider-protocol-v1.md",
)
CONTROLS = (
    "tests/test_ap2_original_native_provider_v1.py",
    "tests/test_ap2_public_scripted_continuation_v1.py",
    "tests/test_ap2_public_task_read_v1.py",
)


def record(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def dump(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if (OUT / "review.json").exists() or (OUT / "review.md").exists():
        raise ValueError("fresh_review_outputs_required")
    bound = list(FILES) + [p.relative_to(ROOT).as_posix() for p in sorted(
        (ROOT / "tests/fixtures/ap2-public-continuation-v1").rglob("*")) if p.is_file()]
    before = {name: record(ROOT / name) for name in bound}
    results = []
    for name in CONTROLS:
        command = [sys.executable, "-B", str(ROOT / name)]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=90)
        log = OUT / (Path(name).stem + ".log")
        with log.open("xb") as stream:
            stream.write(completed.stdout + completed.stderr)
        output = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
        count = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", output)
        if completed.returncode != 0 or count is None or not output.rstrip().endswith("OK"):
            raise AssertionError("constructed_controls_failed:" + name)
        results.append({"source": name, "command": command, "exit_code": completed.returncode,
                        "tests": int(count.group(1)), "reported_seconds": float(count.group(2)),
                        "log": record(log), "log_path": log.relative_to(ROOT).as_posix(),
                        "constructed_only": True, "original_app_or_provider_executed": False})

    spec = importlib.util.spec_from_file_location("owned_read_only_pre_dispatch", ROOT / RUNNER)
    owned = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owned)
    ap2, x402, versions = owned.source_records(), owned.x402_source_records(), owned.expected_versions()
    facts, fields = owned.task_facts(), owned.fixed_plan_fields()
    assert len(ap2) == 136 and len(x402) == 24 and len(versions) == 182 and len(facts) == 5
    assert owned.MAX_CALLS == 80 and owned.MIN_INTERVAL == 6.0
    assert owned.MAX_TOTAL_REQUEST_BYTES == 200000 and owned.MAX_TOTAL_USAGE_TOKENS == 100000
    assert owned.MAX_REQUEST_BYTES == 131072 and owned.MAX_RESPONSE_BYTES == 1048576
    assert fields["limits"]["upstream_calls_including_smoke"] == 80
    assert not fields["human_gold_qualified"] and not fields["held_out_study"]
    assert not fields["original_run_sh_provisioning_qualified"] and not fields["unchanged_adk_shopper_qualified"]
    assert fields["provider_requests"] == 0

    tree = ast.parse((ROOT / "scripts/ap2_public_scripted_continuation_v1.py").read_text(encoding="utf-8"))
    caller_main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = {ast.unparse(n.value.func): i for i, n in enumerate(caller_main.body)
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)}
    for name in ("platform.uname", "platform.processor", "platform.platform", "platform.architecture"):
        assert calls[name] < calls["sys.addaudithook"]
    after = {name: record(ROOT / name) for name in bound}
    if after != before:
        raise AssertionError("reviewed_bytes_changed_during_controls")

    findings = [
        {"id": "native-source-and-entrypoints", "disposition": "verified_source_contract",
         "detail": "Exact 136-file AP2 tree and 24-file x402 tree membership and hashes; original native modules, RPC routes and source-supported SDK base URL.",
         "references": [RUNNER + ":40", RUNNER + ":91", RUNNER + ":110", RUNNER + ":328", RUNNER + ":508"]},
        {"id": "frozen-plan-and-owned-bytes", "disposition": "fixed_and_verified",
         "detail": "Fixed model/provider/limits/source/env/qualification fields use type-sensitive JSON comparison; exact OWNED membership and hashes checked before execution.",
         "references": [RUNNER + ":142", RUNNER + ":441"]},
        {"id": "prospective-cap-delta", "disposition": "fixed_before_freeze_or_dispatch",
         "detail": "60-call proposal changed prospectively to 80; concurrency control confirms 80 sends, four local refusals and 160 started/finished rows. Five cases and other limits unchanged. Static ideal64 accounting does not prove actual provider sufficiency.",
         "references": [RUNNER + ":38", "tests/test_ap2_original_native_provider_v1.py:39", "docs/research/ap2-original-native-provider-protocol-v1.md:77"]},
        {"id": "usage-and-hard-limits", "disposition": "fixed_and_verified",
         "detail": "One serial ledger accounts smoke and nested SDK calls; 6-second pacing, request/response/total-byte bounds. Missing successful usage is sticky unknown-usage stop. 100000 observed tokens is explicitly post-response stopping and can be crossed by the last response.",
         "references": [RUNNER + ":211", RUNNER + ":245", RUNNER + ":272"]},
        {"id": "deadline-cleanup-terminal-census", "disposition": "fixed_and_verified_source_and_constructed_controls",
         "detail": "Readiness/caller waits use remaining screen deadline; cleanup failures are retained; boundary closes before server shutdown, then serial provider lock drains before terminal census. Cleanup/drain can extend wall time beyond execution deadline.",
         "references": [RUNNER + ":409", RUNNER + ":513", RUNNER + ":528", RUNNER + ":537", RUNNER + ":547"]},
        {"id": "credential-private-state-and-caller-isolation", "disposition": "verified_source_and_constructed_controls",
         "detail": "Real key stays in parent; services get synthetic key and accounting URL, caller gets no key. Fresh temporary original state stays outside retained output. Scanner rejects secret/private-key material. Caller denies benchmark/private journals, external network and descendants.",
         "references": [RUNNER + ":328", RUNNER + ":429", RUNNER + ":501", "scripts/ap2_public_scripted_continuation_v1.py:111"]},
        {"id": "authority-errors-and-wire-state", "disposition": "fixed_and_verified_source_and_constructed_controls",
         "detail": "Only actual expected public authority mismatch/task-not-found errors qualify recovery; unexpected transport/RPC errors remain failures. Raw retained state is input-required; the caller correctly accepts that exact hyphenated state.",
         "references": ["src/interoperability/ap2_public_scripted_continuation_v1.py:160", "src/interoperability/ap2_public_scripted_continuation_v1.py:216", "tests/test_ap2_public_scripted_continuation_v1.py:78"]},
        {"id": "platform-prewarm-ordering", "disposition": "verified_source_and_constructed_control",
         "detail": "uname, processor, platform and architecture warm before strict actor audit. Descendant denial remains unconditional. The AST control proves source ordering, not actual native runtime compatibility.",
         "references": ["scripts/ap2_public_scripted_continuation_v1.py:98", "scripts/ap2_public_scripted_continuation_v1.py:149", "tests/test_ap2_public_scripted_continuation_v1.py:92"]},
    ]
    report = {
        "schema_version": "ap2-original-native-provider-independent-pre-dispatch-review/1",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "/root/native_v11_analysis", "status": "no_remaining_source_or_constructed_control_blocker_identified",
        "scope": "specifically bounded five-case prospective development dispatch",
        "review_source": record(Path(__file__)), "source_bindings": before,
        "reviewed_bytes_unchanged_during_controls": True,
        "read_only_source_census": {"ap2_files": len(ap2), "x402_files": len(x402), "required_versions": len(versions)},
        "controls": results, "constructed_control_count": sum(r["tests"] for r in results),
        "fixed_plan_fields": fields, "declared_case_ids": [row["case_id"] for row in facts],
        "findings": findings,
        "provider_requests_made_by_review": 0, "original_application_model_actor_solver_evaluator_checker_executions_by_review": 0,
        "real_provider_credential_value_read_printed_or_persisted_by_review": False,
        "prior_control_result": {"tests": 19, "reported_seconds": 6.310, "exit_code": 0,
                                 "revision": "pre-80 proposal", "source": "resumed unified exec session 98883"},
        "limitations": [
            "Live provider capacity, model routing and native task outcomes remain unobserved by this review.",
            "This treatment does not qualify original run.sh provisioning or the unchanged ADK autonomous shopper.",
            "Source contracts and constructed controls do not establish exact A2A wire attribution, untouched holdout, human gold, independent bridge qualification or whole-task success.",
            "The usage threshold is a post-response stop, not a strict token quota or cost ceiling.",
            "AI-authored proposed answers remain exposed and human-unreviewed; 68 candidates, 48 family identities, 96 slots, 288 path cells and 96 additional crossings are unaffected.",
            "This review performs no allocation, freeze, dispatch, Git mutation, checkpoint credit or retention adjudication.",
        ],
    }
    dump(OUT / "review.json", report)
    rows = ["# Independent original native AP2 provider pre-dispatch review", "",
            "No remaining source or constructed-control blocker was identified for the specifically bounded five-case prospective development dispatch.", "",
            f"All {report['constructed_control_count']} constructed controls passed on stable bytes: 19 provider-ledger/runtime controls and 14 caller/public-read controls. The read-only source census verified all 136 AP2 files, 24 x402 files and 182 required versions. This review made zero provider requests and executed no original application, model, actor, solver, evaluator or checker.", "",
            "The prospective cap is 80 calls including smoke; six-second serial pacing, 200,000 cumulative request bytes and the 100,000 observed-token post-response stop remain unchanged. A stale 60-call plan is refused by the fixed-field comparison. The 100,000-token threshold is not a hard token or cost ceiling.", "",
            "The review confirms exact source membership/hash bindings, frozen owned bytes, original module/routes, private-state and credential separation, caller authority/error boundaries, deadline/cleanup census and platform bootstrap ordering. Detailed findings, source references, exact hashes and retained control logs are in `review.json`.", "",
            "Live provider capacity/model routing and original native task outcomes remain unobserved by this audit. It grants no run.sh provisioning, unchanged ADK shopper, bridge, human gold, untouched holdout, whole-task, full-study or checkpoint credit. Root owns freeze, dispatch and retained-result adjudication.", ""]
    with (OUT / "review.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(rows))
    print(json.dumps({"review": str(OUT / "review.json"), "status": report["status"],
                      "constructed_controls": report["constructed_control_count"], "provider_requests": 0,
                      "review_sha256": record(OUT / "review.json")["sha256"]}))


if __name__ == "__main__":
    main()
