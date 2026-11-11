# Restore and verify only the frozen V15 paper inputs

The additive [V2 helper](../../scripts/verify_v15_paper_package_v2.py) restores the exact 3,468 inputs in the sealed V15 provenance and then runs the unchanged 19-check V15 read auditor. It replaces full SDK extraction for this paper-package check. The V1 helper/guide and the failed isolated V8 restoration attempt remain preserved.

Run from a fresh isolated checkout that includes the V15 package, exact codec inventory, portability census and this V2 source/guide. Use Python 3.12 or later so the explicit Windows junction checks are available. The local controls and paper check used Python 3.13:

```powershell
$paperVerify = Join-Path 'runs/v1-release-paper' ('exact-inputs-v2-' + [guid]::NewGuid().ToString('N'))
python -I -S -B scripts/verify_v15_paper_package_v2.py --output $paperVerify
```

The helper binds the frozen provenance, manuscript, claim ledger, auditor and portability census bytes. All 3,468 required paths are checked. Existing required files must match exactly; missing direct published source/analysis files fail. For absent archived inputs, the census and conventional retained `artifact.zip`/`extracted` mapping select the exact source. This frozen manifest references no legacy download/hosted extraction destinations, so the inherited full-extraction wrapper is unnecessary.

Before publishing an evidence target, V2 validates saved completed-run/plan/retention/API identities, whole-archive size/SHA, selected part sequence/size/SHA and combined archive identity. It checks every central-directory member for safe portable names, allowed types/compression, uniqueness including case aliases, file/directory prefix conflicts, inventory membership and advertised size bounds. It streams and hashes only the needed member payloads against both provenance and retained inventory. All source groups and existing required inputs pass preflight before the first evidence publication.

Only an absent archive named as a V15 input is published. Large archives needed solely as read sources are reconstructed into bounded temporary files and closed afterward. Only missing required members are extracted. The 3,245 required archived-member inputs total 69,361,556 bytes; unrelated SDK members are not decompressed or restored. Existing unrelated files are left outside this paper-input check; it does not claim their payload integrity or full-extraction/runtime qualification. Required exact partial subsets are preserved, and a changed required input, archive, part or needed member is refused. Creation is exclusive and never overwrites a present file.

After restoration, all required input bytes are checked again. The unchanged V15 auditor reads the fresh inputs and checks all members of its small native/provider/Workflow archives as before. The auditor receives a fresh output path under `paper`; its subprocess has a bounded timeout (180 seconds by default, configurable from 1 to 300 seconds) and stdout/stderr are drained with at most 1 MiB retained per stream. A result/command/log manifest under the fresh verification allocation records success or partial failure, restored paths, source identities and the new audit identity. Failed published bytes are retained; later runs refuse drift.

V2 imports no application, SDK, provider, evaluator, solver or certificate checker. It executes only the unchanged standard-library paper read auditor. A successful receipt establishes exact paper-input restoration and that read audit. It does not establish full SDK extraction, runtime/application qualification, independent human scientific review, untouched holdout, algorithmic novelty, settlement or completion of the original 96/288/96 study.
