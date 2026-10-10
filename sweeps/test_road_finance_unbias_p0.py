"""P0 ROAD 121%%: isolated admission capital, never construction or risk."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(filename):
    return (AI / filename).read_text(encoding="utf-8")


class RoadFinanceUnbiasContracts(unittest.TestCase):
    def test_setting_is_off_for_all_difficulties(self):
        info = src("info.nut")
        for setting in ("road_finance_unbias_p0", "road_finance_gate_shadow_p0"):
            match = re.search(rf'name = "{setting}",(.*?)\}}\);', info, re.S)
            self.assertIsNotNone(match)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(match.group(1), rf"\b{key}\s*=\s*0\b")
        self.assertIn(
            'ROAD_FINANCE_UNBIAS_P0 = AIController.GetSetting("road_finance_unbias_p0") != 0;',
            src("settings.nut"),
        )
        self.assertIn(
            'ROAD_FINANCE_GATE_SHADOW_P0 = AIController.GetSetting("road_finance_gate_shadow_p0") != 0;',
            src("settings.nut"),
        )

    def test_only_road_finance_bias_switches(self):
        finance = src("projects_finance.nut")
        self.assertIn('if (CAPITAL_QUOTE_LEARNING) return OpexCapitalQuoteFinance(', finance)
        self.assertIn('if (!CAPITAL_CALIBRATION || !("mode" in project)) return financeCapital;', finance)
        self.assertIn('if (project.mode == "rail") biasPct = RAIL_FINANCE_BIAS_PCT;', finance)
        self.assertIn('else if (project.mode == "road") biasPct = 121;', finance)
        self.assertIn('if (project.mode == "road" && ROAD_FINANCE_UNBIAS_P0) biasPct = 100;', finance)
        self.assertLess(finance.index('if (capitalIsActual) return capital + nonConstructionCapital;'),
                        finance.index('return ((capital * biasPct) / 100) + nonConstructionCapital;'))
        self.assertIn('financeCapital - modelCapital', finance)

    def test_road_build_cash_gate_does_not_change(self):
        task = src("task_road.nut")
        self.assertIn('candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN', task)
        self.assertNotIn('if (ROAD_FINANCE_UNBIAS_P0)', task)
        self.assertNotIn("road_finance_unbias_p0", src("capital_quote_learning.nut"))
        self.assertIn('ROAD_FINANCE_POSTPLAN_P0 date=', task)
        self.assertIn('ROAD_FINANCE_BUILD_P0 date=', task)

    def test_shadow_is_passive_and_compares_same_candidates(self):
        selection = src("projects_selection.nut")
        self.assertIn('ROAD_FINANCE_GATE_SHADOW_P0 && realSelection', selection)
        self.assertIn('legacyNeed > capitalBudget && physicalNeed <= capitalBudget', selection)
        self.assertIn('ROAD_FINANCE_P0 date=', selection)
        self.assertIn('eligible121=', selection)
        self.assertIn('eligible100=', selection)
        self.assertIn('unlocked=', selection)
        self.assertIn('ROAD_FINANCE_UNLOCK_P0 date=', selection)
        self.assertIn('in_top=', selection)

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
