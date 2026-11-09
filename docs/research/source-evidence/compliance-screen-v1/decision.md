# Contract-compliance application screen v1

Reviewed 24 October 2026. **Not selected as a qualified continuation domain or
C1 contribution.** No application, test, package installation, bridge capture
or model call was executed during this source screen.

The discovery site is a mirror: its architecture still says message/send,
while its upstream link identifies GoogleCloudPlatform/generative-ai and
the primary architecture now says SendMessage. Use the primary repository,
not AgriciDaniel/google-genai-brain, as the application identity.
The mirrored document cannot establish the current wire profile.
[Primary architecture](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/adk/contract-compliance-pipeline/ARCHITECTURE.md).

The primary [README](https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/agents/adk/contract-compliance-pipeline/README.md)
describes substantive extracted contract fields, adjustable policies and
pass/violation outcomes. Its fixtures named .pdf contain plain text; the healthy
cockpit is deterministic and completes in one call. Simulated outage paths are
explicit controls, not natural failures or guarded approval continuations.

[Go module](https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/agents/adk/contract-compliance-pipeline/go-compliance-agent/go.mod)
declares Go1.21 with no external dependencies.
[Server](https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/agents/adk/contract-compliance-pipeline/go-compliance-agent/cmd/server/main.go)
uses the standard HTTP library with configurable HOST/port/policy.
A local Go executable exists, but full source bytes, exact pin, compilation and
unchanged runtime feasibility remain unverified.
The upstream [license](https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/LICENSE)
is Apache-2.0 at the inspected unpinned main.

## Actual interface and source-only discrepancy lead

The inspected [card](https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/agents/adk/contract-compliance-pipeline/go-compliance-agent/internal/agentcard/card.go)
advertises a 1.0 JSONRPC interface. The
[handler](https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/agents/adk/contract-compliance-pipeline/go-compliance-agent/internal/handler/task_handler.go)
dispatches SendMessage/GetTask and selected legacy aliases. Accepted validation
runs synchronously and stores a completed task for retrieval; it does not first
create a pending task demanding approval, correlated additional input or a
reservation commitment.

That handler's Part struct has modern fields, yet extractContractPayload
accepts data only when kind/type is data, or JSON text only when kind is text.
Field-presence-only modern inputs therefore appear to miss this branch.
This is a **source-only unpinned discrepancy**, not an observed interoperability
failure. The README's modern-shaped payload does not itself prove runtime
success. Its permissive legacy tags could offer a raw positive control if the
exact unchanged source and native controls were later established; no such case
was run, no bridge behavior was inferred, and no missing field was injected.

GetTask retrieves already completed state. Adding a pause, approval gate,
expiry, authority binding, binary-PDF parser or reservation stage would create
authored application behavior. It cannot turn this screen into a natural
continuation witness or C1 novelty. The real policy checker can be a later
payload-fidelity control under a separately justified question, not gate credit.

## Reproducibility and limits

All retained files are structured/tool-formatted retrieval responses or command
outputs, not byte-exact original source archives. Main remains mutable and the
retrievals have differing crawl dates; do not claim one internally consistent
commit snapshot. API/history/feed metadata routes failed through the web tool.
One ordinary git ls-remote attempt failed at the configured 127.0.0.1:9 proxy;
that configuration was not bypassed. The exact commit is **unresolved**.

The bounded searches found no primary report of this precise application
discrepancy. Search absence proves neither novelty nor nonexistence of reports.
Secondary version discussions are retained as discovery context and establish
no new primary mgcrea-specific finding.

The source screen changes the next action: exclude this lead from the required
second continuation domain and retain its unresolved fidelity issue separately.
The already verified official HTTP environment supports the independently
specified [bridge fidelity control](../../official-handler-bridge-probe-v1.md).
That control also supplies no C1 novelty or second domain. Original method
objective retained; CP2 remains open and verified progress remains 5%.

