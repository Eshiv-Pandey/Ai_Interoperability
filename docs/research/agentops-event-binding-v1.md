# Bind public and private AgentOps event views

29 October 2026. The [event binder](../../src/interoperability/agentops_event_binding_v1.py)
checks existing [raw ADK](agentops-raw-events-v1.md) and
[public protocol](agentops-public-events-v1.md) exports. It executes no
exporter, database, SDK, application or model code. It supports the
[grading contract](upstream-agentops-grading-contract-v1.md), with task/effect
qualification kept separate.

## Comparison and boundaries

The binder verifies both input receipt manifests, exact allocation membership,
copied source hashes, raw/decoded JSON agreement and function projections. It
derives public exchange classification and protocol headers from the copied
wire bytes. Every projected function representation must have one matching
source origin; a projected label cannot hide executed parts that remain in a
copied reply. Origins include task, context, protocol header, identity, part
index, exchange and location. Duplicate ownership or representations fail.

Task metadata must explicitly identify an existing runtime app/user/session;
the binder does not infer it from a synthetic user-ID naming convention.
Declared raw event app/user/session values must agree with their table rows.
Artifact parts match raw event ID, part index, invocation, author and full
function payload. Function messages without ADK event metadata instead require
a unique full-payload match within the recorded session scope. Their public
ADK identity remains absent; the matched private ID is an evaluator relation.

Payload values/types are exact except the declared protobuf representation of
`response.audit.id` and `schema_version`: a nonnegative raw integer within
`2**53-1` may match its equal integral public float. Booleans and other numeric
coercions fail. Both pending and executed responses sharing an original action
ID remain distinct observations. Partial inputs, missing IDs or ambiguous
matches remain unresolved; malformed or contradictory evidence fails.

Manifest verification establishes consistency of the recorded copies. It does
not authenticate a self-resealed receipt or independently reconstruct every
JSON table from the database. Use externally retained byte identities and the
independent input audits when establishing provenance. The binder claims no
causal order, client receipt, complete stream, source authentication, business
effect, upstream-case outcome or admission qualification.

For other existing exports, use a new output:

```powershell
python -B src/interoperability/agentops_event_binding_v1.py --raw-export RAW_EXPORT --public-export PUBLIC_EXPORT --output NEW_OUTPUT
```

The output retains both complete input bundles under `inputs/raw` and
`inputs/public`, both checker implementation sources, a prospective plan and
the comparison receipt. It refuses an existing output and verifies input,
implementation and captured-file preservation. Failed allocations are retained.

## Completed checks

The [captured software validation](../../runs/agentops-event-binding/software-v1/result.json)
passed **15 tests with zero skips**, with original and captured source unchanged.
Resealed adversarial fixtures test omitted completed replies, fabricated
profiles/origin reuse, raw scope contradictions and conflicting message ADK
metadata. Other tests cover phase retention, ambiguity, missing IDs,
manifest/projection tampering, source mutation, exclusivity and audit numbers.

The once-only [N11 comparison](../../runs/agentops-event-binding/native-v12-N11-v1/result.json)
passed with **5 verified function pairs**: **3 recorded artifact identities**
and **2 message payload relations**, with no unresolved pair. It verified
all **9 raw export files and 50 public export files**. This allocation is
consumed. The inputs remain the historical `Restart inventory.` fixture,
not one of the 21 upstream benchmark cases and not a fresh native execution.

The [independent AI audit](../../runs/agentops-event-binding/native-v12-N11-v1-independent-review.json)
passed **109 checks**, with zero failures and **135 monitored files unchanged**.
It checked all input/binding/software files, the five relations, actual runtime
metadata and all 21 exclusive copied-wire function representations. It executed
no comparator, exporter, SDK or application. This is consistency review, not
independent source authentication or human acceptance.
