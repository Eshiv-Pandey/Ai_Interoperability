"""Run six public development recipes against imported original AgentOps tools.

This fixed component reference actor does not run the governed AgentOps App or
a model. It retains that distinction even when original tools and ADK context
objects execute successfully. No private evaluator input is available here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import uuid


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def immediate(coroutine):
    """Drive only a coroutine which completes without an external async wait."""
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    else:
        coroutine.close()
        raise RuntimeError("external_async_wait_refused")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = json.loads(args.input.read_bytes())
    root, out = Path(inputs["root"]).resolve(), args.output.resolve()
    case = inputs["case"]
    if case["split"] != "development":
        raise ValueError("development_inputs_only")
    forbidden = {
        root / "benchmark/tasks-v1/agentops/evaluator.json",
        root / "scripts/agentops_reference_evaluator_v1.py",
        root / "scripts/run_agentops_reference_development_v1.py",
    }
    counts = {"private_reads_blocked": 0, "network_operations_blocked": 0,
              "process_launches_blocked": 0}

    def deny(event, values):
        if event == "open" and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).resolve()
            if (path in forbidden or path.name in {".env", "evaluator.json", "private-seed-gold.json", "evaluation.json"}
                    or path.name.startswith("qualification-private") or path.name.lower().startswith("gemini-api-key")):
                counts["private_reads_blocked"] += 1
                raise PermissionError("private_or_credential_input_denied")
        if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo", "socket.sendto"}:
            counts["network_operations_blocked"] += 1
            raise PermissionError("offline_network_denied")
        if event == "subprocess.Popen" or event == "os.system" or event.startswith("os.spawn"):
            counts["process_launches_blocked"] += 1
            raise PermissionError("actor_descendant_denied")

    sys.addaudithook(deny)
    try:
        (root / "benchmark/tasks-v1/agentops/evaluator.json").read_bytes()
    except PermissionError:
        private_probe = True
    else:
        raise ValueError("private_evaluator_read_probe_not_blocked")
    if any(key in os.environ for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS")):
        raise ValueError("provider_credentials_present")
    site_packages = Path(inputs["site_packages"])
    sys.path[:0] = [inputs["package_root"], str(site_packages),
                   str(site_packages / "win32"), str(site_packages / "win32/lib"),
                   str(site_packages / "pywin32_system32")]
    logging.disable(logging.CRITICAL)
    minimal = inputs.get("component_profile") == "minimal_reads"
    module_names = ("config", "data", "models", "tools", "memory")
    if not minimal:
        module_names += ("longterm", "actions")
    modules = {name: importlib.import_module("agent." + name) for name in module_names}
    data, tools, memory = (modules[name] for name in ("data", "tools", "memory"))
    longterm = modules.get("longterm")
    if not minimal:
        from google.adk.agents.llm_agent import LlmAgent
        from google.adk.agents.invocation_context import InvocationContext
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        from google.adk.tools.tool_context import ToolContext
        from google.adk.tools.function_tool import FunctionTool
        from google.genai import types

    trace = []
    stream = (out / "events.jsonl").open("x", encoding="utf-8", newline="\n")

    def observe(operation, arguments, result):
        record = {"sequence": len(trace) + 1, "at_utc": datetime.now(timezone.utc).isoformat(),
                  "operation": operation, "arguments": arguments, "result": result}
        stream.write(json.dumps(record, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        trace.append(record)
        return result

    def call(function, **kwargs):
        shown = {key: value for key, value in kwargs.items() if key != "tool_context"}
        return observe(function.__module__ + "." + function.__name__, shown, function(**kwargs))

    # The selected agent is an SDK context carrier only; it is never run and
    # must not be confused with the original AgentOps App/root.
    if not minimal:
        context_agent = LlmAgent(name="component_reference_context", model="never-called")
        service = InMemorySessionService()
        session = immediate(service.create_session(app_name="agentops_component_reference", user_id="bank-user-a"))
        identity = {"public_user_label": "bank-user-a", "actual_sdk_user_id": session.user_id,
                    "actual_sdk_session_id": session.id, "sdk_session_created": True, "original_app_selected": False,
                    "context_agent_name": context_agent.name, "invocations": []}
    else:
        identity = {"public_user_label": "bank-user-a", "actual_sdk_user_id": None,
                    "actual_sdk_session_id": None, "sdk_session_created": False,
                    "original_app_selected": False, "invocations": []}

    def context(turn_index, function_call_id=None):
        if minimal:
            return None
        invocation_id = uuid.uuid4().hex
        user_content = types.Content(role="user", parts=[types.Part(text=case["public"]["turns"][turn_index]["text"])])
        invocation = InvocationContext(session_service=service, invocation_id=invocation_id,
                                       agent=context_agent, session=session, user_content=user_content)
        identity["invocations"].append({"turn_index": turn_index, "invocation_id": invocation_id,
                                         "user_id": invocation.user_id, "session_id": invocation.session.id,
                                         "completed_application_task": False})
        return ToolContext(invocation, function_call_id=function_call_id)

    def snapshot(label):
        tables = {}
        for database in ("incidents.db", "memory.db"):
            path = Path(inputs["state_dir"]) / database
            if not path.exists():
                tables[database] = None
                continue
            connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
            try:
                connection.row_factory = sqlite3.Row
                names = [row[0] for row in connection.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
                tables[database] = {
                    name: [dict(row) for row in connection.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid')]
                    for name in names if name in {"incidents", "services", "audit_log", "incident_notes"}
                }
                target = sqlite3.connect(out / (label + "-" + database))
                try:
                    connection.backup(target)
                finally:
                    target.close()
            finally:
                connection.close()
        write_new(out / (label + "-state.json"), tables)
        return tables

    # Initialization is original data-layer work before the task evidence.
    with data._connect():
        pass
    before = snapshot("before")
    observe("public_user_turns", {}, case["public"]["turns"])
    contexts = []
    unexecuted = []
    selected = case["id"]
    if selected == "agentops-d01-health-active":
        contexts.append(context(0))
        call(tools.get_service_status, name=" INVENTORY ")
    elif selected == "agentops-d02-logs-after-record":
        ctx = context(0)
        contexts.append(ctx)
        if minimal:
            unexecuted.append("original same-user incident recall before investigation")
        else:
            call(longterm.recall_incident_context, incident_id="INC-001", tool_context=ctx)
        incident = call(tools.get_incident, incident_id="INC-001")["incident"]
        call(tools.get_service_status, name=incident["service"])
        call(tools.search_service_logs, service=incident["service"], query="", limit=20)
        call(memory.get_runbook, slug=incident["runbook"])
        call(tools.search_service_logs, service=incident["service"], query="pool", limit=20)
    elif selected == "agentops-d03-restart-pause":
        ctx = context(0, "public-restart-proposal")
        contexts.append(ctx)
        incident = call(tools.get_incident, incident_id="INC-002")["incident"]
        call(tools.get_service_status, name=incident["service"])
        call(tools.search_service_logs, service=incident["service"], query="", limit=20)
        call(memory.get_runbook, slug=incident["runbook"])
        if minimal:
            unexecuted.append("actual original guarded SDK restart request and confirmation boundary")
        else:
            guarded = modules["actions"].ACTION_TOOLS[0]
            output = immediate(guarded.run_async(args={"name": incident["service"]}, tool_context=ctx))
            observe("agent.actions.ACTION_TOOLS[0].run_async", {"name": incident["service"], "confirmation_supplied": False},
                    {"tool_output": output, "event_actions": ctx.actions.model_dump(mode="json", exclude_none=True)})
    elif selected == "agentops-d04-note-same-session":
        if minimal:
            unexecuted.append("original PII-backed note write and real same-session subsequent recall")
        else:
            ctx = context(0, "public-save-note")
            contexts.append(ctx)
            note = "Crash-loop investigated; no restart approved yet."
            output = immediate(FunctionTool(func=longterm.save_incident_note).run_async(
                args={"incident_id": "INC-002", "note": note}, tool_context=ctx))
            observe("agent.longterm.save_incident_note.sdk_function_tool", {"incident_id": "INC-002", "note": note}, output)
            snapshot("after-save")
            ctx = context(1, "public-recall-note")
            contexts.append(ctx)
            call(longterm.recall_incident_context, incident_id="INC-002", tool_context=ctx)
    elif selected == "agentops-d05-structured-inventory":
        contexts.append(context(0))
        incident = call(tools.get_incident, incident_id="INC-002")["incident"]
        call(tools.search_service_logs, service=incident["service"], query="", limit=20)
        call(memory.get_runbook, slug=incident["runbook"])
        observe("agent.models.TriageReport.model_json_schema", {}, modules["models"].TriageReport.model_json_schema())
    elif selected == "agentops-d06-keyword-retrieval":
        contexts.append(context(0))
        call(memory.search_runbooks, query="uptime heap leak", limit=2)
    else:
        raise ValueError("unsupported_development_recipe")
    after = snapshot("after")
    stream.close()
    original_imports, environment_imports = {}, {}
    source_root, environment_root = Path(inputs["source_root"]), Path(inputs["environment_root"])
    environment = json.loads(Path(inputs["environment_manifest"]).read_bytes())
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(source_root):
            rel = path.relative_to(source_root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != inputs["source_hashes"].get(rel):
                raise ValueError("imported_original_source_changed")
            original_imports[rel] = digest
        elif path.is_relative_to(environment_root):
            rel = path.relative_to(environment_root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != environment["files"].get(rel, {}).get("sha256"):
                raise ValueError("imported_frozen_dependency_changed")
            environment_imports[rel] = digest
    result = {"schema_version": "agentops-component-reference-actor/1", "id": selected,
              "status": "original_component_recipe_executed", "trace": trace,
              "before_state": before, "after_state": after, "identity": identity,
              "original_imported_files_verified": original_imports,
              "dependency_imported_files_verified": environment_imports,
              "denials": counts, "private_evaluator_probe_blocked": private_probe,
              "component_profile": inputs.get("component_profile"), "unexecuted_component_obligations": unexecuted,
              "original_app_executed": False, "model_requests": 0,
              "full_application_result": "unknown",
              "dependency_profile": inputs["dependency_profile"],
              "interventions": ["fixed public recipe controller", "direct original read functions bypass resilience wrappers",
                                "auxiliary SDK context carrier, no original App", "only immediate SDK coroutines; external waits refused",
                                "explicit frozen pywin32 import paths because isolated -S omits .pth execution"]}
    write_new(out / "actor-output.json", result)
    print(json.dumps({"id": selected, "status": result["status"], "original_app_executed": False,
                      "model_requests": 0, "full_application_result": "unknown"}))


if __name__ == "__main__":
    main()
