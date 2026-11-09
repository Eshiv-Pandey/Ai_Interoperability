# AgentOps original local archive and setup v1

25 October 2026. **Source acquisition resolved; runtime/native eligibility open.**

The user downloaded the requested commit-pinned source ZIP and reported it in
the `sem_7` folder. The original remains there unchanged; an exact copy is retained
at `external/downloads/agentops-c806b7f1.zip`. Its SHA-256 is
`491d1c0ee1bd6f54063eb183915b913fc458a277785eeb4ddfcb5efcba20ad0b`.
Both archive root and ZIP comment report
`c806b7f1cd0042c9817c0a4c46d80a9a95a24293`. CRC inspection passes.
These are coherent archive/provenance labels and byte receipts, not independent
authentication of Git objects or a claim that an archive directory is a Git checkout.

[Ingestion](ingestion.json) accounts for all 423 archive file entries: 421 regular
files are extracted unchanged under `external/agentops-c806b7f1`; two original
symlink payloads are preserved inert under this evidence directory. No symlinks
were created. The `agents/python/agent -> src/agent` convenience alias is therefore
absent; the selected upstream pytest configuration imports its maintained `src`
package directly. The observability link is also not materialized. Full checkout,
ADK discovery via the alias and platform equivalence are not established.

The initial inspector deliberately rejected the first symlink before extraction;
its [failure](initial-inspection-tool-response.json) is retained. The revised
read-only inspector accepted inert link inspection but printing root AGENTS.md
failed under Windows cp1252; that [response](encoding-inspection-tool-response.json)
is retained too. Running the same inspector with Python's UTF-8 mode then printed
the complete instructions and passed; the [full response](utf8-inspection-tool-response.json)
is saved. Neither failed inspection extracted files or imported application code.
Root AGENTS.md is the only AGENTS.md in the archive and was read before extraction.
Its source/seed/state, guarded action, offline/model and contribution boundaries
remain applicable. No upstream source or lock was edited, so this is external
eligibility work rather than a claimed completed contributor/maintainer gate.

Exact local source now revalidates the former formatted-source lead:
application 0.11.0, CPython >=3.13,<3.14, ADK 2.10.0/A2A SDK 1.1.5 lock entries,
MIT `agents/LICENSE`, original DataPart confirmation test, guarded in-process
actions and local transactional service/audit effects. The test begins at source
line372; former web formatting line labels are not local file line numbers.
The test uses the original task/context and asserts inventory operational and
latest audit attribution/session/invocation/rationale/action/target. It still does
not alone assert exactly one new audit row or all unrelated rows unchanged.
Its synthetic A2A_USER attribution is not authenticated human identity.
The source/support policy release-gates Linux x86_64; Python3.13 availability
and lock Windows wheel entries do not establish full native Windows support.

The [once-only preparation](../../../../runs/agentops-native-eligibility/v1/pre-execution.json)
planned pinned uv0.12.0 bootstrap, exact locked dev sync and the unchanged upstream
offline confirmation test. Only bootstrap ran. Its preserved
[result](../../../../runs/agentops-native-eligibility/v1/result.json) and
[binary process streams](../../../../runs/agentops-native-eligibility/v1/bootstrap.json)
record exit1 and no distribution candidates. A read-only environment check found
`PIP_NO_INDEX=1` and no uv/ADK/pytest/A2A distributions or uv cache. This failure
does not show that uv0.12.0 is absent upstream. No setting was cleared or proxy
changed, no package was installed, and no native test or request ran. Pip temporary
cleanup warnings are retained; no temporary directory was deleted manually.

A later source read guessed nonexistent `clients/web/app.js`; rg reported the
missing file while other reads in that command completed. `rg --files` located
the actual maintained `clients/web/index.html`; no absence or runtime conclusion
uses the failed guessed path. This paragraph is a disclosed visible-output
narrative, not an original binary process receipt.

The [prepared normal-terminal setup](../../../../scripts/setup_agentops_dependencies_v2.ps1)
downloads the exact Windows uv0.12.0 artifact from upstream `mise.lock`, verifies
its recorded SHA-256 and version, then syncs the unchanged app lock with runtime,
cache and temporary files confined to the workspace. The script's PowerShell
syntax was checked; it was not executed here and no user result is assumed.
It installs dependencies only, with a separately versioned attempt/receipts,
no model, test, cloud, cluster or application service. A successful future sync
still requires a new native control with all original assertions and private
effect/safety checks, followed by actual card/wire and unchanged bridge eligibility.

The [API-access failure](../agentops-git-object-api-v1/decision.md) remains historical
evidence; its then-pending download status is superseded by this supplied archive.
C1 distinction/threshold, independent task validity and human scientific review
are still missing. No qualified second domain, performance measurement or gate
credit is added. CP2 stays open, CP7 pending and verified credit remains 5%.
