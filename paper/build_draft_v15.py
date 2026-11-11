"""Build the V1 development release manuscript from frozen evidence; stdlib only.

Reads original captures/analyses without importing or executing application, SDK,
provider, evaluator, solver or certificate checker code. V14 bytes are preserved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
V14 = ROOT / "paper/working-draft-v14.md"
GUIDE = ROOT / "docs/research/paper-artifact-guide-v15.md"
FROZEN = {
    "paper/working-draft-v14.md": "32d1064887e0b464ee73739430a0e5cb88fb7c4f0105ceb7b77f0e1bed38bc63",
    "paper/working-draft-v14.provenance.json": "3f691b52b33817f0bb0c7e97684cef4b840921d1c5cdf6e29d5c234d1135109f",
    "paper/working-draft-v14.audit.json": "",  # Identity is joined to its exact saved draft/provenance fields below.
}
NATIVE = "paper/original-native-provider-v2-appendix.provenance.json"
AUTONOMOUS = "paper/original-autonomous-workflow-shopper-appendix-v1.provenance.json"
WORKFLOW = "runs/agentops-workflow-reference-development/v2/retained-43055395848-1/extracted/analysis.json"
SHOPPER = "runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/analysis.json"
WORKFLOW_RESULTS = "docs/research/agentops-workflow-reference-results-v2.md"
WORKFLOW_REVIEW = "runs/agentops-workflow-reference-development/v2/root-raw-review-1/review.json"


def need(condition, label):
    if not condition:
        raise ValueError(label)


def parse(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value, "duplicate_JSON_key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_JSON")))


def read(path):
    return parse((ROOT / path).read_bytes())


def record(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    need(not path.is_symlink(), "symlink_input_refused")
    path = path.resolve()
    need(path.is_relative_to(ROOT) and path.is_file(), "regular_workspace_input_required")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def identity(row):
    return {key: row[key] for key in ("bytes", "sha256")}


def bind(rows, inputs):
    if isinstance(rows, dict):
        rows = [{"path": path, **value} for path, value in rows.items()]
    for row in rows:
        actual = record(row["path"])
        need(identity(actual) == identity(row), "changed_frozen_input:" + row["path"])
        need(row["path"] not in inputs or inputs[row["path"]] == actual, "conflicting_frozen_identity")
        inputs[row["path"]] = actual


def section(text, heading):
    need(text.count(heading + "\n") == 1, "unique_section_required:" + heading)
    start = text.index(heading + "\n")
    matches = list(re.finditer(r"^##(?:#)? .+$", text[start + len(heading):], re.MULTILINE))
    end = start + len(heading) + matches[0].start() if matches else len(text)
    return text[start:end]


def replace_once(text, before, after):
    need(text.count(before) == 1, "frozen_text_anchor_changed:" + before[:75])
    return text.replace(before, after, 1)


ABSTRACT = """## Abstract

Protocol compatibility does not guarantee that a caller retains the public
operations needed to finish an agent's task. We implement bounded task-relative
continuation admission with supported, unsupported and unknown decisions,
independently checked witnesses and complete finite-model obstruction
certificates. A shared-lifting adaptation reuses exact prefixes and complete
relation expansions while preserving correlated frames and witness history.
On 66 related authored development profiles at four method-specific logical
allowances, shared lifting supplies no certified coverage beyond goal-pruned
direct search. At allowance 256 it certifies 39/66 profiles versus 54/66 for
goal-pruned and constraint-pruned direct; at 100,000 all five methods agree on
28 supported, 26 unsupported and 12 unknown profiles. Reconvergence reduces
relation evaluations from 1,024 to 16 while charged work rises from 5,566 to
14,773 and the 8,895-byte proof remains unchanged. A separate 1,650-attempt
physical-cost allocation retains 330 attempts per method, including 60 unknowns.
Shared lifting has higher full-process median CPU, wall and RSS than goal-pruned
direct on all 54 eligible profiles with five dependent repeats. A lossless proof
codec restores 26 negative certificates, reducing aggregate wrappers from
15,128 to 11,918 bytes; direct wrappers total 7,760 bytes. These adverse
development results establish no algorithmic superiority or novelty.

Original-application fixtures separate checked admission from task completion,
attributed effects and observation completeness. Earlier offline AP2 payment
tools observe 3/13 demo purchases with admission alone and 10/13 with informed
public recovery; the earlier offline original ADK shopper observes 29/29
prefixes and zero purchases. Separately allocated original native AP2/Gemini
V2 records two completed public Tasks with demo Success receipts among five
scripted cases; a fifth case stops at an owned request-byte boundary. Its
adaptive V3 follow-up fails on upstream HTTP 503 before the repeat, retaining
839 known tokens and one response with unmeasured usage. Original AgentOps
Workflow V2 reaches all four stages on two cases with nine delivered tool
terminals, but both final recommendations are insufficient with null targets.
Original autonomous native shopper V1-V3 retain generation timeout, runtime
preflight and owned metadata-wiring failures. Every allocation remains
separate. The artifact supplies implemented methods, reproduced finite results
and bounded original-source observations; independently reviewed gold,
untouched holdout, full native/task qualification and generalized live-model
utility remain open.

