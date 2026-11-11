# Prospective shopper V5: loopback guard diagnostics

V5 is post-V1 development. At this protocol's initial software checkpoint it
had not been independently source-reviewed, frozen, dispatched or committed.
Later review and execution records must name their exact source and allocation.
The completed V1 release and all historical
V4 sources and allocations remain unchanged. V4 run `43074319113` retains its
two owned card-network denials and later upstream HTTP 503. Its rejected socket
arguments were not recorded; no exact representation cause is established.

The new [runner](../../scripts/run_ap2_native_shopper_provider_v5.py) selects
[worker V3](../../scripts/ap2_native_shopper_provider_worker_v3.py), whose public
case is `ap2-native-shopper-provider-v5-correct-human`. Plan/result schemas are
`ap2-native-shopper-provider-plan/5` and `ap2-native-shopper-provider-result/5`;
the worker schema is `ap2-native-shopper-provider-worker/3`. All other public
facts, the conservative visible-text actor, original ADK application function,
original tools/models, native entrypoints and V2 provider boundary are preserved.
V5 does not replace the original SDK or alter its timeouts or generation payloads.

The additive [guard](../../scripts/ap2_native_shopper_actor_guard_v5.py) exposes
the pure `classify_network_event(event, values, allowed_ports)` and
`safe_network_diagnostic(event, values, decision)` APIs. Only exact declared
`127.0.0.1`, `localhost` and `::1` hosts and ports 8001/8002/8003 plus the allocated
proxy port are admitted. ASCII bytes hosts and numeric string/bytes service
forms normalize to those same endpoints. IPv6 loopback scope and flow must be
zero. Other hosts, service names, undeclared ports, boolean/float values and
malformed audit argument shapes remain denied. CPython `socket.sendto` arguments
are interpreted as `(socket, address)`; send payloads are never diagnostic inputs.

Each network denial writes a sanitized `actor-network-denials.jsonl` record
under schema `ap2-native-shopper-network-denial/5`. Safe loopback/port values
retain their original scalar types; other names/arguments are redacted. Socket
objects and packet data are omitted. The stream permits at most 160 records,
262,144 total bytes and 4,096 bytes per record. Logging exhaustion still denies
the request and increments the dropped count. The final `actor-input-separation.json`
uses schema `ap2-native-shopper-actor-separation/5`, naming that stream and its
bounds, with logged/dropped/write-failure counters. These are Python audit
controls, not an OS hostile-code sandbox.

Provider and lifecycle bounds remain 80 upstream allocations including smoke,
200,000 request bytes, six-second pacing, a 100,000 known-token stop, the owned
120-second sender option, at most 150 seconds of evidence drain, 12 user turns,
160 ADK events, 262,144 bytes per ADK event, a 600-second worker and a 900-second
screen. Unknown or unclosed provider usage stays unmeasured. The additive guard
and selected worker are source-bound by preparation and plan checks.

The [focused software controls](../../tests/test_ap2_native_shopper_provider_v5.py)
passed 11/11 with no skips on 12 November 2026. Their
[retained result](../../runs/ap2-native-shopper-provider-development/v5/software-controls-v1/result.json)
and [real transport witness](../../runs/ap2-native-shopper-provider-development/v5/software-controls-v1/real-loopback-transport.json)
show actual constructed IPv4, bytes hostname with string/bytes service, UDP
`sendto` and IPv6 loopback traffic. Three attempted prohibited network operations
were denied before external contact; one private-file read was denied. All local
listeners closed, all three sanitized denial records were retained, and no
diagnostic was dropped or failed. Six historical V4 file identities match before
and after. No original application, SDK, provider or model ran.

```powershell
python -I -S -B -m unittest discover -s tests -p test_ap2_native_shopper_provider_v5.py -v
```

The initial checkpoint left independent source review, final-session/actor-separation
diagnostic reconciliation, a prospective workflow and any once-only live allocation
as next-phase work. Subsequent records preserve this checkpoint and identify the
actual completed checks and allocated execution separately.
This checkpoint grants no live task success, human gold, novelty, scientific-gate
credit or additional whole-project completion claim.
