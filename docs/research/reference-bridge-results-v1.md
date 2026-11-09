# Whole-interface Carol bridge observations v1

**24 October 2026.** All four prospectively specified variants were executed once with unchanged pinned bridges and the disclosed Carol A2A 1.0 port. Amir ordinary, Amir modern Tasks and mgcrea typed continuation leave the original task waiting; mgcrea's existing raw alternative completes the original task/context. The results are independently checked development observations. They establish neither a new algorithm nor natural failure prevalence in unchanged deployed applications.

The [prospective contract](reference-bridge-probe-v1.md), SHA-256 `975730c259dfe4470377baeb9ce8b2f007df048a8559aa3dcd14768e4e800ef4`, was retained before every startup. Each variant used fresh port/bridge processes and its own task, the same typed initial request and authoritative pending receipt, and one `Well done!` answer. R4 selected its raw action directly from that public prefix; no failed typed answer preceded it. Its native IDs were obtained from MCP-visible replies. All permitted actions remain available to strong practical comparators.

| Variant | Actual final original task/context | Independently checked historical decision | MCP RPCs | Native HTTP requests |
| --- | --- | --- | ---: | ---: |
| R1: Amir ordinary | Preserved; input-required | Unknown | 6 | 5 |
| R2: Amir modern Tasks | Preserved; input-required | Unknown | 8 | 8 |
| R3: mgcrea typed | Preserved; input-required | Unknown | 6 | 5 |
| R4: mgcrea raw SendMessage/GetTask | Preserved; completed | Supported at the archival clock | 6 | 5 |

Waiting observations cannot establish unsupported: these historical graphs are incomplete. A modern outer complete acknowledgement is result delivery, not logical completion; R2's subsequent Tasks and authoritative ordinary observations still report input-required. R4's completed public result and separate native GetTask agree on the original association. Its success prevents calling mgcrea's typed omission loss of the complete write-enabled interface.

## Exact records and verification

| Variant | Immutable public trace | SHA-256 |
| --- | --- | --- |
| R1 | [runtime.json](../../runs/reference-bridge-observation/R1-amirk_a2a_to_mcp-reference-v1-2026-10-23T21-54-32-840Z-11416/runtime.json) | `e8450de64e1dbb43acd81c1d92850aa8d1e981505818ced54aac1d8733b0135d` |
| R2 | [runtime.json](../../runs/reference-bridge-observation/R2-amirk_a2a_to_mcp-reference-v1-2026-10-23T21-55-11-573Z-32780/runtime.json) | `81478f529d6a838bf759a539b91346e66e14aa63506f2116482edb02b8ea820c` |
| R3 | [runtime.json](../../runs/reference-bridge-observation/R3-mgcrea_mcp_a2a-reference-v1-2026-10-23T21-55-48-985Z-20692/runtime.json) | `2e9cabd0eaee3b2d6ab33dc70a0f6be76e9bc303bf8eb6114435ee7596c790db` |
| R4 | [runtime.json](../../runs/reference-bridge-observation/R4-mgcrea_mcp_a2a-reference-v1-2026-10-23T21-56-46-830Z-30760/runtime.json) | `dc08ccfdc166637a33e77b7a4faef1af275d3a8115e60d7443c7c47fc13ababc` |

Each directory separately retains native HTTP, process diagnostics/lifecycle, runtime configuration, exact pre-execution source/specification snapshots and dependency/source manifests. The public projector accepts only the MCP trace. A separately authored checker checks the projected fields, complete raw setup, IDs, bytes/hashes, intervals, original association and exact three-predicate goal. A separate explicit private input checks native correlation; private evidence never supplies missing public observables. See the [independent software review](status-projection-independent-review.md).

The [verification](../../runs/reference-bridge-observation/verification-v1.json), SHA-256 `dcda0a5c6d9bfd5a0461d0d01ecc7d36b45751fee21d74afd9994aa98f4657c4`, passes all four actual observations. It checks frozen snapshots/source ledgers, source stability, runtime configuration, archived bridge source/dist, byte costs, normal cleanup, public/native projection, finite baseline/oracle agreement and certificates. Expected source hypotheses were not capture-success or verifier-success conditions.

Exact code and input data were copied to a **388-file archive before full verification**. The [isolated clean-interpreter replay](../../runs/reference-bridge-observation/clean-replay-v1.json), SHA-256 `a53d27e741f6e270c2f96f54a0b514927a5c42c5863dfda7cf8b874596fc3ba3`, reproduces all saved check rows exactly, imports only archived implementation modules, leaves archive hashes unchanged and passes **205 tests with zero failures, errors or skips**. Those tests comprise the earlier 146-test foundation/original-native suite plus 24 new projector and 35 separate checker controls. Constructed raw wrappers and corrupted inputs are labelled software controls; they are not extra bridge trials. This replay checks software/data, not a fresh execution of the native services.

