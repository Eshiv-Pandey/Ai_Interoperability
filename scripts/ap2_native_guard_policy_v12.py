"""Narrow owned-host normalization and exact urllib3 capability admission.

This admits no connect, send, listen or descendant process. The only new
socket admission is one import-time bind by the hash-bound urllib3 helper.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import platform
import socket
from types import CodeType, FrameType

RELATIVE_SOURCE = 'urllib3/util/connection.py'
SOURCE_IDENTITY = {'bytes': 4444, 'sha256': '2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74'}
OWNED_HOSTS = {'127.0.0.1', '::1', 'localhost'}
OWNED_BYTES_HOSTS = {b'127.0.0.1': '127.0.0.1', b'::1': '::1', b'localhost': 'localhost'}
CODE_FIELDS = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals', 'co_stacksize',
               'co_flags', 'co_code', 'co_names', 'co_varnames', 'co_freevars', 'co_cellvars',
               'co_filename', 'co_name', 'co_qualname', 'co_firstlineno', 'co_linetable', 'co_exceptiontable')


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def normalized_owned_host(host):
    # No decoding, DNS suffix, case folding or arbitrary bytes acceptance.
    if type(host) is str and host in OWNED_HOSTS:
        return host
    if type(host) is bytes:
        return OWNED_BYTES_HOSTS.get(host)
    return None


def code_identity(code):
    constants = tuple(code_identity(value) if type(value) is CodeType else
                      (type(value).__module__, type(value).__qualname__, repr(value))
                      for value in code.co_consts)
    return tuple(getattr(code, name) for name in CODE_FIELDS) + (constants, tuple(code.co_lines()), tuple(code.co_positions()))


class NativeGuardPolicy:
    def __init__(self, site_packages):
        self.source = Path(site_packages).resolve() / RELATIVE_SOURCE
        if self.source.is_symlink() or self.source.resolve() != self.source or not self.source.is_file():
            raise ValueError('pinned_urllib3_capability_source_missing_or_linked')
        raw = self.source.read_bytes()
        if identity(raw) != SOURCE_IDENTITY:
            raise ValueError('pinned_urllib3_capability_source_changed')
        self.module_code = compile(raw, str(self.source), 'exec', dont_inherit=True)
        candidates = [value for value in self.module_code.co_consts
                      if type(value) is CodeType and value.co_name == '_has_ipv6']
        if len(candidates) != 1:
            raise ValueError('unique_pinned_urllib3_capability_function_required')
        self.function_identity = code_identity(candidates[0])
        self.module_identity = code_identity(self.module_code)
        self.admitted_sockets = []
        self.allowed_rows = []
        self.normalized_bytes_owned_operations = 0
        # CPython platform.platform() can run uname -p. Cache that public
        # environment metadata before the actor hook; allow no guarded child.
        self.platform_value = platform.platform()

    def admit_ipv6_capability_bind(self, event, values, caller):
        if event != 'socket.bind' or len(self.admitted_sockets) >= 1 or len(values) != 2:
            return False
        sock, address = values
        if (type(sock) is not socket.socket or type(address) is not tuple or address != ('::1', 0)
                or sock.family != socket.AF_INET6 or sock.type != socket.SOCK_STREAM
                or sock.proto != 0 or sock.fileno() < 0 or type(caller) is not FrameType):
            return False
        try:
            if sock.getsockname() != ('::', 0, 0, 0) or sock.get_inheritable():
                return False
        except OSError:
            return False
        parent = caller.f_back
        if (caller.f_code.co_filename != str(self.source) or caller.f_code.co_name != '_has_ipv6'
                or caller.f_lineno != 127 or code_identity(caller.f_code) != self.function_identity
                or parent is None or parent.f_lineno != 137
                or code_identity(parent.f_code) != self.module_identity):
            return False
        self.admitted_sockets.append(sock)
        self.allowed_rows.append({'operation': 'socket.bind', 'host': '::1', 'port': 0,
                                  'socket_family': int(socket.AF_INET6), 'socket_type': int(socket.SOCK_STREAM),
                                  'relative_source': RELATIVE_SOURCE, 'function': '_has_ipv6', 'line': 127,
                                  'module_import_line': 137, 'exact_source_and_code_identity_checked': True,
                                  'fresh_unbound_noninheritable_socket_checked': True})
        return True

    def receipt(self):
        return {'schema_version': 'ap2-native-guard-policy/12', 'source_relative_path': RELATIVE_SOURCE,
                'source_identity': SOURCE_IDENTITY,
                'source_unchanged': identity(self.source.read_bytes()) == SOURCE_IDENTITY,
                'allowed_ipv6_capability_binds': len(self.admitted_sockets),
                'capability_rows': self.allowed_rows,
                'admitted_capability_sockets_closed': all(sock.fileno() == -1 for sock in self.admitted_sockets),
                'normalized_bytes_owned_operations': self.normalized_bytes_owned_operations,
                'public_platform_metadata_cached_before_actor_guard': True,
                'guarded_platform_metadata_equals_cached_value': platform.platform() == self.platform_value,
                'scope': 'One exact import-time IPv6 bind only; exact owned loopback host literals; no new connect/send/listen/process allowance'}
