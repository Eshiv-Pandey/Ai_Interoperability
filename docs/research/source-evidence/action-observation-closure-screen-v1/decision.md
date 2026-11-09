# Source-derived action and observation closure: method screen v1

Prepared **25 October 2026**. **Verdict: no additional C1 technical step is
established; do not select this construction for a performance trial.** This
screen makes the proposed compiler precise, identifies stronger relevant
comparators and specifies the missing source-fidelity obligations. It is a
root-authored analytical review, not independent human review, a compiler
implementation or an application experiment. The original method objective,
may-completion target and registered title remain in force. CP2 remains open,
CP7 pending and verified checkpoint credit **5%**.

## Construction assessed

The proposed construction would compile a pinned bridge and handler into a
bounded model of what a caller can send, observe and subsequently construct.
Its inputs must include reviewed request serializers, transport defaults,
response projections, handler transitions, deployment/principal-specific public
surfaces, caller computation rules, initial public evidence, the original-task
goal, safety requirements and a fixed horizon. Evaluator-private task/token
values are excluded from practical inputs. A source excerpt is not a complete
deployment profile, and an arbitrary callback is not automatically a caller
action.

Two concrete versions were assessed:

```text
Field/recipe saturation:
    seed public values and accepted source rules
    repeatedly add fields/recipes producible by enabled operations
    test whether the goal's required input recipes are available

Correlated, bounded closure:
    accept coverage for the specified source/language/deployment fragment
    retain state, observations, bindings and path constraints per history
    compose each permitted caller operation with serializer and handler rules
    enumerate/model every allowed outcome, including failure and updates
    extend the caller's observation frame with the actual projected response
    preserve recipe evaluation and guards under that same frame/history
    solve the original bounded completion query
    optionally solve a separately labelled observation-policy query
    check certificates against the accepted model, or return unknown
```

The first version loses state correlations, control order, consumption, expiry
and principal binding unless those are represented. For an illustrative authored
case, suppose the only operation makes one irreversible choice, returning either
`a` or `b`, and completion requires both values. Pooling the two possible results
would invent availability that no execution attains. This is an analytical
counterexample, not a new domain, measured failure or executed test. Conditioning
every rule on its state/history removes the error but leads to the second
version: ordinary constrained symbolic execution and bounded planning/game
analysis. A monotone pool alone supplies neither safe-completion nor a complete
negative certificate.

Compiling source rules and retaining origins can improve engineering fidelity.
No additional representation, approximation or compiler algorithm with a proved
advantage over a correctly modeled symbolic comparator has been identified.
Source extraction itself must be counted in any future efficiency comparison.

## Precise overlap with primary methods

