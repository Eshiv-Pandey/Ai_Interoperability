# Verified installation failure and prepared runtime resume

26 October 2026. This supersedes the v5 launch instruction in the mutable
handoff. The original v5 attempt exists and is terminal; it must not be repeated.

The existing parent checker verifies all **457 exported files**, including the
442 original replica inputs. Its [read-only report](../../../../runs/agentops-native-eligibility/linux-filesystem-v5-parent-recheck-v1.json)
records artifact integrity, not native or HTTP success. The raw locked-sync
receipt in that exported workspace reports exit 0 without timeout for the
original `uv sync --locked` command. The subsequent `installed-runtime` stderr
identifies `fcntl.__file__` as the failing assumption. Both the outer attempt
and the inner setup retain their failed status. Neither application control ran.

The interrupted continuation already created inspector v5, native v5, HTTP v3,
and resume v6. This continuation reviewed those files and added eight authored
resume orchestration controls. The [current validation](../../../../runs/agentops-native-eligibility/software-validation-runtime-resume-v6/result.json)
passes **36 tests**: six native-module/export tests, eight resume tests, ten
native prerequisite tests and twelve HTTP prerequisite tests. It retains exact
source snapshots, commands and process streams. The PowerShell launcher also
passes its parser check. The previous native/HTTP validation reports remain
unchanged. These checks neither execute Linux nor import the application.

Resume v6 checks the old export against the retained Linux workspace, preserves
the old inputs, adds the new versioned scripts, and uses the existing installed
interpreter. It performs no installation. New runtime revalidation must pass
before the original native confirmation/effect control; native success must
precede the disclosed HTTP fixture. Failures retain their receipts and prevent
dependent execution. Native built-in and extension module identities are
accepted; Python shims are rejected. The managed interpreter is separately
tested for filesystem access and flock exclusion.

The sandbox's current read-only Ubuntu probe still returns
`Wsl/Service/E_ACCESSDENIED`. Process enumeration via CIM was also denied;
the narrower Windows process listing returned no WSL process. No claim about
the contents or availability of the live Linux workspace follows from those
limited observations. The launch command from normal PowerShell is:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v6.ps1
```

The new attempt writes to
`runs/agentops-native-eligibility/linux-runtime-resume-v6`. If the saved Linux
workspace is missing or has changed, the launcher stops for inspection. Do not
reinstall, replace an earlier attempt, or apply the old v5 success checker to
v6 schemas. A returned v6 package needs its own schema-aware parent verification;
software checks do not establish real-capture compatibility.

The current context records are preserved under `snapshots/continuation-v13`
before integration. The input seal and verification alongside this note bind
the new scripts, validation, prior terminal export and context update. They
provide integrity checks, not independent capture authentication.

The next application/source work is the actual Linux native/HTTP control and
confirmation-channel analysis against the installed SDK. Original bridge
qualification, whole-interface fidelity, a substantive C1 method advantage,
second-domain validity, full evaluation and human review remain open. CP2 is in
progress, CP7 pending, verified credit 5%; the research/artifact/paper goal is
not complete. No model inference or scientific gate credit is added.
