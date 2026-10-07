"""R4: evaluate the extracted admission expression, plus source wiring checks.

This is NOT a Squirrel interpreter or a measurement of actual NoAI opcodes.
Only constants, boolean conjunctions and comparisons in the real predicate are
translated; unknown syntax fails closed instead of running arbitrary source.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class TestCatalogContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (AI / "main.nut").read_text(encoding="utf-8")
        cls.scheduler = (AI / "scheduler_tasks.nut").read_text(encoding="utf-8")
        cls.predicate = cls.scheduler.split("function OpexC121CatalogCanContinue(", 1)[1].split("\n}", 1)[0]

    def admit(self, *, ops=9000, tick=12, start=12, enabled=True,
              worker=None, search=None, expansion=None):
        expression = re.search(r"return\s+(.*?);", self.predicate, re.S).group(1)
        for symbol, value in {
            "C121_CATALOG_INCREMENTAL": enabled,
            "owner._activeWorker": worker,
            "owner._railSearch": search,
            "owner._railExpansion": expansion,
            "AIController.GetTick()": tick,
            "AIController.GetOpsTillSuspend()": ops,
            "continuationTick": start,
            "null": None,
        }.items():
            expression = expression.replace(symbol, repr(value))
        expression = " ".join(expression.replace("&&", " and ").split())
        tree = ast.parse(expression, mode="eval")
        allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Compare,
                   ast.Eq, ast.Gt, ast.Constant)
        self.assertTrue(all(isinstance(node, allowed) for node in ast.walk(tree)))
        return eval(compile(tree, "<C121 admission expression>", "eval"), {"__builtins__": {}})

    def test_normal_tick_has_reachable_admission_and_low_budget_stops(self):
        for ops, expected in ((0, False), (1999, False), (2000, False),
                              (2001, True), (9000, True), (10000, True)):
            with self.subTest(ops=ops):
                self.assertEqual(self.admit(ops=ops), expected)

    def test_workers_and_rail_work_exclude_direct_continuation(self):
        for key in ("worker", "search", "expansion"):
            with self.subTest(key=key):
                self.assertFalse(self.admit(**{key: 1}))

    def test_refilled_budget_after_suspend_does_not_extend_chain(self):
        self.assertFalse(self.admit(tick=13, start=12, ops=10000))
        self.assertTrue(self.admit(tick=13, start=13, ops=9000))

    def test_feature_off_never_enters_continuation(self):
        self.assertFalse(self.admit(enabled=False))

    def test_both_dispatch_paths_capture_tick_and_keep_task_alternation(self):
        self.assertEqual(self.main.count("local continuationTick = AIController.GetTick();"), 1)
        self.assertEqual(self.main.count("while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick))"), 1)
        self.assertEqual(self.main.count("this._dispatchCatalog(queuedTask,"), 1)
        self.assertIn("if (catalogPending) this._runOrchestratorTick();", self.main)
        self.assertEqual(self.main.count('queuedTask.c78AirRebuild != null'), 1)
        self.assertNotIn("GetOpsTillSuspend() > 10000", self.main)

    def test_slice_still_uses_live_budget_and_resumable_cursor(self):
        self.assertIn("local liveOps = AIController.GetOpsTillSuspend();", self.scheduler)
        self.assertIn("local sliceBudget = liveOps;", self.scheduler)
        self.assertIn("if (sliceBudget > AIR_PLAN_SLICE_OPS)", self.scheduler)
        self.assertIn("s.band, -1, s.cursor,", self.scheduler)
        self.assertIn("OpexC78RequeueInitialCatalogSlice(owner, task);", self.scheduler)
        self.assertIn("this._processEvents();", self.main)


if __name__ == "__main__":
    unittest.main()