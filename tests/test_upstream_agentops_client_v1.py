"""Loopback transport regressions; no SDK, model or native application."""
from contextlib import contextmanager
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from uuid import uuid4
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.upstream_agentops_client_v1 import run_case, strict_json


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def fixture(turns=1, family="agentops_agent_core"):
    return {"eval_set_id": family, "eval_id": "temporary-case", "creation_timestamp": 1,
            "session_input": {"app_name": "source-app", "user_id": "eval", "state": {}},
            "conversation": [{"invocation_id": "source-label-" + str(index), "creation_timestamp": 1,
                              "user_content": {"role": "user", "parts": [{"text": "Original turn " + str(index)}, {"text": "Exact Unicode: café."}]}}
                             for index in range(turns)]}


def policy(case):
    context = str(uuid4())
    return {"schema_version": "upstream-agentops-session-policy/1", "context_id": context,
            "source_session_input": deepcopy(case["session_input"]), "native_app_name_expected": "agentops-agent",
            "native_user_id_expected_from_source": "A2A_USER_" + context, "native_session_id_expected_from_source": context,
            "mapping_basis": "Prospective source-derived synthetic unauthenticated A2A mapping"}


def task(request, state="TASK_STATE_COMPLETED", task_id=None, context=None):
    message = request.get("params", {}).get("message")
    return {"id": task_id or "task-" + request["id"], "contextId": context or message["contextId"],
            "status": {"state": state, "message": {"messageId": "reply", "role": "ROLE_AGENT", "parts": [{"text": "Observed mock response."}]}},
            "history": [], "artifacts": [], "metadata": {"untrusted_runtime_label": "retained"}}


def rpc(request, result=None, error=None):
    return {"jsonrpc": "2.0", "id": request["id"], **({"error": error} if error is not None else {"result": result})}


def http(body, *, status=200, content_type="application/json", length=None, chunked=False):
    header = f"HTTP/1.1 {status} Mock\r\nContent-Type: {content_type}\r\nConnection: close\r\n"
    if chunked:
        return (header + "Transfer-Encoding: chunked\r\n\r\n").encode("ascii") + hex(len(body))[2:].encode() + b"\r\n" + body + b"\r\n0\r\n\r\n"
    return (header + f"Content-Length: {len(body) if length is None else length}\r\n\r\n").encode("ascii") + body


