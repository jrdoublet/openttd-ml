"""Tests de contrat pour OPCODES/IDLE-1 (valorisation du reliquat de tick pour tâches de fond)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestIdle1Contract(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"idle1_slack_worker"', info)
        block = re.search(r'AddSetting\(\{\s*name = "idle1_slack_worker"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting idle1_slack_worker manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("IDLE1_SLACK_WORKER <- 0;", globals_pre)
        self.assertIn("IDLE1_SLACK_RESERVE <- 2500;", globals_pre)
        self.assertIn("IDLE1_TOWN_CURSOR <- 0;", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('IDLE1_SLACK_WORKER = AIController.GetSetting("idle1_slack_worker") == 1 ? 1 : 0;', settings)

    def test_main_and_probes_loops_symmetry(self):
        main = read_nut("main.nut")
        probes = read_nut("probes.nut")
        call_pattern = "if (IDLE1_SLACK_WORKER) this._idle1SlackStep();"
        self.assertIn(call_pattern, main, "Appel idle1_slack_worker manquant dans main.nut")
        self.assertIn(call_pattern, probes, "Appel idle1_slack_worker manquant dans probes.nut")

    def test_scheduler_slack_step_reserve_guard(self):
        scheduler = read_nut("scheduler.nut")
        self.assertIn("function OpexAI::_idle1SlackStep()", scheduler)
        self.assertIn("IDLE1_SLACK_RESERVE", scheduler)
        self.assertIn("AIController.GetOpsTillSuspend() < IDLE1_SLACK_RESERVE", scheduler)

    def test_hygiene_no_forbidden_constructs(self):
        for name in ("scheduler.nut", "main.nut", "probes.nut"):
            content = read_nut(name)
            self.assertNotIn(".find(", content, f".find( interdit dans {name}")


if __name__ == "__main__":
    unittest.main()
