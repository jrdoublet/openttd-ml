#!/usr/bin/env python3
"""Contrats statiques de v131_town_clearance (degagement urbain de l'A* rail)."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_code(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//.*", "", src)
    return src


def function_body(src, signature):
    idx = src.index(signature)
    start = src.index("{", idx)
    depth = 0
    for i in range(start, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[idx : i + 1]
    raise ValueError(f"accolade fermante introuvable pour {signature}")


class TestV131TownClearance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.builder = source("builder_rail.nut")
        cls.rail = source("task_rail.nut")
        cls.clear_build = function_body(
            cls.builder, "function OpexV131BuildTownClearance("
        )
        cls.clear_log = function_body(
            cls.builder, "function OpexV131LogClearance("
        )

    def test_setting_default_zero_all_difficulties(self):
        block = self.info[self.info.index('name = "v131_town_clearance"') :]
        block = block[: block.index("})")]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, level + r"_value = 0\b")

    def test_setting_read_once(self):
        self.assertEqual(self.settings.count('GetSetting("v131_town_clearance")'), 1)
        self.assertIn(
            'V131_TOWN_CLEARANCE = AIController.GetSetting("v131_town_clearance") != 0;',
            self.settings,
        )
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("v131_town_clearance")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        self.assertRegex(self.globals, r"V131_TOWN_CLEARANCE <- false;")
        self.assertRegex(self.globals, r"V131_TOWN_CLEAR_BUFFER <- 4;")

    def test_clearance_radius_formula_and_bounds(self):
        self.assertIn("4 + (pop / 500)", self.clear_build)
        self.assertIn("if (radius < 4) radius = 4;", self.clear_build)
        self.assertIn("if (radius > 10) radius = 10;", self.clear_build)

    def test_station_platform_and_lead_buffer_exemptions(self):
        self.assertIn("exempt", self.clear_build)
        self.assertIn("V131_TOWN_CLEAR_BUFFER", self.clear_build)
        self.assertIn("exempt[st.lead] <- true;", self.clear_build)
        self.assertIn("exempt[st.station_exit] <- true;", self.clear_build)
        self.assertIn("!(t in exempt)", self.clear_build)

    def test_zero_cost_in_inner_astar_loop(self):
        # Clearance is passed as ignoredTiles to InitializePath, never checked in _Cost loop
        for p_file in ("rail.nut", "aystar.nut"):
            path = AI / "pathfinder_v90" / p_file
            if path.exists():
                code = path.read_text(encoding="utf-8")
                self.assertNotIn("V131_TOWN_CLEARANCE", code)
                self.assertNotIn("town_clearance", code)

    def test_log_clearance_format_and_gating(self):
        self.assertIn("if (!DECISION_LOG || !V131_TOWN_CLEARANCE) return;", self.clear_log)
        self.assertIn('OpexDecide("V131_CLEAR"', self.clear_log)
        for field in ("src=", "dst=", "cleared_tiles=", "avoided=", "path_len="):
            self.assertIn(field, self.clear_log)

    def test_wired_in_rail_searches(self):
        self.assertIn("V131_TOWN_CLEARANCE ? OpexV131BuildTownClearance", self.rail)
        self.assertIn("V131_TOWN_CLEARANCE ? OpexV131BuildTownClearance", self.builder)
        self.assertIn("OpexV131LogClearance", self.rail)
        self.assertIn("OpexV131LogClearance", self.builder)

    def test_no_nested_functions_or_reserved_ids(self):
        for code_str in (self.clear_build, self.clear_log):
            inner = code_str[code_str.index("{") + 1 :]
            self.assertNotIn("function ", inner)
            self.assertNotRegex(inner, r"\bclone\b")
            self.assertNotRegex(inner, r"\bbase\b")
            self.assertNotRegex(inner, r"\bparent\b")
            self.assertNotRegex(inner, r"\byield\b")
            self.assertNotRegex(inner, r"\bdelete\b")
            self.assertNotRegex(inner, r"\bstatic\b")
            self.assertNotRegex(inner, r"\benum\b")
            self.assertNotRegex(inner, r"\bconst\b")


if __name__ == "__main__":
    unittest.main()
