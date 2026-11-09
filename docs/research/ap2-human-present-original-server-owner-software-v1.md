# AP2 original Uvicorn Server ownership software v1

30 October 2026. The source-reviewed [owner adapter](../../src/interoperability/ap2_hp_original_server_owner_v1.py)
passed all thirteen [constructed test methods](../../tests/test_ap2_hp_original_server_owner_v1.py)
in the [once-only owner-v1 capture](../../runs/ap2-hp-server-owner-software/owner-v1/result.json).
No original application, SDK, server, signal or model has been imported,
started or invoked in this preparation or capture. One isolated test process
executed only authored code and explicitly constructed fixtures.

## Original construction and shutdown path

The installed environment's original `uvicorn.main.run` first constructs its
original `Config(app, ...)`, calls `config.load_app()`, and then calls
`Server(config=config)`. The normal single-worker branch calls `server.run()`;
the original function retains its own result/error, startup-failure and UDS
cleanup behavior. The adapter changes only this module-local `Server` alias.
It returns the exact instance produced by the unchanged original constructor.
It does not replace Config, Server methods, the final app, or a process.

Source receipt: [installed environment manifest](../../runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json).
The inspected original module hashes are:

- `uvicorn/main.py`: `ecb83544b48126d700e803d1d558ef158346961a82d0fc5fd5fe77d8befa85df`
- `uvicorn/server.py`: `c1be9d133467a42ab88d7168e408ef5a90257661a901899426214a3d1fc2d026`
- `uvicorn/config.py`: `cf91c6ffae283a2b2020da954b4cc4ed47d3246cb062afd09fb77d98e4c5ca87`

Original `Server.main_loop` responds to `should_exit`; its shutdown closes
listeners, drains connections/tasks and completes lifespan shutdown. Original
`capture_signals` restores signal handlers and re-raises externally captured
signals. This adapter sends no signal, modifies no signal handler or captured
signal list, and never sets `force_exit`. Those original behaviors remain intact.

## Compile-only runtime class proof

The adapter requires the existing exact `SourceBinding` and installed
[final-app lease](ap2-human-present-original-binding-software-v1.md), together
with already imported `uvicorn.main`, `uvicorn.config` and `uvicorn.server`.
Complete source/environment inventories and exact module registry/name/spec/
file origins are checked. The original run function and all source-declared
methods of Config, Server and ServerState are compared with compiled source;
inspected original source is never executed.

Only three declared descriptor patterns are supported: builtin getter-only
`property`, stdlib `functools.cached_property`, and stdlib
`contextlib.contextmanager`. Getter/function code, globals, recursively typed
defaults and supported class closure are checked. The contextmanager wrapper
must match the canonical helper code/globals and its sole closure must contain
the exact verified wrapped function. A cached property must have its canonical
type, declared name, function and limited field footprint. No decorator is
invoked by verification. Other class bases, bodies, decorators or metaclasses
are refused. This trusts the current standard-library identities; it does not
authenticate the full external CPython installation.

Module-local Config/Server/ServerState/run aliases and the final-app lease are
revalidated before installation, construction and stop. Full inventory checks
and compile-only comparisons have not been timed in a native service. The
profile requires no concurrent mutation of these source-bound namespaces;
the checks do not create an atomic snapshot against unrelated threads.

## Ownership and graceful-stop API

Create and install the owner after the final-app lease has installed, before
calling the original service entry point. The factory accepts only the exact
original run code/globals and its `Server(config=config)` keyword call. There
must be one active final-app capture, and both the original run's `app` local
and Config.app must be that exact capture. Config type, role host/port,
keep-alive, one worker, no reload/UDS/FD/factory, and absence of instance method
overrides are checked. An exact original constructor result, Config and final
app are retained by identity immediately after construction, before fresh-state
validation. A malformed returned original instance stays retained as contrary
evidence; construction failure prevents run/stop eligibility. Original
constructor exceptions are retained and re-raised unchanged. There is no second
constructor attempt.

`request_graceful_stop()` succeeds only for that retained instance during the
active original run, after its `started` flag is true and while its original
force-exit state remains false. It validates Server/Config/capture identity,
source/module aliases and method interference, then sets only
`server.should_exit = True`. Unstarted, inactive, altered or unowned state
returns false and keeps authority. Repeated requests do not introduce a force
exit. The original cached request-limit value may legitimately appear in the
instance dictionary; it is distinguished from a substituted method.

`restore()` waits until constructor and original delegated run are inactive.
It restores only its own exact factory alias. An interfering alias stays
untouched and restoration authority remains available. The original Server
reference is retained even after alias restoration. Inactive delegation alone
is not verified graceful drain, process exit, empty Windows Job or closed TCP
listeners. The native parent must keep its exact Job/PID/TCP handles and apply
the existing owned shutdown/cleanup contract; this adapter never searches for
or terminates another process.

## Constructed validation scope

The thirteen constructed tests execute authored fixture strings only. Real compile-only
descriptor verification is checked separately from ownership fixtures whose
original runtime/source checks are explicitly mocked. Fixtures cover original
instance/Config/return and exception identity, constructor failure, exact
caller globals, typed configuration, preinstall alias drift, active/unstarted
refusal, method/app/factory interference, cached-property state and once-only
restoration. Their sentinel-returning caller is synthetic; original
`uvicorn.main.run` discards Server.run's return and keeps its original None/
exception semantics.

The added malformed-fresh-state regression retains the exact returned original
Server before failure, retains the BindingError, and verifies no Server.run or
stop eligibility follows. Even an apparently active final run cannot promote
the contrary instance. No replacement Server or force exit is introduced.

The [dedicated capture driver](../../scripts/capture_ap2_hp_server_owner_tests_v1.py)
pins the owner, four unchanged authored dependencies and the test file. It
copies those six files and its own exact source into a fresh seven-file checkout,
runs only the thirteen new methods in isolated/site-disabled/bytecode-disabled
Python, and retains binary streams, per-test outcomes, synthetic fixture files
and owner reports. Its test parent denies socket, subprocess and native-library
operations. It checks exact method/artifact membership and unchanged original
and copied inputs. Existing output allocations are refused; preparation or
retention failures keep the new output and a failure receipt when possible.
The driver and embedded test program were AST parsed before root review. Root
closed source/driver review before the single approved owner-v1 capture.
That allocation passed all thirteen methods with zero failures, errors, skips,
expected failures or unexpected successes. Exact declared method and synthetic
artifact membership, isolated/site-disabled/bytecode-disabled execution flags,
and all seven original/copied source inputs were verified unchanged. The
[per-test outcomes](../../runs/ap2-hp-server-owner-software/owner-v1/test-outcomes.json),
[binary test output](../../runs/ap2-hp-server-owner-software/owner-v1/tests.stderr.bin)
and thirteen fixture/report directories remain retained. No SDK module was
loaded and no older test suite executed. Owner-v1 is consumed and will not be
rerun or overwritten.

These are constructed software results. Original runtime compatibility,
provider transport, native Job/TCP ownership, graceful shutdown, process-exit
qualification and benchmark task grades remain unverified. The result earns
no research-checkpoint credit.
