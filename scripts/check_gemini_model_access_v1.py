"""Check metadata access for the unchanged AP2 model without generating content.

The key comes only from the child process environment. Never retain headers,
provider response bodies, exception messages, or credentials in the receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request


MODEL = "gemini-3.1-flash-lite-preview"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
MAX_RESPONSE_BYTES = 1_048_576


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_metadata(payload: object) -> dict:
    """Return only fixed-name equality and a boolean for advertised generation."""
    if not isinstance(payload, dict):
        raise ValueError
    methods = payload.get("supportedGenerationMethods")
    if not isinstance(methods, list) or not all(isinstance(x, str) for x in methods):
        raise ValueError
    if payload.get("name") != f"models/{MODEL}":
        raise ValueError
    return {
        "returned_model_name_matches": True,
        "generate_content_advertised": "generateContent" in methods,
    }


def probe(key: str, opener, attempt_state: dict | None = None) -> dict:
    if attempt_state is None:
        attempt_state = {"request_attempted": False}

    def result(**values):
        return {"request_attempted": attempt_state["request_attempted"], **values}

    try:
        request = urllib.request.Request(
            ENDPOINT,
            headers={"x-goog-api-key": key, "Accept": "application/json"},
            method="GET",
        )
        attempt_state["request_attempted"] = True
        with opener.open(request, timeout=20) as response:
            status = response.status
            if status != 200:
                return result(status="unexpected_http_status", http_status=status)
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return result(status="metadata_response_too_large", http_status=status)
        try:
            metadata = validate_metadata(json.loads(raw))
        except (ValueError, TypeError, UnicodeError):
            return result(status="invalid_metadata_response", http_status=status)
        return result(status="metadata_access_confirmed", http_status=status, **metadata)
    except urllib.error.HTTPError as error:
        # Do not read the error body or serialize the exception/header/URL.
        status = error.code
        try:
            error.close()
        except Exception:
            pass
        label = {
            401: "provider_access_rejected",
            403: "provider_access_rejected",
            404: "requested_model_not_found",
            429: "provider_rate_or_quota_rejected",
        }.get(status, "provider_http_failure")
        if 300 <= status < 400:
            label = "redirect_rejected"
        return result(status=label, http_status=status)
    except (urllib.error.URLError, OSError, TimeoutError):
        return result(status="network_or_tls_failure", http_status=None)
    except Exception:
        # No traceback: dependencies can embed request details in exceptions.
        return result(status="probe_failure", http_status=None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New receipt directory")
    args = parser.parse_args()
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except OSError:
        print(json.dumps({"status": "output_allocation_failed", "request_attempted": False}))
        return 2

    receipt = {
        "schema_version": "gemini-model-metadata-access/1",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "GET",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "backend": "Gemini Developer API",
        "maximum_requests": 1,
        "retries": 0,
        "redirects_allowed": False,
        "content_generation_requested": False,
        "request_attempted": False,
        "generation_quota_verified": False,
        "free_tier_or_billing_verified": False,
        "tool_calling_verified": False,
        "native_ap2_execution_verified": False,
    }
    # Record the prospective request contract before reading the environment key.
    try:
        receipt["probe_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        with (args.output / "plan.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
        opener = urllib.request.build_opener(
            NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
        )
    except Exception:
        print(json.dumps({"status": "probe_setup_or_plan_write_failed", "request_attempted": False}))
        return 2

    started = time.perf_counter_ns()
    key = None
    attempt_state = {"request_attempted": False}
    try:
        try:
            key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        except Exception:
            outcome = {"status": "credential_environment_failed", "http_status": None, **attempt_state}
        else:
            if not key:
                outcome = {"status": "missing_process_credential", "http_status": None, **attempt_state}
            else:
                try:
                    outcome = probe(key, opener, attempt_state)
                except Exception:
                    outcome = {"status": "unexpected_probe_failure", "http_status": None, **attempt_state}
    finally:
        key = None
    receipt.update(outcome)
    receipt["elapsed_ns"] = time.perf_counter_ns() - started
    receipt["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        with (args.output / "result.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
    except Exception:
        print(json.dumps({"status": "receipt_write_failed", "request_attempted": receipt["request_attempted"], "probe_outcome": outcome["status"]}))
        return 2
    print(json.dumps(receipt))
    return 0 if outcome["status"] == "metadata_access_confirmed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