Preparation corrected our validator's protocol assumption before new captures: Amir 2026-07-28 uses `server/discover` and per-request metadata; mgcrea uses one 2025-11-25 initialize exchange and initialized notification. An ad hoc Windows-default cp1252 read also produced a transient false hash alarm; explicit UTF-8 reads confirm the unchanged earlier archive. Both mismatches are covered by rejection controls. Capture preparation additionally fixed early-exit promise handling and finalization error retention. No correction or repeat was performed after these four executions began.

## Resource and lifecycle accounting

| Variant | MCP request/response entity bytes | Native request/response entity bytes |
| --- | ---: | ---: |
| R1 | 2,174 / 8,642 | 835 / 4,870 |
| R2 | 3,144 / 8,904 | 1,177 / 7,331 |
| R3 | 1,125 / 19,515 | 965 / 4,501 |
| R4 | 1,451 / 20,150 | 1,066 / 4,569 |

Totals are **26 MCP RPCs plus two initialized notifications**, **7,894 / 57,211 MCP entity bytes**, and **23 native HTTP requests** (four card fetches, eight sends, eleven gets), **4,043 / 21,271 native entity bytes**. Body logging and setup costs are disclosed; TCP framing and implicit headers are excluded. No latency, efficiency, model efficacy or statistical prevalence claim follows from these single development observations.

All eight recorded child processes exited normally with code 0/no signal; all four Carol listeners reported closed. Capture-owner and parent read-only process queries found the recorded bridge, Carol and capture-parent PIDs absent. Git diffs against the pinned commits show no bridge source/package/lock changes. No broad kill, hidden retry, model inference or paid experimental token use occurred.

The separately retained [parent live-state audit](../../runs/reference-bridge-observation/source-runtime-audit-v1.json) verifies all 14 distinct source/dist/runtime-dependency trees against their pre-execution file hashes, both pinned Git heads and tracked source/package/lock bytes, the Node binary hash and absence of all 12 recorded parent/child PIDs. Its exact driver is saved separately. Process absence is an observation at the audit clock; replaying old files cannot establish current process state.

The typed native serializers supply empty references, which the protobuf transport may omit on the wire. Carol's application-specific follow-up branch requires nonempty references; it does not validate reference equality or enforce cross-task authorization. The raw action preserves the supplied nonempty own-task reference. Raw `A2A-Version` header absence is retained, with the authored port's declared/default 1.0 behavior. This is not a protocol-conformance claim; a declared card alone does not excuse a version-selection error in an arbitrary service.

The later [version-default fidelity audit](port-version-default-audit-v1.md) confirms that this wrapper supplies 1.0 on **absent** headers, overriding the specification/SDK default of 0.3. Actual R4 raw requests supply neither a version header nor a URL query parameter. Raw completion therefore applies to this authored version policy; generic A2A 1.0 raw-recovery compatibility remains unestablished. No recorded capture or prospective specification was changed by this audit.

## Scientific consequence and next gate

The [unchanged original A2A 0.3 controls](reference-continuation-results-v0.md), [separate version-matched native controls](reference-port-native-results-v1.md), source branch and four real bridge trajectories now form a checked, bounded evidence chain. The JavaScript port's disclosed changes remain material: this chain does not establish arbitrary-input equivalence, unchanged 1.0 application eligibility, two application domains or natural deployed failure rates.

No C1 advantage is demonstrated. A complete guarded-action model and the same raw alternative already explain the observed contrast. The rejected one-query efficiency pilot remains unrun. The [novelty screen](reference-novelty-screen-v1.md) defines the next bounded source/method decision; scaling an existing reachability procedure or buying model tokens does not pass it.

**CP2 remains in progress; overall progress remains 5%.** The registered title and approved 45-day scope are unchanged. Prospective source/model fidelity, a substantive contribution against strong fair comparators, and recorded human novelty/feasibility review remain mandatory. You are the sole confirmed researcher; supervisor review after substantial progress is possible but unconfirmed. AI-authored independent software checks do not constitute that human review.

For a new software/data verification and isolated archive replay, use new output names:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/verify_reference_bridge.py --output runs/reference-bridge-observation/verification-new.json
.venv/Scripts/python.exe scripts/replay_reference_bridge.py --verification runs/reference-bridge-observation/verification-new.json --python tmp/foundation-replay-env/Scripts/python.exe --output runs/reference-bridge-observation/replay-new.json
```

The original one-attempt probe is closed. A future service execution needs a separately versioned prospective run record, rather than a silent repeat under v1.
