# AP2 V10 owned worker stage-journal repair

11 November 2026. V10 is a separate prospective successor to frozen V9.
Its only production behavior change is to define the missing owned `append`
and `now` helpers used by the V9 stage journal. The exact 13 cases, eight
arms, five native policies and 104-slot allocation remain unchanged. The
denominators remain 65 native policy cells and 39 repeated legal bridge
prefix/initiation slots. Project scope, source-bank IDs and checkpoint weights
are unchanged.

V9 hosted run `42902256098`, commit `19315bc9`, retained return code 3 in the
conventional smoke. Its actual failure is `NameError: name 'append' is not
defined` at worker line 707, before certificate admission. The completed
67,950,293-byte archive has SHA256
`bcb402ab7acc95b67810504405a9ba6f50dd2afa723360dc0fcec2d5c1bf444b`.
No stage journal, public certificate admission, actor guard/separation receipt
or native observation was produced. The actor recorded zero provider requests;
all 104 prospective matrix slots remained unexecuted and missing. This is an
owned harness failure, not an observed policy or interoperability outcome.

The missing `now` helper is a second source-confirmed defect. The retained
first failure does not establish that execution reached its argument evaluation.
The independent failure audit is
`docs/research/ap2-v9-actual-stage-failure-peer-audit-v1.json`.
Frozen V8 and V9 source, controls, allocations and failures remain untouched.

V10 writes bounded JSONL stage entries with real UTC timestamps, flushes each
entry and calls `fsync`. Non-finite or oversized JSON entries are refused before
writing. These are owned diagnostic helpers; original AP2 application, shopper
tool and SDK bodies are unchanged. All V9 read-only public certificate admission,
independent certificate/source/runtime binding, safe denial/frame diagnostics,
sender attribution and strict cleanup rules are inherited without weakening.

Four focused constructed prelude controls execute the exact production stage
and certificate-admission statements with the actor module's real globals.
They reproduce the frozen V9 first missing-`append` dependency, complete V10
public certificate admission, execute all nine actual journal call sites and
check durable append preservation and invalid/oversized entry refusal. Neither
`append`, `now`, `write` nor the certificate helper is stubbed. These controls
stop before audit-hook installation or the SDK event loop and execute no original
application, bridge or provider. The inherited 20 constructed controls retain
their separate source/guard/transport scope.

The prospective hosted workflow separately pins Python 3.13.1, A2A SDK 0.3.24
and Node v22.23.2, freezes all 104 slots before four independent smoke cells,
and preserves failed or interrupted execution without replay. GitHub runtime
outcomes are pending. The strict unexpected-network-denial gate remains zero;
V8's omitted network caller is still unattributed. If a future V10 capture
encounters it, safe endpoint and frame diagnostics must establish the actual
caller/address before any separately declared exception is considered.

This version establishes no full ADK shopper, canonical native launcher,
live-provider, held-out comparative, independent human-gold or whole-route
qualification. Bridge slots remain bounded legal outgoing observations with
no invented Task inverse. The complete inherited scope is documented in
`docs/research/ap2-native-bridge-development-v9.md`.

Workflow: `.github/workflows/ap2-native-bridge-development-v10.yml`.
Planned artifact: `ap2-native-tcp-legal-bridge-initiation-development-v10`.
