# Native V8 failure evidence reproduced from a fresh checkout

The [fresh hosted replay](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42900704876)
at revision `5fba7d6a6fdb9ece7fe7d68f8252046849f3ffed` reconstructed both
original native V8 archives from their published, hash-bound parts. It restored
28,192 files from the source-snapshot setup failure and 28,375 files from the
later guard failure. Every restored archive matched its original GitHub digest.

The unchanged independent appendix auditor passed all 14 checks in the fresh
checkout. It verified 21 claim inputs, all 104 ordered unexecuted matrix cells,
the separate conventional smoke return code 3, and the public-certificate guard
obstruction. The missing actual denied path and traceback remain missing. This
reproduces retained failure evidence; it adds no application execution, provider
request, native performance result or task-success credit.

The [retained replay receipt](../../runs/ci-ap2-v8-failure-evidence/retained-42900704876-1/retention.json)
binds the six-file replay artifact to GitHub's digest. The earlier
[replay attempt](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42900411002)
failed because the archive-part restorer was absent from its checkout. Its
[failure receipt](../../runs/ci-ap2-v8-failure-evidence/retained-42900411002-1/retention.json)
is retained alongside the corrected replay. Neither original V8 allocation was
rerun or changed.

To reproduce the archive and claim audit from the published checkout:

```powershell
python -I -S -B scripts/public_archive_parts_v1.py --restore runs/ap2-native-bridge-development/v8/retained-42897177156-1/archive-parts-v1/index.json
python -I -S -B scripts/public_archive_parts_v1.py --restore runs/ap2-native-bridge-development/v8/retained-42897325489-1/archive-parts-v1/index.json
python -I -S -B scripts/restore_retained_paper_evidence_v3.py --native-v8-only --restore
python -I -S -B scripts/replay_ap2_v8_failure_appendix_v1.py --output runs/ap2-native-bridge-development/v8/fresh-user-replay-v1/audit.json
```

Choose a fresh output for every replay. Restorers verify existing files and
refuse changed evidence. The [failure appendix](../../paper/ap2-v8-native-smoke-failure-appendix-v1.md)
preserves the manuscript's prior results and unresolved full-study requirements.
