"""Additive owned 120-second sender and bounded evidence drain.

No SDK or original application imports. The real provider credential remains
only in this parent boundary. Late outcomes after a bounded capture freeze are
unmeasured; they cannot mutate the retained evidence or become measured zero.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('_native_shopper_boundary_v2_inherited', ROOT / 'scripts/run_ap2_original_native_repeat_v3.py')
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)
REQUEST_TIMEOUT_SECONDS = 120
MAXIMUM_DRAIN_SECONDS = 150


class ProviderBoundary(H.ProviderBoundary):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._capture = threading.Condition(threading.RLock())
        self._active_handlers = 0
        self._closing = False
        self._frozen = False

    def _send_live(self, raw):
        request = urllib.request.Request(H.API_ORIGIN + H.API_PATH, data=raw,
                headers={'Content-Type': 'application/json', 'x-goog-api-key': self.secret}, method='POST')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), H.NoRedirect())
        try:
            response = opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(H.MAX_RESPONSE_BYTES + 1)
            if len(body) > H.MAX_RESPONSE_BYTES:
                raise ValueError('provider_response_size_bound')
            return response.status, body

    def begin_shutdown(self):
        with self._capture:
            self._closing = True
            self.stopped = True
            self._capture.notify_all()

    def drain_and_freeze(self, maximum_seconds):
        """Freeze a stable ledger, retaining open allocations at the deadline.

        The deadline concerns the evidence drain. urllib's sender timeout is a
        transport wait option, not a separately proven whole-request wall cap.
        Neither deadline permits a fabricated terminal provider observation.
        """
        if not 0 <= maximum_seconds <= MAXIMUM_DRAIN_SECONDS:
            raise ValueError('bounded_provider_drain_required')
        self.begin_shutdown()
        started = time.monotonic()
        deadline = started + maximum_seconds
        with self._capture:
            while self._active_handlers and time.monotonic() < deadline:
                self._capture.wait(max(0, deadline - time.monotonic()))
            self._frozen = True
            return {'schema_version': 'ap2-provider-drain/2', 'time': H.now(),
                    'admission_closed': True, 'capture_frozen': True,
                    'all_handlers_completed': self._active_handlers == 0,
                    'active_handlers_at_capture_freeze': self._active_handlers,
                    'maximum_drain_seconds': maximum_seconds,
                    'elapsed_drain_seconds': time.monotonic() - started,
                    'allocated_upstream_calls_at_capture_freeze': self.calls,
                    'request_bytes_at_capture_freeze': self.request_bytes,
                    'late_sender_outcomes_retained': False,
                    'unfinished_allocations_require_unknown_usage': True}

    def request(self, path, raw, downstream_key):
        # These admission, payload, byte and credential checks preserve the
        # inherited V3 boundary's conditions. Only owned lifecycle/sender
        # controls differ; original model payloads pass through untouched.
        if path != H.API_PATH or downstream_key != H.SYNTHETIC_KEY or not raw or len(raw) > H.MAX_REQUEST_BYTES:
            return 400, b'{"error":{"message":"owned_provider_request_refused"}}'
        try:
            payload = json.loads(raw)
            if type(payload) is not dict or 'contents' not in payload:
                raise ValueError('invalid_generate_payload')
        except (ValueError, UnicodeDecodeError):
            return 400, b'{"error":{"message":"owned_provider_invalid_json"}}'
        with self._capture:
            if self._closing or self._frozen:
                return 429, b'{"error":{"message":"owned_provider_admission_closed"}}'
            self._active_handlers += 1
        try:
            with self.lock:
                with self._capture:
                    if self.stopped or self.calls >= H.MAX_CALLS or self.request_bytes + len(raw) > H.MAX_TOTAL_REQUEST_BYTES or self.usage_tokens >= H.MAX_TOTAL_USAGE_TOKENS:
                        self.stopped = True
                        if not self._frozen:
                            H.append(self.output / 'local-refusals.jsonl', {'time': H.now(), 'status': 'no_upstream_call_budget_or_prior_failure'})
                        return 429, b'{"error":{"message":"owned_provider_budget_or_prior_failure"}}'
                if self.last_started is not None:
                    self.sleeper(max(0.0, self.interval - (self.clock() - self.last_started)))
                with self._capture:
                    # Closing during pacing must not allocate a new call.
                    if self._closing or self._frozen or self.stopped:
                        return 429, b'{"error":{"message":"owned_provider_admission_closed"}}'
                    self.last_started = self.clock()
                    number = self.calls
                    self.calls += 1
                    self.request_bytes += len(raw)
                    (self.output / f'{number:03d}.request.json').write_bytes(self.redact(raw))
                    H.append(self.output / 'ledger.jsonl', {'allocation': number, 'phase': 'started', 'time': H.now(),
                            'provider_mode': self.mode, 'path': H.API_PATH, 'request': H.digest(self.redact(raw)),
                            'upstream_call_consumed': True, 'retry': False})
                status, body, problem = 502, b'{"error":{"message":"owned_provider_transport_failure"}}', None
                total, unknown_success = 0, False
                try:
                    status, body = self.send(raw)
                    if type(status) is not int or type(body) is not bytes or len(body) > H.MAX_RESPONSE_BYTES:
                        raise ValueError('malformed_provider_response')
                    body = self.redact(body)
                    parsed = json.loads(body)
                    usage = parsed.get('usageMetadata', {}) if type(parsed) is dict else {}
                    total = usage.get('totalTokenCount')
                    if status == 200 and (type(total) is not int or total <= 0):
                        unknown_success, total = True, 0
                    elif status != 200 and total is None:
                        total = 0
                    if type(total) is not int or total < 0:
                        raise ValueError('malformed_provider_usage')
                except BaseException as error:
                    problem = type(error).__name__
                    # Keep the received adverse HTTP/body when present.
                    if type(status) is not int or type(body) is not bytes or len(body) > H.MAX_RESPONSE_BYTES:
                        status, body = 502, b'{"error":{"message":"owned_provider_transport_or_size_failure"}}'
                with self._capture:
                    if self._frozen:
                        # The opening ledger remains unclosed and unmeasured.
                        # No late counter, terminal ledger or payload writes.
                        return 503, b'{"error":{"message":"owned_provider_capture_deadline"}}'
                    if unknown_success:
                        self.unknown_usage_responses += 1
                        self.stopped = True
                    if problem is None:
                        self.usage_tokens += total
                        if status == 200:
                            self.successful_responses += 1
                    if problem is not None or status != 200:
                        self.stopped = self.failed = True
                    (self.output / f'{number:03d}.response.json').write_bytes(body)
                    H.append(self.output / 'ledger.jsonl', {'allocation': number, 'phase': 'finished', 'time': H.now(),
                            'http_status': status, 'response': H.digest(body), 'transport_error_type': problem,
                            'observed_cumulative_usage_tokens': self.usage_tokens, 'upstream_call_consumed': True})
                    return status, body
        finally:
            with self._capture:
                self._active_handlers -= 1
                self._capture.notify_all()

    def summary(self):
        with self._capture:
            value = super().summary()
            value.update(request_transport_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
                    request_timeout_is_independent_whole_request_wall_cap=False,
                    active_handlers=self._active_handlers, admission_closed=self._closing,
                    capture_frozen=self._frozen)
            return value
