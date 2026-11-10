"""Software checks for the offline application intervention, no original import."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_ap2_development_v3', ROOT / 'scripts/ap2_reference_development_v3.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class DevelopmentTests(unittest.TestCase):
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
