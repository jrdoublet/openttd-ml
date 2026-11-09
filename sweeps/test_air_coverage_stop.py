"""Tests de contrat pour AIR-COVERAGE-STOP (mise en veille du vivier de prospection aéroportuaire)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestAirCoverageStop(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"air_coverage_stop"', info)
        block = re.search(r'AddSetting\(\{\s*name = "air_coverage_stop"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting air_coverage_stop manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("AIR_COVERAGE_STOP <- 0;", globals_pre)
        self.assertIn("AIR_COVERAGE_EXHAUSTED <- false;", globals_pre)
        self.assertIn("AIR_NEW_TOWN_QUEUE <- [];", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('AIR_COVERAGE_STOP = AIController.GetSetting("air_coverage_stop") == 1 ? 1 : 0;', settings)

    def test_air_plans_exhaustion_and_sleeping_guard(self):
        air_plan = read_nut("air_planning.nut")
        self.assertIn("AIR_COVERAGE_STOP", air_plan)
        self.assertIn("AIR_COVERAGE_EXHAUSTED", air_plan)
        self.assertIn("AIR_NEW_TOWN_QUEUE", air_plan)
        self.assertIn('"AIR_STOP"', air_plan)
        self.assertIn("status=sleeping", air_plan)
        self.assertIn("status=exhausted", air_plan)

    def test_event_handler_town_founded_rewake(self):
        events = read_nut("event_handlers.nut")
        self.assertIn("AIR_COVERAGE_STOP", events)
        self.assertIn("AIR_NEW_TOWN_QUEUE.append", events)
        self.assertIn("AIR_COVERAGE_EXHAUSTED = false;", events)

    def test_persist_roundtrip_support(self):
        persist = read_nut("persist.nut")
        self.assertIn("airCoverageExhausted", persist)
        self.assertIn("airNewTownQueue", persist)

    def test_hygiene_no_forbidden_constructs(self):
        for name in ("air_planning.nut", "event_handlers.nut", "persist.nut"):
            content = read_nut(name)
            self.assertNotIn(".find(", content, f".find( interdit dans {name}")


if __name__ == "__main__":
    unittest.main()
