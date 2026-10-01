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


class C105AirReplayChoicePhysicalEconomicsTests(unittest.TestCase):
    def test_setting_is_off_by_default(self):
        self.assertIn("C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS <- false;", GLOBALS)
        start = INFO.index('name = "c105_air_replay_choice_physical_economics"')
        snippet = INFO[start:start + 620]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_c105_uses_physical_timing_globally(self):
        trip = re.search(r"function OpexAirTripModel\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(trip)
        self.assertIn("C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS", trip.group(1))
        self.assertIn("C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS", AIR[AIR.index("function OpexAirEconomics("):])

    def test_c105_ranks_replay_but_returns_physical_economics(self):
        match = re.search(r"function OpexC105ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC104BestAirEngine", body)
        self.assertIn("opcodePadding, 1", body)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("return { plane = replay.plane, economics = physical };", body)

    def test_c105_isolated_in_c68_path(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("if (C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0", full)
        self.assertIn("!C82_ENGINE_CALIBRATION && !C85_AIR_EQUIPMENT_FRONTIER", full)
        self.assertIn("!C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY", full)


if __name__ == "__main__":
    unittest.main()
