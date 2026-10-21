"""Contrats V301 : correctifs NOTRAIN (masque v301_notrain_fix, defaut 0).

- reglage declare a 0 aux quatre niveaux, lu une fois, globale initialisee ;
- bit 1 : NOTRAIN/ORDFAIL ecartent la paire ;
- bit 2 : borne vehicle.max_train_length etendue au fret ;
- bit 4 : la rame garde ses wagons au lieu d'echouer (longueur mesuree ou ERR_VEHICLE_TOO_LONG),
  au moins un wagon, wagon isole vendu et retire du rollback.
"""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV301NotrainFix(unittest.TestCase):
    def test_setting_default_zero_and_loaded_once(self):
        block = re.search(r'AddSetting\(\{\s*name = "v301_notrain_fix",(.*?)\}\);', read("info.nut"), re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertEqual(read("settings.nut").count('GetSetting("v301_notrain_fix")'), 1)
        self.assertIn("V301_NOTRAIN_FIX <- 0;", read("globals_pre.nut"))

    def test_bit1_abandons_pair(self):
        self.assertIn('((V301_NOTRAIN_FIX & 1) && (result.reason == "NOTRAIN" || result.reason == "ORDFAIL"))',
                      read("task_rail.nut"))

    def test_bit8_trkfail_abandons_pair(self):
        self.assertIn('((V301_NOTRAIN_FIX & 8) && result.reason == "TRKFAIL")', read("task_rail.nut"))
        self.assertIn("v301Fix <= 15)", read("settings.nut"))

    def test_bit2_freight_cap(self):
        self.assertIn('(kind != "pax" && (V301_NOTRAIN_FIX & 2))', read("economy.nut"))

    def test_bit4_trim_keeps_at_least_one_wagon(self):
        body = function_body(read("builder_rail.nut"), "function OpexBuildTrains(")
        self.assertEqual(body.count("OpexV301Trim("), 2)
        self.assertEqual(body.count("(V301_NOTRAIN_FIX & 4) && w > 0"), 2)
        self.assertIn("AIError.GetLastError() == AIVehicle.ERR_VEHICLE_TOO_LONG", body)
        trim = function_body(read("builder_rail.nut"), "function OpexV301Trim(")
        self.assertIn("rollbackVehicles.pop();", trim)
        self.assertIn("AIVehicle.SellVehicle(car);", trim)
        self.assertLess(trim.index("AIError.GetLastError()"), trim.index("SellVehicle"))


if __name__ == "__main__":
    unittest.main()
