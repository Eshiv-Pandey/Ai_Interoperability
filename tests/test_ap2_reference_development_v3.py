"""Software checks for the offline application intervention, no original import."""
import importlib.util
import io
import json
import marshal
from pathlib import Path
import tempfile
from types import CodeType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_ap2_development_v3', ROOT / 'scripts/ap2_reference_development_v3.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class DevelopmentTests(unittest.TestCase):
    def test_recursive_projection_retains_nested_public_models_without_mutating_objects(self):
        class PublicModel:
            def __init__(self, value):
                self.value = value
            def model_dump(self, **options):
                self.options = options
                return self.value
        model = PublicModel({'amount': 12.5, 'currency': 'USD'})
        value = {'carts': [model]}
        result = runner.recursive_public_json(value, model_base=PublicModel)
        self.assertEqual(result, {'carts': [{'amount': 12.5, 'currency': 'USD'}]})
        result['carts'][0]['amount'] = 99
        self.assertEqual(model.value['amount'], 12.5)
        self.assertIs(value['carts'][0], model)
        self.assertEqual(model.options, {'mode': 'json', 'by_alias': True})

    def test_source_address_projection_preserves_explicit_null_and_omits_unset_default(self):
        class PublicAddress:
            def model_dump(self, **options):
                result = {'city': 'Sample', 'country': None}
                if not options.get('exclude_unset'):
                    result['sorting_code'] = None
                return result
        address = PublicAddress()
        self.assertEqual(runner.recursive_public_json(address, model_base=PublicAddress,
                                                      explicitly_set_model=PublicAddress),
                         {'city': 'Sample', 'country': None})
        self.assertEqual(runner.recursive_public_json(address, model_base=PublicAddress),
                         {'city': 'Sample', 'country': None, 'sorting_code': None})

    def test_recursive_projection_refuses_nonfinite_keys_cycles_and_implicit_object_conversion(self):
        values = [float('nan'), float('inf'), {1: 'value'}, (1,), object()]
        cyclic = []
        cyclic.append(cyclic)
        values.append(cyclic)
        for value in values:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    runner.recursive_public_json(value)
        self.assertEqual(runner.recursive_public_json({'integer': 1, 'boolean': True}),
                         {'integer': 1, 'boolean': True})

    def test_unchanged_owned_helper_guards_with_structural_comparison(self):
        spec = importlib.util.spec_from_file_location('_ap2_constructed_legacy_guards',
                                                       ROOT / 'tests/test_ap2_hp_original_bindings_v1.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = module.binding.marshal
        module.binding.marshal = SimpleNamespace(dumps=runner.code_fingerprint)
        try:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(module))
            self.assertEqual(result.testsRun, 22)
            self.assertTrue(result.wasSuccessful(), str(result.failures + result.errors))
        finally:
            module.binding.marshal = original

    def test_imported_docstring_code_equal_despite_noncanonical_marshal(self):
        source = ('def operation(value=True):\n'
                  '    """A constructed imported callable docstring to expose reference memoization."""\n'
                  '    return value\n')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'constructed.py'
            path.write_text(source, encoding='utf-8')
            spec = importlib.util.spec_from_file_location('_constructed_docstring', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            actual = module.operation.__code__
            expected = next(value for value in compile(path.read_bytes(), str(path), 'exec', dont_inherit=True).co_consts
                            if type(value) is CodeType)
            self.assertEqual(actual, expected)
            self.assertNotEqual(marshal.dumps(actual), marshal.dumps(expected))
            self.assertEqual(runner.code_fingerprint(actual), runner.code_fingerprint(expected))

    def test_structural_fingerprint_keeps_filename_name_and_position_identity(self):
        code = compile('def operation():\n    return True\n', 'constructed.py', 'exec', dont_inherit=True).co_consts[0]
        for field, value in [('co_filename', 'other.py'), ('co_name', 'other'), ('co_qualname', 'Other.operation'),
                             ('co_firstlineno', code.co_firstlineno + 1),
                             ('co_exceptiontable', b'\x80\x01\x00\x00')]:
            with self.subTest(field=field):
                self.assertNotEqual(runner.code_fingerprint(code),
                                    runner.code_fingerprint(code.replace(**{field: value})))

    def test_bool_and_integer_constants_are_distinct(self):
        code = compile('def operation():\n    return True\n', 'constructed.py', 'exec', dont_inherit=True).co_consts[0]
        changed = code.replace(co_consts=(None, 1))
        self.assertNotEqual(runner.code_fingerprint(code), runner.code_fingerprint(changed))

    def test_nested_code_tampering_is_rejected(self):
        compiled = compile('def outer():\n    def inner():\n        return True\n    return inner\n',
                           'constructed.py', 'exec', dont_inherit=True)
        outer = next(value for value in compiled.co_consts if type(value) is CodeType)
        child = next(value for value in outer.co_consts if type(value) is CodeType)
        changed_child = child.replace(co_consts=(None, 1))
        changed_outer = outer.replace(co_consts=tuple(changed_child if value is child else value for value in outer.co_consts))
        self.assertNotEqual(runner.code_fingerprint(outer), runner.code_fingerprint(changed_outer))

    def test_instruction_and_argument_or_closure_identity_changes_are_rejected(self):
        compiled = compile('def operation(value, other):\n    return value + other\n',
                           'constructed.py', 'exec', dont_inherit=True)
        code = next(value for value in compiled.co_consts if type(value) is CodeType)
        alternate = next(value for value in compile('def operation(value, other):\n    return value - other\n',
                                                    'constructed.py', 'exec', dont_inherit=True).co_consts
                         if type(value) is CodeType)
        self.assertNotEqual(code.co_code, alternate.co_code)
        changes = [{'co_code': alternate.co_code}, {'co_argcount': 1}, {'co_posonlyargcount': 1},
                   {'co_argcount': 1, 'co_kwonlyargcount': 1}, {'co_stacksize': code.co_stacksize + 1},
                   {'co_flags': code.co_flags ^ 0x40}, {'co_freevars': ('captured',)}]
        for change in changes:
            with self.subTest(change=change):
                self.assertNotEqual(runner.code_fingerprint(code), runner.code_fingerprint(code.replace(**change)))

    def test_code_constant_container_types_and_signed_zero_are_distinct(self):
        self.assertNotEqual(runner.constant_fingerprint((True,)), runner.constant_fingerprint((1,)))
        self.assertNotEqual(runner.constant_fingerprint((1,)), runner.constant_fingerprint(frozenset({1})))
        self.assertNotEqual(runner.constant_fingerprint(0.0), runner.constant_fingerprint(-0.0))
        with self.assertRaisesRegex(ValueError, 'unsupported_code_constant_type'):
            runner.constant_fingerprint([])

    def test_unknown_model_choice_stops_before_fixture_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = runner.OfflineModel(Path(temporary))
            config = SimpleNamespace(tools=[SimpleNamespace(function_declarations=[SimpleNamespace(name='initiate_payment')])])
            with self.assertRaisesRegex(ValueError, 'unknown_or_unoffered'):
                model.generate_content(model=runner.MODEL, contents='Unknown operation', config=config)
            self.assertEqual(model.rows, [])
            self.assertFalse((Path(temporary) / 'model-interventions.jsonl').exists())

    def test_unoffered_choice_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = runner.OfflineModel(Path(temporary))
            config = SimpleNamespace(tools=[SimpleNamespace(function_declarations=[SimpleNamespace(name='other')])])
            with self.assertRaisesRegex(ValueError, 'unknown_or_unoffered'):
                model.generate_content(model=runner.MODEL, contents='Initiate a payment', config=config)

    def test_offline_model_budget_is_global_and_retains_all_allowed_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = runner.OfflineModel(Path(temporary))
            config = SimpleNamespace(tools=[SimpleNamespace(function_declarations=[SimpleNamespace(name='initiate_payment')])])
            for _ in range(24):
                model.generate_content(model=runner.MODEL, contents='Initiate a payment', config=config)
            with self.assertRaisesRegex(ValueError, 'budget_or_identity'):
                model.generate_content(model=runner.MODEL, contents='Initiate a payment', config=config)
            rows = [json.loads(line) for line in (Path(temporary) / 'model-interventions.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 24)
            self.assertTrue(all(row['provider_requests'] == 0 for row in rows))

    def test_wrong_model_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'budget_or_identity'):
                runner.OfflineModel(Path(temporary)).generate_content(model='different-model', contents='', config={})

    def test_inventory_refuses_linked_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'file.txt').write_text('constructed')
            try:
                (root / 'link.txt').symlink_to(root / 'file.txt')
            except OSError:
                self.skipTest('OS does not permit this user to create symlinks')
            with self.assertRaisesRegex(ValueError, 'linked_inventory_entry'):
                runner.inventory(root)


if __name__ == '__main__':
    unittest.main()
