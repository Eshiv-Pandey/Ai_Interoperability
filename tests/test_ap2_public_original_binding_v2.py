"""Constructed compile-only binder controls; no original AP2/SDK/model imports."""
from contextlib import contextmanager
import importlib.util
import marshal
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from types import CodeType, FunctionType, ModuleType
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("constructed_binding_v2", ROOT / "src/interoperability/ap2_public_original_binding_v2.py")
BINDER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BINDER)


@contextmanager
def constructed_module(source):
    with TemporaryDirectory() as temp:
        path = Path(temp).resolve() / "constructed.py"
        raw = source.encode()
        path.write_bytes(raw)
        name = "constructed_original_source_binding_v2"
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__spec__ = importlib.util.spec_from_file_location(name, path)
        # Execute definitions in a constructed fixture only. No inspected
        # original module or original business function is executed.
        exec(compile(raw, str(path), "exec", dont_inherit=True, optimize=0), module.__dict__)
        with patch.dict(sys.modules, {name: module}):
            yield module, name, path, raw


SOURCE = "def target(first=7, *, label='x'):\n    try:\n        marker = (1.25, 'memo-shared-value')\n        return first, label, marker\n    except Exception:\n        return None\n"


def target_code():
    compiled = compile(SOURCE, "constructed-code-field-control.py", "exec", dont_inherit=True, optimize=0)
    return next(value for value in compiled.co_consts if type(value) is CodeType)


