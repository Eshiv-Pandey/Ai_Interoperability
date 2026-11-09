"""Constructed state/registry tests only; no SDK imports or native enablement."""
import types
import unittest
from dataclasses import replace

from interoperability.ap2_hp_gemini_client_state_v1 import (
    API_METHODS, HTTP_METHODS, ClientStateRefused, ConstructorClientLease, SuppliedHttp1Profile,
)


class ClientStateChecks(unittest.TestCase):
    def setUp(self):
        class Backend:
            def connect_tcp(self, *args, **kwargs):
                raise AssertionError("Constructed tests cannot connect")
            def connect_unix_socket(self, *args, **kwargs):
                raise AssertionError("Constructed tests cannot connect")
        class Pool:
            def __init__(self):
                self._proxy = self._uds = None
                self._http1, self._http2, self._retries = True, False, 0
                self._network_backend = Backend()
            def handle_request(self, request):
                raise AssertionError("Constructed tests cannot transmit")
        class Transport:
            def __init__(self):
                self._pool = Pool()
            def handle_request(self, request):
                raise AssertionError("Constructed tests cannot transmit")
        class BaseHttp:
            def __init__(self):
                self._auth = None
                self._event_hooks = {"request": [], "response": []}
                self._default_encoding = "utf-8"
                self._mounts = {"constructed-pattern": None}
                self._transport = Transport()
            def request(self, *args, **kwargs): pass
            def build_request(self, *args, **kwargs): pass
            def send(self, *args, auth=None, **kwargs): pass
            def _send_handling_auth(self, *args, **kwargs): pass
            def _send_handling_redirects(self, *args, **kwargs): pass
            def _send_single_request(self, *args, **kwargs): pass
            def _transport_for_url(self, *args, **kwargs): pass
            def _build_request_auth(self, *args, **kwargs): pass
            def _set_timeout(self, *args, **kwargs): pass
        class Http(BaseHttp):
            pass
        class Api:
            def __init__(self, vertexai=None, error=None):
                if error is not None:
                    raise error
                self.vertexai = vertexai
                self._httpx_client = Http()
            def _request_once(self, *args, **kwargs): pass
        class Url: pass
        class Headers: pass
        class Stream: pass
        class Request:
            def __init__(self):
                self.url, self.headers, self.stream = Url(), Headers(), Stream()
                self.extensions = {"timeout": {"connect": 5.0, "read": None, "write": 5, "pool": 5.0}}
        self.Api, self.Http, self.BaseHttp = Api, Http, BaseHttp
        self.Transport, self.Pool, self.Backend = Transport, Pool, Backend
        self.Request = Request
        classes = (Api, Http, BaseHttp, Transport, Pool, Backend, Request, Url, Headers, Stream)
        methods = {(Api, name): getattr(Api, name) for name in API_METHODS}
        methods.update({(Http, name): getattr(Http, name) for name in HTTP_METHODS})
        methods.update({(cls, "handle_request"): cls.handle_request for cls in (Transport, Pool)})
        methods.update({(Backend, name): getattr(Backend, name) for name in ("connect_tcp", "connect_unix_socket")})
        self.profile = SuppliedHttp1Profile(Api, Http, Http.__mro__, Transport, Pool, Backend,
            Request, Url, Headers, Stream, methods, {cls: dict(cls.__dict__) for cls in classes})
        self.lease = ConstructorClientLease(self.profile)

    def tearDown(self):
        if self.lease.installed and not self.lease.restored:
            self.assertTrue(self.lease.restore())

    def initialized(self):
        self.lease.install()
        api = self.Api()
        return api, api._httpx_client, self.Request()

    def test_original_nonvertex_none_and_false_are_enrolled(self):
        self.lease.install()
        for mode in (None, False):
            api = self.Api(vertexai=mode)
            self.assertTrue(self.lease.validate_before_transmission(api, api._httpx_client, self.Request()))

    def test_arbitrary_falsey_and_vertex_modes_are_not_enrolled(self):
        self.lease.install()
        for mode in (0, "", [], True):
            with self.assertRaises(ClientStateRefused):
                self.Api(vertexai=mode)
        self.assertEqual(self.lease.report()["enrolled_api_clients"], 0)

    def test_constructor_exception_is_preserved_and_not_enrolled(self):
        self.lease.install()
        original = RuntimeError("constructed constructor failure")
        with self.assertRaises(RuntimeError) as raised:
            self.Api(error=original)
        self.assertIs(raised.exception, original)
        self.assertEqual(self.lease.active, 0)
        self.assertEqual(len(self.lease.clients), 0)

    def test_client_created_before_owned_constructor_is_refused(self):
        api = self.Api()
        self.lease.install()
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(api, api._httpx_client, self.Request())

    def test_swapped_http_client_cannot_reuse_enrollment(self):
        api, client, request = self.initialized()
        api._httpx_client = self.Http()
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(api, api._httpx_client, request)

    def test_instance_bound_shadow_is_refused(self):
        api, client, request = self.initialized()
        client._send_single_request = types.MethodType(self.BaseHttp._send_single_request, client)
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(api, client, request)

    def test_inherited_class_alias_change_is_refused(self):
        api, client, request = self.initialized()
        original = self.BaseHttp.send
        self.BaseHttp.send = lambda self, request: None
        try:
            with self.assertRaises(ClientStateRefused):
                self.lease.validate_before_transmission(api, client, request)
        finally:
            self.BaseHttp.send = original

    def test_same_function_code_replacement_is_refused(self):
        api, client, request = self.initialized()
        function = self.BaseHttp.send
        original = function.__code__
        function.__code__ = original.replace(co_exceptiontable=b"\x00")
        try:
            with self.assertRaises(ClientStateRefused):
                self.lease.validate_before_transmission(api, client, request)
        finally:
            function.__code__ = original

    def test_in_place_keyword_default_mutation_is_refused(self):
        api, client, request = self.initialized()
        function = self.BaseHttp.send
        original = function.__kwdefaults__["auth"]
        function.__kwdefaults__["auth"] = object()
        try:
            with self.assertRaises(ClientStateRefused):
                self.lease.validate_before_transmission(api, client, request)
        finally:
            function.__kwdefaults__["auth"] = original

    def test_owned_constructor_code_mutation_is_refused(self):
        api, client, request = self.initialized()
        function = self.lease.replacement
        original = function.__code__
        function.__code__ = original.replace(co_exceptiontable=b"")
        try:
            with self.assertRaises(ClientStateRefused):
                self.lease.validate_before_transmission(api, client, request)
        finally:
            function.__code__ = original

    def test_equal_unenrolled_api_cannot_reuse_identity_enrollment(self):
        self.Api.__eq__ = lambda api, other: type(other) is self.Api
        self.Api.__hash__ = lambda api: 1
        snapshots = {cls: dict(values) for cls, values in self.profile.class_members.items()}
        snapshots[self.Api] = dict(self.Api.__dict__)
        self.profile = replace(self.profile, class_members=snapshots)
        self.lease = ConstructorClientLease(self.profile)
        api, client, request = self.initialized()
        other = object.__new__(self.Api)
        other.vertexai, other._httpx_client = None, client
        self.assertEqual(other, api)
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(other, client, request)

    def test_fake_pool_with_matching_flags_is_refused(self):
        api, client, request = self.initialized()
        real = client._transport._pool
        client._transport._pool = types.SimpleNamespace(**real.__dict__)
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(api, client, request)

    def test_custom_backend_is_refused(self):
        api, client, request = self.initialized()
        client._transport._pool._network_backend = object()
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(api, client, request)

    def test_http2_retry_bool_and_proxy_state_are_refused(self):
        api, client, request = self.initialized()
        pool = client._transport._pool
        for field, value in (("_http2", True), ("_retries", 1), ("_retries", False), ("_proxy", object()), ("_uds", "x")):
            original = getattr(pool, field)
            setattr(pool, field, value)
            try:
                with self.assertRaises(ClientStateRefused):
                    self.lease.validate_before_transmission(api, client, request)
            finally:
                setattr(pool, field, original)

    def test_mounted_transport_auth_hooks_and_callable_encoding_refuse(self):
        api, client, request = self.initialized()
        for field, value in (("_mounts", {"x": self.Transport()}), ("_auth", object()),
                             ("_event_hooks", {"request": [lambda r: None], "response": []}),
                             ("_default_encoding", lambda b: "utf-8")):
            original = getattr(client, field)
            setattr(client, field, value)
            try:
                with self.assertRaises(ClientStateRefused):
                    self.lease.validate_before_transmission(api, client, request)
            finally:
                setattr(client, field, original)

    def test_trace_callback_and_malformed_timeouts_refuse(self):
        api, client, request = self.initialized()
        for extensions in ({"trace": lambda *args: None}, {"timeout": {"connect": 1}},
                           {"timeout": {"connect": True, "read": 1, "write": 1, "pool": 1}},
                           {"timeout": {"connect": float("inf"), "read": 1, "write": 1, "pool": 1}}):
            request.extensions = extensions
            with self.assertRaises(ClientStateRefused):
                self.lease.validate_before_transmission(api, client, request)

    def test_custom_request_component_type_is_refused(self):
        api, client, request = self.initialized()
        request.stream = object()
        with self.assertRaises(ClientStateRefused):
            self.lease.validate_before_transmission(api, client, request)

    def test_restore_does_not_overwrite_foreign_constructor(self):
        self.lease.install()
        owned = self.Api.__dict__["__init__"]
        foreign = lambda self: None
        self.Api.__init__ = foreign
        self.assertFalse(self.lease.restore())
        self.assertIs(self.Api.__dict__["__init__"], foreign)
        self.Api.__init__ = owned
        self.assertTrue(self.lease.restore())
        self.assertIs(self.Api.__dict__["__init__"], self.lease.original)

    def test_report_cannot_assert_source_or_native_qualification(self):
        self.lease.install()
        report = self.lease.report()
        self.assertFalse(report["source_identity_verified_by_this_module"])
        self.assertFalse(report["native_guard_installed"])
        self.assertFalse(report["transitive_sdk_fidelity_verified"])


if __name__ == "__main__":
    unittest.main()
