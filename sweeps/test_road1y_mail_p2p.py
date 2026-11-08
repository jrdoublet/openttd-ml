"""Contrats de configuration et d'exécution du levier road1y_mail_p2p."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source


class TestRoad1yMailP2P(unittest.TestCase):
    def test_info_nut_declaration(self):
        info_src = source("info.nut")
        self.assertIn('"road1y_mail_p2p"', info_src)
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"road1y_mail_p2p".*?\}\);', info_src, re.DOTALL)
        self.assertIsNotNone(match)
        setting_block = match.group(0)
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 20", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_globals_pre_declaration(self):
        pre = source("globals_pre.nut")
        self.assertIn("ROAD1Y_MAIL_P2P <- 0;", pre)
        self.assertIn("ROAD1Y_MAIL_P2P_TRY_YM <- -1;", pre)

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_mail_p2p")'), 1)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_MAIL_P2P = AIController.GetSetting("road1y_mail_p2p");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL_P2P < 0 || ROAD1Y_MAIL_P2P > 20) ROAD1Y_MAIL_P2P = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_P2P = 0;", load_fn)

    def test_multimodal_gate_integration(self):
        from test_road1y_multimodal_gate import LOAD_SETTINGS_KEYS, ROAD1Y_OFF, SETTING_TO_GLOBAL
        self.assertIn("road1y_mail_p2p", SETTING_TO_GLOBAL)
        self.assertEqual(SETTING_TO_GLOBAL["road1y_mail_p2p"], "ROAD1Y_MAIL_P2P")
        self.assertIn("ROAD1Y_MAIL_P2P", ROAD1Y_OFF)
        self.assertEqual(ROAD1Y_OFF["ROAD1Y_MAIL_P2P"], "0")
        self.assertIn("road1y_mail_p2p", LOAD_SETTINGS_KEYS)

    def test_bus_districts_helpers(self):
        bd = source("bus_districts.nut")
        self.assertIn("function OpexRoad1yMailP2PLog(fields)", bd)
        self.assertIn("function OpexRoad1yFindMailP2PSite(ai, catalog, townId, mailCargo)", bd)
        self.assertIn("function OpexRoad1yMailP2PActivePairs(ai)", bd)
        self.assertIn("function OpexRoad1yBuildMailP2P(ai, catalog, ta, tb, siteA, siteB, trace, depot, cashReserve)", bd)
        self.assertIn("function OpexRoad1yMailP2PStep(ai, year)", bd)
        self.assertIn("function OpexRoad1yRefleetMailP2PLine(ai, line, year)", bd)
        self.assertIn('OpexDecide("ROAD1Y_MAIL_P2P"', bd)

    def test_guards_and_safety_checks(self):
        step_fn = body("bus_districts.nut", "OpexRoad1yMailP2PStep")
        self.assertIn("if (year <= 1970) return;", step_fn)
        self.assertIn("if (ROAD1Y_MAIL_P2P <= 0) return;", step_fn)
        self.assertIn("if (missing <= 14)", step_fn)
        self.assertIn("local cashReserve = 25000;", step_fn)
        self.assertIn("if (attempts > 4) return;", step_fn)

    def test_squirrel_cleanliness(self):
        for fn_name in (
            "OpexRoad1yMailP2PLog",
            "OpexRoad1yFindMailP2PSite",
            "OpexRoad1yMailP2PActivePairs",
            "OpexRoad1yBuildMailP2P",
            "OpexRoad1yMailP2PStep",
            "OpexRoad1yRefleetMailP2PLine",
        ):
            code = body("bus_districts.nut", fn_name)
            self.assertNotIn("function(", code)
            self.assertNotIn(".find(", code)
            for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
                self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", code), f"reserved word {word} in {fn_name}")

    def test_overrides_wiring(self):
        overrides = source("bus_districts_overrides.nut")
        self.assertIn('if (ROAD1Y_MAIL_P2P > 0 && ("kind" in line) && line.kind == "mail_p2p")', overrides)
        self.assertIn("OpexRoad1yRefleetMailP2PLine(this, line, year);", overrides)
        self.assertIn("if (ROAD1Y_MAIL_P2P > 0) OpexRoad1yMailP2PStep(this, year);", overrides)
        self.assertIn("if (ROAD1Y_MAIL_P2P > 0) OpexAI._refleetRoadLines <- OpexRoad1yRefleetSaved;", overrides)


if __name__ == "__main__":
    unittest.main()
