# Official SDK HTTP version control results v1

Observed and checked **24 October 2026**, under the
[prospective ten-case specification](sdk-http-version-probe-v1.md). This is a
**SOFTWARE/SDK HTTP CONTROL USING THE DISCLOSED CAROL EXECUTOR**. The actual
unchanged SDK 1.1.0 Express JSONRPC handler used its default version policy.
The earlier port's custom HTTP server was not started or changed.

| Cases | Actual version input | Actual HTTP / JSONRPC result | Application outcome |
| --- | --- | --- | --- |
| H1, H2, H4 | Absent, empty, or 0.3 header | HTTP 500; error -32009, VERSION_NOT_SUPPORTED | No new executor task |
| H3 | Header 1.0 | HTTP 200; successful task result | Source-valid pending task and artifact |
| H5 | Query A2A-Version=1.0, absent header | HTTP 500; error -32009 | No new executor task |
| H6 | Header 1.0 and matching query | HTTP 200; successful task result | Separate source-valid pending task |
| H7, H8 | Header 1.0; public H3 task/context | HTTP 200; same-task answer and GetTask | Original task/context completed |
| H9, H10 | Original-task GetTask, absent header, without/with query 1.0 | HTTP 500; error -32009 | Existing application task contexts unchanged |

The run made **ten actual loopback requests once**, with no retry or polling,
remote network request, child process or model call. Process 30148 completed
with exit code 0 and is now absent. All server connections closed and
`server_listening=false` was recorded. The earlier executor source, installed
bridge environments and all monitored dependency bytes remained unchanged.

The [raw report](../../runs/sdk-http-control/sdk-http-version-v1-2026-10-24T12-14-29-559Z-30148/report.json)
has SHA-256 `e4fb684bb8357e891aca85b48ad5f4210c9bd0581dc447a38cf51b786219901f`.
Client entity bytes and actual server-ingress headers/bodies agree. The
[separate corrected checker](../../runs/sdk-http-control/check-v1.1.json)
checks public task/reference bindings, native completion, version rejection
boundaries, raw entities, costs, event records and **925 preserved files**.
It is integrating-assistant software, not independent human review.

## Retained checker error and archive replay

The pre-execution checker incorrectly required HTTP 200 for all responses.
Its first check failed on the handler's actual HTTP 500 version errors. The
[failed check](../../runs/sdk-http-control/check-v1.failed.json), original checker
snapshot and unmodified raw run remain available. Inspection of the actual
handler's catch branch confirms its `res.status(500).json(errorResponse)` behavior.
The **post-run v1.1 checker correction** requires that source-supported status
for version errors and HTTP 200 for positives. No service case was rerun and no
prospective scientific hypothesis was rewritten.

The [clean replay](../../runs/sdk-http-control/clean-replay-v1.1.json) checks an
unchanged **932-file archive** without SDK import or service execution. It
reproduces the original checker's exact failure, validates all ten controls
with the explicitly later checker, and rejects **13 evidence mutations**.
Those include wrong public references, a changed initial artifact, completion
in another context, matching but incorrect HTTP error statuses, changed ingress
headers, missing cases and a server left open. These are software controls,
not additional scientific observations.

```powershell
.\.venv\Scripts\python.exe scripts\replay_sdk_http_version.py `
  --report runs/sdk-http-control/sdk-http-version-v1-2026-10-24T12-14-29-559Z-30148/report.json `
  --output runs/sdk-http-control/clean-replay-new.json
```

Use a new output/archive path. Evidence replay requires only Python and the
retained bytes. The original experiment's dependency setup used verified
cached release tarballs and copied SDK/jose files; its provenance lock and
failed npm setup logs are preserved separately. No package scripts ran.

## What this establishes for admission

The pinned specification permits a version query parameter. The tested official
Express JSONRPC handler reads only the header and rejects the observed query-only
requests as effective version 0.3. This is a concrete configuration-specific
fidelity boundary, with header-positive native controls. A card/profile that
advertises 1.0 alone therefore cannot certify these observed unversioned or
query-only requests through this exact handler.

This does not establish generic A2A query non-support, whole-interface bridge
impossibility, deployed failure prevalence or algorithmic novelty. No MCP bridge
was executed in this control. The existing R4 raw success still applies to its
disclosed authored wrapper, which supplied 1.0 for an absent header. A later real
bridge comparison against this official handler needs its own prospective
specification and unchanged permitted action paths. Ordinary source-aware guarded
reachability remains a fair comparator.

**CP2 remains open; verified project progress remains 5%.** C1's substantive
advantage, two-domain eligibility and actual human scientific review remain
unproved. The full method-led study, reproducible artifact and paper objective
is preserved.
