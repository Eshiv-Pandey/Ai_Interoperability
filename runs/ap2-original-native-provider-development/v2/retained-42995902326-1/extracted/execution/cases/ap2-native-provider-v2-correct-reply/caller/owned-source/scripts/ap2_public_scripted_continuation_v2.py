"""Prospective V2 source-bound caller process for prepared original services.

This runner starts no native service and performs no model inference. A parent
must provide one fresh task's original merchant/processor/credential services,
fresh signing/database state, and retained public human facts. It is a distinct
owned scripted-caller treatment, not an unchanged original ADK tool surface.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys


STAGE_SHA256 = "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463"
ENVIRONMENT_SHA256 = "4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5"
AP2_PIN = "e1ea56db72a6385bce3e5c1112b3a56ce60acb43"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-stage", type=Path, required=True)
    parser.add_argument("--environment-manifest", type=Path, required=True)
    parser.add_argument("--environment-manifest-sha256")
    parser.add_argument("--site-packages", type=Path)
    parser.add_argument("--task-root", type=Path)
    parser.add_argument("--samples-root", type=Path, required=True)
    parser.add_argument("--public-human-facts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage_raw = args.source_stage.read_bytes()
    environment_raw = args.environment_manifest.read_bytes()
    if hashlib.sha256(stage_raw).hexdigest() != STAGE_SHA256:
        raise ValueError("The pinned original AP2 source-stage manifest differs.")
    environment_sha256 = hashlib.sha256(environment_raw).hexdigest()
    expected_environment_sha256 = args.environment_manifest_sha256 or ENVIRONMENT_SHA256
    if environment_sha256 != expected_environment_sha256:
        raise ValueError("The prospective installed runtime manifest differs from its supplied hash.")
    stage, environment = json.loads(stage_raw), json.loads(environment_raw)
    portable_runtime = environment_sha256 != ENVIRONMENT_SHA256
    if portable_runtime:
        if not args.environment_manifest_sha256 or args.site_packages is None:
            raise ValueError("A portable runtime needs an explicit manifest hash and site-packages path.")
        if (environment.get("source_stage_sha256") != STAGE_SHA256
                or environment.get("original_windows_environment_sha256") != ENVIRONMENT_SHA256):
            raise ValueError("Portable runtime must separately bind original source and Windows evidence hashes.")
        if Path(environment["python_executable"]).resolve() != Path(sys.executable).resolve():
            raise ValueError("The caller interpreter differs from its prospective runtime binding.")
        if environment["python_version"] != sys.version.split()[0]:
            raise ValueError("The caller Python version differs from its prospective runtime binding.")
        portable_site_packages = args.site_packages.resolve(strict=True)
        if Path(environment["site_packages"]).resolve(strict=True) != portable_site_packages:
            raise ValueError("The supplied portable site-packages path differs from its manifest.")
        report = environment["pip_report"]
        report_raw = Path(report["path"]).read_bytes()
        if hashlib.sha256(report_raw).hexdigest() != report["sha256"]:
            raise ValueError("The retained prospective pip report changed.")
        def distribution_name(value):
            return value.lower().replace("_", "-").replace(".", "-")
        declared_distributions = {distribution_name(name): version for name, version in environment["distributions"].items()}
        actual_distributions = {distribution_name(dist.metadata["Name"]): dist.version
                                for dist in importlib.metadata.distributions(path=[str(portable_site_packages)])}
        if actual_distributions != declared_distributions:
            raise ValueError("Actual portable installed distributions differ from the prospective manifest.")
        for row in json.loads(report_raw).get("install", []):
            metadata = row["metadata"]
            if actual_distributions.get(distribution_name(metadata["name"])) != metadata["version"]:
                raise ValueError("An installed portable distribution differs from its pip report.")
    if stage["ap2_commit"] != AP2_PIN:
        raise ValueError("The original AP2 source pin differs.")
    if not args.public_human_facts.name.endswith(".public-human-facts.json"):
        raise ValueError("An explicitly named prospective public human-facts file is required.")
    facts_raw = args.public_human_facts.read_bytes()
    facts = json.loads(facts_raw)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    task_root = args.task_root.resolve(strict=True) if args.task_root else output.parent.resolve(strict=True)
    private_db = Path(os.environ.get("TEMP_DB_DIR", "")).resolve()
    if not private_db.is_relative_to(task_root) or private_db == task_root:
        raise ValueError("Original TEMP_DB_DIR must be inside this fresh task's parent directory.")
    if (private_db / "agent_provider_signing_key.pem").exists():
        raise ValueError("This caller requires a previously uncreated original signing key.")
    if os.environ.get("PAYMENT_METHOD", "CARD") != "CARD":
        raise ValueError("This prospective caller is scoped to the original card-payment profile.")
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "AGENT_PROVIDER_SIGNING_KEY_PEM"):
        if os.environ.get(name):
            raise ValueError("Caller process must not inherit provider credentials or preloaded signing keys.")
    if Path(os.environ.get("AGENT_PROVIDER_PUBLIC_KEY_PATH", "")).resolve() != private_db / "agent_provider_signing_key.pub":
        raise ValueError("Original business verification must use this task's fresh original caller public key.")
    repo_root = Path(__file__).resolve().parents[1]
    environment_root = Path(environment["root"]).resolve(strict=True)
    # Warm the standard-library platform cache before the strict actor audit.
    # This permits no application/model imports and avoids later implicit
    # platform helper subprocesses being confused with actor descendants.
    platform.uname()
    platform.processor()
    platform.platform()
    platform.architecture()
    platform_bootstrap = {
        "module_sha256": hashlib.sha256(Path(platform.__file__).read_bytes()).hexdigest(),
        "calls_before_actor_audit": ["platform.uname", "platform.processor", "platform.platform", "platform.architecture"],
        "arbitrary_actor_descendants_permitted": False,
    }

    denials = {"private_reads": 0, "outside_task_writes": 0, "external_network": 0, "descendants": 0}
    forbidden_names = {"evaluator.json", "qualification-private-v1.json", "run_ap2_task_qualification_v1.py",
                       "ap2_task_qualification_evaluator_v1.py", ".env"}
    def owned_host(value):
        if type(value) is bytes:
            try:
                value = value.decode("ascii")
            except UnicodeDecodeError:
                return None
        return value if value in {"localhost", "127.0.0.1", "::1"} else None
    def guard(event, values):
        if event == "open" and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).resolve()
            mode = values[1] if len(values) > 1 else None
            flags = values[2] if len(values) > 2 and isinstance(values[2], int) else 0
            writes = (isinstance(mode, str) and any(char in mode for char in "wax+")) or bool(flags & (os.O_WRONLY | os.O_RDWR))
            if writes and not (path.is_relative_to(task_root) or path.is_relative_to(output)):
                denials["outside_task_writes"] += 1
                raise PermissionError("caller_write_outside_fresh_task_denied")
            if not writes and (path.name.lower() in forbidden_names or path.suffix.lower() == ".jsonl"
                               or path.name.lower().startswith("gemini-api-key")
                               or path.is_relative_to(repo_root / "benchmark")
                               or (path.suffix.lower() in {".pem", ".key"}
                                   and not path.is_relative_to(task_root) and not path.is_relative_to(environment_root))):
                denials["private_reads"] += 1
                raise PermissionError("evaluator_or_journal_or_credential_read_denied")
        if event in {"socket.connect", "socket.connect_ex"}:
            address = values[1] if len(values) > 1 else None
            if (not isinstance(address, tuple) or len(address) < 2
                    or owned_host(address[0]) not in {"127.0.0.1", "::1"} or address[1] not in {8001, 8002, 8003}):
                denials["external_network"] += 1
                raise PermissionError("only_original_owned_AP2_service_connections_allowed")
        if event == "socket.getaddrinfo" and (owned_host(values[0]) is None or values[1] not in {8001, 8002, 8003}):
            denials["external_network"] += 1
            raise PermissionError("external_AP2_caller_DNS_denied")
        if event == "socket.sendto":
            denials["external_network"] += 1
            raise PermissionError("AP2_caller_datagram_network_denied")
        if event == "subprocess.Popen" or event == "os.system" or event.startswith("os.spawn"):
            denials["descendants"] += 1
            raise PermissionError("AP2_caller_descendants_denied")
    sys.addaudithook(guard)
    audit_probes = []
    for label, target in (("private_evaluator", repo_root / "benchmark/tasks-v1/ap2/evaluator.json"),
                          ("private_journal", output / "unread-private-journal-probe.jsonl")):
        try:
            with target.open("rb"):
                pass
        except PermissionError:
            audit_probes.append({"probe": label, "read_blocked_before_data_access": True})
        else:
            raise ValueError("The prospective actor audit failed to block " + label)
    site_packages = args.site_packages.resolve(strict=True) if args.site_packages else environment_root / "Lib/site-packages"
    sys.path[:0] = [str(repo_root / "src"), str(args.samples_root.resolve(strict=True)), str(site_packages)]
    sys.dont_write_bytecode = True
    from interoperability.ap2_public_scripted_continuation_v2 import MODULES, PublicScriptedContinuation, bind_original_modules
    expected = {relative: next(row["sha256"] for row in stage["files"]
                              if row["project"] == "ap2" and row["path"] == "code/samples/python/src/" + relative)
                for relative in MODULES.values()}
    modules, source_records = bind_original_modules(args.samples_root, expected)
    event_path = output / "actor-public-events.jsonl"
    def writer(kind, row):
        with event_path.open("ab") as stream:
            stream.write((json.dumps({"kind": kind, **row}, sort_keys=True) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
    caller = PublicScriptedContinuation(modules, source_records, facts, writer)
    try:
        result = asyncio.run(asyncio.wait_for(caller.run(), timeout=240.0))
    except BaseException as error:
        observations = [row["public_observation"]["task"] for row in caller.public_reads if "public_observation" in row]
        result = caller.result("caller_timeout_or_interruption_retained", observations[0] if observations else None,
                               observations[-1] if observations else None,
                               {"type": type(error).__name__, "message": str(error)})
    imported = {}
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(environment_root) and path.is_file():
            relative = path.relative_to(environment_root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if relative not in environment["files"] or digest != environment["files"][relative]["sha256"]:
                raise ValueError("An imported installed environment file changed: " + relative)
            imported[relative] = digest
    result.update(denials=denials, source_stage_sha256=STAGE_SHA256, environment_sha256=environment_sha256,
                  public_human_facts_sha256=hashlib.sha256(facts_raw).hexdigest(), imported_environment=imported,
                  provider_requests_from_caller=0, original_service_or_model_inference_not_started_by_caller=True)
    result.update(audit_probes=audit_probes, owned_platform_cache_warmed_before_actor_audit=True,
                  platform_bootstrap=platform_bootstrap, private_task_root=str(task_root), retained_caller_output=str(output))
    if portable_runtime:
        result.update(portable_runtime_binding=True, original_windows_environment_sha256=ENVIRONMENT_SHA256,
                      portable_pip_report=environment["pip_report"], portable_distribution_versions=actual_distributions,
                      imported_portable_files_verified_against_fresh_runtime_manifest=True,
                      imported_portable_files_compared_to_windows_bytes=False)
    for relative in ("scripts/ap2_public_scripted_continuation_v2.py", "src/interoperability/ap2_public_scripted_continuation_v2.py",
                     "src/interoperability/ap2_public_original_binding_v2.py",
                     "src/interoperability/ap2_public_task_read_v1.py"):
        raw = (repo_root / relative).read_bytes()
        target = output / "owned-source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (output / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": result["case_id"], "status": result["status"],
                      "calls": len(result["original_business_calls"]), "grade": None}))


if __name__ == "__main__":
    main()
