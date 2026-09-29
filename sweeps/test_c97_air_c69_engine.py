"""Contrats deterministes de la sonde passive C97 choix moteur AIR."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise AssertionError(signature)


def score(point, k_dec=0):
    return point["profit"] * 1000.0 / max(point["capital"], k_dec)


class C97AirC69EngineTests(unittest.TestCase):
    def test_probe_setting_is_passive_and_default_zero(self):
        self.assertIn("C97_AIR_C69_ENGINE_PROBE <- false;", GLOBALS)
        start = INFO.index('name = "c97_air_c69_engine_probe"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn(
            'C97_AIR_C69_ENGINE_PROBE = AIController.GetSetting("c97_air_c69_engine_probe") != 0;',
            SETTINGS,
        )

    def test_uses_exact_portfolio_air_capital_and_calibration_path(self):
        body = function_body(BUILDER, "function OpexC97AirPoint(")
        self.assertIn("OpexProjectFromAir(catalog, virtualPlan, 0)", body)
        self.assertIn("OpexProjectFinanceCapital(project)", body)
        self.assertIn("C70_PROFIT_CALIBRATED", body)
        self.assertIn("OpexCalibratedProfit(project)", body)
        self.assertIn("OpexProjectScore(calibratedProfit, denom)", body)
        self.assertIn("financeCapital > kDec ? financeCapital : kDec", body)

    def test_argmax_is_direct_over_engine_times_n_not_v92_reduction(self):
        body = function_body(BUILDER, "function OpexC97AirFindBest(")
        self.assertIn("foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type])", body)
        self.assertIn("for (local n = 1; n <= maxPlanes; n++)", body)
        self.assertIn("newAirportCount, 0, n, false, false", body)
        self.assertIn("OpexC97AirPointBetter(point, best)", body)
        self.assertNotIn("serviceScan", body)
        self.assertNotIn("OpexAirServiceBetter", body)

    def test_probe_does_not_feed_choice_or_plan(self):
        choose = function_body(BUILDER, "function OpexAirChooseRoutePlane(")
        full = function_body(BUILDER, "function OpexAirChooseRoutePlaneFull(")
        self.assertNotIn("C97_", choose)
        self.assertNotIn("C97_", full)
        call = "if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);"
        self.assertEqual(BUILDER.count(call), 3)
        self.assertEqual(BUILDER.count("function OpexC97ProbeAirEngine(catalog, plan)"), 1)

    def test_log_contract_contains_required_fields(self):
        body = function_body(BUILDER, "function OpexC97ProbeAirEngine(")
        for field in (
            "C97_ENGINE route=", " src=", " dst=", " default_engine=", " c97_engine=",
            " c97_n=", " K_dec=", " default_P=", " default_C=", " default_score=",
            " c97_P=", " c97_C=", " c97_score=", " disagree=",
        ):
            self.assertIn(field, body)

    def test_synthetic_case_prevents_regression_to_v92_two_stage_choice(self):
        points = {
            "A": [
                {"engine": "A", "n": 1, "profit": 90, "capital": 90},
                {"engine": "A", "n": 2, "profit": 300, "capital": 300},
            ],
            "B": [
                {"engine": "B", "n": 1, "profit": 200, "capital": 100},
                {"engine": "B", "n": 2, "profit": 210, "capital": 1000},
            ],
        }
        mature = [max(engine_points, key=lambda p: p["profit"]) for engine_points in points.values()]
        v92_style = max(mature, key=score)
        direct = max((p for engine_points in points.values() for p in engine_points), key=score)
        self.assertEqual(v92_style["engine"], "A")
        self.assertEqual(direct["engine"], "B")
        self.assertEqual(direct["n"], 1)


if __name__ == "__main__":
    unittest.main()
