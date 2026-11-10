# Separate hosted Linux admission profile

Status: implemented; hosted execution has not been dispatched or verified.

This profile runs the existing deterministic AgentOps N11 control followed by
candidate-gated B7 on a standard GitHub Actions Ubuntu 24.04 x86_64 runner. It
uses no paid/larger runner, no live model calls and no Gemini key. The job is
bounded at 20 minutes and retains its artifact for three days.

The failed local Windows RAM/commit gate remains valid. This new profile requires
at least 2 GiB of available physical RAM on its separate Linux host and records
the Linux memory sample. It never identifies that host as the previous WSL
installation or reuses a previous execution receipt.

## Pinned inputs and provisioning

`scripts/ci_agentops_admission_v1.py --check-inputs` checks all inputs without
importing application SDKs or launching processes. Root review and inclusion of
the ignored runtime inputs are required before the workflow is executable from
GitHub. They are:

- The eight checkout `PINNED_DOCS` in `scripts/agentops_admission_live_plan_v3.py`,
  excluding the historical `runtime/materialization.json`. The ninth input is
  the newly generated CI receipt staged at the same acceptance input path.
- `docs/research/source-evidence/agentops-bridge-control-v1/runtime/graph.json`.
- The same directory's `archive.json` and `runtime.zip`.
- The original required scripts, selected tests, `src/interoperability`, and
  `examples/{refinement-development,benchmark-development}`.

The bridge archive is 9,094,376 bytes, SHA-256
`c4567dc405e74d664921f038e6c5acb454c66fd85f42f21c04a10c8e75305864`.
Its 15 nodes and 2,938 regular files are checked against the preserved graph.
Each node declares MIT or Apache-2.0 and retains its license file. The graph
contains the two licensed bridge roots and excludes the unresolved-license
bridge. No package-install script is run for these Node dependencies.

The AgentOps archive is downloaded from the preserved ingestion URL, checked
against SHA-256
`491d1c0ee1bd6f54063eb183915b913fc458a277785eeb4ddfcb5efcba20ad0b`,
and its exact 421 regular files are extracted and verified. The original archive
label remains provenance evidence, not independent Git-object authentication.
The two inert link payloads are not materialized as symlinks.

The original `mise.lock` supplies the checksum-pinned uv 0.12.0 executable. It
installs managed CPython 3.13.1 inside a newly allocated reuse root and runs
`uv sync --locked` against the unchanged original `uv.lock`. The existing runtime
inspector verifies selected provider files, installed metadata, editable-source
identity and required versions. This does not authenticate every runtime byte.
The inspector's setup-receipt path points to a new CI dependency receipt, copied
into the artifact, and carries no reused WSL setup history. The workflow selects
Node22.13.0 through the pinned setup-node action and binds that executable to
`/usr/bin/node` in the disposable runner, preserving the original driver's
absolute executable path. This explicit runner setup satisfies mgcrea's Node>=22
requirement. Its version is verified and the original preparation freezes its
executable digest. No local Windows or retained WSL installation is changed.

The bridge materializer generates a new receipt under the new CI runtime root.
The staging bundle uses this fresh receipt at the original verifier's pinned-doc
path. The original WSL receipt in the local checkout remains unchanged and need
not be uploaded. Its immutable digest is recorded as a historical reference only;
the CI process does not load that receipt or assert its host identity. The new
receipt's digest is independently recorded. This substitution is the explicit
hosted-profile change and carries no old-host identity claim. Every script,
original source file, fixture, request and acceptance rule remains unchanged.

## Execution and acceptance

Each workflow dispatch creates a new namespace under `runs/ci-agentops-native`.
There is no application retry within an allocation. Pinned dependency sync is
bounded at 480 seconds, staging at 120 seconds and the original phase chain at
650 seconds. A timeout is a failed run and triggers owned-descendant termination.
The coordinator declines to start the native chain unless its 18.5-minute
allocation still has 680 seconds remaining, reserving time for evidence retention
within the 20-minute job. Slow provisioning can fail the run before any app starts.
If a terminal export is unavailable, the artifact includes a separately labelled
raw failure snapshot. That snapshot never asserts terminal integrity or success.

The original phase chain runs software checks, preparation, preflight, launch,
after-inspection and export. N11 must pass before B7. Readiness remains 65
seconds. B7 admission retains the 100,000 work budget and 30-second timeout.
The original checks require certificate-to-wire binding, task/context identity,
the original domain effect, unchanged unrelated state, source/runtime integrity,
clean terminal state, startup, asyncio return, interpreter exit and process
cleanup. A process exit code alone does not establish application success.

Only `attempt/result.json` with `status: strict_success`, plus successful original
phase checks and export, can make the CI profile successful. The workflow itself
does not modify any research checkpoint percentage. A passing deterministic
fixture does not qualify a second domain, a conversational corpus, novelty or
the full research-project rubric.

## Review and handoff

Review the three new files, run the read-only input check, then root can include
the required licensed inputs and push/dispatch the workflow. No workflow has been
dispatched by this implementation task. On return, inspect
`runs/ci-agentops-native/<run>-<attempt>/result.json` and the exported original
attempt, checker and raw stream receipts before making a research claim.
