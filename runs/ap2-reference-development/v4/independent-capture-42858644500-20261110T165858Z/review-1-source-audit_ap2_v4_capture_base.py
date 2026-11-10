"""Read an actual retained AP2 capture and freshly verify buyer root signatures.

No original application trial, provider request, or source edit is made. A
signature check over captured bytes does not establish issuer identity or a
completed application/payment trajectory.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json"
ENV_SHA = "4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(value):
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))


def audit(base, expected_returncode=2):
    base = Path(base).resolve()
    before = {path.relative_to(base).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path)}
              for path in sorted(base.rglob("*")) if path.is_file()}
    assert sha(ENV) == ENV_SHA
    environment = json.loads(ENV.read_bytes())
    assert sha(Path(environment["base_interpreter"]["path"])) == environment["base_interpreter"]["sha256"]
    site = Path(environment["site_packages"])
    sys.path.insert(0, str(site))
    denials = {"network_attempts": 0, "process_attempts": 0}

    def deny(event, values):
        if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo", "socket.sendto"}:
            denials["network_attempts"] += 1
            raise PermissionError("offline_verification")
        if event == "subprocess.Popen" or event == "os.system" or event.startswith("os.spawn"):
            denials["process_attempts"] += 1
            raise PermissionError("offline_verification")

    sys.addaudithook(deny)
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    app = base / "application"
    read = lambda name: json.loads((app / name).read_bytes())
    result, cleanup, plan = read("result.json"), read("cleanup.json"), read("plan.json")
    assert result["returncode"] == expected_returncode and result["native_qualification_established"] is False
    assert cleanup["clients_closed"] and cleanup["caller_aliases_restored"]
    assert cleanup["source_tree_unchanged"] and cleanup["runtime_tree_unchanged"]
    assert all(raw["source_complete"] and raw["active_operations"] == 0 and not raw["observation_errors"]
               for raw in cleanup["raw"].values())
    assert sha(app / "source-runner.py") == plan["owned_components"]["scripts/ap2_reference_development_v4.py"]["sha256"]
    source_manifest = read("source-stage-manifest.json")
    assert sha(app / "source-stage-manifest.json") == plan["source_manifest_sha256"]
    originals = [row for row in source_manifest["files"] if row["project"] == "ap2"]
    for row in originals:
        assert sha(app / "original-source" / row["path"]) == row["sha256"]
    assert len(originals) == 136
    for name, row in plan["owned_components"].items():
        if name == "scripts/ap2_reference_development_v4.py":
            continue
        assert sha(app / "owned-source" / name) == row["sha256"]
    imported = read("imported-modules.json")
    runtime = read("runtime-manifest.json")
    runtime_imported = 0
    for row in imported.values():
        marker = "/site-packages/"
        if marker in row["path"]:
            relative = row["path"].split(marker, 1)[1]
            assert runtime["files"][relative] == {"bytes": row["bytes"], "sha256": row["sha256"]}
            runtime_imported += 1
    events_raw = (app / "observations/events.jsonl").read_bytes()
    events = [json.loads(line) for line in events_raw.splitlines()]
    terminal = read("observations/terminal.json")
    assert terminal["journal"] == {"bytes": len(events_raw), "sha256": hashlib.sha256(events_raw).hexdigest()}
    assert terminal["durably_committed_events"] == len(events) == terminal["attempted_events"]
    assert [row["global_index"] for row in events] == list(range(len(events)))
    assert terminal["capture_complete_for_declared_intervals"] and not terminal["observation_errors"]
    assert not terminal["missing_global_indices"] and not terminal["journal_poisoned"]
    for stream in terminal["streams"].values():
        assert stream["final_witness"]["active_operations"] == 0 and stream["final_witness"]["source_complete"]
    code = read("original-callable-code-checks.json")
    assert all(row["full_structural_code_equal"] and row["actual_fingerprint_sha256"] == row["expected_fingerprint_sha256"] for row in code)
    requests = read("transport-interventions.json")
    assert all(row["provider_request"] is False and row["transport"] == "owned_httpx_ASGITransport" for row in requests)
    fixture = [json.loads(line) for line in (app / "model-interventions.jsonl").read_bytes().splitlines()]
    assert all(row["provider_requests"] == 0 for row in fixture)
    tools = {row["phase"]: row["value"] for row in read("original-tool-returns.json")}
    state = read("caller-final-state.json")
    key_path = app / "public-verification/agent_provider_signing_key.pub"
    key = serialization.load_pem_public_key(key_path.read_bytes())
    assert isinstance(key, ec.EllipticCurvePublicKey) and key.curve.name == "secp256r1"
    wrong_key = ec.generate_private_key(ec.SECP256R1()).public_key()
    signature_checks = []
    delegates = {}
    for name, state_key, vct in (("checkout_mandate", "checkout_mandate_sdjwt", "mandate.checkout.1"),
                                 ("payment_mandate", "payment_mandate_sdjwt", "mandate.payment.1")):
        token = tools[name]
        assert token == state[state_key]
        parts = token.split("~")
        header_part, payload_part, signature_part = parts[0].split(".")
        header = json.loads(decode(header_part))
        assert header["alg"] == "ES256"
        signing_input = (header_part + "." + payload_part).encode("ascii")
        signature = decode(signature_part)
        assert len(signature) == 64
        encoded = utils.encode_dss_signature(int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big"))
        key.verify(encoded, signing_input, ec.ECDSA(hashes.SHA256()))
        invalid_signature = bytes([signature[0] ^ 1]) + signature[1:]
        encoded_bad = utils.encode_dss_signature(int.from_bytes(invalid_signature[:32], "big"), int.from_bytes(invalid_signature[32:], "big"))
        negative = []
        for label, verifier, candidate in (("altered-signature", key, encoded_bad), ("fresh-unrelated-key", wrong_key, encoded)):
            try:
                verifier.verify(candidate, signing_input, ec.ECDSA(hashes.SHA256()))
            except InvalidSignature:
                negative.append({"control": label, "rejected": True})
            else:
                raise ValueError("cryptographic_negative_control_accepted")
        root_payload = json.loads(decode(payload_part))
        assert root_payload["_sd_alg"] == "sha-256"
        disclosures = [json.loads(decode(part)) for part in parts[1:] if part]
        allowed = set()

        def collect(value):
            if isinstance(value, dict):
                allowed.update(value.get("_sd", []))
                if "..." in value:
                    allowed.add(value["..."])
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(root_payload)
        for disclosure in disclosures:
            collect(disclosure[1:])
        for disclosure_part in parts[1:]:
            if disclosure_part:
                digest = base64.urlsafe_b64encode(hashlib.sha256(disclosure_part.encode("ascii")).digest()).decode("ascii").rstrip("=")
                assert digest in allowed
        delegate = next(disclosure[1] for disclosure in disclosures
                        if len(disclosure) == 2 and isinstance(disclosure[1], dict) and disclosure[1].get("vct") == vct)
        delegates[name] = delegate
        signature_checks.append({"mandate": name, "token_sha256": hashlib.sha256(token.encode("ascii")).hexdigest(),
                                 "fresh_captured_root_signature_verified": True, "algorithm": "ES256",
                                 "captured_disclosure_digests_verified": len(disclosures), "negative_controls": negative})
    assert delegates["checkout_mandate"]["checkout_hash"] == state["checkout_hash"]
    assert delegates["payment_mandate"]["transaction_id"] == state["checkout_hash"]
    checkout = state["checkout_data"]["checkout_jwt"]
    assert base64.urlsafe_b64encode(hashlib.sha256(checkout.encode("utf-8")).digest()).decode("ascii").rstrip("=") == state["checkout_hash"]
    crypto_imports = {}
    env_root = Path(environment["root"])
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).resolve().is_relative_to(env_root):
            path = Path(filename).resolve()
            rel = path.relative_to(env_root).as_posix()
            assert sha(path) == environment["files"][rel]["sha256"]
            crypto_imports[rel] = sha(path)
    secret_found = any(b"PRIVATE KEY-----" in path.read_bytes() or re.search(rb"AIza[A-Za-z0-9_-]{30,}", path.read_bytes())
                       for path in base.rglob("*") if path.is_file())
    assert not secret_found
    assert before == {path.relative_to(base).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path)}
                      for path in sorted(base.rglob("*")) if path.is_file()}
    return {"schema_version": "ap2-v4-capture-fresh-signature-audit/1", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": base.name.removeprefix("hosted-"), "status": "actual_partial_capture_and_buyer_signatures_verified",
            "actual_returncode": result["returncode"], "files_checked": len(before), "bytes_checked": sum(row["bytes"] for row in before.values()),
            "original_source_files_verified": len(originals), "runtime_imported_file_bindings_matched_to_retained_manifest": runtime_imported,
            "structural_code_checks": len(code), "legacy_marshal_inequality_instances": sum(not row["legacy_marshal_bytes_equal"] for row in code),
            "owned_HTTPX_ASGI_requests": len(requests), "offline_model_fixtures": len(fixture), "provider_requests": 0,
            "durable_events_checked": len(events), "clients_closed": True, "caller_aliases_restored": True,
            "raw_streams_closed_without_observation_errors": True, "source_runtime_unchanged_observed": True,
            "fresh_buyer_root_signature_checks": signature_checks, "buyer_public_key_sha256": sha(key_path),
            "checkout_hash_transaction_association_freshly_recomputed": True,
            "merchant_checkout_JWT_signature_rechecked": False, "merchant_signature_limitation": "No captured merchant public key",
            "cryptographic_scope": "Fresh signature and disclosure-hash checks over captured bytes/public key; no expiration, legal identity or full SDK mandate-policy qualification claim",
            "verifier_dependency_manifest_sha256": ENV_SHA, "verifier_imported_frozen_files": crypto_imports,
            "audit_network_and_process_attempts": denials, "artifact_unchanged_by_audit": True,
            "private_PEM_or_Gemini_key_format_found": False, "native_qualification_established": False,
            "full_application_task_pass": False, "payment_receipt_observed": False,
            "cleanup_scope": "Captured client/alias/raw closure and source/runtime flags; no authenticated external private-directory deletion proof",
            "inventory": before}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    value = audit(options.capture)
    with options.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
    print(json.dumps({key: value[key] for key in ("status", "run_id", "files_checked", "durable_events_checked", "owned_HTTPX_ASGI_requests", "offline_model_fixtures")}, indent=2))