"""


def application_sections(native, workflow):
    rows = ["| Scripted native profile / run | Declared cases | Upstream allocations | HTTP 200 / 503 | Request bytes | Known reported tokens | Responses missing usage | Owned refusals |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in native["runs"]:
        statuses = row["HTTP_status_counts"]
        rows.append(f"| {row['version'].upper()} / {row['run_id']} | {row['parent_attempts']} | {row['upstream_allocations']} | {statuses.get('200', 0)} / {statuses.get('503', 0)} | {row['request_bytes']:,} | {row['known_reported_tokens']:,} | {row['responses_without_usage']} | {row['owned_local_refusals']} |")
    cases = workflow["cases"]
    calls = " / ".join(str(row["model_calls"]) for row in cases)
    events = " / ".join(str(row["raw_official_events"]) for row in cases)
    terminals = " / ".join(str(row["raw_official_tool_terminal_count"]) for row in cases)
    return """### 8.13. Separately allocated original native AP2 and Gemini profiles

The [three-run native/provider appendix](original-native-provider-v2-appendix.md)
and its [provenance](original-native-provider-v2-appendix.provenance.json) bind
actual original native services, SDK generation, provider captures and public
Task observations. All calls request `gemini-3.1-flash-lite-preview`; successful
responses report `gemini-3.1-flash-lite`. No provider revision or billing-tier
identity follows. These use an owned accounting proxy, scripted public caller
and owned Task reader; they are distinct from the original autonomous shopper.

**Table V15N. Every separately allocated scripted-native provider profile.**

""" + "\n".join(rows) + """

V1's five declared cases retain failed parent attempts before business or public
Task capture. Its one allocation is access smoke only. The first caller fails
an owned callable binder; four later launch failures lack retained errno.

V2 retains five cases. Correct reply and foreign-context recovery each reach
one completed public Task and one corresponding demo Success receipt. Wrong
reply remains input-required with the original incorrect-challenge response;
no reply remains waiting without OTP submission. The fifth case's prerequisite
payment stops when the owned cumulative request-byte boundary refuses a later
call, before any repeated continuation. The all-200 upstream ledger supplies no
observed upstream quota failure. The two receipt cases are not a human-gold
pass rate, real settlement or a hidden-effect idempotence result.

V3 is one adaptive development follow-up selected after V2. Original catalog
generation receives upstream HTTP 503 UNAVAILABLE, and no payment Task read,
receipt or repeat is reached. Its 839 known tokens cover only two successful
responses; failed-response usage remains unknown. A successful-response usage
counter of zero unknowns does not make failed-response usage zero. All four
recorded children are reaped. Workflow success means retained evidence, not a
successful application task.

No run replaces another denominator. Native entrypoints and actual provider
requests do not establish unchanged `run.sh` provisioning, independent bridge
qualification, autonomous shopper utility, human gold or untouched holdout.
The 100,000 observed-token threshold stops after responses and is not a hard
token or cost ceiling. Exact raw reconstruction and separate semantic/raw
reviews remain in the appendix provenance.

### 8.14. Original AgentOps Workflow: delivered evidence and failed task handoffs

The [original-autonomous appendix](original-autonomous-workflow-shopper-appendix-v1.md)
preserves two separate two-case Workflow allocations. V1 leaves the executing
SDK-cloned models unbound after changing exported models, recording zero
fixture callbacks and tool calls, four MODEL_UNAVAILABLE events and twelve
denied loopback connects per case. V2 preserves original models and supplies
an owned deterministic, public-only before-model fixture after the unchanged
policy. It executes the original direct ADK Workflow; original A2A rejects
Workflow roots, so this is not an A2A result or a model-quality trial.

**Table V15W. Original Workflow V2, denominator two cases.**

| Observation | Case 1 / Case 2 |
| --- | --- |
""" + f"| Fixture callbacks | {calls} |\n| Raw official events | {events} |\n| Delivered raw tool terminals | {terminals} |\n" + """| Optional after-tool observer callbacks | 0 / 0 |
| Denied socket operations | 0 / 0 |
| Original stage entries and exits | All four / all four |
| Final recommendation | Insufficient with null target / insufficient with null target |
| Frozen analysis questions | 3 / 3 |

The original policy short-circuits optional after-tool observers, while the
nine corresponding function-response terminals remain in raw SDK delivery.
The frozen analyzer keeps all six questions about target/read correspondence
and executing-node object identity. The pinned SDK deliberately clones agents
again through DynamicNodeScheduler/replay, so exported or compiled node object
identity alone is not a faithful execution signature. That source diagnosis
does not erase the frozen questions or supply absent expanded witnesses.

