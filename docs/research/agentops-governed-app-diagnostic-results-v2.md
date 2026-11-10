# Verified original App socket diagnostic v2

[Run 42878197269](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42878197269)
at `cd5e8570f17ca26cf93ef0407fbe0765f2d3137c` retains d01 completed and d03
input-required with no approved action or business effect. Both strict profiles
remain failed, solely at `no_network_attempts`; the aggregate is **0/2**.
The fresh raw/state audit checks all 117 extracted files, the original 421
source members, raw SSE/task/database correlations and each retained diagnostic
source frame. It invokes no App, model, solver or private evaluator.

Each case records the same actual import-time urllib3 call:
`urllib3.util.connection._has_ipv6("::1")` creates an AF_INET6/SOCK_STREAM socket
and attempts `bind(("::1", 0))` at line 127. The module's line 137 invokes the
probe during cold import. The exact retained helper has 4444 bytes and SHA256
`2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74`.
The target, socket attributes, bounded stack and source hashes were recorded
durably before PermissionError. The original v1 bind lacked these records;
this attribution applies to the fresh v2 observations.

The [fresh semantic review](../../runs/ci-agentops-governed-app-pilot-v2/retained-42878197269-1/semantic-read-review-1.json)
preserves the strict failures and verifies actual d01/d03 model/tool/event
counts as 2/1/4 and 5/5/12. The retained ZIP is 23220764 bytes; SHA256
`fbfdd5903f054a7b393975d91a3ab9391aeb2cfff78fdf465a04acbbe612b4ef`
matches GitHub's artifact digest.

The source-bound cold-import successor temporarily disables Python's advertised
IPv6 capability while importing the unchanged helper, restores the flag before
App startup and retains urllib3's IPv4-only cache. It permits no socket operation
and makes no native-network equivalence claim. See the versioned
[diagnosis](agentops-socket-bootstrap-diagnosis-v2.md) and
[reference allocation](agentops-governed-app-reference-v2.md).

The first six-recipe allocation, run 42880999920, failed before App launch:
constructed evaluator controls required the original seed database, absent in
the fresh Git checkout. Its metadata and failed logs are retained at
`runs/ci-agentops-governed-app-reference-v2/failed-42880999920-1` with zero
executed application cases. The separate v2.1/v3 allocations stage all original
source members before controls. Earlier failures are not replaced.
