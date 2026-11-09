# AP2 original caller and final ASGI binding software v1

30 October 2026. These adapters prepare original AP2 bindings for the
implemented reference benchmark. The single retained constructed capture
passed **22 tests** at 17:22:06 UTC. No original module, SDK, credential,
service or model was imported or invoked. The consumed adapter, test and
driver sources must now be preserved. Earlier Python 3.13.1 AST parsing was
syntax evidence; the retained outcomes below provide constructed test evidence.

## Source consistency and caller bindings

[Caller adapter](../../src/interoperability/ap2_hp_original_binding_v1.py)
accepts already imported module objects. `validate_inputs` checks the complete
136-file AP2 source union and the installed environment against the frozen
manifests. Their required SHA256 values are
`78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463`
and `4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5`.
Regular absolute paths, reparse/link refusal, canonical relative paths,
bounded file size/count and strict JSON are checked. The original source stage
manifest is `runs/ap2-environment-preparation/source-stage-v1/manifest.json`.

For supplied original modules, the adapter checks name, `sys.modules` identity,
file/spec origin, function globals, compile-only marshalled code, supported
defaults with recursive type preservation, and class closure/base/member
footprint. It never executes inspected
source. Callable or class decorators, metaclass keywords and unreviewed
base/default expressions are refused. This is a deliberately narrow verifier,
not a general verifier for every SDK class.

`make_caller_binding` retains original functions, the original message builder
and the original receipt helper in `ReferenceBindings`. It checks original
mandate/receipt constants, the owned temporary signing root, required internal
builder/artifact aliases, the fresh original client footprint, endpoint,
extension set and uncached card. Client type is checked before instance
attribute reads. The observers replace exactly these seven aliases:

| Original module | Client aliases |
| --- | --- |
| shopping `remote_agents` | merchant, credentials |
| shopping `tools` | merchant, credentials |
| shopper `tools` | merchant |
| payment-method collector `tools` | credentials |
| shipping-address collector `tools` | credentials |

Installation revalidates source and all construction-time caller checks through
an uninstalled probe, then compares module, original client and reference
callable identity before changing any alias. The intended profile has no
concurrent mutation of these namespaces; checks do not provide an atomic
snapshot against another thread.

The owned observers preserve returned object and exception identity. Their
active-call counts remain positive throughout delegation, including error
handling. `restore()` refuses during active calls and changes only aliases
that still contain its exact proxy. Interference stays untouched and retains
restoration authority. An installation error is retained on the returned
lease; callers must require `installed`, no `error`, and no premature
restoration before reference execution. Clients, HTTPX resources, credentials
and service processes remain the native owner's responsibility.

## Final original ASGI placement

[Final-app adapter](../../src/interoperability/ap2_hp_final_asgi_binding_v1.py)
replaces only the original `common.server` module's `uvicorn` alias. The proxy
wraps the final `app` passed to `uvicorn.run` by the exact original
`run_agent_blocking` code/globals, after original app construction and logging
and CORS middleware. It checks original typed host/role-port/log/keep-alive
kwargs and delegates to the captured original `uvicorn.main.run` once.
Other Uvicorn attributes are forwarded.

The proxy preserves original run results and raised exceptions. If wrapper
construction fails, it delegates the original app and records an observation
error. HTTP scope/event objects and lifespan calls are preserved by the
unchanged passive wrapper. Restoration waits for the original run to finish
and only restores its own module-local alias. Install rechecks source,
environment and original run identity before mutation.

Neither adapter authenticates the original import, proves all transitive SDK
constructor/global identities, installs a provider request hook, owns a TCP
peer, creates durable capture, or grants native qualification. In particular,
original server builder/handler aliases and `uvicorn.main.run`'s `Config` and
`Server` globals require the native owner's separate review. The final-app
lease has no Server shutdown authority. No alternate server is constructed.

## Review and retained constructed capture

[Constructed tests](../../tests/test_ap2_hp_original_bindings_v1.py) explicitly
execute only authored fixture strings in synthetic namespaces. Origin/code,
defaults (including nested tuple/set values and dictionary key types), globals,
class closure/member checks use the real adapter verifier.
Alias/final-call fixtures separately mock original source validation and do
not establish compatibility with the original SDK. They cover seven-slot
placement, preinstall constant/callable/card drift, active-call refusal,
interference, original return/error identity, final-app middleware placement,
caller code/globals and typed kwargs, once-only delegation, observer failure,
and lossless HTTP/lifespan forwarding.

All functional coroutine fixtures complete through one explicit
`coroutine.send(None)`; their results and exceptions are preserved and the
coroutine is always closed. Any suspension is refused. No event loop is
created. The existing forwarding test also checks refusal and closure for a
deliberately suspended constructed fixture.

The final independent source review closed on the recursive literal-default
fix, class footprint, typed client values, module identity and immediate
coroutine fixtures. Root then authorized one capture after the dedicated
driver's local read-only review. No earlier suite was rerun.

The [consumed driver](../../scripts/capture_ap2_hp_original_bindings_tests_v1.py)
pins exactly five source/test files plus its separate externally pinned
driver copy. It refused an existing output namespace before allocation and
used Python 3.13.1 with `-I -S -B`, a 120-second bound, and a minimal child
environment. The parent admitted exactly its bound Python child once; the
child denied socket/process operations, original/SDK/provider imports and
file content outside the capture and read-only standard library. Both audit
receipts contain zero rejected attempts. These are Python audit receipts for
reviewed constructed code, not runtime authentication.

The [retained result](../../runs/ap2-hp-reference-software/original-bindings-v1/result.json)
has SHA256 `122a3246c11b0a5d3a3180f8e81f903e6084d72233bb419f2c5855150497f963`.
It records return code 0, all 22 declared test IDs passed, zero failures,
errors, skips, expected failures or unexpected successes, no timeout, and
no cleanup/execution error. Five source inputs, the driver copy and the
interpreter remained unchanged. The child created no event loop or process.

The [capture plan](../../runs/ap2-hp-reference-software/original-bindings-v1/capture-plan.json),
[per-ID outcomes](../../runs/ap2-hp-reference-software/original-bindings-v1/test-outcomes.json),
[binary stdout](../../runs/ap2-hp-reference-software/original-bindings-v1/tests.stdout.bin)
and [binary stderr](../../runs/ap2-hp-reference-software/original-bindings-v1/tests.stderr.bin)
are retained with all six source/driver copies. Stdout is an intentionally
retained empty stream; stderr contains the complete test runner output.

The consumed hashes are:

| File | SHA256 |
| --- | --- |
| caller binding | `27c37938751dfb00f21a3a53043ea2f468814d264df71bb8024dd58cea5ac3af` |
| final ASGI binding | `51623f3333c0479a708d05b10b1bac46117cee2c2cde8a8b75d033659445c1d3` |
| reference execution dependency | `821b463c1e8d8500b32774b7c04ace2b865c7089c7a8e0ca1f5e7f20ab5df340` |
| passive capture dependency | `e3abb063246ee0688b098bba933a74c3c2e6c5789b7c9b39bc59cc12b135a5a8` |
| constructed tests | `d5c5a9da681740183a87385dd4ddda962109e876440f55fb661f73a0e790bc7b` |
| dedicated driver | `d6e4617b569018d3db93d32b7b15a97f0d5c55660d1e08fa003865a14d8d3e91` |

No original SDK/runtime compatibility, provider entitlement, TCP ownership,
native qualification or full-research gate credit is established. Native
imports, provider access and grade attempts remain zero.