The [actual V2 results and source diagnosis](../docs/research/agentops-workflow-reference-results-v2.md)
show a separate handoff failure: the original PII filter replaces `n1`/`n2`
spans within escaped multiline runbook text, creating an invalid backslash
before the `<US_DRIVER_LICENSE>` replacement. Both governed evidence-review
inputs fail JSON decoding, at character offsets 2140 and 2737. Thus a
delivered tool result and completed stage sequence do not establish usable
evidence or a correct selected target. A later compact scalar handoff is a
prospective correction and supplies no result here. The underlying original
policy and every failed V1/V2 observation remain preserved.

### 8.15. Original autonomous native shopper: separate unsuccessful allocations

The [native-shopper appendix](original-autonomous-workflow-shopper-appendix-v1.md)
and [V3 results](../docs/research/ap2-native-shopper-provider-development-results-v3.md)
preserve one declared case per allocation. These execute the original shopper
root only when its startup prerequisites pass; none reaches a purchase.

**Table V15S. One case in each original-native-shopper profile.**

| Profile / run | Upstream allocations | Known tokens | Unmeasured allocations | Reached shopper observation |
| --- | ---: | ---: | ---: | --- |
| V1 / 43038234376 | 2 | 45 | 1 | Original root instantiated; generation transport wait times out |
| V2 / 43045731741 | 0 | 0 | 0 | Runtime preflight fails; task unexecuted |
| V3 / 43055390208 | 1 | 45 | 0 | Owned case metadata rejected before original ADK startup |

V1's known 45 tokens come from access smoke. Its shopper generation times out
at the owned 45-second transport wait and has unknown usage. Six ADK error
events, zero business calls, no visible messages and no receipts remain
retained; four later local refusals consume no new upstream allocation.

V2's owned runner incorrectly resolves the virtual-environment Python link,
potentially selecting the global interpreter. All 182 required versions match
the retained pip report, which does not substitute for an absent mismatch
census of the actual selected interpreter. This preflight failure remains an
unexecuted task with zero provider/application calls.

V3 preserves the virtual-environment launcher and passes runtime preflight and
access smoke. Three original services supply readiness cards, but the owned
worker rejects the supplied facts before importing original ADK/SDK code. Its
whole-dictionary guard expects the V1 case identifier while the runner passes
the V3 identifier; all other public human facts match. The
[source diagnosis](../runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/source-diagnosis.json)
joins exact frozen worker facts, supplied input, stdout and runtime records.
The sole V3 allocation is 45-token smoke, with zero shopper model requests,
ADK events or receipts. All four recorded children are reaped, with zero active
handlers and unclosed allocations at capture freeze.

An improved wait option is not evaluated when no shopper generation starts.
Any later metadata correction must be a new allocation. These failures do not
erase V1's unknown usage or evaluate actor rendering, whole-task live utility,
original `run.sh` provisioning, hidden effects, settlement or human gold.

