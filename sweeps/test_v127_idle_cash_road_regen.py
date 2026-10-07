import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def rd(n):
    return (AI / n).read_text(encoding="utf-8")


class V127Contracts(unittest.TestCase):
    def test_setting_default_zero_four_difficulties(self):
        s = rd("info.nut")
        m = re.search(r'name = "v127_idle_cash_road_regen",(.*?)\}\);', s, re.S)
        self.assertIsNotNone(m)
        b = m.group(1)
        self.assertIn("AICONFIG_BOOLEAN", b)
        self.assertIn("0 = off (default)", b)
        for k in ("easy", "medium", "hard", "custom"):
            self.assertRegex(b, k + r"_value = 0\b")

    def test_loading_gated_by_c121(self):
        s = rd("settings.nut")
        self.assertRegex(
            s, r"V127_IDLE_CASH_ROAD_REGEN = C121_CATALOG_INCREMENTAL\s*&&\s*"
               r'AIController\.GetSetting\("v127_idle_cash_road_regen"\) != 0')

    def test_globals_default(self):
        g = rd("globals_pre.nut")
        self.assertIn("V127_IDLE_CASH_ROAD_REGEN <- false;", g)
        self.assertIn("V127_IDLE_CASH_MIN <- 100000;", g)

    def test_trigger_guarded_and_uses_existing_path(self):
        t = rd("scheduler_tasks.nut")
        self.assertIn("if (V127_IDLE_CASH_ROAD_REGEN) this._v127IdleCashRoadRegen(ym);", t)
        o = rd("orchestrator.nut")
        body = o[o.index("function OpexAI::_v127IdleCashRoadRegen"):
                 o.index("function OpexAI::_c77RefreshModeCatalog")]
        self.assertTrue(body.split("{", 1)[1].lstrip().startswith("if (!V127_IDLE_CASH_ROAD_REGEN"))
        self.assertIn('_c77EnqueueEntity(["road"], null, -1, true, "v127_idle_cash")', body)
        self.assertIn("V127_LAST_MONTH == ym", body)
        self.assertIn("OpexAvailableCapital()", body)
        self.assertIn("V127_IDLE_CASH_MIN", body)
        self.assertIn('OpexDecide("V127_ROAD_REGEN"', body)
        for w in ("month=", "cash=", "pool=", "reason="):
            self.assertIn(w, body)

    def test_no_reserved_words(self):
        o = rd("orchestrator.nut")
        body = o[o.index("function OpexAI::_v127IdleCashRoadRegen"):
                 o.index("function OpexAI::_c77RefreshModeCatalog")]
        for w in ("parent", "clone", "base"):
            self.assertNotRegex(body, r"\blocal\s+" + w + r"\b")


if __name__ == "__main__":
    unittest.main()
