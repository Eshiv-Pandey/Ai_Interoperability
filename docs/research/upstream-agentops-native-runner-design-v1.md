# Upstream AgentOps native runner design v1

Date: 2026-10-29. Status: source-only design; no native execution or runtime allocation.

The next runner should execute the original pinned AgentOps objects with the selected native model, retain public A2A evidence and evaluator-private runtime/business evidence, and keep benchmark grading separate. This note establishes feasible source paths. It does not establish model availability for AgentOps, native behavior, admission qualification, or checkpoint credit.

## Original execution surfaces

Upstream source base: `external/agentops-c806b7f1/agents/python/`.
Upstream documentation base: `external/agentops-c806b7f1/docs/`.
Pinned SDK source base: `external/runtime-agentops-v2-recovery-2/venv/Lib/site-packages/google/adk/` (distribution metadata records ADK 2.10.0).

| Family | Cases in retained input export | Original canonical surface | Prospective A2A surface |
| --- | ---: | --- | --- |
| Core | 15 | `AGENT_ENTRYPOINT=agent`; original conversational agent; `mise run eval` | Default `agent.server.create_app()` / original `python -m agent.server` |
| Structured report | 3 | `agent.structured_report.agent`; original `triage_report_agent`; `mise run eval:report` | Explicit unchanged-object embedding: `create_app(agent=triage_report_agent)` |
| Workflow | 3 | `AGENT_ENTRYPOINT=workflow`; original `triage_workflow`; `mise run eval:workflow` | Explicit unchanged-object embedding: `create_app(agent=triage_workflow)`; default A2A launcher rejects it |

Core selection is in `src/agent/composition.py:119-133`; default A2A selection is `src/agent/server.py:537-546`. Report discovery re-exports the original agent and governed App in `src/agent/structured_report/agent.py:3-6`; `evals/report_eval.py:28-31` selects that module and requests three runs. Workflow evaluation sets the original entrypoint and repeats each case three times (`mise.toml:98-101`). The retained single-sample input export is `runs/upstream-agentops-cases/v1/application/cases.json`: 21 cases, 22 user turns, including the two-turn memory case. It is not the complete repeated upstream evaluation schedule.

The report A2A path is an embedding of the original report object, not the default server's selection. `server.py:544-567` accepts an explicit agent and attaches the same policy via `build_app`; `server.py:595-607` passes the selected object and original runner into ADK's A2A adapter. The original agent card remains the server's card, so record this embedding and its advertised modes rather than claiming a separate upstream report A2A launcher exists.

### Workflow boundary

Pinned SDK `workflow/_workflow.py:131` defines `Workflow(BaseNode)`, while `agents/base_agent.py:99` defines `BaseAgent(BaseNode, abc.ABC)`. Therefore a workflow fails the original server's `isinstance(root_agent, BaseAgent)` guard (`server.py:537-541`).

Explicit embedding bypasses that guard (`server.py:544-546`). The original policy builder accepts `BaseAgent | Workflow` (`src/agent/governance.py:100-102`); SDK `apps/app.py:72-78` accepts a `BaseNode`; SDK `runners.py:1151-1169` dispatches a non-BaseAgent node to its node runtime. The original server's session-serializing runner delegates to `super().run_async` (`server.py:183-211`), and SDK `a2a/utils/agent_to_a2a.py:79-98` explicitly accepts `Workflow`. No additional runtime type obstacle was found in this source path. Actual workflow A2A behavior remains untested. The original ADK workflow/evaluation route remains the canonical upstream option.

## Supported key and model configuration

`src/agent/config.py:51-84` defaults to:

```text
AGENT_ENTRYPOINT=agent
AGENT_MODEL_PROVIDER=gemini
AGENT_MODEL=gemini-3.5-flash
GOOGLE_GENAI_USE_ENTERPRISE=false
```

AI Studio authentication uses a nonempty `GOOGLE_API_KEY`, loaded securely into the native process. This application does not alias `GEMINI_API_KEY`. The enterprise/ADC alternative requires `GOOGLE_GENAI_USE_ENTERPRISE=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`; API-key auth and enterprise mode cannot be combined (`config.py:213-233`). `build_model()` enforces credentials (`src/agent/model.py:135-149`; `config.py:258-269`) and passes explicit auth/deadlines to the original ADK Gemini client (`model.py:48-74`). No key value belongs in an artifact or log.

