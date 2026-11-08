"""Contrats de configuration et d'exécution du levier road1y_alt_load_cond."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source


class TestRoad1yAltLoadCond(unittest.TestCase):
    def test_info_nut_declaration(self):
        info_src = source("info.nut")
        self.assertIn('"road1y_alt_load_cond"', info_src)
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"road1y_alt_load_cond".*?\}\);', info_src, re.DOTALL)
        self.assertIsNotNone(match)
        setting_block = match.group(0)
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 100", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_ALT_LOAD_COND <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_alt_load_cond")'), 1)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_ALT_LOAD_COND = AIController.GetSetting("road1y_alt_load_cond");', load_fn)
        self.assertIn("if (ROAD1Y_ALT_LOAD_COND < 0 || ROAD1Y_ALT_LOAD_COND > 100) ROAD1Y_ALT_LOAD_COND = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_ALT_LOAD_COND = 0;", load_fn)
        self.assertNotIn("road1y_alt_load_cond", source("persist.nut"))
        self.assertNotIn("ROAD1Y_ALT_LOAD_COND", source("persist.nut"))

    def test_bus_districts_helpers(self):
        bd = source("bus_districts.nut")
        self.assertIn("function OpexRoad1yAltLoadIsInverted(vehicle)", bd)
        self.assertIn("function OpexRoad1yAltLoadOrient(vehicle, inverted)", bd)
        self.assertIn("function OpexRoad1yAltLoadCondEligible(line)", bd)
        self.assertIn("function OpexRoad1yAltLoadCondEligibleCandidate(candidate)", bd)
        self.assertIn("function OpexRoad1yAltLoadCondAdjustFleet(lineOrCandidate, built, site)", bd)
        self.assertIn('OpexDecide("ROAD1Y_ALT_LOAD_COND"', bd)

        adjust_fn = body("bus_districts.nut", "OpexRoad1yAltLoadCondAdjustFleet")
        self.assertNotIn("function(", adjust_fn)
        self.assertNotIn(".find(", adjust_fn)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", adjust_fn), word)

    def test_builder_road_calls(self):
        route_fn = body("builder_road.nut", "OpexBuildRoadRoute")
        refleet_fn = body("builder_road.nut", "OpexRoadRefleet")
        self.assertIn("if (ROAD1Y_ALT_LOAD_COND > 0 && !isFreight && (\"kind\" in candidate) && candidate.kind == \"pax\")", route_fn)
        self.assertIn('OpexRoad1yAltLoadCondAdjustFleet(candidate, built, "open");', route_fn)
        self.assertIn("if (ROAD1Y_ALT_LOAD_COND > 0)", refleet_fn)
        self.assertIn('OpexRoad1yAltLoadCondAdjustFleet(line, built, "refleet");', refleet_fn)


if __name__ == "__main__":
    unittest.main()
