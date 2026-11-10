# Lossless proof packaging: appendix to manuscript V7

This representation experiment supplements [manuscript V7](working-draft-v7.md).
It packages the ordered negative-proof prefixes already retained by shared
lifting as a suffix-shared acyclic language graph. The independent decoder
restores exactly the original ordered prefix list; the adapter submits the
restored proof to the unchanged semantic checker.

We encoded all 26 unsupported certificates from the retained shared-lifting
solver run with its 100,000-unit allowance. Encoding used the separate default
codec allowance of 2,000,000 operations. All 26 restored certificate objects
match their originals. Byte counts use complete certificate wrappers serialized as UTF-8
JSON with sorted keys, compact separators, `ensure_ascii=False` and
`allow_nan=False`. The direct certificates use the same serializer and subset.

| Case or subset | Original prefix proof | DAG proof | Goal-pruned direct proof |
| --- | ---: | ---: | ---: |
| `scale-0031`, 256 prefixes | 8,895 bytes | 1,736 bytes | 338 bytes |
| `scale-0023`, 16 prefixes | 735 bytes | 652 bytes | 338 bytes |
| All 26 unsupported cases | 15,128 bytes | 11,918 bytes | 7,760 bytes |

Two DAG proofs shrink and 24 grow; none tie. The largest repeated-prefix case
drives the aggregate reduction of 3,210 bytes, or approximately 21.2 percent.
The direct proof remains smaller in aggregate and on that case. These are
deterministic representation-size observations. They establish no solver,
checker, memory, latency, admission-coverage or business-utility improvement.

The graph retains terminal nodes, uniquely labeled arcs and the original word
order. It shares finite suffix languages. Checking the expanded proof preserves
the original correlated incoming frames, horizon, uncertainty and binding.
The `call-A,target-B` refutation cannot erase the modeled
`call-B,target-B` witness. Concrete prefix replay can remain exponential.

The [V2 implementation](../src/interoperability/refutation_prefix_dag_v2.py)
passed 31 constructed checks, including malformed graph, incomplete coverage,
correlation, clock, expansion and resource-bound cases. The independent review
identified three V1 defects: oversized integer conversion, unbounded extra-field
traversal and missing complete-input-envelope size checks. V2 corrects them.
The new adapter bounds its input and output under one codec allowance and
delegates only the negative decision and restored certificate. V1 artifacts
and their adverse review remain preserved.

The [complete comparison receipt](../docs/research/refutation-prefix-dag-comparison-v2.json)
records all 26 cases, every size increase and exact source and certificate
fingerprints. The input is the unchanged retained
`budget-100000/results.jsonl`, 981,178 bytes, SHA-256
`92137f9cc15feac73fb51b9777cd961be307c6161bf6ad5c797ef3464ff1817c`.
The comparison performed no new admission solver or semantic-checker runs on
those retained cases. Existing semantic-checker outcomes are inherited evidence.

These are related authored development profiles, not independent held-out
application tasks. The experiment supplies a bounded proof-packaging artifact
and an aggregate comparison with the direct proofs. Original-method
novelty, qualified application evaluation and accountable final scientific
review remain unresolved.
