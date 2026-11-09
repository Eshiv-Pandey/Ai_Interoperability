# Original Gemini client construction and live dispatch

30 October 2026. The frozen transport remains unchanged and refuses native installation. The new [client-state component](../../src/interoperability/ap2_hp_gemini_client_state_v1.py) is an implementation step toward original SDK binding, not a complete source verifier or native guard.

## A source-derived compatibility correction

The original [catalog](../../runs/ap2-environment-preparation/source-stage-v1/ap2/code/samples/python/src/roles/merchant_agent/sub_agents/catalog_agent.py) constructs `genai.Client()` without a `vertexai` argument. The pinned [BaseApiClient constructor](../../runs/ap2-environment-preparation/installed-environment-v1/environment/Lib/site-packages/google/genai/_api_client.py) leaves ordinary API-key mode at `None`; it sets `True` when Vertex configuration selects that mode. The frozen transport's `vertexai is False` condition therefore refuses this source-derived default. The successor state checker accepts exactly `None` or `False`, while rejecting arbitrary falsey values. Actual mode/environment binding still belongs to the complete constructor proof.

## Implemented component

`SuppliedHttp1Profile` receives separately verified class/function/member identities. It checks their class footprints, MROs, function code/default-object identities and effective bound methods again at use. It requires an exact default HTTP client, no instance shadows, no custom auth or event hooks, a string encoding, direct mount entries, exact lower transport/pool/backend types, HTTP/1 enabled, HTTP/2 disabled, zero integer retries and no proxy/UDS. Request URL/header/byte-stream types must match the supplied classes; only the original timeout extension is accepted. `trace` callbacks and custom extensions are refused.

`ConstructorClientLease` delegates the supplied original API constructor with unchanged arguments, result and exceptions. Only a successful constructor and state check enroll its resulting API/HTTP objects. Before transmission, callers must verify both identities against that enrollment and repeat the state/request checks. Clients created before the lease or replaced afterward cannot reuse the enrollment. Restoration changes only the owned constructor and waits for active constructors; interference retains authority.

The [19 constructed tests](../../tests/test_ap2_hp_gemini_client_state_v1.py) passed in the once-only [state-v1 capture](../../runs/ap2-gemini-client-state-software/state-v1/result.json), with zero failures, errors or skips, exact declared membership and all two source/test inputs plus the copied driver unchanged. Source and driver review closed before allocation. They use synthetic classes and perform no SDK imports or sends. Supplied class identity is an input assumption, explicitly not authenticated by this component. It does not reserve quota or dispatch requests, and its report cannot assert native qualification.

Pre-capture review closed three gaps: in-place keyword-default mutation, code/default mutation of owned wrappers, and equality-based weak-key enrollment. The final implementation checks keyword-default keys/value identities, registers wrapper state before installation and uses API object IDs plus exact weak referent identity. Regression checks include an equal but unenrolled API object sharing an enrolled HTTP client; it is refused. These corrections were made before the first capture; no failed allocation was consumed.

## Complete closure still required

The native successor must bind `genai.Client.__init__`/`_get_api_client`, the original API/HTTP constructors, and canonical module globals and public exports. It must verify the HTTPX request/build/send/auth/redirect/transport route and the original lower pool connection-assignment, HTTPConnection and HTTP11 send path, including existing live connections and their stream/backend identities. It must reject undeclared attribute hooks and class/instance shadows, bind original request/model builders, and preserve an unchanged environment branch; proxy transports cannot be silently removed to obtain a pass. Source consistency does not establish source authentication.

The exact installed-source pins already retained include `_api_client.py`, HTTPX `_client.py`/`_transports/default.py`, HTTPcore connection pool/connection/HTTP11/synchronous backend/trace, and HTTPX auth/content helpers. The [transport guide](ap2-gemini-transport-software-v1.md) records the first pins and earlier software limits. The complete source-graph verifier and its native integration are not yet implemented by this component.

## Native observation remains refused

The [17:29:16 UTC diagnostic](../../runs/resource-diagnostics/ap2-continuation-20261030-v3.json) found 472,776,704 bytes available physical memory, about 451 MiB, and 6,961,418,240 bytes available commit. Physical headroom was below the fixed 1 GiB minimum. It was a single read-only observation, not a timed native gate. No installed-SDK construction probe, original AP2 import, real key access, model request or native allocation followed.

A later import-only SDK diagnostic may use an explicitly synthetic key with network/process access denied and no original AP2 modules; it still needs fresh timed/immediate resource gates and exact installed environment binding. Such a diagnostic could establish observed constructor compatibility, not project quota, native task execution or checkpoint credit. Genuine quota/bounds and owned execution/capture integration remain required for original model-bearing tasks.
