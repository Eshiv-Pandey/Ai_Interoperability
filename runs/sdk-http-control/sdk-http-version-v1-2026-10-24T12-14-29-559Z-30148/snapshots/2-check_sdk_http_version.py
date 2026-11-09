"""Separate checker for pinned official-handler HTTP controls and archives.

No SDK/driver import. Public raw requests establish identity; private ingress
and unchanged-executor diagnostics only verify transport/rejection boundaries.
This is integrating-assistant software logic, not independent human review.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(raw):
    def unique(pairs):
        value = {}
        for name, item in pairs:
            require(name not in value, "Duplicate JSON key")
            value[name] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inside(root, relative):
    require(isinstance(relative, str) and bool(relative) and not Path(relative).is_absolute(), "Invalid evidence path")
    target = (root / relative).resolve()
    require(target.is_relative_to(root.resolve()), "Evidence path escapes archive")
    return target


def entity(value):
    raw = value["raw"].encode("utf-8")
    require(base64.b64decode(value["base64"], validate=True) == raw
            and value["bytes"] == len(raw) and value["sha256"] == digest(raw), "Raw entity disagreement")
    if "json" in value:
        require(decode(value["raw"]) == value["json"], "Parsed JSON differs from raw bytes")
    return raw


def check_semantics(report):
    require(report["schema_version"] == "sdk-http-version-control/1"
            and report["kind"] == "SOFTWARE/SDK HTTP CONTROL USING DISCLOSED CAROL EXECUTOR", "Wrong evidence class")
    require(report["default_context_builder"] is True and report["legacy_compatibility"] is False, "Handler policy altered")
    require(report["outcome"] == "recorded-once" and report["exit_code"] == 0
            and report["cleanup"]["server_listening"] is False and "error" not in report["cleanup"], "Nonterminal or failed control")
    require(report["model_calls"] == report["remote_network_requests"] == report["child_processes_started"] == 0, "Control boundary violated")
    expected = [(None, None), ("", None), ("1.0", None), ("0.3", None), (None, "1.0"),
                ("1.0", "1.0"), ("1.0", None), ("1.0", None), (None, None), (None, "1.0")]
    require(len(report["cases"]) == len(report["case_plan"]) == len(report["ingress"]) == 10, "Missing or extra actual case")
    require(report["costs"] == {"http_requests": 10, "server_ingress_requests": 10, "child_processes": 0,
                                "model_calls": 0, "remote_network_requests": 0}, "Wrong actual request costs")
    interface = report["card"]["supportedInterfaces"]
    require(len(interface) == 1 and interface[0]["protocolVersion"] == "1.0"
            and interface[0]["protocolBinding"] == "JSONRPC" and interface[0]["url"] == report["endpoint"], "Wrong 1.0-only interface")
    original_response = decode(report["cases"][2]["response"]["raw"])["result"]["task"]
    original = {"task_id": original_response["id"], "context_id": original_response["contextId"], "public_source_case": "H3"}
    require(report["original"] == original and all(isinstance(original[k], str) and original[k] for k in ("task_id", "context_id")), "Public original binding mismatch")
    initial_text = '{"action":"shuffle","history":[{"guess":25,"response":"Go higher"}]}'
    message_ids = set()
    contexts = []
    conclusions = []
    for index, (record, planned, ingress, versions) in enumerate(zip(report["cases"], report["case_plan"], report["ingress"], expected), 1):
        case_id = f"H{index}"
        require(record["case_id"] == planned["case_id"] == case_id
                and record["executed"] is True and record["attempt"] == 1 and "error" not in record, "Wrong case order or execution")
        require((planned["version_header"], planned["version_query"]) == versions, "Wrong frozen version plan")
        request, response = record["request"], record["response"]
        request_raw = entity(request)
        entity(response)
        require(entity(ingress["body"]) == request_raw and ingress["method"] == request["method"] == "POST", "Server ingress body differs")
        url = urlparse(request["url"])
        require(url.hostname == "127.0.0.1" and url.path == "/a2a"
                and ingress["url"] == url.path + ("?" + url.query if url.query else ""), "Unexpected endpoint or query")
        headers = {k.lower(): v for k, v in request["headers"].items()}
        header, query = versions
        require(headers == {"content-type": "application/json", **({"a2a-version": header} if header is not None else {})}, "Actual headers differ from plan")
        require(("a2a-version" in ingress["headers"]) is (header is not None)
                and ingress["headers"].get("a2a-version") == header, "Server version header differs")
        require(parse_qs(url.query, keep_blank_values=True) == ({"A2A-Version": [query]} if query is not None else {}), "Actual query differs from plan")
        require(response["status"] == ingress["response_status"] == 200, "Unexpected HTTP status")
        body, reply = request["json"], response["json"]
        require(body["jsonrpc"] == reply["jsonrpc"] == "2.0" and body["id"] == reply["id"] == index, "RPC association mismatch")
        method = "SendMessage" if index <= 7 else "GetTask"
        require(body["method"] == planned["method"] == method, "Wrong protocol operation")
        if method == "SendMessage":
            params = body["params"]
            message = params["message"]
            require(message["role"] == "ROLE_USER" and message["messageId"] not in message_ids, "Wrong or reused message ID")
            message_ids.add(message["messageId"])
            require(message["parts"] == [{"text": "Well done" if index == 7 else initial_text, "mediaType": "text/plain"}]
                    and params["configuration"] == {"acceptedOutputModes": ["text/plain"]}, "Wrong application input")
            if index == 7:
                require(message["taskId"] == original["task_id"] and message["contextId"] == original["context_id"]
                        and message["referenceTaskIds"] == [original["task_id"]], "Answer uses nonpublic or wrong binding")
            else:
                require(all(k not in message for k in ("taskId", "contextId", "referenceTaskIds")), "Initial request has injected binding")
        else:
            require(body["params"] == {"id": original["task_id"], "historyLength": 10}, "GetTask uses wrong original task")
        if index in (1, 2, 4, 5, 9, 10):
            require("result" not in reply and reply["error"]["code"] == -32009
                    and reply["error"]["data"][0]["reason"] == "VERSION_NOT_SUPPORTED", "Expected version rejection absent")
            require("0.3" in reply["error"]["message"], "Wrong effective rejected version")
            require(record["executor_task_contexts"] == contexts, "Rejected request reached new application task")
            conclusions.append({"case_id": case_id, "outcome": "observed-version-rejection"})
        else:
            require("error" not in reply, "Positive native control failed")
            task = reply["result"]["task"] if method == "SendMessage" else reply["result"]
            if index in (3, 6):
                require(task["status"]["state"] == "TASK_STATE_INPUT_REQUIRED", "Initial source-valid pending control failed")
                require(len(task["artifacts"]) == 1 and len(task["artifacts"][0]["parts"]) == 1
                        and decode(task["artifacts"][0]["parts"][0]["text"]) == [{"guess": 25, "response": "Go higher"}], "Invalid initial application artifact")
                require(task["id"] not in [x[0] for x in contexts], "Positive initial reused task")
                contexts.append([task["id"], task["contextId"]])
            else:
                require(task["id"] == original["task_id"] and task["contextId"] == original["context_id"]
                        and task["status"]["state"] == "TASK_STATE_COMPLETED", "Original task/context not completed")
            require(record["executor_task_contexts"] == contexts, "Executor association diagnostics disagree")
            conclusions.append({"case_id": case_id, "outcome": "observed-native-positive"})
    return conclusions


def check_archive(root, relative_report):
    filename = inside(root, relative_report)
    report = decode(filename.read_text(encoding="utf-8"))
    cases = check_semantics(report)
    require(decode((filename.parent / "pre-execution-ledger.json").read_text(encoding="utf-8")) == report["pre_execution"], "Frozen ledger differs")
    require(report["source_hashes"] == report["pre_execution"]["source_hashes"]
            and report["dependency_trees"] == report["pre_execution"]["dependency_trees"], "Top-level evidence differs from ledger")
    preserved = 0
    for before, after in zip(report["source_hashes"], report["post_sources"]):
        source = inside(root, before["snapshot"])
        require(digest(source.read_bytes()) == before["sha256"] and source.stat().st_size == before["bytes"], "Changed source snapshot")
        require(after == {"path": before["path"], "sha256": before["sha256"]}, "Original source changed during execution")
        preserved += 1
    require(len(report["source_hashes"]) == len(report["post_sources"]), "Missing post-source result")
    require(len(report["dependency_trees"]) == len(report["post_trees"]) == 3, "Missing dependency tree")
    for before, after in zip(report["dependency_trees"], report["post_trees"]):
        directory = inside(root, before["snapshot"])
        paths = [e["path"] for e in before["entries"]]
        require(len(paths) == len(set(paths)) and set(paths) == {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}, "Added/removed snapshot file")
        for entry in before["entries"]:
            source = inside(directory, entry["path"])
            require(digest(source.read_bytes()) == entry["sha256"] and source.stat().st_size == entry["bytes"], "Changed dependency bytes")
            preserved += 1
        encoded = json.dumps(before["entries"], ensure_ascii=False, separators=(",", ":")).encode()
        require(digest(encoded) == before["entries_sha256"]
                and after == {"source": before["source"], "entries_sha256": before["entries_sha256"]}, "Dependency manifest changed")
    require(report["post_node_sha256"] == report["node"]["sha256"] and report["node"]["version"] == "v22.13.0", "Node identity changed")
    event_file = inside(root, report["events"]["path"])
    require(digest(event_file.read_bytes()) == report["events"]["sha256"], "Changed event bytes")
    events = [decode(line) for line in event_file.read_text(encoding="utf-8").splitlines()]
    require(events[0]["type"] == "ledger-frozen-before-imports"
            and events[0]["sha256"] == digest((filename.parent / "pre-execution-ledger.json").read_bytes()), "Ledger event differs")
    completed = [e["case"] for e in events if e["type"] == "case-completed"]
    ingress = [e["ingress"] for e in events if e["type"] == "server-ingress-completed"]
    require(completed == report["cases"] and ingress == report["ingress"] and events[-1]["type"] == "server-closed", "Event record disagreement")
    return {"valid": True, "cases": cases, "preserved_files_checked": preserved,
            "report_sha256": digest(filename.read_bytes()),
            "claim_limit": "Pinned official-handler HTTP control and archive fidelity only; no novelty or human approval"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = check_archive(args.root.resolve(), args.report)
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    result["checker_sha256"] = digest(Path(__file__).read_bytes())
    with inside(args.root.resolve(), args.output).open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
