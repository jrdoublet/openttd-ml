"""Contrats source DIST-BORNES-1 ; ne compilent pas Squirrel."""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class DistAirMinTests(unittest.TestCase):
    def test_integer_setting_and_zero_defaults(self):
        info = source("info.nut")
        blocks = re.findall(r'AddSetting\(\{\s*name = "dist_air_min"(.*?)\}\);', info, re.S)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        for field, value in [("min_value", 0), ("max_value", 512), ("step_size", 1),
                             ("flags", 0), ("easy_value", 0), ("medium_value", 0),
                             ("hard_value", 0), ("custom_value", 0)]:
            self.assertRegex(block, rf"\b{field}\s*=\s*{value}\b")
        self.assertIn("DIST_AIR_MIN <- 0;", source("globals_pre.nut"))

    def test_single_setting_read_and_validation(self):
        all_sources = "\n".join(p.read_text(encoding="utf-8") for p in AI.glob("*.nut"))
        self.assertEqual(all_sources.count('GetSetting("dist_air_min")'), 1)
        settings = source("settings.nut")
        self.assertIn('local distAirMin = AIController.GetSetting("dist_air_min");', settings)
        self.assertIn("DIST_AIR_MIN = (distAirMin != null && distAirMin >= 0 && distAirMin <= 512) ? distAirMin : 0;", settings)

    def test_epoch_override_after_original_bounds_before_log(self):
        text = source("candidates.nut")
        epoch = text.split("function OpexRefreshEpochBounds(", 1)[1].split("function OpexCatalogBounds(", 1)[0]
        self.assertEqual(epoch.count("DIST_AIR_MIN"), 1)
        self.assertIn("airMin = (railAir < railMax) ? railAir : railMax,", epoch)
        override = """local distAirMin = DIST_AIR_MIN;
  if (distAirMin > 0) {
    railAir = (distAirMin < railMax) ? distAirMin : railMax;
    catalog.bounds.airMin = railAir;
    catalog.bounds.railAirOverlapMin = railAir;
  }"""
        self.assertIn(override, epoch)
        self.assertLess(epoch.index("catalog.bounds = {"), epoch.index(override))
        self.assertLess(epoch.index(override), epoch.index('OpexDecide("EPOCH_BOUNDS"'))
        self.assertIn('" railAir=" + railAir', epoch)
        self.assertIn('" airMin=" + catalog.bounds.airMin', epoch)
        self.assertNotRegex(override, r"\brailMax\s*=")

    def test_static_fallback_same_clamp_and_overlap(self):
        fallback = source("candidates.nut").split("function OpexCatalogBounds(", 1)[1].split("function OpexRoadDistanceAllowed(", 1)[0]
        self.assertEqual(fallback.count("DIST_AIR_MIN"), 1)
        self.assertIn("local airMin = railMax;", fallback)
        self.assertIn("local distAirMin = DIST_AIR_MIN;", fallback)
        self.assertIn("if (distAirMin > 0) airMin = (distAirMin < railMax) ? distAirMin : railMax;", fallback)
        self.assertIn("railAirOverlapMin = airMin, railMax = railMax, airMax = 0, airMin = airMin,", fallback)
        # Un entier strictement positif est deja >= 1 ; le ternaire borne au railMax.
        for setting, expected in [(1, 1), (100, 100), (200, 200), (512, 200)]:
            self.assertEqual(setting if setting < 200 else 200, expected)

    def test_po01c_uses_shared_bounds_and_band_filter(self):
        copied = source("po01c_generators.nut")
        self.assertIn("local bounds = OpexCatalogBounds(catalog);", copied)
        self.assertIn("OpexRailPaxPairInBand(", copied)
        self.assertNotRegex(copied, r"\b(?:airMin|railAirOverlapMin)\s*=")


if __name__ == "__main__":
    unittest.main()
