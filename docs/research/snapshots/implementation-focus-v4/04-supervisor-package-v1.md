# Supervisor package: 31 October 2026

Prepared 28 October for an eight-minute review. Working completion target:
1 November, assuming the week ends Sunday. The [deadline plan](deadline-plan-v3.md)
preserves the full study. This package makes completed development work
inspectable; the manuscript, contribution and evaluation remain incomplete.

## Open and present

1. Open [the eight-slide presentation](../../demo/supervisor-v1/presentation.html)
   in a current browser. Arrow keys navigate; the notes and fullscreen buttons
   support presenting. This is portable HTML, not a PowerPoint file.
2. Open [the archived case replay](../../demo/supervisor-v1/index.html).
   Its default B6/B7 comparison distinguishes public recovery, task completion,
   domain effect, evidence completeness and strict result. Select N11 to compare
   a strict native positive control. Expand the captured requests and headers.
3. Use [the supervisor brief](../../paper/supervisor-brief-v2.md) for the spoken
   explanation and record actual feedback against the reviewed versions.
4. Supply [working draft v3](../../paper/working-draft-v3.md), its
   [claim ledger](../../paper/claim-ledger-v3.json) and
   [remaining requirements](../../paper/draft-status-v3.json) for detailed review.

Copy the entire `demo/supervisor-v1` folder to preserve its local evidence links.
The replay and slides need JavaScript, but no server, installation, network,
application execution or model call. Replaying captured bytes is distinct from
reproducing the application experiment.

## What the evidence supports

The [v10 parent report](../../runs/agentops-native-eligibility/bridge-parent-check-v10.json)
accounts for 18 executed cases: **4 strict native successes, 11 complete
recorded non-successes, and 3 partial cases**. The parent report records 2,371
exported files checked. The [results](agentops-bridge-results-v10.md) and
[partial-case analysis](agentops-bridge-gap-analysis-v1.md) explain the boundaries.
B7 achieved the required task/effect observations but has a forced service exit
and no terminal snapshot; it remains partial. B5/B6 did not attempt confirmation
after public recovery failed. These cases do not prove whole-interface absence
of a legal completion route.

The study uses deterministic local fixtures and simulated SQLite domain state.
It does not measure production reliability, natural failure prevalence,
live-model utility or authenticated human approval. CP1 alone is passed:
**5% verified deliverable credit**. No contribution route change, human approval
or final paper completion follows from preparing this package.

## Verification and current limits

From the project root:

```text
python scripts/build_supervisor_demo_v1.py --check
node --check demo/supervisor-v1/app.js
node --check demo/supervisor-v1/presentation.js
```

On 28 October these checks passed: 211 package inputs, 220 output files,
all 18 exact case records and JavaScript syntax. This is package verification,
not a new application run or a fresh scientific reproduction. The package
[manifest](../../demo/supervisor-v1/manifest.json) binds the exact inputs and
generated files. The [package README](../../demo/supervisor-v1/README.md) explains
rebuilding and the suggested walkthrough.

**Screen verification is pending.** The browser access host was unavailable;
the native Chrome fallback stopped because Computer Use could not confidently
determine the current URL. No slide-fit, mobile-layout or interactive browser
pass is claimed. Before presenting, check all eight slides on the actual
display, arrow navigation, notes/fullscreen, case selection, B6/B7 comparison
and request expansion. This limitation does not invalidate the byte/count
checks above.

The sealed v11 preparation was not launched and remains preserved. After the
prospective export correction and 100 passing Linux tests, the separately sealed
[v12 diagnostic](agentops-bridge-diagnostic-results-v12.md) executed all three
cases. N11 and explicitly header-configured B7 passed the strict contract with
clean exits and terminal snapshots. B6 remains partial; all three shutdown
captures are complete. The parent checker verified 2,617 exported files.
The earlier B7 hang did not reproduce; no cause or repair is established.
Read this follow-up alongside the unchanged 18-case v10 replay and slides.
Do not merge the two allocations or rewrite the historical B7 partial outcome.

## Decisions still needed

The [CP2 packet](cp2-review-packet-v2.md) gives the mandatory gate questions.
The [task-validity packet](task-validity-supervisor-packet-v1.md) supplies concrete
operations acceptance contracts and separate human review forms. It also makes
the missing procurement domain explicit; Carol remains a reference microcontrol.
Review the actual contribution beyond strong comparators, substantive validity
of two domains and their task contracts, and the remaining evaluation/review
work. Record reviewer identity, date, exact versions, allowed claims, objections
and required changes in a new record. The planned meeting is not completed
review, and an AI assessment cannot stand in for the supervisor.
