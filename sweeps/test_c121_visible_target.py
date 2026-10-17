"""Shared fleet guards for C121 visible competition; NoAI fixture covers the cap."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class TestVisibleFleetTarget(unittest.TestCase):
    def test_final_guard_is_before_purchase_and_after_replacement(self):
        text = (AI / "air_fleet.nut").read_text(encoding="utf-8")
        text = text[text.index('function OpexAirAddPlane('):]
        self.assertIn('if (C121_AIR_VISIBLE_COMPETITION)', text)
        self.assertLess(text.index('OpexAirMaybeReequip'), text.index('result.reason = "TARGET"'))
        self.assertLess(text.index('result.reason = "TARGET"'), text.index('AIVehicle.CloneVehicle'))
        self.assertIn('AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR', text)
        self.assertIn('OpexC121AirPhysicalTarget(line, catalog, lines)', text)

    def test_all_production_growth_calls_supply_shared_airports(self):
        task = (AI / "task_air.nut").read_text(encoding="utf-8")
        projects = (AI / "task_projects.nut").read_text(encoding="utf-8")
        self.assertEqual(task.count('OpexAirAddPlane(line, this._catalog, this._lines)'), 2)
        self.assertEqual(projects.count('OpexAirAddPlane(line, this._catalog, this._lines)'), 1)


if __name__ == "__main__":
    unittest.main()
