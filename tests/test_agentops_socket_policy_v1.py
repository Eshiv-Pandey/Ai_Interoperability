"""Authored observer checks; no AgentOps imports or application requests."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from agentops_socket_policy_v1 import OfflineSocketPolicy, SOURCE_SHA256
from check_agentops_socket_policy_v1 import check_policy
from check_agentops_effect_v3 import check_record, seed_snapshot

SOURCE = ROOT / "docs/research/source-evidence/agentops-socket-policy-v1/source/urllib3-util-connection.py"


def policy_fixture(*, port=None):
    return {"schema_version": "agentops-offline-socket-policy/1",
            "capability_source": {"installed_path": "/var/tmp/authored/external/runtime/venv/lib/python3.13/site-packages/urllib3/util/connection.py",
                                  "bytes": 4444, "sha256": SOURCE_SHA256},
            "listener_port": port, "unexpected": [], "internal_socketpairs": [],
            "listener_binds": [] if port is None else [{"event": "socket.bind", "address": ["127.0.0.1", port],
                                                        "family": 2, "socket_type": 1}],
            "denied_capability_probes": [{"event": "socket.bind", "address": ["::1", 0], "family": 10,
                "socket_type": 1, "action": "blocked", "function": "_has_ipv6", "phase": "module-import",
                "source_sha256": SOURCE_SHA256}]}


class PolicyTests(unittest.TestCase):
    def test_pinned_import_is_still_denied_but_ordinary_calls_are_not_excused(self):
        # Import the exact captured source within a minimal authored package.
        # Its relative type/exception imports are inert stubs, not an SDK mock.
        base = ROOT / "tmp" / ("authored-socket-policy-" + uuid.uuid4().hex)
        folder = base / "urllib3/util"
        folder.mkdir(parents=True)
        (base / "urllib3/__init__.py").write_text("")
        (folder / "__init__.py").write_text("")
        (base / "urllib3/exceptions.py").write_text("class LocationParseError(Exception): pass\n")
        (base / "urllib3/_base_connection.py").write_text("_TYPE_SOCKET_OPTIONS = object\n")
        (folder / "timeout.py").write_text("_DEFAULT_TIMEOUT = object()\n_TYPE_TIMEOUT = object\n")
        (folder / "connection.py").write_bytes(SOURCE.read_bytes())
        code = '''
import json, pathlib, socket, sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
from agentops_socket_policy_v1 import OfflineSocketPolicy
source = pathlib.Path(sys.argv[2]) / 'urllib3/util/connection.py'
policy = OfflineSocketPolicy(source)
sys.addaudithook(policy.audit)
import urllib3.util.connection as module
assert module.HAS_IPV6 is False
initial = len(policy.record['denied_capability_probes'])
assert initial == int(socket.has_ipv6)
# Calling the same exact helper after module initialization must be unexpected.
module._has_ipv6('::1')
for event, address in [('socket.bind', ('127.0.0.1', 0)), ('socket.connect', ('127.0.0.1', 9)),
                       ('socket.connect', ('203.0.113.1', 443))]:
    with socket.socket() as sock:
        try:
            getattr(sock, event.split('.')[1])(address)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Unexpected operation escaped the guard')
assert len(policy.record['unexpected']) == initial + 3
assert len(policy.record['denied_capability_probes']) == initial
print(json.dumps(policy.record))
'''
        result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT / "scripts"), str(base)],
                                capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        value = json.loads(result.stdout)
        self.assertEqual(len(value["listener_binds"]), 0)
        self.assertTrue(all(row["stack"] for row in value["unexpected"]))

    def test_modified_source_is_refused_before_guard_installation(self):
        with patch.object(Path, "read_bytes", return_value=SOURCE.read_bytes() + b"\n"):
            with self.assertRaisesRegex(ValueError, "reviewed pin"):
                OfflineSocketPolicy(SOURCE)

    def test_valid_native_and_http_records(self):
        self.assertEqual(check_policy(policy_fixture())["blocked_capability_probes"], 1)
        self.assertEqual(check_policy(policy_fixture(port=18761), listener_port=18761)["listener_binds"], 1)
        without_ipv6 = policy_fixture()
        without_ipv6["denied_capability_probes"] = []
        self.assertEqual(check_policy(without_ipv6)["blocked_capability_probes"], 0)

    def test_forged_exemptions_fail(self):
        for key, value in (("event", "socket.connect"), ("address", ["::1", 1]), ("address", ["0.0.0.0", 0]),
                           ("action", "allowed"), ("family", 2), ("socket_type", True),
                           ("function", "create_connection"), ("phase", "application-call"), ("source_sha256", "0" * 64)):
            with self.subTest(key=key, value=value):
                record = policy_fixture()
                record["denied_capability_probes"][0][key] = value
                with self.assertRaises(ValueError):
                    check_policy(record)
        for field in ("unexpected", "internal_socketpairs", "listener_binds"):
            record = policy_fixture()
            record[field].append({"event": "socket.connect"})
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_policy(record)
        duplicate = policy_fixture()
        duplicate["denied_capability_probes"] *= 2
        with self.assertRaises(ValueError):
            check_policy(duplicate)

    def test_unrelated_effects_and_legacy_failure_are_still_rejected(self):
        sys.path.insert(0, str(ROOT / "tests"))
        from test_agentops_effect_checker import authored_profile
        seed = seed_snapshot(ROOT / "external/agentops-c806b7f1/agents/data/incidents.db")
        profile = authored_profile(seed)
        profile.update(schema_version="agentops-passive-upstream-observation/3", socket_policy=policy_fixture())
        self.assertEqual(check_record(profile, seed)["new_audit_rows"], 1)
        forged = copy.deepcopy(profile)
        forged["observations"][3]["database"]["tables"]["audit_log"].append(
            dict(forged["observations"][3]["database"]["tables"]["audit_log"][0], id=2))
        with self.assertRaises(ValueError):
            check_record(forged, seed)
        legacy = json.loads((ROOT / "runs/agentops-native-eligibility/linux-persistent-v7/workspace/runs/agentops-native-eligibility/native-probe-v6/passive-profile.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "profile version"):
            check_record(legacy, seed)


if __name__ == "__main__":
    unittest.main()
