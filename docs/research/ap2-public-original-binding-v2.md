# AP2 public caller structural source binding V2

Prepared 2026-11-11. This is a prospective owned verifier/caller correction.
No original AP2 application, SDK, business function or model was imported or
executed for these controls. The V1 sources and all five retained failed V1
attempts remain unchanged.

The retained V1 caller failed before business execution because the owned
source binder compared `marshal.dumps` of loaded and freshly compiled code.
Marshal's object-reference memoization can differ for equal code constants;
that byte difference does not establish a source-body difference. The actual
V1 result and limits are documented separately in
`docs/research/ap2-original-native-provider-results-v1.md`.

`src/interoperability/ap2_public_original_binding_v2.py` copies the existing
compile-only module, source-origin, function-type/globals, class/member,
decorator and typed-default checks. It replaces the marshal comparison with
the established V13 `CODE_FIELDS` recipe: all listed code identity fields,
recursively typed constants, `co_lines()` and `co_positions()`. Filenames,
opcodes, argument/local/stack/flag metadata, names, free/cell variables, line and
exception tables remain part of the comparison. Float and complex components
use exact IEEE bytes (`struct.pack('!d', value)`), preserving signed zero and
NaN sign/payload distinctions.

`src/interoperability/ap2_public_scripted_continuation_v2.py` changes the binder
import and treatment schema; its business sequence and public-read behavior
come from V1. `scripts/ap2_public_scripted_continuation_v2.py` imports that new
caller and retains the new verifier among its owned sources. The unchanged
`ap2_public_task_read_v1.py` remains explicitly pinned. Original business-source
bytes and loaded bodies are still checked before the caller is constructed.

All **32 constructed binder controls passed**, including a module whose code
has unequal marshal bytes solely from constant-reference sharing, plus refusal
of opcode, literal/nested constant, filename/position/table/metadata, default,
decorator, class footprint and module-origin changes. Float/complex signed-zero
and NaN bit controls pass. These controls execute constructed fixture
definitions only; they establish owned verifier behavior, not native task or
provider qualification. The preserved 14 public-caller controls and companion
V2 provider runner controls remain separate checks.

Command:

```text
python -B -m unittest discover -s tests -p test_ap2_public_original_binding_v2.py
```

Stable source SHA256 values:

| File | SHA256 |
| --- | --- |
| `scripts/ap2_public_scripted_continuation_v2.py` | `06a2bcf732cacc042180e6d5d89f64a54efd1d4fd9789621c906eae7cbdf6954` |
| `src/interoperability/ap2_public_scripted_continuation_v2.py` | `afc3f0a010b83eb516d59c329811aaa257f8d8973205c4428b08bb6770fd9048` |
| `src/interoperability/ap2_public_original_binding_v2.py` | `f5ecd810445c445b19cd6ce2cb99f714d47f137895b96a68b8c56c2d9cfc0787` |
| `src/interoperability/ap2_public_task_read_v1.py` | `feaa86eb5ec62d1627a0d7e0744bd8a626e3f597a7a2012e7f8eb0a80dbf0c46` |
| `tests/test_ap2_public_original_binding_v2.py` | `e5b50878b8e9a8b1fc549b08221cf3ef2d2fa4f11a9ba7c86c0c3a31d7c7055a` |

Actual original/native/provider outcomes require a separately frozen V2
allocation and retained execution. These controls do not retroactively qualify
V1, the original ADK root tool surface, independent bridges, human gold or the
held-out study.
