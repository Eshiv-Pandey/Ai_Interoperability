# AP2 V12 exact capability admission and owned-host normalization

11 November 2026. V12 is a separate prospective successor to frozen V11.
The public 13 cases, eight arms, 104 slots, 65 native policy cells, 39 legal
bridge initiation slots, 34 source-bank candidates and zero provider allowance
remain unchanged. Checkpoint weights and project scope remain unchanged.

V11 run `42911850107`, commit `f6aa8926bc36f58e571ab8a4a62a0dfb6a1acd4d`,
retained a conventional smoke actor return code of zero, no worker failure,
all nine stage labels and a rejected independent evaluation. Its strict
evaluator refused `native_unexpected_private_network_or_process_guard_interference`.
The three unexpected denials were an IPv6 capability bind, a public host
metadata child process attempt and a hostname lookup. The 104 allocated matrix
slots remain unexecuted; the rejected smoke does not establish an independently
verified original application, native transport or provider outcome.

The retained archive is 69,262,746 bytes, SHA256
`f3760855cf0af7074b2a2c75dad058ef66834f2b3c2fc4a3cef9b91fcfd08154`.
Its content-free guard record, SHA256
`3448c030dd740eeb87eed5f3466f3a9d016a9163aeafa9d67c413ab0a767ebd1`,
identifies `socket.bind` at `::1:0`, family 10/type 1, directly from
`urllib3/util/connection.py:_has_ipv6` line 127 and its module import line 137.
The process frames identify `platform`'s processor lookup through
`from_subprocess`, `check_output`, `run` and `Popen`, reached from the owned
`application` line 477 call to `platform.platform()`. The port-8001
`socket.getaddrinfo` host was redacted. Its original value and string/bytes
type cannot be recovered from that capture. V8's older omitted network caller
remains unattributed; V11's observed caller does not resolve V8 retrospectively.

The V11 pip report pins urllib3 2.8.0's public wheel, SHA256
`0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3`.
A separately downloaded and hash-verified copy contains the exact 4,444-byte
`urllib3/util/connection.py`, SHA256
`2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74`.
That identity matches the actual retained V11 runtime manifest. The wheel,
unchanged source, license and provenance receipt are retained under
`docs/research/source-evidence/ap2-v12-runtime-guard-fixtures-v1`.
This is source reconstruction, not a claim that installed source bytes were
copied into the failed smoke capture.

V12 adds one narrow capability admission: the exact hash-bound urllib3 helper
may bind one fresh, unbound, non-inheritable IPv6 stream socket to `::1:0` at
the observed import-time call site. Full structural code identities of both
the direct `_has_ipv6` frame and the importing module, exact frame lines,
socket type/protocol, pre-bind endpoint and one-attempt limit are required.
Other callers, later calls, different endpoints, changed code or source,
connections and datagram sends keep the existing denials. The accepted socket
is retained by the policy helper until its closed descriptor is checked.
There is no new connection, send, listen or descendant process allowance.

The owner caches `platform.platform()` before installing the actor guard.
The application body still makes its original call, now using CPython's public
metadata cache. The final receipt checks that the guarded call equals the
cached value. All guarded unallocated child processes remain denied.

Only the exact existing owned host literals `127.0.0.1`, `::1` and `localhost`
and their exact ASCII bytes equivalents are normalized. The existing four
owned ports stay fixed, and datagram sends remain denied. There is no general
decoding, case folding, suffix matching or new external-host admission. This
is a tested guard correctness change; the V11 redacted hostname is not proven
to have been one of those bytes values.

The independent evaluator preserves its original unexpected denial gate:
one expected private evaluator read, zero unexpected network denials and zero
unallocated process denials. Its original denial journal must still contain
exactly that one expected private probe. A separate `native-guard-policy.json`
receipt binds the pinned source to the actual runtime inventory, permits only
zero or one exact capability row, requires closure of every admitted socket,
and bounds normalized bytes operations by the existing owned-loopback count.
The original application and evaluator capture-check ASTs remain unchanged
after version retagging and removal of the one added receipt-check call.

The separate V2 safe diagnostic printer adds only bounded policy counters and
booleans. It emits no capability record contents, original host values, source
lines, argument values, locals, headers, environment or raw application output.
The separate V2 launcher retains V1's exact-once execution and return-code
preservation. Frozen V8 through V11 and their diagnostics remain unchanged.

Seven focused constructed controls passed locally; two positive POSIX socket
controls are skipped on Windows because an unbound Winsock `getsockname()`
raises observed WinError 10022. The policy rejects that unavailable witness;
it adds no Windows or network exception. The pinned hosted Linux workflow
runs both positive controls before smoke execution. The copied public urllib3
module control uses supplied generic imports and a socket wrapper, calls no
operating-system bind/connect/listen/send, and imports no original AP2 or SDK
module. Tests also check literal normalization, changed source rejection,
cached metadata without descendants, unchanged application/guard ASTs,
independent receipt mutations and bounded diagnostic output.

Independent source review found no implementation blockers. Hosted V12
outcomes, including the two positive POSIX controls, remain pending. This candidate
provides no full ADK shopper, canonical launcher, live-provider, held-out
comparison, human-gold or complete bidirectional bridge qualification.

Workflow: `.github/workflows/ap2-native-bridge-development-v12.yml`.
Planned artifact: `ap2-native-tcp-legal-bridge-initiation-development-v12`.
