# AgentOps startup import boundaries, 29 October 2026

The retained v4 stacks locate two concrete application import chains before fixture readiness. The inspected pinned source provides no supported configuration that removes either chain while preserving this confirmation fixture. This is a localization finding, not a proven SDK defect, deadlock, resource diagnosis or repair.

The [16-sample analysis](../../runs/agentops-admission-execution/v4/startup-analysis-v1.json) spans 5.002–82.581 seconds after observer installation. Samples move through import loading and module initialization. Some reach faulthandler's 100-frame limit; the analysis identifies the same thread from entrypoint-bearing samples and marks truncated entrypoints. The [v4 results](pending-admission-live-results-v3.md) retain the failed 65-second readiness gate, forced termination and skipped B7. They establish no fresh candidate application run.

The wrapper installs observation before calling the preserved service. In `serve_agentops_bridge_v1.py:32–36`, the service loads the original `tests/test_server.py`; `create_app` is only called later, at service line 57. The observed stacks remain inside that original test-module import. They do not show the later fixture construction or Uvicorn startup.

| Observed chain | Raw stack evidence |
| --- | --- |
| `test_server.py:25` → `actions.py:25` → `pii.py:23` → `presidio_analyzer` → spaCy/Thinc | [startup-stacks.txt](../../runs/agentops-admission-execution/v4/export/workspace/runs/agentops-http-control/admission-live-v1-N11/service/startup-diagnostics/startup-stacks.txt), lines 283–363; application edges at 346, 352 and 360. |
| `test_server.py:25` → `server.py:44` → `composition.py:17` → `governance.py:42` → `guardrails.py:23` → `google.adk.tools.skill_toolset` → `google.adk.skills._utils` | The same raw stack file, final sample, lines 1398–1445. This is the sample at 82.581 seconds, after the readiness deadline while cleanup was pending. |

`pii.py` imports Presidio classes unconditionally at lines 23–28. Its analyzer construction is lazy at lines 118–126, but the imports are not; the module-level `_OfflineEmailRecognizer` subclass at lines 109–115 also requires the imported class. `actions.py:25` imports `redact_persisted_text` before any action is called. Thus “lazy analyzer” does not mean the Presidio/spaCy import closure is absent during startup.

The second chain also precedes configuration-dependent construction. `server.py:44` imports `root_agent` from `composition`; composition imports governance at line 17, and governance imports guardrails at line 42. `guardrails.py:23` unconditionally imports `LoadSkillTool`. The fixture later injects its own agent into `server.create_app`; that selection at server lines 544–546 does not bypass these already-executed imports. The same factory applies the policy plugin to the injected agent at lines 560–565.

The supported-configuration check found:

- `Settings.entrypoint` selects agent/workflow/coordinator, but composition's imports run before the selection at lines 120–133. Changing that setting does not remove either observed chain.
- `semantic_retrieval` is already false by default (`config.py:163–166`) and does not guard the Presidio imports.
- `sanitize_tool_output` (`config.py:159–161`) controls injection hardening, not import loading or PII removal. Guardrails explicitly retain PII treatment for both output trust classes (lines 3–9); governance attaches the redaction callbacks at lines 59 and 69.
- No PII-import or skill-import disable setting is declared in the inspected `Settings` class. Removing dependencies, changing import order through stubs, bypassing policies or modifying the original application would be a different fixture/source boundary, not an established repair for this control.

The host observations also do not justify a fresh launch now. The recorded [v4 invocation plan](../../runs/agentops-admission-execution/v4-invocation/plan.json) reports 323,731,456 available physical bytes before staging; its [result](../../runs/agentops-admission-execution/v4-invocation/result.json) reports only 2,453,504 afterward. A Windows-only tool observation during this review at **2026-10-29 00:45:30.5145517 UTC** reported 254,000 KiB free out of 6,139,972 KiB total physical memory, approximately 248 MiB free. A root-agent observation in this same 29 October turn reported 15,652 KiB free; its read-only `wsl.exe --list --running --quiet` returned exit 0 with empty output. The latter observation has no exact timestamp in its stdout, so no precise ordering is asserted. These current-turn observations came from tool output; no retained raw command files are claimed for them. They are snapshots, not a time series or proof that memory pressure caused the earlier failure.

