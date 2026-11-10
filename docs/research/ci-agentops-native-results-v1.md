# Verified hosted AgentOps admission result

On 10 November 2026, [GitHub Actions run 42808110286](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42808110286)
at commit `76d133f3ba251ffe37e7f932cb986af8e7830f28` completed the original
N11 native control followed by admitted B7 with **strict success in both cases**.
The standard Ubuntu 24.04 job took about 75 seconds. It used managed Python
3.13.1, Node22.13.0 and no live model calls. This is a separate hosted profile;
the prior WSL host identity and failed local resource gate are not reinterpreted.

| Verified observation | N11 | B7 |
|---|---:|---:|
| Original task reached `completed` | Yes | Yes |
| Original inventory status became `operational` | Yes | Yes |
| New audit rows | 1 | 1 |
| Captured ASGI requests | 7 | 11 |
| Client and service exit codes | 0 / 0 | 0 / 0 |
| Forced cleanup or cleanup errors | None | None |

The native control finished before B7 started. B7's admission returned
`supported` with a valid certificate, using 33 work units of the unchanged
100,000 budget. Its public task/context matched the original service task.
Exactly one MCP continuation write matched exactly one actual origin
`SendMessage` continuation, ASGI sequence 9, with identical method and parameters.
The independently checked effect was `expected_single_effect`, with no deviations
or unrelated-state changes at the captured boundaries.

The local audit reran trusted checkout validators against downloaded raw
evidence, without executing downloaded code or importing application SDKs.
Native case, admitted client/case, service effect, ASGI byte/chunk, startup,
asyncio return, interpreter exit and owned-process checks all passed. Both
process groups were already empty and remained empty; no forced stop was used.
The service factory named the fresh staged original `agent/server.py`.

All **1,138 exported files (15,333,533 bytes)** and **864 staged inputs**, including
the exact 421 original application files, matched their recorded hashes. The
source archive, staging bundle, export manifest and exporter hashes also matched.
The exporter retained unchanged source inventories, and the selected Python
runtime inspection was identical before and after. Current checker/source bytes
matched the staged bytes. Full installed-runtime authentication and independent
capture authentication are outside this result.

The compact review is [download-42808110286-independent-review.json](../../runs/ci-agentops-native/download-42808110286-independent-review.json).
The downloaded evidence is retained locally at
`runs/ci-agentops-native/download-42808110286/`; its original terminal result is
`export/workspace/runs/agentops-admission-live-v1/attempt/result.json`.
GitHub's artifact `agentops-native-42808110286-1` has three-day retention. Its
reported transport ZIP digest is recorded as reference only; the local audit
verified the exported file inventory and hashes directly.

This result establishes one deterministic application fixture in each arm and a
conditional one-step public-recipe admission followed by the real original task
completion and effect. It does not establish full action-space closure, a second
qualified domain, a conversational benchmark, or novel comparative advantage.

Remaining CP2 work is a defensible contribution and the required human
feasibility/novelty approval; the fair direct comparison has not demonstrated
added certified cases. Remaining CP3 work is qualification of the two-domain
task/gold corpus, original AP2 execution and the prescribed human reviews.
Prospective candidate banks remain unqualified. This note grants no automatic
research-rubric percentage credit.
