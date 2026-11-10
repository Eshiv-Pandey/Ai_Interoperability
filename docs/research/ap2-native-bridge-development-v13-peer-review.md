# Independent AP2 V13 package and source peer review

11 November 2026. This V13 snapshot is ready for a separate hosted allocation;
no concrete blockers remain. The reviewer independently verified all 59
distinct controls across eight suites: 57 passed and two POSIX positive IPv6
probe controls remain skipped on Windows. The generic native TCP controls
were rechecked with installed site-packages enabled and all eleven tests in
that suite passed. No original AP2 application, solver or provider executed
locally; constructed TCP/Node controls are not benchmark observations.

The earlier V12 review missed physically checking its declared outgoing
fixture paths. V13 now includes all nine exact source/license files, totalling
81,046 bytes. Each exact V13 retained path was checked for containment and
regular-file presence; its bytes match V11, the V13 public manifest, the pinned
sealed graph and the actual sealed runtime ZIP member. The graph SHA256 remains
`efafadaa673d78dd1e4ccf20d92db9941e00d6bd802d909fdae4c4b8a8278de6`;
the runtime ZIP SHA256 remains
`c4567dc405e74d664921f038e6c5acb454c66fd85f42f21c04a10c8e75305864`.

The reviewer independently ran the early package check with `--require-tracked`:
all 53 required paths were present in the Git index, including the nine
previously ignored outgoing fixtures, 25 owned components and 19 support paths.
Support checks cover the evaluator, workflow, controls, CA fixtures and pinned
urllib3 fixture provenance. The checker runs before runtime preparation/install.

Version comparison used explicit module names, full AP2 schema strings and
exact benchmark/private-path prefixes, never a generic slash-version
replacement. Ten production/Python/JS bridge/control files preserve V12
semantics after those allowed retags; the actor's sole extra owned component
is the package checker. HTTP URLs and loopback hosts/ports were separately
compared without normalization and are literally unchanged, including bridge
request helpers. The repaired controls also use full-name normalization and
cover the three JS pairs. The temporary bad URL retag is not accepted evidence.

Cases, arms, source pin, 104-cell prospective scope, policy/application logic,
native transport, certificate policy and inherited evaluator guard gate remain
unchanged. The gate still requires one expected evaluator-file denial, zero
unexpected network denials and zero unallocated process denials. V13 preserves
the previously reviewed exact single import-time IPv6 bind capability, fresh
socket/close witness, pre-guard public platform cache and exact loopback bytes
handling. V11's redacted `getaddrinfo` host type and original bytes remain
unknown. Hosted Linux positives, smoke and any actual matrix outcomes are
pending; no historical missing outcomes are supplied by this source review.

The exact reviewed identities are below. The public manifest additionally binds
all nine source/license copies. Subsequent code changes require a fresh review.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| scripts/ap2_reference_development_v13.py | 58,196 | `5bff3e8fcc9ee84b8393b14be843b0a3c01c9b98444760ba4b5c9da01660b77e` |
| scripts/ap2_native_guard_policy_v13.py | 5,568 | `f0f2e77afa776211e7ebb64dd4a5527bc98b4b4a50e94a35e85887fdce528642` |
| scripts/check_ap2_native_package_inputs_v13.py | 5,348 | `eda7939c1e1b0a8482fa3f6a3dea0ea8d9da6cda5825855ff98d83b208d61522` |
| scripts/evaluate_ap2_native_bridge_matrix_v13.py | 61,075 | `be377372a4996dd5b5dfd11cb829a35c2694cfb6148b659057709095171af6ed` |
| scripts/ap2_native_bridge_runtime_v13.py | 6,487 | `69ab94203b986114cf53fcd9714bfe0ddc2dc1b14bb9d7973e6374a3ea7e77cf` |
| scripts/ap2_public_certificate_guard_v13.py | 8,306 | `c7f8b00c97ee2842e589a267fabb6ef2d4e30bb64325d1b286d0f1a90825ac33` |
| scripts/run_ap2_native_bridge_matrix_v13.py | 12,877 | `9c832477cab29ec5f8ee8b08f71a53eb127235172df5d8727ddd135b5cf577cc` |
| src/interoperability/ap2_native_transport_v13.py | 10,362 | `374e83e804b2a4dd0e48b4b688a8b52f349bd5afa18a39e231df3130c3ad66cc` |
| scripts/ap2_bridge_client_v13.mjs | 16,725 | `90d43522b793f2fdcb34c1828b6b50b6d5be6ca2fc1275110a187694c2abd9c2` |
| scripts/ap2_bridge_network_guard_v13.mjs | 10,035 | `c5703df2b78cf374929e6c443f7d4e3b83b139a62c7f1edbd6c6e83475ecf5cc` |
| tests/ap2_native_bridge_controls_v13.mjs | 5,301 | `c8e5c0cb4a5bc47da86ee56b772d255935bb023c8a7a7fa9754c46e8807053d4` |
| tests/test_ap2_native_bridge_development_v13.py | 16,017 | `eb9ab90e98376a7458be57f6e9ba22ccfaf58e8933905a678823ad2849e77f02` |
| tests/test_ap2_native_guard_policy_v13.py | 12,340 | `9555a37bc1e81501120b84363bc38c4da307bf70524c9c99510bea2792316a35` |
| tests/test_ap2_native_package_inputs_v13.py | 7,585 | `9d0712e05b4d8502cd1ab2841a423a844aaac8673fa6640fa37eeff828721e23` |
| tests/test_ap2_public_certificate_guard_v13.py | 12,437 | `d31fa80a42efc5d887116328d78096aeb36c3a7a312154ddbe9a03b346d79b04` |
| tests/test_ap2_worker_stage_prelude_v13.py | 7,152 | `d30d4c3d424b6b3603e31ebeea0b3b3ddd31cefa6407d681552669d2a8aa753d` |
| tests/test_ap2_grpc_public_ca_v13.py | 6,248 | `018f77d1c30bebed87a4e44b1875ee423d0615df24e03b531e5e0d44ac3296ef` |
| .github/workflows/ap2-native-bridge-development-v13.yml | 6,126 | `b7ab7de2be45e73556229169b112c5a1cf9a90a84f2e84dd703239e1997d8b7a` |
| benchmark/ap2-native-bridge-development-v13/application.json | 11,806 | `623c255f6781c9c72dea606b3d0939b6d23c17296440cedc9d0225d3f39b6943` |
| benchmark/ap2-native-bridge-development-v13/evaluator.json | 2,591 | `9b9c41a58975e8c5ffb6bc5aebb0aae39ef3af8841875aaea788403cfcf19ce7` |
