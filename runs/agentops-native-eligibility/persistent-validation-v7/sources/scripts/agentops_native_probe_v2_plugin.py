"""Passive pytest observations for one unchanged upstream AgentOps test.

Loaded only by the explicit offline runner. No app/SDK function is replaced.
The JSON payload/results are Python values from the upstream SSE parser, not
byte-exact HTTP wire capture. Socket connections/listeners are forbidden here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import time

import pytest

from agentops_native_probe_v2 import (
    NODEID, SOURCE, TEST_NAME, WORKSPACE, database_snapshot, now, within, write_json,
)

OUTPUT = within(Path(os.environ["AGENTOPS_PROBE_OUTPUT"]), WORKSPACE / "runs/agentops-native-eligibility")
OBSERVATION = {"schema_version": "agentops-passive-upstream-observation/2", "nodeid": NODEID,
               "observations": [], "final_test_locals": {}, "errors": [],
               "capture_scope": "Main-thread upstream helper Python values; not raw HTTP bytes",
               "function_replacements": 0, "network_attempts": [],
               "internal_socketpair_operations": []}
REPORTS = []
SOCKET_SOURCE = Path(socket.__file__).resolve()


def audit(event, args):
    if event in {"socket.connect", "socket.bind"}:
        # Windows asyncio may build its self-wakeup pipe with stdlib socketpair.
        # Permit only that exact stdlib call stack and loopback address; ordinary
        # application/model loopback connections remain forbidden.
        address = args[1]
        frame = sys._getframe(1)
        while frame is not None:
            if (frame.f_code.co_name == "socketpair"
                    and Path(frame.f_code.co_filename).resolve() == SOCKET_SOURCE
                    and isinstance(address, tuple) and len(address) >= 2
                    and address[0] in {"127.0.0.1", "::1"}
                    and isinstance(address[1], int) and 0 <= address[1] <= 65535):
                OBSERVATION["internal_socketpair_operations"].append({"event": event, "address": list(address)})
                return
            frame = frame.f_back
        OBSERVATION["network_attempts"].append({"event": event})
        raise RuntimeError("The in-process offline control forbids socket connections/listeners")


sys.addaudithook(audit)


def clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def pytest_collection_modifyitems(session, config, items):
    del session, config
    if len(items) != 1 or items[0].nodeid != NODEID:
        raise pytest.UsageError("Probe is restricted to exactly the unchanged upstream confirmation node")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # Fixtures have completed; no application startup has yet run for this test.
    from agent.config import settings

    state = within(settings.state_dir, OUTPUT / "pytest-temp")
    dataset = within(settings.data_dir, OUTPUT / "pytest-temp")
    if state.exists():
        raise RuntimeError("Fresh isolated test unexpectedly has existing runtime state")
    write_json(OUTPUT / "isolated-seed-before.json",
               database_snapshot(dataset / "incidents.db", OUTPUT, "run"))
    helper_code = item.module._stream_rpc_results.__code__
    test_code = getattr(item.module, TEST_NAME).__code__
    expected_file = (SOURCE / "agents/python/tests/test_server.py").resolve()
    if Path(helper_code.co_filename).resolve() != expected_file or Path(test_code.co_filename).resolve() != expected_file:
        raise RuntimeError("Observed helper/test code does not originate in the pinned source test")
    if sys.getprofile() is not None:
        raise RuntimeError("An existing profiler would conflict with passive observation")

    def observe(frame, event, arg):
        if frame.f_code not in {helper_code, test_code}:
            return
        try:
            if frame.f_code is helper_code and event in {"call", "return"}:
                payload = clone(frame.f_locals["payload"])
                record = {"sequence": len(OBSERVATION["observations"]),
                          "event": "helper_" + event, "rpc_id": payload["id"],
                          "observed_at_utc": now(), "monotonic_ns": time.monotonic_ns(),
                          "payload": payload,
                          "database": database_snapshot(state / "incidents.db", OUTPUT, "run")}
                if event == "return":
                    record["results"] = clone(arg)
                OBSERVATION["observations"].append(record)
            elif frame.f_code is test_code and event == "return":
                values = frame.f_locals
                final = {name: clone(values[name]) for name in
                         ("task_id", "context_id", "rationale", "seen_contexts", "confirmation_call")
                         if name in values}
                if "model" in values:
                    final["model_calls"] = values["model"].calls
                OBSERVATION["final_test_locals"] = final
        except Exception as error:
            OBSERVATION["errors"].append({"event": event, "error": f"{type(error).__name__}: {error}"})

    sys.setprofile(observe)
    try:
        yield
    finally:
        sys.setprofile(None)


def pytest_runtest_logreport(report):
    REPORTS.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
                    "duration_seconds": report.duration,
                    "longrepr": str(report.longrepr) if report.longrepr is not None else None})


def pytest_sessionfinish(session, exitstatus):
    del session
    write_json(OUTPUT / "passive-profile.json", OBSERVATION)
    write_json(OUTPUT / "pytest-reports.json", {"schema_version": "agentops-upstream-pytest-reports/2",
               "exitstatus": int(exitstatus), "reports": REPORTS})
