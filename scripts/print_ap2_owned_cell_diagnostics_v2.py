"""Print bounded, allowlisted owned diagnostics without raw application output."""
from __future__ import annotations

import argparse
import ast
import builtins
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'runs/ap2-environment-preparation/source-stage-v1/manifest.json'
STAGE_SHA = '78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463'
MAX_INPUT_BYTES = 256 * 1024
MAX_OUTPUT_BYTES = 32 * 1024
MAX_FRAMES = 12
MAX_GUARD_ROWS = 8
MAX_STAGE_ROWS = 12
STAGES = {
    'before_declared_public_certificate_admission', 'declared_public_certificate_admission_completed',
    'before_guarded_application_event_loop', 'application_entry', 'original_mandate_import_completed',
    'ADK_tool_context_import_completed', 'before_original_source_inventory',
    'original_source_inventory_completed', 'installed_runtime_inventory_completed',
}
GUARD_CODES = {
    'actor_private_evaluator_or_saved_credential_read_denied',
    'native_actor_unowned_network_operation_denied', 'native_actor_unallocated_descendant_process_denied',
}
OPERATIONS = {'open', 'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.bind',
              'socket.sendto', 'subprocess.Popen', 'os.system'}
ERROR_TYPES = {name for name in dir(builtins) if isinstance(getattr(builtins, name), type)
               and issubclass(getattr(builtins, name), BaseException)} | {
    'SSLError', 'ValidationError', 'BridgeInitiationBoundary', 'ConnectError', 'ReadTimeout',
    'RemoteProtocolError', 'WriteError', 'ReadError', 'CancelledError',
}
REPOSITORY_FILES = {
    'src/interoperability/' + name for name in (
        '__init__.py', 'ap2_hp_original_binding_v1.py', 'ap2_hp_reference_execution_v1.py',
        'ap2_hp_reference_plan_v1.py', 'ap2_hp_durable_observer_v1.py',
        'ap2_application_coordinator_v5.py', 'ap2_application_profile_v5.py',
        'refinement_shared_lift_v2.py', 'refinement.py', 'refinement_oracle.py',
        'manifest.py', 'oracle.py',
    )
}
RUNTIME_FRAMES = {
    'urllib3/util/connection.py': {'_has_ipv6', 'create_connection'},
    'urllib3/connection.py': {'__init__', 'connect', '_new_conn'},
    'google/auth/compute_engine/_metadata.py': {'ping', 'is_on_gce', 'get', 'detect_gce_residency_linux'},
    'google/auth/_default.py': {'default', '_get_gce_credentials'},
    'google/adk/tools/tool_context.py': {'__init__'},
}


def bounded_int(value, low, high):
    return value if type(value) is int and low <= value <= high else None


