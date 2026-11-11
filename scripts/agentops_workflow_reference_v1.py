"""Run the unchanged original Workflow via its original App and official ADK.

The original A2A server rejects Workflow roots. This direct in-process ADK
allocation does not claim an original A2A or live-provider route. Four owned,
public-only deterministic model fixtures replace only node models; an extra
observational App plugin returns None and preserves original policy ordering.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
import uuid

from agentops_governed_app_pilot_v2 import now, sha, snapshot, write_new
from agentops_workflow_public_v1 import IDS, STAGES, TOOLS, choose

WORKFLOW_SHA256 = "68c3fefa9966ecddb69d96150423379433016be508f811df7638a30ba9bb9747"
INSTRUCTION_SHA256 = (
    "290cfa7d7b04aa3321ec27f0089fc1771fc5ac739c98b32f3dc25f08cddf9129",
    "05b2f9cfa2ba5882b819eb3eda715e28215e40cd36a5b821442d07e52c0bc27f",
    "506d4bf2bc6a5ca7061e87f81132ad3b0186a8edb67519235c3683472ff4125c",
    "60f917ec16911ac8a5cb48c57ffdf3ed6f8ca7ee85c9afbd30790ad2d7b9e2a1",
)


def append(path, row):
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def visible_input(llm_request):
    """Extract the actual immediate predecessor/current-stage source input."""
    prompt, boundary = None, None
    for index, content in enumerate(llm_request.contents):
        texts = [part.text for part in content.parts or [] if part.text is not None]
        if content.role == "user" and texts:
            prompt, boundary = "\n".join(texts), index
    if prompt is None:
        raise ValueError("Original current-stage user/predecessor text is absent")
    responses, history = {}, []
    for content in llm_request.contents[boundary + 1:]:
        for part in content.parts or []:
            if part.function_response is not None:
                name, response = part.function_response.name, part.function_response.response
                history.append({"name": name, "response": response})
                responses[name] = response
    return prompt, responses, boundary, history


def run(case, original, public_path, diagnosis_path):
    if sys.platform != "linux":
        raise ValueError("Use the separately gated hosted Linux workflow profile")
    if public_path.parent != case or not case.is_dir() or any(case.iterdir()) and set(p.name for p in case.iterdir()) != {"public-task.json"}:
        raise ValueError("A fresh case with only its public-task projection is required")
    public = json.loads(public_path.read_bytes())
    case_id, turns, recipe = public["id"], public["public"]["turns"], public["public"]["fixture_recipe"]
    if (case_id not in IDS or recipe["application_entrypoint"] != "workflow"
            or len(turns) != 1 or turns[0]["kind"] != "user_message"
            or recipe["memory_initialization"]["kind"] != "absent_store"):
        raise ValueError("Only the two original one-turn read-only Workflow candidates are allocated")
    metadata = {"schema_version": "agentops-original-workflow-reference/1", "case_id": case_id,
                "status": "failed", "started_at_utc": now(), "provider_calls": 0,
                "application_entrypoint": "workflow", "original_source_modified": False,
                "graph_or_instruction_modified": False, "task_success_claimed": False,
                "human_gold_qualification": False, "held_out_qualification": False,
                "original_A2A_route": False, "runtime_route": "official ADK InMemoryRunner with original composition.app",
                "model_intervention": "Four separately attributed deterministic public-only node BaseLlm fixtures",
                "policy_intervention": "Owned observational App plugin appended after the unchanged single original policy; every hook returns None",
                "after_tool_observer_may_be_short_circuited_by_original_policy": True,
                "tool_terminal_authority": "Raw official SDK function-response events after original policy dispatch; optional after-hook observations remain separate",
                "socket_policy": "diagnostic deny before native/provider socket operations",
                "declared_original_case_denominator": len(IDS), "declared_public_turns": 1}
    denied, journal, contexts, observations, events = [], [], [], [], []
    data_dir, state = case / "data", case / "state"
    try:
        shutil.copytree(original / "agents/data", data_dir)
        state.mkdir()
        if sha((data_dir / "incidents.db").read_bytes()) != recipe["seed_database"]["sha256"]:
            raise ValueError("Original seed database bytes differ")
        workflow_source = original / "agents/python/src/agent/workflow.py"
        if sha(workflow_source.read_bytes()) != WORKFLOW_SHA256:
            raise ValueError("Original Workflow source bytes differ")
        for key in list(os.environ):
            if key.upper().startswith(("GOOGLE_", "OPENAI_", "GEMINI_", "AGENT_", "OTEL_")):
                del os.environ[key]
        os.environ.update(OTEL_SDK_DISABLED="true", AGENT_MODEL_PROVIDER="openai-compatible",
            AGENT_MODEL="deterministic-original-workflow-reference-v1", AGENT_ENTRYPOINT="workflow",
            AGENT_DATA_DIR=str(data_dir), AGENT_STATE_DIR=str(state), AGENT_SEMANTIC_RETRIEVAL="false",
            AGENT_SANITIZE_TOOL_OUTPUT="true", AGENT_WRITES_DISABLED="false", AGENT_A2A_STREAMING="false")
        for key, value in recipe["configuration"].items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        sys.path.insert(0, str(original / "agents/python/src"))
        from agentops_public_fixture_v4 import apply_data
        metadata["data_fixture"] = apply_data(case, data_dir, public)
        from agentops_socket_diagnostics_v2 import make_guard
        aliases = [(str(original), "<original-source>"), (str(case), "<case>"),
                   (str(Path(sys.prefix)), "<python-environment>"),
                   (str(Path(__file__).resolve().parents[1]), "<research-checkout>")]
        sys.addaudithook(make_guard(case, denied, aliases))
        private_names = {"evaluator-private.json", "human-review-packet.md", "second-instance-review.md", "candidate-table.md", ".env"}
        def private_guard(event, arguments):
            if event == "open" and isinstance(arguments[0], (str, bytes, os.PathLike)) and Path(os.fsdecode(arguments[0])).name in private_names:
                raise PermissionError("Private answer/review material and credentials are excluded from the actor")
        sys.addaudithook(private_guard)
        try:
            Path("evaluator.json").read_bytes()
        except PermissionError:
            metadata["private_evaluator_probe_denied"] = True
        else:
            raise ValueError("Private evaluator audit probe must fail closed")
        from agentops_urllib3_bootstrap_v2 import prepare
        metadata["socket_bootstrap"] = prepare(case, diagnosis_path, denied)
        from google.adk.models import BaseLlm, LlmResponse
        from google.adk.plugins.base_plugin import BasePlugin
        from google.adk.runners import InMemoryRunner
        from google.genai import types
        from agent import composition, workflow, data
        from agent.governance import AgentOpsPolicyPlugin

        class PublicWorkflowLlm(BaseLlm):
            stage: str
            calls: int = 0

            async def generate_content_async(self, llm_request, stream=False):
                if stream or self.calls >= 8 or len(journal) >= 24:
                    raise ValueError("Declared public Workflow model-call/stream bound exceeded")
                prompt, responses, boundary, history = visible_input(llm_request)
                item = choose(self.stage, self.calls, responses, prompt)
                if "name" in item:
                    if item["name"] not in TOOLS[self.stage] or item["name"] not in llm_request.tools_dict:
                        raise ValueError("Owned model requested a tool outside the actual original node surface")
                    parts = [types.Part(function_call=types.FunctionCall(
                        id=f"workflow-v1-{self.stage}-{self.calls}", name=item["name"], args=item["args"]))]
                else:
                    parts = [types.Part(text=item["text"])]
                response = LlmResponse(content=types.Content(role="model", parts=parts))
                row = {"sequence": len(journal) + 1, "stage": self.stage, "stage_call_index": self.calls,
                       "observed_at_utc": now(), "observed_input": prompt, "observed_input_content_index": boundary,
                       "observed_function_responses": history,
                       "request": llm_request.model_dump(mode="json", exclude_none=True),
                       "response": response.model_dump(mode="json", exclude_none=True)}
                journal.append(row)
                append(case / "model-journal.jsonl", row)
                self.calls += 1
                yield response

        def stage_name(context):
            name = getattr(context, "agent_name", None)
            if not name:
                name = context._invocation_context.agent.name
            return name

        class ObservationalPlugin(BasePlugin):
            def __init__(self):
                super().__init__(name="owned_workflow_observer_v1")

            async def before_agent_callback(self, *, agent, callback_context):
                row = {"sequence": len(observations) + 1, "kind": "stage_entry", "stage": agent.name,
                       "observed_at_utc": now(), "user_id": callback_context.user_id,
                       "session_id": callback_context.session.id, "invocation_id": callback_context.invocation_id}
                observations.append(row)
                append(case / "stage-observations.jsonl", row)
                return None

            async def after_agent_callback(self, *, agent, callback_context):
                row = {"sequence": len(observations) + 1, "kind": "stage_exit", "stage": agent.name,
                       "observed_at_utc": now(), "user_id": callback_context.user_id,
                       "session_id": callback_context.session.id, "invocation_id": callback_context.invocation_id}
                observations.append(row)
                append(case / "stage-observations.jsonl", row)
                return None

            async def before_tool_callback(self, *, tool, tool_args, tool_context):
                row = {"sequence": len(contexts) + 1, "stage": stage_name(tool_context), "kind": "tool_before",
                       "observed_at_utc": now(), "tool": tool.name, "args": dict(tool_args),
                       "user_id": tool_context.user_id, "session_id": tool_context.session.id,
                       "invocation_id": tool_context.invocation_id,
                       "confirmation_present": tool_context.tool_confirmation is not None}
                contexts.append(row)
                append(case / "tool-contexts.jsonl", row)
                return None

            async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
                row = {"sequence": len(contexts) + 1, "stage": stage_name(tool_context), "kind": "tool_after",
                       "observed_at_utc": now(), "tool": tool.name, "args": dict(tool_args), "result": result,
                       "user_id": tool_context.user_id, "session_id": tool_context.session.id,
                       "invocation_id": tool_context.invocation_id}
                contexts.append(row)
                append(case / "tool-contexts.jsonl", row)
                return None

        selected, app = workflow.triage_workflow, composition.app
        nodes = (workflow.plan, workflow.investigate, workflow.evidence_review, workflow.recommend)
        if (composition.root_agent is not selected or app.root_agent is not selected
                or len(selected.edges) != 1 or selected.edges[0][0] != "START"
                or list(selected.edges[0][1:]) != list(nodes)
                or tuple(node.name for node in nodes) != STAGES):
            raise ValueError("Original App/Workflow identity or original graph topology differs")
        if len(app.plugins) != 1 or type(app.plugins[0]) is not AgentOpsPolicyPlugin:
            raise ValueError("Exactly one unchanged original policy plugin is required")
        metadata["original_app_identity"] = {"app_name": app.name, "root_name": selected.name,
            "root_type": type(selected).__module__ + "." + type(selected).__qualname__,
            "composition_root_is_original_workflow": True, "composition_app_root_is_original_workflow": True,
            "workflow_source_sha256": sha(workflow_source.read_bytes()),
            "original_policy_type": type(app.plugins[0]).__module__ + "." + type(app.plugins[0]).__qualname__,
            "graph": ["START", *STAGES]}
        metadata["nodes"] = []
        for node, instruction_hash in zip(nodes, INSTRUCTION_SHA256):
            names = [getattr(tool, "name", None) or getattr(tool, "__name__", "") for tool in node.tools]
            digest = sha(str(node.instruction).encode())
            if tuple(names) != TOOLS[node.name] or digest != instruction_hash:
                raise ValueError("Original node instruction or exact read-only tool surface differs")
            callbacks = ("before_model_callback", "after_model_callback", "before_tool_callback", "after_tool_callback",
                         "on_model_error_callback", "on_tool_error_callback")
            if any(getattr(node, name) is not None for name in callbacks):
                raise ValueError("Original nodes must retain their unmodified absent policy callbacks")
            metadata["nodes"].append({"name": node.name, "instruction_sha256": digest, "tools": names,
                "original_model_type": type(node.model).__module__ + "." + type(node.model).__qualname__,
                "original_model_client_unmaterialized": "_openai_client" not in vars(node.model),
                "original_node_callbacks_unchanged": True})
            node.model = PublicWorkflowLlm(model="deterministic-original-workflow-reference-v1", stage=node.name)
        app.plugins.append(ObservationalPlugin())
        metadata["runtime_plugins"] = [type(p).__module__ + "." + type(p).__qualname__ for p in app.plugins]
        # Direct CLI/ADK execution does not use the original A2A startup hook.
        # Call the original explicit initialization boundary before the read-only
        # task; do not have a read tool mutate/migrate its database.
        data.prepare_runtime_database()
        write_new(case / "state-before.json", snapshot(state))
        initial_data = {p.relative_to(data_dir).as_posix(): sha(p.read_bytes()) for p in data_dir.rglob("*") if p.is_file()}
        runner = InMemoryRunner(app=app)
        if runner.app is not app:
            raise ValueError("Official Runner did not preserve the actual original App object")
        metadata["runner_type"] = type(runner).__module__ + "." + type(runner).__qualname__

        async def execute():
            session = await runner.session_service.create_session(app_name=app.name, user_id="workflow-fixture-user-" + uuid.uuid4().hex)
            metadata["actual_identity"] = {"fixture_user_label": recipe["identity"]["user_id_label"],
                "actual_sdk_user_id": session.user_id, "actual_sdk_session_id": session.id,
                "identity_authentication_claimed": False}
            message = types.Content(role="user", parts=[types.Part(text=turns[0]["text"])])
            write_new(case / "user-message.json", message.model_dump(mode="json", exclude_none=True))
            try:
                async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=message):
                    row = {"sequence": len(events) + 1, "observed_at_utc": now(),
                           "event": event.model_dump(mode="json", exclude_none=True)}
                    events.append(row)
                    append(case / "adk-events.jsonl", row)
                    if len(events) > 80:
                        raise ValueError("Declared raw official event limit exceeded")
                stored = await runner.session_service.get_session(app_name=app.name, user_id=session.user_id, session_id=session.id)
                if stored is None:
                    raise ValueError("Original official session disappeared")
                write_new(case / "session-after.json", stored.model_dump(mode="json", exclude_none=True))
                metadata["official_run_returned"] = True
            finally:
                closing = runner.close()
                if inspect.isawaitable(closing):
                    await closing
                metadata["official_runner_closed"] = True

        asyncio.run(execute())
        write_new(case / "state-after.json", snapshot(state))
        for path in sorted(state.glob("*.db")):
            shutil.copyfile(path, case / ("closed-" + path.name))
        final_data = {p.relative_to(data_dir).as_posix(): sha(p.read_bytes()) for p in data_dir.rglob("*") if p.is_file()}
        if final_data != initial_data:
            raise ValueError("Read-only original workflow modified its copied seed inputs")
        metadata["copied_data_unchanged_during_task"] = True
        metadata["status"] = "official_original_workflow_observed"
    except BaseException:
        metadata["error_type"] = sys.exc_info()[0].__name__
        (case / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        metadata.update(finished_at_utc=now(), model_calls=len(journal), tool_observations=len(contexts),
                        raw_official_events=len(events), denied_capability_probes=denied)
        write_new(case / "actor-receipt.json", metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--public-task", type=Path, required=True)
    parser.add_argument("--diagnosis", type=Path, required=True)
    args = parser.parse_args()
    run(args.case.resolve(), args.original.resolve(), args.public_task.resolve(), args.diagnosis.resolve())
