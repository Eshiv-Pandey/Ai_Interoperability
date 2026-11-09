# Version-default fidelity audit v1

**24 October 2026.** This read-only source/raw-data audit identifies a material limit on transferring the recorded raw recovery to other services. No port, bridge, SDK, capture, frozen specification or original change map was altered. No additional service execution occurred.

The [four-variant results](reference-bridge-results-v1.md) remain valid historical status/association observations for the disclosed authored port. They do not establish generic A2A 1.0 raw-recovery compatibility.

## Exact source and wire distinction

| Evidence | Actual rule or observation |
| --- | --- |
| Pinned [A2A v1.0.1 specification](source-evidence/reference-continuation/normative/v1.0.1/docs/specification.md), lines 712, 724, 737-739 | Clients supply the version; an HTTP query parameter is permitted as an alternative. The server interprets absent/empty versioning as 0.3 and rejects an unsupported requested version. |
| Installed official SDK 1.1 `dist/server/index.js`, lines 3417, 3442-3447, 3685-3692 | `ServerCallContext` defaults missing/empty requestedVersion to 0.3. `validateVersion` checks that value against the card's supported interfaces. |
| [Authored port](../../scripts/fixtures/carol-reference-v1.mjs), lines 153-155 | The wrapper explicitly supplies `A2A_PROTOCOL_VERSION` (1.0) when the header is absent before calling the SDK context builder. This differs from the normative/SDK absent-header default. An empty string still reaches the SDK's 0.3 default. |
| mgcrea pinned `src/client/peer.ts`, lines 261-279 | Raw RPC selects the JSON-RPC URL from the peer card and supplies content type. The fetch wrapper adds authentication/User-Agent, without a version header. Tool arguments do not provide arbitrary HTTP headers. |
| [Actual R4 native sidecar](../../runs/reference-bridge-observation/R4-mgcrea_mcp_a2a-reference-v1-2026-10-23T21-56-46-830Z-30760/private-native-http.jsonl) | Typed prefix `native-2/3` supplies `a2a-version:1.0`. Raw answer/read `native-4/5` supplies no version header. All four use the card's `/a2a` URL with no query parameter. |

The SDK body hash is `57ab549afa0e2cb2bef0de37f88f1ea0192c918b360322232bbd6d30263cd643`; its full file hash belongs to the checked pre-execution dependency tree. The specification hash is `627ccfe6ffb1be2c56811c3dcc18780deb419f41cdc98248095c939b2d9dc9cb`. The unchanged port hash is `b6b6492ee5c27cf5db0474054b0f18a8feafe0859d9faaa4fd67946c7768626d`. Root inspection and a separately authored AI source review agree on these rules; no independent human assessment is asserted.

The earlier change map broadly disclosed authored protocol/card/server adaptation, and the prospective bridge probe explicitly retained raw header absence and the port's 1.0 default. This addendum makes the **normative deviation and its transfer consequence** explicit. Do not rewrite the historical pre-execution map to imply this later audit was completed earlier.

## Consequence for claims and future work

R4 demonstrates that the raw interface can express references and that this exact authored service completes the original task/context. It does not show that a standards-default 1.0-only service accepts those unversioned requests. Under the inspected SDK default and a 1.0-only card, version validation rejects an unversioned request before application execution. That is a conditional conclusion from source, not an observed new bridge failure or a universal non-support certificate.

An interface URL containing the permitted version query parameter could change the outcome in another configuration. The recorded card has no such parameter, and this alternative was not exercised. Do not infer whole-interface impossibility from the header omission or deny alternatives available to a strong comparator.

A later fidelity probe would need a new prospective specification, the ordinary official version-handling path, native positive controls and preserved error outcomes, while keeping original traces immutable. It cannot manufacture a lossy adapter or add an application guard just to obtain a failure. An authored conformance control must remain labelled as such; it cannot supply natural-failure prevalence or algorithmic novelty.

The historical projection's contract contains only logical completion and original association. Its successful certificate does not certify transport/version conformance. Keep that distinction in the paper, benchmark labels and human review packet. **CP2 remains open; progress remains 5%.**
