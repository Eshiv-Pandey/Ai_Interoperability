# Native AgentOps control v5 after runtime revalidation

26 October 2026. This is a new native attempt, not a rerun or replacement of the
earlier Windows, mounted-filesystem, or inspection failures. The existing Linux
runtime remains at `external/runtime-agentops-linux-v4/venv/bin/python` inside
its original Linux replica. No installation, relocation, application patch or
fcntl shim occurs here.

The former inspector incorrectly assumed that native `fcntl` has `__file__`.
The separately versioned inspector v5 accepts an interpreter-provided built-in
or native extension and records its provider bytes. Its schema is
`agentops-installed-runtime-inspection/5`; this changes inspection, not AgentOps
or the upstream test. The previous inspection exception stays retained.

Before preparation, native v5 requires
`runs/agentops-native-eligibility/runtime-revalidation-v5/result.json` with schema
`agentops-runtime-revalidation/5`, status `installed_runtime_revalidated`, unchanged
original source, unique retained receipts, a successful non-timeout inspection,
and a matching `runtime_inventory` stdout digest. It verifies the new inspector
and revalidation coordinator hashes and the original setup/locked-sync receipts.
The managed interpreter's mode-0700/flock exclusion capability must pass, with
its exact interpreter command and complete successful capture receipts retained.
The original dependency sync must have succeeded; the later setup-inspection
failure is not relabeled as successful installation. The outer revalidation
coordinator owns its full source/runtime acquisition checks.

Preparation binds the revalidation-result digest as `runtime_revalidation`,
compares a fresh inventory to the revalidated JSON, hashes the original source,
native harness and immutable seed, and performs the unchanged mode-0700 directory
capability probe. Existing output directories are refused. Preparation failures
retain their receipts; no application is imported by preparation.

Execution accepts only a native-plan `/5`, rechecks the revalidation and all
prepared bindings, then reserves one attempt. Its fresh runtime inventory must
match both preparation and revalidation before pytest can start. The original
single upstream confirmation test, passive v2 observer, exact three passed pytest
phases, seed-equality checks and separate v2 effect checker remain unchanged.
No original application, SDK, model double, protocol input or grader behavior is
modified. Partial/failure evidence remains; no automatic retry occurs.

From the same Linux replica, only after successful revalidation:

```bash
python3 -B scripts/agentops_native_probe_v5.py prepare
python3 -B scripts/agentops_native_probe_v5.py run
```

The new output is `runs/agentops-native-eligibility/native-probe-v5`. The input
harness comprises this controller, original v2 coordinator/observer/checker/spec,
inspector v5, revalidation coordinator v5 and this protocol. Native plan,
preparation, execution and result schemas use `/5`; the original observation and
effect-check payload schemas stay `/2`.

Authored gate tests are software validation, not actual native execution. A
passing future native test remains in-process evidence rather than real HTTP or
bridge qualification. The separately versioned HTTP v3 controller must pass
its own native/runtime gates. C1 novelty, second-domain validity, evaluation and
human review remain open; this adaptation adds no research-gate credit.
