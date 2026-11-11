# Original native shopper V4: match the selected worker's public facts

V4 prospectively allocates one fresh adaptive development case after retained
V3 run `43055390208`. V3's runner supplied a V3 case ID to the immutable V1
worker, whose strict public-facts guard expected its V1 ID. The worker stopped
before importing ADK or the original shopper and before its model request.
V3's task failure and all its actual provider allocations remain retained.
Root owns the separate actual V3 analysis; this protocol does not alter it.

The new worker `scripts/ap2_native_shopper_provider_worker_v2.py` is an exact
byte copy of V1 except two literals: its public case ID is now
`ap2-native-shopper-provider-v4-correct-human` and its result schema is
`ap2-native-shopper-provider-worker/2`. Public actor grammar, price/currency
checks, original imports/models/tools, input separation, network/process
guards, client cleanup and all bounds remain byte-identical.

The separately copied V4 runner selects that actual worker for the child
command and includes its exact source bytes/hash in the prepared `OWNED`
snapshots. Plan/result schemas and successor/case metadata identify V4. Every
public field remains identical to the earlier proposal except the case ID.
Before provider smoke, original runtime execution or App imports, a standard-
library preflight compares the prepared public facts with the selected worker's
`public_facts()` using canonical JSON, including field types. It checks the
selected owned import origin and records the worker-source digest and exact
agreement. The check runs during preparation, plan verification and again
before execution; a mismatch cannot reach runtime or provider smoke.

An executed V4 allocation retains `worker-public-facts-preflight.json` before
runtime census or provider boundary construction. The V2 provider boundary and
V3 `.absolute()` virtual-environment executable choice are retained. Sender/
drain behavior, original SDK/client timeouts, model payloads, native entries
and private source copies remain unchanged: 120-second sender option,
150-second maximum drain, 80 upstream-call budget, 200,000 request-byte bound,
six-second pacing, 100,000 known-token stop, 12 user turns, 160 ADK events,
262,144 bytes per owned event, 600-second worker and 900-second screen deadline.
Unknown successful, failed and unclosed usage remains unmeasured.

Eleven standard-library controls reproduce V3's actual worker guard rejection
without starting its actor or importing ADK; verify V4's exact public agreement
and child selection; reject field/type drift before provider smoke; verify
selected-worker source snapshots; preserve the launcher and all limits; and
retain the agreement receipt on a constructed runtime stop. They execute no
original application, SDK, listener or provider.

```powershell
python -I -S -B -m unittest discover -s tests -p test_ap2_native_shopper_provider_v4.py -v
```

Root owns the independent review, new CI workflow, source freeze, dispatch and
exact retention. V1/V2/V3 source and outcomes remain unchanged. Actual V4 native
execution, accountable semantic results and full-study qualification are still
pending; this wiring correction does not establish a whole-task grade, human
gold, independent holdout, original `run.sh` provisioning or settlement result.
