# Retained first release-software preflight failure

Run [43076696650](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43076696650)
at `03590f3d54c100caef411d0102f319b9e6133c1d` failed before source capture,
tests, benchmarks or demo execution. The complete candidate-bank validator
required the original pinned public AgentOps seed database, which was present
locally but absent from the Git index. The upload step found no allocation and
failed too. Root reproduced the same missing-file error in the clean isolated
checkout. This attempt earns no release-software acceptance credit.

The [terminal run/log receipt](../../runs/v1-release-software/v1-failure-43076696650-1/retention.json)
preserves the run head, failed logs and absence of artifacts. Its separate
bank-source census identifies 32 unindexed pinned public source/data files.
Their exact bytes, including the upstream license, are included prospectively
for the source-derived bank. This packages citation inputs; it executes no
original application and supplies no human gold.

The [additive V2 wrapper](../../scripts/verify_research_v1_release_v2.py)
creates an outer receipt before the unchanged V1 checker preflights. Its
[separate workflow](../../.github/workflows/research-v1-release-verification-v2.yml)
retains failed preflight outcomes as well as the existing core, demo and replay
outputs. The original V1 coordinator, workflow and failed attempt are preserved.
Only an actual completed, retained and checked V2 run can close the release gate.