The parent session has already probed `gemini-3.1-flash-lite-preview` metadata for the AP2 work. Selecting that name through the supported `AGENT_MODEL` setting would change configuration, not upstream source. That metadata probe does not verify AgentOps's default `gemini-3.5-flash`, tool use, output-schema support, quota, or native execution. Pin and disclose the selected provider/model in every run and complete actual AgentOps validation before claiming success.

For attributable comparisons, unset `AGENT_MODEL_FALLBACK`; leave `AGENT_PROMPT_URI` unset for the committed prompt or select an immutable numeric version (`evals/runtime.py:14-38`). Record sampling and retry settings. Defaults include unset temperature, 60-second model timeout and two configured retries (`config.py:134-138`). The A2A path also has a 12-call budget and token streaming disabled (`config.py:114-118`; `server.py:324-343`); do not assume these A2A settings automatically bound the separate evaluator path. Model-backed mise tasks load the root `.env` with redaction (`mise.toml:83,95,100,175`); direct Python launches require an explicitly prepared environment.

## Outer evidence retention

The unchanged upstream evaluation wrappers are insufficient as the sole evidence archive. Core/workflow runs use a temporary state directory per sample that is deleted after the subprocess (`evals/run_adk_eval.py:177-205`). Report evaluation uses a temporary state scope that is also deleted (`evals/runtime.py:41-50`). Preserve upstream metrics and stdout if using those paths, and design retention before running them. MLflow's flattened tool aggregates also omit event/function identity; they cannot substitute for the raw causal-evidence source.

The prospective outer runner must:

1. Use fresh per-case/sample state and evidence paths after prerequisite/resource checks; never overwrite or rerun a consumed allocation. Keep source inputs and evaluator-private references separate, with references withheld from the model/client.
2. Record pinned source/dependency digests, original object/entrypoint, full nonsecret configuration, and mappings from exported case/session labels to actual native identities. The original governed App is `agentops-agent` (`governance.py:46`); exported `app_name` labels are not automatically native App names. Record context, task, user, session and invocation identities as observed.
3. Retain exact request/response bytes and cumulative Task observations for original `SendMessage` / `GetTask`, along with agent card and protocol/header settings. Retain all raw runtime events and IDs before disposable state cleanup; normalize public artifacts using event/part identity with content checks. Preserve multiple response phases under one call ID.
4. Snapshot prepared business state after startup and around each user/confirmation exchange; retain the runtime DB and any memory DB with their schema and attribution. Keep physical row order, timestamp order and phase linkage distinct. Public text may be sanitized or protobuf-number-normalized; do not demand blanket byte equality with stored business rows.
5. Keep all turns of a case in one actual user/context/session. The memory case's second task in the same context establishes session continuity; it does not resume a completed first task. Isolate state between cases and samples.
6. Report provider/quota/transport failures separately from benchmark failures. Preserve original reference trajectories and acceptance criteria. The original evaluator does not auto-approve guarded actions (`docs/4. Quality/4.7. Evaluation Reference.md:253`); a separate controlled approval/effect experiment needs its own explicit contract.

Native A2A evidence establishes source-case execution and protocol observations. Raw DB/snapshots remain evaluator-private. Neither layer alone establishes the new admission method's novelty, causal completeness, qualification, or 70% project completion.

## Prospective first case: inventory-status

Use the exact retained input `inventory-status` from core family `agentops_agent_core`:

```text
What is the status of the inventory service?
```

The original `evals/ops.evalset.json` reference requires `get_service_status` with `{"name":"inventory"}` and states that inventory is currently down. The original tool reads seeded service and incident data (`src/agent/tools.py:82-103`). Keep the original conversational agent and full tool surface; do not replace it with a fixture agent or constrain tools to manufacture the trajectory.

Before execution, verify the host resource gate and native dependency/model preflight, then define a fresh isolated case allocation. After startup, retain the seeded business baseline, run the exact user message through the original A2A surface, and retain polling, public parts, raw events and final state. Evaluate the required lookup, factual answer, identities and absence of unexpected business/memory writes. The original required-trajectory contract permits extra calls; preserve and assess them rather than asserting an exact single-call trace.

A passed first run would establish one faithful native source-case/evidence path. Expansion to the remaining core/report/workflow cases, controlled confirmation/effect checks, reviewed evaluation inputs, new admission qualification and human acceptance remain subsequent work. This design creates no runtime allocation and authorizes no launch by itself.
