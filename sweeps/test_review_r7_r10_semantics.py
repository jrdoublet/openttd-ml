from __future__ import annotations

import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from air_source import read_builder_air  # noqa: E402
from opex_projects_source import read_projects_source  # noqa: E402


AIR = read_builder_air()
PROJECTS = read_projects_source()
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


def _r7_admitted(profit: int, tier: int, defensive: bool, floor_profit: int = 0) -> bool:
    """Fixed-context transcription of the R7 floor arithmetic only."""
    effective_floor = floor_profit
    if defensive:
        if tier >= 2:
            effective_floor = floor_profit // 2
        elif tier == 1:
            effective_floor = floor_profit * 3 // 4
    return profit >= effective_floor



class ReviewR7SemanticsTest(unittest.TestCase):
    def test_live_source_still_forces_zero_floor_and_keeps_tier_formula(self):
        self.assertIn("PORTFOLIO_FLOOR_PCT = 0;", SETTINGS)
        self.assertIn("if (c121DefensiveTier >= 2) c121DefensiveFloor = floorProfit / 2;", PROJECTS)
        self.assertIn("else if (c121DefensiveTier == 1) c121DefensiveFloor = floorProfit * 3 / 4;", PROJECTS)
        self.assertIn("if (project.profitAnnual < c121DefensiveFloor", PROJECTS)

    def test_zero_floor_makes_positive_tiers_identical_but_still_rejects_negative(self):
        cases = [(2, 900), (1, 700), (0, 500), (0, -1)]
        off = [_r7_admitted(profit, tier, False, 0) for tier, profit in cases]
        on = [_r7_admitted(profit, tier, True, 0) for tier, profit in cases]
        self.assertEqual(off, [True, True, True, False])
        self.assertEqual(on, off)

    def test_nonzero_counterfactual_keeps_documented_50_75_100_percent_tiers(self):
        floor = 100
        self.assertTrue(_r7_admitted(50, 2, True, floor))
        self.assertFalse(_r7_admitted(49, 2, True, floor))
        self.assertTrue(_r7_admitted(75, 1, True, floor))
        self.assertFalse(_r7_admitted(74, 1, True, floor))
        self.assertTrue(_r7_admitted(100, 0, True, floor))
        self.assertFalse(_r7_admitted(99, 0, True, floor))


class ReviewR10CompositionTest(unittest.TestCase):
    def test_live_source_keeps_the_c115_gate(self):
        self.assertIn("if (C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0", AIR)

if __name__ == "__main__":
    unittest.main()
