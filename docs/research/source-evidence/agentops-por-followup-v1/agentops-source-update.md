# AgentOps pinned-source eligibility update

25 October 2026. This additive update preserves the unpinned findings in
[screen v1](../agentops-screen-v1/decision.md).

The [v0.11.0 release](https://github.com/MLOps-Courses/agentops-open-course/releases/tag/v0.11.0)
links to commit `c806b7f1cd0042c9817c0a4c46d80a9a95a24293`.
The commit and commit-pinned blob/raw views were inspected. Release notes
explain the historical Python/Go discrepancy and explicitly disclose a
model-backed Eval waiver; no such release evaluation result should be assumed.
[Pairs 03](03-pinned-license-and-dependencies-tool-response.json) and
[11](11-por-completeness-and-application-factory-tool-response.json)
retain the pin and release context. A web-resolved pin is not a checked-out
Git object or an authenticated local source-byte capture.

Pinned `agents/LICENSE` is MIT, attributed to Médéric Hurier.
`pyproject.toml` and `uv.lock` report application 0.11.0/Python 3.13;
the actual lock package blocks identify A2A SDK 1.1.5 and Google ADK 2.10.0.
The ADK block is finally located at formatted lines 756-792 in
[pair 08](08-test-data-lock-and-por-tool-response.json). Earlier pair 07
find excerpts only showed references/floors, so they were insufficient for
the exact lock claim. Selected Windows wheels exist, including cp313
artifacts; this does not prove complete Windows installation compatibility.
Pinned `mise.toml` uses `uv sync --locked`.

The upstream
`test_a2a_confirmation_response_resumes_the_guarded_action_with_audit_identity`
is inspected at formatted lines 341-471 in
[pair 09](09-confirmation-roundtrip-and-transactions-tool-response.json).
It injects an upstream deterministic model double and the real maintained
application factory. Its first `message/stream` pauses at input-required
with a nonterminal final flag. The follow-up preserves the emitted task and
context IDs and returns a DataPart with `adk_type=function_response`,
the confirmation function ID/name, confirmed=true and rationale payload.
Assertions require completed status on those original IDs, inventory
operational, audit attribution/session/invocation/rationale/action/target,
and two model-double calls. The test reads the most recent audit row; this
test alone does not assert exactly one total new row or no unrelated changes.
Those remain prospective independently valid task requirements.

Pinned `actions.py` requires confirmation, nonempty identity/session/
invocation/rationale and applies the write kill switch. Pinned `data.py`
performs restart and audit under one BEGIN IMMEDIATE transaction, returns
a prior audit on the same invocation/action/target key, updates the named
service and commits the audit together. Migration creates a unique key;
SQLite errors roll back through the connection boundary.
[Pairs 09](09-confirmation-roundtrip-and-transactions-tool-response.json),
[10](10-transaction-boundaries-and-por-tool-response.json) and
[11](11-por-completeness-and-application-factory-tool-response.json) retain
those source passages. This is actual local simulation state, not a
production infrastructure action. Durability/crash and concurrency behavior
have not been exercised here.

Pinned fixtures clear ambient provider/runtime environment, disable OTel and
use separate disposable data/state directories. Pinned `server.py` delegates
request conversion to ADK, uses its maintained executor, and builds persistent
session/task stores through `to_a2a`; it can replace synthetic caller identity
with gateway-verified identity. The test's synthetic A2A_USER identity must
not be reported as authenticated human identity. A nonmatching compatibility
find proves no absent feature. Actual serialized card, accepted versions,
headers/bindings and installed ADK conversion still require inspection.

Pinned root AGENTS instructions preserve immutable seed/state separation,
offline controls and real contributor gates. A focused external test is not
the root complete contributor gate: install:maintainer, format, check, test,
scan and at least 95% combined line/branch coverage are specified. No gate
ran or was bypassed here. The missing subtree AGENTS URL returned 404; a
checkout must still establish applicable nested instructions, if any.

Next acquisition/native steps remain those in
[native eligibility preparation v1](../agentops-screen-v1/native-eligibility-preparation.md),
with this pin replacing the former unresolved web revision. An accessible
local checkout path is pending. Unchanged proxy/browser acquisition retries
must stop. Acquisition would not itself resolve runtime or scientific gates.
