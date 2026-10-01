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


class C100AirTripPhysicalTests(unittest.TestCase):
    def test_setting_is_off_by_default(self):
        self.assertIn("C100_AIR_TRIP_PHYSICAL <- false;", GLOBALS)
        start = INFO.index('name = "c100_air_trip_physical"')
        snippet = INFO[start:start + 440]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_trip_model_physical_path_uses_direct_api_speed_and_maneuvers(self):
        match = re.search(
            r"function OpexAirTripModel\(speed, capacity, distance, engineId = -1, airportType = -1,\s*forcePhysicalTiming = false, forceC100RankReplay = false\)(.*?)\n\}",
            AIR,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("physicalTiming = C100_AIR_TRIP_PHYSICAL || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS", body)
        self.assertIn("|| forcePhysicalTiming", body)
        self.assertIn("local c100ReplayTiming = C114_AIR_C100_FULL_REPLAY || forceC100RankReplay;", body)
        self.assertIn("directSpeed = physicalTiming || c100ReplayTiming", body)
        self.assertIn("C99_AIR_SPEED_API_FIX || directSpeed", body)
        self.assertIn("speed.tofloat()", body)
        self.assertIn("OpexC100AirManeuverDays(engineId, airportType, airportType)", body)

    def test_c100_maneuver_model_does_not_mutate_historical_helper(self):
        match = re.search(
            r"function OpexC100AirManeuverDays\(engineId, srcType, dstType\)(.*?)\n\}",
            AIR,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("maxSpeed < 50.0 ? maxSpeed : 50.0", body)
        self.assertIn("groundTiles = groundTiles * 2.0 / 3.0", body)
        self.assertNotIn("OpexPlaneSpeedDivisor", body)

    def test_legacy_three_day_path_remains_present(self):
        self.assertIn("local airportDelayDays = 3.0;", AIR)

    def test_economics_passes_engine_and_airport_type(self):
        self.assertGreaterEqual(
            AIR.count("OpexAirTripModel(plane.speed, plane.capacity, distance, plane.id, airport.type,"),
            2,
        )

    def test_physical_trip_memo_key_contains_airport_type(self):
        self.assertIn('plane.id + "|" + airport.type + "|" + distance', AIR)


if __name__ == "__main__":
    unittest.main()
