import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C114AirC100FullReplayTests(unittest.TestCase):
    def test_setting_is_off_by_default(self):
        self.assertIn("C114_AIR_C100_FULL_REPLAY <- false;", GLOBALS)
        start = INFO.index('name = "c114_air_c100_full_replay"')
        snippet = INFO[start:start + 720]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c114_air_c100_full_replay")', SETTINGS)

    def test_trip_model_replays_historical_c100_globally(self):
        start = AIR.index("function OpexAirTripModel(")
        end = AIR.index("function OpexAirLiveRoutesAtAirport", start)
        body = AIR[start:end]
        self.assertIn("local c100ReplayTiming = C114_AIR_C100_FULL_REPLAY || forceC100RankReplay;", body)
        self.assertIn("local directSpeed = physicalTiming || c100ReplayTiming;", body)
        self.assertIn("if (c100ReplayTiming && engineId >= 0", body)
        self.assertIn("OpexAirManeuverDays(engineId, airportType, airportType,", body)

    def test_economics_memo_separates_replay_from_other_timings(self):
        start = AIR.index("function OpexAirEconomics(")
        end = AIR.index("function OpexAirTargetEconomics", start)
        body = AIR[start:end]
        self.assertIn('"|rr=" + ((C114_AIR_C100_FULL_REPLAY || forceC100RankReplay) ? 1 : 0)', body)
        self.assertIn("local tripKey = (C114_AIR_C100_FULL_REPLAY || forceC100RankReplay)", body)

    def test_c114_keeps_normal_c68_engine_scan(self):
        start = AIR.index("function OpexAirChooseRoutePlaneFull(")
        end = AIR.index("function OpexM3ProbeAirEquipment", start)
        body = AIR[start:end]
        self.assertNotIn("if (C114_AIR_C100_FULL_REPLAY", body)
        self.assertIn("foreach (plane in routePlaneChoices)", body)
        self.assertIn("local economics = OpexAirEconomics(catalog, airport, plane", body)


if __name__ == "__main__":
    unittest.main()
