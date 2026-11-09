# AP2 human-present environment preparation

**Latest result, 30 October:** the exact 187-package offline installation is now assessed with [source/file manifest](../../runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json) SHA4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5. The [read-only result](../../runs/ap2-environment-preparation/installed-assessment-v1/result.json) verifies 15,276 environment files, 14,491 source payloads and 10,991 code payloads, including all 129 local Python modules. Pip consistency passed; all jobs released. Ten stale RECORD claims at five shared documentation paths remain explicit: eth-abi/eth-rlp/hexbytes each ships different docs, and actual installed bytes match eth-abi. No RECORD repair or reinstall occurred. Original imports, model/key/service calls and original runtime compatibility remain unverified. The external base runtime is not fully inventoried.

The initial [installer preallocation refusal](../../runs/ap2-environment-preparation/installer-prepare-failure-v1/failure.json) is preserved: py1.11 contains nested vendored metadata; the reviewed v2 selected unique top-level distribution metadata. The completed [first install result](../../runs/ap2-environment-preparation/installed-environment-v1/result.json) is also preserved with its strict RECORD failure. The separate assessment records actual collisions instead of changing that result or the environment.

The earlier [14:43:31 UTC diagnostic](../../runs/resource-diagnostics/ap2-continuation-20261030-v2.json) had about 25 MiB physical and 3.83 GiB commit available. After the user freed resources, a single 15:56:13 UTC diagnostic passed both minima, but the subsequent [AgentOps timed gate](../../runs/upstream-agentops-native/inventory-status-v2/prestage-gate.json) fell to about 79/128 MiB physical and refused before staging. Sustained headroom and fresh AP2-specific bound checks remain necessary before original imports. The complete provider-usage/reference/passive-capture contract also remains open.

The [reviewer index and form](reviewer-files-v1.md) are available in a [ready ZIP](../../review-packages/reviewer-2026-10-30-v1.zip). Supervisor contribution review is not yet done, and the 12/8/48 task bank remains incomplete. The hard 70% marker is 31 October under the full rubric; verified gate credit remains 5%. Paper is deferred. Historical preparation detail follows; the installation state below is superseded by this latest result.

30 October 2026. The original AP2 runtime declarations resolve on native Windows
CPython 3.13.1 without changing their pins. The indexed runtime and separate
declared build-backend artifacts are now acquired. All three local source wheels are now built and checked. Installation, import
compatibility and original application execution remain separate obligations.

| Preparation | Retained result |
| --- | --- |
| Source-derived inputs | 25 runtime rows, preserving order and duplicates; two source-bound local edges; three separate backend rows |
| Indexed runtime dry run | Exit 0; 184 distributions; original inputs unchanged |
| Declared build-backend dry run | Exit 0; seven distributions; original inputs unchanged |
| Report-derived artifact selections | Exact wheel URLs, versions, SHA256 and metadata retained; no repeated solve |
| Frozen wheel acquisition | 189 unique wheels, 189 hashes verified, 111,982,465 bytes; both input locks unchanged |
| Pristine original source layout | 136 AP2 files and 24 x402 files; all staged copies and original inputs unchanged |
| Local source builds v2 | Three wheels built; original dependency/Python metadata and 129 Python module hashes match |

The [input export](ap2-source-derived-dependency-inputs-v1.md) and
[artifact-selection guide](ap2-report-derived-wheel-locks-v1.md) describe the
original declarations, selected x402 source and separate local package edges.
The completed dry runs retain their exact argv, input snapshots, driver and
stdout/stderr in
[runtime](../../runs/ap2-dependency-resolution/windows-cp313-dry-run-v1/result.json)
and [backend](../../runs/ap2-dependency-resolution/build-backend-dry-run-v1/result.json)
allocations. Python `-I`, pip `--isolated`, `PIP_CONFIG_FILE=nul`, explicit
public PyPI and binary-only selection suppress startup/configuration drift and
source builds. Neither dry run installed packages or imported the application.

The [wheel-byte manifest](../../runs/ap2-environment-preparation/wheel-store-v1/manifest.json)
retains one request and response record for each immutable artifact, its HTTP
status/final URL and actual SHA256. The 184 runtime and seven backend selections
share packaging and pluggy, so their union contains 189 files. A preliminary
count guard incorrectly expected 190 and refused before allocating output or
issuing requests. Its
[post-observation failure receipt](../../runs/ap2-environment-preparation/wheel-fetch-preallocation-failure-v1/result.json)
and failed driver are preserved. The corrected first byte capture passed; no
consumed artifact allocation was rerun.

