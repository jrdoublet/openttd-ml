import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C115CapitalReplayTests(unittest.TestCase):
    def test_setting_is_temporarily_on_by_default(self):
        self.assertIn("C115_AIR_C100_CAPITAL_REPLAY <- false;", GLOBALS)
        start = INFO.index('name = "c115_air_c100_capital_replay"')
        snippet = INFO[start:start + 700]
        for field in ("easy_value = 1", "medium_value = 1", "hard_value = 1", "custom_value = 1"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c115_air_c100_capital_replay")', SETTINGS)

    def test_tracks_builds_for_endogenous_kdec(self):
        self.assertIn("|| C97_AIR_C69_ENGINE_PROBE || C115_AIR_C100_CAPITAL_REPLAY || C116_AIR_MARGINAL_CAPITAL;", SETTINGS)

    def test_replay_only_when_c68_capital_exceeds_kdec(self):
        start = AIR.index("function OpexC115ChooseRoutePlane(")
        end = AIR.index("function OpexAirChooseRoutePlaneFull(", start)
        body = AIR[start:end]
        self.assertIn("local decision = scan != null ? scan.decision", body)
        self.assertIn(": OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,", body)
        self.assertIn("newAirportCount, opcodePadding, 0)", body)
        self.assertIn("local kDec = OpexC69CachedKDec();", body)
        self.assertIn("if (kDec >= decision.economics.capital)", body)
        self.assertIn("return { plane = decision.plane, economics = decision.economics };", body)
        self.assertIn("OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,", body)
        self.assertIn("newAirportCount, opcodePadding, 1)", body)
        self.assertIn("return { plane = replay.plane, economics = replay.economics };", body)

    def test_c115_isolated_from_c114_global_replay(self):
        start = AIR.index("if (C115_AIR_C100_CAPITAL_REPLAY")
        end = AIR.index("if (C82_ENGINE_CALIBRATION", start)
        body = AIR[start:end]
        self.assertIn("!C114_AIR_C100_FULL_REPLAY", body)
        trip_start = AIR.index("function OpexAirTripModel(")
        trip_end = AIR.index("function OpexAirLiveRoutesAtAirport", trip_start)
        self.assertNotIn("C115_AIR_C100_CAPITAL_REPLAY", AIR[trip_start:trip_end])

    def test_choice_memo_cannot_drop_conditional_replay_economics(self):
        start = AIR.index("function OpexAirChooseRoutePlane(")
        end = AIR.index("function OpexC101ChooseRoutePlane", start)
        body = AIR[start:end]
        self.assertIn("C111_AIR_C100_DECISION_SHADOW", body)
        self.assertIn("(C115_AIR_C100_CAPITAL_REPLAY && !C116_AIR_MARGINAL_CAPITAL)", body)


if __name__ == "__main__":
    unittest.main()