"""


CLAIMS = [
    ("SEMANTICS", "## 3. Task-relative continuation semantics", "Bounded existential completion has three-valued decisions; complete finite evidence is required for a negative, with deployment assumptions retained.", ["src/interoperability/refinement.py", "src/interoperability/refinement_oracle.py"], "Conditional finite-model specification; no complete real-route negative."),
    ("ALGORITHMS", "## 4. Admission algorithms and certificates", "Shared lifting caches exact prefixes and complete relation expansions while preserving correlated frames, uncertainty and witness history; independent checks remain separate.", ["src/interoperability/refinement_shared_lift_v2.py", "src/interoperability/refinement_oracle.py"], "Implemented bounded adaptation, not a new general CEGAR or memoization principle."),
    ("PROPERTIES", "## 5. Properties under explicit assumptions", "Soundness and finite-completeness arguments are conditional on faithful recipes, complete evidence, stable bindings and adequate bounds.", ["src/interoperability/refinement.py", "src/interoperability/refinement_oracle.py", "docs/research/method-contribution-assessment-v2.json"], "Mathematical argument with assumptions; no formal machine proof or universal deployment assurance."),
    ("DESIGN", "## 6. Experimental design", "The authored development design uses 66 related profiles, four original methods/four allowances and a separately allocated fifth comparator.", ["paper/draft-audit-v6-5.json", "docs/research/paper-artifact-guide-v7.md"], "Related authored development variants; not independent held-out tasks."),
    ("COVERAGE", "### 7.1. Certified coverage", "At 256 shared lifting certifies 39/66 versus 54/66 for goal/constraint-pruned direct; at 100000 all methods agree on 28 supported, 26 unsupported and 12 unknown.", ["paper/draft-audit-v6-5.json", "docs/research/paper-artifact-guide-v7.md"], "All 66 remain denominator; no general superiority or population inference."),
    ("STRESS", "### 7.2. Work and proof representation", "Reconvergence cuts relation evaluations from 1024 to 16, while work rises from 5566 to 14773 and an 8895-byte proof remains unchanged.", ["paper/draft-audit-v6-5.json", "src/interoperability/refinement_shared_lift_v2.py"], "Method-specific charged work and retained proof representation, not equal hardware cost."),
    ("REPRODUCTION", "### 7.3. Timing and cross-platform reproduction", "Linux reproduces 1056 deterministic algorithm comparisons, 2003 worker successes and 167 tests; the fifth-method supplement preserves its separate audit.", ["paper/draft-audit-v6-5.json", "docs/research/paper-artifact-guide-v7.md"], "Software reproduction on authored finite profiles; no independent application/population study."),
    ("ABSTRACT_CONTROL", "### 7.4. Supplementary abstraction-only control", "The inner graph's 64 supported/two unsupported decisions differ from full-recipe decisions on the 66 exact pairs.", ["paper/draft-audit-v6-5.json"], "Deliberately restricted graph control, not qualified public task continuation."),
    ("CACHE_ABLATION", "### 7.5. Separately allocated cache-component ablations", "The separate 1584-cell ablation adds no certified cases beyond goal-pruned direct.", ["runs/shared-cache-ablation/read-review-42879031721-1/result.json", "paper/draft-audit-v7-1.json"], "Same related development corpus; no held-out application efficacy."),
    ("PROOF_CODEC", "### 7.6. Lossless refutation-prefix proof packaging", "All 26 negative proofs restore exactly; aggregate wrappers are 15128/11918/7760 bytes for original/codec/direct; two shrink and 24 grow; 31 constructed controls reproduce.", ["docs/research/refutation-prefix-dag-comparison-v2.json", "paper/refutation-prefix-dag-appendix-v2.audit.json", "runs/ci-refutation-prefix-dag-v2/retained-42910442359-1/extracted/result.json"], "Representation artifact only; no new solver/checker-speed/coverage/utility/novelty result."),
    ("AGENTOPS_EFFECT", "### 8.1. Deterministic AgentOps confirmation fixture", "Native and admitted bridge routes complete original confirmation tasks with one attributed expected effect and clean lifecycle observations.", ["docs/research/paper-artifact-guide-v7.md", "paper/draft-audit-v6-5.json"], "Deterministic original confirmation fixture; original refinement, not an application run of shared lifting."),
    ("EFFECT_BOUNDARY", "### 8.2. What the integration establishes", "Conditional model-relative admission, public task completion and attributed effects are separately checked.", ["src/interoperability/refinement.py", "paper/draft-audit-v6-5.json"], "No general protocol composition or complete action-space closure."),
    ("AP2_SEQUENCE", "### 8.3. Original AP2 development sequence and corpus boundary", "Intervened original merchant/processor tasks resume to corresponding demo Success receipts.", ["docs/research/paper-artifact-guide-v7.md", "paper/draft-audit-v6-5.json"], "Offline model and ASGI interventions; demo receipts are not settlement."),
    ("AP2_SOURCE", "### 8.4. Executed AP2 source-boundary checks", "Original source boundaries and public continuation constraints were checked within the declared development fixture.", ["docs/research/paper-artifact-guide-v7.md", "paper/draft-audit-v6-5.json"], "Source-relative restricted checks; no full native launcher qualification."),
    ("AP2_SHARED", "### 8.5. Shared-lifting admission before the original AP2 continuation", "The shared-lifting continuation certificate is checked before its actual send and a corresponding demo receipt is separately observed.", ["docs/research/paper-artifact-guide-v7.md", "paper/draft-audit-v6-5.json"], "Bounded intervened development continuation; no generalized utility or hidden effects."),
    ("AP2_PAYMENT_BANK", "### 8.6. Original payment tools: paired development outcomes", "The 65-cell/13-per-arm payment-tool bank observes 3/13 purchases with admission alone and 10/13 with informed recovery; all 36 purchase observations and five later duplicate-call errors remain.", ["runs/ap2-reference-development/v5/retained-42881390576-2/extracted/independent-evaluation/result.json", "paper/draft-audit-v7-1.json"], "Offline original payment-tool development bank; no human gold, strict unconditional success or live-model generalization."),
    ("AGENTOPS_BANK", "### 8.7. Original governed-App candidate references", "A 34-candidate source-bound census preserves complete/partial recipes, unsupported cases and failed checks.", ["runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted/evaluation.json", "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/independent-raw-state-census-v1.json"], "Source feasibility, not complete original autonomous Workflow outcome."),
    ("OFFLINE_SHOPPER", "### 8.8. Original ADK shopper feasibility and remaining branches", "Earlier offline original ADK shopper observes 29/29 prefixes and zero purchases, preserving the missing-challenge boundary.", ["runs/ap2-original-shopper-development/v7/retained-42886479185-1/extracted/independent-bank-evaluation/result.json", "paper/draft-audit-v7-1.json"], "Historical offline profile; does not claim native provider shopper utility."),
    ("OWNED_TCP", "### 8.9. Original payment tools over owned TCP and legal bridge initiation", "The historical owned-TCP/bridge allocation retains every declared arm/status and distinguishes transport from task outcome.", ["runs/ap2-native-bridge-development/v8/retained-42897325489-1/extracted/independent-evaluation/result.json", "runs/ap2-native-bridge-development/v9/retained-42902256098-1/extracted/independent-evaluation/result.json", "runs/ap2-native-bridge-development/v10/retained-42905259371-1/extracted/independent-evaluation/result.json", "paper/working-draft-v11.audit.json"], "Owned TCP serving, not unchanged original launcher, provider or whole-task qualification."),
    ("NATIVE_FAILURE_HISTORY", "### 8.10. Preserved native bootstrap failures and interpretation limits", "V8-V12 retain smoke/stage/bootstrap/preallocation failures; V11 has 104 missing matrix observations and 65 non-evaluable native transport pairs; V12 has no actual matrix census.", ["docs/research/ap2-v8-actual-smoke-failure-peer-audit-v1.json", "docs/research/ap2-v9-actual-stage-failure-peer-audit-v1.json", "runs/ap2-native-bridge-development/v12/preallocation-failure-42915964952-1/result.json", "paper/working-draft-v11.audit.json"], "Failure records supply no missing task or transport success; historical bytes unchanged."),
    ("NATIVE_V13", "### 8.11. Separately retained V13 native and bridge development allocation", "V13 verifies 65/65 native payment-tool captures and 39/39 legal bridge initiation captures while retaining adverse outcomes.", ["runs/ap2-native-bridge-development/v13/analysis-42918421487-1/result.json", "paper/working-draft-v13.audit.json"], "Actual separately retained development allocation; native capture/bridge initiation is not full task or provider utility."),
    ("COMMON_COST", "### 8.12. Actual common end-to-end physical-cost development comparison", "All 1650 attempts retain costs; each method has 270 certified and 60 unknown results. Ten paired cohorts contain 54 profiles/five dependent repeats; shared lifting is higher in CPU/wall/RSS on all eligible profiles.", ["runs/common-cost-development/v1/read-audit-42927208534-3/result.json", "paper/working-draft-v14.audit.json", "docs/research/common-cost-results-v1.md"], "Descriptive full-process costs on one authored development cohort; no independent timing-task denominator, superiority or uncertainty interval."),
    ("NATIVE_PROVIDER", "### 8.13. Separately allocated original native AP2 and Gemini profiles", "V1/V2/V3 separately retain 5/5/1 declared cases, 1/60/3 provider allocations and 45/44940/839 known tokens. V2 has two completed public Task/Success cases; V3 fails upstream503 before repeat and has one unmeasured response.", [NATIVE, "runs/ap2-original-native-provider-development/v2/independent-semantic-analysis-v1/analysis.json", "runs/ap2-original-native-provider-development/v3/independent-raw-review-v1.json"], "Original native modules/SDK with owned proxy/scripted caller/reader; no pooled efficacy, autonomous shopper, settlement, human gold or holdout."),
    ("WORKFLOW_V2", "### 8.14. Original AgentOps Workflow: delivered evidence and failed task handoffs", "Two original direct-ADK Workflow V2 cases retain 9/8 fixture callbacks,14/12 raw events,5/4 tool terminals and six frozen questions; both final recommendations are insufficient with null targets. Governed review JSON fails at offsets 2140/2737.", [AUTONOMOUS, WORKFLOW, WORKFLOW_RESULTS, WORKFLOW_REVIEW, "scripts/review_agentops_workflow_capture_v2.py"], "Deterministic before-model fixture, unchanged PII policy, direct ADK. Raw delivery differs from optional observers; no A2A route, model quality or task success."),
    ("SHOPPER_V3", "### 8.15. Original autonomous native shopper: separate unsuccessful allocations", "Native shopper V1/V2/V3 have one declared case each and remain timeout/unexecuted-preflight/owned-metadata failures, with 2/0/1 allocations and 45/0/45 known smoke tokens. V1 usage of one allocation is unknown; V3 has no shopper request/event/receipt.", [AUTONOMOUS, SHOPPER, "runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/source-diagnosis.json", "docs/research/ap2-native-shopper-provider-development-results-v3.md"], "Each allocation and failure kept separate; no successful native autonomous shopping or evaluated wait/actor-rendering improvement."),
    ("DISCUSSION", "## 9. Discussion", "The observed reuse/proof-unit separation explains the concrete adverse implementation result without claiming a general impossibility theorem or distinct new method.", ["docs/research/method-contribution-assessment-v2.json", "docs/research/method-contribution-code-peer-v1.json", "paper/working-draft-v14.audit.json"], "Author interpretation of bounded evidence; novelty and broader significance require human judgment."),
    ("LIMITATIONS", "## 10. Threats to validity and limitations", "Related development dependence, restricted model fidelity, unequal logical accounting and absent human/holdout/native-task qualification limit scientific generalization.", ["docs/research/method-contribution-assessment-v2.json", "paper/references-v3.json", "paper/working-draft-v14.provenance.json"], "No independent human scientific review or publication approval is inferred; literature retrieval is inherited V14."),
    ("REPRODUCIBILITY", "## 11. Reproducibility and artifact availability", "Current bytes, versioned raw evidence, inherited numerical audits and separate native/provider captures are mapped for read-only checking.", ["docs/research/paper-artifact-guide-v15.md", "paper/working-draft-v14.audit.json", NATIVE, AUTONOMOUS], "Byte consistency is not capture authenticity; no provider or certificate-semantic execution by this build/audit."),
    ("CONCLUSION", "## 12. Conclusion", "The released artifact is an implemented benchmark with finite reproduced adverse results and bounded original-source observations, retaining open novelty, held-out two-domain utility and general live-model interoperability.", ["paper/working-draft-v14.audit.json", NATIVE, AUTONOMOUS, WORKFLOW_RESULTS], "V1 development-release completion is separate from the original scientific-study completion and publication readiness."),
]


def local_links(body):
    paths = []
    for target in re.findall(r"\]\(([^)]+)\)", body):
        target = target.strip("<>")
        parsed = urlparse(target)
        if parsed.scheme or target.startswith("#"):
            continue
        # The current ledger is generated after the manuscript and binds it;
        # including that ledger as its own evidence would create a hash cycle.
        if target == "claim-ledger-v15.json":
            continue
        path = (ROOT / "paper" / unquote(parsed.path)).resolve()
        need(path.is_relative_to(ROOT) and path.exists(), "missing_claim_section_link:" + target)
        if path.is_file():
            paths.append(path.relative_to(ROOT).as_posix())
    return sorted(set(paths))


def build():
    inputs = {}
    for path, sha in FROZEN.items():
        row = record(path)
        need(not sha or row["sha256"] == sha, "changed_frozen_V14:" + path)
        inputs[path] = row
    prior = read("paper/working-draft-v14.provenance.json")
    audit = read("paper/working-draft-v14.audit.json")
    need(audit["checks_passed"] == 20 and all(item["passed"] for item in audit["checks"])
         and audit["draft_identity"] == inputs["paper/working-draft-v14.md"]
         and audit["provenance_identity"] == inputs["paper/working-draft-v14.provenance.json"]
         and prior["paper_sha256"] == inputs["paper/working-draft-v14.md"]["sha256"],
         "saved_passing_V14_audit_join_required")
    bind(prior["inputs"], inputs)
    native, autonomous = read(NATIVE), read(AUTONOMOUS)
    for value, path, manuscript, identity_key in (
        (native, NATIVE, "paper/original-native-provider-v2-appendix.md", "paper_identity"),
        (autonomous, AUTONOMOUS, "paper/original-autonomous-workflow-shopper-appendix-v1.md", "appendix")):
        inputs[path] = record(path)
        need(identity(record(manuscript)) == value[identity_key], "changed_actual_result_appendix")
        inputs[manuscript] = record(manuscript)
        bind(value["inputs"], inputs)
    expected = [(42982595287, 5, 1, 45, 0), (42995902326, 5, 60, 44940, 0), (43014447502, 1, 3, 839, 1)]
    need([(row["run_id"], row["parent_attempts"], row["upstream_allocations"], row["known_reported_tokens"], row["responses_without_usage"]) for row in native["runs"]] == expected,
         "three_separate_actual_native_profile_counts_changed")
    workflow = read(WORKFLOW)
    need(workflow["case_denominator"] == 2 and len(workflow["cases"]) == 2
         and [(row["model_calls"], row["raw_official_events"], row["raw_official_tool_terminal_count"], len(row["questions"])) for row in workflow["cases"]] == [(9, 14, 5, 3), (8, 12, 4, 3)],
         "frozen_workflow_V2_census_changed")
    need((ROOT / WORKFLOW_RESULTS).is_file(), "actual_workflow_result_diagnosis_required")
    diagnosis_text = (ROOT / WORKFLOW_RESULTS).read_text(encoding="utf-8")
    need("2140" in diagnosis_text and "2737" in diagnosis_text and "US_DRIVER_LICENSE" in diagnosis_text,
         "actual_PII_invalid_escape_diagnosis_required")
    shopper = read(SHOPPER)
    need(shopper["case_denominator"] == 1 and not shopper["consistency_questions"]
         and shopper["all_recorded_children_reaped"] is True, "actual_shopper_V3_join_changed")
    review = read(WORKFLOW_REVIEW)
    need(review["case_denominator"] == 2 and review["same_byte_analysis_reproduced"] is True
         and review["frozen_analysis_questions"] == 6
         and [row["malformed_governed_review_input"]["position"] for row in review["cases"]] == [2140, 2737]
         and review["analysis_identity"] == identity(record(WORKFLOW)), "actual_workflow_raw_review_join_changed")
    for path in (WORKFLOW, SHOPPER, WORKFLOW_RESULTS, WORKFLOW_REVIEW,
                 "runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/source-diagnosis.json",
                 "docs/research/ap2-native-shopper-provider-development-results-v1.md",
                 "docs/research/ap2-native-shopper-provider-development-results-v2.md",
                 "docs/research/ap2-native-shopper-provider-development-results-v3.md"):
        inputs[path] = record(path)
    historical = V14.read_text(encoding="utf-8")
    title = historical.splitlines()[0]
    preamble_end = historical.index("## Abstract")
    text = title + "\n\n" + """Research manuscript, version 15, 11 November 2026. This is the paper package
