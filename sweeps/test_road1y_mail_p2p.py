"""Contrats de configuration et d'exécution du levier road1y_mail_p2p et road1y_mail_p2p_missing."""

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
        for setting_name, max_val in (
            ("road1y_mail_p2p", 20),
            ("road1y_mail_p2p_missing", 60),
            ("road1y_mail_p2p_cash", 60),
            ("road1y_mail_p2p_start", 12),
        ):
            self.assertIn(f'"{setting_name}"', info_src)
            match = re.search(r'AddSetting\(\{\s*name\s*=\s*"' + re.escape(setting_name) + r'".*?\}\);', info_src, re.DOTALL)
            self.assertIsNotNone(match, f"Setting {setting_name} not found in info.nut")
            setting_block = match.group(0)
            self.assertIn("min_value = 0", setting_block)
            self.assertIn(f"max_value = {max_val}", setting_block)
            for diff in ("easy", "medium", "hard", "custom"):
                self.assertIn(f"{diff}_value = 0", setting_block)
            self.assertIn("flags = 0", setting_block)

    def test_globals_pre_declaration(self):
        pre = source("globals_pre.nut")
        self.assertIn("ROAD1Y_MAIL_P2P <- 0;", pre)
        self.assertIn("ROAD1Y_MAIL_P2P_TRY_YM <- -1;", pre)
        self.assertIn("ROAD1Y_MAIL_P2P_CURSOR <- 0;", pre)
        self.assertIn("ROAD1Y_MAIL_P2P_MISSING <- 0;", pre)
        self.assertIn("ROAD1Y_MAIL_P2P_CASH <- 0;", pre)
        self.assertIn("ROAD1Y_MAIL_P2P_START <- 0;", pre)

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_mail_p2p")'), 1)
        self.assertEqual(settings_src.count('GetSetting("road1y_mail_p2p_missing")'), 1)
        self.assertEqual(settings_src.count('GetSetting("road1y_mail_p2p_cash")'), 1)
        self.assertEqual(settings_src.count('GetSetting("road1y_mail_p2p_start")'), 1)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_MAIL_P2P = AIController.GetSetting("road1y_mail_p2p");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL_P2P < 0 || ROAD1Y_MAIL_P2P > 20) ROAD1Y_MAIL_P2P = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_P2P = 0;", load_fn)
        self.assertIn('ROAD1Y_MAIL_P2P_MISSING = AIController.GetSetting("road1y_mail_p2p_missing");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL_P2P_MISSING < 0 || ROAD1Y_MAIL_P2P_MISSING > 60) ROAD1Y_MAIL_P2P_MISSING = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_P2P_MISSING = 0;", load_fn)
        self.assertIn('ROAD1Y_MAIL_P2P_CASH = AIController.GetSetting("road1y_mail_p2p_cash");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL_P2P_CASH < 0 || ROAD1Y_MAIL_P2P_CASH > 60) ROAD1Y_MAIL_P2P_CASH = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_P2P_CASH = 0;", load_fn)
        self.assertIn('ROAD1Y_MAIL_P2P_START = AIController.GetSetting("road1y_mail_p2p_start");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL_P2P_START < 0 || ROAD1Y_MAIL_P2P_START > 12) ROAD1Y_MAIL_P2P_START = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_P2P_START = 0;", load_fn)

    def test_multimodal_gate_integration(self):
        from test_road1y_multimodal_gate import LOAD_SETTINGS_KEYS, ROAD1Y_OFF, SETTING_TO_GLOBAL
        for key, glob in (
            ("road1y_mail_p2p", "ROAD1Y_MAIL_P2P"),
            ("road1y_mail_p2p_missing", "ROAD1Y_MAIL_P2P_MISSING"),
            ("road1y_mail_p2p_cash", "ROAD1Y_MAIL_P2P_CASH"),
            ("road1y_mail_p2p_start", "ROAD1Y_MAIL_P2P_START"),
        ):
            self.assertIn(key, SETTING_TO_GLOBAL)
            self.assertEqual(SETTING_TO_GLOBAL[key], glob)
            self.assertIn(glob, ROAD1Y_OFF)
            self.assertEqual(ROAD1Y_OFF[glob], "0")
            self.assertIn(key, LOAD_SETTINGS_KEYS)

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
        self.assertIn("if (ROAD1Y_MAIL_P2P <= 0) return;", step_fn)
        self.assertIn("ROAD1Y_MAIL_P2P_START", step_fn)
        self.assertIn("ROAD1Y_MAIL_P2P_CASH", step_fn)
        self.assertIn("local threshold = (ROAD1Y_MAIL_P2P_CASH > 0) ? (ROAD1Y_MAIL_P2P_CASH * 1000) : 37000;", step_fn)
        self.assertIn("local maxMissing = (ROAD1Y_MAIL_P2P_MISSING > 0) ? ROAD1Y_MAIL_P2P_MISSING : 14;", step_fn)
        self.assertIn("if (missing <= maxMissing)", step_fn)
        self.assertIn("local cashReserve = 25000;", step_fn)
        # Curseur tournant present
        self.assertIn("local startI = (ROAD1Y_MAIL_P2P_CURSOR >= 0) ? (ROAD1Y_MAIL_P2P_CURSOR % nTowns) : 0;", step_fn)
        self.assertIn("ROAD1Y_MAIL_P2P_CURSOR = (startI + 1) % nTowns;", step_fn)
        # Attempts deplace apres siteA/siteB et borne a 6
        self.assertIn("attempts++;", step_fn)
        self.assertIn("if (attempts > 6) return;", step_fn)
        idx_site = step_fn.index("local siteA = OpexRoad1yFindMailP2PSite")
        idx_attempts = step_fn.index("attempts++;")
        self.assertLess(idx_site, idx_attempts, "attempts++ must be after find site checks")

    def test_decision_log_reasons(self):
        step_fn = body("bus_districts.nut", "OpexRoad1yMailP2PStep")
        build_fn = body("bus_districts.nut", "OpexRoad1yBuildMailP2P")
        self.assertIn('reason=START', step_fn)
        self.assertIn('reason=CASH', step_fn)
        self.assertIn('reason=CASH', build_fn)
        self.assertIn('reason=SITE_A', step_fn)
        self.assertIn('reason=SITE_B', step_fn)
        self.assertIn('reason=MISSING', step_fn)
        self.assertIn('reason=NO_TRACE', step_fn)
        self.assertIn('reason=DEPOT', step_fn)

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
