# apcore-a2a framework continuation lead: screen v1

25 October 2026. **Not qualified as the second substantive application domain.**
The inspected source is a real modern A2A framework, but no independently
grounded application/native approval continuation was selected or executed.
This is an incomplete source screen, not a proof of full-interface non-support.

## Correct implementation provenance

[aiperceivable/apcore-a2a](https://github.com/aiperceivable/apcore-a2a) is the
shared specification/conformance repository. Its README points to separate
Python, TypeScript and Rust SDKs. The selected Python lead is
[apcore-a2a-python](https://github.com/aiperceivable/apcore-a2a-python).
Release `python/v0.8.4` resolves through its release commit link to
`c8b5ae5c15ae7e848cdfb45c2f063293d172061d`; the inspected pinned LICENSE is
Apache-2.0. This is a web-resolved pin with formatted source excerpts, not a
complete local Git checkout or byte-exact downloaded source archive.

The pinned pyproject declares Python>=3.11, apcore>=0.32.2,
apcore-toolkit>=0.14.0 and a2a-sdk[http-server]>=1.0.0, alongside Starlette,
uvicorn, httpx and PyJWT ranges. These are dependency declarations, not a
resolved installed lock or demonstrated reproducible runtime. No installation
or direct remote-download attempt occurred.

## Application/contract boundaries actually inspected

- The shared PRD's multi-turn and approval requirements are design intent. Its
  Server Core page expressly says the original ExecutionRouter/TaskManager/
  TransportManager design was superseded. Do not execute those snippets as if
  they were current implementation or infer resume semantics from a state
  diagram alone.
- Pinned `server/executor.py` uses the official SDK's AgentExecutor and the
  supplied `context.task_id`. It publishes an initial SUBMITTED Task, requires
  `message.metadata.skillId`, checks the registry, converts input and invokes
  the apcore executor. An APPROVAL_PENDING exception emits INPUT_REQUIRED with
  `str(exc)` as a text status message. Supplying a same-task RequestContext to
  that method is not a native wire demonstration that an actual approval can
  be consumed and the original task completed.
- The inspected method constructs a new apcore Context from the authentication
  identity, CancelToken and deadline. No dedicated approval-confirmation branch
  is evident in this method. Approval handling may depend on apcore's external
  state and modules; those contracts were not audited. Do not infer that approval
  resume is impossible or invent a required confirmation field.
- Pinned `adapters/parts.py` accepts exactly one part. For an object input schema,
  TextPart is parsed as JSON; DataPart is also accepted. Therefore typed text
  alone is not a general structured-input obstruction. File/multiple-part
  restrictions are explicit source limitations, not newly discovered defects.
- The inspected executor test uses a mock registry/module and AsyncMock to
  raise an APPROVAL_PENDING-coded exception. It checks INPUT_REQUIRED but does
  not establish a real governed application effect, human confirmation or
  original-task completion. That test was not run here. Neither image.resize's
  mock output nor an authored replacement approval handler would constitute a
  newly observed independent application domain.
- The pinned factory uses official DefaultRequestHandler, owner-scoped server
  call context, REST routes and JSONRPC routes. It expressly sets
  `enable_v0_3_compat=True`. A legacy discovery-path alias is not the sole
  compatibility mechanism. The strict JS SDK-handler B4 header rejection must
  not be transplanted to this Python app. Actual serialized card, accepted
  version/binding profile and wire behavior remain unobserved.
- Missing required `skillId` is a source guard relevant to initial invocation
  as well as a follow-up. It is not alone a continuation-specific or C1
  finding. Fair screening must preserve the full typed/raw interfaces and their
  actual permitted fields, without granting hidden internal metadata to the
  caller or excluding an existing public route.

This service wrapper is not counted as another measured MCP/A2A bridge or
crossing direction. Its vendor mapping/ancestry and application independence
have not been established as benchmark evidence.

## Decision and remaining discriminating work

A useful next application witness would need a licensed pinned real module,
actual governed local state/effect, independently valid runtime/reference
contract, source-valid same-original-task native pause/confirmation/completion,
an isolated reset and the actual unchanged bridge profile. It must preserve
the allowed principals, input alternatives and SDK compatibility behavior. A
mock phase switch or manually granted token cannot be credited as original
native continuation. Existing task/evaluator evidence remains unchanged.

Six query/result pairs retain shared docs, the implementation-release link,
tag and later commit-pinned source excerpts. The tag tree URL failed restricted
fetch; it is retained without an absence conclusion. A first local excerpt
print failed with a cp1252 output-encoding error; it read the retained JSON,
made no source mutation and succeeded with Python UTF-8 mode. A failed find for
`supported_interfaces` in factory.py does not establish an empty actual card.
The shared PRD snapshot is also retained in the diagnostic screen's second
query/result pair and explicitly reused, not counted as a seventh new request.

No source checkout, dependencies, native/bridge application requests, model
inference, business transaction, candidate/performance experiment, human review
or external message occurred. The full method objective, original contract
requirements and 5% checkpoint credit remain unchanged.