The original 134-file AP2 source capture contains the complete selected SDK and
Python sample build inputs, root README, license and pyproject. The human-present
flow also reads two files outside that Python subtree:
`code/samples/certs/issuer_cert_sdjwt.pem` and `ds_cert_sdjwt.pem`. Both were
[captured once](source-evidence/ap2-hp-cert-assets-v1/manifest.json) at the original
AP2 commit with HTTP 200, exact sizes and matching Git blob identities. The
retained complete AP2 tree remained unchanged. Their inclusion is separately
bound; the earlier source capture is preserved.

The [pristine source-stage manifest](../../runs/ap2-environment-preparation/source-stage-v1/manifest.json)
records all 136 AP2 and 24 x402 files, exact source origins, hashes and original
Git blob identities. It preserves the original directory layout and the three
human-present `agent.json` files. Build operations must use separate copies of
this tree. The original sample packaging has no explicit JSON package-data
configuration; actual wheel inclusion must be inspected before relying on an
installed-wheel-only launch. Original JSON/source files must not be edited to
make an unchanged-source claim.

The first [local build attempt](../../runs/ap2-environment-preparation/local-build-v1/result.json)
installed and byte/version-verified the seven backend packages, and all three
dynamic requirement hooks passed with empty requirements. AP2 backend import
then failed because the preparation guard denied `subprocess.Popen`. No wheel
was produced. All 171 pristine/backend inputs and 296 original source files in
the separate build copies remained unchanged; all owned jobs were released.
Static tool-source inspection identifies CPython's Windows `ver` fallback as a
candidate, but the denied call's exact runtime stack/argv was not retained, so
the v1 cause remains unconfirmed. This failed allocation is consumed. Any
prospective guard correction and build use a new namespace; original source,
runtime pins and live resource minimums stay unchanged.

The first [prospective v2 build](../../runs/ap2-environment-preparation/local-build-v2/result.json)
passed all 12 commands and built the three original local packages once. Its
seven-wheel backend environment and all three empty dynamic requirements passed.
All 177 pristine/backend inputs and 296 original files in the separate source
copies stayed unchanged, all 129 Python wheel modules matched original hashes,
and wheel `Requires-Dist`/`Requires-Python` metadata matched the original
declarations. All owned processes were released.

The v2 preparation guard prospectively admits only the hash-bound Windows
`cmd.exe /c "ver"` version fallback while the process is in its owned Job,
with source/argv bindings and retained subprocess decisions. This permitted
probe was not exercised: all decisions were empty and its observed count was
zero. The successful v2 is therefore not a causal explanation or reproduction
of the earlier v1 failure. Both attempts remain preserved.

The original sample wheel omits all three human-present `agent.json` files;
the omission is recorded without packaging changes. Original source-root
execution retains those files in the pristine source stage. The x402 wheel
includes its original empty `py.typed` file with matching bytes. Neither fact
establishes original role-import compatibility.

Next, install the exact 184 indexed and three local wheels into a fresh runtime
environment offline, with dependency resolution disabled. The source-reviewed
installer requires an explicit passed local-build receipt and verifies installed
metadata, RECORD hashes, script interpreter targets and its complete file tree.
It refuses the failed v1 before allocation. No runtime environment installation
or original-role import compatibility is claimed yet.

The latest [single read-only diagnostic](../../runs/resource-diagnostics/ap2-continuation-20261030-v1.json)
at 12:02:54 UTC reports 329,293,824 available physical bytes, about 314 MiB, and
2,090,475,520 available commit bytes, about 1.95 GiB. Both are below the unchanged
1 GiB physical and 2 GiB commit minimums. This is not a timed prospective gate.
No native allocation or original application launch followed.

The admission algorithm, comparison benchmark and prior demonstration remain
the supervisor review's runnable evidence. This preparation adds no native
AP2 task grade, novel-method claim, domain qualification or checkpoint credit.
The confirmed full research-project rubric remains at 5 percent; paper work is
deferred this week.

Key receipt SHA256 values:

- Runtime report: `c478997b9d16f6a217380c89aff4ae2bd8bb9218f070848d37b7bb54c56efd6a`
- Backend report: `429666e5b75579fd3f09a63bbb32a0582e824226cb194b682a522c115ea5e770`
- Wheel-byte manifest: `ac4e3883891a108b141eed6f5bf4cb1e2b97439316f003bd6baeb89ca7ff8689`
- Pristine source-stage manifest: `78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463`
