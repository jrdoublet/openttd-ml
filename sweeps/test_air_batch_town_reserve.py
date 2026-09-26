"""Contrats de air_batch_town_reserve : une ville neuve par lot, defaut 0."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


class AirBatchTownReserveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.projects = read("ai/OpexAI/projects.nut")
        cls.task_projects = read("ai/OpexAI/task_projects.nut")
        cls.task_air = read("ai/OpexAI/task_air.nut")

    def test_setting_is_wired_default_off(self):
        start = self.info.index('name = "air_batch_town_reserve"')
        setting = self.info[start:self.info.index("});", start)]
        self.assertIn("easy_value = 0", setting)
        self.assertIn("medium_value = 0", setting)
        self.assertIn("hard_value = 0", setting)
        self.assertIn("custom_value = 0", setting)
        self.assertIn("flags = AICONFIG_BOOLEAN", setting)
        self.assertIn("AIR_BATCH_TOWN_RESERVE <- false;", self.globals)
        self.assertIn(
            'AIR_BATCH_TOWN_RESERVE = AIController.GetSetting("air_batch_town_reserve") != 0;',
            self.settings,
        )
        self.assertEqual(self.info.count('name = "air_batch_town_reserve"'), 1)

    def test_selection_keeps_one_new_town_and_leaves_the_pool(self):
        towns = body(self.projects, "function OpexAirProjectNewSlotTowns(")
        self.assertIn('project.mode != "air"', towns)
        self.assertIn("if (!reuseA)", towns)
        self.assertIn("if (!reuseB)", towns)
        self.assertIn("OpexAirSlotTownId(plan.siteA.anchor)", towns)
        self.assertIn("OpexAirSlotTownId(plan.siteB.anchor)", towns)
        self.assertNotIn("candidateGroups", towns)

        compact = body(self.projects, "function OpexAirBatchTownReserveCompact(")
        self.assertIn("if (!AIR_BATCH_TOWN_RESERVE || best == null) return 0;", compact)
        self.assertIn("OpexAirProjectNewSlotTowns(project)", compact)
        self.assertIn("best.resize(0);", compact)
        self.assertNotIn("candidateGroups", compact)
        self.assertNotIn("alternatives", compact)
        self.assertIn('OpexAirBatchTownReserveNote("dropped", dropped)', compact)

        select = body(self.projects, "function OpexProjectSelectAffordable(")
        self.assertIn("if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveCompact(affordable);", select)
        self.assertIn(
            "OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);",
            select,
        )
        self.assertLess(
            select.index("OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);"),
            select.index("if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveCompact(affordable);"),
        )

    def test_build_batch_and_dead_counter_are_gated(self):
        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        self.assertIn("if (AIR_BATCH_TOWN_RESERVE) airReserveTowns = {};", attempt)
        self.assertIn("OpexAirBatchTownReserveHit(airReserveTowns, project)", attempt)
        self.assertIn('OpexAirBatchTownReserveNote("dropped", 1)', attempt)
        dead = body(self.task_air, "function OpexAI::_tryBuildAirProject(")
        still = dead.index("if (!OpexAirBatchPlanStillLive(plan, this._lines))")
        note = dead.index('if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveNote("batch_plan_dead", 1);')
        reason = dead.index('reason = "batch_plan_dead"')
        self.assertLess(still, note)
        self.assertLess(note, reason)

    def test_probe_counts_drops_and_remaining_dead_under_existing_gates(self):
        note = body(self.projects, "function OpexAirBatchTownReserveNote(")
        self.assertIn("if (!C69_BOTTLENECK_PROBE && !C78_SLOT_INTERCEPT_PROBE) return;", note)
        self.assertIn("AIR_BATCH_TOWN_RESERVE_DROPPED", note)
        self.assertIn("AIR_BATCH_TOWN_RESERVE_DEAD", note)
        self.assertIn("phase=air_batch_town_reserve", note)
        self.assertIn("batch_plan_dead=", note)
        self.assertIn("OpexC78SlotLog(fields)", note)
        self.assertIn("OpexC69Log(fields)", note)


if __name__ == "__main__":
    unittest.main()