@contextmanager
def server(reply=None, card_change=None):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *_):
            pass
        def do_GET(self):
            card = {"name": "Temporary transport fixture", "supportedInterfaces": [{"url": self.server.endpoint,
                    "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}]}
            if card_change is not None:
                card = card_change(card)
            raw = http(encoded(card))
            self.server.gets.append({"path": self.path, "headers": list(self.headers.items())})
            self.server.sent.append(raw)
            self.wfile.write(raw)
            self.close_connection = True
        def do_POST(self):
            raw_body = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(raw_body)
            self.server.posts.append({"request": request, "body": raw_body, "headers": list(self.headers.items())})
            if reply is None:
                answer = rpc(request, {"task": task(request)})
            else:
                answer = reply(request, self.server)
            raw = answer if type(answer) is bytes else http(encoded(answer))
            self.server.sent.append(raw)
            try:
                self.wfile.write(raw)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True
    instance = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    instance.daemon_threads = True
    instance.endpoint = f"http://127.0.0.1:{instance.server_port}/"
    instance.posts, instance.gets, instance.sent = [], [], []
    thread = threading.Thread(target=instance.serve_forever, kwargs={"poll_interval": 0.005}, daemon=True)
    thread.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(2)


@contextmanager
def wire_server(reply=None):
    """Retain every byte actually received, including empty rejected sockets."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(0.05)
    service = SimpleNamespace(endpoint=f"http://127.0.0.1:{listener.getsockname()[1]}/", accepted=[])
    stop = threading.Event()
    changed = threading.Condition()
    def wait_finished(count):
        with changed:
            return changed.wait_for(lambda: len(service.accepted) >= count and
                                    all(entry["finished"].is_set() for entry in service.accepted), timeout=2)
    service.wait_finished = wait_finished
    def receive():
        while not stop.is_set():
            try:
                connection, peer = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            entry = {"local": connection.getsockname(), "peer": peer, "bytes": b"", "finished": threading.Event()}
            with changed:
                service.accepted.append(entry)
                changed.notify_all()
            with connection:
                connection.settimeout(2)
                try:
                    while True:
                        block = connection.recv(65536)
                        if not block:
                            break
                        entry["bytes"] += block
                        head, delimiter, body = entry["bytes"].partition(b"\r\n\r\n")
                        if not delimiter:
                            continue
                        content_length = next(int(line.split(b":", 1)[1]) for line in head.split(b"\r\n")[1:]
                                              if line.lower().startswith(b"content-length:"))
                        if len(body) < content_length:
                            continue
                        if head.startswith(b"GET "):
                            answer = {"supportedInterfaces": [{"url": service.endpoint, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}]}
                        else:
                            request = json.loads(body)
                            answer = reply(request, service) if reply else rpc(request, {"task": task(request)})
                        connection.sendall(http(encoded(answer)))
                        break
                finally:
                    entry["finished"].set()
                    with changed:
                        changed.notify_all()
    thread = threading.Thread(target=receive, daemon=True)
    thread.start()
    try:
        yield service
    finally:
        stop.set()
        listener.close()
        thread.join(3)


class CaseClientTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.case = fixture()
        self.policy = policy(self.case)
    def tearDown(self):
        self.temporary.cleanup()
    def run_client(self, service, **changes):
        return run_case(self.case, service.endpoint, self.directory / "capture", session_policy=self.policy, **changes)
    def assert_partial(self, report, reason=None):
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["graded_upstream_cases"], 0)
        self.assertEqual(report["automatic_confirmations_sent"], 0)
        if reason:
            self.assertTrue(any(reason in value["message"] for value in report["errors"]), report["errors"])

    def test_exact_original_parts_and_http_bytes_are_retained(self):
        with server() as service:
            report = self.run_client(service)
            self.assertEqual(report["status"], "recorded")
            request = service.posts[0]["request"]
            self.assertEqual(request["params"]["message"]["parts"], self.case["conversation"][0]["user_content"]["parts"])
            self.assertNotIn("taskId", request["params"]["message"])
            self.assertNotIn("metadata", request["params"]["message"])
            self.assertEqual(dict(service.posts[0]["headers"])["A2A-Version"], "1.0")
            root = self.directory / "capture"
            self.assertEqual((root / "wire/000002/request.body.bin").read_bytes(), service.posts[0]["body"])
            self.assertEqual((root / "wire/000002/response.http.bin").read_bytes(), service.sent[1])
            raw_request = (root / "wire/000002/request.http.bin").read_bytes()
            self.assertEqual(raw_request.partition(b"\r\n\r\n")[2], service.posts[0]["body"])
            self.assertTrue(raw_request.startswith(b"POST / HTTP/1.1\r\n"))
            self.assertTrue(report["captured_files_unchanged"])
            self.assertTrue(report["input_objects_unchanged"])
            self.assertTrue(report["implementation_unchanged"])
            self.assertEqual(report["direct_model_calls"], 0)
            self.assertEqual(report["hidden_retries"], 0)
            self.assertFalse(report["connection_guard_configured"])
            for exchange in report["exchanges"]:
                self.assertFalse(exchange["connection_guard_configured"])
                self.assertFalse(exchange["connection_guard_invoked"])
                self.assertFalse(exchange["connection_guard_passed"])
            self.assertEqual(report["exchanges"][-1]["response_rpc_id"], request["id"])
            self.assertEqual(report["exchanges"][-1]["response_rpc_id_type"], "str")
            self.assertFalse(report["runtime_identity_observed"])
            observed = report["turns"][0]["observations"][0]
            self.assertEqual(observed["observed_task_metadata"], {"untrusted_runtime_label": "retained"})
            self.assertEqual(observed["history"], [])
            self.assertEqual(observed["artifacts"], [])
            names = {row["path"] for row in report["files"]}
            self.assertEqual(names | {"result.json"}, {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()})

    def test_connection_guard_rejection_precedes_every_get_send_and_poll_byte(self):
        for rejected_sequence in (1, 2, 3):
            with self.subTest(rejected_sequence=rejected_sequence), tempfile.TemporaryDirectory() as directory:
                def reply(request, service):
                    service.context = request["params"]["message"]["contextId"]
                    return rpc(request, {"task": task(request, "TASK_STATE_WORKING", "working-task")})
                seen = []
                def guard(connection):
                    seen.append((connection.getsockname(), connection.getpeername()))
                    if len(seen) == rejected_sequence:
                        raise RuntimeError("reject without request bytes")
                with wire_server(reply) as service:
                    report = run_case(self.case, service.endpoint, Path(directory) / "capture", session_policy=self.policy,
                                      connection_guard=guard, limits={"poll_interval_seconds": 0.001})
                    self.assert_partial(report, "connection_guard_rejected")
                    self.assertTrue(service.wait_finished(rejected_sequence))
                    self.assertEqual(len(seen), rejected_sequence)
                    self.assertEqual(report["http_requests"], rejected_sequence)
                    self.assertEqual(len(service.accepted), rejected_sequence)
                    for index, accepted in enumerate(service.accepted):
                        self.assertTrue(accepted["finished"].wait(1))
                        self.assertEqual(seen[index], (accepted["peer"], accepted["local"]))
                    self.assertEqual(service.accepted[-1]["bytes"], b"")
                    for prior in service.accepted[:-1]:
                        self.assertTrue(prior["bytes"].startswith((b"GET ", b"POST ")))
                    rejected = report["exchanges"][-1]
                    self.assertTrue(rejected["connection_guard_configured"])
                    self.assertTrue(rejected["connection_guard_invoked"])
                    self.assertFalse(rejected["connection_guard_passed"])
                    self.assertFalse(rejected["request_send_attempted"])
                    self.assertFalse(rejected["request_fully_sent"])
                    self.assertEqual(rejected["attempts"], 1)
                    self.assertEqual(rejected["connection_guard_error_type"], "RuntimeError")
                    self.assertEqual(rejected["connected_local_endpoint"], list(seen[-1][0]))
                    self.assertEqual(rejected["connected_peer_endpoint"], list(seen[-1][1]))
                    self.assertEqual(rejected["request_capture_representation"], "prepared_http_request_bytes")
                    self.assertEqual((Path(directory) / "capture/wire" / f"{rejected_sequence:06d}" / "response.http.bin").read_bytes(), b"")
                    self.assertFalse(report["qualification_established"])
                    self.assertFalse(report["runtime_identity_authenticated"])

    def test_successful_connection_guard_is_applied_to_get_send_and_get_task(self):
        def reply(request, service):
            if request["method"] == "SendMessage":
                service.context = request["params"]["message"]["contextId"]
                return rpc(request, {"task": task(request, "TASK_STATE_WORKING", "working-task")})
            return rpc(request, {"task": task(request, task_id="working-task", context=service.context)})
        seen = []
        def guard(connection):
            seen.append((connection.getsockname(), connection.getpeername()))
        with server(reply) as service:
            report = self.run_client(service, connection_guard=guard, limits={"poll_interval_seconds": 0.001})
            self.assertEqual(report["status"], "recorded", report["errors"])
            self.assertEqual(len(seen), 3)
            self.assertEqual([entry["rpc_method"] for entry in report["exchanges"]], [None, "SendMessage", "GetTask"])
            for exchange, endpoints in zip(report["exchanges"], seen):
                self.assertTrue(exchange["connection_guard_passed"])
                self.assertEqual(exchange["connected_local_endpoint"], list(endpoints[0]))
                self.assertEqual(exchange["connected_peer_endpoint"], list(endpoints[1]))
            self.assertFalse(report["qualification_established"])

    def test_invalid_connection_guard_stops_before_opening_socket(self):
        with server() as service:
            report = self.run_client(service, connection_guard=False)
            self.assert_partial(report, "connection_guard_not_callable")
            self.assertEqual(report["exchanges"], [])
            self.assertEqual(service.gets, [])
            self.assertEqual(service.posts, [])

    def test_completed_memory_next_turn_uses_new_task_same_context(self):
        self.case = fixture(2)
        self.policy = policy(self.case)
        with server() as service:
            report = self.run_client(service)
            self.assertEqual(report["turns_completed"], 2)
            self.assertEqual(len(service.posts), 2)
            first, second = [item["request"]["params"]["message"] for item in service.posts]
            self.assertNotIn("taskId", first)
            self.assertNotIn("taskId", second)
            self.assertEqual(first["contextId"], second["contextId"])
            self.assertNotEqual(report["turns"][0]["task_id"], report["turns"][1]["task_id"])

    def test_completed_task_cannot_be_reused_by_second_turn(self):
        self.case = fixture(2)
        self.policy = policy(self.case)
        with server(lambda request, _: rpc(request, {"task": task(request, task_id="same-completed-task")})) as service:
            self.assert_partial(self.run_client(service), "completed_task_reused")
            self.assertEqual(len(service.posts), 2)

    def test_input_required_never_sends_confirmation_or_later_source_turn(self):
        self.case = fixture(2)
        self.policy = policy(self.case)
        def reply(request, _):
            value = task(request, "TASK_STATE_INPUT_REQUIRED")
            value["status"]["message"]["parts"] = [{"data": {"id": "confirm", "name": "adk_request_confirmation", "args": {}}, "metadata": {"adk_type": "function_call"}}]
            return rpc(request, {"task": value})
        with server(reply) as service:
            report = self.run_client(service)
            self.assertEqual(report["status"], "recorded")
            self.assertTrue(report["stopped_for_input_required"])
            self.assertEqual(report["turns_attempted"], 1)
            self.assertEqual(len(service.posts), 1)
            self.assertEqual(report["automatic_confirmations_sent"], 0)
            self.assertEqual(report["answer_attempts"], 0)

    def test_working_polls_explicitly_without_resending_source_message(self):
        def reply(request, service):
            if request["method"] == "SendMessage":
                service.context = request["params"]["message"]["contextId"]
                return rpc(request, task(request, "TASK_STATE_WORKING", "working-task"))
            self.assertEqual(request["method"], "GetTask")
            self.assertEqual(request["params"]["id"], "working-task")
            return rpc(request, task(request, "TASK_STATE_COMPLETED", "working-task", service.context))
        with server(reply) as service:
            report = self.run_client(service, limits={"poll_interval_seconds": 0.001})
            self.assertEqual(report["status"], "recorded")
            self.assertEqual(report["turns"][0]["polls"], 1)
            self.assertEqual([item["request"]["method"] for item in service.posts], ["SendMessage", "GetTask"])

    def test_poll_limit_preserves_working_outcome(self):
        def reply(request, service):
            if request["method"] == "SendMessage":
                service.context = request["params"]["message"]["contextId"]
            return rpc(request, task(request, "TASK_STATE_WORKING", "working-task", service.context))
        with server(reply) as service:
            report = self.run_client(service, limits={"max_polls": 1, "poll_interval_seconds": 0.001})
            self.assert_partial(report, "poll_limit_reached")
            self.assertEqual(len(service.posts), 2)
            self.assertEqual(len(report["turns"][0]["observations"]), 2)
            self.assertEqual(report["turns"][0]["last_observed_state"], "working")
            self.assertEqual(report["turns"][0]["poll_observations"], 1)

    def test_total_poll_deadline_does_not_start_a_hidden_retry(self):
        with server(lambda request, _: rpc(request, task(request, "TASK_STATE_WORKING"))) as service:
            report = self.run_client(service, limits={"total_timeout_seconds": 0.03, "poll_interval_seconds": 0.04})
            self.assert_partial(report)
            self.assertEqual(len(service.posts), 1)
            self.assertEqual(report["hidden_retries"], 0)

    def test_rpc_id_type_and_value_mismatches_are_unresolved(self):
        for invalid in (True, 1, "wrong-rpc"):
            with self.subTest(id=invalid), tempfile.TemporaryDirectory() as directory:
                def reply(request, _):
                    value = rpc(request, task(request))
                    value["id"] = invalid
                    return value
                with server(reply) as service:
                    report = run_case(self.case, service.endpoint, Path(directory) / "capture", session_policy=self.policy)
                    self.assert_partial(report, "response_rpc_id_type_or_value_mismatch")

    def test_returned_context_mismatch_is_unresolved(self):
        with server(lambda request, _: rpc(request, task(request, context=str(uuid4())))) as service:
            self.assert_partial(self.run_client(service), "returned_task_context_mismatch")

    def test_get_task_must_return_the_polled_task(self):
        def reply(request, service):
            if request["method"] == "SendMessage":
                service.context = request["params"]["message"]["contextId"]
                return rpc(request, task(request, "TASK_STATE_WORKING", "correct-task"))
            return rpc(request, task(request, task_id="other-task", context=service.context))
        with server(reply) as service:
            self.assert_partial(self.run_client(service, limits={"poll_interval_seconds": 0.001}), "polled_task_id_mismatch")

    def test_rpc_error_is_preserved_without_retry(self):
        with server(lambda request, _: rpc(request, error={"code": -32000, "message": "Fixture failure", "data": {"observed": True}})) as service:
            report = self.run_client(service)
            self.assert_partial(report, "jsonrpc_error_response")
            self.assertEqual(report["exchanges"][-1]["envelope"]["error"]["data"], {"observed": True})
            self.assertEqual(len(service.posts), 1)

    def test_message_only_reply_is_partial(self):
        with server(lambda request, _: rpc(request, {"message": {"messageId": "message", "parts": [{"text": "Completed!"}]}})) as service:
            self.assert_partial(self.run_client(service), "message_only_reply_task_unresolved")

    def test_missing_task_context_state_and_conflicting_kind_are_partial(self):
        for change in ("id", "contextId", "status", "kind"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                def reply(request, _):
                    value = task(request)
                    if change == "kind":
                        value["kind"] = "message"
                    else:
                        value.pop(change)
                    return rpc(request, {"task": value})
                with server(reply) as service:
                    report = run_case(self.case, service.endpoint, Path(directory) / "capture", session_policy=self.policy)
                    self.assert_partial(report)

    def test_false_completed_text_does_not_make_failed_task_a_grade(self):
        with server(lambda request, _: rpc(request, task(request, "TASK_STATE_FAILED"))) as service:
            report = self.run_client(service)
            self.assert_partial(report, "source_turn_did_not_complete")
            self.assertFalse(report["qualification_established"])

    def test_duplicate_nonfinite_and_overflowed_json_are_retained_partial(self):
        for body in (b'{"jsonrpc":"2.0","id":1,"id":1,"result":{}}', b'{"value":NaN}', b'{"value":1e999}'):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                with server(lambda *_: http(body)) as service:
                    report = run_case(self.case, service.endpoint, Path(directory) / "capture", session_policy=self.policy)
                    self.assert_partial(report)
                    self.assertEqual((Path(directory) / "capture/wire/000002/response.body.bin").read_bytes(), body)

    def test_truncated_http_body_retains_received_prefix(self):
        raw = http(b'{"unfinished":', length=100)
        with server(lambda *_: raw) as service:
            report = self.run_client(service)
            self.assert_partial(report, "content_length")
            root = self.directory / "capture/wire/000002"
            self.assertEqual((root / "response.http.bin").read_bytes(), raw)
            self.assertFalse(report["exchanges"][-1]["http_body_complete"])

    def test_complete_chunked_json_is_supported(self):
        with server(lambda request, _: http(encoded(rpc(request, task(request))), chunked=True)) as service:
            report = self.run_client(service)
            self.assertEqual(report["status"], "recorded")

    def test_truncated_streaming_body_is_partial(self):
        raw = b"HTTP/1.1 200 Mock\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n20\r\ndata: incomplete"
        with server(lambda *_: raw) as service:
            self.assert_partial(self.run_client(service))
            self.assertEqual((self.directory / "capture/wire/000002/response.http.bin").read_bytes(), raw)

    def test_redirect_is_not_followed(self):
        with server(lambda *_: http(b"", status=302)) as service:
            report = self.run_client(service)
            self.assert_partial(report, "http_status_302")
            self.assertEqual(len(service.posts), 1)
            self.assertEqual(report["exchanges"][-1]["redirects_followed"], 0)

    def test_agent_card_wrong_protocol_or_endpoint_stops_before_post(self):
        for change in ("protocolVersion", "url"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                def mutate(card):
                    card["supportedInterfaces"][0][change] = "0.3" if change == "protocolVersion" else "http://127.0.0.1:65534/"
                    return card
                with server(card_change=mutate) as service:
                    report = run_case(self.case, service.endpoint, Path(directory) / "capture", session_policy=self.policy)
                    self.assert_partial(report, "agent_card")
                    self.assertEqual(len(service.posts), 0)

    def test_original_omitted_interface_version_preserves_legacy_card_and_requested_1_0(self):
        def mutate(card):
            interface = card["supportedInterfaces"][0]
            interface.pop("protocolVersion")
            card.update(protocolVersion="0.3", url=interface["url"], preferredTransport="JSONRPC")
            return card
        with server(card_change=mutate) as service:
            report = self.run_client(service)
            self.assertEqual(report["status"], "recorded")
            self.assertEqual(len(service.posts), 1)
            binding = report["agent_card_binding"]
            self.assertFalse(binding["interface_protocol_version_present"])
            self.assertIsNone(binding["interface_protocol_version"])
            self.assertEqual(binding["legacy_global_protocol_version"], "0.3")
            self.assertEqual(binding["advertisement_qualification"], "unresolved_omitted_interface_version")
            self.assertFalse(binding["advertised_1_0"])
            self.assertFalse(binding["card_rewritten"])
            self.assertFalse(binding["legacy_protocol_fallback_attempted"])
            self.assertFalse(binding["native_protocol_qualification_established"])
            self.assertEqual(binding["requested_protocol_version"], "1.0")
            self.assertEqual(dict(service.posts[0]["headers"])["A2A-Version"], "1.0")
            captured = json.loads((self.directory / "capture/wire/000001/response.body.bin").read_bytes())
            self.assertEqual(captured["protocolVersion"], "0.3")
            self.assertNotIn("protocolVersion", captured["supportedInterfaces"][0])

    def test_omitted_version_does_not_accept_conflicting_global_or_duplicate_interfaces(self):
        for change in ("global", "duplicate", "legacy_url", "explicit_empty"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                def mutate(card):
                    interface = card["supportedInterfaces"][0]
                    interface.pop("protocolVersion")
                    card["protocolVersion"] = "0.3"
                    if change == "global":
                        card["protocolVersion"] = "2.0"
                    elif change == "duplicate":
                        card["supportedInterfaces"].append({**interface, "protocolVersion": "1.0"})
                    elif change == "legacy_url":
                        card["url"] = "http://127.0.0.1:65534/"
                    else:
                        interface["protocolVersion"] = ""
                    return card
                with server(card_change=mutate) as service:
                    report = run_case(self.case, service.endpoint, Path(directory) / "capture", session_policy=self.policy)
                    self.assert_partial(report)
                    self.assertEqual(len(service.posts), 0)

    def test_invalid_endpoint_and_nonempty_state_do_not_issue_requests(self):
        with server() as service:
            for index, endpoint in enumerate(("http://localhost:12345/", service.endpoint + "?token=not-used", "http://user@127.0.0.1:12345/")):
                report = run_case(self.case, endpoint, self.directory / str(index), session_policy=self.policy)
                self.assert_partial(report, "endpoint")
            self.case["session_input"]["state"] = {"unsupported": True}
            self.policy = policy(self.case)
            self.assert_partial(self.run_client(service), "nonempty_source_state")
            self.assertEqual(service.gets, [])

    def test_output_is_exclusive_including_failed_allocation(self):
        with server(lambda request, _: rpc(request, {})) as service:
            self.assert_partial(self.run_client(service))
            original = (self.directory / "capture/result.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "refusing_existing_output"):
                self.run_client(service)
            self.assertEqual((self.directory / "capture/result.json").read_bytes(), original)

    def test_application_source_binding_and_mutation_detection(self):
        source = self.directory / "inputs/application-cases.json"
        source.parent.mkdir()
        original = encoded({"schema_version": "upstream-agentops-application-cases/1", "cases": [self.case]})
        source.write_bytes(original)
        def reply(request, _):
            source.write_bytes(original + b"\n")
            return rpc(request, task(request))
        with server(reply) as service:
            report = self.run_client(service, source_case_path=source)
            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["application_source_unchanged"])
            self.assertEqual((self.directory / "capture/input/application-cases.json").read_bytes(), original)

    def test_supplied_object_mutation_does_not_change_published_source_turn(self):
        original = deepcopy(self.case)
        def reply(request, _):
            self.case["conversation"][0]["user_content"]["parts"][0]["text"] = "Changed externally."
            return rpc(request, task(request))
        with server(reply) as service:
            report = self.run_client(service)
            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["input_objects_unchanged"])
            self.assertEqual(service.posts[0]["request"]["params"]["message"]["parts"], original["conversation"][0]["user_content"]["parts"])

    def test_all_21_audited_application_inputs_use_exact_original_user_parts(self):
        # Read only the existing application projection; evaluator files are never opened.
        source = ROOT / "runs/upstream-agentops-cases/v1/application/cases.json"
        document = json.loads(source.read_bytes())
        self.assertEqual(len(document["cases"]), 21)
        self.assertEqual(sum(len(case["conversation"]) for case in document["cases"]), 22)
        with server() as service:
            total = 0
            seen = []
            def guard(connection):
                seen.append((connection.getsockname(), connection.getpeername()))
            for index, original in enumerate(document["cases"]):
                start = len(service.posts)
                guard_start = len(seen)
                report = run_case(original, service.endpoint, self.directory / ("original-" + str(index)), session_policy=policy(original),
                                  source_case_path=source, connection_guard=guard)
                self.assertEqual(report["status"], "recorded", report["errors"])
                self.assertTrue(report["connection_guard_configured"])
                self.assertEqual(len(seen) - guard_start, len(original["conversation"]) + 1)
                for exchange, endpoints in zip(report["exchanges"], seen[guard_start:]):
                    self.assertTrue(exchange["connection_guard_configured"])
                    self.assertTrue(exchange["connection_guard_invoked"])
                    self.assertTrue(exchange["connection_guard_passed"])
                    self.assertEqual(exchange["connected_local_endpoint"], list(endpoints[0]))
                    self.assertEqual(exchange["connected_peer_endpoint"], list(endpoints[1]))
                    self.assertTrue(exchange["request_send_attempted"])
                self.assertFalse(report["qualification_established"])
                self.assertFalse(report["runtime_identity_authenticated"])
                self.assertEqual(report["turns_completed"], len(original["conversation"]))
                for turn, posted in zip(original["conversation"], service.posts[start:]):
                    message = posted["request"]["params"]["message"]
                    self.assertEqual(message["parts"], turn["user_content"]["parts"])
                    self.assertNotIn("taskId", message)
                self.assertEqual(report["graded_upstream_cases"], 0)
                total += report["turns_completed"]
            self.assertEqual(total, 22)


if __name__ == "__main__":
    unittest.main()
