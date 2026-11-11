# Offline analysis of retained original native shopper V3

The additive [V3 analyzer](../../scripts/analyze_ap2_native_shopper_provider_v3.py) checks the actual root-retained V3 archive using an explicit expected run and full head. It binds the [reviewed preparation-1 template](../../runs/ap2-native-shopper-provider-development/v3/preparation-1/plan.json), SHA-256 `49343a1fa5c7836b6acf851ce213a4699718026dd7ebaf305a2f9186c7a9d63f`, compares every plan field except preparation timestamp, and validates all five frozen owned source snapshots. Plan/result schema 3 and `ap2-native-shopper-provider-v3-correct-human` case identity are checked directly; retained schemas are not rewritten.

V3's frozen execution keeps the V2 sender/boundary and `ap2-provider-drain/2` record schema, plus the original V1 worker. Accordingly the analyzer reuses the unchanged V2 drain reconstruction and V1 public/SDK/provider helpers. Its pinned V2 analyzer SHA-256 is `c1211733a21dd8bc8ea1aee5135b471c43f53fe7459eb998daf678160375e07d`; that module independently pins V1 helper SHA-256 `fd07c3609400f951d8500ce97f1cc655fc4ed654b7836597c30d26262ef930ab`. All frozen V1/V2/V3 execution sources and earlier analyses remain unchanged.

Root supplies the actual retained path and run after terminal retention:

```text
python -I -S -B scripts/analyze_ap2_native_shopper_provider_v3.py --retained <actual-retained-directory> --output <fresh-analysis-directory> --expected-run <actual-V3-run-id> --expected-head 04dfdf2a3b1d1c75ad991e610df61815a329669e
```

The inherited reader binds expected run/head, archive hash/API digest, completed run status, ZIP membership/member hashes and extracted inspected bytes. A fresh additive output records exact analyzer/helper/template hashes, source bindings and inspected members. No constructed fixture or virtual schema conversion substitutes for an actual retained archive.

The partial-runtime-preflight branch preserves its original error, one unexecuted case and zero allocations when applications/providers did not start. Post-preflight results require the retained runtime manifest and its result digest. Original ADK errors, visible replies, proposed versus delivered actor decisions, consent/OTP timing, visible USD prices, tool identity/order, Cart selection and sample receipt shape retain their existing narrower evidence scope. An owned rendering stop, model/provider/transport error and unreached branch stay separate. Whole-task grade remains `null`; no human-gold, held-out-study, hidden-effect or settlement qualification is inferred.

Inherited drain analysis joins the standalone/result freeze record with the raw provider census. Active/queued handlers and consumed allocations are separate counts. Unclosed consumption remains unknown even when a sender later finishes after capture freeze. A completed-handler assertion with open allocations, altered counts/bounds, absent freeze or post-freeze ledger timestamps remains an inconsistency. The recorded wait and transport option do not prove a whole-request socket wall-clock cap.

Seven new [V3 analyzer controls](../../tests/test_analyze_ap2_native_shopper_provider_v3.py) cover direct V3 schema/case binding, forged V3 runner bytes, frozen launcher/public-fact/source membership, result schema/denominator, partial-preflight error preservation, contradictory executed-preflight claims and reviewed-template identity. They run only owned standard-library analysis. The existing 19 V2 analyzer controls and frozen sender/drain controls are reused rather than duplicated. These software controls supply no actual V3 task or provider result.
