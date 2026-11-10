"""Original 34 public candidate reference attempts through original Apps and SDK.

The model is a disclosed deterministic reference actor. No provider-quality,
held-out, human-gold or admission-to-application claim follows from these runs.
"""
from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

from agentops_governed_app_pilot_v2 import now, sha, snapshot, write_new
from agentops_public_reference_v4 import IDS, choose


def exported_report_harness(server, exported_app):
    """Assemble the original runtime around the actual natively discovered App.

    This disclosed assembly avoids create_app(), which constructs a new App.
    No original function binding, policy or factory body is replaced.
    """
    settings = server.settings
    database_url = f"sqlite+aiosqlite:///{settings.state_dir / 'runtime.db'}"
    session_service = server._A2ASessionService(db_url=database_url, pool_size=1,
        max_overflow=0, connect_args={"timeout": 30})
    runner = server._SessionSerializingRunner(app=exported_app, session_service=session_service)
    runtime = server.Runtime(runner=runner, session_service=session_service,
        task_engine=session_service.db_engine,
        task_store=server.DatabaseTaskStore(engine=session_service.db_engine))

    @asynccontextmanager
    async def lifespan(_):
        try:
            server.recover_interrupted_restore(settings.state_dir)
            server._preflight_existing_runtime_store(settings.state_dir / "runtime.db")
            server.prepare_runtime_database()
            await runtime.session_service.prepare_tables()
            await runtime.task_store.initialize()
            yield
        finally:
            await runtime.close()

    app = server.to_a2a(exported_app.root_agent, host=settings.a2a_host,
        port=settings.a2a_port, protocol=settings.a2a_protocol,
        agent_card=server.agent_card, runner=runner, task_store=runtime.task_store,
        lifespan=lifespan, agent_executor_factory=server._agent_executor)
    app.state.runtime = runtime
    app.add_middleware(server.VerifiedIdentityMiddleware)
    app.add_middleware(server.RequestTraceMiddleware)
    healthz, livez = server._health_routes()
    app.add_route("/healthz", healthz, methods=["GET"])
    app.add_route("/livez", livez, methods=["GET"])
    return app


def capture_turn(client, case, prompt, turn, previous):
    directory = case / f"turn-{turn}"
    directory.mkdir()
    message = {"kind": "message", "messageId": f"reference-v4-message-{turn}",
        "role": "user", "parts": [{"kind": "text", "text": prompt}]}
    if previous:
        if previous["last_state"] != "completed" or not previous["context_id"]:
            raise ValueError("A same-session second turn requires actual completed first task/context")
        # A new SDK task uses the real prior context, deliberately omitting taskId.
        message["contextId"] = previous["context_id"]
    payload = {"jsonrpc": "2.0", "id": f"reference-v4-start-{turn}",
        "method": "message/stream", "params": {"message": message}}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    with (directory / "request.raw.json").open("xb") as target:
        target.write(raw)
    observed = {"turn": turn}
    with client.stream("POST", "/", content=raw,
            headers={"Content-Type": "application/json"}) as response:
        observed["http_status"] = response.status_code
        observed["content_type"] = response.headers.get("content-type")
        with (directory / "response.raw.sse").open("xb") as target:
            for chunk in response.iter_bytes():
                target.write(chunk)
    if observed["http_status"] != 200 or not str(observed["content_type"]).startswith("text/event-stream"):
        raise ValueError("Original A2A request did not produce successful SSE")
    events = [json.loads(line[6:]) for line in (directory / "response.raw.sse").read_text().splitlines()
              if line.startswith("data: ")]
    write_new(directory / "rpc-events.json", events)
    results = [event["result"] for event in events if "result" in event]
    if not results or any("error" in event for event in events):
        raise ValueError("Original SDK did not return task events")
    last = results[-1]
    observed.update(last_state=last.get("status", {}).get("state"),
        task_id=last.get("taskId", last.get("id")), context_id=last.get("contextId"))
    if not observed["task_id"] or not observed["context_id"]:
        raise ValueError("Observed SDK task or context missing")
    if previous and (observed["task_id"] == previous["task_id"] or observed["context_id"] != previous["context_id"]):
        raise ValueError("Second turn is not a new task in the same actual SDK context")
    get_payload = {"jsonrpc": "2.0", "id": f"reference-v4-get-{turn}",
        "method": "tasks/get", "params": {"id": observed["task_id"]}}
    get_raw = json.dumps(get_payload, separators=(",", ":")).encode()
    with (directory / "task-get.request.raw.json").open("xb") as target:
        target.write(get_raw)
    response = client.post("/", content=get_raw, headers={"Content-Type": "application/json"})
    with (directory / "task-get.response.raw.json").open("xb") as target:
        target.write(response.content)
    if response.status_code != 200 or "result" not in response.json():
        raise ValueError("Original SDK task observation failed")
    return observed


