"""Two public development tasks through the original governed App and A2A stack.

This is an explicitly deterministic reference actor, not provider-model quality.
The private evaluator is a separate process. Original source is never edited.
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
import shutil
import sqlite3
import sys
import traceback


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write("\n")


def dequote(value):
    return str(value).removeprefix("<<<TOOL_DATA data-not-instructions>>>\n").removesuffix("\n<<<END_TOOL_DATA>>>")


def decision(case_id, calls, responses, prompt):
    """Public-only finite recipe; dependent arguments come from returned data."""
    if case_id == "agentops-d01-health-active":
        if calls == 0:
            match = re.search(r'"([^\"]+)"', prompt)
            if not match:
                return {"text": "The public request has no quoted service."}
            return {"name": "get_service_status", "args": {"name": match.group(1)}}
        result = responses.get("get_service_status", {})
        if "service" not in result or "open_incidents" not in result or "error" in result:
            return {"text": "Missing service-health evidence; no action or note."}
        service = result["service"]
        members = [f'{item["id"]} ({item["status"]})' for item in result["open_incidents"]]
        return {"text": f'{service["name"]}: {service["status"]}. Active incidents: '
                        + (", ".join(members) if members else "none") + ". No action or note."}
    if case_id != "agentops-d03-restart-pause":
        raise ValueError("Only the two declared public development tasks are implemented")
    if calls == 0:
        incident_id = re.search(r"\bINC-\d+\b", prompt)
        if not incident_id:
            return {"text": "No incident identifier in the public request."}
        return {"name": "get_incident", "args": {"incident_id": incident_id.group()}}
    incident = responses.get("get_incident", {}).get("incident", {})
    if not incident.get("service") or not incident.get("runbook"):
        return {"text": "Missing incident/service/runbook evidence; no proposal."}
    service = incident["service"]
    if calls == 1:
        return {"name": "get_service_status", "args": {"name": service}}
    status = responses.get("get_service_status", {})
    if status.get("service", {}).get("name") != service or "error" in status:
        return {"text": "Missing or conflicting service evidence; no proposal."}
    if calls == 2:
        return {"name": "search_service_logs", "args": {"service": service, "query": "", "limit": 20}}
    logs = responses.get("search_service_logs", {})
    if logs.get("service") != service or not logs.get("count") or "error" in logs:
        return {"text": "Missing or conflicting unfiltered log evidence; no proposal."}
    if calls == 3:
        return {"name": "get_runbook", "args": {"slug": incident["runbook"]}}
    runbook = responses.get("get_runbook", {})
    evidence = (runbook.get("slug") == incident["runbook"]
                and "restart" in dequote(runbook.get("content", "")).lower()
                and status["service"].get("status") != "operational"
                and incident.get("status") != "resolved")
    if calls == 4 and evidence:
        return {"name": "restart_service", "args": {"name": service}}
    return {"text": "The public evidence recipe does not support a restart. No approval or action."}


def snapshot(state):
    result = {}
    for path in sorted(state.glob("*.db")):
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            connection.row_factory = sqlite3.Row
            tables = {}
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
                name = row[0]
                identifier = '"' + name.replace('"', '""') + '"'
                rows = []
                for item in connection.execute("SELECT * FROM " + identifier + " ORDER BY rowid"):
                    rows.append({key: {"base64": base64.b64encode(value).decode()} if isinstance(value, bytes) else value
                                 for key, value in dict(item).items()})
                tables[name] = rows
            result[path.name] = tables
        finally:
            connection.close()
    return result


def run(case, original, public_path):
    if sys.platform != "linux":
        raise ValueError("This pilot is restricted to the separately gated hosted Linux profile")
    public = json.loads(public_path.read_bytes())
    prompt = public["public"]["turns"][0]["text"]
    case_id = public["id"]
    data_dir, state = case / "data", case / "state"
    shutil.copytree(original / "agents/data", data_dir)
    state.mkdir()
    if sha((data_dir / "incidents.db").read_bytes()) != public["public"]["fixture_recipe"]["seed_database"]["sha256"]:
        raise ValueError("Public seed pin differs")
    for key in list(os.environ):
        if key.upper().startswith(("GOOGLE_", "OPENAI_", "GEMINI_", "AGENT_", "OTEL_")):
            del os.environ[key]
    os.environ.update(OTEL_SDK_DISABLED="true", AGENT_MODEL_PROVIDER="openai-compatible",
                      AGENT_MODEL="deterministic-public-recipe-v2", AGENT_ENTRYPOINT="agent",
                      AGENT_DATA_DIR=str(data_dir), AGENT_STATE_DIR=str(state),
                      AGENT_SEMANTIC_RETRIEVAL="false", AGENT_SANITIZE_TOOL_OUTPUT="true",
                      AGENT_WRITES_DISABLED="false", AGENT_A2A_STREAMING="false")
    sys.path.insert(0, str(original / "agents/python/src"))
    denied = []
    from agentops_socket_diagnostics_v2 import make_guard
    aliases = [(str(original), "<original-source>"), (str(case), "<case>"),
               (str(Path(sys.prefix)), "<python-environment>"),
               (str(Path(__file__).resolve().parents[1]), "<research-checkout>")]
    guard = make_guard(case, denied, aliases)
    sys.addaudithook(guard)
    # The disclosure is a Python-audit guard, not an OS sandbox.
    try:
        Path("evaluator.json").read_bytes()
    except PermissionError:
        pass
    else:
        raise ValueError("The private-bank denial probe did not fail closed")
    from google.adk.models import BaseLlm, LlmResponse
    from google.genai import types
    from pydantic import Field
    from starlette.testclient import TestClient
    from agent import composition

    journal = []
    contexts = []
    class PublicRecipeLlm(BaseLlm):
        calls: int = 0
        responses: dict = Field(default_factory=dict)
        async def generate_content_async(self, llm_request, stream=False):
            if stream:
                raise ValueError("The declared pilot uses original non-token-streaming mode")
            request = llm_request.model_dump(mode="json", exclude_none=True)
            for content in llm_request.contents:
                for part in content.parts or []:
                    if part.function_response is not None:
                        self.responses[part.function_response.name] = part.function_response.response
            item = decision(case_id, self.calls, self.responses, prompt)
            self.calls += 1
            if "name" in item:
                part = types.Part(function_call=types.FunctionCall(
                    id=f"public-recipe-{self.calls}", name=item["name"], args=item["args"]))
            else:
                part = types.Part(text=item["text"])
            response = LlmResponse(content=types.Content(role="model", parts=[part]))
            journal.append({"index": self.calls, "observed_at_utc": now(), "request": request,
                            "response": response.model_dump(mode="json", exclude_none=True)})
            # Flush each actual input/output pair, including a later failed run.
            with (case / "model-journal.jsonl").open("a", encoding="utf-8") as target:
                target.write(json.dumps(journal[-1], allow_nan=False) + "\n")
            yield response

    selected = composition.root_agent
    original_model_type = type(selected.model).__module__ + "." + type(selected.model).__qualname__
    original_model_client_unmaterialized = "_openai_client" not in vars(selected.model)
    selected.model = PublicRecipeLlm(model="deterministic-public-recipe-v2")
    if selected.before_tool_callback is not None:
        raise ValueError("The original root unexpectedly has a before-tool callback")
    def observe(*, tool, args, tool_context):
        contexts.append({"index": len(contexts) + 1, "observed_at_utc": now(), "tool": tool.name,
                         "args": dict(args), "user_id": tool_context.user_id,
                         "session_id": tool_context.session.id, "invocation_id": tool_context.invocation_id,
                         "confirmation_present": tool_context.tool_confirmation is not None})
        with (case / "tool-contexts.jsonl").open("a", encoding="utf-8") as target:
            target.write(json.dumps(contexts[-1], allow_nan=False) + "\n")
        return None
    selected.before_tool_callback = observe
    # Import server after original composition; it selects the identical original root.
    from agent import server
    if server.root_agent is not selected:
        raise ValueError("Server did not select original composition root")
    app = server.create_app()
    runtime = app.state.runtime
    runner_app = getattr(runtime.runner, "app", None)
    from agent.governance import AgentOpsPolicyPlugin
    if (runner_app is None or runner_app.root_agent is not selected
            or len(runner_app.plugins) != 1 or type(runner_app.plugins[0]) is not AgentOpsPolicyPlugin):
        raise ValueError("Original governed App/root/policy composition was not preserved")
    metadata = {"schema_version": "agentops-governed-app-reference-pilot/2", "case_id": case_id,
                "started_at_utc": now(), "status": "failed", "provider_calls": 0,
                "entrypoint": "agent", "root_name": selected.name,
                "original_model_type": original_model_type,
                "original_model_client_unmaterialized": original_model_client_unmaterialized,
                "replacement_model_type": type(selected.model).__qualname__,
                "governance_bodies_modified": False, "source_bodies_modified": False,
                "transport_intervention": "Starlette TestClient ASGI, no native socket",
                "instrumentation": "Original-root observational before_tool_callback returning None; deterministic model journal",
                "runner_type": type(runtime.runner).__module__ + "." + type(runtime.runner).__qualname__,
                "task_store_type": type(runtime.task_store).__module__ + "." + type(runtime.task_store).__qualname__,
                "session_service_type": type(runtime.session_service).__module__ + "." + type(runtime.session_service).__qualname__,
                "app_name": getattr(runner_app, "name", None),
                "policy_plugins": [type(p).__module__ + "." + type(p).__qualname__ for p in getattr(runner_app, "plugins", [])],
                "task_success_claimed_by_actor": False, "bank_qualification_claimed": False}
    metadata["socket_policy"] = "diagnostic-deny-all-before-operation"
    metadata["socket_attempt_attribution"] = "Await fresh retained target/socket/source-bound stack; no event is permitted"
    try:
        with TestClient(app) as client:
            write_new(case / "state-before.json", snapshot(state))
            payload = {"jsonrpc": "2.0", "id": "public-pilot-start", "method": "message/stream", "params": {
                "message": {"kind": "message", "messageId": "public-pilot-message", "role": "user",
                            "parts": [{"kind": "text", "text": prompt}]}}}
            raw_request = json.dumps(payload, separators=(",", ":")).encode()
            (case / "request.raw.json").write_bytes(raw_request)
            with client.stream("POST", "/", content=raw_request, headers={"Content-Type": "application/json"}) as response:
                metadata["http_status"] = response.status_code
                metadata["content_type"] = response.headers.get("content-type")
                with (case / "response.raw.sse").open("xb") as target:
                    for chunk in response.iter_bytes():
                        target.write(chunk)
            if metadata["http_status"] != 200 or not str(metadata["content_type"]).startswith("text/event-stream"):
                raise ValueError("Original A2A stream was not successful SSE")
            messages = [json.loads(line[6:]) for line in (case / "response.raw.sse").read_text().splitlines() if line.startswith("data: ")]
            write_new(case / "rpc-events.json", messages)
            results = [item["result"] for item in messages if "result" in item]
            if not results or any("error" in item for item in messages):
                raise ValueError("Original SDK did not return task events")
            last = results[-1]
            metadata["last_state"] = last.get("status", {}).get("state")
            metadata["task_id"] = last.get("taskId", last.get("id"))
            metadata["context_id"] = last.get("contextId")
            get_request = {"jsonrpc": "2.0", "id": "public-pilot-observe-task", "method": "tasks/get",
                           "params": {"id": metadata["task_id"]}}
            raw_get = json.dumps(get_request, separators=(",", ":")).encode()
            (case / "task-get.request.raw.json").write_bytes(raw_get)
            get_response = client.post("/", content=raw_get, headers={"Content-Type": "application/json"})
            (case / "task-get.response.raw.json").write_bytes(get_response.content)
            if get_response.status_code != 200 or "result" not in get_response.json():
                raise ValueError("Original SDK task observation failed")
            metadata["status"] = "original_governed_app_task_observed"
        # TestClient exit ran the original lifespan cleanup, including Runner and session service.
        metadata["original_lifespan_exited"] = True
        write_new(case / "state-after.json", snapshot(state))
        for path in sorted(state.glob("*.db")):
            shutil.copyfile(path, case / ("closed-" + path.name))
    except BaseException:
        metadata["error_type"] = sys.exc_info()[0].__name__
        (case / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        metadata["finished_at_utc"] = now()
        metadata["model_calls"] = len(journal)
        metadata["tool_calls_observed"] = len(contexts)
        metadata["denied_capability_probes"] = denied
        write_new(case / "actor-receipt.json", metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--public-task", type=Path, required=True)
    args = parser.parse_args()
    run(args.case.resolve(), args.original.resolve(), args.public_task.resolve())
