"""Frozen legacy bytes remain checked after subtracting exact ROAD100 hunks."""
from pathlib import Path
import json
import unittest

from road100_off_projection import FIXTURE, SITE_FIRST_FIXTURE, V30A_FIXTURE, V31_FIXTURE, V31B_FIXTURE, V32_FIXTURE, V33_FIXTURE, V34_FIXTURE, V35_FIXTURE, ROOT, off_source


class Road100OptInProjectionTests(unittest.TestCase):
    def test_all_reviewed_hunks_project_and_projection_is_idempotent(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(fixture), {
            "builder_road.nut", "candidates.nut", "economy.nut", "globals_pre.nut",
            "info.nut", "opcode_exact.nut", "settings.nut", "task_projects.nut", "task_road.nut",
        })
        site_fixture = json.loads(SITE_FIRST_FIXTURE.read_text(encoding="utf-8"))
        self.assertIn("po01c_regen.nut", site_fixture)
        self.assertIn("candidates.nut", site_fixture)
        # ROAD100-14 ajoute une reconciliation de la troisieme station
        # uniquement si road100TourActive figure dans la ligne sauvegardee.
        # Ce hunk doit lui aussi etre retire pour la projection historique.
        self.assertEqual(set(site_fixture) - set(fixture),
                         {"po01c_regen.nut", "po01c_generators.nut", "persist.nut"})
        v30_fixture = json.loads(V30A_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v30_fixture), {
            "builder_road.nut", "candidates.nut", "economy.nut", "globals_pre.nut",
            "info.nut", "settings.nut", "task_road.nut",
        })
        v31_fixture = json.loads(V31_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v31_fixture), {
            "builder_road.nut", "economy.nut", "globals_pre.nut",
            "info.nut", "settings.nut", "task_road.nut",
        })
        v31b_fixture = json.loads(V31B_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v31b_fixture), {"builder_road.nut"})
        self.assertTrue(any("OpexRoad100PaxFixedFleetEconomics" in h["after"]
                            for h in v31b_fixture["builder_road.nut"]))
        v32_fixture = json.loads(V32_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v32_fixture), {
            "builder_road.nut", "candidates.nut", "globals_pre.nut",
            "info.nut", "opcode_exact.nut", "settings.nut", "task_road.nut",
        })
        v33_fixture = json.loads(V33_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v33_fixture), {
            "builder_road.nut", "candidates.nut", "globals_pre.nut",
            "info.nut", "opcode_exact.nut", "settings.nut", "task_road.nut",
        })
        self.assertTrue(all("OpexRoad100PaxFixedFleetEconomics" not in h["after"]
                            for h in v33_fixture["builder_road.nut"]))
        v34_fixture = json.loads(V34_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v34_fixture), {
            "builder_road.nut", "globals_pre.nut", "info.nut", "settings.nut",
        })
        self.assertTrue(any("ROAD100_LONG_MARKET" in h["after"]
                            for h in v34_fixture["builder_road.nut"]))
        v35_fixture = json.loads(V35_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(v35_fixture), {
            "builder_road.nut", "candidates.nut", "globals_pre.nut",
            "info.nut", "settings.nut", "opcode_exact.nut",
        })
        self.assertTrue(any("OpexRoad100PortalStitchTrace" in h["after"]
                            for h in v35_fixture["builder_road.nut"]))
        for name, changes in fixture.items():
            with self.subTest(name=name):
                self.assertTrue(changes)
                current = (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
                projected = off_source(name, current)
                self.assertNotEqual(projected, current)
                self.assertEqual(off_source(name, projected), projected)

    def test_partial_or_mutated_source_fails(self):
        current = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
        broken = current.replace('AIController.GetSetting("road100_intercity_site_fleet")',
                                 'AIController.GetSetting("unexpected_settings_alias")', 1)
        self.assertNotEqual(current, broken)
        with self.assertRaises(AssertionError):
            off_source("settings.nut", broken)


if __name__ == "__main__":
    unittest.main()
