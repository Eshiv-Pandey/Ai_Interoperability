# AgentOps Workflow clone and callback binding diagnosis V1

V1 replaced the models on the exported original agents after the official SDK
had compiled distinct clones into the Workflow graph. Runtime executed those
compiled clones with their original backend model fields. The diagnosis is
bound to the locked ADK 2.10.0 wheel and the actual failed run `43036777469`.
Source identities are recorded in
`agentops-workflow-clone-binding-diagnosis-v1.json`; V1 outcomes are preserved in
`agentops-workflow-reference-results-v1.md`.

The verified source chain is:

1. Original `agent/workflow.py:40-113` constructs four exported agents and
   `:116-120` constructs `triage_workflow` immediately from those agents.
2. ADK `workflow/_workflow.py:169-178` compiles `edges` during `model_post_init`.
3. `workflow/_graph.py:117-121` calls `parse_edge_items`. Tuple endpoints resolve
   through `workflow/utils/_graph_parser.py:161-206`.
4. `_graph_parser.py:103-118` calls `build_node` and stores its returned node.
5. `workflow/utils/_workflow_graph_utils.py:116-141` calls
   `agent_node.clone(update=kwargs)`. Those updates concern resume/mode fields;
   they do not replace the model.
6. `agents/base_agent.py:236-270` creates a new agent using
   `self.model_copy(update=update)`, preserving its current model field.
7. Owned V1 `scripts/agentops_workflow_reference_v1.py:205` selects the exported
   original agents and `:233` assigns their replacement model fields.
8. Runtime `_workflow.py:875-880` resolves `graph.nodes`; `:581-622` schedules
   those compiled nodes. `agents/llm_agent.py:670-681` passes the executing node
   to the official wrapper.

V1's topology check examines `selected.edges`, which still contains the
exported originals. It does not inspect or replace `selected.graph.nodes`.
Therefore the check can pass while execution uses the earlier compiled clones.
`agents/llm_agent.py:696-697` immediately returns a `BaseLlm` assigned to the
executing agent, so this is not a canonical-model cache failure. V1 assigned its
fixture to a different object.

The actual V1 raw events and denial stacks agree with this source diagnosis:
eight `MODEL_UNAVAILABLE` events, zero owned fixture responses and original
OpenAI-compatible code reached before denied loopback socket operations. V1 did
not journal compiled/exported runtime object identities; that missing runtime
identity evidence remains explicit. The source chain explains the failure
without claiming an external provider outage.

Pinned `flows/llm_flows/core/_finalizer.py:82-126` dispatches App
`before_model_callback` before backend invocation, and a returned `LlmResponse`
short-circuits that invocation. The actual installed V1 plugin-manager source
matches the pinned wheel and dispatches ordered callbacks until the first
non-`None` result. V2 consequently preserves original exported and compiled
models, appends its fixture after the unchanged original policy, and returns
public-only declared fixture responses from the actual executing clone's
governed model callback. An original policy response still has priority and
prevents the fixture callback.

The source diagnosis and its independent read-only review import no SDK and
execute no application or provider. V2 must separately retain actual
compiled/exported identity, model-type and callback binding observations.
