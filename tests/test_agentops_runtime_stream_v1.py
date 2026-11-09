"""Mocked async-generator journal checks: no SDK, application or model launch."""
import asyncio
from contextvars import ContextVar
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("agentops_runtime_stream_v1", ROOT / "scripts/agentops_runtime_stream_v1.py")
journal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journal_module)
RunAsyncJournal = journal_module.RunAsyncJournal


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


class FakeSdkObject:
    def __init__(self, value):
        self.value = deepcopy(value)
    def model_dump(self, *, mode):
        if mode != "json":
            raise AssertionError("explicit SDK JSON mode required")
        return deepcopy(self.value)


def serializer(value):
    return encoded(value.model_dump(mode="json"))


def event(number=1, *, invocation="actual-native-invocation", parts=None):
    return FakeSdkObject({"id": "actual-event-" + str(number), "invocation_id": invocation,
                          "timestamp": 123.5 + number, "author": "original_agent", "partial": False,
                          "content": {"role": "model", "parts": parts or [{"text": "Original Unicode café."}]},
                          "actions": {"state_delta": {"original": True}}, "custom_metadata": {"kept": [1, None]}})


class Source:
    def __init__(self, events):
        self.events, self.calls, self.closed = events, [], 0
    async def run_async(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        try:
            for original in self.events:
                yield original
        finally:
            await asyncio.sleep(0)
            self.closed += 1


class RuntimeStreamTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def recorder(self, source, **options):
        return RunAsyncJournal(source.run_async, self.directory / "capture", event_serializer=serializer,
                               content_serializer=serializer, config_serializer=serializer, **options)
    def read(self, name):
        return json.loads((self.directory / "capture" / name).read_bytes())
    async def consume(self, source, **options):
        recorder = self.recorder(source, **options)
        received = [item async for item in recorder.run_async(user_id="actual-user", session_id="actual-session")]
        return recorder, received, recorder.finish()

    async def test_same_objects_exact_input_omissions_and_preconverter_full_batch_bytes(self):
        parts = [{"function_call": {"id": "call-a", "name": "unchanged_tool", "args": {"query": "original"}}},
                 {"function_response": {"id": "call-b", "name": "earlier_tool", "response": {"value": 42}}}]
        original = event(parts=parts)
        source = Source([original])
        new_message = FakeSdkObject({"role": "user", "parts": [{"text": "Exact original question."}]})
        config = FakeSdkObject({"max_llm_calls": 12, "streaming_mode": "NONE"})
        state = {"nested": [1, False, None]}
        objects_before = [deepcopy(item.value) for item in (original, new_message, config)]
        recorder = self.recorder(source)
        supplied = {"user_id": "actual-user", "session_id": "actual-session", "invocation_id": None,
                    "new_message": new_message, "state_delta": state, "run_config": config, "yield_user_message": False}
        stream = recorder.run_async(**supplied)
        received = await anext(stream)
        self.assertIs(received, original)
        raw = self.directory / "capture/invocations/000001/events/000001.json"
        self.assertEqual(raw.read_bytes(), serializer(original))  # already exists before downstream resume
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertEqual(source.closed, 1)
        self.assertEqual(len(source.calls), 1)
        for key, value in supplied.items():
            self.assertIs(source.calls[0][1][key], value)
        self.assertEqual([item.value for item in (original, new_message, config)], objects_before)
        self.assertEqual(state, {"nested": [1, False, None]})
        inputs = self.read("invocations/000001/input.json")
        self.assertEqual(inputs["omitted_known_fields"], [])
        self.assertIsNone(inputs["invocation_id"])
        self.assertFalse(inputs["objects_or_argument_values_rewritten"])
        self.assertEqual((self.directory / "capture/invocations/000001/input/new_message.json").read_bytes(), serializer(new_message))
        self.assertEqual((self.directory / "capture/invocations/000001/input/run_config.json").read_bytes(), serializer(config))
        receipt = recorder.receipts[0]
        self.assertEqual(receipt["observed_invocation_ids"], ["actual-native-invocation"])
        self.assertEqual(receipt["events"][0]["part_count_in_original_yield"], 2)
        self.assertEqual(receipt["events"][0]["actual_event_id"], "actual-event-1")
        self.assertTrue(receipt["events"][0]["captured_before_downstream_yield"])
        root = recorder.finish()
        self.assertTrue(root["capture_complete"])
        self.assertTrue(root["eligible_for_ordered_evidence_checks"])
        self.assertFalse(root["benchmark_grade_proven"])
        self.assertFalse(root["causal_tool_execution_order_proven"])

    async def test_omitted_keywords_remain_omitted_and_ids_are_not_synthesized(self):
        source = Source([event()])
        recorder, received, result = await self.consume(source)
        self.assertEqual(set(source.calls[0][1]), {"user_id", "session_id"})
        inputs = self.read("invocations/000001/input.json")
        self.assertNotIn("invocation_id", inputs)
        self.assertIn("invocation_id", inputs["omitted_known_fields"])
        self.assertEqual(result["invocations"][0]["observed_invocation_ids"], ["actual-native-invocation"])
        self.assertEqual(recorder.receipts[0]["original_call_attempts"], 1)

    async def test_consumer_aclose_awaits_original_cleanup_and_is_not_normal_completion(self):
        source = Source([event(1), event(2)])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        await anext(stream)
        await stream.aclose()
        self.assertEqual(source.closed, 1)
        receipt = self.read("invocations/000001/result.json")
        self.assertEqual(receipt["original_termination"], "consumer_aclose")
        self.assertTrue(receipt["original_aclose_completed"])
        self.assertFalse(receipt["capture_complete"])
        self.assertFalse(recorder.finish()["eligible_for_ordered_evidence_checks"])

    async def test_consumer_athrow_preserves_same_exception_and_closes_original(self):
        source = Source([event(1), event(2)])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        await anext(stream)
        error = LookupError("must never be logged as exception text")
        with self.assertRaises(LookupError) as caught:
            await stream.athrow(error)
        self.assertIs(caught.exception, error)
        self.assertEqual(source.closed, 1)
        receipt = self.read("invocations/000001/result.json")
        self.assertEqual(receipt["original_termination"], "consumer_athrow")
        self.assertNotIn(str(error), json.dumps(receipt))

    async def test_original_generator_can_recover_consumer_athrow_without_call_retry(self):
        error = LookupError("original recovery signal")
        class Recovering(Source):
            async def run_async(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                try:
                    try:
                        yield self.events[0]
                    except LookupError as caught:
                        self.caught = caught
                        yield self.events[1]
                    yield self.events[2]
                finally:
                    self.closed += 1
        source = Recovering([event(1), event(2), event(3)])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        self.assertIs(await anext(stream), source.events[0])
        self.assertIs(await stream.athrow(error), source.events[1])
        self.assertIs(source.caught, error)
        self.assertIs(await anext(stream), source.events[2])
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertEqual(len(source.calls), 1)
        self.assertEqual(recorder.receipts[0]["consumer_protocol_throws"], 1)
        self.assertTrue(recorder.finish()["capture_complete"])

    async def test_original_generator_receives_identical_non_none_asend_value(self):
        signal = object()
        class Receiving(Source):
            async def run_async(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                try:
                    self.received = yield self.events[0]
                    yield self.events[1] if self.received is signal else self.events[2]
                finally:
                    self.closed += 1
        source = Receiving([event(1), event(2), event(3)])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        self.assertIs(await anext(stream), source.events[0])
        self.assertIs(await stream.asend(signal), source.events[1])
        self.assertIs(source.received, signal)
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertEqual(len(source.calls), 1)
        self.assertEqual(recorder.receipts[0]["consumer_non_none_sends"], 1)
        self.assertTrue(recorder.finish()["capture_complete"])

    async def test_explicit_generator_exit_and_cancelled_throws_can_be_recovered_originally(self):
        for index, signal in enumerate((GeneratorExit(), asyncio.CancelledError())):
            with self.subTest(signal=type(signal).__name__):
                class Recovering(Source):
                    async def run_async(self, *args, **kwargs):
                        self.calls.append((args, kwargs))
                        try:
                            try:
                                yield self.events[0]
                            except (GeneratorExit, asyncio.CancelledError) as caught:
                                self.caught = caught
                                yield self.events[1]
                        finally:
                            self.closed += 1
                source = Recovering([event(1), event(2)])
                recorder = RunAsyncJournal(source.run_async, self.directory / str(index), event_serializer=serializer)
                stream = recorder.run_async(user_id="u", session_id="s")
                self.assertIs(await anext(stream), source.events[0])
                self.assertIs(await stream.athrow(signal), source.events[1])
                self.assertIs(source.caught, signal)
                with self.assertRaises(StopAsyncIteration):
                    await anext(stream)
                self.assertTrue(recorder.finish()["capture_complete"])

    async def test_original_exception_is_preserved_without_retry(self):
        error = RuntimeError("original secret-bearing exception message")
        class Failing(Source):
            async def run_async(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                try:
                    yield self.events[0]
                    raise error
                finally:
                    self.closed += 1
        source = Failing([event()])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        self.assertIs(await anext(stream), source.events[0])
        with self.assertRaises(RuntimeError) as caught:
            await anext(stream)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(source.calls), 1)
        self.assertEqual(source.closed, 1)
        receipt = self.read("invocations/000001/result.json")
        self.assertEqual(receipt["original_termination"], "original_exception")
        self.assertNotIn(str(error), json.dumps(receipt))
        self.assertFalse(recorder.finish()["capture_complete"])

    async def test_cancellation_during_original_next_keeps_cleanup_and_cancelled_outcome(self):
        started = asyncio.Event()
        class Waiting(Source):
            async def run_async(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                try:
                    started.set()
                    await asyncio.Event().wait()
                    yield self.events[0]
                finally:
                    await asyncio.sleep(0)
                    self.closed += 1
        source = Waiting([event()])
        recorder = self.recorder(source)
        task = asyncio.create_task(anext(recorder.run_async(user_id="u", session_id="s")))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(source.closed, 1)
        receipt = self.read("invocations/000001/result.json")
        self.assertEqual(receipt["original_termination"], "cancelled_during_original_next")
        self.assertTrue(receipt["original_aclose_completed"])
        self.assertFalse(recorder.finish()["capture_complete"])

    async def test_cleanup_remains_in_original_task_context(self):
        marker = ContextVar("native_context_marker", default="outside")
        class ContextSource(Source):
            async def run_async(self, *args, **kwargs):
                token = marker.set("inside")
                try:
                    yield self.events[0]
                finally:
                    await asyncio.sleep(0)
                    marker.reset(token)
                    self.closed += 1
        source = ContextSource([event()])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        await anext(stream)
        self.assertEqual(marker.get(), "inside")
        await stream.aclose()
        self.assertEqual(marker.get(), "outside")
        self.assertEqual(source.closed, 1)

    async def test_original_aclose_exception_is_not_suppressed(self):
        error = OSError("original cleanup secret")
        class Iterator:
            async def __anext__(self):
                raise StopAsyncIteration
            async def aclose(self):
                raise error
        class Original:
            def run_async(self, *args, **kwargs):
                return Iterator()
        recorder = self.recorder(Original())
        with self.assertRaises(OSError) as caught:
            await anext(recorder.run_async(user_id="u", session_id="s"))
        self.assertIs(caught.exception, error)
        receipt = self.read("invocations/000001/result.json")
        self.assertEqual(receipt["cleanup_error_type"], "OSError")
        self.assertFalse(receipt["original_aclose_completed"])
        self.assertFalse(recorder.finish()["eligible_for_ordered_evidence_checks"])

    async def test_serializer_failure_is_explicit_partial_but_preserves_all_business_events(self):
        source = Source([event(1), event(2), event(3)])
        recorder = self.recorder(source)
        def broken(_):
            raise ValueError("serializer exception must not leak values")
        recorder.event_serializer = broken
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        self.assertEqual(len(received), 3)
        self.assertTrue(all(left is right for left, right in zip(received, source.events)))
        self.assertEqual(len(source.calls), 1)
        self.assertEqual(source.closed, 1)
        receipt = recorder.receipts[0]
        self.assertTrue(receipt["capture_disabled"])
        self.assertEqual(receipt["events_recorded"], 0)
        self.assertEqual(receipt["events_seen"], 3)
        self.assertTrue(receipt["durable_receipt_written"])
        self.assertFalse(recorder.finish()["eligible_for_ordered_evidence_checks"])

    async def test_event_io_partial_write_is_retained_and_does_not_retry_source_call(self):
        source = Source([event(1), event(2)])
        recorder = self.recorder(source)
        write = recorder._write
        def fail_event(relative, raw, **options):
            if "/events/" in relative:
                path = recorder.output / relative
                path.parent.mkdir(parents=True)
                path.write_bytes(raw[:9])
                raise OSError("fixture disk error")
            return write(relative, raw, **options)
        with patch.object(recorder, "_write", side_effect=fail_event):
            received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        self.assertEqual(received, source.events)
        self.assertEqual(len(source.calls), 1)
        self.assertEqual((recorder.output / "invocations/000001/events/000001.json").read_bytes(), serializer(source.events[0])[:9])
        root = recorder.finish()
        self.assertFalse(root["captured_inputs_unchanged"])
        self.assertFalse(root["capture_complete"])

    async def test_fsync_failure_keeps_written_bytes_reserved_and_business_events_unchanged(self):
        source = Source([event(1), event(2)])
        recorder = self.recorder(source)
        sync = journal_module.os.fsync
        calls = []
        def failing_sync(fd):
            calls.append(fd)
            if len(calls) == 2:  # input succeeds; first event's durability fails
                raise OSError("fixture fsync failure")
            return sync(fd)
        with patch.object(journal_module.os, "fsync", side_effect=failing_sync):
            received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        self.assertEqual(received, source.events)
        self.assertEqual(len(source.calls), 1)
        path = recorder.output / "invocations/000001/events/000001.json"
        self.assertEqual(path.read_bytes(), serializer(source.events[0]))
        self.assertNotIn("invocations/000001/events/000001.json", recorder.files)
        self.assertGreaterEqual(recorder.total_bytes, sum(item.stat().st_size for item in recorder.output.rglob("*") if item.is_file()))
        self.assertFalse(recorder.finish()["capture_complete"])

    async def test_missing_durable_invocation_receipt_never_qualifies(self):
        source = Source([event()])
        recorder = self.recorder(source)
        write = recorder._write_receipt
        def fail_receipt(relative, raw, **options):
            if relative == "invocations/000001/result.json":
                raise OSError("receipt write unavailable")
            return write(relative, raw, **options)
        with patch.object(recorder, "_write_receipt", side_effect=fail_receipt):
            received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        self.assertEqual(received, source.events)
        self.assertFalse(recorder.receipts[0]["durable_receipt_written"])
        root = recorder.finish()
        self.assertTrue(root["durable_receipt_written"])
        self.assertFalse(root["eligible_for_ordered_evidence_checks"])

    async def test_missing_root_receipt_is_explicit_in_memory_and_never_qualifies(self):
        source = Source([event()])
        recorder = self.recorder(source)
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        write = recorder._write_receipt
        def fail_root(relative, raw, **options):
            if relative == "result.json":
                raise OSError("root receipt unavailable")
            return write(relative, raw, **options)
        with patch.object(recorder, "_write_receipt", side_effect=fail_root):
            root = recorder.finish()
        self.assertFalse(root["durable_receipt_written"])
        self.assertFalse(root["eligible_for_ordered_evidence_checks"])
        self.assertFalse((recorder.output / "result.json").exists())
        self.assertIs(recorder.finish(), root)  # no hidden write retry

    async def test_root_fsync_failure_never_exposes_complete_json_at_final_name(self):
        source = Source([event()])
        recorder = self.recorder(source)
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        with patch.object(journal_module.os, "fsync", side_effect=OSError("root fsync unavailable")):
            root = recorder.finish()
        self.assertFalse(root["capture_complete"])
        self.assertFalse(root["durable_receipt_written"])
        self.assertEqual((recorder.output / "result.json").read_bytes(), b"")
        self.assertTrue((recorder.output / "result.json.pending").is_file())
        with self.assertRaises(json.JSONDecodeError):
            json.loads((recorder.output / "result.json").read_bytes())

    async def test_invocation_fsync_failure_retains_nonqualifying_final_and_pending(self):
        source = Source([event()])
        recorder = self.recorder(source)
        sync = journal_module.os.fsync
        calls = []
        def fail_terminal(fd):
            calls.append(fd)
            if len(calls) == 3:  # input, event, terminal pending
                raise OSError("invocation fsync unavailable")
            return sync(fd)
        with patch.object(journal_module.os, "fsync", side_effect=fail_terminal):
            received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        self.assertEqual(received, source.events)
        self.assertEqual((recorder.output / "invocations/000001/result.json").read_bytes(), b"")
        self.assertTrue((recorder.output / "invocations/000001/result.json.pending").is_file())
        self.assertFalse(recorder.receipts[0]["durable_receipt_written"])
        self.assertFalse(recorder.finish()["eligible_for_ordered_evidence_checks"])

    async def test_changed_terminal_placeholder_is_never_overwritten(self):
        source = Source([event()])
        recorder = self.recorder(source)
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        sync = journal_module.os.fsync
        changed = b'{"caller_owned":"preserve"}'
        def mutate_placeholder(fd):
            (recorder.output / "result.json").write_bytes(changed)
            return sync(fd)
        with patch.object(journal_module.os, "fsync", side_effect=mutate_placeholder):
            root = recorder.finish()
        self.assertFalse(root["durable_receipt_written"])
        self.assertEqual((recorder.output / "result.json").read_bytes(), changed)
        self.assertTrue((recorder.output / "result.json.pending").is_file())

    async def test_replaced_empty_terminal_placeholder_identity_is_never_overwritten(self):
        source = Source([event()])
        recorder = self.recorder(source)
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        sync = journal_module.os.fsync
        changed_identity = []
        def replace_placeholder(fd):
            replacement = recorder.output / "caller-empty.json"
            replacement.write_bytes(b"")
            changed_identity.append(replacement.stat().st_ino)
            journal_module.os.replace(replacement, recorder.output / "result.json")
            return sync(fd)
        with patch.object(journal_module.os, "fsync", side_effect=replace_placeholder):
            root = recorder.finish()
        self.assertFalse(root["durable_receipt_written"])
        self.assertEqual((recorder.output / "result.json").read_bytes(), b"")
        self.assertEqual((recorder.output / "result.json").stat().st_ino, changed_identity[0])
        self.assertTrue((recorder.output / "result.json.pending").is_file())

    async def test_unknown_values_are_not_dumped_and_original_args_are_identical(self):
        class SecretObject:
            def __repr__(self):
                raise AssertionError("unsupported value must never be inspected")
        secret = SecretObject()
        source = Source([event()])
        recorder = self.recorder(source)
        received = [item async for item in recorder.run_async(secret, user_id="u", session_id="s", unknown=secret)]
        self.assertEqual(received, source.events)
        self.assertIs(source.calls[0][0][0], secret)
        self.assertIs(source.calls[0][1]["unknown"], secret)
        inputs = self.read("invocations/000001/input.json")
        self.assertEqual(inputs["positional_argument_count"], 1)
        self.assertEqual(inputs["unsupported_keyword_field_count"], 1)
        self.assertTrue(inputs["unsupported_capture"])
        self.assertNotIn("unknown", inputs)
        self.assertFalse(recorder.finish()["capture_complete"])

    async def test_missing_sdk_input_serializer_disables_capture_not_business(self):
        source = Source([event()])
        recorder = RunAsyncJournal(source.run_async, self.directory / "capture", event_serializer=serializer)
        message = FakeSdkObject({"role": "user", "parts": [{"text": "original"}]})
        received = [item async for item in recorder.run_async(user_id="u", session_id="s", new_message=message)]
        self.assertIs(source.calls[0][1]["new_message"], message)
        self.assertEqual(received, source.events)
        self.assertFalse(recorder.finish()["capture_complete"])

    async def test_event_count_bound_retains_prefix_and_preserves_remaining_events(self):
        source = Source([event(1), event(2), event(3)])
        recorder, received, root = await self.consume(source, limits={"max_events_per_invocation": 1})
        self.assertEqual(received, source.events)
        self.assertEqual(recorder.receipts[0]["events_recorded"], 1)
        self.assertEqual(recorder.receipts[0]["events_seen"], 3)
        self.assertFalse(root["capture_complete"])

    async def test_invocation_bound_preserves_new_calls_but_cannot_qualify(self):
        source = Source([event()])
        recorder = self.recorder(source, limits={"max_invocations": 1})
        for index in range(2):
            received = [item async for item in recorder.run_async(user_id="u", session_id=str(index))]
            self.assertEqual(received, source.events)
        root = recorder.finish()
        self.assertEqual(len(source.calls), 2)
        self.assertEqual(root["unallocated_calls"], 1)
        self.assertEqual(len(recorder.receipts), 1)
        self.assertFalse(root["capture_complete"])

    async def test_file_count_bound_does_not_change_original_events_or_exceed_hard_count(self):
        source = Source([event(1), event(2)])
        recorder, received, root = await self.consume(source, limits={"max_files": 3})
        self.assertEqual(received, source.events)
        self.assertEqual(len(source.calls), 1)
        self.assertLessEqual(len([path for path in recorder.output.rglob("*") if path.is_file()]), 3)
        self.assertFalse(root["capture_complete"])
        self.assertFalse(root["durable_receipt_written"])

    async def test_aggregate_byte_bound_retains_prefix_without_changing_business_sequence(self):
        source = Source([event(index, parts=[{"text": "x" * 50000}]) for index in range(4)])
        limit = 4 * 65536
        recorder, received, root = await self.consume(source, limits={"max_json_bytes": 65536, "max_total_bytes": limit})
        self.assertTrue(all(a is b for a, b in zip(received, source.events)))
        self.assertEqual(len(received), 4)
        self.assertGreater(recorder.receipts[0]["events_recorded"], 0)
        self.assertLess(recorder.receipts[0]["events_recorded"], 4)
        self.assertLessEqual(sum(path.stat().st_size for path in recorder.output.rglob("*") if path.is_file()), limit)
        self.assertFalse(root["eligible_for_ordered_evidence_checks"])

    async def test_actual_missing_identity_fields_cannot_qualify_ordered_evidence(self):
        original = FakeSdkObject({"content": {"parts": [{"text": "Unbound original event"}]}})
        source = Source([original])
        recorder, received, root = await self.consume(source)
        self.assertTrue(root["capture_complete"])
        self.assertFalse(root["eligible_for_ordered_evidence_checks"])
        self.assertIsNone(recorder.receipts[0]["events"][0]["actual_event_id"])
        self.assertFalse(root["source_authentication_proven"])

    async def test_supplied_invocation_id_must_agree_with_all_actual_captured_ids(self):
        for index, supplied in enumerate(("actual-native-invocation", "different-native-invocation")):
            with self.subTest(supplied=supplied):
                source = Source([event()])
                recorder = RunAsyncJournal(source.run_async, self.directory / str(index), event_serializer=serializer)
                received = [item async for item in recorder.run_async(user_id="u", session_id="s", invocation_id=supplied)]
                self.assertIs(source.calls[0][1]["invocation_id"], supplied)
                expected = index == 0
                self.assertEqual(recorder.receipts[0]["supplied_invocation_id_matches_all_observed"], expected)
                self.assertEqual(recorder.finish()["eligible_for_ordered_evidence_checks"], expected)

    async def test_mixed_original_invocation_ids_are_preserved_without_unique_id_assumption(self):
        source = Source([event(1, invocation="parent"), event(2, invocation="child")])
        recorder, received, root = await self.consume(source)
        self.assertEqual(recorder.receipts[0]["observed_invocation_ids"], ["parent", "child"])
        self.assertIsNone(recorder.receipts[0]["supplied_invocation_id_matches_all_observed"])
        self.assertTrue(root["capture_complete"])
        self.assertTrue(root["eligible_for_ordered_evidence_checks"])
        self.assertFalse(root["benchmark_grade_proven"])

    async def test_invalid_or_partial_serializer_json_is_not_hidden_as_complete(self):
        samples = [b'{"id":"a","id":"b"}', b'{"value":NaN}', b'{"value":1e999}', b'{"truncated":', b'[]']
        for index, raw in enumerate(samples):
            with self.subTest(index=index):
                source = Source([event()])
                recorder = RunAsyncJournal(source.run_async, self.directory / str(index), event_serializer=lambda _, raw=raw: raw)
                received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
                self.assertEqual(received, source.events)
                self.assertFalse(recorder.finish()["capture_complete"])

    async def test_concurrent_invocations_have_exclusive_parent_and_global_yield_order(self):
        source = Source([event(1), event(2)])
        recorder = self.recorder(source)
        left = recorder.run_async(user_id="u", session_id="left")
        right = recorder.run_async(user_id="u", session_id="right")
        for stream in (left, right, left, right):
            await anext(stream)
        for stream in (left, right):
            with self.assertRaises(StopAsyncIteration):
                await anext(stream)
        self.assertEqual([row["invocation_sequence"] for row in recorder.receipts], [1, 2])
        self.assertEqual([[item["global_yield_sequence"] for item in row["events"]] for row in recorder.receipts], [[1, 3], [2, 4]])
        self.assertEqual([[item["event_ordinal"] for item in row["events"]] for row in recorder.receipts], [[1, 2], [1, 2]])
        self.assertTrue(recorder.finish()["capture_complete"])

    async def test_reused_original_object_is_snapshotted_before_each_later_mutation(self):
        original = event()
        first = serializer(original)
        class MutatingSource(Source):
            async def run_async(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                try:
                    yield self.events[0]
                    self.events[0].value["content"]["parts"] = [{"text": "Changed by original between yields"}]
                    yield self.events[0]
                finally:
                    self.closed += 1
        source = MutatingSource([original])
        recorder = self.recorder(source)
        stream = recorder.run_async(user_id="u", session_id="s")
        self.assertIs(await anext(stream), original)
        self.assertEqual((recorder.output / "invocations/000001/events/000001.json").read_bytes(), first)
        self.assertIs(await anext(stream), original)
        second = serializer(original)
        self.assertNotEqual(first, second)
        self.assertEqual((recorder.output / "invocations/000001/events/000002.json").read_bytes(), second)
        self.assertEqual((recorder.output / "invocations/000001/events/000001.json").read_bytes(), first)
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertTrue(recorder.finish()["capture_complete"])

    async def test_changed_capture_bytes_never_qualify_and_are_preserved(self):
        source = Source([event()])
        recorder = self.recorder(source)
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        path = recorder.output / "invocations/000001/events/000001.json"
        changed = path.read_bytes() + b"\n"
        path.write_bytes(changed)
        root = recorder.finish()
        self.assertFalse(root["captured_inputs_unchanged"])
        self.assertFalse(root["capture_complete"])
        self.assertEqual(path.read_bytes(), changed)

    async def test_call_after_finalization_invalidates_eligibility_and_preserves_original_call(self):
        source = Source([event()])
        recorder, _, root = await self.consume(source)
        self.assertTrue(root["eligible_for_ordered_evidence_checks"])
        received = [item async for item in recorder.run_async(user_id="u", session_id="after-finish")]
        self.assertEqual(received, source.events)
        self.assertFalse(root["eligible_for_ordered_evidence_checks"])
        self.assertTrue((recorder.output / "after-finalization-error.json").is_file())
        self.assertEqual(len(source.calls), 2)

    async def test_output_is_exclusive_and_no_source_or_global_patch_is_installed(self):
        source = Source([event()])
        method = source.run_async
        recorder = self.recorder(source)
        self.assertEqual(source.run_async, method)
        original = (recorder.output / "plan.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.recorder(source)
        self.assertEqual((recorder.output / "plan.json").read_bytes(), original)
        self.assertEqual(source.calls, [])
        self.assertFalse(recorder.finish()["capture_complete"])

    async def test_conflicting_call_directory_is_preserved_without_any_writes_inside_it(self):
        source = Source([event()])
        recorder = self.recorder(source)
        conflict = recorder.output / "invocations/000001"
        conflict.mkdir(parents=True)
        sentinel = conflict / "untouched.json"
        sentinel.write_bytes(b'{"preexisting":true}')
        before = sentinel.read_bytes()
        received = [item async for item in recorder.run_async(user_id="u", session_id="s")]
        self.assertEqual(received, source.events)
        self.assertEqual(len(source.calls), 1)
        self.assertEqual(list(conflict.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), before)
        self.assertFalse(recorder.receipts[0]["directory_created_exclusively"])
        self.assertFalse(recorder.receipts[0]["durable_receipt_written"])
        self.assertFalse(recorder.finish()["eligible_for_ordered_evidence_checks"])

    async def test_invalid_limits_and_linked_parent_fail_before_source_or_output_creation(self):
        source = Source([event()])
        with self.assertRaises(ValueError):
            self.recorder(source, limits={"max_invocations": True})
        self.assertFalse((self.directory / "capture").exists())
        with patch.object(journal_module, "_regular", side_effect=ValueError("linked ancestor")):
            with self.assertRaises(ValueError):
                self.recorder(source)
        self.assertFalse((self.directory / "capture").exists())
        self.assertEqual(source.calls, [])


if __name__ == "__main__":
    unittest.main()
