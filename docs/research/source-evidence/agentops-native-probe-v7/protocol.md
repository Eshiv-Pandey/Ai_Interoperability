# Native control v7 with classified denied initialization probe

Prospective correction, 26 October 2026. This version retains the upstream
confirmation node, immutable seed, original two requests, four observed database
boundaries, exact pytest phases and the successful v7 installed-runtime gate.
The original native-v6 attempt remains failed and cannot authorize HTTP.

Observer v3 uses socket policy v1. The exact pinned urllib3 `_has_ipv6` code,
called directly by its original module initialization, can record a denied
`AF_INET6/SOCK_STREAM` bind to `::1:0` separately. The same RuntimeError is still
raised before the bind reaches the OS. Other binds/connections remain unexpected
and fail the control. Detailed event records replace the old event-only log.
No upstream application, test or installed SDK code changes.

Effect checker v3 requires the new metadata and applies all original v2
boundary/effect requirements. In particular, only one target status and one
attributed audit row may change after confirmation; no extra domain changes
are accepted. Legacy profiles cannot be relabeled as successful observations.

Run only through the [sealed v8 coordinator](../agentops-socket-policy-v1/protocol.md).
Native output: `runs/agentops-native-eligibility/native-probe-v7` in the retained
Linux workspace. Preparation compares the current installed runtime to its
successful setup inventory; execution repeats this check before pytest. Every
attempt is exclusive. This is an offline in-process control, not real HTTP,
bridge qualification, human validation, a novel method or live-model evidence.
