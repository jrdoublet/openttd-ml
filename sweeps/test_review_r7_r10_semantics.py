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


def _r10_state(**overrides):
    state = {
        "c72": 0,
        "c104": False,
        "c105": False,
        "c109": False,
        "c111": False,
        "c112": False,
        "c115": False,
    }
    state.update(overrides)
    c72 = state["c72"]
    c104 = state["c104"]
    c105 = state["c105"]
    c109 = state["c109"]
    c111 = state["c111"]
    c112 = state["c112"]
    c115 = state["c115"]

    # All unrelated exclusion flags are fixed false in this directed matrix.
    probe104 = c104 and not c115 and c72 == 0 and not c105 and not c109 and not c111 and not c112
    choose105 = c105 and c72 == 0 and not c109 and not c111 and not c112
    choose109 = c109 and c72 == 0 and not c104 and not c105 and not c111 and not c112
    choose111 = c111 and c72 == 0 and not c104 and not c105 and not c109 and not c112
    choose112 = c112 and c72 == 0 and not c104 and not c105 and not c109 and not c111
    choose115 = c115 and c72 == 0 and not c105 and not c109 and not c111 and not c112
    physical_timing = c105 or c109 or c112
    active = [name for name, enabled in (
        ("c105", choose105), ("c109", choose109), ("c111", choose111),
        ("c112", choose112), ("c115", choose115),
    ) if enabled]
    return {"probe104": probe104, "active": active, "physical_timing": physical_timing}


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
    def test_live_source_contains_the_matrix_gates_and_global_timing(self):
        self.assertIn("if (C104_AIR_C100_COMPARE_PROBE && !C115_AIR_C100_CAPITAL_REPLAY", AIR)
        self.assertIn("if (C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0", AIR)
        self.assertIn("if (C109_AIR_SPEED_ELASTICITY_PHYSICAL && C72_PLANE_CHOICE == 0", AIR)
        self.assertIn("if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0", AIR)
        self.assertIn("if (C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL && C72_PLANE_CHOICE == 0", AIR)
        self.assertIn("if (C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0", AIR)
        self.assertIn("C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS", AIR)
        self.assertIn("C109_AIR_SPEED_ELASTICITY_PHYSICAL", AIR)
        self.assertIn("C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL", AIR)

    def test_c72_masks_new_choosers_but_c105_timing_remains_global(self):
        c115 = _r10_state(c72=1, c115=True)
        self.assertEqual(c115["active"], [])
        self.assertFalse(c115["physical_timing"])

        c105 = _r10_state(c72=1, c105=True)
        self.assertEqual(c105["active"], [])
        self.assertTrue(c105["physical_timing"])

    def test_standalone_controls_activate_exactly_one_expected_path(self):
        self.assertEqual(_r10_state(c105=True)["active"], ["c105"])
        self.assertEqual(_r10_state(c109=True)["active"], ["c109"])
        self.assertEqual(_r10_state(c111=True)["active"], ["c111"])
        self.assertEqual(_r10_state(c112=True)["active"], ["c112"])
        self.assertEqual(_r10_state(c115=True)["active"], ["c115"])
        self.assertTrue(_r10_state(c104=True)["probe104"])

    def test_c104_is_mutually_exclusive_with_c109_c111_c112(self):
        for flag in ("c109", "c111", "c112"):
            state = _r10_state(c104=True, **{flag: True})
            self.assertFalse(state["probe104"], flag)
            self.assertEqual(state["active"], [], flag)

    def test_c104_and_default_c115_are_also_mutually_exclusive(self):
        state = _r10_state(c104=True, c115=True)
        self.assertFalse(state["probe104"])
        self.assertEqual(state["active"], ["c115"])


if __name__ == "__main__":
    unittest.main()
