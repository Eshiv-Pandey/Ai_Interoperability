"""Independent archive checker for official-handler bridge fidelity probe v1.

No SDK, capture-driver, subprocess, network, or service imports. check_archive
reads only a preserved archive. check_records accepts its returned records for
in-memory mutations; changes are never written to the original evidence.
"valid" means evidence/policy integrity, independently of expected behavior.
Partial attempts are retained, not promoted to complete successful experiments.
The integrating assistant added pre-execution strict JSON, advertised-card and
post-source/dist checks after the separate agent authored the checker.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

INITIAL = '{"action":"shuffle","history":[{"guess":25,"response":"Go higher"}]}'
ANSWER = "Well done!"
HISTORY = [{"guess": 25, "response": "Go higher"}]
PORT = "scripts/fixtures/carol-reference-v1.mjs"
PORT_HASH = "b6b6492ee5c27cf5db0474054b0f18a8feafe0859d9faaa4fd67946c7768626d"
SPEC = "docs/research/official-handler-bridge-probe-v1.md"
DRIVER = "scripts/capture-official-handler-bridge-v1.mjs"
CHECKER = "scripts/check_official_handler_bridge.py"
PINS = {
    "amirk_a2a_to_mcp": "58eff9da469bccdc432bf164662727947de646b4",
    "mgcrea_mcp_a2a": "c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5",
}
LOCKS = {
    "amirk_a2a_to_mcp": "3e3c7e550d7166bd7f32e4e8e27811eaaf678bf3c3a1157b974f87734037b4da",
    "mgcrea_mcp_a2a": "ae2b80a794c9ab45118f2f9653e96332296b149793cfe6bb14c8170c41c0a3c3",
}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


CHECKER_IMPORT_SHA256 = sha(Path(__file__).read_bytes())


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def strict_json(value):
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = item
        return result

    def invalid_constant(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    return json.loads(value, object_pairs_hook=unique, parse_constant=invalid_constant)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def nonempty(value):
    return isinstance(value, str) and bool(value)


def safe_relative(value):
    return (nonempty(value) and "\\" not in value and ":" not in value
            and not PurePosixPath(value).is_absolute()
            and all(part not in ("", ".", "..") for part in value.split("/")))


def lower_headers(value):
    return {str(k).lower(): str(v) for k, v in (value or {}).items()}


def at(value, path):
    for token in re.findall(r"[^.\[\]]+", path):
        if isinstance(value, list) and token.isdigit():
            index = int(token)
            value = value[index] if index < len(value) else None
        elif isinstance(value, dict):
            value = value.get(token)
        else:
            return None
    return value


def message_text(params):
    return "\n".join(part.get("text", "") for part in
                     (params or {}).get("message", {}).get("parts", [])
                     if isinstance(part, dict) and isinstance(part.get("text"), str))


def task_from_rpc(value, send=False):
    result = (value or {}).get("result")
    return result.get("task") if send and isinstance(result, dict) else result


def task_identity(task):
    if not isinstance(task, dict):
        return None, None
    return task.get("id"), task.get("contextId")


def task_state(task):
    return at(task, "status.state")


def artifact_texts(task):
    if not isinstance(task, dict) or not isinstance(task.get("artifacts"), list):
        return None
    texts = []
    for artifact in task["artifacts"]:
        parts = artifact.get("parts") if isinstance(artifact, dict) else None
        if not isinstance(parts, list):
            return None
        for part in parts:
            if not isinstance(part, dict) or not isinstance(part.get("text"), str):
                return None
            texts.append(part["text"])
    return texts


def initial_artifact(task):
    texts = artifact_texts(task)
    if texts is None or len(texts) != 1:
        return False
    try:
        return strict_json(texts[0]) == HISTORY
    except (ValueError, TypeError):
        return False


class Check:
    def __init__(self):
        self.errors = []
        self.deviations = []
        self.observations = {}
        self.entity_count = 0

    def require(self, condition, where, reason):
        if not condition:
            self.errors.append({"path": where, "reason": reason})
        return bool(condition)

    def expected(self, condition, where, reason):
        if not condition:
            self.deviations.append({"path": where, "reason": reason})
        return bool(condition)

    def time(self, value, where):
        try:
            if isinstance(value, dict):
                utc, mono = value["utc"], value["monotonic_ns"]
            else:
                utc, mono = value, None
            parsed = datetime.fromisoformat(utc.replace("Z", "+00:00"))
            self.require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
                         where, "UTC timestamp required")
            if mono is not None:
                self.require(isinstance(mono, str) and mono.isdigit(), where, "Monotonic ns must be a digit string")
                return int(mono)
            return parsed.timestamp() * 1e9
        except (KeyError, TypeError, ValueError, AttributeError):
            self.require(False, where, "Invalid recorded timestamp")
            return None

    def entity(self, value, where, parse=True, sse=False):
        if not self.require(isinstance(value, dict), where, "Missing entity object"):
            return None
        try:
            data = base64.b64decode(value["base64"], validate=True)
            self.require(value.get("bytes") == len(data), where + ".bytes", "Byte count differs from base64")
            self.require(value.get("sha256") == sha(data), where + ".sha256", "Digest differs from retained entity")
            raw = data.decode("utf-8")
            self.require(value.get("raw") == raw, where + ".raw", "UTF-8 raw text differs from base64")
            self.entity_count += 1
            if not parse:
                return raw
            if sse:
                events = [line[5:].strip() for line in raw.splitlines() if line.startswith("data:")]
                raw_json = events[-1] if events else "null"
            else:
                raw_json = raw
            try:
                decoded = strict_json(raw_json) if raw_json else None
            except ValueError:
                decoded = None
                self.require(value.get("json") is None, where + ".json", "Unparseable raw entity has invented JSON")
                self.require(bool(value.get("json_parse_error") or value.get("parse_error")),
                             where, "Parse failure lacks retained reason")
            else:
                if "json" in value:
                    self.require(value["json"] == decoded, where + ".json", "Decoded convenience JSON differs from bytes")
            return decoded
        except (KeyError, TypeError, ValueError, UnicodeError):
            self.require(False, where, "Entity encoding is invalid or incomplete")
            return None

    def exchange(self, item, where, http=False):
        request, response = item.get("request"), item.get("response")
        rq = self.entity(request, where + ".request") if request is not None else None
        rp = None
        if response is not None:
            sse = "text/event-stream" in lower_headers(response.get("headers")).get("content-type", "")
            rp = self.entity(response, where + ".response", sse=sse)
        if request:
            start = self.time({"utc": request.get("started_at_utc"),
                               "monotonic_ns": request.get("monotonic_ns")}, where + ".request.time")
        else:
            start = None
        if response:
            end = self.time({"utc": response.get("observed_at_utc"),
                             "monotonic_ns": response.get("monotonic_ns")}, where + ".response.time")
        else:
            end = None
        if start is not None and end is not None:
            self.require(end >= start, where, "Response precedes request")
            if "elapsed_ms" in item:
                duration = item["elapsed_ms"]
                self.require(isinstance(duration, (int, float)) and not isinstance(duration, bool)
                             and math.isfinite(duration) and abs(duration - (end - start) / 1e6) < 0.001,
                             where + ".elapsed_ms", "Elapsed time differs from monotonic timestamps")
        if rq and isinstance(rq, dict):
            self.require(rq.get("jsonrpc") == "2.0", where + ".request", "Unexpected JSONRPC version")
            if rp and isinstance(rp, dict) and "id" in rq:
                # The official Express version exception legitimately uses null.
                if response.get("status", 200) < 400:
                    self.require(rp.get("id") == rq["id"], where + ".response.id", "Response ID does not bind request")
        if http and request:
            u = urlsplit(request.get("url", ""))
            self.require(u.scheme == "http" and u.hostname == "127.0.0.1" and u.port not in (None, 0)
                         and not u.query and not u.fragment and not u.username,
                         where + ".request.url", "Request escaped isolated loopback profile")
            self.require(request.get("method") in ("GET", "POST"), where, "Unexpected HTTP method")
            if response:
                self.require(integer(response.get("status")) and 100 <= response["status"] <= 599,
                             where + ".response.status", "Missing HTTP status")
        if response is None and rq and "id" in rq:
            self.require(nonempty(item.get("error")), where, "Unanswered request lacks retained failure reason")
        return {"item": item, "request": rq, "response": rp, "start": start, "end": end}


def decode_tool(rpc):
    body = rpc.get("result") if isinstance(rpc, dict) else None
    if not isinstance(body, dict):
        return None, body, None
    if "structuredContent" in body:
        return body["structuredContent"], body, "structuredContent object"
    blocks = body.get("content")
    if isinstance(blocks, list) and blocks and blocks[0].get("type") == "text":
        try:
            return strict_json(blocks[0]["text"]), body, "JSON serialized inside result.content[0].text"
        except (ValueError, KeyError, TypeError):
            pass
    return None, body, None


def check_records(records):
    """Check mutable returned records without importing any runtime application."""
    c = Check()
    try:
        _check_records(c, records)
    except Exception as error:
        # Corrupt/missing data is a retained checker failure, never a crash/rerun.
        c.require(False, "checker", type(error).__name__ + ": " + str(error))
    report = records.get("report", {})
    completed = c.observations.get("complete_planned_attempt", False)
    return {
        "schema_version": "official-handler-bridge-check/1",
        "valid": not c.errors,
        "complete": bool(completed) and not c.errors,
        "partial": not bool(completed),
        "expected_outcome_observed": bool(completed) and not c.errors and not c.deviations,
        "validation_errors": c.errors,
        "expectation_deviations": c.deviations,
        "observations": c.observations,
        "checked_entity_count": c.entity_count,
        "official_variant": report.get("official_variant"),
        "claim_limit": "Archive/software fidelity validation only; no service rerun, scientific novelty credit, second domain or human review",
        "records": records,
    }


def check_report(report, native_events=None, lifecycle_events=None, diagnostics=None,
                 *, archive_material=None):
    """Semantic API; archive_material comes from check_archive()['records'].

    For mutations, prefer deepcopy(result['records']) then check_records(copy).
    Archive material is mandatory for source/snapshot integrity validation.
    """
    material = copy.deepcopy(archive_material or {})
    material.update(report=report, native_events=native_events or [],
                    lifecycle_events=lifecycle_events or [], diagnostics=diagnostics or {})
    return check_records(material)


def _check_records(c, data):
    r = data["report"]
    variant = r.get("official_variant")
    c.require(variant in ("B1", "B2", "B3", "B4"), "official_variant", "Unknown prospective variant")
    amir = variant in ("B1", "B2")
    route = "amirk_a2a_to_mcp" if amir else "mgcrea_mcp_a2a"
    inherited = "R" + str(variant)[1:]
    c.require(r.get("schema_version") == "runtime-wire-observation/1"
              and r.get("experiment_id") == "official-handler-bridge-fidelity/1", "report", "Wrong experiment/schema")
    c.require(r.get("route_id") == route and r.get("variant_id") == inherited
              and r.get("source_commit") == PINS[route], "report", "Caller/pin association differs from frozen profile")
    c.require(r.get("node") == "v22.13.0" and integer(r.get("parent_pid")), "node", "Recorded parent identity missing")
    profile_ok = (at(r, "configuration.tasks_extension") == (variant == "B2") if amir else
                  at(r, "configuration.writes") is True and at(r, "configuration.channel") is False
                  and at(r, "configuration.retries") == 0)
    c.require(at(r, "protocol.mcp") == ("2026-07-28" if amir else "2025-11-25") and profile_ok,
              "configuration", "MCP/bridge profile changed")
    c.require(r.get("model_calls") == 0 and r.get("remote_network_requests") == 0
              and at(r, "provenance.model_calls") == 0, "costs", "Forbidden inference/remote request")
    c.require(at(r, "provenance.kind") == "official-handler-bridge-fidelity-control"
              and nonempty(at(r, "provenance.instrumentation.inherited_preload_labels")),
              "provenance", "Actual official service classification or inherited-label disclosure missing")
    service = r.get("official_service", {})
    frozen_service = at(r, "official_pre_execution.official_service")
    fixed_service = {"sdk_version": "1.1.0", "default_context_builder": True,
                     "legacy_compatibility": False, "custom_http_wrapper_started": False,
                     "handler_mount": "/a2a", "card_mount": "/.well-known/agent-card.json"}
    c.require(all(service.get(k) == v for k, v in fixed_service.items()), "official_service", "Handler/profile changed")
    if r.get("official_pre_execution"):
        c.require(frozen_service == fixed_service, "official_pre_execution.official_service",
                  "Frozen service object was changed/aliased after startup")
    c.require(r.get("native_control_plan") == ["N1", "N2", "N3"]
              and r.get("origin_diagnostic_plan") == "E1", "plans", "Prospective control plan altered")
    c.time(r.get("started_at_utc"), "started_at_utc")
    c.time(r.get("completed_at_utc"), "completed_at_utc")
    c.require(r.get("outcome") in ("recorded", "recorded-native-ineligible", "failed")
              and r.get("exit_code") in (0, 1), "outcome", "Attempt not closed")
    if r.get("outcome") == "failed":
        c.require(bool(r.get("error") or r.get("caller_error") or r.get("native_correlation_error")
                       or r.get("post_source_changes") or r.get("post_source_errors")
                       or service.get("cleanup_error") or any(x.get("error") for x in r.get("cleanup", []))),
                  "outcome", "Failed attempt lacks retained explanation")
        c.expected(False, "outcome", "Attempt retained a setup/caller/cleanup failure")
    elif r.get("outcome") == "recorded-native-ineligible":
        c.require(nonempty(r.get("bridge_unexecuted_reason")), "bridge_unexecuted_reason", "No eligibility failure reason")
    _snapshots(c, r, data)

    mcp = []
    mcp_by_id = {}
    phases = {}
    previous_start = None
    rpc_number = 0
    allowed_phases = {"discover_full_tools", "initial_typed_send", "initial_authoritative_pending_get",
                      "final_authoritative_original_get", "unsolicited_notification_or_reply"}
    allowed_phases.update({"discover_profile", "fixed_same_task_answer_send"} if variant == "B1" else
                          {"discover_profile", "pending_extension_get_form", "fixed_same_task_answer_update",
                           "extension_get_after_answer"} if variant == "B2" else
                          {"initialize", "initialized_notification", "fixed_same_task_answer",
                           "final_authoritative_original_raw_get"})
    for index, exchange in enumerate(r.get("exchanges", [])):
        where = "exchanges." + str(index)
        eid = exchange.get("exchange_id")
        c.require(nonempty(eid) and eid not in mcp_by_id, where, "MCP exchange ID reused")
        parsed = c.exchange(exchange, where)
        c.require(exchange.get("phase") in allowed_phases, where, "Action outside frozen caller routine")
        mcp.append(parsed)
        mcp_by_id[eid] = parsed
        phases.setdefault(exchange.get("phase"), []).append(parsed)
        if parsed["request"] is not None:
            if "id" in parsed["request"]:
                rpc_number += 1
                c.require(parsed["request"]["id"] == rpc_number and eid == "mcp-" + str(rpc_number),
                          where, "MCP request sequence/identity altered")
            if previous_start is not None and parsed["start"] is not None:
                c.require(parsed["start"] >= previous_start, where, "MCP request order altered")
            previous_start = parsed["start"]
            if amir:
                headers = lower_headers(exchange["request"].get("headers"))
                target = urlsplit(exchange["request"].get("url", ""))
                c.require(target.scheme == "http" and target.hostname == "127.0.0.1" and target.port not in (0, None)
                          and exchange["request"]["url"] == r.get("endpoint") and not target.query,
                          where, "MCP request escaped selected loopback endpoint")
                c.require(headers.get("mcp-protocol-version") == "2026-07-28",
                          where, "Modern MCP header altered")
                meta = at(parsed["request"], "params._meta") or {}
                caps = {"extensions": {"io.modelcontextprotocol/tasks": {}}} if variant == "B2" else {}
                c.require(meta.get("io.modelcontextprotocol/protocolVersion") == "2026-07-28"
                          and meta.get("io.modelcontextprotocol/clientCapabilities") == caps,
                          where, "Per-request MCP profile changed")
                c.require(headers.get("mcp-method") == parsed["request"].get("method"), where, "MCP method header changed")
                method = parsed["request"].get("method", "")
                params = parsed["request"].get("params", {})
                if method == "tools/call" or method.startswith("tasks/"):
                    c.require(headers.get("mcp-name") == params.get("name" if method == "tools/call" else "taskId"),
                              where, "MCP operation header altered")
                if exchange.get("response") is not None:
                    c.require(integer(exchange["response"].get("status")), where, "MCP HTTP status missing")

    native_events = data.get("native_events", [])
    bridge_native = []
    starts = {}
    header = native_events[0] if native_events else None
    previous_native_time = None
    for index, event in enumerate(native_events):
        kind = event.get("type")
        event_stamp = (at(event, "request.monotonic_ns") if kind == "request-started" else
                       at(event, "response.monotonic_ns") if kind == "exchange-completed" else
                       at(event, "observed.monotonic_ns"))
        if isinstance(event_stamp, str) and event_stamp.isdigit():
            event_time = int(event_stamp)
            c.require(previous_native_time is None or event_time >= previous_native_time,
                      "native_events." + str(index), "Native event ordering altered")
            previous_native_time = event_time
        if kind == "request-started":
            eid = event.get("exchange_id")
            c.require(eid not in starts, "native_events." + str(index), "Native request ID reused")
            starts[eid] = event
        elif kind == "exchange-completed":
            eid = event.get("exchange_id")
            c.require(eid in starts and event.get("request") == starts.get(eid, {}).get("request"),
                      "native_events." + str(index), "Native start/completion pair changed")
            c.require(not any(x["item"].get("exchange_id") == eid for x in bridge_native),
                      "native_events", "Native completion duplicated")
            bridge_native.append(c.exchange(event, "native_events." + str(index), http=True))
    c.require(set(starts) == {x["item"].get("exchange_id") for x in bridge_native},
              "native_events", "Started native exchange lacks final retained record")
    if header:
        c.require(header.get("schema_version") == "private-native-http/1"
                  and header.get("run_id") == r.get("run_id") and header.get("route_id") == route
                  and header.get("pid") == at(r, "provenance.bridge_pid")
                  and at(header, "fixture.sha256") == PORT_HASH,
                  "native_events.0", "Sidecar run/process/source identity differs")
    native_sequence = list(starts)
    c.require(native_sequence == ["native-" + str(i + 1) for i in range(len(native_sequence))],
              "native_events", "Native request ordering/ID sequence altered")

    controls = r.get("native_controls", [])
    c.require([x.get("case_id") for x in controls] == ["N1", "N2", "N3"],
              "native_controls", "All planned controls must appear once in order")
    control_parsed = {}
    sequence = 0
    control_end = None
    for record in controls + [r.get("origin_diagnostic", {})]:
        cid = record.get("case_id")
        where = "native_controls." + str(cid)
        c.require(cid in ("N1", "N2", "N3", "E1") and isinstance(record.get("executed"), bool),
                  where, "Control execution status missing")
        if not record.get("executed"):
            c.require(nonempty(record.get("reason")) and not record.get("request") and not record.get("response"),
                      where, "Unexecuted control needs reason and no invented entities")
            continue
        sequence += 1
        start = c.time(record.get("started"), where + ".started")
        end = c.time(record.get("completed"), where + ".completed")
        c.require(record.get("attempt") == 1 and start is not None and end is not None and end >= start,
                  where, "Control attempt/timing altered")
        rq = c.entity(record.get("request"), where + ".request")
        rp = c.entity(record.get("response"), where + ".response") if record.get("response") else None
        c.require(record.get("response") is not None or nonempty(record.get("error")),
                  where, "Control reply/failure absent")
        c.require(rq.get("id") == cid + "-" + str(sequence) and rq.get("jsonrpc") == "2.0",
                  where, "Control JSONRPC order/ID altered")
        c.require(record["request"].get("method") == "POST" and record["request"].get("url") == service.get("endpoint")
                  and lower_headers(record["request"].get("headers")) ==
                  {"content-type": "application/json", "a2a-version": "1.0"},
                  where, "Native positive control endpoint/version changed")
        if rp and record["response"].get("status") == 200:
            c.require(rp.get("id") == rq.get("id"), where, "Positive control response ID mismatch")
        if control_end is not None:
            c.require(start >= control_end, where, "Native controls/E1 reordered")
        control_end = end
        control_parsed[cid] = {"item": record, "request": rq, "response": rp, "start": start, "end": end}
    n1 = control_parsed.get("N1")
    n2 = control_parsed.get("N2")
    n3 = control_parsed.get("N3")
    n_task = task_from_rpc(n1["response"], True) if n1 else None
    n_id, n_context = task_identity(n_task)
    if n1:
        message = at(n1["request"], "params.message") or {}
        c.require(n1["request"].get("method") == "SendMessage"
                  and message_text(n1["request"].get("params")) == INITIAL
                  and not at(n1["request"], "params.message.referenceTaskIds")
                  and message.get("role") == "ROLE_USER"
                  and bool(UUID.fullmatch(str(message.get("messageId"))))
                  and message.get("parts") == [{"text": INITIAL, "mediaType": "text/plain"}]
                  and at(n1["request"], "params.configuration") == {"acceptedOutputModes": ["text/plain"]},
                  "N1", "Initial native action altered")
    if n2:
        msg = at(n2["request"], "params.message") or {}
        c.require(n2["request"].get("method") == "SendMessage" and message_text(n2["request"].get("params")) == ANSWER
                  and msg.get("taskId") == n_id and msg.get("contextId") == n_context
                  and msg.get("referenceTaskIds") == [n_id] and msg.get("role") == "ROLE_USER"
                  and bool(UUID.fullmatch(str(msg.get("messageId"))))
                  and msg.get("parts") == [{"text": ANSWER, "mediaType": "text/plain"}]
                  and at(n2["request"], "params.configuration") == {"acceptedOutputModes": ["text/plain"]},
                  "N2", "Native completion binding/reference altered")
    if n3:
        c.require(n3["request"].get("method") == "GetTask"
                  and n3["request"].get("params") == {"id": n_id, "historyLength": 10},
                  "N3", "Native authoritative read action altered")
    native_ok = bool(n1 and n2 and n3 and nonempty(n_id) and nonempty(n_context)
                     and all(x["item"].get("response", {}).get("status") == 200
                             for x in (n1, n2, n3))
                     and task_state(n_task) == "TASK_STATE_INPUT_REQUIRED" and initial_artifact(n_task)
                     and task_identity(task_from_rpc(n2["response"], True)) == (n_id, n_context)
                     and task_state(task_from_rpc(n2["response"], True)) == "TASK_STATE_COMPLETED"
                     and task_identity(task_from_rpc(n3["response"])) == (n_id, n_context)
                     and task_state(task_from_rpc(n3["response"])) == "TASK_STATE_COMPLETED")
    c.require(r.get("native_eligible") is native_ok, "native_eligible", "Declared eligibility differs from raw controls")
    c.expected(native_ok, "native_controls", "Header-positive native eligibility did not succeed")
    if n2 and n3 and isinstance(n_task, dict):
        for name, task in (("N2", task_from_rpc(n2["response"], True)), ("N3", task_from_rpc(n3["response"]))):
            if isinstance(task, dict):
                c.require(task.get("artifacts") == n_task.get("artifacts"), name, "Native completion changed original artifact")
    if r.get("native_original"):
        c.require(r["native_original"] == {"task_id": n_id, "context_id": n_context, "public_source_case": "N1"},
                  "native_original", "Native convenience binding differs from N1 bytes")

    initial_native = [x for x in bridge_native if at(x["request"], "method") == "SendMessage"
                      and message_text(at(x["request"], "params")) == INITIAL
                      and at(x["response"], "result.task.id")]
    c.require(len(initial_native) <= 1, "native_events", "Initial bridge send repeated")
    original_native = initial_native[0] if initial_native else None
    b_task = task_from_rpc(original_native["response"], True) if original_native else None
    b_id, b_context = task_identity(b_task)
    binding = r.get("evaluator_binding")
    e1 = control_parsed.get("E1")
    if original_native:
        c.require(binding == {"source": "evaluator-private captured native initial response",
                              "native_exchange_id": original_native["item"]["exchange_id"],
                              "response_sha256": original_native["item"]["response"]["sha256"],
                              "task_id": b_id, "context_id": b_context,
                              "fed_to_bridge_caller": False, "recovery_action": False},
                  "evaluator_binding", "E1 private binding does not derive from initial raw response")
        c.require((b_id, b_context) != (n_id, n_context) and b_id != n_id,
                  "evaluator_binding", "Bridge and native control tasks were conflated")
        c.require(bool(e1), "E1", "Identifiable initial bridge task must receive one evaluator read")
    else:
        c.require(binding is None and not e1, "E1", "Invented evaluator binding/action without initial bridge response")
    if e1:
        c.require(e1["request"].get("method") == "GetTask"
                  and e1["request"].get("params") == {"id": b_id, "historyLength": 10},
                  "E1", "Evaluator action changed original binding")
        e_task = task_from_rpc(e1["response"])
        c.expected(e1["item"].get("response", {}).get("status") == 200
                   and task_identity(e_task) == (b_id, b_context), "E1", "Evaluator read did not establish original association")
        c.require(not isinstance(e_task, dict) or task_identity(e_task) == (b_id, b_context),
                  "E1", "Evaluator task/context mismatch")
    else:
        e_task = None
    c.observations.update(native_eligible=native_ok, native_control_task_id=n_id,
                          bridge_original_task_id=b_id, bridge_original_context_id=b_context,
                          evaluator_original_state=task_state(e_task))

    if service.get("started"):
        card = r.get("card", {})
        c.require(card.get("supportedInterfaces") == [{"url": service.get("endpoint"), "protocolVersion": "1.0",
                  "protocolBinding": "JSONRPC", "tenant": ""}]
                  and service.get("endpoint") == r.get("fixture_endpoint", "") + "/a2a"
                  and card.get("capabilities") == {"streaming": False, "pushNotifications": False,
                      "extensions": [], "extendedAgentCard": False}
                  and card.get("defaultInputModes") == card.get("defaultOutputModes") == ["text/plain"],
                  "card", "Advertised singleton 1.0-only official-handler profile changed")
        for parsed in bridge_native:
            request = parsed["item"]["request"]
            if request.get("method") == "GET":
                c.require(urlsplit(request.get("url", "")).path == "/.well-known/agent-card.json"
                          and parsed["item"].get("response", {}).get("status") == 200
                          and parsed["response"] == card,
                          "native_card", "Captured advertised card differs from actual service profile")

    _caller_policy(c, r, variant, mcp_by_id, phases, original_native, bridge_native, e1)
    _ingress(c, r, bridge_native, list(control_parsed.values()))
    _lifecycle(c, r, data, native_ok, mcp, bridge_native, control_parsed)
    request_mcp = [x["item"]["request"] for x in mcp if x["item"].get("request")]
    costs = r.get("costs", {})
    expected_costs = {
        "mcp_rpc_requests": sum("id" in x.get("json", {}) for x in request_mcp),
        "mcp_notifications_sent": sum("id" not in x.get("json", {}) for x in request_mcp),
        "request_bytes": sum(x["bytes"] for x in request_mcp),
        "response_bytes": sum(x["item"].get("response", {}).get("bytes", 0) for x in mcp),
        "setup_ms": at(r, "pre_execution.setup_ms"),
    }
    c.require(all(costs.get(k) == v for k, v in expected_costs.items()), "costs", "MCP aggregate costs altered")
    started_children = sum(x.get("type") == "spawn" for x in data.get("lifecycle_events", []))
    cc = r.get("control_costs", {})
    c.require(cc == {"native_control_requests": sum(x.get("executed") is True for x in controls),
                     "evaluator_only_requests": int(bool(e1)), "server_ingress_requests": len(r.get("ingress", [])),
                     "bridge_children_started": started_children, "model_calls": 0, "remote_network_requests": 0},
              "control_costs", "Separately charged control/ingress/lifecycle costs altered")
    c.observations["derived_costs"] = dict(expected_costs, bridge_native_requests=len(bridge_native), **cc)


def _caller_policy(c, r, variant, by_id, phases, initial_native, bridge_native, e1):
    amir = variant in ("B1", "B2")
    contract = r.get("contract", {})
    if contract:
        c.require(contract.get("initial_text") == INITIAL and contract.get("answer_text") == ANSWER
                  and contract.get("native_parameters_from_private_sidecar") is False,
                  "contract", "Fixed inputs/private-source policy altered")
    for key in ("initial", "pending", "answer", "final", "pending_extension", "final_extension"):
        row = r.get(key)
        if not row:
            continue
        parsed = by_id.get(row.get("exchange_id"))
        if not c.require(parsed is not None, key, "Convenience record refers to absent MCP exchange"):
            continue
        decoded, body, encoding = decode_tool(parsed["response"])
        if "body" in row:
            c.require(row["body"] == body, key, "Convenience body differs from raw MCP reply")
        if "decoded" in row:
            c.require(row["decoded"] == decoded and row.get("encoding") == encoding,
                      key, "Decoded bundle differs from raw MCP reply")
    for row in r.get("tool_interpretations", []):
        parsed = by_id.get(row.get("exchange_id"))
        if not c.require(parsed is not None, "tool_interpretations", "Absent interpreted MCP exchange"):
            continue
        decoded, body, encoding = decode_tool(parsed["response"])
        rq = parsed["request"]
        c.require(row.get("decoded") == decoded and row.get("encoding") == encoding
                  and row.get("tool") == at(rq, "params.name") and row.get("arguments") == at(rq, "params.arguments")
                  and row.get("mcp_tool_error") == (body.get("isError") is True or body.get("isToolError") is True),
                  "tool_interpretations", "Interpretation/arguments differ from raw MCP entities")
    for row in r.get("initial_reads", []):
        parsed = by_id.get(row.get("exchange_id"))
        if parsed:
            decoded, body, encoding = decode_tool(parsed["response"])
            c.require(row.get("body", body) == body and row.get("decoded", decoded) == decoded
                      and row.get("encoding", encoding) == encoding, "initial_reads", "Pending bundle was altered")
    initial_rows = phases.get("initial_typed_send", [])
    c.require(len(initial_rows) <= 1, "caller", "Initial MCP send repeated")
    public_initial = initial_rows[0] if initial_rows else None
    public_pending = by_id.get(at(r, "pending.exchange_id"))
    decoded_initial, body_initial, _ = decode_tool(public_initial["response"] if public_initial else None)
    decoded_pending, body_pending, _ = decode_tool(public_pending["response"] if public_pending else None)
    if amir:
        task = body_initial.get("taskId") if variant == "B2" and isinstance(body_initial, dict) else at(decoded_initial, "taskHandle")
        context = at(decoded_pending, "contextHandle")
        if contract.get("original_task_handle") is not None:
            c.require(contract["original_task_handle"] == task, "contract", "Opaque task binding not public in initial response")
        if contract.get("original_context_handle") is not None:
            c.require(contract["original_context_handle"] == context, "contract", "Context binding not public in pending response")
        if public_pending:
            c.require(at(decoded_pending, "taskHandle") == task, "pending", "Pending opaque task differs from initial")
            texts = [x.get("text") for x in (body_pending or {}).get("content", []) if x.get("type") == "text"]
    else:
        task, context = at(decoded_initial, "task.id"), at(decoded_pending, "context_id")
        if contract.get("original_task_id") is not None:
            c.require(contract["original_task_id"] == task, "contract", "Native task binding not public in initial response")
        if contract.get("original_context_id") is not None:
            c.require(contract["original_context_id"] == context, "contract", "Native context binding not public in pending response")
        if public_pending:
            c.require(at(decoded_pending, "id") == task, "pending", "Pending native ID differs from initial")
        texts = [x.get("text") for x in (decoded_pending or {}).get("artifacts", [])]
    if public_pending and r.get("observation", {}).get("initial_required_observed"):
        try:
            payload_valid = len(texts) == 1 and strict_json(texts[0]) == HISTORY
        except (TypeError, ValueError):
            payload_valid = False
        c.require(payload_valid, "pending.artifacts", "Public original one-entry artifact changed")
        if not amir:
            condition = r.get("initial_condition", {})
            c.require(condition.get("artifact_texts") == texts and condition.get("decoded_history") == HISTORY
                      and condition.get("artifact_history_matches") is True
                      and condition.get("task_id") == task and condition.get("context_id") == context,
                      "initial_condition", "Artifact convenience condition differs from public bytes")
    if r.get("discovery"):
        listed = by_id.get(r["discovery"].get("tools_exchange_id"))
        c.require(listed is not None and at(listed["request"], "method") == "tools/list", "discovery", "No full tool-list exchange")
        if listed:
            tools = at(listed["response"], "result.tools")
            c.require(r["discovery"].get("tools") == tools and isinstance(tools, list), "discovery", "Discovered tools altered")
            names = [x.get("name") for x in tools]
            c.require("a2a_send_message" in names and "a2a_get_task" in names
                      and (variant != "B4" or "a2a_request" in names), "discovery", "Required profile tools absent")
            if variant == "B4":
                raw_tool = next((x for x in tools if x.get("name") == "a2a_request"), {})
                methods = at(raw_tool, "inputSchema.properties.method.enum") or []
                c.require("SendMessage" in methods and "GetTask" in methods, "discovery", "Raw method permission changed")
        if listed and public_initial:
            c.require(listed["end"] <= public_initial["start"], "discovery", "Tool discovery must precede intervention")

    answers = []
    finals = []
    for parsed in by_id.values():
        rq = parsed["request"]
        if not isinstance(rq, dict):
            continue
        phase = parsed["item"].get("phase")
        method, params = rq.get("method"), rq.get("params", {})
        args = params.get("arguments", {}) if method == "tools/call" else {k: v for k, v in params.items() if k != "_meta"}
        if phase == "initial_typed_send":
            wanted = {"agent": "carol", "text": INITIAL} if amir else {"url": r.get("fixture_endpoint"), "text": INITIAL}
            c.require(method == "tools/call" and params.get("name") == "a2a_send_message" and args == wanted,
                      phase, "Initial typed action changed")
        if phase == "initial_authoritative_pending_get":
            wanted = ({"agent": "carol", "taskHandle": task, "historyLength": 10} if amir else
                      {"task_id": task, "history_length": 10, "refresh": True})
            c.require(method == "tools/call" and params.get("name") == "a2a_get_task" and args == wanted,
                      phase, "Pending action used altered/nonpublic binding")
        if phase in ("fixed_same_task_answer_send", "fixed_same_task_answer_update", "fixed_same_task_answer"):
            answers.append(parsed)
            if variant == "B1":
                wanted = {"agent": "carol", "text": ANSWER, "taskHandle": task, "contextHandle": context}
            elif variant == "B2":
                waiting = by_id.get(at(r, "pending_extension.exchange_id"))
                bundle = at(waiting["response"], "result") if waiting else {}
                requests = (bundle or {}).get("inputRequests", {})
                c.require(isinstance(requests, dict) and len(requests) == 1, "B2.form", "Not exactly one actual form")
                key = next(iter(requests), None)
                form = requests.get(key, {})
                props = at(form, "params.requestedSchema.properties") or {}
                field = next(iter(props), None)
                c.require(len(props) == 1 and at(props, str(field) + ".type") == "string"
                          and form.get("method") == "elicitation/create"
                          and bundle.get("taskId") == task and bundle.get("status") == "input_required",
                          "B2.form", "Actual elicitation eligibility changed")
                c.require(contract.get("input_request_key") == key and contract.get("requested_field") == field
                          and contract.get("requested_form") == form, "B2.form", "Form convenience binding differs")
                wanted = {"taskId": task, "inputResponses": {key: {"action": "accept", "content": {field: ANSWER}}}}
            elif variant == "B3":
                wanted = {"url": r.get("fixture_endpoint"), "text": ANSWER, "task_id": task, "context_id": context}
            else:
                wanted = {"url": r.get("fixture_endpoint"), "method": "SendMessage",
                          "params": {"message": {"messageId": at(args, "params.message.messageId"),
                                                "taskId": task, "contextId": context, "role": "ROLE_USER",
                                                "parts": [{"text": ANSWER, "mediaType": "text/plain"}],
                                                "referenceTaskIds": [task]},
                                     "configuration": {"returnImmediately": False, "acceptedOutputModes": ["text/plain"]}}}
                c.require(bool(UUID.fullmatch(str(at(args, "params.message.messageId")))), phase, "Raw message ID altered")
            c.require(args == wanted and contract.get("answer_arguments") == args,
                      phase, "Fixed answer intervention/binding altered")
            expected_method = "tasks/update" if variant == "B2" else "tools/call"
            expected_tool = "a2a_request" if variant == "B4" else "a2a_send_message"
            c.require(method == expected_method and (variant == "B2" or params.get("name") == expected_tool),
                      phase, "Wrong selected answer operation")
        if phase in ("final_authoritative_original_get", "final_authoritative_original_raw_get"):
            finals.append(parsed)
            wanted = ({"agent": "carol", "taskHandle": task, "historyLength": 10} if amir else
                      {"task_id": task, "history_length": 10, "refresh": True} if variant == "B3" else
                      {"url": r.get("fixture_endpoint"), "method": "GetTask", "params": {"id": task, "historyLength": 10}})
            c.require(method == "tools/call" and params.get("name") == ("a2a_request" if variant == "B4" else "a2a_get_task")
                      and args == wanted, phase, "Final action/binding changed")
        if method in ("tasks/get", "tasks/update"):
            c.require(variant == "B2" and params.get("taskId") == task, phase, "Tasks extension binding/profile changed")
    c.require(len(answers) <= 1 and len(finals) <= 1, "caller", "Once-only answer/final bound exceeded")
    if contract:
        c.require(contract.get("answer_attempts") == len(answers), "contract.answer_attempts", "Answer count differs from actual requests")
    if answers and finals:
        c.require(answers[0]["start"] < finals[0]["start"], "caller", "Final read preceded answer attempt")
    if e1:
        last_end = max((x["end"] or x["start"] or 0 for x in by_id.values()), default=0)
        c.require(e1["start"] >= last_end, "E1", "Evaluator read preceded caller completion")
    initial_task = task_from_rpc(initial_native["response"], True) if initial_native else None
    original_id, original_context = task_identity(initial_task)
    sends = [x for x in bridge_native if at(x["request"], "method") == "SendMessage"]
    answer_native = [x for x in sends if message_text(at(x["request"], "params")) == ANSWER]
    c.require(len(sends) <= 2 and len(answer_native) <= 1, "native_events", "Unexpected/repeated send action")
    for parsed in sends:
        msg = at(parsed["request"], "params.message") or {}
        text = message_text(at(parsed["request"], "params"))
        c.require(text in (INITIAL, ANSWER) and msg.get("role") == "ROLE_USER", "native_send", "Native text/role drift")
        refs = msg.get("referenceTaskIds") or []
        if text == INITIAL:
            c.require(not refs, "native_initial", "Initial request acquired follow-up references")
        else:
            c.require(msg.get("taskId") == original_id and msg.get("contextId") == original_context
                      and refs == ([original_id] if variant == "B4" else []),
                      "native_answer", "Serialized same-task/context/reference policy altered")
        header = lower_headers(parsed["item"]["request"].get("headers")).get("a2a-version")
        c.require(header == (None if variant == "B4" and text == ANSWER else "1.0"),
                  "native_send.headers", "Outgoing version header changed")
    for parsed in bridge_native:
        if at(parsed["request"], "method") == "GetTask":
            c.require(at(parsed["request"], "params.id") == original_id, "native_get", "Native GetTask lost original association")
            header = lower_headers(parsed["item"]["request"].get("headers")).get("a2a-version")
            # B4 has typed pending reads before the sole raw final read.
            is_raw_final = bool(finals and parsed["start"] >= finals[0]["start"] and variant == "B4")
            c.require(header == (None if is_raw_final else "1.0"), "native_get.headers", "Native read version changed")
    if initial_task is not None:
        c.expected(initial_artifact(initial_task) and task_state(initial_task) == "TASK_STATE_INPUT_REQUIRED",
                   "native_initial", "Bridge initial source condition differs")
        if not amir and nonempty(task) and nonempty(context):
            c.require((task, context) == (original_id, original_context), "public_binding",
                      "Public native ID/context differ from the actual initial task")
    if variant == "B4":
        raw = answer_native + [x for x in bridge_native if at(x["request"], "method") == "GetTask"
                               and lower_headers(x["item"]["request"].get("headers")).get("a2a-version") is None]
        c.expected(len(raw) == 2 and all(x["item"].get("response", {}).get("status") == 500
                                        and at(x["response"], "error.code") == -32009 for x in raw),
                   "B4.raw", "Raw answer/final read did not both produce HTTP500/-32009")
    else:
        c.expected(len(answer_native) == 1 and answer_native[0]["item"].get("response", {}).get("status") == 200,
                   "typed_answer", "Typed selected answer did not receive transport-positive reply")
    if e1:
        final_task = task_from_rpc(e1["response"])
        c.expected(task_state(final_task) == "TASK_STATE_INPUT_REQUIRED", "E1.state", "Source waiting expectation differs")
        if isinstance(initial_task, dict) and isinstance(final_task, dict):
            initial_artifacts = initial_task.get("artifacts", [])
            final_artifacts = final_task.get("artifacts", [])
            c.require(final_artifacts[:len(initial_artifacts)] == initial_artifacts,
                      "E1.artifacts", "Original artifact prefix was altered")
        readable = [x for x in bridge_native if at(x["request"], "method") == "GetTask"
                    and x["item"].get("response", {}).get("status") == 200
                    and isinstance(task_from_rpc(x["response"]), dict)]
        if readable and isinstance(final_task, dict):
            latest = max(readable, key=lambda x: x["start"])
            after_answer = bool(answer_native and latest["start"] > answer_native[0]["start"])
            raw_rejected = bool(variant == "B4" and answer_native
                                and answer_native[0]["item"].get("response", {}).get("status") == 500
                                and at(answer_native[0]["response"], "error.code") == -32009)
            if after_answer or raw_rejected:
                c.require(final_task == task_from_rpc(latest["response"]), "E1.snapshot",
                          "Evaluator task/artifacts differ from last unchanged authoritative origin snapshot")
        if finals and variant != "B4" and readable:
            decoded, body, _ = decode_tool(finals[0]["response"])
            if isinstance(body, dict) and not body.get("isError") and not body.get("isToolError"):
                texts = ([x.get("text") for x in body.get("content", []) if x.get("type") == "text"] if amir else
                         [x.get("text") for x in (decoded or {}).get("artifacts", [])])
                final_reads = [x for x in readable if x["start"] >= finals[0]["start"]]
                if final_reads:
                    c.require(texts == artifact_texts(task_from_rpc(final_reads[-1]["response"])),
                              "final.artifacts", "Public final artifacts differ from native response bytes")
    for receipt in r.get("receipts", []):
        parsed = by_id.get(receipt.get("exchange_id"))
        if not c.require(parsed is not None and parsed["item"].get("response") is not None,
                         "receipts", "Receipt refers to absent response"):
            continue
        source = receipt.get("source", {})
        decoded, body, _ = decode_tool(parsed["response"])
        role = receipt.get("role")
        if role == "bridge_task_record":
            task_receipt, context_receipt = (body or {}).get("taskId"), None
        elif amir:
            task_receipt, context_receipt = at(decoded, "taskHandle"), at(decoded, "contextHandle")
        elif role in ("typed_initial_public_task_receipt", "typed_answer_public_receipt"):
            task_receipt, context_receipt = at(decoded, "task.id"), at(decoded, "task.context_id")
        elif role == "raw_native_answer_public_receipt":
            task_receipt, context_receipt = at(decoded, "result.task.id"), at(decoded, "result.task.contextId")
        elif role == "raw_native_peer_task_query_final":
            task_receipt, context_receipt = at(decoded, "result.id"), at(decoded, "result.contextId")
        else:
            task_receipt, context_receipt = at(decoded, "id"), at(decoded, "context_id")
        c.require(receipt.get("task_id") == task_receipt and receipt.get("context_id") == context_receipt,
                  "receipts", "Receipt task/context is not public in its raw response")
        c.require(source.get("response_sha256") == parsed["item"]["response"]["sha256"]
                  and source.get("source_commit") == r.get("source_commit")
                  and source.get("method") == at(parsed["request"], "method")
                  and receipt.get("request_cost") == int("id" in (parsed["request"] or {})),
                  "receipts", "Receipt provenance/cost changed")
        for field in receipt.get("returned_field_paths", []):
            c.require(at(parsed["response"], field) is not None, "receipts", "Receipt claims absent public field")
    if finals:
        decoded_final, final_body, _ = decode_tool(finals[0]["response"])
        tool_error = bool(final_body and (final_body.get("isError") is True or final_body.get("isToolError") is True))
        if amir:
            final_id, final_context = at(decoded_final, "taskHandle"), at(decoded_final, "contextHandle")
            state = at(decoded_final, "a2aState")
        elif variant == "B3":
            final_id, final_context = at(decoded_final, "id"), at(decoded_final, "context_id")
            state = at(decoded_final, "state")
        else:
            final_id, final_context = at(decoded_final, "result.id"), at(decoded_final, "result.contextId")
            state = at(decoded_final, "result.status.state")
            tool_error = tool_error or bool(isinstance(decoded_final, dict) and decoded_final.get("error") is not None)
        normalized = state.removeprefix("TASK_STATE_").lower() if isinstance(state, str) else None
        goal = not tool_error and (final_id, final_context) == (task, context) and normalized == "completed"
        observation = r.get("observation", {})
        c.require(observation.get("goal_achieved") is goal, "observation", "Goal summary differs from final public receipt")
        if amir:
            c.require(observation.get("final_task_handle") == final_id and observation.get("final_context_handle") == final_context
                      and observation.get("final_state") == state, "observation", "Final opaque binding/state summary altered")
        else:
            c.require(observation.get("final_task_id") == final_id and observation.get("final_context_id") == final_context
                      and observation.get("final_state") == normalized, "observation", "Final native binding/state summary altered")
        c.expected((variant == "B4" and tool_error) or
                   (variant != "B4" and not tool_error and normalized == "input_required"
                    and (final_id, final_context) == (task, context)),
                   "final_public_outcome", "Final public receipt differs from prospective behavior")
    c.observations["selected_answer_attempts"] = len(answers)
    c.observations["final_bridge_read_attempts"] = len(finals)
    c.observations["complete_planned_attempt"] = bool(r.get("native_eligible") and initial_native
                                                      and len(answers) == len(finals) == 1 and e1)
    c.expected(c.observations["complete_planned_attempt"], "caller", "Prospective attempt is partial/unexecuted")


def _ingress(c, r, bridge_native, controls):
    requests = bridge_native + controls
    used = set()
    previous_complete = None
    for index, ingress in enumerate(r.get("ingress", [])):
        where = "ingress." + str(index)
        c.entity(ingress.get("body"), where + ".body", parse=False)
        start = c.time(ingress.get("started"), where + ".started")
        end = c.time(ingress.get("completed"), where + ".completed")
        c.require(start is not None and end is not None and end >= start, where, "Ingress time invalid")
        if previous_complete is not None:
            c.require(end >= previous_complete, where, "Ingress completion order changed")
        previous_complete = end
        candidates = []
        for number, parsed in enumerate(requests):
            if number in used:
                continue
            item = parsed["item"]
            request = item.get("request") or {}
            path = urlsplit(request.get("url", "")).path
            if (ingress.get("url") != path or ingress.get("method") != request.get("method")
                    or at(ingress, "body.sha256") != request.get("sha256")):
                continue
            delivered = lower_headers(ingress.get("headers"))
            supplied = lower_headers(request.get("headers"))
            if not all(delivered.get(k) == v for k, v in supplied.items()):
                continue
            if parsed["start"] is not None and start < parsed["start"]:
                continue
            if parsed["end"] is not None and end > parsed["end"]:
                continue
            if item.get("response") and ingress.get("response_status") != item["response"].get("status"):
                continue
            candidates.append(number)
        c.require(bool(candidates), where, "Ingress does not correlate exact supplied body/headers/status/timing")
        if candidates:
            used.add(candidates[0])
    for number, parsed in enumerate(requests):
        if parsed["item"].get("response"):
            c.require(number in used, "ingress", "HTTP response lacks paired server ingress")
    c.observations["paired_ingress"] = len(used)


def _lifecycle(c, r, data, native_ok, mcp, bridge_native, controls):
    life = data.get("lifecycle_events", [])
    previous = None
    for index, item in enumerate(life):
        observed = c.time(item.get("observed"), "lifecycle." + str(index) + ".observed")
        c.require(observed is not None and (previous is None or observed >= previous),
                  "lifecycle." + str(index), "Lifecycle event ordering altered")
        previous = observed
    spawn = [x for x in life if x.get("type") == "spawn"]
    exits = [x for x in life if x.get("type") == "exit"]
    c.require(len(spawn) <= 1 and all(x.get("role") == "bridge" for x in spawn),
              "lifecycle", "Unexpected child/custom wrapper started")
    if spawn:
        child = spawn[0]
        c.require(native_ok and child.get("pid") == at(r, "provenance.bridge_pid")
                  and child.get("command") == at(r, "provenance.bridge_command"),
                  "lifecycle", "Bridge child provenance/native eligibility changed")
        spawned = c.time(child.get("observed"), "lifecycle.spawn")
        n3 = controls.get("N3")
        if n3:
            c.require(spawned >= n3["end"], "lifecycle.spawn", "Bridge started before native controls")
        c.require(len(exits) == 1 and exits[0].get("pid") == child.get("pid") and exits[0].get("role") == "bridge",
                  "lifecycle", "Actual bridge exit absent/reused")
        cleanup = r.get("cleanup", [])
        c.require(len(cleanup) == 1 and cleanup[0].get("pid") == child.get("pid"),
                  "cleanup", "Cleanup did not target recorded child")
        if cleanup and exits:
            closed = c.time(exits[0].get("observed"), "lifecycle.exit")
            requested = c.time(cleanup[0].get("requested"), "cleanup.requested")
            c.require(cleanup[0].get("exit") == {k: exits[0][k] for k in ("code", "signal", "observed")},
                      "cleanup", "Cleanup exit differs from actual lifecycle")
            c.require(cleanup[0].get("already_exited") is True or closed >= requested, "cleanup", "Exit precedes requested shutdown")
            c.require(cleanup[0].get("normal_exit") == (exits[0].get("code") == 0 and exits[0].get("signal") is None),
                      "cleanup", "Normal-exit summary changed")
            if cleanup[0].get("normal_exit") is not True:
                c.expected(False, "cleanup", "Child cleanup failed; attempt retained")
            native_events = data.get("native_events", [])
            shutdown = [x for x in native_events if x.get("type") == "shutdown-request"]
            logger_exit = [x for x in native_events if x.get("type") == "logger-exit"]
            if cleanup[0].get("method"):
                c.require(len(shutdown) == 1 and shutdown[0].get("pid") == child.get("pid")
                          and shutdown[0].get("original_sigterm_listeners", 0) > 0,
                          "cleanup", "Original CLI shutdown handler not retained")
            c.require(len(logger_exit) == 1 and logger_exit[0].get("pid") == child.get("pid")
                      and logger_exit[0].get("code") == exits[0].get("code"), "cleanup", "Preload exit evidence differs")
        configs = [x for x in life if x.get("type") == "runtime-config-frozen-before-bridge-spawn"]
        c.require(len(configs) == 1 and c.time(configs[0].get("observed"), "runtime_config.time") <= spawned,
                  "runtime_config", "Dynamic configuration not frozen before spawn")
        config_record = r.get("pre_bridge_runtime_config", {})
        config = data.get("runtime_config", {})
        c.require(c.entity(data.get("runtime_config_entity"), "runtime_config_entity") == config,
                  "runtime_config_entity", "Decoded configuration differs from frozen bytes")
        c.require(config_record.get("sha256") == data.get("runtime_config_entity", {}).get("sha256")
                  and config.get("fixture_url") == r.get("fixture_endpoint")
                  and config.get("captured") == config_record.get("captured")
                  and config.get("bridge_profile") == r.get("configuration"),
                  "runtime_config", "Dynamic configuration bytes/endpoint changed")
        c.require(c.time(config_record.get("captured"), "runtime_config.captured") <= spawned,
                  "runtime_config", "Configuration captured after child spawn")
        supplied = config.get("supplied_environment", {})
        c.require(supplied.get("REFERENCE_RUN_ID") == r.get("run_id")
                  and supplied.get("REFERENCE_ROUTE_ID") == r.get("route_id")
                  and supplied.get("REFERENCE_PORT_ORIGIN") == r.get("fixture_endpoint")
                  and "A2A_TOKEN" not in supplied, "runtime_config", "Captured environment changed")
        if r.get("official_variant") in ("B3", "B4"):
            c.require(all(supplied.get(k) == v for k, v in
                          {"A2A_ALLOW_WRITES": "1", "A2A_CHANNEL": "0", "A2A_MAX_RETRIES": "0"}.items()),
                      "runtime_config", "mgcrea writes/retry/channel profile changed")
    else:
        c.require(not mcp and not bridge_native and not r.get("cleanup"), "lifecycle", "Exchanges invented without child")
    service = r.get("official_service", {})
    c.require(service.get("server_listening") is False, "official_service", "Service still listening or cleanup missing")
    if service.get("started"):
        start = c.time(service["started"], "official_service.started")
        freeze = c.time(at(r, "official_pre_execution.frozen"), "official_pre_execution.frozen")
        c.require(start >= freeze, "official_service", "Service imported/started before frozen evidence")
        if controls.get("N1"):
            c.require(controls["N1"]["start"] >= start, "N1", "Control precedes service startup")
    cleanup_time = c.time(service.get("cleanup_started"), "official_service.cleanup_started")
    close_time = c.time(service.get("closed"), "official_service.closed")
    c.require(close_time >= cleanup_time, "official_service.closed", "Service closure reordered")
    if controls.get("E1"):
        c.require(cleanup_time >= controls["E1"]["end"], "official_service", "Service closed before E1 finished")
    contexts = r.get("executor_task_contexts", [])
    c.require(isinstance(contexts, list) and all(isinstance(x, list) and len(x) == 2 for x in contexts),
              "executor_task_contexts", "Executor context evidence malformed")
    mapping = dict(contexts)
    for task_id, context in ((c.observations.get("native_control_task_id"),
                              at(r, "native_original.context_id")),
                             (c.observations.get("bridge_original_task_id"),
                              c.observations.get("bridge_original_context_id"))):
        if task_id:
            c.require(mapping.get(task_id) == context, "executor_task_contexts", "Executor original association altered")


def _snapshots(c, r, data):
    pre = r.get("pre_execution")
    official = r.get("official_pre_execution")
    if not pre or not official:
        c.expected(False, "pre_execution", "Setup did not establish complete frozen runtime")
        c.require(r.get("outcome") == "failed" and not r.get("native_eligible"),
                  "pre_execution", "Runtime observations without frozen environment")
        return
    c.require(pre == data.get("pre_ledger"), "pre_execution", "Standard pre-ledger was changed after freeze")
    c.require(official == data.get("official_pre_ledger"), "official_pre_execution", "Official pre-ledger changed after freeze")
    c.require(c.entity(data.get("pre_ledger_entity"), "pre_ledger_entity") == pre,
              "pre_ledger_entity", "Frozen standard ledger bytes differ from decoded ledger")
    c.require(c.entity(data.get("official_pre_ledger_entity"), "official_pre_ledger_entity") == official,
              "official_pre_ledger_entity", "Frozen official ledger bytes differ from decoded ledger")
    captured = c.time(pre.get("captured"), "pre_execution.captured")
    frozen = c.time(official.get("frozen"), "official_pre_execution.frozen")
    c.require(captured is not None and frozen is not None and frozen >= captured,
              "official_pre_execution.frozen", "Frozen ledgers were reordered")
    c.require(official.get("standard_pre_execution_ledger_sha256") == data.get("pre_ledger_entity", {}).get("sha256"),
              "official_pre_execution", "Standard pre-ledger byte hash altered")
    c.require(official.get("official_variant") == r.get("official_variant")
              and official.get("inherited_variant") == r.get("variant_id")
              and official.get("native_control_plan") == ["N1", "N2", "N3"]
              and official.get("origin_diagnostic_plan") == "E1",
              "official_pre_execution", "Frozen plans/variant changed")
    c.require(pre.get("source_checkout") == r.get("source_commit")
              and pre.get("dependency_lock_sha256") == LOCKS[r["route_id"]]
              and pre.get("port_dependency_lock_sha256") == LOCKS["amirk_a2a_to_mcp"],
              "pre_execution", "Bridge/source dependency pins changed")
    c.require(at(pre, "node.version") == "v22.13.0"
              and str(at(pre, "node.path")).lower() == r"c:\program files\nodejs\node.exe"
              and DIGEST.fullmatch(str(at(pre, "node.sha256"))) is not None,
              "pre_execution.node", "Node identity/hash missing")
    source_hashes = pre.get("source_hashes", {})
    required = {SPEC, DRIVER, CHECKER, PORT, "scripts/log-reference-http.mjs",
                "scripts/reference-mgcrea-v1.mjs", "scripts/official-handler-amir-v1.mjs",
                "external/source-lock.json", "external/sdk-http-control-v1/environment-lock.json",
                "docs/research/source-evidence/reference-continuation/port/change-map.json",
                "docs/research/source-evidence/reference-continuation/port/ATTRIBUTION.md"}
    c.require(required <= source_hashes.keys(), "pre_execution.source_hashes", "Required source/provenance/checker not frozen")
    c.require(at(pre, "specification.path") == SPEC
              and at(pre, "specification.sha256") == source_hashes.get(SPEC, {}).get("sha256")
              and source_hashes.get(PORT, {}).get("sha256") == PORT_HASH
              and source_hashes.get(CHECKER, {}).get("sha256") == CHECKER_IMPORT_SHA256,
              "pre_execution", "Frozen specification/executor changed")
    entities = data.get("source_entities", {})
    for filename, row in source_hashes.items():
        c.require(safe_relative(filename) and safe_relative(row.get("snapshot")), "source_hashes", "Unsafe source/snapshot path")
        saved = entities.get(filename)
        if c.require(isinstance(saved, dict), filename, "Source bytes missing from archive material"):
            c.entity(saved, filename, parse=False)
            c.require(saved.get("sha256") == row.get("sha256") and saved.get("bytes") == row.get("bytes"),
                      filename, "Frozen source snapshot byte hash/count differs")
    c.require(set(r.get("post_source_sha256", {})) == set(source_hashes)
              and all(r["post_source_sha256"].get(k) == row.get("sha256") for k, row in source_hashes.items())
              and not r.get("post_source_changes") and not r.get("post_source_errors"),
              "post_source_sha256", "Source changed or post-source byte closure incomplete")
    deps = pre.get("installed_runtime_dependencies", [])
    lock_entity = entities.get("external/source-lock.json")
    if lock_entity:
        source_lock = strict_json(base64.b64decode(lock_entity["base64"]))
        pinned_source = next((x for x in source_lock.get("sources", []) if x.get("id") == r.get("route_id")), {})
        c.require(pinned_source.get("commit") == r.get("source_commit")
                  and at(pinned_source, "dependency_lock.sha256") == LOCKS[r["route_id"]]
                  and at(pinned_source, "license.spdx") == ("Apache-2.0" if r["official_variant"] in ("B1", "B2") else "MIT")
                  and pinned_source.get("runtime_dependencies") == {x.get("name"): x.get("version") for x in deps},
                  "source_lock", "Pinned license/direct dependency versions differ from frozen source evidence")
    sdk = next((x for x in deps if x.get("name") == "@a2a-js/sdk"), {})
    c.require(sdk.get("version") == ("1.1.0" if r["official_variant"] in ("B1", "B2") else "1.3.0"),
              "dependencies", "Bridge SDK version changed")
    port_sdk = next((x for x in pre.get("port_runtime_dependencies", []) if x.get("name") == "@a2a-js/sdk"), {})
    c.require(port_sdk.get("version") == "1.1.0", "dependencies", "Executor SDK version changed")
    trees = official.get("trees", [])
    sources = [x.get("source") for x in trees]
    required_trees = {"external/sdk-http-control-v1/node_modules"}
    required_trees.update(x["manifest"]["root"] for x in deps + pre.get("port_runtime_dependencies", []))
    c.require(len(sources) == len(set(sources)) and set(sources) == required_trees,
              "official_pre_execution.trees", "Complete direct/HTTP dependency coverage changed")
    manifests = [pre.get("bridge_source_manifest", {}), pre.get("bridge_dist_manifest", {})]
    bridge_directory = "external/a2a-to-mcp" if r["official_variant"] in ("B1", "B2") else "external/mcp-a2a"
    c.require(manifests[0].get("root") == bridge_directory + "/src"
              and manifests[1].get("root") == bridge_directory + "/dist",
              "bridge_manifests", "Source/dist snapshot roots changed")
    for tree in trees:
        manifests.append({"root": tree.get("source"), "snapshot_root": tree.get("snapshot"),
                          "entries": tree.get("entries"), "entries_sha256": tree.get("entries_sha256")})
    c.require(r.get("official_post_bridge_trees") == [
        {"root": pre[key]["root"], "entries_sha256": pre[key]["entries_sha256"]}
        for key in ("bridge_source_manifest", "bridge_dist_manifest")],
        "official_post_bridge_trees", "Bridge source/dist changed or post-check missing")
    for manifest in manifests:
        entries = manifest.get("entries") or []
        c.require(bool(entries) and sha(compact(entries)) == manifest.get("entries_sha256"),
                  "trees", "Tree entry ledger checksum differs")
        expected = {}
        for row in entries:
            c.require(safe_relative(row.get("path")) and integer(row.get("bytes")) and row["bytes"] >= 0
                      and DIGEST.fullmatch(str(row.get("sha256"))) is not None,
                      "trees.entries", "Malformed tree entry")
            c.require(row.get("path") not in expected, "trees.entries", "Tree file duplicated")
            expected[row["path"]] = {"bytes": row["bytes"], "sha256": row["sha256"]}
        actual = data.get("tree_inventory", {}).get(manifest.get("snapshot_root"))
        c.require(actual == expected, "trees." + str(manifest.get("root")),
                  "Frozen full tree snapshot missing, altered, or contains extra files")
    tree_by_source = {x.get("source"): x for x in trees}
    for dep in deps + pre.get("port_runtime_dependencies", []):
        manifest = dep["manifest"]
        tree = tree_by_source.get(manifest["root"], {})
        c.require(manifest.get("entries") == tree.get("entries")
                  and manifest.get("entries_sha256") == tree.get("entries_sha256"),
                  "dependencies", "Direct dependency manifest differs from preserved full tree")
    posts = r.get("official_post_trees", [])
    c.require(len(posts) == len(trees) and {x.get("source") for x in posts} == set(sources)
              and all(x.get("entries_sha256") == tree_by_source[x["source"]]["entries_sha256"] and not x.get("error")
                      for x in posts), "official_post_trees", "Runtime dependency changed or post-check missing")
    env_entity = entities.get("external/sdk-http-control-v1/environment-lock.json")
    if env_entity:
        env = strict_json(base64.b64decode(env_entity["base64"]))
        c.require(env.get("copied_sdk_version") == "1.1.0" and env.get("network_requests") == 0,
                  "official_environment", "Official environment pin changed")
        http_tree = tree_by_source.get("external/sdk-http-control-v1/node_modules", {})
        selected = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in http_tree.get("entries", [])}
        c.require(bool(env.get("installed_files")), "official_environment", "Installed environment file ledger absent")
        for row in env.get("installed_files", []):
            path = row.get("path", "")
            if path.startswith("node_modules/"):
                c.require(selected.get(path[len("node_modules/"):]) == {"bytes": row["bytes"], "sha256": row["sha256"]},
                          "official_environment", "HTTP environment differs from prior installed lock")
    c.observations["source_snapshot_count"] = len(source_hashes)
    c.observations["complete_tree_snapshot_count"] = len(manifests)


def _file_entity(path):
    data = path.read_bytes()
    return {"raw": data.decode("utf-8"), "base64": base64.b64encode(data).decode("ascii"),
            "bytes": len(data), "sha256": sha(data)}


def check_archive(root: Path, report_path: str):
    """Read only an archive, supporting either preserved workspace paths or a
    copied attempt directory. Never resolve a snapshot through the live workspace.
    """
    root = Path(root).resolve()
    errors = []
    report_file = (root / report_path).resolve()
    if not report_file.is_relative_to(root):
        return {"valid": False, "complete": False, "validation_errors": [{"path": report_path, "reason": "Report escapes archive"}]}
    try:
        report = strict_json(report_file.read_text(encoding="utf-8-sig"))
        prefixes = []
        for value in (at(report, "private_sidecars.process_lifecycle"),
                      at(report, "private_sidecars.native_http")):
            if value:
                prefixes.append(str(PurePosixPath(value).parent))

        def resolve(recorded):
            if not safe_relative(recorded):
                raise ValueError("Unsafe recorded path: " + str(recorded))
            candidates = [root / recorded]
            for prefix in prefixes:
                if recorded == prefix or recorded.startswith(prefix + "/"):
                    suffix = recorded[len(prefix):].lstrip("/")
                    candidates.append(report_file.parent / suffix)
            for candidate in candidates:
                path = candidate.resolve()
                if path.is_relative_to(root) and path.exists():
                    return path
            raise FileNotFoundError("Preserved archive file missing: " + recorded)

        def optional_json(name):
            path = report_file.parent / name
            if not path.exists():
                return None, None
            entity = _file_entity(path)
            return strict_json(entity["raw"]), entity

        def sidecar(key, lines=False):
            recorded = at(report, "private_sidecars." + key)
            if not recorded:
                return [] if lines else {}
            path = resolve(recorded)
            raw = path.read_text(encoding="utf-8-sig")
            return [strict_json(line) for line in raw.splitlines() if line.strip()] if lines else strict_json(raw)

        pre, pre_entity = optional_json("pre-execution-ledger.json")
        official, official_entity = optional_json("official-pre-execution-ledger.json")
        data = {"report": report, "native_events": sidecar("native_http", True),
                "lifecycle_events": sidecar("process_lifecycle", True),
                "diagnostics": sidecar("diagnostics"),
                "pre_ledger": pre, "pre_ledger_entity": pre_entity,
                "official_pre_ledger": official, "official_pre_ledger_entity": official_entity,
                "source_entities": {}, "tree_inventory": {}}
        for filename, row in (report.get("pre_execution") or {}).get("source_hashes", {}).items():
            try:
                data["source_entities"][filename] = _file_entity(resolve(row["snapshot"]))
            except Exception as error:
                errors.append({"path": filename, "reason": str(error)})
        manifests = [(report.get("pre_execution") or {}).get(k, {})
                     for k in ("bridge_source_manifest", "bridge_dist_manifest")]
        manifests += [{"snapshot_root": x.get("snapshot")} for x in (official or {}).get("trees", [])]
        for manifest in manifests:
            snapshot = manifest.get("snapshot_root")
            if not snapshot:
                continue
            try:
                directory = resolve(snapshot)
                inventory = {}
                for file in directory.rglob("*"):
                    if file.is_file():
                        actual = file.resolve()
                        if not actual.is_relative_to(root):
                            raise ValueError("Tree symlink escapes archive")
                        payload = file.read_bytes()
                        inventory[file.relative_to(directory).as_posix()] = {"bytes": len(payload), "sha256": sha(payload)}
                data["tree_inventory"][snapshot] = inventory
            except Exception as error:
                errors.append({"path": snapshot, "reason": str(error)})
        if report.get("pre_bridge_runtime_config"):
            path = resolve(report["pre_bridge_runtime_config"]["path"])
            data["runtime_config_entity"] = _file_entity(path)
            data["runtime_config"] = strict_json(data["runtime_config_entity"]["raw"])
        result = check_records(data)
        result["validation_errors"][:0] = errors
        result["valid"] = result["valid"] and not errors
        result["complete"] = result["complete"] and not errors
        result["expected_outcome_observed"] = result["expected_outcome_observed"] and not errors
        result["archive"] = str(root)
        result["report_path"] = report_path
        result["report_sha256"] = sha(report_file.read_bytes())
        return result
    except Exception as error:
        return {"schema_version": "official-handler-bridge-check/1", "valid": False, "complete": False,
                "partial": True, "expected_outcome_observed": False,
                "validation_errors": [{"path": report_path, "reason": type(error).__name__ + ": " + str(error)}],
                "expectation_deviations": [], "records": {}, "archive": str(root)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("report_path", nargs="?", default="runtime.json")
    parser.add_argument("--include-records", action="store_true", help="Emit mutation-ready decoded records")
    args = parser.parse_args()
    result = check_archive(args.root, args.report_path)
    if not args.include_records:
        result.pop("records", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(not result.get("valid"))


if __name__ == "__main__":
    raise SystemExit(main())