| Inspected primary source | Relevant established step | Boundary retained here |
| --- | --- | --- |
| [YAPA v1](https://arxiv.org/html/1005.0737v1), Sections 2.1, 3.1-3.2, 4.3-4.4 | Public recipes, frames, deduction, visible equations and finite saturated representations | Theorem 4.6 is conditional on reaching a saturated nonfailure state; arbitrary convergent rewriting does not ensure termination. This is static knowledge analysis, not original-task winning. |
| [DeepSec 2018 author PDF](https://members.loria.fr/IRakotonirina/files/public_html/publications/18-sp.pdf), Sections 2.3-2.5 | Recipe-labelled inputs, observation frames, failed destructors, equality tests and active trace equivalence/bisimilarity | Bounded sessions and the specified rewrite-system class; indistinguishability is a different property from safe task completion. The separate 2024 v2 abstract is metadata, not the inspected 2018 body. |
| [ProVerif project](https://bblanche.gitlabpages.inria.fr/proverif/) | Horn-clause symbolic protocol analysis and public/private term modeling | Project documentation/example inspected; no tool execution, comparative accuracy result or general exact strategy claim. |
| [Dauvier, Filiot and Reynier, CSL 2026](https://drops.dagstuhl.de/storage/00lipics/lipics-vol363-csl2026/html/LIPIcs.CSL.2026.8/LIPIcs.CSL.2026.8.html), Sections 1 and 6 | Reduction to finite-alphabet register-bounded synthesis with visible/hidden inputs; Theorem 31 and Corollary 32 | Fixed register bound, specified data domains and infinite-word objectives. Outputs use register contents; arbitrary fresh strings/JSON operations are not automatically covered. Do not transfer Section 5's prefix-domain result to partial observation without proof. |
| [RESTler paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2021/03/RESTler.pdf), Sections II-III, Figure 3 | Compiled request grammar, producer-consumer resource dependencies, observed-response reuse and stateful sequence exploration | Finite dictionaries and feedback pruning are testing mechanisms. Discarding non-2xx sequences or failing to sample a value does not prove our no-completion property. |
| [APIphany v2 abstract](https://arxiv.org/abs/2203.16697v2) | Semantic-type inference, semi-structured data wrangling, API-call composition and simulated execution | Abstract/metadata inspected only; full method and implementation were not audited or run. Broad first-API-recipe/compiler claims require this comparison. |

These overlap observations are analytical inferences from the cited passages;
they do not prove that any listed system already implements a complete MCP/A2A
compiler or that a new specialized procedure is impossible. Existing
[source-recipe](../../source-recipe-baseline-v0.md),
[acquisition](../../evidence-acquisition-review-v1.md) and
[identity](../identity-method-screen-v1/decision.md) screens remain applicable.
The strongest baseline receives the same source summaries, action alternatives,
public evidence and costs, including symbolic/backward/cached implementations.
Giving the candidate reviewed source while restricting the baseline to field
advertisements or enumerated UUID values would manufacture an advantage.

## Guessing and quantifiers must survive compilation

A missing output field does not imply an unavailable caller action. If an API
accepts arbitrary strings, the model must retain all legally constructible
strings, including guesses. Replacing a concrete UUID string with a private
symbol that no public recipe can name changes the action space unless an
explicit abstraction argument justifies that replacement for the exact query.
The symbolic security convention is an assumption, not a consequence of UUID
format. No probability distribution, entropy bound or unguessability result for
the screened application is established here.

Three predicates remain separate:

- Fixed-state may completion: a legal safe completing execution exists from a
  stated state within the original horizon.
- Evidence-relative may completion: such an execution exists from at least one
  state consistent with the public evidence.
- Caller guarantee: one policy based on public observation history completes
  safely for every compatible state and every permitted outcome within that
  horizon.

The last predicate is an auxiliary diagnostic, not a silent replacement of the
approved may target. For a purely illustrative equality-test interface with
`N` possible stable strings, at most `H` distinct guesses, no other revealing
action, harmless failures and completion on a match: `N > H` precludes a
worst-case guarantee. Along an all-failure history some string remains untested.
If `N <= H`, testing all values can guarantee completion. A lucky legal guess
can still produce a may-completing trace when `N > H`. If a success needs a later
operation, failures consume tokens, or observations expose partial information,
the simple bound no longer describes that interface. This is a standard counting
argument, unexecuted and unapplied to apcore or AgentOps.

Finite testing, nondeducibility and one pair of equal pending replies therefore
cannot establish whole-interface non-support. Static-equivalent initial frames
also do not prove identical interactive behavior. An exposing read, public token
derivation, safe testing policy, token-free approval or omitted raw route
falsifies a putative obstruction.

## Concrete source-fidelity boundary and next selection condition

[Closure obligations](closure-obligations.json) retain the actual apcore source
lead: token parsing/stripping and one pending text projection have inspected
pinned excerpts, while a substantive deployed handler, public-surface closure,
native effect and original-task continuation remain open. Object JSON text,
DataPart, raw alternatives and version compatibility cannot be erased.
AgentOps remains an [unqualified source lead](../agentops-screen-v1/decision.md);
its upstream same-task test was inspected, not executed, and its differing
unpinned views cannot be fused into one source revision. The blocked Git probe
is retained; this screen made no new acquisition attempt.

A future compiler candidate must name an actual extra transformation and show
which established comparator cannot obtain its correctness/coverage/cost result
on the same accepted fragment. Freeze fidelity assumptions, task-derived safety,
action costs, horizon and a meaningful advantage threshold before performance
measurement. A useful exact finite representation or sound two-sided
approximation needs a proof connecting concrete legal actions and observations
to its model; unexplored calls produce unknown. No such extra step or threshold
is selected in this screen, so scaling remains unjustified.

Eight query/result pairs are saved as formatted web-tool JSON, not original
downloaded source bytes. The attempted DeepSec v2 HTML URL returned 404.
Query 7's two intended RESTler finds were returned against the YAPA abstract by
the tool; they are retained as misresolved, non-supporting results. Query 8 uses
the full observed RESTler URL and supplies the relevant algorithm passages.
Other nonmatching finds remain retained without absence claims.

No compiler, solver, tests, archive replay, native/bridge requests, study-model
inference, installation, external messages, issues/PRs or human review occurred.
File-integrity audits are maintenance verification and earn no gate credit.

File-preparation note: an initial combined add/update patch was rejected at a
nonmatching context line before creating its new files. The corrected add-only
patch succeeded. A subsequent attempted relocation used incorrect context and
was also rejected; a direct file read then supported the exact correction. The
local failure receipt is retained separately.

