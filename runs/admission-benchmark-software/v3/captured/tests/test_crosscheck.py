"""Exhaustive tiny-model validation, not a statistical benchmark sample."""

import copy
import itertools
import unittest

from interoperability import baseline, oracle
from test_baseline import tiny_model


class IndependentCrosscheck(unittest.TestCase):
    def test_all_two_state_graphs_three_valued_predicates_and_bounds(self):
        # 16 edge sets x 9 safety assignments x 9 goal assignments x 4 bounds
        # x 2 completeness assumptions = 10,368 fully enumerated finite worlds.
        values = (True, False, None)  # None sentinel omits field: unknown, not JSON null.
        combinations = 0
        for mask, safety, goals, horizon, complete in itertools.product(
            range(16), itertools.product(values, repeat=2), itertools.product(values, repeat=2),
            range(4), (True, False),
        ):
            model = tiny_model()
            model["horizon"] = horizon
            model["evidence"]["complete"] = complete
            model["initial"] = "s0"
            model["states"] = {
                f"s{i}": {key: val for key, val in (("safe", safety[i]), ("done", goals[i])) if val is not None}
                for i in range(2)
            }
            model["transitions"] = [
                {"id": f"e{i}", "source": f"s{i // 2}", "target": f"s{i % 2}", "operation": "step"}
                for i in range(4) if mask & (1 << i)
            ]
            result = baseline.evaluate(model, 20)
            reference = oracle.evaluate(model, 20)
            self.assertEqual(result["decision"], reference["decision"], (mask, safety, goals, horizon, complete))
            if result["decision"] != "unknown":
                self.assertTrue(oracle.check_certificate(model, result, 20), (mask, safety, goals, horizon, complete))
                self.assertTrue(oracle.check_certificate(model, reference, 20))
            combinations += 1
        self.assertEqual(combinations, 10368)

    def test_rejects_mutated_binding_and_omitted_cut_state(self):
        model = tiny_model()
        result = baseline.evaluate(model, 20)
        changed = copy.deepcopy(model)
        changed["states"]["end"]["done"] = False
        self.assertFalse(oracle.check_certificate(changed, result, 20))
        changed["states"]["start"]["done"] = False
        negative = baseline.evaluate(changed, 20)
        negative["certificate"]["layers"][1] = []
        self.assertFalse(oracle.check_certificate(changed, negative, 20))


if __name__ == "__main__":
    unittest.main()
