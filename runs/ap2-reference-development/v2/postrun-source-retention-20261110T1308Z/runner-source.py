"""Audit secure AP2 readiness or run one offline original-function subset.

The subset is an intervention with a constructed cart, direct tool invocation
and an extracted function namespace. It never claims the original shopper,
router, catalog, credential flow or suspended payment completed.
"""
from __future__ import annotations

import argparse
import ast
import base64
import builtins
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib
import json
import logging
import marshal
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import time
import types
import uuid


ROOT = Path(__file__).resolve().parents[1]
MODEL = "gemini-3.1-flash-lite-preview"
SOURCE_PIN = "e1ea56db72a6385bce3e5c1112b3a56ce60acb43"
STAGE_REL = "runs/ap2-environment-preparation/source-stage-v1/manifest.json"
STAGE_SHA = "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463"
ENV_REL = "runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json"
ENV_SHA = "4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5"
SETUP_REL = "scripts/configure_gemini_key.ps1"
SETUP_SHA = "b8cca046be3223f8dbb231a96564ab1d5ccd90f9d98bcca0b938913ddde424b0"
SOURCE_ROOT = ROOT / "runs/ap2-environment-preparation/source-stage-v1/ap2"
SAMPLES = SOURCE_ROOT / "code/samples/python/src"
PROFILE_FILES = {
    "agent_provider_signing_key.pem", "agent_provider_signing_key.pub",
    "merchant_signing_key.pem",
}
LIMITS = {"development_trials": 1, "provider_requests": 0,
          "worker_timeout_seconds": 90, "maximum_observation_bytes": 1_048_576}
GAPS = [
    {"binding": "project_model_allowance",
     "missing": "Current project/model quota, remaining usage and free-tier scope; supplied UI text is ambiguous."},
    {"binding": "before_wire_provider_guard",
     "missing": "Existing transport install_guard refuses native installation; complete constructor/lower-send binding is not wired."},
    {"binding": "owned_service_bootstrap",
     "missing": "Successor bootstrap must install final-ASGI and original-server leases before original server construction."},
    {"binding": "owned_caller_coordinator",
     "missing": "Successor must import exact caller modules, install seven observed client aliases and feed ReferenceCoordinator."},
    {"binding": "peer_wire_capture",
     "missing": "Three live peers need durable raw-ASGI streams and client connection/peer ownership evidence."},
    {"binding": "original_model_prelude",
     "missing": "Resolver and catalog both call Gemini; one generation cannot complete even the catalog prelude."},
]


