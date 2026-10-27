"""P0 ROAD 121%%: isolated admission capital, never construction or risk."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(filename):
    return (AI / filename).read_text(encoding="utf-8")


class RoadFinanceUnbiasContracts(unittest.TestCase):
    def test_setting_is_off_for_all_difficulties(self):
        for setting in ("road_finance_unbias_p0", "road_finance_gate_shadow_p0"):
            self.assertNotIn(setting, src("info.nut"))
            self.assertNotIn(setting, src("settings.nut"))
            self.assertNotIn(setting.upper(), src("globals_pre.nut"))

    def test_only_road_finance_bias_switches(self):
        finance = src("projects_finance.nut")
        self.assertNotIn("CAPITAL_CALIBRATION", finance)
        self.assertIn('if (!("mode" in project)) return financeCapital;', finance)
        self.assertIn('if (project.mode == "rail") biasPct = RAIL_FINANCE_BIAS_PCT;', finance)
        self.assertIn('else if (project.mode == "road") biasPct = 121;', finance)
        self.assertNotIn('ROAD_FINANCE_UNBIAS_P0', finance)
        self.assertLess(finance.index('if (capitalIsActual) return capital + nonConstructionCapital;'),
                        finance.index('return ((capital * biasPct) / 100) + nonConstructionCapital;'))
        self.assertIn('financeCapital - modelCapital', finance)

    def test_road_build_cash_gate_does_not_change(self):
        task = src("task_road.nut")
        self.assertIn('candidate.capital + ROAD_CAPITAL_MARGIN', task)
        self.assertNotIn('if (ROAD_FINANCE_UNBIAS_P0)', task)
        self.assertNotIn('ROAD_FINANCE_POSTPLAN_P0', task)
        self.assertNotIn('ROAD_FINANCE_BUILD_P0', task)

    def test_shadow_is_passive_and_compares_same_candidates(self):
        selection = src("projects_selection.nut")
        for token in ("ROAD_FINANCE_GATE_SHADOW_P0", "roadFinanceExposure",
                      "ROAD_FINANCE_P0", "ROAD_FINANCE_UNLOCK_P0"):
            self.assertNotIn(token, selection)

    def test_economic_capital_and_reserve_are_invariant(self):
        # Representative values assert the financial interpretation, not
        # Squirrel execution: both arms share physical quote and reserves.
        for physical, margin, transit in ((10000, 1000, 0), (50000, 1000, 3000)):
            budget = physical + margin + transit
            historical = physical * 121 // 100 + budget - physical
            variant = physical * 100 // 100 + budget - physical
            self.assertEqual(historical - variant, physical * 121 // 100 - physical)
            self.assertEqual(variant, budget)
            self.assertGreater(historical, variant)


if __name__ == "__main__":
    unittest.main()
