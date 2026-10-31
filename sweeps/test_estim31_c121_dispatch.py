"""ESTIM-C121: untouched historical chooser, separate exhaustive opt-in.

The upperScore of a single aircraft cannot bound the multi-aircraft calibrated
decision score.  The ESTIM chooser must not use it to stop scanning.
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
BAD_BREAK = "if (best != null && candidate.upperScore < best.economics.decisionScore) break;"


class C121DispatchContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (AI / "air_economics_c121.nut").read_text(encoding="utf-8")
        cls.settings = (AI / "settings.nut").read_text(encoding="utf-8")
        cls.globals = (AI / "globals_pre.nut").read_text(encoding="utf-8")

    def test_historical_chooser_and_fallback_preserved(self):
        source = self.source.split("/* ESTIM C121 experimental full-scan functions. */", 1)
        self.assertEqual(len(source), 2)
        historical, experimental = source
        self.assertEqual(historical.count(BAD_BREAK), 2)
        self.assertEqual(experimental.count(BAD_BREAK), 0)
        self.assertIn("function OpexC121ChooseRoutePlane(", historical)
        self.assertIn("function OpexC121ScanRoutePlaneEngines(", historical)

    def test_experimental_scans_can_not_prune_by_unproven_bound(self):
        experimental = self.source.split("/* ESTIM C121 experimental full-scan functions. */", 1)[1]
        self.assertIn("function OpexC121ChooseRoutePlaneFullScan(", experimental)
        self.assertIn("function OpexC121ScanRoutePlaneEnginesFullScan(", experimental)
        self.assertNotIn("candidate.upperScore < best.economics.decisionScore", experimental)
        self.assertIn("best = OpexC121ScanRoutePlaneEnginesFullScan(catalog, plan);", experimental)
        self.assertIn("OpexC121EngineEconomics", experimental)

    def test_dispatch_is_opt_in_and_not_in_historical_loop(self):
        self.assertIn('ESTIM_UNIFIE <- 0;', self.globals)
        self.assertIn('ESTIM_UNIFIE = AIController.GetSetting("estim_unifie");', self.settings)
        self.assertIn('if ((ESTIM_UNIFIE & 1) != 0)\n    ::OpexC121ChooseRoutePlane <- OpexC121ChooseRoutePlaneFullScan;', self.settings)
        self.assertEqual(self.settings.count("::OpexC121ChooseRoutePlane <-"), 1)

    def test_scanned_score_tiebreak_contract_preserved(self):
        text = self.source.split("/* ESTIM C121 experimental full-scan functions. */", 1)[1]
        self.assertEqual(text.count("economics.decisionScore > best.economics.decisionScore"), 2)
        self.assertIn("economics.decisionProfitAnnual > best.economics.decisionProfitAnnual", text)
        self.assertIn("plane.id < best.plane.id", text)


if __name__ == "__main__":
    unittest.main()
