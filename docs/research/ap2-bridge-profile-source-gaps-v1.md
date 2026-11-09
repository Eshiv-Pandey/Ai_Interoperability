# AP2 human-present bridge-profile prerequisites

30 October 2026. Bounded source inspection only. The human-present native
merchant path is a positive source lead; the existing two bridge profiles must
not be assumed to preserve it. No bridge/application request, SDK import,
model call or certificate was executed for this note. This is not a complete
whole-interface non-support argument or an observed bridge failure.

The original Python JSON-RPC handler constructs `requested_extensions` from
the HTTP extension header (`jsonrpc_app.py:157-158`). The original
`BaseServerExecutor` activates the intersection with supported URIs and rejects
execution unless `https://github.com/google-agentic-commerce/ap2/v1` is active
(`base_server_executor.py:90-95,172-184`). Original
`PaymentRemoteA2aClient._get_a2a_client` sets that header before sending
(`payment_remote_a2a_client.py:103-109`). Message metadata is not an inspected
replacement for this HTTP-level request.

Original shopper payment requests also contain actual DataParts: mandate,
risk and shopping-agent identity, plus a continuation task/context and OTP.
The processor's public challenge and receipt are DataParts. Putting JSON text
inside a text part does not make it a DataPart for the original executor's
`get_data_parts` parser.

| Inspected bridge path | Concrete source behavior | Evidence needed before qualification |
| --- | --- | --- |
| AmirK-S typed send | `buildUserMessage` creates one text Part, `ROLE_USER`, `metadata=undefined` and `extensions=[]`. The exposed send input is text/task/context; no mandate DataPart or HTTP extension-header input was found in that operation. | Verify the full configured public surface and installed SDK transport/card handling. Do not add a DataPart/header parameter or force an injected transport and call it unchanged bridge behavior. |
| mgcrea typed send | The supplied public typed message likewise carries text and empty extensions. Its transport fetch adds configured bearer/User-Agent, retaining SDK-produced headers. | Inspect exact installed SDK extension activation/negotiation and allowed original configuration, then matched native/bridge wire evidence. Caller text or metadata does not prove an AP2 header/mandate crossed. |
| mgcrea raw request | `rawRpc` uses a card's JSONRPC interface, serializes arbitrary legal params and sends content-type through its original fetch. The MCP method enum permits modern `SendMessage`, not legacy `message/send`; no caller HTTP-header field exists in this inspected operation. | Keep modern method/header/card restrictions in the profile. Inspect SDK card normalization and the original Python dispatch before a matched trial; raw params alone do not establish a legal legacy method or extension header. |

AP2's inspected merchant card declares protocolVersion `0.3.0`; application
version `1.0.0` is a different field. Retain exact discovery, method, header,
entity and task/context observations. An invented supportedInterfaces card,
endpoint proxy that adds headers, legacy method outside the raw enum or
rewritten source would be a disclosed different route, not a repair to the
original comparison. SDK behavior and other allowed original interfaces have
not been exhaustively closed by this seven-file inspection.

The next comparison first needs the unchanged native HP task to qualify, then
source-bound legal bridge profiles and a prospectively frozen control. A
rejection must be retained at its exact discovery/dispatch/effect boundary;
selected-path failure cannot become blanket non-support. None of these source
gaps establishes the candidate algorithm's novelty or comparative advantage.

## Inspected byte identities

Original bridge pins remain AmirK-S `58eff9da469bccdc432bf164662727947de646b4`
and mgcrea `c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5` in the retained source
lock. AP2 is `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`, with pinned Python
A2A SDK `0.3.24`. Hashes identify read local source, not loaded native code.

| File | SHA256 |
| --- | --- |
| `external/a2a-to-mcp/src/a2a-client.ts` | `38cca90108c057823c823fac881bba074bc6df99e2ac07746ad2426550815b06` |
| `external/mcp-a2a/src/client/peer.ts` | `62c36155dd3f2438f4a629fff8cc5b1961d2f7c20bfbc5a620706a2f8218b909` |
| `external/mcp-a2a/src/client/fetch.ts` | `9427084ca3907354da603ea2e45e56cba65ec9257e8515b37e3e6c58d61e833d` |
| `external/mcp-a2a/src/tools/request.ts` | `1c9eb49a065f3eac95c0fd2172068443719a29aeca9453a31690c70a61731342` |
| AP2 `common/base_server_executor.py` | `a1e1f85ba4481aa1712d01bef83778c9ab970ed2e3856fdafc4fb821d48f27a9` |
| AP2 `common/payment_remote_a2a_client.py` | `88bd46d93eb7408912c254b4dc6a392a821d07eabc049c5a04a42b8627042efb` |
| Pinned A2A `server/apps/jsonrpc/jsonrpc_app.py` | `0e2316226fc7dda48dcb6d74b069a7577a388d5adb6b0a1041303248623287d9` |

Use this note with the [native design](ap2-human-present-native-runner-design-v1.md)
and [response-contract acquisition](cp2-response-contract-acquisition-v1.md).
The original sources, frozen solvers and completed captures remain unchanged.
