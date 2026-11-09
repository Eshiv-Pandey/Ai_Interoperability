# Installed SDK version-default control results v1

Checked **24 October 2026**. The once-only four-case control prepared in
[the prospective specification](version-default-control-probe-v1.md) completed
in process 18924 with exit code 0. That process is now absent. No application,
server, child process, network request or model call was made by the capture.
These are **SOFTWARE/SDK CONTROL** results, not a new bridge or application finding.

| Case | Actual requestedVersion input | Effective version | Actual validation against JSONRPC 1.0-only card |
| --- | --- | --- | --- |
| D1 | Property omitted | 0.3 | VersionNotSupportedError |
| D2 | Empty string | 0.3 | VersionNotSupportedError |
| D3 | 1.0 | 1.0 | Accepted; undefined return |
| D4 | 0.3 | 0.3 | VersionNotSupportedError |

All three semantic exceptions carry reason `VERSION_NOT_SUPPORTED`. Separately
calling the official serializer yields JSONRPC code `-32009`; these serialized
objects were not received over HTTP. Direct costs were four builder calls, four
validator calls, one support-set call and three optional serialization calls.

The [raw report](../../runs/version-default-control/sdk-version-default-v1-2026-10-24T11-29-23-093Z-18924/report.json)
has SHA-256 `16ae4e0202eff104d568894479fa5fd2862008e3199d141eb1a1ed7d0629ef37`.
The [separate checker result](../../runs/version-default-control/check-v1.json)
verifies actual inputs, call order/count, returns/errors, events and **167 preserved
source/dependency files**. The checker was snapshotted before SDK import. Its
authorship is a separate implementation by the integrating assistant, not
independent human review. Post-execution source/dependency checks found no changes.

The [clean archive replay](../../runs/version-default-control/clean-replay-v1.json)
uses that exact pre-execution checker in an isolated Python process with no SDK
import. All **173 archived files** remained unchanged; **18 evidence mutations**
were rejected, including fabricated wire fields, altered defaults, incorrect
call counts, nonterminal outcomes, duplicate JSON keys and escaping paths.
Changing claimed pass flags did not affect the checked evidence. These are
software integrity controls, not 18 scientific trials.

Replay the retained evidence without re-running the original SDK calls:

```powershell
.\.venv\Scripts\python.exe scripts\replay_version_default_control.py `
  --report runs/version-default-control/sdk-version-default-v1-2026-10-24T11-29-23-093Z-18924/report.json `
  --output runs/version-default-control/clean-replay-new.json
```

The output and its archive must be new paths; existing attempts are preserved.
No dependency installation is required for this evidence replay.

This confirms the installed SDK's function default and the transfer restriction
in [the port fidelity audit](port-version-default-audit-v1.md). It does not test
HTTP header/query parsing, the official Express adapter or whole-interface raw
recovery. R4 remains a historical success on its disclosed authored port.
Prospective route fidelity, a substantive method advantage and actual human
review remain open. **CP2 is not passed; verified progress remains 5%.**
