# Original native AP2 and accounted Gemini development screen V2

Prospective protocol, 11 November 2026. This is a separately named V2 five-case development
allocation. Historical offline, ASGI, owned-server and failed bridge observations
remain unchanged. Preparation and constructed controls make no provider request.
Root alone commits, dispatches and retains the actual hosted result.

V1 run `42982595287` remains unchanged: its exact-model access smoke succeeded,
then the first caller failed its marshal-serialization code check and four
later preflights recorded `OSError` without errno. V2 uses a separately authored
structural caller binder. The later original OSError cause is unproven; V2
prospectively corrects the listener preflight and records safe errno/message.

The source pin is `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`, bound by source-stage
manifest SHA-256 `78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463`.
All 136 staged AP2 source files and complete member identity must match; all
24 separately pinned x402 source files reachable on PYTHONPATH are also checked. Python
distribution versions derive from the frozen installed-assessment manifest,
SHA-256 `4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5`.
Platform-specific Windows distributions and local source packages are excluded
from the Linux requirements exactly as in V13. A fresh runtime inventory binds
the actual Python executable/version/prefix, required distribution versions,
loaded-runtime file hashes and pip-report bytes. Linux installed bytes do not
inherit Windows wheel fidelity.

## Treatments and declared cases

Each task starts fresh, unchanged `python -m roles.merchant_agent`,
`python -m roles.credentials_provider_agent` and
`python -m roles.merchant_payment_processor_agent` entries. They serve the
original RPC prefixes, cards, handler/stores, extension activation and business
tools on original loopback ports 8001, 8002 and 8003. Public original v0.3 cards
must become readable before the caller starts. No `genai.Client` or original
function body is replaced.

Before launch, an eight-second bounded bind-only preflight uses `SO_REUSEADDR`,
matching original Uvicorn listener semantics. It records every unsuccessful
bind's port, exception type and errno/message; a persistently occupied listener
is refused. No preflight connection or request is sent to an existing service,
and no foreign process is terminated. Before any card request, Linux `/proc`
socket inodes must show that the exact spawned native PID owns that loopback
LISTEN port. This closes the bind-release discovery race. Missing ownership
never authorizes a foreign card read. This V2 treatment requires Linux.

An owned HTTP accounting proxy uses the pinned SDK's supported
`GOOGLE_GEMINI_BASE_URL` configuration. Original SDK generation payloads and the
original `gemini-3.1-flash-lite-preview` model string pass through unchanged.
Provider authentication and HTTP transport headers belong to this explicit
proxy treatment. Its only upstream authority is
`https://generativelanguage.googleapis.com`, and its only path is
`/v1beta/models/gemini-3.1-flash-lite-preview:generateContent`.
Redirect following and environment proxy inheritance are disabled.

The owned scripted caller follows original shopper business functions and reads
only its own public Task. It receives prospectively declared human choices,
never evaluator/gold or private-journal data. The original ADK root tool surface
and autonomous shopper are not exercised by this treatment. The five cases are:

1. Original full business-function prefix, actual public OTP challenge, explicit
   human reply `123`, original continuation and actual public receipt read.
2. The same prefix with explicit wrong reply `wrong-human-reply`; retain actual
   continuation and subsequent Task observation.
3. The same prefix with no human OTP reply; retain waiting and public Task state.
4. A separately received original context is used for an adverse query/call;
   retain that result and recover only from a previously returned public Task.
5. After an actually observed completed receipt, repeat the original OTP call
   and retain every original outcome. No idempotence is presumed.

Public facts are frozen in `plan.json`; selections use offered index zero.
Changed catalog output, missing offered choices, task/store errors, wrong
model routing, timeouts and duplicate effects remain observed failures or
partial outcomes. The caller's success status is an observation, not independent
human gold or an automatically validated whole-task grade.

## Resource and failure rules

One exact-model forced-tool request checks actual access before any application
starts. Its actual status/body/usage remain retained on success or failure.
Failure leaves all five declared tasks unexecuted. Access does not establish
current account RPM/TPM/RPD or sufficient capacity for the complete study.
No fallback model, billing change or paid-tier substitution is selected.

The proxy serializes all nested callers through one lock and durable
started/finished allocation ledger. At most 80 upstream allocations include the
smoke. Allocation is consumed before the upstream send. Original SDK retries
can reach the proxy, but any non-200 response or upstream transport failure
stops subsequent upstream sends; later retries are locally refused and retained.
The owned forwarder itself never retries. Starts are spaced at least six
seconds, at most ten starts per minute in a continuous window apart from exact
boundary counting. This is a conservative runner rate, not verified quota.

Before any freeze or dispatch, independent source accounting identified at
least 64 ideal allocations across the five fresh paths including the smoke.
The implementation's initial 60-call proposal was therefore prospectively
corrected to 80, with no task removal, reordered outcome or prior execution.
The unchanged rate, byte limits and post-response usage stopping still apply.

Request bodies are limited to 128 KiB each and 200,000 cumulative bytes;
received bodies are bounded to 1 MiB. Recorded total-token usage is summed when
present. A successful response without valid positive usage stops further
requests and is explicitly counted as unknown usage. Reaching 100,000 observed
tokens also prevents the next call. This is **post-response stopping, not a hard
token or cost ceiling**: the final response may cross that threshold. Original
generation payloads are not secretly rewritten to impose an output-token cap.
Call and byte bounds are the prospective hard allocation limits.

Upstream HTTP timeout is 45 seconds. Service readiness uses at most 45 seconds
and remaining screen time. The parent caller deadline is at most 300 seconds
and remaining screen time; the caller independently bounds original awaited
calls and its own run. The 1,500-second screen deadline stops launches and waits;
bounded process cleanup and draining the final in-flight proxy request can
extend wall time beyond that execution deadline. Every launched process gets a
retained reap/error disposition. No failed or partially captured task is rerun.

## Isolation and retained evidence

Only the parent proxy holds the actual repository secret. Native processes
receive an unmistakable synthetic downstream key; the caller receives no
provider credential. Inherited endpoint, proxy and credential settings are
discarded from both child environments. Secret-bearing headers/exception text
are never stored. Exact secret bytes are redacted if unexpectedly echoed in a
provider body, with original non-secret observations otherwise preserved.

Every task's original databases, private signing keys, logs and CWD are in a
fresh temporary tree outside retained evidence. Only explicit public cards,
original watch output, process logs, caller public events/results and provider
request/response/usage receipts are copied into the artifact. Private `.pem`,
`.key`, `.env` files are excluded. A final scanner rejects provider-secret bytes
and private-key PEM material before retention. It scans actual artifacts, not
only filename exclusions.

The original `run.sh` dependency provisioning/reset/ADK-web workflow is not
qualified. Exact A2A wire-frame attribution, unchanged independent bridges,
human gold, untouched holdout and full-study scientific completion are not
claimed by this screen. Public service/watch and caller observations are kept
distinct from provider request bytes.

## Commands

```powershell
python -I -S -B scripts/run_ap2_original_native_provider_v2.py prepare --output <fresh-plan>
python -I -S -B scripts/run_ap2_original_native_provider_v2.py execute --plan <fresh-plan> --output <fresh-execution> --python <fresh-venv-python> --site-packages <fresh-site-packages> --pip-report <pip-install-report.json> --provider-mode live
python -B -m unittest discover -s tests -p test_ap2_original_native_provider_v2.py -v
```

Replace placeholder arguments with actual paths; never reuse an execution or
plan directory. Keep the venv executable's path rather than resolving its
symlink to the global Python binary. Hosted setup installs `plan/requirements.txt`
with a retained pip installation report before the explicit live step.