def run(case, original, public_path, diagnosis_path):
    if sys.platform != "linux":
        raise ValueError("Reference execution requires the gated hosted Linux profile")
    public = json.loads(public_path.read_bytes())
    case_id, turns = public["id"], public["public"]["turns"]
    if case_id not in IDS or public.get("split") not in ("development", "calibration", "held_out"):
        raise ValueError("Only the 34 original source candidate attempts may execute")
    data_dir, state = case / "data", case / "state"
    shutil.copytree(original / "agents/data", data_dir)
    state.mkdir()
    if sha((data_dir / "incidents.db").read_bytes()) != public["public"]["fixture_recipe"]["seed_database"]["sha256"]:
        raise ValueError("Public seed pin differs")
    for key in list(os.environ):
        if key.upper().startswith(("GOOGLE_", "OPENAI_", "GEMINI_", "AGENT_", "OTEL_")):
            del os.environ[key]
    os.environ.update(OTEL_SDK_DISABLED="true", AGENT_MODEL_PROVIDER="openai-compatible",
        AGENT_MODEL="deterministic-public-reference-v4", AGENT_ENTRYPOINT="agent",
        AGENT_DATA_DIR=str(data_dir), AGENT_STATE_DIR=str(state), AGENT_SEMANTIC_RETRIEVAL="false",
        AGENT_SANITIZE_TOOL_OUTPUT="true", AGENT_WRITES_DISABLED="false", AGENT_A2A_STREAMING="false")
    sys.path.insert(0, str(original / "agents/python/src"))
    journal, contexts, denied = [], [], []
    metadata = {"schema_version": "agentops-governed-app-reference/4", "case_id": case_id,
        "started_at_utc": now(), "status": "failed", "tasks": [], "provider_calls": 0,
        "bank_qualification_claimed": False, "task_success_claimed_by_actor": False,
        "governance_bodies_modified": False, "source_bodies_modified": False,
        "transport_intervention": "Starlette TestClient ASGI, no native socket",
        "socket_policy": "diagnostic-deny-all-before-operation",
        "instrumentation": "Original-root observational before_tool_callback returning None; deterministic model journal",
        "declared_public_turns": len(turns), "executed_public_turns": [], "unsupported_public_turns": [],
        "configuration": public["public"]["fixture_recipe"]["configuration"], "unrealized_obligations": []}
    try:
        from agentops_public_fixture_v4 import apply_data, stage_notes
        metadata["data_fixture"] = apply_data(case, data_dir, public)
        configuration = public["public"]["fixture_recipe"]["configuration"]
        for key, value in configuration.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if public["public"]["fixture_recipe"]["application_entrypoint"] == "workflow":
            metadata["status"] = "unsupported_public_recipe"
            metadata["unsupported_public_turns"] = [{"turn": i, "reason": "Original four-stage workflow model harness is not implemented; no SDK/task/body execution is claimed."} for i in range(1, len(turns) + 1)]
            return
        from agentops_socket_diagnostics_v2 import make_guard
        aliases = [(str(original), "<original-source>"), (str(case), "<case>"),
            (str(Path(sys.prefix)), "<python-environment>"),
            (str(Path(__file__).resolve().parents[1]), "<research-checkout>")]
        sys.addaudithook(make_guard(case, denied, aliases))
        try:
            Path("evaluator.json").read_bytes()
        except PermissionError:
            pass
        else:
            raise ValueError("Private-bank audit denial did not fail closed")
        from agentops_urllib3_bootstrap_v2 import prepare
        metadata["socket_bootstrap"] = prepare(case, diagnosis_path, denied)
        # Only after the source-bound cold bootstrap may the SDK/App import begin.
        from google.adk.models import BaseLlm, LlmResponse
        from google.genai import types
        from pydantic import Field
        from starlette.testclient import TestClient
        from agent import composition

        class PublicReferenceLlm(BaseLlm):
            turn: int = 1
            calls: int = 0
            responses: dict = Field(default_factory=dict)
            prompt: str = turns[0]["text"]

            async def generate_content_async(self, llm_request, stream=False):
                if stream:
                    raise ValueError("Declared reference uses original non-token-streaming mode")
                # Restrict dependencies to the actual current user turn. Prior same-
                # session function responses must not overwrite fresh observations.
                boundary = None
                visible_prompt = None
                for index, content in enumerate(llm_request.contents):
                    visible_parts = [part.text for part in content.parts or [] if part.text is not None]
                    if content.role == "user" and visible_parts:
                        boundary, visible_prompt = index, "\n".join(visible_parts)
                if boundary is None:
                    raise ValueError("Current governed user text is absent from actual model input")
                observed_history = []
                for content in llm_request.contents[boundary + 1:]:
                    for part in content.parts or []:
                        if part.function_response is not None:
                            self.responses[part.function_response.name] = part.function_response.response
                            observed_history.append({"id": part.function_response.id,
                                "name": part.function_response.name, "response": part.function_response.response})
                self.responses["_observed_history"] = observed_history
                item = choose(case_id, self.turn, self.calls, self.responses, visible_prompt)
                self.calls += 1
                parts = [types.Part(text=item["plan"])] if item.get("plan") else []
                if "name" in item:
                    parts.append(types.Part(function_call=types.FunctionCall(
                        id=f"reference-v4-t{self.turn}-call{self.calls}", name=item["name"], args=item["args"])))
                else:
                    parts.append(types.Part(text=item["text"]))
                response = LlmResponse(content=types.Content(role="model", parts=parts))
                row = {"turn": self.turn, "index": self.calls, "observed_at_utc": now(),
                    "observed_user_text": visible_prompt, "observed_user_content_index": boundary,
                    "request": llm_request.model_dump(mode="json", exclude_none=True),
                    "response": response.model_dump(mode="json", exclude_none=True)}
                journal.append(row)
                with (case / "model-journal.jsonl").open("a", encoding="utf-8") as target:
                    target.write(json.dumps(row, allow_nan=False) + "\n")
                yield response

        exported_app = None
        if public["public"]["fixture_recipe"]["application_entrypoint"] == "structured_report":
            from google.adk.cli.utils.agent_loader import AgentLoader
            from google.adk.apps import App
            loader = AgentLoader(agents_dir=str(original / "agents/python/src/agent"))
            exported_app = loader.load_agent("structured_report")
            module = sys.modules.get("structured_report.agent")
            module_source = original / "agents/python/src/agent/structured_report/agent.py"
            if not isinstance(exported_app, App) or module is None or module.app is not exported_app:
                raise ValueError("Native discovery did not return the original exported report App")
            if Path(module.__file__).resolve() != module_source.resolve():
                raise ValueError("Native report export came from a different source")
            selected = exported_app.root_agent
            metadata.update(native_exported_App_identity=True, app_discovery={
                "loader": type(loader).__module__ + "." + type(loader).__qualname__,
                "agent_name": "structured_report", "requested": "structured_report", "returned_type": type(exported_app).__module__ + "." + type(exported_app).__qualname__,
                "module": "structured_report.agent", "source": "agents/python/src/agent/structured_report/agent.py",
                "source_sha256": sha(module_source.read_bytes()), "returned_is_module_app": True})
        else:
            selected = composition.root_agent
        metadata["original_model_type"] = type(selected.model).__module__ + "." + type(selected.model).__qualname__
        metadata["original_model_client_unmaterialized"] = "_openai_client" not in vars(selected.model)
        actor = PublicReferenceLlm(model="deterministic-public-reference-v4")
        selected.model = actor
        if selected.before_tool_callback is not None:
            raise ValueError("Selected original root already has an observational callback")

        def observe(*, tool, args, tool_context):
            row = {"turn": actor.turn, "index": sum(item["turn"] == actor.turn for item in contexts) + 1,
                "observed_at_utc": now(), "tool": tool.name, "args": dict(args),
                "user_id": tool_context.user_id, "session_id": tool_context.session.id,
                "invocation_id": tool_context.invocation_id,
                "confirmation_present": tool_context.tool_confirmation is not None}
            contexts.append(row)
            with (case / "tool-contexts.jsonl").open("a", encoding="utf-8") as target:
                target.write(json.dumps(row, allow_nan=False) + "\n")
            return None

        selected.before_tool_callback = observe
        if public["public"]["fixture_recipe"]["memory_initialization"]["kind"] == "declared_note_rows":
            if selected.before_model_callback is not None:
                raise ValueError("Original selected root already has a before-model callback")
            def observed_fixture(*, callback_context, llm_request):
                result = stage_notes(case, original, public, callback_context, state)
                if result is not None:
                    metadata["note_fixture"] = result
                    metadata["unrealized_obligations"].extend(result["obligations_pending"])
                    write_new(case / "state-after-fixture.json", snapshot(state))
                return None
            selected.before_model_callback = observed_fixture
        from agent import server
        app = exported_report_harness(server, exported_app) if exported_app is not None else server.create_app()
        runtime = app.state.runtime
        runner_app = runtime.runner.app
        from agent.governance import AgentOpsPolicyPlugin
        if runner_app.root_agent is not selected or len(runner_app.plugins) != 1 or type(runner_app.plugins[0]) is not AgentOpsPolicyPlugin:
            raise ValueError("Original selected root and policy composition differ")
        if exported_app is not None and runner_app is not exported_app:
            raise ValueError("Harness did not retain actual native exported App object")
        metadata.update(entrypoint=public["public"]["fixture_recipe"]["application_entrypoint"],
            root_name=selected.name, app_name=runner_app.name,
            policy_plugins=[type(plugin).__module__ + "." + type(plugin).__qualname__ for plugin in runner_app.plugins],
            runner_type=type(runtime.runner).__module__ + "." + type(runtime.runner).__qualname__,
            session_service_type=type(runtime.session_service).__module__ + "." + type(runtime.session_service).__qualname__,
            task_store_type=type(runtime.task_store).__module__ + "." + type(runtime.task_store).__qualname__,
            replacement_model_type=type(actor).__qualname__,
            app_harness="Original exported structured App in disclosed original-runtime assembly" if exported_app is not None else "Original server.create_app()")
        with TestClient(app) as client:
            write_new(case / "state-before.json", snapshot(state))
            previous = None
            for turn, public_turn in enumerate(turns, 1):
                unsupported = public_turn["kind"] != "user_message" or (case_id == "agentops-c04-cross-session-identity" and turn > 1)
                if unsupported or (previous is not None and previous["last_state"] != "completed"):
                    reason = "Native confirmation/replay or verified cross-session continuation remains unimplemented; retain actual prior task/proposal without fabricated identities or completion."
                    metadata["unsupported_public_turns"].extend({"turn": index, "reason": reason} for index in range(turn, len(turns) + 1))
                    break
                actor.turn, actor.calls, actor.responses, actor.prompt = turn, 0, {}, public_turn["text"]
                observed = capture_turn(client, case, actor.prompt, turn, previous)
                metadata["tasks"].append(observed)
                metadata["executed_public_turns"].append(turn)
                if len(turns) > 1:
                    write_new(case / f"state-after-turn-{turn}.json", snapshot(state))
                previous = observed
        metadata["original_lifespan_exited"] = True
        write_new(case / "state-after.json", snapshot(state))
        for path in sorted(state.glob("*.db")):
            shutil.copyfile(path, case / ("closed-" + path.name))
        metadata["status"] = "partial_original_task" if metadata["unsupported_public_turns"] or metadata["unrealized_obligations"] else "original_governed_app_tasks_observed"
    except BaseException:
        metadata["error_type"] = sys.exc_info()[0].__name__
        (case / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        metadata.update(finished_at_utc=now(), model_calls=len(journal), tool_calls_observed=len(contexts),
            denied_capability_probes=denied)
        write_new(case / "actor-receipt.json", metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--public-task", type=Path, required=True)
    parser.add_argument("--diagnosis", type=Path, required=True)
    args = parser.parse_args()
    run(args.case.resolve(), args.original.resolve(), args.public_task.resolve(), args.diagnosis.resolve())
