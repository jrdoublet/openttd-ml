"""Contrats de air_batch_town_reserve : réglage et branche retirés (V232).

Le défaut était 0. La réserve d'une ville neuve par lot n'existait que derrière
ce drapeau. Le rejet batch_plan_dead et OpexAirSlotTownId restent.
"""
import unittest
from pathlib import Path
from opex_projects_source import read_projects_source


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class AirBatchTownReserveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.persist = read("ai/OpexAI/persist.nut")
        cls.projects = read_projects_source()
        cls.task_projects = read("ai/OpexAI/task_projects.nut")
        cls.task_air = read("ai/OpexAI/task_air.nut")
        cls.towns = read("ai/OpexAI/air_towns.nut")

    def test_setting_and_symbols_are_removed(self):
        self.assertNotIn('name = "air_batch_town_reserve"', self.info)
        self.assertNotIn("air_batch_town_reserve", self.settings)
        for symbol in (
            "AIR_BATCH_TOWN_RESERVE",
            "AIR_BATCH_TOWN_RESERVE_DROPPED",
            "AIR_BATCH_TOWN_RESERVE_DEAD",
        ):
            self.assertNotIn(symbol, self.globals)
            self.assertNotIn(symbol, self.settings)
            self.assertNotIn(symbol, self.persist)
            self.assertNotIn(symbol, self.projects)
            self.assertNotIn(symbol, self.task_projects)
            self.assertNotIn(symbol, self.task_air)

    def test_reserve_helpers_are_removed(self):
        for name in (
            "OpexAirProjectNewSlotTowns",
            "OpexAirBatchTownReserveNote",
            "OpexAirBatchTownReserveCompact",
            "OpexAirBatchTownReserveHit",
            "airReserveTowns",
        ):
            self.assertNotIn(name, self.projects)
            self.assertNotIn(name, self.task_projects)
            self.assertNotIn(name, self.task_air)

    def test_slot_town_and_dead_plan_discard_remain(self):
        self.assertEqual(self.towns.count("function OpexAirSlotTownId("), 1)
        self.assertIn("OpexAirSlotTownId(", self.task_projects)
        select = self.projects
        self.assertIn(
            'OpexProjectInsertDefensive(affordable, project, scoreKey, limit, true);',
            select,
        )
        self.assertIn("OpexC122ProbeExposure(affordable);", select)
        self.assertNotIn("OpexAirBatchTownReserve", select)
        self.assertIn('reason = "batch_plan_dead"', self.task_projects)
        self.assertIn("!OpexAirBatchPlanStillLive(project.payload, this._lines)", self.task_projects)
        self.assertIn('reason = "batch_plan_dead"', self.task_air)
        self.assertIn("!OpexAirBatchPlanStillLive(plan, this._lines)", self.task_air)


if __name__ == "__main__":
    unittest.main()