class OriginalBindingV2Tests(unittest.TestCase):
    def test_exact_constructed_module_is_accepted(self):
        with constructed_module(SOURCE) as values:
            BINDER.verify_module(*values)

    def test_marshal_reference_sharing_difference_is_structurally_equal_and_accepted(self):
        source = "def target():\n    return ('memo-shared-value', 'memo-shared-value')\n"
        with constructed_module(source) as (module, name, path, raw):
            original = module.target.__code__
            first = bytearray(b"memo-shared-value").decode()
            second = bytearray(b"memo-shared-value").decode()
            self.assertIsNot(first, second)
            changed = original.replace(co_consts=(None, (first, second)))
            self.assertNotEqual(marshal.dumps(original), marshal.dumps(changed))
            self.assertEqual(BINDER.code_fingerprint(original), BINDER.code_fingerprint(changed))
            module.target.__code__ = changed
            BINDER.verify_module(module, name, path, raw)

    def test_changed_nested_code_body_is_refused(self):
        source = "def target():\n    def child():\n        return 1\n    return child\n"
        with constructed_module(source) as (module, name, path, raw):
            code = module.target.__code__
            child = next(value for value in code.co_consts if type(value) is CodeType)
            changed_child = child.replace(co_consts=(None, 2))
            module.target.__code__ = code.replace(co_consts=tuple(changed_child if value is child else value for value in code.co_consts))
            with self.assertRaises(BINDER.BindingError):
                BINDER.verify_module(module, name, path, raw)

    def test_changed_literal_constant_is_refused_by_module_verifier(self):
        with constructed_module("def target():\n    return 1250\n") as (module, name, path, raw):
            module.target.__code__ = module.target.__code__.replace(co_consts=(None, 1251))
            with self.assertRaisesRegex(BINDER.BindingError, "callable code differs"):
                BINDER.verify_module(module, name, path, raw)

    def test_positional_default_type_change_is_refused(self):
        with constructed_module(SOURCE) as (module, name, path, raw):
            module.target.__defaults__ = (True,)
            with self.assertRaisesRegex(BINDER.BindingError, "positional defaults"):
                BINDER.verify_module(module, name, path, raw)

    def test_keyword_default_change_is_refused(self):
        with constructed_module(SOURCE) as (module, name, path, raw):
            module.target.__kwdefaults__ = {"label": "changed"}
            with self.assertRaisesRegex(BINDER.BindingError, "keyword defaults"):
                BINDER.verify_module(module, name, path, raw)

    def test_callable_globals_replacement_is_refused(self):
        with constructed_module(SOURCE) as (module, name, path, raw):
            module.target = FunctionType(module.target.__code__, dict(module.__dict__), argdefs=(7,))
            with self.assertRaisesRegex(BINDER.BindingError, "globals/function identity"):
                BINDER.verify_module(module, name, path, raw)

    def test_module_origin_change_is_refused(self):
        with constructed_module(SOURCE) as (module, name, path, raw):
            module.__spec__.origin = str(path.parent)
            with self.assertRaises(BINDER.BindingError):
                BINDER.verify_module(module, name, path, raw)

    def test_decorator_is_not_silently_unwrapped(self):
        source = "def identity(value):\n    return value\n@identity\ndef target():\n    return 1\n"
        with constructed_module(source) as values:
            with self.assertRaisesRegex(BINDER.BindingError, "decorator"):
                BINDER.verify_module(*values)

    def test_class_member_footprint_change_is_refused(self):
        with constructed_module("class Box:\n    def method(self):\n        return 1\n") as (module, name, path, raw):
            module.Box.extra = "unexpected"
            with self.assertRaisesRegex(BINDER.BindingError, "member footprint"):
                BINDER.verify_module(module, name, path, raw)

    def test_float_nan_payload_and_sign_changes_are_distinct(self):
        values = [struct.unpack("!d", bytes.fromhex(raw))[0] for raw in
                  ("7ff8000000000001", "fff8000000000001", "7ff8000000000002")]
        self.assertEqual(len({BINDER.constant_fingerprint(value) for value in values}), 3)

    def test_float_negative_zero_is_distinct(self):
        self.assertNotEqual(BINDER.constant_fingerprint(0.0), BINDER.constant_fingerprint(-0.0))

    def test_complex_nan_and_signed_zero_components_are_distinct(self):
        positive_nan = struct.unpack("!d", bytes.fromhex("7ff8000000000001"))[0]
        negative_nan = struct.unpack("!d", bytes.fromhex("fff8000000000001"))[0]
        self.assertNotEqual(BINDER.constant_fingerprint(complex(positive_nan, 0.0)),
                            BINDER.constant_fingerprint(complex(negative_nan, 0.0)))
        self.assertNotEqual(BINDER.constant_fingerprint(complex(1.0, 0.0)),
                            BINDER.constant_fingerprint(complex(1.0, -0.0)))

    def test_typed_constant_change_is_distinct(self):
        self.assertNotEqual(BINDER.constant_fingerprint(1), BINDER.constant_fingerprint(True))

    def test_v2_caller_uses_new_binder_and_retains_v1_public_read(self):
        caller = (ROOT / "src/interoperability/ap2_public_scripted_continuation_v2.py").read_text()
        self.assertIn("from .ap2_public_original_binding_v2 import verify_module", caller)
        self.assertIn("from .ap2_public_task_read_v1 import read_public_payment_task", caller)
        self.assertNotIn("from .ap2_hp_original_binding_v1 import verify_module", caller)


def field_control(field):
    def test(self):
        original = target_code()
        value = getattr(original, field)
        if field in {"co_argcount", "co_kwonlyargcount", "co_stacksize", "co_firstlineno"}:
            changed = original.replace(**{field: value + 1})
        elif field == "co_posonlyargcount":
            changed = original.replace(co_posonlyargcount=1)
        elif field == "co_nlocals":
            changed = original.replace(co_nlocals=value + 1, co_varnames=original.co_varnames + ("additional",))
        elif field == "co_flags":
            changed = original.replace(co_flags=value ^ 0x100)
        elif field in {"co_code", "co_linetable", "co_exceptiontable"}:
            changed = original.replace(**{field: value + b"\x09\x00"})
        elif field in {"co_names", "co_freevars", "co_cellvars"}:
            changed = original.replace(**{field: value + ("changed",)})
        elif field == "co_varnames":
            changed = original.replace(co_varnames=("changed",) + value[1:])
        else:
            changed = original.replace(**{field: value + "-changed"})
        self.assertNotEqual(BINDER.code_fingerprint(original), BINDER.code_fingerprint(changed))
    return test


for field in BINDER.CODE_FIELDS:
    setattr(OriginalBindingV2Tests, "test_changed_" + field + "_is_refused_by_fingerprint", field_control(field))


if __name__ == "__main__":
    unittest.main()
