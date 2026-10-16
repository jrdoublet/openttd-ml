"""V216f : sejour mecanique en gare dans le cycle rail, inerte a 0 (contrats statiques)."""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class TestV216fDwell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = (AI / "info.nut").read_text(encoding="utf-8")
        cls.economy = (AI / "economy.nut").read_text(encoding="utf-8")
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}

    def test_setting_default_qualified(self):
        block = re.search(r'name = "v216f_dwell_pct",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block.group(1), level + r" = 100\b")
        self.assertIn("V216F_DWELL_PCT <- 0;", self.sources["globals_pre.nut"])
        self.assertEqual(sum(s.count('GetSetting("v216f_dwell_pct")') for s in self.sources.values()), 1)

    def test_helper_returns_zero_when_inert(self):
        body = self.economy[self.economy.index("function OpexRailStationDwellDays"):]
        body = body[:body.index("\n}\n")]
        self.assertIn("if (V216F_DWELL_PCT <= 0", body)
        self.assertIn("return 0.0;", body)

    def test_rail_cycles_use_dwell(self):
        rail = self.economy.count("OpexLoadedTripsPerMonth(oneWayDays + dwellDays, roundTripDays + dwellDays")
        self.assertEqual(rail, 4)
        self.assertEqual(self.economy.count("local dwellDays = OpexRailStationDwellDays(wagon);"), 2)
        # Definition + routier (ROAD_PAX_STOP_DWELL_DAYS), inchange.
        self.assertEqual(self.economy.count("OpexLoadedTripsPerMonth(oneWayDays, roundTripDays"), 2)


if __name__ == "__main__":
    unittest.main()
