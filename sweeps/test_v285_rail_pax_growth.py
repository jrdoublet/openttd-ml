"""Tests de contrat source V285 : croissance des rames et quais voyageurs en rail seul (v285_rail_pax_growth)."""
from pathlib import Path
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV285RailPaxGrowth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("info.nut")
        cls.settings = read("settings.nut")
        cls.globals = read("globals_pre.nut")
        cls.main = read("main.nut")
        cls.economy = read("economy.nut")
        cls.task_rail = read("task_rail.nut")

    def test_setting_declared_in_info(self):
        self.assertIn('name = "v285_rail_pax_growth"', self.info)
        start = self.info.index('name = "v285_rail_pax_growth"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 3", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("flags = 0", block)

    def test_setting_loaded_in_settings(self):
        self.assertEqual(self.settings.count('GetSetting("v285_rail_pax_growth")'), 1)
        self.assertIn("V285_RAIL_PAX_GROWTH = (paxGrowth != null && paxGrowth > 0 && paxGrowth <= 3) ? paxGrowth : 0;", self.settings)

    def test_globals_declared(self):
        self.assertIn("V285_RAIL_PAX_GROWTH <- 0;", self.globals)

    def test_main_method_declared(self):
        self.assertIn("function _v285StartWagonExpansion(year);", self.main)

    def test_inert_at_zero(self):
        start = self.task_rail.index("function OpexV285Active()")
        end = self.task_rail.index("}", start)
        body = self.task_rail[start:end]
        self.assertIn("return V285_RAIL_PAX_GROWTH > 0;", body)

    def test_economy_platform_guarded(self):
        self.assertIn("(V285_RAIL_PAX_GROWTH & 1)", self.economy)
        self.assertIn('kind == "pax"', self.economy)
        self.assertIn("catalog.maxTrainLength", self.economy)

    def test_task_rail_wagon_expansion_guarded(self):
        self.assertIn("OpexV285Active() && (V285_RAIL_PAX_GROWTH & 2) && this._v285StartWagonExpansion(year)", self.task_rail)
        start = self.task_rail.index("function OpexAI::_v285StartWagonExpansion(year)")
        end = self.task_rail.index("\n/* Demarre une recherche A*", start)
        body = self.task_rail[start:end]
        self.assertIn('line.kind != "pax"', body)
        self.assertIn("OpexRailNominalMaxWagons(line.platformLength)", body)
        self.assertIn("waiting < trainPaxCapacity", body)
        self.assertIn("85 * line.effectiveSpeed", body)
        self.assertIn("this._continueRailExpansion()", body)


if __name__ == "__main__":
    unittest.main()
