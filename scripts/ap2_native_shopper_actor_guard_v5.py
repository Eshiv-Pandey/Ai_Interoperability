"""Bounded loopback-only audit guard with sanitized denied-address witnesses.

The pure classifier consumes CPython socket audit arguments, not packet data.
Only exact declared loopback names and numeric forms of declared ports pass.
No original application, SDK or provider is imported by this owned module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse

CLASSIFIER_SCHEMA = 'ap2-native-shopper-network-classification/5'
DIAGNOSTIC_SCHEMA = 'ap2-native-shopper-network-denial/5'
SEPARATION_SCHEMA = 'ap2-native-shopper-actor-separation/5'
NETWORK_EVENTS = frozenset(('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'))
LOOPBACK_NAMES = frozenset(('127.0.0.1', 'localhost', '::1'))
NATIVE_PORTS = frozenset((8001, 8002, 8003))
MAX_DIAGNOSTICS = 160
MAX_DIAGNOSTIC_BYTES = 262144
MAX_SINGLE_DIAGNOSTIC_BYTES = 4096


def normalize_host(value):
    if type(value) is bytes:
        try:
            value = value.decode('ascii')
        except UnicodeDecodeError:
            return None
    return value if type(value) is str and value in LOOPBACK_NAMES else None


def normalize_port(value):
    if type(value) is bytes:
        try:
            value = value.decode('ascii')
        except UnicodeDecodeError:
            return None
    if type(value) is str:
        if not 1 <= len(value) <= 5 or any(ch not in '0123456789' for ch in value):
            return None
        value = int(value)
    return value if type(value) is int and 1 <= value <= 65535 else None


def _address(event, values):
    # CPython documents socket.sendto as (self, address), excluding payload.
    # socket.connect emits (self, address); connect_ex uses that event in current
    # CPython, and the explicit alias is handled without assuming it is emitted.
    if type(values) is not tuple:
        return None
    if event == 'socket.getaddrinfo':
        return (values[0], values[1]) if len(values) == 5 else None
    if event in {'socket.connect', 'socket.connect_ex', 'socket.sendto'}:
        return values[1] if len(values) == 2 else None
    return None


def classify_network_event(event, values, allowed_ports):
    """Pure fail-closed classifier; it performs no DNS, connection or logging."""
    if event not in NETWORK_EVENTS:
        raise ValueError('unsupported_socket_audit_event')
    ports = frozenset(allowed_ports)
    if not ports or any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        raise ValueError('explicit_valid_numeric_ports_required')
    decision = {'schema_version': CLASSIFIER_SCHEMA, 'allowed': False,
                'reason': 'audit_argument_shape_invalid', 'normalized_host': None,
                'normalized_port': None, 'address_length': None}
    address = _address(event, values)
    if type(address) is not tuple or len(address) not in (2, 4):
        return decision
    decision['address_length'] = len(address)
    host, port = normalize_host(address[0]), normalize_port(address[1])
    decision.update(normalized_host=host, normalized_port=port)
    if host is None:
        decision['reason'] = 'host_not_declared_loopback'
    elif port is None:
        decision['reason'] = 'port_not_valid_numeric'
    elif len(address) == 4 and (host != '::1' or any(type(item) is not int or item != 0 for item in address[2:])):
        decision['reason'] = 'ipv6_scope_or_flow_not_declared'
    elif port not in ports:
        decision['reason'] = 'port_not_declared'
    else:
        decision.update(allowed=True, reason='declared_loopback_endpoint')
    return decision


def _safe_atom(value, *, host=False, port=False):
    # Never call arbitrary __repr__/__str__ or retain external names, payload,
    # credentials, bytes hashes or unrestricted argument strings.
    kind = ('str' if type(value) is str else 'bytes' if type(value) is bytes
            else 'int' if type(value) is int else 'bool' if type(value) is bool
            else 'none' if value is None else 'other')
    result = {'type': kind}
    if type(value) in (str, bytes):
        result['length'] = len(value)
    normalized = normalize_host(value) if host else normalize_port(value) if port else None
    if normalized is not None:
        result['safe_value'] = value.decode('ascii') if type(value) is bytes else value
    elif type(value) is int and not (host or port) and 0 <= value <= 65535:
        result['safe_value'] = value
    else:
        result['value_redacted'] = True
    return result


def safe_network_diagnostic(event, values, decision):
    """Expose exact safe loopback/port representation, redact all other data."""
    address = _address(event, values)
    safe = {'audit_values_type': 'tuple' if type(values) is tuple else 'other',
            'audit_values_count': len(values) if type(values) is tuple else None,
            'address_type': 'tuple' if type(address) is tuple else 'other'}
    if type(address) is tuple:
        safe['address_length'] = len(address)
        if address:
            safe['host'] = _safe_atom(address[0], host=True)
        if len(address) > 1:
            safe['port'] = _safe_atom(address[1], port=True)
        if len(address) == 4:
            safe['ipv6_flowinfo'] = _safe_atom(address[2])
            safe['ipv6_scope_id'] = _safe_atom(address[3])
    return {'schema_version': DIAGNOSTIC_SCHEMA, 'time': datetime.now(timezone.utc).isoformat(),
            'event': event, 'classification': dict(decision), 'sanitized_arguments': safe,
            'socket_object_or_send_payload_retained': False,
            'external_host_or_unrestricted_argument_retained': False}


class DenialRecorder:
    """An exclusively reserved, bounded diagnostic stream; denial stays closed."""
    def __init__(self, output, counters):
        self.path = Path(output) / 'actor-network-denials.jsonl'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('xb'):
            pass
        self.counters = counters
        self.lock = threading.Lock()

    def record(self, event, values, decision):
        raw = (json.dumps(safe_network_diagnostic(event, values, decision),
                          sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
        with self.lock:
            if (self.counters['network_diagnostics_logged'] >= MAX_DIAGNOSTICS
                    or len(raw) > MAX_SINGLE_DIAGNOSTIC_BYTES
                    or self.counters['network_diagnostic_bytes'] + len(raw) > MAX_DIAGNOSTIC_BYTES):
                self.counters['network_diagnostics_dropped'] += 1
                return
            try:
                with self.path.open('ab') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError:
                self.counters['diagnostic_write_failures'] += 1
            else:
                self.counters['network_diagnostics_logged'] += 1
                self.counters['network_diagnostic_bytes'] += len(raw)


def install_actor_guard(proxy_url, *, output, protected_root):
    """Install once in an owned worker; audit hooks cannot be uninstalled."""
    parsed = urlparse(proxy_url)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port
            or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError('owned_loopback_provider_required')
    ports = NATIVE_PORTS | {parsed.port}
    protected_root = Path(protected_root).resolve()
    denied = {'private_reads': 0, 'external_network': 0, 'descendants': 0,
              'network_diagnostics_logged': 0, 'network_diagnostics_dropped': 0,
              'diagnostic_write_failures': 0, 'network_diagnostic_bytes': 0}
    recorder = DenialRecorder(output, denied)

    def guard(event, values):
        if event == 'open' and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).absolute()
            name = path.name.casefold()
            if name == '.env' or name.startswith('gemini-api-key') or ('evaluator' in name and path.is_relative_to(protected_root)):
                denied['private_reads'] += 1
                raise PermissionError('owned_user_actor_private_read_denied')
        if event in NETWORK_EVENTS:
            decision = classify_network_event(event, values, ports)
            if decision['allowed'] is not True:
                denied['external_network'] += 1
                recorder.record(event, values, decision)
                raise PermissionError('owned_user_actor_external_network_denied')
        if event == 'subprocess.Popen' or event == 'os.system' or event.startswith('os.spawn'):
            denied['descendants'] += 1
            raise PermissionError('owned_user_actor_descendant_process_denied')

    sys.addaudithook(guard)
    return denied
