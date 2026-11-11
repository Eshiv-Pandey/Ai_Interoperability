"""Public-only bounded before-model fixture; no SDK/application imports.

An App plugin calls this only after the unchanged original policy returned None.
Actual callback agent identity and the governed request select the response.
"""
from __future__ import annotations

from agentops_workflow_public_v1 import STAGES, TOOLS, choose
from agentops_workflow_reference_v1 import visible_input


def compiled_node_map(graph_nodes):
    """Resolve the pinned SDK's list[BaseNode], rejecting ambiguous surfaces."""
    if not isinstance(graph_nodes, list):
        raise ValueError("Pinned original Graph.nodes must be a list")
    result = {}
    for node in graph_nodes:
        name = getattr(node, "name", None)
        if name not in (*STAGES, "__START__") or name in result:
            raise ValueError("Compiled graph has an unknown, unnamed or duplicate node")
        result[name] = node
    if result.keys() != {*STAGES, "__START__"}:
        raise ValueError("Compiled graph must contain exactly the original START sentinel and four stages")
    return result


class PublicWorkflowFixture:
    def __init__(self, journal, record, timestamp):
        self.journal = journal
        self.record = record
        self.timestamp = timestamp
        self.calls = {stage: 0 for stage in STAGES}

    def respond(self, callback_context, llm_request, make_response):
        stage = callback_context.agent_name
        if stage not in STAGES:
            raise ValueError("Actual before-model callback agent is not an original Workflow stage")
        index = self.calls[stage]
        if index >= 8 or len(self.journal) >= 24:
            raise ValueError("Declared per-stage/global before-model fixture bound exceeded")
        prompt, responses, boundary, history = visible_input(llm_request)
        item = choose(stage, index, responses, prompt)
        if "name" in item and (item["name"] not in TOOLS[stage] or item["name"] not in llm_request.tools_dict):
            raise ValueError("Fixture requested a tool outside the actual governed original node surface")
        call_id = f"workflow-v2-{stage}-{index}"
        response = make_response(item, call_id)
        row = {"sequence": len(self.journal) + 1, "stage": stage, "stage_call_index": index,
               "fixture_boundary": "App before_model callback after unchanged original policy",
               "actual_callback_agent_name": stage,
               "actual_callback_invocation_id": callback_context.invocation_id,
               "actual_callback_user_id": callback_context.user_id,
               "actual_callback_session_id": callback_context.session.id,
               "observed_at_utc": self.timestamp(), "observed_input": prompt,
               "observed_input_content_index": boundary, "observed_function_responses": history,
               "actual_governed_request_model": llm_request.model,
               "request": llm_request.model_dump(mode="json", exclude_none=True),
               "response": response.model_dump(mode="json", exclude_none=True)}
        self.record(row)
        self.journal.append(row)
        self.calls[stage] += 1
        return response
