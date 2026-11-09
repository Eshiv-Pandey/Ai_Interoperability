# AgentOps incident-remediation continuation: source screen v1

25 October 2026. **Promising substantive local simulation; not yet a qualified
second domain.** The selected lead is the Python reference application under
[MLOps-Courses/agentops-open-course](https://github.com/MLOps-Courses/agentops-open-course),
not Azure/agentops or a generic tracing product. There is no local checkout,
resolved Git pin, installation, native request or bridge observation.

## Why this lead is more discriminating

The inspected `agents/python/src/agent/actions.py` calls a real SQLite mutation
layer after ADK confirmation. `restart_service` validates the target and requires
confirmed approval, user/session/invocation identity and a nonempty rationale.
`data.restart_service_with_audit` takes a SQLite write lock, checks the invocation/
action/target idempotency key, updates `services.status`, appends attributable
audit evidence and commits. `resolve_incident_with_audit` similarly changes the
incident record. These are actual local database effects. The application
explicitly calls them mock infrastructure actions: no real service is restarted
and no production incident is resolved. Any benchmark must preserve that scope.

The source [native confirmation test](https://github.com/MLOps-Courses/agentops-open-course/blob/main/agents/python/tests/test_server.py)
is particularly useful. It supplies an upstream deterministic BaseLlm that
requests `restart_service`, then calls the maintained `server.create_app(agent)`.
The application's actual FunctionTool, policy, ADK/A2A execution and SQLite stores
remain in that tested path. The source test submits a streaming text request,
receives INPUT_REQUIRED, extracts the `adk_request_confirmation` FunctionCall,
and sends a DataPart FunctionResponse on the same task/context. Its assertions
check COMPLETED on those original identifiers, operational service state and
an audit row with rationale, session, invocation, action and target. It also
checks that exactly two deterministic model-double callbacks occurred.

This test was **inspected, not executed here**. A model double does not by itself
invalidate a software fidelity control, but it cannot measure LLM behavior,
prove the full production composition or replace independent task validity.
The test's app construction is a disclosed injection supported by the public
factory. A later harness must retain that distinction and cannot replace the
approval/effect logic with an authored phase switch.

## Exact contract and serialization obligations

The structured resume in the inspected source includes more than a confirmed
flag. Its DataPart has `id` and `name` from the paused confirmation call,
`response.confirmed`, `response.payload.rationale`, and part metadata
`adk_type: function_response`. The initial source request uses
`message/stream`; taskId/contextId occur on the follow-up message. Dropping
function-response metadata, substituting the original tool-call ID for the
confirmation-call ID, or starting a fresh task changes the tested contract.
All source-valid typed/raw alternatives must nevertheless be audited before
any non-support claim. One DataPart expectation does not prove JSON text is
incapable of being interpreted by another permitted path.

`server.create_app` uses the actual ADK `to_a2a`, maintained executor,
DatabaseSessionService and DatabaseTaskStore. Source code constructs an
AgentCard with a JSONRPC supported interface and streaming enabled. The app
does not directly set `enable_v0_3_compat`; a nonmatching find cannot establish
the behavior of ADK's delegated route factory. The source test uses legacy method
spellings under modern SDK types. The final serialized card, protocol version,
bindings and accepted headers must be captured from the resolved runtime. Do
not transplant strict JS SDK-handler B4 missing-header rejection to this app.

The inspected offline test expects `approved_by=A2A_USER_<contextId>`. That is
synthetic unauthenticated continuity evidence, not verified human identity.
The application has a gateway-verified subject path and configured trust boundary;
those contracts were not fully audited or deployed. Do not manually grant a
principal or require authenticated attribution without an equally valid native
reference. User approval for a disposable study action is separate from this
application's simulated confirmation protocol.

## Reset, licensing, revision and dependencies

The inspected test conftest copies bundled data into a fresh temporary directory
and points both data/state settings there. It clears ambient provider/runtime
environment variables inside the test process and disables OTel. This supports
an isolated source-valid test setup; it does not prove every imported module
avoids network traffic. The runtime copies the seed into its local writable
state. No reset or deletion was performed in this workspace.

Repository and `agents/LICENSE` excerpts are MIT. The repository README/CITATION
distinguish MIT software from CC BY4.0 course prose. Current formatted main-branch
pyproject/CITATION report application0.11.0; the latter gives release date
26 September2026. That version is metadata, **not a resolved Git revision**.
Search returned an older Go-rewrite changelog and repository description while
the current inspected subtree is Python. Blob server.py reported640 lines;
the raw-main response reported596. These differing unpinned views must not be
combined into a fictitious coherent commit. A local pin and exact source
snapshot must resolve them before runtime work.

The inspected Python pyproject requires >=3.13,<3.14; declares google-adk[a2a]
>=2.10.0, a2a-sdk>=1.1.5, mcp>=2.2.0,<3, SQLite/SQLAlchemy, privacy/NLP and
telemetry dependencies; and points to a spaCy model wheel. These are declarations,
not a resolved lock or installed versions. No dependencies, models, services,
cloud account or paid resources were installed or invoked.

The once-only local `git ls-remote` metadata probe returned exit128: the configured
proxy at127.0.0.1:9 could not be reached. Exact stdout/stderr bytes, hashes,
command and timestamps are retained in `git-pin-probe-v1.json`. No proxy settings
were changed. This is a setup failure, not an application failure. GitHub history
fetch was restricted, API browsing unavailable and tag click empty. A local
checkout-path question is pending; do not repeat the blocked probe unchanged.

## Decision and bounded next work

Proceed with [native eligibility preparation](native-eligibility-preparation.md)
once exact source/runtime acquisition is available. This can answer whether a
genuine governed local effect completes on the original task through the unchanged
bridges, while charging every permitted alternative equally. It does not supply
a novel method step; its documented confirmation flow is prior behavior, not a
newly discovered protocol defect.

The adjacent A2EO page in the first retrieval is only an unselected procurement
lead. It describes a custom REST A2A alpha and explicit limits on real side effects;
no pin, official-handler parity or native application trace was established.
It is not counted as a second mapping/domain or a fallback to a weaker contract.

Seven query/result pairs plus the reused apcore discovery pair retain successes,
negative finds, mismatched views and failures as formatted tool excerpts. No
original source bytes were downloaded. No native test, listener, database effect,
bridge case, candidate performance experiment or model inference ran. Human
review remains missing. CP2 stays open, title/method route unchanged, credit5%.
