"""Original AgentOps factory and upstream offline model double over Uvicorn.

The test-agent construction is reproduced explicitly. This is a disclosed wire
fixture, not the unchanged pytest test or the full conversational agent.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import socket
import sys
import time

import agentops_native_probe_v2 as evidence


async def serve(output: Path, port: int) -> None:
    from agentops_socket_policy_v1 import OfflineSocketPolicy
    policy = OfflineSocketPolicy(listener_port=port)
    network_errors = policy.record['unexpected']
    internal_pairs = policy.record['internal_socketpairs']
    sys.addaudithook(policy.audit)
    result = {"schema_version": "agentops-http-service/1", "status": "failed",
              "observer_version": 2, "socket_policy": policy.record, "network_errors": network_errors, "internal_socketpairs": internal_pairs,
              "fixture": "Reproduced original confirmation agent with imported upstream model double"}
    model, seen = None, []
    try:
        # Environment and guard are in place before any app/SDK import.
        spec = importlib.util.spec_from_file_location(
            "agentops_original_test_server", evidence.PROJECT / "tests/test_server.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        from agent.config import settings
        import uvicorn

        if (settings.data_dir.resolve() != (evidence.SOURCE / "agents/data").resolve()
                or settings.state_dir.resolve() != output / "state"
                or settings.a2a_port != port or settings.a2a_host != "127.0.0.1"):
            raise ValueError("Fixture settings differ from the prepared isolated paths")
        model = module._ConfirmationLlm(model="confirmation-test")

        def capture_tool_context(*, tool, args, tool_context):
            del tool, args
            seen.append([tool_context.user_id, tool_context.session.id,
                         tool_context.invocation_id, tool_context.tool_confirmation is not None])

        agent = module.Agent(
            name="confirmation_test_agent",
            instruction="Call restart_service for the requested inventory restart.",
            model=model, tools=[module.actions.ACTION_TOOLS[0]],
            before_tool_callback=[module.validate_actions, capture_tool_context])
        app = module.server.create_app(agent)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                  log_level="info", timeout_graceful_shutdown=10,
                                  lifespan="on", access_log=True))
        task = asyncio.create_task(server.serve())
        deadline = time.monotonic() + 60
        while not server.started:
            if task.done():
                await task
                raise RuntimeError("Uvicorn stopped before startup")
            if time.monotonic() >= deadline:
                server.should_exit = True
                await task
                raise TimeoutError("Uvicorn startup deadline")
            await asyncio.sleep(0.05)
        evidence.write_json(output / "service-ready.json", {
            "started_at_utc": evidence.now(), "port": port,
            "state_dir": str(settings.state_dir), "source_factory": str(Path(module.server.__file__).resolve())})
        deadline = time.monotonic() + 240
        while not (output / "stop-requested.json").exists() and not task.done():
            if time.monotonic() >= deadline:
                result["watchdog_expired"] = True
                break
            await asyncio.sleep(0.05)
        server.should_exit = True
        await task
        if network_errors:
            raise RuntimeError("Unexpected network operations were attempted")
        if result.get("watchdog_expired"):
            raise TimeoutError("Fixture watchdog expired")
        result["status"] = "stopped"
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        result.update(model_double_calls=None if model is None else model.calls,
                      seen_contexts=seen, finished_at_utc=evidence.now())
        evidence.write_json(output / "service-result.json", result)
    if result["status"] != "stopped":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    target = evidence.within(args.output, evidence.WORKSPACE / "runs/agentops-http-control")
    asyncio.run(serve(target, args.port))
