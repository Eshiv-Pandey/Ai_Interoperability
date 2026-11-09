# Official SDK HTTP version control v1

Prepared **24 October 2026 before SDK/handler execution**. This is a labelled
**SOFTWARE/SDK HTTP CONTROL USING THE DISCLOSED CAROL EXECUTOR**, following the
checked function defaults. It supplies neither a natural-failure prevalence
estimate nor a new algorithm, bridge mapping or passed novelty gate.

Use unchanged `@a2a-js/sdk` 1.1.0 and its actual exported Express `jsonRpcHandler`.
Use the default context builder; supply no `contextBuilder` or legacy compatibility
override. Mount the router at `/a2a` on one ephemeral 127.0.0.1 server. Use the
unchanged `CarolReferenceExecutor` exported by the earlier disclosed port, with
the official DefaultRequestHandler and InMemoryTaskStore and a clearly authored
JSONRPC 1.0-only card. The earlier port's custom HTTP server is never started.
All earlier source files, cards, captures, dependency environments and results
remain unchanged. An ordinary header-positive trajectory must work through this
actual official handler before interpreting its negative cases.

The isolated dependency environment is `external/sdk-http-control-v1`. Express
5.2.1 and its pinned dependency graph were unpacked from original cached npm
tarballs, with publisher integrity verification, no package scripts and no network.
Conflicting dependency versions remain nested. The SDK and jose 6.2.12 were copied
byte-for-byte from the earlier installation. `environment-lock.json` records the
actual installed tree and original package integrity; it is a local provenance
lock, not an npm-generated package-lock. Earlier failed npm setup logs and the
cache-copy ledger remain under `runs/sdk-http-control`. Setup attempts are not
service trials and are not counted as successful experiments.

## Once-only ordered controls

Every request uses genuine loopback HTTP and canonical A2A 1.0 JSONRPC bodies.
Use a fresh message ID for each SendMessage. Initial text is the original valid
shuffle payload with one guess/response. The answer is `Well done`; its original
task/context and referenceTaskIds come only from H3's public response.

| Case | Request | A2A-Version header | Query parameter | Source-based expectation |
| --- | --- | --- | --- | --- |
| H1 | Initial SendMessage | Absent | Absent | VersionNotSupportedError; executor not reached |
| H2 | Initial SendMessage | Empty | Absent | Same rejection |
| H3 | Initial SendMessage | 1.0 | Absent | Pending task with original source-valid artifact |
| H4 | Initial SendMessage | 0.3 | Absent | VersionNotSupportedError |
| H5 | Initial SendMessage | Absent | A2A-Version=1.0 | Handler source reads only header; record actual outcome |
| H6 | Initial SendMessage | 1.0 | A2A-Version=1.0 | Pending positive control |
| H7 | Same-task answer SendMessage | 1.0 | Absent | Original H3 task/context completed |
| H8 | GetTask for H3 task | 1.0 | Absent | Authoritative completed original task/context |
| H9 | GetTask for H3 task | Absent | Absent | VersionNotSupportedError |
| H10 | GetTask for H3 task | Absent | A2A-Version=1.0 | Record actual query-only outcome |

The specification explicitly permits the query alternative (v1.0.1 section
3.6.1). The installed Express JSONRPC implementation reads the header at line
3359 and validates before dispatch at 3369. Any query-only discrepancy is a
bounded observation of this pinned SDK/handler configuration. Do not infer that
every A2A implementation ignores the query alternative or that all raw bridge
interfaces are unusable. The original R4 success remains service-specific.

## Preservation, verification and stopping

Create an exclusive attempt directory before importing the SDK, executor or
Express handler. Preserve this specification, driver, separate checker, unchanged
executor source, installed dependency lock, relevant normative source, complete
installed environment and original SDK/jose bytes. Freeze their hashes and copies,
the case plan, Node executable hash/version and source-ledger before imports.
Record client request/response entity bytes, base64, digests, URLs, explicit headers,
actual server-ingress headers/body, JSONRPC IDs/errors and post-case task-context
diagnostics. Charge all ten actual requests; no hidden retries or polling.

Continue after a recorded negative/contradictory outcome when the subsequent
fixed cases remain constructible. If H3 fails to yield a public original task and
context, H7-H10 are recorded as not executed due to failed positive eligibility;
do not manufacture identifiers or rerun H3. Preserve setup failures, unexpected
exceptions and every actual response. Finish by closing all server connections,
awaiting server close, recording listening=false and verifying source/tree hashes.
All output files use exclusive creation. The driver starts no child or model.

The integrating assistant separately checks raw requests/responses, public bindings,
same-task completion, rejection boundaries, ingress agreement and archived bytes.
This is separate checker logic, not independent human authorship. A mismatch
remains an adverse outcome rather than a reason for favorable replacement.
**CP2 remains open; progress remains 5%.**
