import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")


class C101AirPhysicalEngineChoiceTests(unittest.TestCase):
    def test_setting_is_off_by_default(self):
        self.assertIn("C101_AIR_PHYSICAL_ENGINE_CHOICE <- false;", GLOBALS)
        start = INFO.index('name = "c101_air_physical_engine_choice"')
        snippet = INFO[start:start + 520]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_c101_ranks_physical_but_returns_legacy_economics(self):
        match = re.search(
            r"function OpexC101ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S
        )
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("local legacy = OpexAirEconomics", body)
        self.assertIn("0, false, false, true", body)
        self.assertIn("item.legacy.capital > rawLegacy.capital", body)
        self.assertIn("physical.profitAnnual > bestPhysical.profitAnnual", body)
        self.assertIn("return { plane = bestPlane, economics = bestLegacy };", body)
        self.assertIn("phase=c101_choice", body)
        self.assertIn("raw_price=", body)
        self.assertIn("pick_legacy_P=", body)
        self.assertIn("pick_physical_P=", body)

    def test_c101_isolated_from_other_engine_choice_modes(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("C101_AIR_PHYSICAL_ENGINE_CHOICE && C72_PLANE_CHOICE == 0", full)
        self.assertIn("!C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL", full)
        self.assertIn("!C85_AIR_EQUIPMENT_FRONTIER", full)
        self.assertIn("if (C82_ENGINE_CALIBRATION)", full)

    def test_force_physical_timing_has_distinct_memo_key(self):
        self.assertIn('"|pt=" + ((C100_AIR_TRIP_PHYSICAL || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS', AIR)
        self.assertIn('|| forcePhysicalTiming) ? 1 : 0)', AIR)


if __name__ == "__main__":
    unittest.main()
