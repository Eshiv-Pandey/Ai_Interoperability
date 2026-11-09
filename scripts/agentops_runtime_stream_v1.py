"""Passive ordered journal around an unchanged original bound run_async method.

Importing this module uses stdlib only and installs no patch. The caller passes
the original instance's bound method and explicit read-only SDK serializers.
Each original event is serialized before the identical object is yielded to
the downstream A2A converter. Capture faults disable observation, not business
execution. A missing/partial durable receipt cannot qualify ordered evidence.
Synchronous local writes add overhead; these times are not latency benchmarks.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import time


SCHEMA = "agentops-runtime-stream/1"
KNOWN_FIELDS = frozenset(("user_id", "session_id", "invocation_id", "new_message", "state_delta", "run_config", "yield_user_message"))
DEFAULT_LIMITS = {"max_invocations": 64, "max_events_per_invocation": 4096,
                  "max_json_bytes": 4 * 1024 * 1024, "max_total_bytes": 64 * 1024 * 1024, "max_files": 8192}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _strict(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate serialized JSON member")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite serialized JSON value")
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid)
    _json_bytes(result)  # also rejects a finite-looking exponent overflowing to infinity
    return result


def _regular(path, directory=False):
    path = Path(path).absolute()
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked capture path")
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError("nonregular capture path")
    return path


class RunAsyncJournal:
    """Delegate exactly once to an original bound run_async; never install it.

    ``event_serializer``, ``content_serializer`` and ``config_serializer`` must
    return complete UTF-8 JSON bytes (or a UTF-8 JSON string). They must not
    mutate objects. No fallback serializer, repr, environment or credential
    inspection is used. ``run_async`` preserves positional arguments, omitted
    keywords and identical supplied objects in the original invocation.

    ``finish()`` must be called after all invocations close. Consumers must
    require a persisted complete root receipt AND complete invocation receipts
    and verify every hash plus exact terminal membership (root result plus its
    declared files) before using the journal for ordered evidence. Pending,
    missing, empty or changed receipt files cannot qualify. Those conditions do not
    themselves establish a benchmark grade or source authentication.
    """
    def __init__(self, original_run_async, output, *, event_serializer,
                 content_serializer=None, config_serializer=None, limits=None):
        if not callable(original_run_async) or not callable(event_serializer):
            raise ValueError("original bound callable and event serializer are required")
        if any(value is not None and not callable(value) for value in (content_serializer, config_serializer)):
            raise ValueError("optional serializers must be callable")
        configured = dict(DEFAULT_LIMITS)
        if limits is not None:
            if type(limits) is not dict or not set(limits) <= set(configured):
                raise ValueError("unsupported recorder limits")
            configured.update(limits)
        if any(type(value) is not int or value <= 0 or value > DEFAULT_LIMITS[key] for key, value in configured.items()):
            raise ValueError("recorder limits must be bounded positive integers")
        if configured["max_total_bytes"] < 4 * configured["max_json_bytes"]:
            raise ValueError("total byte bound must reserve terminal receipt space")
        self.original_run_async, self.output = original_run_async, Path(output).absolute()
        self.event_serializer, self.content_serializer, self.config_serializer = event_serializer, content_serializer, config_serializer
        self.limits = configured
        self.calls_seen = self.global_yield_sequence = self.active_calls = self.total_bytes = self.file_attempts = 0
        self.receipts, self.errors, self.files = [], [], {}
        self.disabled = self.finalized = False
        self.root_receipt = None
        self.unallocated_calls = 0
        if self.output.exists() or self.output.is_symlink():
            raise FileExistsError("preserve existing runtime journal allocation")
        if self.output != self.output.resolve():
            raise ValueError("capture allocation must be canonical")
        ancestor = self.output.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        _regular(ancestor, True)
        self.output.mkdir(parents=True, exist_ok=False)
        _regular(self.output, True)
        self.source_path = _regular(Path(__file__).absolute())
        self.source_raw = self.source_path.read_bytes()
        # Constructor failure precedes installation and is deliberately not hidden.
        self._write("source/agentops_runtime_stream_v1.py", self.source_raw, terminal=True)
        self._write("plan.json", _json_bytes({"schema_version": SCHEMA, "created_at_utc": _now(),
                    "limits": self.limits, "observer_source": _digest(self.source_raw), "known_input_fields": sorted(KNOWN_FIELDS),
                    "original_call_installed_by_observer": False, "sdk_imported_by_observer": False,
                    "serializer_outputs_are_exact_captured_json_bytes": True, "source_authentication_proven": False,
                    "capture_failure_policy": "disable capture; preserve original delegation and outcomes; qualification remains incomplete"}), terminal=True)

    def _write(self, relative, raw, *, terminal=False):
        if type(raw) is not bytes or len(raw) > self.limits["max_json_bytes"]:
            raise ValueError("capture file byte bound")
        if self.file_attempts >= self.limits["max_files"]:
            raise ValueError("capture file count bound")
        reserve = 0 if terminal else 2 * self.limits["max_json_bytes"]
        if self.total_bytes + len(raw) > self.limits["max_total_bytes"] - reserve:
            raise ValueError("capture aggregate byte bound")
        if relative in self.files:
            raise FileExistsError("exclusive capture file already recorded")
        # Reserve the entire attempt before opening: a short/failed write can
        # leave bytes behind and must not free budget for subsequent receipts.
        self.file_attempts += 1
        self.total_bytes += len(raw)
        path = self.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _regular(path.parent, True)
        with path.open("xb") as stream:
            written = stream.write(raw)
            if written != len(raw):
                raise OSError("capture short write")
            stream.flush()
            os.fsync(stream.fileno())
        self.files[relative] = _digest(raw)
        return self.files[relative]

    def _fault(self, receipt, phase, error):
        problem = {"phase": phase, "error_type": type(error).__name__}
        # No exception messages, object reprs or arbitrary unsupported values.
        if len(self.errors) < 64:
            self.errors.append({"invocation_sequence": receipt.get("invocation_sequence"), **problem})
        if len(receipt["capture_errors"]) < 64:
            receipt["capture_errors"].append(problem)
        receipt.update(capture_disabled=True, capture_complete=False, status="partial")
        self.disabled = True

    def _write_receipt(self, relative, raw):
        """Publish qualifying JSON only after its exclusive pending file fsync.

        The final name is first reserved as an exclusive empty placeholder.
        A fault before publication retains empty final/pending evidence, never
        complete JSON at the final name. Replacement targets only that owned
        placeholder; preexisting final and pending names are never overwritten.
        """
        final = self.output / relative
        if relative in self.files or final.exists() or final.is_symlink():
            raise FileExistsError("terminal receipt allocation already consumed")
        if self.file_attempts + 2 > self.limits["max_files"]:
            raise ValueError("terminal pending and final file count bound")
        self.file_attempts += 1
        _regular(final.parent, True)
        descriptor = os.open(final, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        try:
            placeholder = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        self.files[relative] = _digest(b"")
        pending = relative + ".pending"
        identity = self._write(pending, raw, terminal=True)
        current = _regular(final).stat()
        if (current.st_dev, current.st_ino, current.st_size) != (placeholder.st_dev, placeholder.st_ino, 0) or final.read_bytes() != b"":
            raise ValueError("owned terminal placeholder changed before publication")
        os.replace(self.output / pending, final)
        del self.files[pending]
        self.files[relative] = identity
        return identity

    def _serialized(self, value, serializer):
        if serializer is None:
            raise ValueError("explicit serializer required for SDK input")
        raw = serializer(value)
        if type(raw) is str:
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or len(raw) > self.limits["max_json_bytes"]:
            raise ValueError("serializer output byte bound or type")
        parsed = _strict(raw)
        if type(parsed) is not dict:
            raise ValueError("serializer output must be a complete JSON object")
        return raw, parsed

    def _inputs(self, receipt, args, kwargs, directory):
        unsupported = bool(args) or bool(set(kwargs) - KNOWN_FIELDS)
        record = {"schema_version": SCHEMA, "invocation_sequence": receipt["invocation_sequence"],
                  "supplied_known_fields": sorted(set(kwargs) & KNOWN_FIELDS), "omitted_known_fields": sorted(KNOWN_FIELDS - set(kwargs)),
                  "positional_argument_count": len(args), "unsupported_keyword_field_count": len(set(kwargs) - KNOWN_FIELDS),
                  "unsupported_capture": unsupported, "objects_or_argument_values_rewritten": False}
        for key in ("user_id", "session_id", "invocation_id", "yield_user_message"):
            if key not in kwargs:
                continue
            value = kwargs[key]
            valid = type(value) is bool if key == "yield_user_message" else type(value) is str or key == "invocation_id" and value is None
            if not valid:
                raise ValueError("unsupported known identity/boolean input type")
            record[key] = value
        for key, serializer in (("new_message", self.content_serializer), ("run_config", self.config_serializer)):
            if key not in kwargs:
                continue
            if kwargs[key] is None:
                record[key] = None
            else:
                raw, _ = self._serialized(kwargs[key], serializer)
                relative = directory + "/input/" + key + ".json"
                record[key] = {"path": relative, **self._write(relative, raw)}
        if "state_delta" in kwargs:
            value = kwargs["state_delta"]
            if value is not None and type(value) is not dict:
                raise ValueError("state delta must be original JSON object or null")
            raw = _json_bytes(value)
            if len(raw) > self.limits["max_json_bytes"]:
                raise ValueError("state delta byte bound")
            _strict(raw)
            record["state_delta"] = value
        self._write(directory + "/input.json", _json_bytes(record))
        receipt["supplied_invocation_id_present"] = "invocation_id" in kwargs
        receipt["supplied_invocation_id"] = kwargs.get("invocation_id")
        receipt["inputs_complete"] = not unsupported
        if unsupported:
            raise ValueError("unsupported positional or keyword input capture")

    def _event(self, receipt, event, directory, ordinal, global_sequence):
        if ordinal > self.limits["max_events_per_invocation"]:
            raise ValueError("per invocation event count bound")
        observed_at, monotonic = _now(), time.monotonic_ns()
        raw, value = self._serialized(event, self.event_serializer)
        relative = directory + f"/events/{ordinal:06d}.json"
        content = value.get("content")
        parts = content.get("parts") if type(content) is dict else None
        identity = {key: value.get(key) if type(value.get(key)) is str else None for key in ("id", "invocation_id")}
        complete_identity = all(type(value.get(key)) is str and bool(value[key]) for key in identity)
        receipt["event_identity_fields_complete"] = receipt["event_identity_fields_complete"] and complete_identity
        invocation = identity["invocation_id"]
        if invocation and invocation not in receipt["observed_invocation_ids"]:
            receipt["observed_invocation_ids"].append(invocation)
        receipt["events"].append({"event_ordinal": ordinal, "batch_ordinal": ordinal,
                    "global_yield_sequence": global_sequence, "observed_at_utc": observed_at, "monotonic_ns": monotonic,
                    "actual_event_id": identity["id"], "actual_invocation_id": invocation,
                    "part_count_in_original_yield": len(parts) if type(parts) is list else None,
                    "captured_before_downstream_yield": True, "path": relative, **self._write(relative, raw)})
        receipt["events_recorded"] += 1

    async def run_async(self, *args, **kwargs):
        self.calls_seen += 1
        sequence = self.calls_seen
        if self.finalized and self.root_receipt is not None:
            self.root_receipt.update(status="partial", capture_complete=False,
                                    eligible_for_ordered_evidence_checks=False, post_finalization_call_observed=True)
            if "after-finalization-error.json" not in self.files:
                try:
                    self._write("after-finalization-error.json", _json_bytes({"schema_version": SCHEMA,
                                "status": "partial", "reason": "original call after terminal recorder receipt",
                                "invocation_sequence": sequence, "observed_at_utc": _now()}), terminal=True)
                except Exception:
                    self.root_receipt["post_finalization_diagnostic_persisted"] = False
        allocated = sequence <= self.limits["max_invocations"] and not self.finalized
        directory = f"invocations/{sequence:06d}"
        receipt = {"schema_version": SCHEMA, "invocation_sequence": sequence, "directory": directory if allocated else None,
                   "directory_created_exclusively": False,
                   "status": "partial", "started_at_utc": _now(), "started_monotonic_ns": time.monotonic_ns(),
                   "capture_complete": False, "capture_disabled": self.disabled or not allocated,
                   "capture_errors": [], "inputs_complete": False, "events": [], "events_seen": 0, "events_recorded": 0,
                   "supplied_invocation_id_present": False, "supplied_invocation_id": None,
                   "supplied_invocation_id_matches_all_observed": None, "consumer_protocol_throws": 0,
                   "consumer_non_none_sends": 0,
                   "downstream_yields_entered": 0, "event_identity_fields_complete": True, "observed_invocation_ids": [],
                   "original_call_attempts": 0, "original_termination": None, "original_error_type": None,
                   "original_aclose_attempted": False, "original_aclose_completed": False, "cleanup_error_type": None,
                   "durable_receipt_written": False, "source_authentication_proven": False,
                   "benchmark_grade_proven": False, "causal_tool_execution_order_proven": False}
        if allocated:
            self.receipts.append(receipt)
        else:
            self.unallocated_calls += 1
            self._fault(receipt, "allocation", ValueError("invocation bound or finalized recorder"))
        self.active_calls += 1
        original = None
        try:
            if allocated:
                try:
                    (self.output / directory).mkdir(parents=True, exist_ok=False)
                    _regular(self.output / directory, True)
                    receipt["directory_created_exclusively"] = True
                    if not receipt["capture_disabled"]:
                        self._inputs(receipt, args, kwargs, directory)
                except Exception as error:
                    self._fault(receipt, "input_capture", error)
            receipt["original_call_attempts"] = 1
            try:
                original = self.original_run_async(*args, **kwargs)
            except BaseException as error:
                receipt.update(original_termination="call_exception", original_error_type=type(error).__name__)
                raise
            advance, value = "next", None
            while True:
                try:
                    if advance == "throw":
                        event = await original.athrow(value)
                    elif advance == "send":
                        event = await original.asend(value)
                    else:
                        event = await original.__anext__()
                except StopAsyncIteration:
                    receipt["original_termination"] = "normal_exhaustion"
                    break
                except asyncio.CancelledError as error:
                    receipt.update(original_termination="cancelled_at_downstream_yield" if advance == "throw" else "cancelled_during_original_next", original_error_type=type(error).__name__)
                    raise
                except BaseException as error:
                    termination = "original_exception"
                    if advance == "throw":
                        termination = "consumer_aclose" if isinstance(value, GeneratorExit) else "consumer_athrow"
                    receipt.update(original_termination=termination, original_error_type=type(error).__name__)
                    raise
                receipt["events_seen"] += 1
                self.global_yield_sequence += 1
                if not receipt["capture_disabled"] and not self.disabled:
                    try:
                        self._event(receipt, event, directory, receipt["events_seen"], self.global_yield_sequence)
                    except Exception as error:
                        self._fault(receipt, "event_capture", error)
                else:
                    receipt["capture_disabled"] = True
                receipt["downstream_yields_entered"] += 1
                try:
                    sent = yield event  # same object, never a reconstruction or converter output
                except BaseException as error:
                    # Forward, rather than replacing recoverable consumer throws
                    # with aclose. Do not inspect or serialize protocol values.
                    advance, value = "throw", error
                    receipt["consumer_protocol_throws"] += 1
                else:
                    advance, value = ("next", None) if sent is None else ("send", sent)
                    if sent is not None:
                        receipt["consumer_non_none_sends"] += 1
        finally:
            try:
                if original is not None:
                    receipt["original_aclose_attempted"] = True
                    try:
                        # Same task/context as delegation: no helper task, shield,
                        # timeout, retry, or cancellation suppression changes ADK.
                        await original.aclose()
                        receipt["original_aclose_completed"] = True
                    except BaseException as error:
                        receipt["cleanup_error_type"] = type(error).__name__
                        raise
            finally:
                self.active_calls -= 1
                receipt.update(finished_at_utc=_now(), finished_monotonic_ns=time.monotonic_ns())
                supplied = receipt["supplied_invocation_id"]
                if receipt["supplied_invocation_id_present"] and supplied is not None:
                    receipt["supplied_invocation_id_matches_all_observed"] = (receipt["event_identity_fields_complete"]
                            and bool(receipt["observed_invocation_ids"]) and all(value == supplied for value in receipt["observed_invocation_ids"]))
                receipt["capture_complete"] = (not receipt["capture_disabled"] and not receipt["capture_errors"]
                        and receipt["inputs_complete"] and receipt["events_recorded"] == receipt["events_seen"]
                        and receipt["original_termination"] == "normal_exhaustion" and receipt["original_aclose_completed"])
                receipt["status"] = "recorded" if receipt["capture_complete"] else "partial"
                if allocated and receipt["directory_created_exclusively"]:
                    try:
                        # The on-disk value records this completed exclusive write.
                        receipt["durable_receipt_written"] = True
                        self._write_receipt(directory + "/result.json", _json_bytes(receipt))
                    except Exception as error:
                        receipt["durable_receipt_written"] = False
                        self._fault(receipt, "terminal_receipt", error)

    def _inventory(self):
        _regular(self.output, True)
        result = {}
        total = 0
        for path in sorted(self.output.rglob("*")):
            _regular(path, path.is_dir())
            if path.is_file():
                if len(result) >= self.limits["max_files"] or path.stat().st_size > self.limits["max_json_bytes"]:
                    raise ValueError("terminal inventory bound")
                result[path.relative_to(self.output).as_posix()] = _digest(path.read_bytes())
                total += result[path.relative_to(self.output).as_posix()]["bytes"]
                if total > self.limits["max_total_bytes"]:
                    raise ValueError("terminal inventory aggregate byte bound")
        return result

    def finish(self):
        """One exclusive terminal root receipt; callers must reject partial state."""
        if self.finalized:
            return self.root_receipt
        self.finalized = True
        summaries = [{key: row[key] for key in ("invocation_sequence", "directory", "status", "capture_complete",
                    "capture_disabled", "durable_receipt_written", "original_termination", "original_aclose_completed",
                    "events_seen", "events_recorded", "event_identity_fields_complete", "observed_invocation_ids",
                    "supplied_invocation_id_present", "supplied_invocation_id", "supplied_invocation_id_matches_all_observed")} for row in self.receipts]
        result = {"schema_version": SCHEMA, "status": "partial", "calls_seen": self.calls_seen,
                  "global_yields_seen": self.global_yield_sequence, "active_calls": self.active_calls,
                  "unallocated_calls": self.unallocated_calls, "capture_disabled": self.disabled,
                  "invocations": summaries, "errors": list(self.errors), "files": {}, "finished_at_utc": _now(),
                  "durable_receipt_written": False, "capture_complete": False, "eligible_for_ordered_evidence_checks": False,
                  "source_authentication_proven": False, "benchmark_grade_proven": False,
                  "causal_tool_execution_order_proven": False, "latency_benchmark_proven": False,
                  "directory_entry_crash_durability_proven": False}
        self.root_receipt = result
        try:
            result["files"] = self._inventory()
            unchanged = result["files"] == self.files and _regular(self.source_path).read_bytes() == self.source_raw
            result["captured_inputs_unchanged"] = unchanged
            complete = (self.calls_seen > 0 and not self.active_calls and not self.disabled and not self.unallocated_calls
                        and unchanged and all(row["capture_complete"] and row["durable_receipt_written"] for row in self.receipts))
            result["capture_complete"] = bool(complete)
            result["eligible_for_ordered_evidence_checks"] = bool(complete and all(row["events_seen"] > 0 and row["event_identity_fields_complete"]
                        and row["supplied_invocation_id_matches_all_observed"] is not False for row in self.receipts))
            result["status"] = "recorded" if complete else "partial"
            result["durable_receipt_written"] = True
            self._write_receipt("result.json", _json_bytes(result))
        except Exception as error:
            result.update(status="partial", durable_receipt_written=False, capture_complete=False,
                          eligible_for_ordered_evidence_checks=False, terminal_error_type=type(error).__name__)
        return result
