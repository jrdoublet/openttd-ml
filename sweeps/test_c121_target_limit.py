"""Target-limit integration contracts; executable assertions live in the NoAI fixture."""
from pathlib import Path
import unittest

from campaign_freeze import parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class TestTargetLimit(unittest.TestCase):
    def test_setting_is_off_and_scoped_to_c121(self):
        self.assertEqual(parse_ai_settings(AI / "info.nut")["c121_air_target_limit"], 0)
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('C121_AIR_TARGET_LIMIT = C121_AIR_ECONOMICS\n'
                      '      && AIController.GetSetting("c121_air_target_limit") != 0;', settings)

    def test_both_build_paths_cap_target_and_keep_raw_economics(self):
        text = (AI / "task_air.nut").read_text(encoding="utf-8")
        self.assertEqual(text.count('builtLine.targetAirPlanes = OpexC121AirPhysicalTarget('), 2)
        self.assertEqual(text.count('local modelTarget = builtLine.targetAirPlanes;'), 2)
        self.assertIn('if (have >= limit)', text)
        self.assertLess(text.index('"c121_target_reached"'), text.index('local c121BelowTarget'))

    def test_stale_project_cannot_use_legacy_average_after_target(self):
        for name in ("projects_builders.nut", "projects_selection.nut"):
            text = (AI / name).read_text(encoding="utf-8")
            self.assertIn('have + entry.want > line.targetAirPlanes', text)

    def test_final_guard_is_before_purchase_and_after_replacement(self):
        text = (AI / "air_fleet.nut").read_text(encoding="utf-8")
        text = text[text.index('function OpexAirAddPlane('):]
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
