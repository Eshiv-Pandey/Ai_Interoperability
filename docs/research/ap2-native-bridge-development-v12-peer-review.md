# Independent AP2 V12 source peer review

11 November 2026. The reviewed V12 snapshot is ready for a separate hosted
allocation; no concrete source blockers remain. This review does not establish
hosted application success. The reviewer changed none of the candidate files.

The exact public cases, arms, source pin, 104-cell denominator and zero-provider
scope are unchanged from V11. After version normalization, the application AST
is unchanged. The inherited evaluator gate still requires one expected private
evaluator-file denial, zero unexpected network denials and zero unallocated
process denials. Native transport and public certificate policy are unchanged
apart from their separate version bindings.

The new IPv6 admission is limited to one `socket.bind` to `::1:0`, from the
observed 4,444-byte urllib3 source file with SHA256
`2633bbdb69731e5ccb5cf4e4afd65605d86c7979cc5633126f50c92d5ad74a74`.
It checks the full compiled function and module identities, the direct
`_has_ipv6` line 127 caller and module-import line 137, exact real socket type,
IPv6 family, stream type and protocol. It additionally witnesses the fresh
unbound `::` port-zero endpoint and non-inheritable descriptor before admitting
the bind, then records and verifies that the admitted socket is closed.
No new connect, send, listen or guarded descendant-process permission is added.

Owned-host normalization accepts only the exact three existing string loopback
literals and their exact bytes equivalents, at the previously allocated ports.
It performs no decoding, hostname expansion or suffix matching. The evaluator
checks the normalized bytes-operation count against the recorded total allowed
owned loopback operations. Public `platform.platform()` metadata is cached
before the actor hook; the original application call remains unchanged and
introduces no guarded subprocess exception. Separate V2 diagnostics emit only
bounded counters and booleans, while the launcher preserves exact-once actor
execution and its return code. The V1 diagnostic helpers remain frozen.

The reviewer independently ran nine focused constructed controls: seven passed
and two POSIX positive probe controls were skipped on Windows. Compilation
checks passed for the helper, actor, evaluator, V2 diagnostics, launcher and
tests. The constructed module controls use supplied generic imports and a
socket wrapper without OS bind/connect/listen/send; no original AP2 application
or provider executed locally. Hosted Linux runs the two positive controls
before any actual smoke case. Those controls and all hosted outcomes were
pending at review time.

The fresh-socket witness and cross-receipt counter checks resolve the reviewer's
two early tightening requests. V11's redacted `getaddrinfo` host still does not
reveal its original type or bytes. V12's exact bytes handling is a prospective
policy refinement, not attribution of the historical denial. Frozen V11
evidence and its missing matrix outcomes remain unchanged.

These are the exact reviewed file identities; subsequent source changes require
a fresh review of their differences.

| Reviewed file | Bytes | SHA256 |
| --- | ---: | --- |
| scripts/ap2_native_guard_policy_v12.py | 5,568 | `552c2345f81ed07dc35efeb2ba53f55ff8229d7b383d10bde0dcd6904d89a1ff` |
| scripts/ap2_reference_development_v12.py | 58,142 | `cddfa98e247336e1afa76890a99bdbdf4b8eb54ca8b53639ce0be5aff189aa78` |
| scripts/evaluate_ap2_native_bridge_matrix_v12.py | 61,075 | `50ac4bf1536c577c012aa38330f15bd3734d2cce3557a449fee095f52cef4512` |
| scripts/print_ap2_owned_cell_diagnostics_v2.py | 11,935 | `d5ce3ffe277852ee38de4869cb69419bc89cd53d3ae661329d4d25a0b91ee060` |
| scripts/run_ap2_cell_with_safe_diagnostics_v2.py | 1,583 | `eac79654464ac78d7bcb0a98dcfb44eb23b738835e092da23c881cad551fab23` |
| tests/test_ap2_native_guard_policy_v12.py | 11,111 | `3c802e84659b3836db66bac4bf478cf3809bbb4c6d49e61274b6a94e25443178` |
| .github/workflows/ap2-native-bridge-development-v12.yml | 5,786 | `54fc90e9c51eba8e9c430a981aba6127e048027545469722ae533b5eb3733277` |
| benchmark/ap2-native-bridge-development-v12/application.json | 11,806 | `60fe83f3b8e82a8415a51922ff49f5d1a4c1c15b53a033cc23107fc6f2c938a0` |
| benchmark/ap2-native-bridge-development-v12/evaluator.json | 2,591 | `4243c0f42010628b7540f861b3cf045a52061c52400929082769cc1acbb3fdd3` |

The review authorizes no stronger scientific claim: human gold, full original
server-launch qualification, provider utility, complete bridge continuation
and completion of the original study still require separate evidence.
