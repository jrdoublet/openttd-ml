"""RAIL-CAL-1 ranking-only implementation contracts and independent transcription."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
COST_A = 1.062686150395
COST_B = 0.003008780074
PROFIT = {
    "COAL": [0.8442, 1.1066, 1.3735, 1.4834],
    "GOOD": [0.8546, 1.2900, 1.2912, 1.4259],
    "GRAI": [1.0015, 1.1159, 1.3087, 1.3803],
    "IORE": [0.9875, 1.1785, 1.2944, 1.4475],
    "LVST": [1.0597, 1.0690, 1.3980, 1.5792],
    "OIL_": [0.8823, 1.0358, 1.0943, 1.3488],
    "PASS": [0.6692, 0.8194, 1.1796, 1.4225],
    "STEL": [1.1237, 1.1145, 1.2912, 1.4225],
    "VALU": [0.7410, 1.1077, 1.3316, 1.4746],
    "WOOD": [0.9116, 1.1280, 1.3689, 1.3862],
}
FALLBACK = [0.905527, 1.114477, 1.291211, 1.422478]


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def factor(label, dist):
    q = 0 if dist <= 90 else 1 if dist <= 127 else 2 if dist <= 172 else 3
    return PROFIT.get(label, FALLBACK)[q]


def score(mode, actual, label, distance, value, finance, kdec, enabled, fleet_exempt=False):
    """Straight transcription of the new score-only gate; does not mutate inputs."""
    if enabled and mode == "rail" and not actual:
        d = max(0, distance)
        return max(0.0, 1000.0 * value * factor(label, distance)
                   / max(kdec if not fleet_exempt else 0, finance * (COST_A + COST_B * d)))
    denom = max(kdec if not fleet_exempt else 0, finance)
    return max(0.0, 1000.0 * value / denom) if denom and value > 0 else 0.0


class TestRailCal(unittest.TestCase):
    def test_setting_default_zero_all_profiles_and_single_load(self):
        info = source("info.nut")
        block = re.search(r'name = "rail_cal",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertRegex(block.group(1), r"default_value\s*=\s*0\b")
        self.assertIn("RAIL_CAL <- 0;", source("globals_pre.nut"))
        self.assertEqual(source("settings.nut").count('GetSetting("rail_cal")'), 1)

    def test_only_rail_ranking_is_changed_and_physical_capital_guarded(self):
        body = source("projects_selection.nut")
        start = body.index("function OpexRailCalFundScore(")
        end = body.index("function OpexSelectRejectScore(", start)
        code = body[start:end]
        self.assertIn('project.mode == "rail"', code)
        self.assertIn('("capitalIsActual" in project)', code)
        self.assertIn('("capitalIsActual" in project.payload)', code)
        self.assertIn("fundProfit * profitFactor", code)
        self.assertIn("scoreDecisionFinanceCapital * costFactor", code)
        self.assertIn("kDec > calCost", code)
        self.assertEqual(body.count("project.fundScore <- OpexRailCalFundScore("), 2)
        self.assertNotIn('GetSetting("rail_cal")', body)
        for mode in ("air", "fleet", "road", "water"):
            self.assertEqual(score(mode, False, "COAL", 120, 100, 200, 0, True),
                             score(mode, False, "COAL", 120, 100, 200, 0, False))
        self.assertEqual(score("rail", True, "COAL", 120, 100, 200, 0, True),
                         score("rail", True, "COAL", 120, 100, 200, 0, False))

    def test_table_literal_and_distance_boundaries(self):
        body = source("projects_selection.nut")
        for label, vals in PROFIT.items():
            match = re.search(rf"\b{label}\s*=\s*\[([^]]+)\]", body)
            self.assertIsNotNone(match, label)
            self.assertEqual([float(x) for x in match.group(1).split(",")], vals)
        self.assertIn(f"{COST_A} + {COST_B} * d", body)
        self.assertEqual([factor("COAL", x) for x in [90, 91, 127, 128, 172, 173]],
                         [0.8442, 1.1066, 1.1066, 1.3735, 1.3735, 1.4834])
        self.assertEqual(factor("MISC", 0), FALLBACK[0])

    def test_profit_factor_is_actually_active_alone(self):
        raw = score("rail", False, "COAL", 90, 100, 200, 0, False)
        # Pure profit-factor effect when the cost factor is held at one.
        standalone = raw * factor("COAL", 90)
        self.assertNotEqual(standalone, raw)
        self.assertAlmostEqual(standalone / raw, 0.8442)
        calibrated = score("rail", False, "COAL", 90, 100, 200, 0, True)
        self.assertAlmostEqual(calibrated / raw, 0.8442 / (COST_A + COST_B * 90))
        kdec_score = score("rail", False, "COAL", 90, 100, 100, 1000, True)
        self.assertAlmostEqual(kdec_score / score("rail", False, "COAL", 90, 100, 100, 1000, False), 0.8442)


if __name__ == "__main__":
    unittest.main()
