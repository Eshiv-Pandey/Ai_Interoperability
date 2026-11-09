# Supervisor review package · browser format

Open **index.html** in a current browser for the archived case replay. Open
**presentation.html** for the eight-slide presentation. Keep the entire folder
together when copying it to another computer. No server, install, network,
application run or model call is needed. JavaScript must be enabled.

## Suggested eight-minute walkthrough

1. Present slides 1–4: problem, path, strict success contract, fixed matrix.
2. On slide 5, open the replay's default B6 / B7 comparison. Read its four
   outcome fields separately. Expand B6's raw GetTask (sequence 5) and B7's
   raw GetTask (sequence 6) / DataPart SendMessage (sequence 7).
3. Select N11 as the comparison for a strict native baseline. Use route and
   outcome filters to inspect the remaining cases; filters affect the left
   selector, while the comparison selector retains all 18 cases.
4. Return to slides 6–8 for the artifact, schedule and supervisor decisions.

Presentation: Left/Right or PageUp/PageDown navigate; Home/End jump to first/last.
Space advances when focus is not on a control. Use the Fullscreen button (or
browser F11), and Escape to exit. Speaker notes toggles the editable notes.
The deck adapts to a narrow display; a desktop or projector is recommended.
Browser print includes all eight slides. This is HTML, not a PowerPoint file.

## Dates and evidence limits

Application experiment: **27 October 2026**. Package context: **28 October**.
Supervisor review: **31 October**. Working completion: **1 November**, assuming
the week ends Sunday. The unchanged registered title appears on slide 1.

This is archived replay, not a live demonstration. It uses a reproduced
AgentOps confirmation fixture, a deterministic model double and simulated
SQLite inventory. Synthetic protocol approval is not authenticated human
approval. It establishes neither a novel method nor a qualified second domain,
and the counts are not a population performance estimate.

The v10 report accounts for 18 cases: 4 strict native successes, 11 complete
recorded non-successes and 3 partial cases. B5/B6 attempted no continuation
after the public read failed. B7 reached the effect but lacks clean teardown
and its required terminal snapshot, so it remains partial. Task completion,
effect, evidence completeness and strict result are separate fields.

## Rebuild and verify

From the repository root, with Python 3.10 or later:

```text
python scripts/build_supervisor_demo_v1.py
python scripts/build_supervisor_demo_v1.py --check
node --check demo/supervisor-v1/app.js
node --check demo/supervisor-v1/presentation.js
```

The builder reads retained reports and wire captures and writes only this
package. It does not change any experiment or research outcome. Rebuilding
replaces only its generated files. `--check` verifies package/source hashes,
18-case accounting, exact checker fields, captured headers and local links.
It is not a rerun of the scientific checker or independent reproduction.
The manifest lists every source input, copied evidence path and SHA-256 hash;
its output hashes exclude the manifest itself. No fresh 2,371-file audit is
claimed by this presentation builder.

`data.json` is portable structured data; `data.js` provides the same data without
fetch so local-file browsers can run it. `source-report.json` is the exact
parent report. `gap-inspection.json` is the retained post-capture inspection.
`evidence/` contains the exact request body and exchange metadata for each RPC
shown. Full source responses, domain snapshots and process evidence remain in
the repository paths named by the report and manifest.

To edit the presentation or interface, change the template constants in
`scripts/build_supervisor_demo_v1.py`, rebuild, and repeat verification. Direct
edits to generated files are overwritten on the next build.