class DevelopmentError(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise DevelopmentError(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def regular(path, directory=False):
    path = Path(path).absolute()
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        require(not stat.S_ISLNK(info.st_mode)
                and not getattr(info, "st_file_attributes", 0) & 0x400,
                "linked_path_refused")
    require(path.is_dir() if directory else path.is_file(), "regular_path_required")
    return path


def bounded_read(path, maximum=32 * 1024 * 1024):
    path = regular(path)
    require(path.stat().st_size <= maximum, "input_bound_exceeded")
    return path.read_bytes()


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def invalid(_):
        raise DevelopmentError("nonfinite_json")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def write_new(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    require(len(raw) <= LIMITS["maximum_observation_bytes"], "output_bound_exceeded")
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def allocate_output(path):
    path = Path(path).absolute()
    parent = regular(path.parent, True)
    require(path == parent / path.name and path.name not in {"", ".", ".."},
            "canonical_new_output_required")
    path.mkdir(exist_ok=False)
    return regular(path, True)


def secure_status(root=ROOT, run=subprocess.run):
    helper = root / SETUP_REL
    require(sha(bounded_read(helper)) == SETUP_SHA, "secure_setup_helper_changed")
    executable = shutil.which("powershell.exe")
    if executable is None:
        return {"status": "windows_powershell_unavailable", "configured": None,
                "plaintext_key_read_by_this_program": False}
    result = run([executable, "-NoProfile", "-NonInteractive", "-File",
                  str(helper), "-CheckOnly"], capture_output=True, timeout=20, check=False)
    require(len(result.stdout) <= 16_384, "secure_status_output_too_large")
    require(result.returncode == 0, "secure_status_failed")
    payload = strict_json(result.stdout)
    require(type(payload) is dict and set(payload) == {"configured", "path"}
            and type(payload["configured"]) is bool and type(payload["path"]) is str,
            "secure_status_not_allowlisted")
    return {"status": "local_protected_value_readable" if payload["configured"] else "not_configured",
            "configured": payload["configured"], "helper_sha256": SETUP_SHA,
            "storage_outside_workspace": not Path(payload["path"]).is_relative_to(root),
            "plaintext_key_read_by_this_program": False,
            "provider_acceptance_proved_by_local_status": False}


def metadata_summary(path):
    raw = bounded_read(path, 1_048_576)
    data = strict_json(raw)
    require(data.get("schema_version") == "gemini-model-metadata-access/1"
            and data.get("requested_model") == MODEL
            and data.get("content_generation_requested") is False
            and data.get("probe_source_sha256") ==
            "a4c4378311d93a03bb29e0d89500dd4efbd8525cf66c54e95d773ad9a5ee3498",
            "wrong_metadata_receipt")
    accepted_statuses = {"metadata_access_confirmed", "unexpected_http_status",
                         "metadata_response_too_large", "invalid_metadata_response",
                         "provider_access_rejected", "requested_model_not_found",
                         "provider_rate_or_quota_rejected", "provider_http_failure",
                         "redirect_rejected", "network_or_tls_failure", "probe_failure",
                         "credential_environment_failed", "missing_process_credential",
                         "unexpected_probe_failure"}
    require(data.get("status") in accepted_statuses
            and (data.get("http_status") is None or type(data["http_status"]) is int),
            "metadata_status_not_allowlisted")
    finished = data.get("finished_at_utc")
    require(type(finished) is str and datetime.fromisoformat(finished).tzinfo is not None,
            "metadata_capture_time_missing")
    return {"path": str(Path(path).absolute()), "sha256": sha(raw),
            "finished_at_utc": finished,
            "status": data.get("status"), "http_status": data.get("http_status"),
            "model": MODEL, "request_attempted": data.get("request_attempted") is True,
            "content_generation_requested": data.get("content_generation_requested") is True,
            "generation_quota_verified": False, "free_tier_or_billing_verified": False}


def latest_metadata(root=ROOT):
    candidates = list((root / "runs/ap2-reference-development/v2").glob("metadata-access*/result.json"))
    old = root / "runs/gemini-access/metadata-v1/result.json"
    if old.exists():
        candidates.append(old)
    summaries = [metadata_summary(path) for path in candidates]
    return max(summaries, key=lambda row: row["finished_at_utc"] or "") if summaries else None


def frozen_inputs(root=ROOT):
    stage_raw, env_raw = bounded_read(root / STAGE_REL), bounded_read(root / ENV_REL)
    require(sha(stage_raw) == STAGE_SHA and sha(env_raw) == ENV_SHA, "frozen_input_identity_changed")
    stage, environment = strict_json(stage_raw), strict_json(env_raw)
    require(stage.get("status") == "pristine_source_stage_created"
            and stage.get("ap2_files") == 136
            and environment.get("status") == "installed_hash_verified", "unsupported_frozen_inputs")
    source_root = root / "runs/ap2-environment-preparation/source-stage-v1/ap2"
    rows = {}
    for row in stage["files"]:
        if row["project"] != "ap2":
            continue
        rel = PurePosixPath(row["path"])
        require(not rel.is_absolute() and ".." not in rel.parts, "source_path_escape")
        require(str(rel) not in rows, "duplicate_source_path")
        raw = bounded_read(source_root / str(rel))
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "original_source_changed")
        rows[str(rel)] = {"bytes": len(raw), "sha256": sha(raw)}
    require(len(rows) == 136, "source_inventory_incomplete")
    require(sha(bounded_read(environment["interpreter"]["path"])) ==
            environment["interpreter"]["sha256"], "frozen_interpreter_changed")
    require(sha(bounded_read(environment["base_interpreter"]["path"])) ==
            environment["base_interpreter"]["sha256"], "frozen_base_interpreter_changed")
    return stage, environment, rows


def memory_observation():
    if sys.platform != "win32":
        return {"status": "windows_memory_observation_unavailable"}
    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in (
                "total_physical", "available_physical", "total_commit", "available_commit",
                "total_virtual", "available_virtual", "available_extended_virtual")]
    value = Memory()
    value.length = ctypes.sizeof(value)
    require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)), "memory_observation_failed")
    return {"status": "observed", "at_utc": now(),
            "physical_available_bytes": value.available_physical,
            "commit_available_bytes": value.available_commit,
            "three_service_thresholds_met": value.available_physical >= 1024**3
            and value.available_commit >= 2 * 1024**3}


