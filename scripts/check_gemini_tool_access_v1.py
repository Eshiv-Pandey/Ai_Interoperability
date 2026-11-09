"""One bounded synthetic forced-tool request for the AP2 router's exact model.

No returned function is executed. Secrets, headers, provider bodies, generated
text, thought signatures and exception messages are never serialized.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request

from check_gemini_model_access_v1 import MODEL, MAX_RESPONSE_BYTES, NoRedirect


ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
FUNCTION = "acknowledge_connectivity"
PAYLOAD = {
    "systemInstruction": {"parts": [{"text": "Select the connectivity function for this fixed API check."}]},
    "contents": [{"role": "user", "parts": [{"text": "Acknowledge connectivity by selecting the available function."}]}],
    "tools": [{"functionDeclarations": [{
        "name": FUNCTION,
        "description": "A harmless connectivity acknowledgement. This function takes no arguments.",
    }]}],
    "toolConfig": {"functionCallingConfig": {"mode": "ANY"}},
    "generationConfig": {"maxOutputTokens": 32, "candidateCount": 1},
}


def validate_response(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise ValueError
    candidate = candidates[0]
    if not isinstance(candidate, dict) or candidate.get("finishReason") != "STOP":
        raise ValueError
    content = candidate.get("content")
    if not isinstance(content, dict) or content.get("role") != "model":
        raise ValueError
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError
    calls = []
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError
        if "functionCall" in part:
            call = part["functionCall"]
            if not isinstance(call, dict) or call.get("name") != FUNCTION or call.get("args", {}) != {}:
                raise ValueError
            calls.append(call)
        elif part.get("thought") is not True:
            # A prose response does not satisfy this forced-function smoke.
            raise ValueError
    if len(calls) != 1:
        raise ValueError
    usage = payload.get("usageMetadata", {})
    if not isinstance(usage, dict):
        raise ValueError
    counts = {}
    for name in ("promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"):
        if name in usage:
            value = usage[name]
            if type(value) is not int or value < 0:
                raise ValueError
            counts[name] = value
    return {"expected_function_call_received": True, "empty_arguments_received": True,
            "function_calls_received": 1, "token_usage": counts}


def probe(key: str, opener, attempt_state: dict) -> dict:
    def result(**values):
        return {**attempt_state, **values}

    try:
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(PAYLOAD).encode("utf-8"),
            headers={"x-goog-api-key": key, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        attempt_state["request_attempted"] = True
        with opener.open(request, timeout=30) as response:
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if status != 200:
            return result(status="unexpected_http_status", http_status=status)
        if len(raw) > MAX_RESPONSE_BYTES:
            return result(status="response_too_large", http_status=status)
        try:
            validated = validate_response(json.loads(raw))
        except (ValueError, TypeError, UnicodeError):
            return result(status="forced_tool_response_not_verified", http_status=status)
        return result(status="synthetic_forced_tool_access_confirmed", http_status=status, **validated)
    except urllib.error.HTTPError as error:
        status = error.code
        try:
            error.close()
        except Exception:
            pass
        label = {400: "provider_request_rejected", 401: "provider_access_rejected",
                 403: "provider_access_rejected", 404: "requested_model_not_found",
                 429: "provider_rate_or_quota_rejected"}.get(status, "provider_http_failure")
        if 300 <= status < 400:
            label = "redirect_rejected"
        return result(status=label, http_status=status)
    except (urllib.error.URLError, OSError, TimeoutError):
        return result(status="network_or_tls_failure", http_status=None)
    except Exception:
        return result(status="probe_failure", http_status=None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except OSError:
        print(json.dumps({"status": "output_allocation_failed", "request_attempted": False}))
        return 2
    receipt = {
        "schema_version": "gemini-synthetic-forced-tool-access/1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_model": MODEL, "method": "POST", "endpoint": ENDPOINT,
        "maximum_requests": 1, "retries": 0, "redirects_allowed": False,
        "content_generation_requested": True, "maximum_output_tokens": 32,
        "function_calling_mode": "ANY", "function_execution_count": 0,
        "request_attempted": False, "native_ap2_execution_verified": False,
        "free_tier_or_billing_verified": False,
        "claim_limit": "One synthetic provider routing smoke; no original AP2 router/application import or execution, no native task/effect qualification, no future quota guarantee.",
    }
    try:
        receipt["probe_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        receipt["metadata_helper_sha256"] = hashlib.sha256(Path(__file__).with_name("check_gemini_model_access_v1.py").read_bytes()).hexdigest()
        receipt["request_payload"] = PAYLOAD
        with (args.output / "plan.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    except Exception:
        print(json.dumps({"status": "probe_setup_or_plan_write_failed", "request_attempted": False}))
        return 2
    started = time.perf_counter_ns()
    key = None
    state = {"request_attempted": False}
    try:
        try:
            key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        except Exception:
            outcome = {"status": "credential_environment_failed", "http_status": None, **state}
        else:
            if not key:
                outcome = {"status": "missing_process_credential", "http_status": None, **state}
            else:
                try:
                    outcome = probe(key, opener, state)
                except Exception:
                    outcome = {"status": "unexpected_probe_failure", "http_status": None, **state}
    finally:
        key = None
    receipt.update(outcome)
    receipt["elapsed_ns"] = time.perf_counter_ns() - started
    receipt["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        with (args.output / "result.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
    except Exception:
        print(json.dumps({"status": "receipt_write_failed", **state, "probe_outcome": outcome["status"]}))
        return 2
    print(json.dumps(receipt))
    return 0 if outcome["status"] == "synthetic_forced_tool_access_confirmed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