def source_records():
    try:
        raw = STAGE.read_bytes()
        if hashlib.sha256(raw).hexdigest() != STAGE_SHA:
            return {}
        return {row['path']: row for row in json.loads(raw)['files'] if row['project'] == 'ap2'}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def safe_frame(frame, source):
    if type(frame) is not dict:
        return None
    raw_file, raw_function = frame.get('file'), frame.get('function')
    safe_file, functions = '<redacted_frame_path>', set()
    path, expected = None, None
    if type(raw_file) is str and raw_file.startswith('<REPOSITORY>/'):
        relative = raw_file[len('<REPOSITORY>/'):]
        owned_versioned = re.fullmatch(
            r'(?:scripts/(?:ap2_reference_development|ap2_public_certificate_guard|ap2_native_bridge_runtime|ap2_native_guard_policy|'
            r'run_ap2_native_bridge_matrix|evaluate_ap2_native_bridge_matrix)_v[0-9]{1,4}|'
            r'src/interoperability/ap2_native_transport_v[0-9]{1,4})\.py', relative)
        if relative in REPOSITORY_FILES or owned_versioned:
            path, safe_file = ROOT / relative, raw_file
    elif type(raw_file) is str and raw_file.startswith('<SOURCE>/'):
        relative = raw_file[len('<SOURCE>/'):]
        if relative in source and relative.endswith('.py'):
            path, expected, safe_file = STAGE.parent / 'ap2' / relative, source[relative], raw_file
    elif type(raw_file) is str and raw_file.startswith('<SITE_PACKAGES>/'):
        relative = raw_file[len('<SITE_PACKAGES>/'):]
        if relative in RUNTIME_FRAMES:
            safe_file, functions = raw_file, RUNTIME_FRAMES[relative]
    if path is not None:
        try:
            if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('unsafe_source')
            raw = path.read_bytes()
            if expected is not None and (len(raw) != expected['bytes']
                    or hashlib.sha256(raw).hexdigest() != expected['sha256']):
                raise ValueError('source_changed')
            tree = ast.parse(raw)
            functions = {node.name for node in ast.walk(tree)
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            functions.add('<lambda>')
        except (OSError, ValueError, SyntaxError, TypeError):
            safe_file, functions = '<redacted_frame_path>', set()
    return {'file': safe_file,
            'function': raw_function if type(raw_function) is str and raw_function in functions else '<redacted_function>',
            'line': bounded_int(frame.get('line'), 1, 10_000_000)}


def safe_frames(value, source):
    if type(value) is not list:
        return []
    return [row for frame in value[:MAX_FRAMES] if (row := safe_frame(frame, source)) is not None]


def safe_guard_path(value, source):
    if type(value) is not str:
        return None
    source_public = {'code/samples/certs/ds_cert_sdjwt.pem', 'code/samples/certs/issuer_cert_sdjwt.pem'}
    runtime_public = {'certifi/cacert.pem', 'grpc/_cython/_credentials/roots.pem', 'pip/_vendor/certifi/cacert.pem'}
    if value.startswith('<SOURCE>/') and value[len('<SOURCE>/'):] in source_public & source.keys():
        return value
    if value.startswith('<SITE_PACKAGES>/') and value[len('<SITE_PACKAGES>/'):] in runtime_public:
        return value
    if re.fullmatch(r'<REPOSITORY>/benchmark/ap2-native-bridge-development-v[0-9]{1,4}/evaluator\.json', value):
        return value
    return '<redacted_guard_path>'


def load_owned_file(cell, name, lines=False):
    path = cell / name
    try:
        if not path.exists():
            return 'absent', [] if lines else None
        if path.is_symlink() or path.resolve().parent != cell.resolve() or not path.is_file():
            return 'unsafe_file', [] if lines else None
        if path.stat().st_size > MAX_INPUT_BYTES:
            return 'input_bound_exceeded', [] if lines else None
        raw = path.read_bytes()
        if len(raw) > MAX_INPUT_BYTES:
            return 'input_bound_exceeded', [] if lines else None
        if lines:
            return 'read', [json.loads(row) for row in raw.splitlines() if row]
        return 'read', json.loads(raw)
    except (OSError, ValueError, TypeError):
        return 'unavailable_or_malformed', [] if lines else None


def diagnostic_rows(cell, returncode):
    cell = Path(cell).resolve()
    source = source_records()
    rows = [{'kind': 'owned_actor_returncode', 'returncode': bounded_int(returncode, -255, 255)}]
    status, failure = load_owned_file(cell, 'worker-failure.json')
    if status == 'read' and type(failure) is dict:
        error_type = failure.get('error_type')
        rows.append({'kind': 'owned_worker_failure',
                     'error_type': error_type if type(error_type) is str and error_type in ERROR_TYPES else '<redacted_error_type>',
                     'frames': safe_frames(failure.get('frames'), source)})
    else:
        rows.append({'kind': 'owned_worker_failure', 'status': status})
    status, guards = load_owned_file(cell, 'actor-guard-denials.jsonl', lines=True)
    if status != 'read':
        rows.append({'kind': 'owned_guard_diagnostics', 'status': status})
    else:
        for guard in guards[:MAX_GUARD_ROWS]:
            if type(guard) is not dict:
                continue
            endpoint = guard.get('network_endpoint')
            safe_endpoint = None
            if type(endpoint) is dict:
                host = endpoint.get('host')
                safe_endpoint = {'host': host if type(host) is str and host in {'127.0.0.1', '::1', 'localhost'} else '<redacted_external_host>',
                                 'port': bounded_int(endpoint.get('port'), 0, 65535),
                                 'socket_family': endpoint.get('socket_family') if type(endpoint.get('socket_family')) is int and endpoint.get('socket_family') in {2, 10, 23} else None,
                                 'socket_type': endpoint.get('socket_type') if type(endpoint.get('socket_type')) is int and endpoint.get('socket_type') in {1, 2} else None}
            operation, code = guard.get('operation'), guard.get('guard_code')
            rows.append({'kind': 'owned_guard_denial',
                         'operation': operation if type(operation) is str and operation in OPERATIONS else '<redacted_operation>',
                         'guard_code': code if type(code) is str and code in GUARD_CODES else '<redacted_guard_code>',
                         'path': safe_guard_path(guard.get('path'), source),
                         'network_endpoint': safe_endpoint, 'frames': safe_frames(guard.get('frames'), source)})
        if len(guards) > MAX_GUARD_ROWS:
            rows.append({'kind': 'owned_guard_diagnostics', 'status': 'row_bound_reached'})
    status, policy = load_owned_file(cell, 'native-guard-policy.json')
    if status == 'read' and type(policy) is dict:
        rows.append({'kind': 'owned_native_guard_policy',
                     'allowed_ipv6_capability_binds': bounded_int(policy.get('allowed_ipv6_capability_binds'), 0, 1),
                     'admitted_capability_sockets_closed': policy.get('admitted_capability_sockets_closed') is True,
                     'normalized_bytes_owned_operations': bounded_int(policy.get('normalized_bytes_owned_operations'), 0, 100000),
                     'source_unchanged': policy.get('source_unchanged') is True,
                     'public_platform_metadata_cached_before_actor_guard': policy.get('public_platform_metadata_cached_before_actor_guard') is True,
                     'guarded_platform_metadata_equals_cached_value': policy.get('guarded_platform_metadata_equals_cached_value') is True})
    else:
        rows.append({'kind': 'owned_native_guard_policy', 'status': status})
    status, stages = load_owned_file(cell, 'worker-stages.jsonl', lines=True)
    if status != 'read':
        rows.append({'kind': 'owned_stage_diagnostics', 'status': status})
    else:
        labels = [row.get('stage') if type(row) is dict else None for row in stages[:MAX_STAGE_ROWS]]
        rows.append({'kind': 'owned_stage_labels', 'labels': [value if type(value) is str and value in STAGES else '<redacted_stage>' for value in labels]})
        if len(stages) > MAX_STAGE_ROWS:
            rows.append({'kind': 'owned_stage_diagnostics', 'status': 'row_bound_reached'})
    return rows


def print_diagnostics(cell, returncode, emit=print):
    emitted = 0
    for row in diagnostic_rows(cell, returncode):
        line = json.dumps(row, sort_keys=True, allow_nan=False)
        length = len(line.encode()) + 1
        if emitted + length > MAX_OUTPUT_BYTES - 128:
            emit('{"kind":"owned_diagnostics","status":"output_bound_reached"}')
            break
        emit(line)
        emitted += length


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cell', type=Path, required=True)
    parser.add_argument('--returncode', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        print_diagnostics(args.cell, args.returncode)
    except Exception:
        # Never echo arbitrary exception text or diagnostic input.
        print('{"kind":"owned_diagnostics","status":"unavailable"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