def audit(root=ROOT):
    _, environment, rows = frozen_inputs(root)
    return {"schema_version": "ap2-reference-development-audit/2", "at_utc": now(),
            "mode": "read_only_secure_setup_and_source_audit",
            "source_pin": SOURCE_PIN, "original_declared_source_files_verified": len(rows),
            "stage_manifest_sha256": STAGE_SHA, "environment_manifest_sha256": ENV_SHA,
            "environment_packages_from_retained_manifest": environment["packages"],
            "environment_full_runtime_compatibility_verified": False,
            "secure_setup": secure_status(root), "model_metadata_receipt": latest_metadata(root),
            "quota_evidence": {"source": "user supplied prior AI Studio UI text",
                               "free_tier_label_present": True, "model_label_present": True,
                               "numeric_limit_assignment": "ambiguous",
                               "capture_clock_and_current_remaining_usage": "unknown",
                               "authenticated_project_key_association": "unknown",
                               "approved_generation_budget_in_this_runner": 0},
            "memory": memory_observation(), "full_reference_implemented": False,
            "missing_bindings": GAPS, "model_requests_by_this_audit": 0,
            "original_application_imports_by_this_audit": 0}


def child_environment(profile, supplied=os.environ):
    names = {"SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE",
             "LOCALAPPDATA", "APPDATA", "ProgramData", "COMSPEC"}
    result = {key: value for key, value in supplied.items()
              if key.upper() in {name.upper() for name in names}}
    result.update(PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
                  GOOGLE_GENAI_USE_VERTEXAI="false", PAYMENT_METHOD="CARD",
                  TEMP_DB_DIR=str(profile),
                  MERCHANT_SIGNING_KEY_PATH=str(profile / "merchant_signing_key.pem"),
                  AGENT_PROVIDER_PUBLIC_KEY_PATH=str(profile / "agent_provider_signing_key.pub"))
    return result


def allocate_profile():
    local = os.environ.get("LOCALAPPDATA")
    require(local and sys.platform == "win32", "windows_local_private_profile_required")
    local = regular(local, True)
    base = local / "AiInteroperability" / "development-profiles"
    base.mkdir(parents=True, exist_ok=True)
    regular(base, True)
    profile = base / ("ap2-reference-v2-" + uuid.uuid4().hex)
    profile.mkdir(exist_ok=False)
    regular(profile, True)
    require(profile.is_relative_to(local) and not profile.is_relative_to(ROOT),
            "private_profile_location_invalid")
    return profile


def cleanup_profile(profile):
    try:
        profile = regular(profile, True)
        require(profile.name.startswith("ap2-reference-v2-")
                and profile.parent.name == "development-profiles"
                and not profile.is_relative_to(ROOT), "owned_private_profile_required")
        for name in PROFILE_FILES:
            path = profile / name
            if path.exists():
                require(regular(path).parent == profile, "private_cleanup_path_invalid")
                path.unlink()
        profile.rmdir()
        return {"status": "owned_generated_key_files_removed", "complete": True}
    except Exception as error:
        return {"status": "cleanup_incomplete_authority_retained", "complete": False,
                "owned_profile": str(profile), "error_type": type(error).__name__}


