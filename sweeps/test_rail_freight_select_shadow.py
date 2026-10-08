"""Static invariants for the optional freight selection diagnostic."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class FreightSelectionShadowContract(unittest.TestCase):
    def test_default_off_and_explicit_settings(self):
        settings = (ROOT / "settings.nut").read_text(encoding="utf-8")
        info = (ROOT / "info.nut").read_text(encoding="utf-8")
        globals_pre = (ROOT / "globals_pre.nut").read_text(encoding="utf-8")
        self.assertIn("RAIL_FREIGHT_SELECT_SHADOW <- false;", globals_pre)
        self.assertIn('RAIL_FREIGHT_SELECT_SHADOW = AIController.GetSetting("rail_freight_select_shadow") != 0;', settings)
        cfg = info.split('name = "rail_freight_select_shadow",', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(cfg, rf"\b{difficulty}_value\s*=\s*0\b")

    def test_scan_and_log_are_only_called_under_guard(self):
        source = (ROOT / "projects_selection.nut").read_text(encoding="utf-8")
        self.assertRegex(source, r"if \(RAIL_FREIGHT_SELECT_SHADOW && realSelection\)\s+OpexRailFreightSelectShadow\(")
        self.assertIn("function OpexProjectSelectAffordable(alternatives, capitalBudget, limit, realSelection = true)", source)
        self.assertEqual(source.count("OpexRailFreightSelectShadow(alternatives, affordable,"), 1)
        diagnostic = (ROOT / "projects_diagnostics.nut").read_text(encoding="utf-8")
        self.assertRegex(diagnostic, r"OpexProjectSelectAffordable\(\s*liveAlternatives, liveBudget, PORTFOLIO_MAX_BATCH, false\)")
        method = source.split("function OpexRailFreightSelectShadow(", 1)[1].split(
            "function OpexProjectSelectionScore(", 1)[0]
        self.assertIn("foreach (p in alternatives)", method)
        self.assertIn("foreach (p in selected)", method)
        self.assertIn('p.kind == "freight"', method)
        self.assertIn('("dstTown" in p.payload)', method)
        self.assertIn('AILog.Info("RAIL_FREIGHT_SELECT_SHADOW', method)
        for field in ("total_f=", "cash_f=", "floor_f=", "eligible_f=", "selected_f=",
                      "head_tier=", "head_mode=", "best_f_score="):
            self.assertIn(field, method)


if __name__ == "__main__":
    unittest.main()
