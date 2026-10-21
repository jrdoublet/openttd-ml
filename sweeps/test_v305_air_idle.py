"""Contrats V305 : V269 s'ouvre quand l'aerien a fini de poser des lignes, sans condition d'annee.

Verifie :
- reglage v305_air_idle_months a defaut 0 aux 4 niveaux, lu une seule fois, globale declaree ;
- au defaut, la condition historique de V269 (annee >= depart + N) reste en place ;
- a M > 0, la condition d'annee est remplacee par les mois sans ligne aerienne neuve ;
- OpexV305AirIdleMonths : sans etat sauvegarde, sans closure ni .find() ; transcription Python.
"""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def air_idle_months(lines, date):
    """Transcription de OpexV305AirIdleMonths (date en jours, annee -> 1er janvier = 365 * an)."""
    last = -1
    for line in lines:
        if line.get("mode") != "air":
            continue
        d = line["buildDate"] if "buildDate" in line else (365 * line["year"] if "year" in line else -1)
        last = max(last, d)
    if last < 0:
        return 999
    return (date - last) // 30


class TestV305AirIdle(unittest.TestCase):
    def setUp(self):
        self.info = read("info.nut")
        self.orch = read("orchestrator.nut")

    def test_setting_default_zero_and_loaded_once(self):
        block = re.search(r'name = "v305_air_idle_months",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertIn("max_value = 36", block.group(1))
        self.assertEqual(read("settings.nut").count('GetSetting("v305_air_idle_months")'), 1)
        self.assertIn("V305_AIR_IDLE_MONTHS <- 0;", read("globals_pre.nut"))

    def test_default_keeps_year_condition(self):
        body = function_body(self.orch, "function OpexAI::_v217RailRefill(")
        self.assertIn("if (V305_AIR_IDLE_MONTHS > 0) {", body)
        self.assertIn("V269_RELAXED = year >= OPEX_START_YEAR + V269_RAIL_LATE_RELAX && cash >= V269_IDLE_CASH_MIN;", body)
        self.assertIn("V269_RELAXED = airIdle >= V305_AIR_IDLE_MONTHS && cash >= V269_IDLE_CASH_MIN;", body)
        self.assertIn("OpexV305AirIdleMonths(this._lines, date)", body)

    def test_helper_stateless(self):
        body = function_body(self.orch, "function OpexV305AirIdleMonths(")
        self.assertNotIn("function(", body)
        self.assertNotIn(".find(", body)
        self.assertNotIn("<-", body)

    def test_air_idle_simulation(self):
        self.assertEqual(air_idle_months([], 1000), 999)
        self.assertEqual(air_idle_months([{"mode": "rail", "buildDate": 10}], 1000), 999)
        lines = [{"mode": "air", "buildDate": 100}, {"mode": "air", "buildDate": 700}, {"mode": "rail", "buildDate": 990}]
        self.assertEqual(air_idle_months(lines, 1000), 10)
        self.assertEqual(air_idle_months([{"mode": "air", "year": 2}], 365 * 2 + 60), 2)


if __name__ == "__main__":
    unittest.main()