for the V1 development release due 12 November 2026 at 06:00 IST. The audited
V14 technical/numerical evidence, historical V11-V13 failures and original
registered title and study scope remain preserved. Separately scoped native
AP2/provider and original autonomous Workflow/shopper profiles are added with
their actual failures, missing observations and interventions. Release
completion does not establish completion of the original 96-task, 288-path-cell
and 96-crossing research study or publication readiness. All empirical claims
are finite-model or declared development-profile observations; independently
reviewed gold, untouched holdout and held-out live-model utility remain
unestablished.

""" + historical[preamble_end:]
    text = replace_once(text, section(text, "## Abstract"), ABSTRACT)
    text = replace_once(text, "and an original-application confirmation fixture in\nwhich a conditional admitted continuation is followed by the required task\ncompletion and effect.", "and separately scoped original-application fixtures that distinguish\nconditional admitted continuations, public task completion, attributed effects\nand missing observations.")
    text = text.replace("paper-artifact-guide-v14.md", "paper-artifact-guide-v15.md")
    text = replace_once(text, "## 9. Discussion", application_sections(native, workflow) + "## 9. Discussion")
    text = replace_once(text, "independent human domain review, genuine provider execution or evidence of a\ndistinct contribution.", "independent human domain review, complete route/source-to-model qualification,\nindependently validated live-task utility or evidence of a distinct contribution.")
    text = replace_once(text, "Twenty-two identities were refreshed against primary\nsources for this version,", "Twenty-two identities were refreshed against primary\nsources for the inherited V14 literature assessment,")
    text = replace_once(text, "mixed-model behavior and live conversational utility remain unqualified.", "mixed-model behavior and held-out live conversational utility remain unqualified.\nSubsequent original native/provider profiles establish their specifically\nretained requests and public observations, while original autonomous shopper\nfailures and deterministic Workflow handoff failures remain separate. Their\nowned proxy, reader, actor and fixture interventions limit transfer to other\ndeployments; actual provider usage alone does not establish semantic utility.")
    text = replace_once(text, "Its claim ledger binds this manuscript\nto those artifacts.", "The current [V15 claim ledger](claim-ledger-v15.json) binds this manuscript\nto those artifacts; older ledgers bind only their historical manuscripts.")
    text = replace_once(text, "The finite matrices and Linux reproduction made no application or live\nmodel calls. AgentOps and AP2 development integrations made no live model calls. The\nanalysis recomputes retained measurements without executing solvers. A later\napplication or provider experiment must be prospectively scoped and separately\nreported rather than silently extending this paper's completed evidence.", "The finite matrices and Linux reproduction made no application or live\nmodel calls. Earlier offline AgentOps/AP2 integrations also made no live model\ncalls. The separately allocated original native AP2/Gemini profiles retain\nactual provider requests and original SDK generation with their declared\nscripted caller, proxy and accounting interventions. The autonomous native\nshopper allocations and original direct-ADK Workflow fixtures retain their\nseparate startup/generation/handoff failures. This paper build and read audit\nrecompute retained evidence without executing an application, SDK, provider,\nevaluator, solver or certificate checker. Later allocations remain separate\nand cannot silently extend a historical denominator.")
    text = replace_once(text, "research results at their stated scope. Algorithmic novelty, held-out\ntwo-domain utility and live-model interoperability remain open scientific\nclaims.", "research results at their stated scope. Separately retained original native\nAP2/Gemini observations add two scripted completed public Tasks with demo\nSuccess receipts, while an upstream503 follow-up, original autonomous shopper\nfailures and insufficient original Workflow recommendations retain the limits\nof task transfer. The V1 development release has a complete paper/artifact\npackage for these bounded results. Algorithmic novelty, human-validated gold,\nheld-out two-domain utility, the full registered study and generalized\nlive-model interoperability remain open scientific claims.")
    unchanged_start = "## 2. Related work and comparator requirements"
    need(text[text.index(unchanged_start):text.index("### 8.13.")] == historical[historical.index(unchanged_start):historical.index("## 9. Discussion")],
         "inherited_V14_technical_and_result_sections_must_remain_identical")
    inputs[record(GUIDE)["path"]] = record(GUIDE)
    inputs[record(__file__)["path"]] = record(__file__)
    claims = []
    for claim_id, heading, statement, primary, scope in CLAIMS:
        body = section(text, heading)
        evidence = sorted(set(primary + local_links(body) + ["paper/working-draft-v14.audit.json"]))
        for path in evidence:
            inputs[path] = record(path)
        start = text[:text.index(heading + "\n")].count("\n") + 1
        claims.append({"id": claim_id, "statement": statement, "status": "established_at_stated_scope",
                       "manuscript_location": {"heading": heading, "line_start": start,
                                               "line_end": start + body.count("\n") - 1},
                       "source_artifact_paths": evidence, "scope_and_limitations": scope,
                       "validation": {"inherited_numerical_audit": "paper/working-draft-v14.audit.json",
                                      "current_read_audit": "paper/working-draft-v15.audit.json",
                                      "new_semantic_or_application_execution_by_build": False,
                                      "independent_human_scientific_review": False}})
    text_identity = {"path": "paper/working-draft-v15.md", "bytes": len(text.encode()),
                     "sha256": hashlib.sha256(text.encode()).hexdigest()}
    ledger = {"schema_version": "working-paper-claim-ledger/15", "draft": text_identity,
              "builder": record(__file__), "artifact_guide": record(GUIDE), "claims": claims,
              "evidence": [inputs[path] for path in sorted({path for claim in claims for path in claim["source_artifact_paths"]})],
              "inherited_numerical_evidence": {"draft": inputs["paper/working-draft-v14.md"],
                                               "provenance": inputs["paper/working-draft-v14.provenance.json"],
                                               "audit": inputs["paper/working-draft-v14.audit.json"],
                                               "saved_checks_passed": 20,
                                               "technical_and_numerical_sections_unchanged": True,
                                               "new_V15_numerical_runtime_execution": False},
              "open_claims": [
                  {"id": "NOVELTY", "status": "unestablished", "reason": "No distinctive general method or accountable human novelty decision."},
                  {"id": "HUMAN_GOLD", "status": "unqualified", "reason": "Independent human domain/task/gold review is incomplete; AI read audits do not replace it."},
                  {"id": "HOLDOUT", "status": "unexecuted", "reason": "Related authored development profiles are not untouched held-out tasks or near misses."},
                  {"id": "FULL_REGISTERED_STUDY", "status": "incomplete", "tasks": 96, "path_cells": 288, "additional_crossings": 96, "original_scope_revised": False},
                  {"id": "LIVE_TASK_UTILITY", "status": "unqualified", "reason": "Specific provider/Task observations do not prove autonomous two-domain, bridge or generalized live-model utility."},
                  {"id": "PUBLICATION_READY", "status": "not_claimed", "reason": "Accountable scientific/reference review and eventual submission approval remain open."}],
              "human_scientific_review_claimed": False, "full_original_study_complete": False,
              "publication_ready": False, "new_application_sdk_provider_solver_checker_or_evaluator_executions": 0}
    provenance = {"schema_version": "paper-v15-evidence-bound-build/1",
                  "built_utc": datetime.now(timezone.utc).isoformat(), "registered_title": title[2:],
                  "paper_identity": text_identity, "inputs": list(inputs.values()),
                  "inherited_v14": {path: inputs[path] for path in FROZEN},
                  "inherited_technical_numerical_sections_unchanged": True,
                  "native_scripted_profiles": native["runs"], "autonomous_profiles": autonomous["profiles"],
                  "workflow_case_denominator": 2, "workflow_cases": [{key: row[key] for key in ("case_id", "model_calls", "raw_official_events", "raw_official_tool_terminal_count", "questions")} for row in workflow["cases"]],
                  "original_study_tasks": 96, "original_study_path_cells": 288,
                  "original_study_additional_crossings": 96, "original_full_scope_revised": False,
                  "full_original_study_complete": False, "publication_ready": False,
                  "human_scientific_review": False,
                  "release_scope": "V1 development release paper package; original full research study remains open",
                  "new_application_sdk_provider_solver_checker_or_evaluator_executions": 0}
    return text, provenance, ledger


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    output, provenance_path, ledger_path = [path.resolve() for path in (args.output, args.provenance, args.ledger)]
    need([output, provenance_path, ledger_path] == [ROOT / name for name in ("paper/working-draft-v15.md", "paper/working-draft-v15.provenance.json", "paper/claim-ledger-v15.json")]
         and all(not path.exists() for path in (output, provenance_path, ledger_path)), "fresh_owned_V15_outputs_required")
    text, provenance, ledger = build()
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    write_json(ledger_path, ledger)
    provenance["claim_ledger_identity"] = record(ledger_path)
    write_json(provenance_path, provenance)
    print(json.dumps({"status": "V1_development_release_manuscript_built", "paper": record(output),
                      "claims": len(ledger["claims"]), "bound_inputs": len(provenance["inputs"]),
                      "new_runtime_or_provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
