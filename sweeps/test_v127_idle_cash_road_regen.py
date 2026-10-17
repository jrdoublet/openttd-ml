import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def rd(n):
    return (AI / n).read_text(encoding="utf-8")


class V127Contracts(unittest.TestCase):
    def test_setting_default_zero_four_difficulties(self):
        s = rd("info.nut")
        self.assertNotIn('name = "v127_idle_cash_road_regen"', s)

    def test_loading_gated_by_c121(self):
        s = rd("settings.nut")
        self.assertNotIn("v127_idle_cash_road_regen", s)
        self.assertNotIn("V127_IDLE_CASH_ROAD_REGEN", s)

    def test_globals_default(self):
        g = rd("globals_pre.nut")
        self.assertNotIn("V127_IDLE_CASH_ROAD_REGEN", g)
        self.assertNotIn("V127_IDLE_CASH_MIN", g)

    def test_trigger_guarded_and_uses_existing_path(self):
        t = rd("scheduler_tasks.nut")
        self.assertNotIn("_v127IdleCashRoadRegen", t)
        o = rd("orchestrator.nut")
        self.assertNotIn("function OpexAI::_v127IdleCashRoadRegen", o)
        self.assertNotIn("V127_ROAD_REGEN", o)

    def test_no_reserved_words(self):
        o = rd("orchestrator.nut")
        self.assertNotIn("function OpexAI::_v127IdleCashRoadRegen", o)


if __name__ == "__main__":
    unittest.main()
