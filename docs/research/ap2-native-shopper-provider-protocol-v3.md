# Original native shopper V3: preserve the virtual-environment launcher

V3 allocates one fresh adaptive development task after run 43045731741. V2
remains one unexecuted task: runtime preflight failed before provider smoke,
native services or shopper calls. Its exact 529,223-byte archive has SHA-256
`c41af803458b432eaa934e606169a76235488c65472bd4c27e41ac73a2deee56`.
The [V2 results](ap2-native-shopper-provider-development-results-v2.md) preserve
the error, denominator, source diagnosis and zero provider allocations.

All 182 required versions match the retained pip installation report, and pip
check passes. V2 changed the CLI's Python path from V1's `absolute()` to
`resolve()`. On a Linux virtual environment whose Python is a symlink, resolution
selects the global executable and loses the virtual-environment launcher.
The actual selected-interpreter distribution census was not retained by V2;
the diagnosis is derived from source and does not invent specific mismatches.

The new [V3 runner](../../scripts/run_ap2_native_shopper_provider_v3.py) restores
`absolute()` for the executable passed to runtime preflight and child launches.
Fresh case/schema/successor metadata and temporary/source-snapshot names keep
this allocation separate. Original sources, SDKs, required versions, model
payloads, tools, public actor, native entries and V2 provider boundary remain
unchanged. The owned 120-second sender option, 150-second maximum drain,
80-call and 200,000-byte bounds, six-second pacing, 100,000 known-token stop,
600-second shopper limit and 900-second screen deadline remain unchanged.
Unknown successful, failed and unclosed consumption remains unmeasured.

[Launcher controls](../../tests/test_ap2_native_shopper_provider_v3.py) exercise
the actual V2 and V3 CLI path choices with the executor replaced, preserve the
source/plan/runtime limits, and test a real filesystem symlink. Three constructed
controls pass locally; the real symlink control skips on Windows where link
creation fails. It must pass on Linux before the workflow reaches live execution.
The existing 15 sender/drain controls remain in the workflow. None of these
software controls executes the original application or calls a provider.

Root owns review, freezing the remote head, one dispatch and exact retention.
The one declared case is `ap2-native-shopper-provider-v3-correct-human`.
The original V1 timeout and V2 preflight failure are preserved separately.
Whole-task grade remains null until accountable semantic review; this is not a
held-out study, human gold qualification, unchanged `run.sh` provisioning,
hidden-effect audit or real-settlement result.
