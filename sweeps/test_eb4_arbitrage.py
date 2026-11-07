"""Tests de contrat pour EB-4 (arbitrage de caisse 1970-1972 entre air et route)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestEB4Arbitrage(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"eb4_air_road_arbitrage"', info)
        block = re.search(r'AddSetting\(\{\s*name = "eb4_air_road_arbitrage"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting eb4_air_road_arbitrage manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("EB4_AIR_ROAD_ARBITRAGE <- 0;", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('EB4_AIR_ROAD_ARBITRAGE = AIController.GetSetting("eb4_air_road_arbitrage") == 1 ? 1 : 0;', settings)

    def test_selection_arbitrage_logic(self):
        proj = read_nut("projects_selection.nut")
        self.assertIn("OpexEB4RoadAllowed", proj)
        self.assertIn("EB4_AIR_ROAD_ARBITRAGE", proj)
        self.assertIn("deltaC <= monthlyIncome * 2", proj)
        self.assertIn("deltaC > monthlyIncome * 3", proj)
        self.assertIn("roadCapital > (capitalBudget / 4)", proj)
        self.assertIn("prof < 2 * roadCapital", proj)
        self.assertIn("OpexGetCandidateTownEndpoints", proj)

    def test_hygiene_no_forbidden_constructs(self):
        content = read_nut("projects_selection.nut")
        # pas de .find( dans le code neuf EB-4
        self.assertNotIn("EB4_AIR_ROAD_ARBITRAGE.find(", content)
        self.assertNotIn("OpexEB4RoadAllowed.find(", content)
