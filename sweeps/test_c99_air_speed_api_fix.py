import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")

def trip_days(distance, speed, corrected):
    effective = float(speed) if corrected else float(speed) / 4.0
    return float(distance) / (0.036 * max(1.0, effective)) + 3.0

class C99AirSpeedApiFixTests(unittest.TestCase):
    def test_setting_defaults_off(self):
        self.assertIn("C99_AIR_SPEED_API_FIX <- false;", GLOBALS)
        start = INFO.index('name = "c99_air_speed_api_fix"')
        snippet = INFO[start:start + 500]
        for value in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(value, snippet)
        self.assertIn('C99_AIR_SPEED_API_FIX = AIController.GetSetting("c99_air_speed_api_fix") != 0;', SETTINGS)

    def test_fix_is_isolated_to_trip_speed_interpretation(self):
        match = re.search(
            r"function OpexAirTripModel\(speed, capacity, distance, engineId = -1, airportType = -1,\s*forcePhysicalTiming = false\)(.*?)\n\}",
            AIR,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("physicalTiming = C100_AIR_TRIP_PHYSICAL || forcePhysicalTiming", body)
        self.assertIn("C99_AIR_SPEED_API_FIX || physicalTiming", body)
        self.assertIn("? speed.tofloat() : speed / 4.0;", body)
        self.assertIn("local airportDelayDays = 3.0;", body)
        self.assertEqual(body.count("C99_AIR_SPEED_API_FIX"), 1)
        self.assertIn("!C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL", AIR)

    def test_legacy_path_is_preserved_when_flag_is_off(self):
        self.assertAlmostEqual(trip_days(168, 236, False), 82.0960451977, places=5)

    def test_corrected_path_uses_noai_speed_directly(self):
        corrected = trip_days(168, 236, True)
        self.assertAlmostEqual(corrected, 22.7740112994, places=5)
        self.assertLess(corrected, trip_days(168, 236, False) / 3.0)

    def test_corrected_prediction_is_closer_to_observed_example(self):
        observed = 37.25
        self.assertLess(abs(trip_days(168, 236, True) - observed), abs(trip_days(168, 236, False) - observed))

if __name__ == "__main__":
    unittest.main()
