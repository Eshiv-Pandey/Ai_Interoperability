"""Unexecuted synthetic durable-observer tests; no original or SDK import.

Frozen authored observers are loaded only for sink compatibility. Coroutines
are driven finitely without an event loop, thread, socket or subprocess.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).absolute().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


durable = load("_constructed_durable_observer", "src/interoperability/ap2_hp_durable_observer_v1.py")
frozen_asgi = load("_constructed_frozen_asgi", "src/interoperability/ap2_hp_passive_capture_v1.py")
frozen_public = load("_constructed_frozen_public", "src/interoperability/ap2_hp_reference_execution_v1.py")


def run_immediate(coroutine):
    if type(coroutine) is not types.CoroutineType:
        raise TypeError("A constructed native coroutine is required")
    try:
        try:
            coroutine.send(None)
        except StopIteration as completed:
            return completed.value
        raise AssertionError("Constructed fixture unexpectedly suspended")
    finally:
        coroutine.close()


class DurableObserverChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="constructed-durable-observer-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.owners = []
        self.addCleanup(self.close_owners)

    def close_owners(self):
        for owner in self.owners:
            owner.close()

    def owner(self, streams=None, limits=durable.Limits()):
        result = durable.DurableRecorder.allocate(self.directory / ("artifacts-" + str(len(self.owners))),
                                                  streams or {"http": "raw_asgi"}, limits=limits)
        self.owners.append(result)
        self.assertTrue(result.ready)
        return result

    @staticmethod
    def rows(owner):
        return [json.loads(line) for line in (owner.path / "events.jsonl").read_bytes().splitlines()]

    @classmethod
    def payloads(cls, owner):
        return [durable.decode_value(row["payload"]) for row in cls.rows(owner)]

    @staticmethod
    def witness(records, complete=True, active=0):
        return {"source_complete": complete, "active_operations": active, "attempted_records": records}

    @staticmethod
    def public(sequence, call, boundary, value=None):
        row = {"sequence": sequence, "call": call, "boundary": boundary,
               "operation": "send_a2a_message", "endpoint": frozen_public.MERCHANT}
        if boundary != "error":
            row["public_value"] = value
        return row

    def http_fixture(self, owner):
        scope = {"type": "http", "path": "/a2a", "raw_path": b"/a2a", "headers": [(b"x", b"one"), (b"x", b"two")],
                 "client": ("127.0.0.1", 3210)}
        request = {"type": "http.request", "body": b"request", "more_body": False, (b"extension", 1): (True, 1)}
        start = {"type": "http.response.start", "status": 200, "headers": [(b"x", b"one"), (b"x", b"two")]}
        body = {"type": "http.response.body", "body": b"response", "more_body": False,
                "marker": {"type": "bytes", "value": "untrusted application marker"}}
        original_return, send_return, delivered = object(), object(), []
        async def receive():
            return request
        async def send(event):
            delivered.append(event)
            return send_return
        async def app(actual_scope, actual_receive, actual_send):
            self.assertIs(actual_scope, scope)
            self.assertIs(await actual_receive(), request)
            self.assertIs(await actual_send(start), send_return)
            self.assertIs(await actual_send(body), send_return)
            return original_return
        wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
        return wrapper, scope, request, start, body, original_return, receive, send, delivered

    def test_tagged_roundtrip_preserves_types_keys_order_bytes_and_negative_zero(self):
        marker = {"type": "tuple", "items": ["ordinary application dictionary"]}
        value = {True: (True, 1, -0.0), 2: [b"\x00\xff", marker], (b"key", 1): {None: "none", "1": "text"}}
        decoded = durable.decode_value(durable.encode_value(value))
        self.assertEqual(list(decoded), list(value))
        self.assertIs(type(next(iter(decoded))), bool)
        self.assertIs(type(decoded[True]), tuple)
        self.assertIs(type(decoded[True][0]), bool)
        self.assertIs(type(decoded[True][1]), int)
        self.assertEqual(math.copysign(1, decoded[True][2]), -1)
        self.assertIs(type(decoded[2][0]), bytes)
        self.assertEqual(decoded[2][1], marker)
        self.assertIs(type(decoded[2][1]), dict)
        self.assertEqual(decoded[(b"key", 1)], {None: "none", "1": "text"})

    def test_codec_rejects_nonfinite_cycles_unsupported_and_tampered_tags(self):
        cycle = []
        cycle.append(cycle)
        for value in (float("nan"), float("inf"), object(), bytearray(b"mutable"), {1, 2}, cycle):
            with self.assertRaises(durable.ObservationError):
                durable.encode_value(value)
        tag = durable.encode_value(b"raw")
        tag["sha256"] = "0" * 64
        with self.assertRaises(durable.ObservationError):
            durable.decode_value(tag)
        class OpaqueEquality:
            def __eq__(self, other):
                raise AssertionError("Opaque digest comparison must not occur")
        wrong_digest = durable.encode_value(b"raw")
        wrong_digest["sha256"] = OpaqueEquality()
        with self.assertRaises(durable.ObservationError):
            durable.decode_value(wrong_digest)
        collision = {"type": "dict", "entries": [[durable.encode_value(True), durable.encode_value("bool")],
                                                      [durable.encode_value(1), durable.encode_value("int")]]}
        with self.assertRaises(durable.ObservationError):
            durable.decode_value(collision)
        with self.assertRaises(durable.ObservationError):
            durable.encode_value([[[[True]]]], durable.Limits(depth=2))

    def test_allocation_is_exclusive_and_invalid_targets_do_not_overwrite(self):
        target = self.directory / "existing"
        target.mkdir()
        sentinel = target / "sentinel"
        sentinel.write_bytes(b"owned elsewhere")
        with self.assertRaises(durable.ObservationError):
            durable.DurableRecorder.allocate(target, {"http": "raw_asgi"})
        self.assertEqual(sentinel.read_bytes(), b"owned elsewhere")
        with self.assertRaises(durable.ObservationError):
            durable.DurableRecorder.allocate(Path("relative"), {"http": "raw_asgi"})
        for streams in ({}, {"../bad": "public"}, {"good": "unknown"}):
            with self.assertRaises(durable.ObservationError):
                durable.DurableRecorder.allocate(self.directory / "invalid", streams)
        self.assertFalse((self.directory / "invalid").exists())

    def test_partial_allocation_returns_its_owned_descriptors_for_cleanup(self):
        with patch.object(durable.os, "fsync", side_effect=OSError("constructed allocation fsync failure")):
            owner = durable.DurableRecorder.allocate(self.directory / "partial", {"http": "raw_asgi"})
        self.owners.append(owner)
        self.assertFalse(owner.ready)
        self.assertFalse(owner.capture_complete)
        self.assertTrue(owner.report()["owned_directory_allocated"])
        self.assertTrue(owner.report()["open_file_authority_retained"])
        self.assertTrue(owner.close())
        self.assertFalse(owner.report()["open_file_authority_retained"])

    def test_full_write_handles_short_writes_and_fsyncs_before_acknowledgment(self):
        owner = self.owner({"client": "public"})
        write, fsync = durable.os.write, durable.os.fsync
        writes, synced = [], []
        def short(fd, raw):
            writes.append(len(raw))
            return write(fd, raw[:7])
        def sync(fd):
            synced.append(fd)
            return fsync(fd)
        with patch.object(durable.os, "write", side_effect=short), patch.object(durable.os, "fsync", side_effect=sync):
            self.assertTrue(owner.append("client", self.public(0, 0, "attempt", {"request": True})))
        self.assertGreater(len(writes), 1)
        self.assertEqual(len(synced), 1)
        self.assertEqual(owner.committed_events, 1)
        self.assertTrue(owner.append("client", self.public(1, 0, "returned", {"result": True})))
        self.assertTrue(owner.finish_stream("client", self.witness(2)))
        self.assertTrue(owner.publish())
        self.assertTrue(owner.published_complete)
        manifest = json.loads((owner.path / "terminal.json").read_bytes())
        raw = (owner.path / "events.jsonl").read_bytes()
        self.assertEqual(manifest["journal"], {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        self.assertEqual((owner.path / "terminal.pending.json").read_bytes(), (owner.path / "terminal.json").read_bytes())

    def test_raw_http_preserves_original_objects_and_tags_marker_data_once(self):
        owner = self.owner()
        wrapper, scope, request, start, body, returned, receive, send, delivered = self.http_fixture(owner)
        original_request = durable.encode_value(request)
        original_scope = durable.encode_value(scope)
        self.assertIs(run_immediate(wrapper(scope, receive, send)), returned)
        self.assertIs(delivered[0], start)
        self.assertIs(delivered[1], body)
        self.assertEqual(durable.encode_value(scope), original_scope)
        self.assertEqual(durable.encode_value(request), original_request)
        payloads = self.payloads(owner)
        self.assertEqual([row["global_index"] for row in self.rows(owner)], list(range(len(payloads))))
        self.assertEqual([row["sequence"] for row in payloads], list(range(len(payloads))))
        received = next(row["value"] for row in payloads if row["boundary"] == "receive_returned")
        self.assertIs(type(received[(b"extension", 1)]), tuple)
        self.assertIs(type(received["body"]), bytes)
        recorded_body = next(row["value"] for row in payloads if row["boundary"] == "send_attempt" and row["value"]["type"] == "http.response.body")
        self.assertEqual(recorded_body["marker"], body["marker"])
        self.assertIs(type(recorded_body["marker"]), dict)
        self.assertTrue(wrapper.finish())
        self.assertTrue(owner.publish())
        self.assertTrue(owner.published_complete)

    def test_append_validates_and_publishes_the_same_detached_encoded_snapshot(self):
        owner = self.owner({"client": "public"})
        row = self.public(0, 0, "attempt", {"snapshot": "before"})
        original_encode = durable.encode_value
        def mutate_after_encode(value, limits=durable.Limits()):
            tagged = original_encode(value, limits)
            if value is row:
                row["sequence"], row["call"] = 999, 999
                row["public_value"]["snapshot"] = "after"
            return tagged
        with patch.object(durable, "encode_value", side_effect=mutate_after_encode):
            self.assertTrue(owner.append("client", row))
        envelope = self.rows(owner)[0]
        payload = self.payloads(owner)[0]
        self.assertEqual(envelope["source_index"], 0)
        self.assertEqual(payload["sequence"], 0)
        self.assertEqual(payload["call"], 0)
        self.assertEqual(payload["public_value"], {"snapshot": "before"})
        self.assertEqual(row["sequence"], 999)
        self.assertTrue(owner.append("client", self.public(1, 0, "returned", {"result": True})))
        self.assertTrue(owner.finish_stream("client", self.witness(2)))
        self.assertTrue(owner.publish())

    def test_raw_receive_send_and_application_errors_preserve_exact_exception(self):
        for boundary in ("receive", "send", "application"):
            owner = self.owner()
            failure = RuntimeError("constructed " + boundary)
            event = {"type": "http.response.start", "status": 200}
            received = []
            async def receive():
                raise failure
            async def send(actual):
                received.append(actual)
                raise failure
            async def app(scope, recv, emit):
                if boundary == "receive":
                    await recv()
                elif boundary == "send":
                    await emit(event)
                else:
                    raise failure
            wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
            with self.assertRaises(RuntimeError) as caught:
                run_immediate(wrapper({"type": "http"}, receive, send))
            self.assertIs(caught.exception, failure)
            if boundary == "send":
                self.assertIs(received[0], event)
            self.assertTrue(wrapper.capture_complete)
            self.assertEqual(wrapper.active_io_operations, 0)
            self.assertEqual(self.payloads(owner)[-1]["boundary"], "application_error")
            self.assertTrue(wrapper.finish())
            self.assertTrue(owner.publish())

    def test_partial_write_and_fsync_failures_keep_original_http_calls_and_partial_evidence(self):
        for stage in ("partial_write", "fsync"):
            owner = self.owner()
            wrapper, scope, request, start, body, returned, receive, send, delivered = self.http_fixture(owner)
            original_write = durable.os.write
            written = False
            def fail_after_prefix(fd, raw):
                nonlocal written
                if not written:
                    written = True
                    return original_write(fd, raw[:5])
                raise OSError("constructed write failure")
            patcher = patch.object(durable.os, "write", side_effect=fail_after_prefix) if stage == "partial_write" else patch.object(
                durable.os, "fsync", side_effect=OSError("constructed append fsync failure"))
            with patcher:
                self.assertIs(run_immediate(wrapper(scope, receive, send)), returned)
            self.assertIs(delivered[0], start)
            self.assertIs(delivered[1], body)
            self.assertFalse(wrapper.capture_complete)
            self.assertTrue(owner.journal_poisoned)
            self.assertEqual(owner.committed_events, 0)
            self.assertTrue(wrapper.finish())
            self.assertFalse(owner.publish())
            self.assertFalse((owner.path / "terminal.json").exists())
            self.assertTrue(owner.publish(allow_incomplete=True))
            manifest = json.loads((owner.path / "terminal.json").read_bytes())
            self.assertFalse(manifest["capture_complete_for_declared_intervals"])
            self.assertFalse(manifest["committed_prefix_identity_verified"])

    def test_malformed_and_unserializable_io_is_forwarded_with_incomplete_observation(self):
        for value in (object(), {"type": "http.request", "body": object()}, {"type": "http.request", "body": b"raw", "more_body": 1}):
            owner = self.owner()
            result, delivered = object(), []
            async def receive():
                return value
            async def send(event):
                delivered.append(event)
            async def app(scope, recv, emit):
                self.assertIs(await recv(), value)
                await emit({"type": "http.response.start", "status": 200})
                await emit({"type": "http.response.body", "body": b"done"})
                return result
            wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
            self.assertIs(run_immediate(wrapper({"type": "http"}, receive, send)), result)
            self.assertEqual(len(delivered), 2)
            self.assertFalse(wrapper.capture_complete)
            self.assertFalse(owner.capture_complete)
        class OpaqueScopeType:
            def __eq__(self, other):
                raise AssertionError("Opaque scope comparison must not occur")
        owner = self.owner()
        scope, returned = {"type": OpaqueScopeType()}, object()
        async def receive():
            return object()
        async def send(event):
            return None
        async def app(actual_scope, actual_receive, actual_send):
            self.assertIs(actual_scope, scope)
            self.assertIs(actual_receive, receive)
            self.assertIs(actual_send, send)
            return returned
        wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
        self.assertIs(run_immediate(wrapper(scope, receive, send)), returned)
        self.assertFalse(wrapper.capture_complete)
        self.assertTrue(wrapper.finish())
        self.assertFalse(owner.publish())
        self.assertTrue(owner.publish(allow_incomplete=True))

    def test_lifespan_is_forwarded_identically_and_active_source_cannot_finish(self):
        owner = self.owner()
        scope, result = {"type": "lifespan"}, object()
        async def receive():
            return {"type": "lifespan.startup"}
        async def send(event):
            return None
        async def app(actual_scope, actual_receive, actual_send):
            self.assertIs(actual_scope, scope)
            self.assertIs(actual_receive, receive)
            self.assertIs(actual_send, send)
            self.assertFalse(wrapper.finish())
            return result
        wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
        self.assertIs(run_immediate(wrapper(scope, receive, send)), result)
        self.assertEqual(self.rows(owner), [])
        self.assertTrue(wrapper.finish())
        self.assertTrue(owner.publish())

    def test_interleaved_http_exchanges_keep_source_order_and_bound_io_ids_without_loop(self):
        owner = self.owner()
        scopes = [{"type": "http", "path": "/first"}, {"type": "http", "path": "/second"}]
        results = [object(), object()]
        class Pause:
            def __await__(self):
                yield "constructed pause"
        async def receive():
            return {"type": "http.request", "body": b"request"}
        async def send(event):
            return None
        async def app(scope, recv, emit):
            await recv()
            await Pause()
            await emit({"type": "http.response.start", "status": 200})
            await emit({"type": "http.response.body", "body": b"done"})
            return results[0] if scope is scopes[0] else results[1]
        wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
        coroutines = [wrapper(scope, receive, send) for scope in scopes]
        try:
            for coroutine in coroutines:
                self.assertEqual(coroutine.send(None), "constructed pause")
            self.assertEqual(wrapper.active_operations, 2)
            self.assertFalse(wrapper.finish())
            for index in (1, 0):
                with self.assertRaises(StopIteration) as completed:
                    coroutines[index].send(None)
                self.assertIs(completed.exception.value, results[index])
        finally:
            for coroutine in coroutines:
                coroutine.close()
        terminal_exchanges = [row["exchange"] for row in self.payloads(owner) if row["boundary"] == "application_returned"]
        self.assertEqual(terminal_exchanges, [1, 0])
        self.assertTrue(wrapper.finish())
        self.assertTrue(owner.publish())

    def test_retained_raw_io_after_app_return_prevents_even_partial_seal_until_settled(self):
        class Pause:
            def __await__(self):
                yield "constructed pending IO"
        class Cancellation(BaseException):
            pass
        for direction in ("receive", "send"):
            for completion in ("return", "cancel"):
                owner = self.owner()
                retained, app_return, io_return = [], object(), object()
                request = {"type": "http.request", "body": b"request"}
                async def receive():
                    await Pause()
                    return request
                async def send(event):
                    if direction == "send" and event["type"] == "http.response.body":
                        await Pause()
                    return io_return
                async def app(scope, recv, emit):
                    if direction == "receive":
                        pending = recv()
                        self.assertEqual(pending.send(None), "constructed pending IO")
                        retained.append(pending)
                    await emit({"type": "http.response.start", "status": 200})
                    body = {"type": "http.response.body", "body": b"done"}
                    if direction == "send":
                        pending = emit(body)
                        self.assertEqual(pending.send(None), "constructed pending IO")
                        retained.append(pending)
                    else:
                        await emit(body)
                    return app_return
                wrapper = durable.RawAsgiCapture(app, owner.sink("http"))
                try:
                    self.assertIs(run_immediate(wrapper({"type": "http"}, receive, send)), app_return)
                    self.assertEqual(wrapper.active_operations, 0)
                    self.assertEqual(wrapper.active_io_operations, 1)
                    self.assertEqual(wrapper.witness()["active_operations"], 1)
                    self.assertFalse(wrapper.finish())
                    self.assertFalse(owner.publish(allow_incomplete=True))
                    self.assertFalse((owner.path / "terminal.json").exists())
                    if completion == "return":
                        with self.assertRaises(StopIteration) as finished:
                            retained[0].send(None)
                        self.assertIs(finished.exception.value, request if direction == "receive" else io_return)
                    else:
                        failure = Cancellation("constructed cancellation")
                        with self.assertRaises(Cancellation) as caught:
                            retained[0].throw(failure)
                        self.assertIs(caught.exception, failure)
                    self.assertEqual(wrapper.active_io_operations, 0)
                    self.assertEqual(wrapper.witness()["active_operations"], 0)
                    self.assertTrue(wrapper.finish())
                    self.assertTrue(owner.publish(allow_incomplete=True))
                    self.assertFalse(owner.published_complete)
                finally:
                    for coroutine in retained:
                        coroutine.close()

    def test_interleaved_public_calls_and_named_streams_share_global_durable_order(self):
        owner = self.owner({"merchant": "public", "credentials": "public"})
        records = [("merchant", self.public(0, 0, "attempt", {"first": True})),
                   ("credentials", self.public(0, 0, "attempt", {"other": True})),
                   ("merchant", self.public(1, 1, "attempt", {"second": True})),
                   ("merchant", self.public(2, 1, "returned", {"second": "done"})),
                   ("credentials", self.public(1, 0, "returned", {"other": "done"})),
                   ("merchant", self.public(3, 0, "error"))]
        for name, row in records:
            owner.sink(name)(row)
        self.assertEqual([row["global_index"] for row in self.rows(owner)], list(range(6)))
        self.assertEqual([row["stream"] for row in self.rows(owner)], [name for name, _ in records])
        self.assertTrue(owner.finish_stream("merchant", self.witness(4)))
        self.assertTrue(owner.finish_stream("credentials", self.witness(2)))
        self.assertTrue(owner.publish())

    def test_gap_and_unmatched_intervals_refuse_complete_publication(self):
        owner = self.owner({"client": "public"})
        self.assertTrue(owner.append("client", self.public(0, 0, "attempt", {"request": True})))
        self.assertFalse(owner.append("client", self.public(2, 0, "returned", {"result": True})))
        self.assertTrue(owner.finish_stream("client", self.witness(3, complete=False)))
        self.assertFalse(owner.publish())
        self.assertFalse((owner.path / "terminal.pending.json").exists())
        self.assertTrue(owner.publish(allow_incomplete=True))
        manifest = json.loads((owner.path / "terminal.json").read_bytes())
        self.assertFalse(manifest["capture_complete_for_declared_intervals"])
        active = durable.decode_value(manifest["streams"]["client"]["active_intervals"])
        self.assertIs(type(next(iter(active))), int)
        self.assertIs(type(active[0]), tuple)

    def test_source_witness_is_required_even_when_no_sink_record_was_seen(self):
        owner = self.owner({"client": "public"})
        self.assertFalse(owner.publish())
        self.assertFalse(owner.finish_stream("client", self.witness(0, active=1)))
        self.assertFalse(owner.finish_stream("client", {"source_complete": 1, "active_operations": 0, "attempted_records": 0}))
        self.assertTrue(owner.finish_stream("client", self.witness(0, complete=False)))
        self.assertFalse(owner.publish())
        self.assertTrue(owner.publish(allow_incomplete=True))
        self.assertFalse(owner.published_complete)

    def test_frozen_public_sink_failure_marks_wrapper_incomplete_without_changing_return(self):
        owner = self.owner({"client": "public"}, durable.Limits(events=1))
        returned = {"constructed": True}
        class Client:
            async def send_a2a_message(self, request):
                return returned
        observer = frozen_public.PublicClientObserver(Client(), frozen_public.MERCHANT, sink=owner.sink("client"))
        self.assertIs(run_immediate(observer.send_a2a_message({"request": True})), returned)
        self.assertFalse(observer.capture_complete)
        self.assertFalse(owner.capture_complete)
        self.assertEqual(owner.committed_events, 1)
        self.assertTrue(owner.finish_stream("client", self.witness(len(observer.records), complete=observer.capture_complete)))
        self.assertTrue(owner.publish(allow_incomplete=True))

    def test_frozen_asgi_compatibility_preserves_earlier_encoding_without_upgrading_it(self):
        owner = self.owner({"legacy": "frozen_asgi"})
        body = {"type": "http.response.body", "body": b"raw"}
        delivered = []
        async def receive():
            return {"type": "http.request", "body": b"request"}
        async def send(event):
            delivered.append(event)
        async def app(scope, recv, emit):
            await recv()
            await emit({"type": "http.response.start", "status": 200})
            await emit(body)
        wrapper = frozen_asgi.PassiveAsgiCapture(app, owner.sink("legacy"))
        run_immediate(wrapper({"type": "http"}, receive, send))
        self.assertIs(delivered[-1], body)
        record = next(row for row in self.payloads(owner) if row["boundary"] == "send_attempt" and row["value"]["type"] == "http.response.body")
        self.assertIs(type(record["value"]["body"]), dict)
        self.assertEqual(record["value"]["body"]["encoding"], "base64")
        self.assertTrue(owner.finish_stream("legacy", self.witness(len(wrapper.records), complete=wrapper.capture_complete)))
        self.assertTrue(owner.publish())

    def test_reentrant_append_is_refused_without_deadlock_or_interleaved_bytes(self):
        owner = self.owner({"client": "public"})
        original_write, nested = durable.os.write, []
        def reenter(fd, raw):
            if not nested:
                nested.append(owner.append("client", self.public(0, 0, "attempt", {"nested": True})))
            return original_write(fd, raw)
        with patch.object(durable.os, "write", side_effect=reenter):
            self.assertTrue(owner.append("client", self.public(0, 0, "attempt", {"outer": True})))
        self.assertEqual(nested, [False])
        self.assertEqual(len(self.rows(owner)), 1)
        self.assertFalse(owner.capture_complete)
        self.assertEqual(owner.missing_indices, [1])

    def test_retained_journal_interference_is_detected_before_complete_publication(self):
        owner = self.owner({"client": "public"})
        owner.sink("client")(self.public(0, 0, "attempt", {"request": True}))
        owner.sink("client")(self.public(1, 0, "returned", {"result": True}))
        self.assertTrue(owner.finish_stream("client", self.witness(2)))
        with (owner.path / "events.jsonl").open("ab") as stream:
            stream.write(b"unacknowledged bytes\n")
        self.assertFalse(owner.publish())
        self.assertFalse(owner.capture_complete)
        self.assertFalse((owner.path / "terminal.json").exists())

    def test_publication_never_overwrites_existing_terminal_and_close_failure_keeps_authority(self):
        owner = self.owner({"client": "public"})
        self.assertTrue(owner.finish_stream("client", self.witness(0)))
        sentinel = owner.path / "terminal.json"
        sentinel.write_bytes(b"unrelated terminal")
        self.assertFalse(owner.publish())
        self.assertEqual(sentinel.read_bytes(), b"unrelated terminal")
        self.assertTrue((owner.path / "terminal.pending.json").exists())
        another = self.owner({"client": "public"})
        with patch.object(durable.os, "close", side_effect=OSError("constructed close failure")):
            self.assertFalse(another.close())
        self.assertTrue(another.report()["open_file_authority_retained"])
        self.assertTrue(another.close())

    def test_post_seal_calls_mark_current_observation_incomplete_without_rewriting_terminal(self):
        owner = self.owner({"client": "public"})
        self.assertTrue(owner.finish_stream("client", self.witness(0)))
        self.assertTrue(owner.publish())
        terminal = (owner.path / "terminal.json").read_bytes()
        self.assertFalse(owner.append("client", self.public(0, 0, "attempt", {"late": True})))
        self.assertFalse(owner.capture_complete)
        self.assertEqual(owner.post_seal_attempts, 1)
        self.assertEqual((owner.path / "terminal.json").read_bytes(), terminal)
        self.assertTrue(json.loads(terminal)["capture_complete_for_declared_intervals"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
