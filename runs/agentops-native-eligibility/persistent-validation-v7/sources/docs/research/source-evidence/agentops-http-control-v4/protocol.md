# HTTP control v4 in the persistent Linux workspace

The [v7 recovery protocol](../agentops-persistent-v7/protocol.md) governs this
new control. It derives from HTTP v3 with native-v6/setup-v7 prerequisites,
inspection schema `/6`, controller/result schema `/4`, and separate output
`runs/agentops-http-control/native-http-linux-v4`. The service, raw-byte capture,
wire/effect checker, five exchanges, six database boundaries, port 18761,
deterministic original model double and no-A2A-Version input are unchanged.
Native success and rechecked exact effect semantics remain mandatory before
either preparation or execution. All setup/native/HTTP runtime inventories must
match. Existing reservations cannot be reused; failures retain their evidence.

Commands inside the replica: `python3 -B scripts/agentops_http_control_v4.py prepare`
then `python3 -B scripts/agentops_http_control_v4.py run`. This is the previously
disclosed HTTP fixture around the original factory, not the full conversational
agent or an unchanged pytest test. No bridge, model inference, human-authenticated
identity, duplicate-confirmation idempotency, transient-effect exclusion or
scientific novelty is established by this one control.
