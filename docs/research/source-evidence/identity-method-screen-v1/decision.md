# Identity representation and freshness screen v1

Recorded 25 October 2026 (Asia/Calcutta). **No C1 technical distinction is
demonstrated.** This source/design screen examines an exact compact identity
representation as a possible checking-cost route. No candidate, solver,
performance trial, source-modified runtime or bridge/application case was run.
The full method objective remains active, CP2 is open and credit remains 5%.

## Question screened

Could storing identifier origins, equality classes and scope bindings avoid
enumerating opaque task/context/handle strings while preserving the original
bounded may-compatibility decision and independently checkable certificates?
The target remains existence of a permitted completion within the original
horizon, with its invariants. It is not universal progress or a hidden-state
strategy claim. Known public IDs, legal caller arguments, private internal
bindings and generator outputs must remain distinct.

For a restricted equality-only fragment, fix non-renamable constants and finite
control. Rename opaque atoms consistently in registers, map keys/values,
messages, contract predicates and relevant histories. If transitions and goal/
invariant predicates commute with these renamings, states can be represented
by equality patterns and scope structure. A concrete safe path projects to a
quotient path; equivariance permits lifting each quotient step back to a
concrete path from the corresponding state. This is ordinary nominal/orbit or
data-independence reasoning, not a new theorem introduced by this project.
Orbit-finiteness, bounded support and executable lifting require their own
justification; finitely supported individual states do not automatically make
an unbounded map collection orbit-finite.

## Primary mechanisms already available

| Inspected primary source | Consequence for the proposed distinction |
| --- | --- |
| [Oxford data-independence research summary](https://www.cs.ox.ac.uk/activities/concurrency/research/dataindependence/) | Equality-only data manipulation, symbolic operational semantics, symmetry elimination and finite verification reductions are established. This summary is not a universal cutoff theorem for arbitrary bridge code. |
| [Register automata with fresh output](https://automata.cs.ru.nl/Syntax/RegisterFresh) | Guarded input/output names, register copying and fresh-value generation already model server-generated identifiers. Its simplified definition notes extensions to constants and multi-parameter actions. The wiki's bibliography entry mixes journal/conference labels; no publication status is inferred from that label. |
| [History-Register Automata](https://lmcs.episciences.org/1630), Grigore and Tzevelekos, LMCS2016 | Histories with storage, consumption and reset address unbounded allocated resources. The inspected journal summary establishes overlap; the full HRA construction was not read or implemented here. |
| [A Logic for Fresh Labelled Transition Systems](https://drops.dagstuhl.de/storage/00lipics/lipics-vol363-csl2026/html/LIPIcs.CSL.2026.23/LIPIcs.CSL.2026.23.html), Bandukara and Tzevelekos, CSL2026 | Inspected Sections1-2 and Section4 excerpts define nominal/orbit structure, distinguish global freshness, give a parity-game model-checking correspondence (Theorem30), and use bounded histories of N+1 names (Definition31) under fresh-orbit-finite assumptions. A generic fresh-name/history cutoff is therefore not an unoccupied technical step. No parity-game implementation or complexity advantage is reproduced. |

Four retained query/result pairs include the initial broad search, primary
opens, mechanism excerpts and definition finds. Search results about diagnosis/
repair remain discovery leads, not inspected primary support for another
candidate. All web records are JSON representations of tool-formatted excerpts,
not original remote source archives or complete papers.

## Actual pinned source constraints

The local bridge pins remain AmirK-S
`58eff9da469bccdc432bf164662727947de646b4` and mgcrea
`c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5`. Exact licensed snapshots and the
source index preserve these inspected boundaries:

- Amir's HandleTable generates a prefixed random token and retries while that
  token is a key in its current entries map. Expired but unswept entries are
  still in this map. Delete/sweep/expired-key replacement can remove entries.
  The implementation thus establishes uniqueness against stored entries when
  minting returns; it does not test the set of all historically emitted tokens.
  A fresh-register model imposing global non-repetition would need an additional
  explicit abstraction assumption. No historical collision was observed, forced,
  measured or classified as a natural bridge defect in this screen.
- Amir's task store keys identity by alias plus native task ID; its context
  table similarly keys alias plus context ID. Alias validation excludes the
  delimiter. Do not invent a delimiter collision or merge identities across
  agents. Table retention, touch, expiry and terminal freezing remain state
  predicates; renaming does not erase them or grant a lease over remote state.
- mgcrea constructs generated message/RPC IDs from prefix, clock and randomness.
  The caller-visible typed tool cannot choose these generated IDs. The task
  store validates native IDs using a character/length predicate and special
  exclusions, then uses them in filenames. Peer URLs are normalized as strings.
  A blanket equality-only abstraction of all these fields is not justified.
  Admissibility predicates, endpoint/namespace constants and filesystem effects
  need preserved interpretations or explicit unknown coverage.
- Removing a name from an internal table does not remove an old public handle
  from the caller's observation history or contract. Any safe forget/merge step
  must preserve the relevant binding distinctions. A recipe can refer only to
  known public names or values obtainable by actual permitted actions; renaming
  a hidden native ID does not reveal it to a caller.

These are source-scope findings, not a full abstraction proof of either bridge.
The finite horizon does not bound an arbitrary initial remote store, opaque
application state, background events or primitive execution time. Count profile
construction, source review, symbolic compilation, checking, certificate lifting
and updates for every comparator. Random generation is not a free, controllable
caller input, and retry termination/timing is not proved by token equivalence.

## Decision and next action

An optimized exact comparator can use the same equality-pattern/orbit
representation and preserve the same scope/history predicates. Symbolic and
cached baselines also receive this representation. Comparing it only against
enumerated UUID strings would manufacture a cost advantage. The primary
bounded-history result and actual source constraints rule out promoting a
generic identity canonicalizer/cutoff as the new C1 procedure.

Retain a source-faithful identity representation as a possible baseline
implementation technique. Do not implement or scale an efficiency trial without
an additional precise technical step and a prespecified advantage over the
strong symmetry-aware comparator. Current official-handler results are
unchanged; no new continuation domain or completed human review follows.
Stable manuscript foundation/evidence sections may be drafted while the missing
method and benchmark gates remain explicit. That drafting does not select a
systems-only contribution route or pass the paper-completion checkpoint.
