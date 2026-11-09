# Disclosed post-capture checker correction v2.1

24 October 2026. All four v2 service cases already ran once. Preserve their
runtime bytes, frozen spec, checker/replay v2, initial checks and initial replay
archives. Do not run any service case again. This correction changes software
checking of the same evidence; it is not a new trial or human/independent review.

The initial v2 checks returned: B1 valid/complete/expected; B2 valid/complete but
an initial-state expectation deviation; B3/B4 checker AttributeError in cost
aggregation, plus the same initial-state deviation. The original replay archives
all remained byte-unchanged but failed their complete replay claim. B1 attempted
25 mutations; three outgoing-answer mutations failed during setup because the
selector called .get on the card GET's null request JSON. They were explicitly
counted as failures, never as rejected claims. B2-B4 ran zero mutations because
their initial checker did not establish the complete expected-outcome claim.

Corrections are separate files, scripts/check_official_handler_bridge_v2_1.py and
scripts/replay_official_handler_bridge_v2_1.py. Their hashes are frozen before
corrected checking in post-capture-checker-correction-v2.1.json.

1. Notification response bytes are zero when response is null. The unchanged
   mgcrea caller sends notifications with no response. Actual pipe reconstruction
   must still match every request/reply/notification byte; nothing is invented.
2. The unchanged bridges request returnImmediately true in B2-B4. Their first
   native response really is SUBMITTED and has no artifact yet. The earlier
   blanket initial INPUT_REQUIRED expectation was incorrect for that mode.
   The correction retains the initial state and its original expectation
   deviation, allows source-declared nonterminal initial states only in that
   mode, and additionally requires a genuine same-task/context GetTask with the
   expected one-entry artifact, inside the existing public pending query and
   before the fixed answer. The unchanged 5s observation bound still applies.
   E1's final state, serialized references, outgoing headers, binding and HTTP
   result expectations are unchanged. This is a disclosed checker expectation
   correction, not a retroactively pre-registered initial-state prediction.
3. The replay selector treats null request JSON as absent; the three outgoing
   mutations now target the genuine retained answer exchange. Setup errors
   continue to fail a replay claim. Added mutations remove the pre-answer source
   artifact and contradict returnImmediately in a SUBMITTED initial response.

Corrected replay prospectively attempts 26 mutations for B1, 27 for B2, and 28
each for B3/B4, only if the corrected same-byte check succeeds. Original frozen
checker/replay files are archived alongside the corrected versions. Runtime
trees and both actual subprocess directories are copied without live-workspace
fallback. The isolated replay imports no SDK/driver, starts no bridge, performs
zero service requests/model calls, and must leave its archive unchanged.

These controls provide no C1 novelty, qualifying second domain, natural failure
prevalence, human review or added checkpoint credit. CP2 remains open at 5%.