**The next live prerequisite is a measurable, prospectively described improvement in host resource availability before allocating another attempt.** The current readings do not show it, even with no running WSL distribution reported. No numerical “safe” memory threshold has been established by the retained service data. Once conditions materially change, a new allocation must retain the original 65-second readiness rule, native N11-before-B7 gate, required completion/effect checks and cleanup requirements from the [live plan](pending-admission-live-plan-v3.md). No consumed allocation should be rerun. Until then, the implemented admission algorithm and benchmark remain the supervisor demonstration; no new SDK fix, readiness relaxation, unrelated service shutdown or paper work follows from this investigation.

The following hashes were read from the captured v4 files for this source inspection. Application paths below are relative to `runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/`; script paths are relative to that export's `workspace/`.

| Captured file and relevant lines | SHA256 |
| --- | --- |
| [tests/test_server.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/tests/test_server.py), 15–28 | `8257f7267d516d12f656ff886f5796bb58178051cc13d3c582dc9eefbd78b270` |
| [src/agent/actions.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/actions.py), 19–25 | `e5aa3eeba9d3b04a4a505514241ea4fbce1890989f54a89ba9ea7173895eedd0` |
| [src/agent/pii.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/pii.py), 18–32, 109–126 | `702c6afa72203c124d91e9de16a20cbd2a18ae8f215d780fdf078944b5bd6455` |
| [src/agent/server.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/server.py), 44–48, 537–565 | `578bd65522c3edcfd49d831b96b42a4990e1aaa4f39c0e52612e1dbe667680d8` |
| [src/agent/composition.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/composition.py), 12–24, 120–139 | `d1ad9f887328345f6edda5ef7d412c48938e62d708e39c645a479e1d5c166ad8` |
| [src/agent/governance.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/governance.py), 40–43, 55–85 | `e622f9811521cf6c6ea51161bdcf9f2280db3def7281abe2b632ad38decd0c33` |
| [src/agent/guardrails.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/guardrails.py), 3–9, 19–32 | `65d747eee5bc305e260d049200e24157144c54f71992ce5149b85b87a9402406` |
| [src/agent/config.py](../../runs/agentops-admission-execution/v4/export/workspace/external/agentops-c806b7f1/agents/python/src/agent/config.py), 24–29, 40–52, 154–172 | `ae37459425a0720f607ff7b3ee30c100c1d902b07e5e12da7b698557a0774587` |
| [scripts/serve_agentops_bridge_v1.py](../../runs/agentops-admission-execution/v4/export/workspace/scripts/serve_agentops_bridge_v1.py), 20–38, 51–75 | `ee2f2a91481fb53ff704327d54d48d6ec8e334b8589bb8fd66d0b0243491e0ec` |
| [scripts/serve_agentops_bridge_diagnostic_v4.py](../../runs/agentops-admission-execution/v4/export/workspace/scripts/serve_agentops_bridge_diagnostic_v4.py), 18–39 | `c93360877a0de2f68a409d410d1a3f157e3ede68d2004b35c26dfba63c6be569` |
| Raw `startup-stacks.txt`, sample references above | `55a2ad0a00c4423496d397951b286236eef5169a192510e8e1ac34f96a4b23a8` |
| `runs/agentops-admission-execution/v4/startup-analysis-v1.json` | `a4260eaa7723e31fd3f70ed342fdfe8fe39571cddc38f30b600603424b2f97dd` |

This note used source/stack reads and Windows host observations only. It performed no application, test, solver, checker, replay or WSL-runtime launch, changed no implementation or host setting, and establishes no human approval, fresh live acceptance, novelty, domain qualification or completion percentage.
