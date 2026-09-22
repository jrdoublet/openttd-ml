"""Contrats de fusion : les correctifs de sauvegarde C69 et C76 coexistent."""
from pathlib import Path
import unittest
from test_c45_subsidy_persistence import function_body


class TestC69ReloadContract(unittest.TestCase):
    def test_saved_dates_survive_line_projection_change(self):
        root = Path(__file__).resolve().parents[1] / "ai/OpexAI"
        text = (root / "persist.nut").read_text(encoding="utf-8")
        save = function_body(text, "function OpexAI::Save()")
        load = function_body(text, "function OpexAI::Load(version, data)")
        reconcile = function_body(text, "function OpexAI::_reconcileAfterLoad()")
        for prefix in ("C69Build", "C75Pass"):
            key = prefix[0].lower() + prefix[1:] + "Dates"
            field = "_reload" + prefix + "Dates"
            self.assertIn(key + " = ", save)
            self.assertIn("this." + field, load)
            self.assertIn("this." + field, reconcile)
        self.assertLess(load.index("if (data == null) return;"), load.index('"c69BuildDates" in data'))
        self.assertIn("OpexC70RecomputeFactors(this._lines)", reconcile)
        self.assertNotIn("needsProjection", save)
        self.assertIn("saveLines = projectedLines;", save)

    def test_c80_restore_does_not_require_unloaded_settings(self):
        text = (Path(__file__).resolve().parents[1] / "ai/OpexAI/persist.nut").read_text(encoding="utf-8")
        load = function_body(text, "function OpexAI::Load(version, data)")
        self.assertNotIn("if (C80_DOUBLE_REGISTER)", load)
        self.assertIn("OpexLoadReactiveQueue(data.c80ReactiveQueue)", load)
        self.assertIn("OpexLoadActiveWorker(data.c80ActiveWorker)", load)
