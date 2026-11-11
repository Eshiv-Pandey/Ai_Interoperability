"""Public read controls with retained Tasks; no original/native/model execution."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from ap2_public_control_support_v1 import fixture, sdk_doubles


class PublicTaskReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_sdk_query_preserves_original_task_context_and_extension(self):
        task = fixture("v13-correct-pending-task.json")
        context = SimpleNamespace(state={"initiate_payment_task_id": task["id"], "shopping_context_id": task["contextId"]})
        before = deepcopy(context.state)
        with sdk_doubles(task=task) as (helper, calls):
            observed = await helper.read_public_payment_task(context)
        self.assertEqual(observed["task"], task)
        self.assertEqual(context.state, before)
        self.assertIn(("get_task", task["id"], 100), calls)
        http = next(row[1] for row in calls if row[0] == "http_client")
        self.assertEqual(http["headers"], {"X-A2A-Extensions": "https://github.com/google-agentic-commerce/ap2/v1"})
        self.assertFalse(observed["caller_state_repaired"])

    async def test_mismatched_context_refuses_but_retains_actual_public_task(self):
        task = fixture("v13-correct-pending-task.json")
        other = fixture("v13-wrong-pending-task.json")
        context = SimpleNamespace(state={"initiate_payment_task_id": task["id"], "shopping_context_id": other["contextId"]})
        with sdk_doubles(task=task) as (helper, calls):
            with self.assertRaises(helper.PublicTaskAuthorityError) as caught:
                await helper.read_public_payment_task(context)
        self.assertEqual(caught.exception.public_observation["task"], task)
        self.assertIn(("get_task", task["id"], 100), calls)
        self.assertEqual(context.state["shopping_context_id"], other["contextId"])

    async def test_unconfigured_card_endpoint_is_rejected_before_query(self):
        task = fixture("v13-correct-pending-task.json")
        card = fixture("original-merchant-card.json")
        card["url"] = "http://example.invalid:8001/a2a/merchant_agent"
        context = SimpleNamespace(state={"initiate_payment_task_id": task["id"], "shopping_context_id": task["contextId"]})
        with sdk_doubles(task=task, card=card) as (helper, calls):
            with self.assertRaisesRegex(ValueError, "original merchant endpoint/version"):
                await helper.read_public_payment_task(context)
        self.assertFalse(any(row[0] == "get_task" for row in calls))

    async def test_missing_original_task_authority_does_not_invent_id(self):
        with sdk_doubles() as (helper, calls):
            with self.assertRaisesRegex(ValueError, "caller-held payment task ID"):
                await helper.read_public_payment_task(SimpleNamespace(state={}))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