def extract_functions(path, names, namespace, expected_sha):
    """Execute exact original function code objects; disclose omitted module setup."""
    raw = bounded_read(path)
    require(sha(raw) == expected_sha, "extracted_source_changed")
    tree = ast.parse(raw, filename=str(path))
    nodes = {node.name: node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    module_code = compile(raw, str(path), "exec", dont_inherit=True)
    codes = {code.co_name: code for code in module_code.co_consts if isinstance(code, types.CodeType)}
    namespace.setdefault("__builtins__", builtins.__dict__)
    namespace.setdefault("__name__", "_ap2_original_function_subset")
    namespace["__file__"] = str(path)
    identities = {}
    for name in names:
        node, code = nodes[name], codes[name]
        require(not node.decorator_list, "decorated_function_subset_refused")
        defaults = tuple(ast.literal_eval(value) for value in node.args.defaults) or None
        function = types.FunctionType(code, namespace, name, defaults)
        function.__kwdefaults__ = {arg.arg: ast.literal_eval(value)
                                 for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults)
                                 if value is not None} or None
        namespace[name] = function
        identities[name] = {"source_sha256": expected_sha,
                            "function_code_sha256": sha(marshal.dumps(code)),
                            "first_line": node.lineno, "last_line": node.end_lineno}
    return namespace, identities


def immediate(coroutine):
    """Drive only an already-immediate original coroutine; external awaits refuse."""
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    else:
        coroutine.close()
        raise DevelopmentError("external_async_wait_outside_offline_subset")


def install_offline_denials():
    counts = {"blocked_network_operations": 0, "blocked_process_launches": 0,
              "blocked_secret_file_reads": 0}
    def deny(event, args):
        if event in {"socket.connect", "socket.connect_ex", "socket.bind",
                     "socket.getaddrinfo", "socket.sendto"}:
            counts["blocked_network_operations"] += 1
            raise DevelopmentError("network_outside_offline_subset")
        if event == "subprocess.Popen" or event == "os.system" or event.startswith("os.spawn"):
            counts["blocked_process_launches"] += 1
            raise DevelopmentError("process_launch_outside_offline_subset")
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            name = Path(os.fsdecode(args[0])).name.lower()
            if name.startswith("gemini-api-key") or name in {".env", "application_default_credentials.json"}:
                counts["blocked_secret_file_reads"] += 1
                raise DevelopmentError("credential_file_outside_offline_subset")
    sys.addaudithook(deny)
    return counts


