"""Zero-token V5 guard controls, including real CPython loopback audit events."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = load('_v5_guard_controls', 'scripts/ap2_native_shopper_actor_guard_v5.py')
V4 = load('_v4_shopper_controls', 'scripts/run_ap2_native_shopper_provider_v4.py')
V5 = load('_v5_shopper_controls', 'scripts/run_ap2_native_shopper_provider_v5.py')

# This child creates only local constructed echo endpoints. The guard is
# installed inside the child, avoiding an irreversible hook in the test runner.
REAL_TRANSPORT_CHILD = r'''
import importlib.util,json,socket,sys
from pathlib import Path
guard_path, output = Path(sys.argv[1]), Path(sys.argv[2])
spec=importlib.util.spec_from_file_location('_real_loopback_guard',guard_path)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
listener.bind(('127.0.0.1',0));listener.listen(4)
port=listener.getsockname()[1]
udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.bind(('127.0.0.1',port));udp.settimeout(2)
ipv6=None;ipv6_status='unavailable'
if socket.has_ipv6:
    try:
        ipv6=socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
        ipv6.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,1)
        ipv6.bind(('::1',port,0,0));ipv6.listen(1);ipv6_status='available'
    except OSError:
        if ipv6 is not None:ipv6.close()
        ipv6=None
observed=[]
def observer(event, values):
    if event in g.NETWORK_EVENTS:
        address=(values[0],values[1]) if event=='socket.getaddrinfo' else values[1] if len(values)==2 else None
        observed.append({'event':event,'audit_values_count':len(values),
                         'address_length':len(address) if isinstance(address,tuple) else None,
                         'host_type':type(address[0]).__name__ if isinstance(address,tuple) and address else None,
                         'port_type':type(address[1]).__name__ if isinstance(address,tuple) and len(address)>1 else None})
sys.addaudithook(observer)
denied=g.install_actor_guard('http://127.0.0.1:'+str(port),output=output,protected_root=output)
successes=[]
for label,host,service in [('str-ipv4','127.0.0.1',port),('bytes-host-str-service',b'127.0.0.1',str(port)),
                           ('bytes-host-bytes-service',b'127.0.0.1',str(port).encode('ascii'))]:
    with socket.create_connection((host,service),timeout=2) as client:
        client.sendall(b'constructed-loopback')
        peer,_=listener.accept()
        with peer:
            assert peer.recv(64)==b'constructed-loopback'
    successes.append(label)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
    client.sendto(b'constructed-udp-payload',('127.0.0.1',port))
    assert udp.recvfrom(64)[0]==b'constructed-udp-payload'
successes.append('udp-sendto')
if ipv6 is not None:
    with socket.socket(socket.AF_INET6,socket.SOCK_STREAM) as client:
        client.settimeout(2);client.connect(('::1',port,0,0));client.sendall(b'constructed-ipv6')
        peer,_=ipv6.accept()
        with peer:assert peer.recv(64)==b'constructed-ipv6'
    successes.append('ipv6-loopback')
    ipv6_status='observed'
blocked=[]
for label,operation in [('external-dns',lambda:socket.getaddrinfo('NEVER_RETAIN_THIS_SECRET.example.invalid',port)),
                        ('external-connect',lambda:socket.create_connection(('192.0.2.1',port),timeout=.1)),
                        ('undeclared-loopback-port',lambda:socket.getaddrinfo('127.0.0.1',1 if port!=1 else 2))]:
    try:operation()
    except PermissionError as error:
        assert str(error)=='owned_user_actor_external_network_denied';blocked.append(label)
    else:raise AssertionError('guard permitted '+label)
try:(output/'.env').read_bytes()
except PermissionError as error:assert str(error)=='owned_user_actor_private_read_denied'
else:raise AssertionError('private read permitted')
listener.close();udp.close()
if ipv6 is not None:ipv6.close()
records=[json.loads(line) for line in (output/'actor-network-denials.jsonl').read_bytes().splitlines()]
print(json.dumps({'successes':successes,'blocked':blocked,'ipv6_status':ipv6_status,
                  'denials':denied,'diagnostics':records,'observed_socket_audit_shapes':observed,
                  'application_calls':0,'provider_calls':0,'loopback_listeners_closed':True}))
'''


class PureNetworkClassificationControls(unittest.TestCase):
    def test_only_declared_loopback_equivalent_host_and_port_types_pass(self):
        for event in sorted(G.NETWORK_EVENTS):
            for host in ('127.0.0.1', 'localhost', '::1', b'127.0.0.1', b'localhost', b'::1'):
                for port in (8002, '8002', b'8002'):
                    with self.subTest(event=event, host=host, port=port):
                        values = (host, port, 0, 0, 0) if event == 'socket.getaddrinfo' else (object(), (host, port))
                        result = G.classify_network_event(event, values, {8001, 8002, 8003, 12345})
                        self.assertTrue(result['allowed'])
                        self.assertEqual(result['normalized_port'], 8002)
                        self.assertIn(result['normalized_host'], G.LOOPBACK_NAMES)

    def test_other_addresses_services_and_json_type_confusion_remain_denied(self):
        cases = [('127.0.0.2', 8002), ('127.0.0.1.evil.invalid', 8002), ('example.invalid', 8002),
                 ('192.0.2.1', 8002), ('::ffff:127.0.0.1', 8002), (b'\xff', 8002),
                 ('127.0.0.1', 'https'), ('127.0.0.1', True), ('127.0.0.1', 8002.0),
                 ('127.0.0.1', 8004), ('127.0.0.1', 0), ('127.0.0.1', 65536),
                 (['127.0.0.1'], 8002), ('127.0.0.1', [8002])]
        for host, port in cases:
            with self.subTest(host=host, port=port):
                self.assertFalse(G.classify_network_event('socket.connect', (object(), (host, port)), {8002})['allowed'])

    def test_documented_sendto_address_position_and_malformed_shapes(self):
        result = G.classify_network_event('socket.sendto', (object(), ('127.0.0.1', 8002)), {8002})
        self.assertTrue(result['allowed'])
        for values in ((object(), b'payload', ('127.0.0.1', 8002)), (object(),), (),
                       (object(), ['127.0.0.1', 8002]), (object(), ('127.0.0.1', 8002, 0)),
                       [object(), ('127.0.0.1', 8002)]):
            self.assertFalse(G.classify_network_event('socket.sendto', values, {8002})['allowed'])
        with self.assertRaisesRegex(ValueError, 'unsupported_socket_audit_event'):
            G.classify_network_event('socket.send', (object(), b'payload'), {8002})

    def test_ipv6_zero_scope_and_flow_only(self):
        self.assertTrue(G.classify_network_event('socket.connect', (object(), ('::1', 8002, 0, 0)), {8002})['allowed'])
        for address in (('::1', 8002, 1, 0), ('::1', 8002, 0, 1), ('::1', 8002, False, 0),
                        ('127.0.0.1', 8002, 0, 0)):
            self.assertFalse(G.classify_network_event('socket.connect', (object(), address), {8002})['allowed'])

    def test_diagnostic_preserves_safe_types_and_redacts_unrestricted_data(self):
        secret = 'NEVER_RETAIN_THIS_SECRET'
        values = (object(), (secret + '.example.invalid', '8002'))
        decision = G.classify_network_event('socket.connect', values, {8002})
        diagnostic = G.safe_network_diagnostic('socket.connect', values, decision)
        raw = json.dumps(diagnostic)
        self.assertNotIn(secret, raw)
        self.assertNotIn('object at', raw)
        self.assertTrue(diagnostic['sanitized_arguments']['host']['value_redacted'])
        self.assertEqual(diagnostic['sanitized_arguments']['port'], {'type': 'str', 'length': 4, 'safe_value': '8002'})
        bytes_values = (b'127.0.0.1', b'8002', 0, 0, 0)
        safe = G.safe_network_diagnostic('socket.getaddrinfo', bytes_values,
                                        G.classify_network_event('socket.getaddrinfo', bytes_values, {8002}))
        self.assertEqual(safe['sanitized_arguments']['host']['type'], 'bytes')
        self.assertEqual(safe['sanitized_arguments']['host']['safe_value'], '127.0.0.1')

    def test_diagnostic_count_and_bytes_are_bounded(self):
        counters = {'network_diagnostics_logged': 0, 'network_diagnostics_dropped': 0,
                    'network_diagnostic_bytes': 0, 'diagnostic_write_failures': 0}
        with tempfile.TemporaryDirectory() as temporary:
            recorder = G.DenialRecorder(Path(temporary), counters)
            values = (object(), ('example.invalid', 8002))
            decision = G.classify_network_event('socket.connect', values, {8002})
            for _ in range(G.MAX_DIAGNOSTICS + 2):
                recorder.record('socket.connect', values, decision)
            raw = recorder.path.read_bytes()
            self.assertEqual(len(raw.splitlines()), G.MAX_DIAGNOSTICS)
            self.assertEqual(counters['network_diagnostics_logged'], G.MAX_DIAGNOSTICS)
            self.assertEqual(counters['network_diagnostics_dropped'], 2)
            self.assertEqual(counters['network_diagnostic_bytes'], len(raw))
            self.assertLessEqual(len(raw), G.MAX_DIAGNOSTIC_BYTES)


class RealLoopbackTransportControls(unittest.TestCase):
    def test_real_ipv4_bytes_hostname_service_udp_and_available_ipv6(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = {k: v for k, v in os.environ.items() if not k.startswith('GOOGLE_')}
            completed = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', REAL_TRANSPORT_CHILD,
                                        str(ROOT / 'scripts/ap2_native_shopper_actor_guard_v5.py'), temporary],
                                       env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stderr.decode('utf-8', errors='replace'))
            proof = json.loads(completed.stdout)
            self.assertEqual(proof['successes'][:4], ['str-ipv4', 'bytes-host-str-service', 'bytes-host-bytes-service', 'udp-sendto'])
            self.assertIn(proof['ipv6_status'], ('observed', 'unavailable'))
            if proof['ipv6_status'] == 'observed':
                self.assertIn('ipv6-loopback', proof['successes'])
            self.assertEqual(proof['denials']['external_network'], 3)
            self.assertEqual(proof['denials']['private_reads'], 1)
            self.assertEqual(proof['denials']['network_diagnostics_logged'], 3)
            self.assertEqual(proof['denials']['network_diagnostics_dropped'], 0)
            self.assertEqual(proof['denials']['diagnostic_write_failures'], 0)
            self.assertEqual(len(proof['diagnostics']), 3)
            self.assertNotIn('NEVER_RETAIN_THIS_SECRET', json.dumps(proof))
            shapes = proof['observed_socket_audit_shapes']
            self.assertTrue(any(s['event'] == 'socket.getaddrinfo' and s['host_type'] == 'bytes' for s in shapes))
            self.assertTrue(any(s['event'] == 'socket.getaddrinfo' and s['port_type'] == 'str' for s in shapes))
            self.assertTrue(any(s['event'] == 'socket.getaddrinfo' and s['port_type'] == 'bytes' for s in shapes))
            self.assertTrue(any(s['event'] == 'socket.sendto' and s['audit_values_count'] == 2 for s in shapes))
            self.assertEqual(proof['application_calls'], 0)
            self.assertEqual(proof['provider_calls'], 0)
            self.assertTrue(proof['loopback_listeners_closed'])
            # Retain optional concrete transport witnesses in an exclusively
            # allocated control directory, never overwrite earlier output.
            receipt_dir = os.environ.get('AP2_V5_CONTROL_RECEIPTS')
            if receipt_dir:
                base = Path(receipt_dir)
                base.mkdir(parents=True, exist_ok=True)
                with (base / 'real-loopback-transport.json').open('x', encoding='utf-8') as stream:
                    json.dump(proof, stream, indent=2, sort_keys=True)
                    stream.write('\n')


class ProspectiveV5WiringControls(unittest.TestCase):
    def test_public_facts_worker_selection_and_original_bounds(self):
        old, new = V4.fixed_plan_fields(), V5.fixed_plan_fields()
        self.assertEqual(new['public_human_facts'], V5.W.public_facts())
        self.assertEqual(new['public_human_facts']['case_id'], 'ap2-native-shopper-provider-v5-correct-human')
        for field in old['public_human_facts']:
            if field != 'case_id':
                self.assertEqual(old['public_human_facts'][field], new['public_human_facts'][field])
        self.assertEqual(new['limits'], old['limits'])
        self.assertEqual(new['prospective_successor_to_run'], 43074319113)
        self.assertEqual(new['selected_worker_relative_path'], 'scripts/ap2_native_shopper_provider_worker_v3.py')
        self.assertEqual(V5.worker_command(Path('/venv/bin/python'), Path('/facts'), Path('/source'), Path('/output'))[2], str(V5.WORKER))
        self.assertTrue(V5.public_facts_preflight(new)['exact_public_field_agreement'])
        self.assertIn('scripts/ap2_native_shopper_actor_guard_v5.py', V5.OWNED)
        self.assertIn('scripts/ap2_native_shopper_provider_worker_v2.py', V5.OWNED)

    def test_original_public_actor_and_application_functions_are_preserved(self):
        old = ast.parse(V4.WORKER.read_text(encoding='utf-8'))
        new_source = V5.WORKER.read_text(encoding='utf-8').replace('ap2-native-shopper-provider-worker/3', 'ap2-native-shopper-provider-worker/2')
        new = ast.parse(new_source)
        for function in ('public_price_check', 'public_reply', 'visible_final_text', 'application'):
            a = next(n for n in old.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == function)
            b = next(n for n in new.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == function)
            self.assertEqual(ast.dump(a, include_attributes=False), ast.dump(b, include_attributes=False), function)

    def test_prepare_binds_guard_worker_and_detects_guard_snapshot_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan_dir = Path(temporary) / 'plan'
            V5.prepare(plan_dir)
            plan = V5.check_plan(plan_dir)
            guard_name = 'scripts/ap2_native_shopper_actor_guard_v5.py'
            self.assertEqual(plan['owned_sources'][guard_name], V5.H.digest((ROOT / guard_name).read_bytes()))
            snapshot = plan_dir / 'owned-source' / guard_name
            snapshot.write_bytes(b'constructed guard drift')
            with self.assertRaisesRegex(ValueError, 'prospective_owned_source_or_retained_snapshot_changed'):
                V5.check_plan(plan_dir)

    def test_controls_import_no_original_application_sdk_or_provider(self):
        self.assertFalse(any(name == 'roles' or name.startswith(('roles.', 'google.adk', 'google.genai')) for name in sys.modules))


if __name__ == '__main__':
    unittest.main()
