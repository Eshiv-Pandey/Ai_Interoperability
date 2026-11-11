"""Constructed API doubles around exact retained public AP2 Task fixtures."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ap2-public-continuation-v1"
sys.path.insert(0, str(ROOT / "src"))


def fixture(name):
    raw = (FIXTURES / name).read_bytes()
    provenance = json.loads((FIXTURES / "provenance.json").read_bytes())
    record = next(row for row in provenance["fixtures"] if row["fixture"] == name)
    if hashlib.sha256(raw).hexdigest() != record["fixture_sha256"]:
        raise AssertionError("Retained public fixture changed: " + name)
    return json.loads(raw)


def load_helper():
    name = "interoperability.ap2_public_task_read_v1"
    leaf = ModuleType("google.adk.tools.tool_context")
    leaf.ToolContext = SimpleNamespace
    with patch.dict(sys.modules, {leaf.__name__: leaf}):
        spec = importlib.util.spec_from_file_location(name, ROOT / "src/interoperability/ap2_public_task_read_v1.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class RPCError(Exception):
    def __init__(self, code):
        super().__init__("Constructed SDK error with retained source error code " + str(code))
        self.error = SimpleNamespace(code=code, model_dump=lambda **kwargs: {"code": code})


@contextmanager
def sdk_doubles(task=None, failure=None, card=None):
    """No original SDK/application/model is invoked by these doubles."""
    calls = []
    raw_card = fixture("original-merchant-card.json") if card is None else card
    card_value = SimpleNamespace(url=raw_card["url"], protocol_version=raw_card["protocolVersion"])
    raw_task = fixture("v13-correct-pending-task.json") if task is None else deepcopy(task)
    task_value = SimpleNamespace(id=raw_task["id"], context_id=raw_task["contextId"],
                                 model_dump=lambda **kwargs: deepcopy(raw_task))
    async def get_agent_card():
        calls.append(("get_agent_card",))
        return card_value
    async def get_task(query):
        calls.append(("get_task", query.id, query.history_length))
        if failure is not None:
            raise failure
        return task_value
    class HttpClient:
        def __init__(self, **kwargs):
            calls.append(("http_client", kwargs))
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
    class Factory:
        def __init__(self, config):
            calls.append(("factory", config))
        def create(self, observed_card):
            calls.append(("create", observed_card))
            return SimpleNamespace(get_task=get_task)
    specs = {
        "httpx": {"AsyncClient": HttpClient, "Timeout": lambda value: value},
        "a2a.client.client": {"ClientConfig": lambda **kwargs: SimpleNamespace(**kwargs)},
        "a2a.client.client_factory": {"ClientFactory": Factory},
        "a2a.client.errors": {"A2AClientJSONRPCError": RPCError},
        "a2a.extensions.common": {"HTTP_EXTENSION_HEADER": "X-A2A-Extensions"},
        "a2a.types": {"TaskQueryParams": lambda **kwargs: SimpleNamespace(**kwargs)},
        "common.a2a_extension_utils": {"EXTENSION_URI": raw_card["capabilities"]["extensions"][0]["uri"]},
        "roles.shopping_agent.remote_agents": {"merchant_agent_client": SimpleNamespace(get_agent_card=get_agent_card)},
    }
    modules = {}
    for name, attributes in specs.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module
    helper = load_helper()
    modules["interoperability.ap2_public_task_read_v1"] = helper
    with patch.dict(sys.modules, modules):
        yield helper, calls
