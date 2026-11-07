"""Tests de contrat pour LATE-GAME-1 (réinvestissement de l'excédent de trésorerie tardif)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestLateGame(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"late_game_policy"', info)
        block = re.search(r'AddSetting\(\{\s*name = "late_game_policy"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting late_game_policy manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 2", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("LATE_GAME_POLICY <- 0;", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('LATE_GAME_POLICY = AIController.GetSetting("late_game_policy");', settings)

    def test_late_game_dispatch_guards(self):
        v249 = read_nut("task_v249.nut")
        self.assertIn("OpexLateGameDispatch", v249)
        self.assertIn("year < 1976", v249)
        self.assertIn("loan > 0", v249)
        self.assertIn("cash <= reserve", v249)
        self.assertIn("(v252Cost * 2) + 5000000", v249)
        self.assertIn("TOWN_ACTION_ADVERTISE_SMALL", v249)
        self.assertIn("LATE_GAME_ACTION", v249)

    def test_hygiene_no_rail_modifications(self):
        builder_rail = read_nut("builder_rail.nut")
        self.assertNotIn("LATE_GAME_", builder_rail)
