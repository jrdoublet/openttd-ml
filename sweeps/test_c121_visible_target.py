"""Shared fleet guards for C121 visible competition; NoAI fixture covers the cap."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class TestVisibleFleetTarget(unittest.TestCase):
    def test_final_guard_is_before_purchase_and_after_replacement(self):
        text = (AI / "air_fleet.nut").read_text(encoding="utf-8")
        self.assertNotIn("function OpexC121AirTargetLimit(", text)
        self.assertNotIn("function OpexC121AirPhysicalTarget(", text)
        text = text[text.index('function OpexAirAddPlane('):]
        self.assertNotIn('C121_AIR_VISIBLE_COMPETITION', text)
        self.assertNotIn('OpexAirMaybeReequip', text)
        self.assertNotIn('result.reason = "TARGET"', text)
        self.assertIn('AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR', text)
        self.assertNotIn('OpexC121AirPhysicalTarget(line, catalog, lines)', text)

    def test_all_production_growth_calls_supply_shared_airports(self):
        task = (AI / "task_air.nut").read_text(encoding="utf-8")
        projects = (AI / "task_projects.nut").read_text(encoding="utf-8")
        self.assertEqual(task.count('OpexAirAddPlane(line, this._catalog, this._lines)'), 1)
        # Le constructeur de flotte utilise toujours les trois memes
        # informations AIR et passe en quatrieme un garde N75 opt-in.
        self.assertEqual(projects.count('OpexAirAddPlane(line, this._catalog, this._lines,'), 1)
        self.assertIn('N75_AIR_TRUE_QUOTE == 2 && ("n75QuoteEngine" in entry)', projects)


if __name__ == "__main__":
    unittest.main()
