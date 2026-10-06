import re
import unittest
from pathlib import Path
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


ROOT = Path(__file__).resolve().parents[1]
AIR = read_builder_air()
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")


class C103AirC100RankReplayTests(unittest.TestCase):
    def test_setting_is_off_by_default(self):
        self.assertIn("C103_AIR_C100_RANK_REPLAY <- false;", GLOBALS)
        start = INFO.index('name = "c103_air_c100_rank_replay"')
        snippet = INFO[start:start + 560]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_replay_trip_uses_direct_speed_and_historical_maneuver_helper(self):
        trip = re.search(r"function OpexAirTripModel\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(trip)
        body = trip.group(1)
        self.assertIn("local c100ReplayTiming = C114_AIR_C100_FULL_REPLAY || forceC100RankReplay;", body)
        self.assertIn("local directSpeed = physicalTiming || c100ReplayTiming;", body)
        self.assertIn("if (c100ReplayTiming", body)
        self.assertIn("OpexAirManeuverDays(engineId, airportType, airportType", body)
        self.assertIn("OpexPlaneSpeedDivisor()", body)

    def test_c103_ranks_replay_but_returns_legacy_economics(self):
        match = re.search(r"function OpexC103ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("legacy = OpexAirEconomics", body)
        self.assertIn("0, false, false, false, true", body)
        self.assertNotIn("item.legacy.capital >", body)
        self.assertIn("replay.profitAnnual > bestReplay.profitAnnual", body)
        self.assertIn("return { plane = bestPlane, economics = bestLegacy };", body)
        self.assertIn("phase=c103_choice", body)

    def test_c103_isolated_from_other_engine_choice_modes(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("C103_AIR_C100_RANK_REPLAY && C72_PLANE_CHOICE == 0", full)
        self.assertIn("!C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL", full)
        self.assertIn("!C85_AIR_EQUIPMENT_FRONTIER", full)

    def test_replay_has_distinct_memo_keys(self):
        self.assertIn('"|rr=" + ((C114_AIR_C100_FULL_REPLAY || forceC100RankReplay) ? 1 : 0)', AIR)
        self.assertIn('? ("r|" + plane.id + "|" + airport.type + "|" + distance)', AIR)


if __name__ == "__main__":
    unittest.main()