def subset_worker(plan_path):
    plan = strict_json(bounded_read(plan_path, 1_048_576))
    require(plan["runner_sha256"] == sha(bounded_read(__file__))
            and plan["parent_pid"] == os.getppid(), "worker_plan_parent_or_source_changed")
    output, profile = regular(plan["output"], True), regular(plan["private_profile"], True)
    require(not any(key in os.environ for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY")),
            "provider_secret_in_subset_environment")
    counts = install_offline_denials()
    _, environment, source_rows = frozen_inputs()
    sys.path[:0] = [str(SAMPLES), environment["site_packages"]]
    logging.disable(logging.CRITICAL)
    from a2a.server.events.event_queue import EventQueue
    from a2a.server.tasks.task_updater import TaskUpdater
    from a2a.types import Artifact, DataPart, Part, TextPart
    from ap2.sdk.generated.checkout_mandate import CheckoutMandate
    from ap2.sdk.generated.payment_mandate import PaymentMandate
    from ap2.sdk.generated.payment_receipt import PaymentReceipt
    from ap2.sdk.generated.types.amount import Amount
    from ap2.sdk.generated.types.checkout import Checkout, Status
    from ap2.sdk.generated.types.item import Item
    from ap2.sdk.generated.types.line_item import LineItem
    from ap2.sdk.generated.types.link import Link
    from ap2.sdk.generated.types.merchant import Merchant
    from ap2.sdk.generated.types.payment_instrument import PaymentInstrument
    from ap2.sdk.generated.types.total import Total
    from ap2.sdk.mandate import MandateClient
    from ap2.sdk.utils import compute_sha256_b64url
    from common import artifact_utils, constants, message_utils
    from common.a2a_message_builder import A2aMessageBuilder
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
    from jwcrypto.jwk import JWK
    from roles.merchant_agent import storage
    require(constants.TEMP_DB == profile, "original_key_path_does_not_use_owned_profile")
    common = dict(base64=base64, hashlib=hashlib, json=json, logging=logging, os=os,
                  time=time, uuid=uuid, ec=ec, serialization=serialization, JWK=JWK,
                  hashes=hashes, x509=x509, decode_dss_signature=decode_dss_signature,
                  load_pem_private_key=serialization.load_pem_private_key,
                  load_pem_public_key=serialization.load_pem_public_key,
                  Encoding=serialization.Encoding, NoEncryption=serialization.NoEncryption,
                  PrivateFormat=serialization.PrivateFormat, Part=Part, DataPart=DataPart,
                  TextPart=TextPart, Checkout=Checkout, Status=Status, Item=Item,
                  LineItem=LineItem, Link=Link, Total=Total, Merchant=Merchant,
                  Amount=Amount, PaymentInstrument=PaymentInstrument,
                  CheckoutMandate=CheckoutMandate, PaymentMandate=PaymentMandate,
                  PaymentReceipt=PaymentReceipt, MandateClient=MandateClient,
                  artifact_utils=artifact_utils, message_utils=message_utils, storage=storage,
                  A2aMessageBuilder=A2aMessageBuilder, compute_sha256_b64url=compute_sha256_b64url)
    merchant_path = SAMPLES / "roles/merchant_agent/tools.py"
    shopper_path = SAMPLES / "roles/shopping_agent/tools.py"
    processor_path = SAMPLES / "roles/merchant_payment_processor_agent/tools.py"
    source_sha = lambda path: source_rows[path.relative_to(SOURCE_ROOT).as_posix()]["sha256"]
    merchant_ns = dict(common, _MERCHANT_NAME="Generic Merchant", _MERCHANT_ID="merchant_1",
                       _MERCHANT_WEBSITE="https://demo-merchant.example",
                       _MERCHANT_KEY_PATH=os.environ["MERCHANT_SIGNING_KEY_PATH"],
                       _AGENT_PROVIDER_PUB_KEY_PATH=os.environ["AGENT_PROVIDER_PUBLIC_KEY_PATH"])
    merchant_ns, merchant_ids = extract_functions(merchant_path, [
        "_b64url_encode", "_compute_sha256_b64url", "_get_merchant_signing_key",
        "_create_jwt", "create_checkout", "_fail_task", "_verify_checkout_mandate"],
        merchant_ns, source_sha(merchant_path))
    shopper_ns = dict(common, AGENT_PROVIDER_KEY_PATH=constants.AGENT_PROVIDER_KEY_PATH,
                      AGENT_PROVIDER_PUB_PATH=constants.AGENT_PROVIDER_PUB_PATH,
                      DEFAULT_MANDATE_TTL_SECONDS=constants.DEFAULT_MANDATE_TTL_SECONDS)
    for node in ast.parse(bounded_read(shopper_path)).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id in {"DEMO_MERCHANT", "DEMO_PAYMENT_INSTRUMENT"} for target in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(shopper_path),
                         "exec", dont_inherit=True), shopper_ns)
    shopper_ns, shopper_ids = extract_functions(shopper_path, [
        "_get_user_signing_key", "create_checkout_mandate", "create_payment_mandate"],
        shopper_ns, source_sha(shopper_path))
    from datetime import UTC
    processor_ns = dict(common, UTC=UTC, datetime=datetime,
                        _AGENT_PROVIDER_PUB_KEY_PATH=os.environ["AGENT_PROVIDER_PUBLIC_KEY_PATH"])
    processor_ns, processor_ids = extract_functions(processor_path, [
        "_verify_payment_mandate", "_create_payment_receipt"], processor_ns, source_sha(processor_path))
    observations, checks = {}, {}
    journal = (output / "events.jsonl").open("xb")
    sequence = 0
    def observe(operation, value):
        nonlocal sequence
        row = {"sequence": sequence, "operation": operation, "actual_result": value}
        raw = (json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n").encode()
        require(sequence < 64 and journal.tell() + len(raw) <= LIMITS["maximum_observation_bytes"],
                "observation_bound_exceeded")
        journal.write(raw)
        journal.flush()
        os.fsync(journal.fileno())
        sequence += 1
        return value
    try:
        cart = {"cart_id": "development-shoe-cart", "item_label": "Unbranded walking shoes",
                "amount": 12.5, "currency": "USD"}
        context_id, task_id = uuid.uuid4().hex, uuid.uuid4().hex
        observe("constructed_subset_input", {"cart": cart, "context_id": context_id, "task_id": task_id})
        storage.set_cart_data(cart["cart_id"], cart)
        queue = EventQueue(max_queue_size=16)
        updater = TaskUpdater(queue, task_id, context_id)
        immediate(merchant_ns["create_checkout"]([{"cart_id": cart["cart_id"]}], updater, None))
        events = []
        while not queue.queue.empty():
            event = immediate(queue.dequeue_event(no_wait=True))
            events.append(event)
            queue.task_done()
        require(len(events) == 2 and events[-1].status.state.value == "completed",
                "original_checkout_did_not_complete")
        checkout = artifact_utils.get_first_data_part([events[0].artifact])["ap2.checkout"]
        observations["checkout_events"] = observe("original_merchant_create_checkout",
            [event.model_dump(mode="json", by_alias=True, exclude_none=True) for event in events])
        observations["checkout_data"] = checkout
        pieces = checkout["checkout_jwt"].split(".")
        signature = base64.urlsafe_b64decode(pieces[2] + "=" * (-len(pieces[2]) % 4))
        signature = encode_dss_signature(int.from_bytes(signature[:32], "big"),
                                        int.from_bytes(signature[32:], "big"))
        merchant_key = merchant_ns["_get_merchant_signing_key"]()
        merchant_key.public_key().verify(signature, ".".join(pieces[:2]).encode(),
                                        ec.ECDSA(hashes.SHA256()))
        checks["merchant_checkout_signature_verified_independently"] = True
        expected_checkout_hash = base64.urlsafe_b64encode(hashlib.sha256(
            checkout["checkout_jwt"].encode()).digest()).rstrip(b"=").decode()
        checks["checkout_hash_matches_exact_jwt_bytes"] = expected_checkout_hash == checkout["checkout_hash"]
        context = types.SimpleNamespace(state={"checkout_data": checkout})
        checkout_token = shopper_ns["create_checkout_mandate"](context)
        payment_token = shopper_ns["create_payment_mandate"](context)
        observations["mandates"] = observe("original_shopper_signer_results",
            {"checkout_mandate": checkout_token, "payment_mandate": payment_token})
        checkout_payload = merchant_ns["_verify_checkout_mandate"](checkout_token)
        payment_payload = processor_ns["_verify_payment_mandate"](
            payment_token, nonce=checkout["checkout_hash"], aud="credential-provider")
        observations["verified_payloads"] = observe("original_mandate_verifier_results", {
            "checkout": checkout_payload.model_dump(mode="json"),
            "payment": payment_payload.model_dump(mode="json")})
        checks["checkout_mandate_retains_actual_checkout"] = (
            checkout_payload.checkout_jwt == checkout["checkout_jwt"]
            and checkout_payload.checkout_hash == checkout["checkout_hash"])
        checks["payment_transaction_matches_checkout_hash"] = payment_payload.transaction_id == checkout["checkout_hash"]
        checks["payment_amount_and_currency_match_checkout"] = (
            payment_payload.payment_amount.amount == checkout["amount_cents"]
            and payment_payload.payment_amount.currency == checkout["currency"])
        receipt = processor_ns["_create_payment_receipt"](payment_payload, payment_token)
        observations["receipt"] = observe("original_receipt_constructor", receipt.model_dump(mode="json"))
        leaf = MandateClient().get_closed_mandate_jwt(payment_token)
        independent_reference = base64.urlsafe_b64encode(hashlib.sha256(
            leaf.encode()).digest()).rstrip(b"=").decode()
        checks["receipt_reference_matches_exact_closed_leaf"] = receipt.reference == independent_reference
        message = (A2aMessageBuilder().set_context_id(context_id)
                   .add_text("Initiate a payment")
                   .add_data(constants.PAYMENT_MANDATE_SD_JWT_KEY, payment_token)
                   .add_data("risk_data", "").add_data("debug_mode", False).build())
        observations["unsent_message"] = observe("original_builder_unsent_message",
            message.model_dump(mode="json", by_alias=True, exclude_none=True))
        checks["builder_preserves_falsy_omission_and_part_order"] = (
            len(message.parts) == 2 and message.parts[0].root.text == "Initiate a payment"
            and message.parts[1].root.data == {constants.PAYMENT_MANDATE_SD_JWT_KEY: payment_token})
        artifact = Artifact(artifact_id=uuid.uuid4().hex, parts=[
            Part(root=DataPart(data={constants.PAYMENT_RECEIPT_DATA_KEY: receipt.model_dump(mode="json")}))])
        extracted = artifact_utils.only(artifact_utils.find_canonical_objects(
            [artifact], constants.PAYMENT_RECEIPT_DATA_KEY, PaymentReceipt))
        checks["canonical_receipt_extraction_matches_constructor"] = extracted == receipt
        text_artifact = Artifact(artifact_id=uuid.uuid4().hex, parts=[Part(root=TextPart(text="no credential data"))])
        checks["nonempty_artifact_without_datapart_returns_empty_dict"] = (
            artifact_utils.get_first_data_part([text_artifact]) == {})
        first, *rest = payment_token.split("~")
        token_parts = first.split(".")
        token_parts[2] = ("A" if token_parts[2][0] != "A" else "B") + token_parts[2][1:]
        tampered = "~".join([".".join(token_parts), *rest])
        try:
            processor_ns["_verify_payment_mandate"](tampered, nonce=checkout["checkout_hash"],
                                                   aud="credential-provider")
        except Exception as error:
            tamper_result = {"accepted": False, "error_type": type(error).__name__}
        else:
            tamper_result = {"accepted": True}
        checks["changed_payment_signature_rejected"] = not tamper_result["accepted"]
        observe("altered_observation_signature_control", tamper_result)
        wrong_key = JWK.from_pyca(ec.generate_private_key(ec.SECP256R1()).public_key())
        try:
            MandateClient().verify(token=payment_token, key_or_provider=wrong_key,
                                   payload_type=PaymentMandate)
        except Exception as error:
            wrong_key_result = {"accepted": False, "error_type": type(error).__name__}
        else:
            wrong_key_result = {"accepted": True}
        checks["different_user_public_key_rejected"] = not wrong_key_result["accepted"]
        observe("different_public_key_control", wrong_key_result)
        imported_files = {}
        environment_root = Path(environment["root"])
        for module in list(sys.modules.values()):
            filename = getattr(module, "__file__", None)
            if not filename:
                continue
            path = Path(filename).absolute()
            if path.is_relative_to(environment_root):
                rel = path.relative_to(environment_root).as_posix()
                require(rel in environment["files"], "imported_file_outside_frozen_environment_inventory")
                raw = bounded_read(path)
                require(sha(raw) == environment["files"][rel]["sha256"], "imported_environment_module_changed")
                imported_files[rel] = sha(raw)
        frozen_inputs()
        require(all(checks.values()), "original_subset_check_failed")
        require(not any(counts.values()), "offline_denial_was_triggered")
        write_new(output / "public-observations.json", observations)
        result = {"schema_version": "ap2-reference-development-subset/2",
                  "status": "original_function_subset_completed", "completed_at_utc": now(),
                  "source_pin": SOURCE_PIN, "development_trials": 1, "provider_requests": 0,
                  "full_reference_completed": False, "original_module_import_compatibility_verified": False,
                  "original_functions": {"merchant": merchant_ids, "shopper": shopper_ids,
                                         "processor": processor_ids},
                  "imported_environment_files_verified": imported_files, "checks": checks,
                  "offline_denials": counts, "observed_events": sequence,
                  "events_sha256": sha(bounded_read(output / "events.jsonl", 1_048_576)),
                  "constructed_inputs": ["cart and merchant storage seed", "caller state carrier",
                                         "local task/context IDs", "unsent request and receipt artifact wrapper"],
                  "interventions": ["extracted original function namespaces; no ADK ToolContext",
                                    "direct merchant tool invocation bypasses model router/catalog",
                                    "original immediate SDK coroutine path; external awaits refused"],
                  "omitted_path": ["Gemini resolver/catalog", "ADK shopper", "credential selection/association",
                                   "merchant/processor OTP task continuation", "provider receipt acknowledgment"],
                  "receipt_is_payment_completion_evidence": False,
                  "os_sandbox_or_external_capture_authentication_established": False}
        write_new(output / "worker-result.json", result)
        return result
    finally:
        journal.close()


def run_subset(output, audit_result):
    require(sys.platform == "win32", "windows_installed_subset_profile_required")
    _, environment, _ = frozen_inputs()
    profile = allocate_profile()
    plan = {"schema_version": "ap2-reference-development-plan/2", "mode": "offline_original_function_subset",
            "created_at_utc": now(), "output": str(output), "private_profile": str(profile),
            "parent_pid": os.getpid(), "runner_sha256": sha(bounded_read(__file__)),
            "limits": LIMITS, "source_pin": SOURCE_PIN,
            "stage_manifest_sha256": STAGE_SHA, "environment_manifest_sha256": ENV_SHA,
            "full_reference_completed": False}
    write_new(output / "plan.json", plan)
    write_new(output / "audit.json", audit_result)
    result = {"schema_version": "ap2-reference-development-result/2", "started_at_utc": now(),
              "mode": plan["mode"], "development_trials": 1, "provider_requests": 0,
              "full_reference_completed": False}
    try:
        invocation = [environment["base_interpreter"]["path"], "-I", "-S", "-B", "-X", "utf8",
                      str(Path(__file__).absolute()), "_worker", "--plan", str(output / "plan.json")]
        result["worker_interpreter_binding"] = "hash-pinned base interpreter; explicit frozen site-packages; site disabled"
        process = subprocess.run(invocation, env=child_environment(profile), cwd=profile,
                                 capture_output=True, timeout=LIMITS["worker_timeout_seconds"], check=False)
        require(len(process.stdout) + len(process.stderr) <= LIMITS["maximum_observation_bytes"],
                "worker_log_bound_exceeded")
        for filename, raw in (("stdout.bin", process.stdout), ("stderr.bin", process.stderr)):
            with (output / filename).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        result["worker_returncode"] = process.returncode
        result["status"] = "original_function_subset_completed" if process.returncode == 0 else "subset_failed"
        worker_path = output / "worker-result.json"
        if worker_path.exists():
            worker = strict_json(bounded_read(worker_path, 1_048_576))
            result["worker_status"] = worker["status"]
            result["checks"] = worker.get("checks", {})
            result["worker_result_sha256"] = sha(bounded_read(worker_path, 1_048_576))
        require(process.returncode == 0 and result.get("worker_status") == "original_function_subset_completed",
                "worker_did_not_complete_subset")
    except Exception as error:
        result.update(status="subset_failed", error_type=type(error).__name__)
    finally:
        result["private_profile_cleanup"] = cleanup_profile(profile)
    result["finished_at_utc"] = now()
    result["success"] = result["status"] == "original_function_subset_completed" \
        and result["private_profile_cleanup"]["complete"]
    write_new(output / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("audit", "subset"):
        command = subcommands.add_parser(mode)
        command.add_argument("--output", type=Path, required=True, help="New directory under an existing parent")
    worker = subcommands.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "_worker":
            result = subset_worker(args.plan)
        else:
            output = allocate_output(args.output)
            audited = audit()
            if args.mode == "audit":
                write_new(output / "result.json", audited)
                result = {"status": "read_only_audit_completed", "full_reference_completed": False}
            else:
                result = run_subset(output, audited)
        print(json.dumps({key: result[key] for key in (
            "status", "success", "full_reference_completed", "provider_requests") if key in result}))
        return 0 if result.get("status") in {
            "read_only_audit_completed", "original_function_subset_completed"} and result.get("success", True) else 2
    except BaseException as error:
        failure = {"status": "development_run_refused_or_failed",
                   "error_type": type(error).__name__, "full_reference_completed": False,
                   "provider_requests": 0}
        if type(error) is DevelopmentError:
            label = str(error)
            if 0 < len(label) <= 100 and all(char.isascii() and
                    (char.islower() or char.isdigit() or char == "_") for char in label):
                failure["reason_code"] = label
        print(json.dumps(failure))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
