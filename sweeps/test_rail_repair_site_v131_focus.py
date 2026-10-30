"""Contracts for the two new default-OFF rail repair interventions.

These source checks guard the integration contracts. A real OpenTTD smoke and
causal construction proof remain required; Python does not execute NoAI.
"""

from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def function(text, start):
    begin = text.index("function " + start + "(")
    opening = text.index("{", begin)
    depth = 0
    for cursor in range(opening, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[begin : cursor + 1]
    raise ValueError(start)


class TestRailRepairSiteV131Focus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.globals = read("globals_pre.nut")
        cls.info = read("info.nut")
        cls.settings = read("settings.nut")
        cls.builder = read("builder_rail.nut")
        cls.rail = read("task_rail.nut")
        cls.persist = read("persist.nut")

    def test_both_controls_are_off_for_all_difficulties(self):
        for name, glob in (("rail_repair_join_site", "RAIL_REPAIR_JOIN_SITE"),
                           ("rail_repair_v131_focus", "RAIL_REPAIR_V131_FOCUS")):
            with self.subTest(setting=name):
                block = re.search(r'name = "' + name + r'"(.*?)}\);', self.info, re.S)
                self.assertIsNotNone(block)
                for difficulty in ("easy", "medium", "hard", "custom"):
                    self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*0\b")
                self.assertEqual(self.settings.count(f'GetSetting("{name}")'), 1)
                self.assertIn(glob + " <- false;", self.globals)
        self.assertIn('V131_RAIL_REPAIR = AIController.GetSetting("v131_rail_repair") != 0;', self.settings)
        self.assertIn("V131_RAIL_REPAIR = V131_RAIL_REPAIR || RAIL_REPAIR_V131_FOCUS;", self.settings)

    def test_site_preserves_existing_station_and_tests_actual_command(self):
        join = function(self.builder, "OpexRailRepairJoinSite")
        plan = function(self.builder, "OpexRailPlatformPlans")
        spread = function(self.builder, "OpexV264TrySpreadAnchor")
        self.assertIn("AIStation.IsValidStation(stationId)", join)
        self.assertIn("station.distant_join_stations", join)
        self.assertIn("platform.length > spread", join)
        self.assertRegex(join, r"platform\.length, 1, 2\)")
        self.assertIn("local probe = AITestMode();", spread)
        self.assertIn("AIRail.BuildRailStation(anchor, direction, 1, length, stationId)", spread)
        self.assertIn("AITile.IsBuildable(lead)", spread)
        self.assertIn('(("shared_dest" in candidate) && candidate.shared_dest)', plan)
        self.assertIn("jointPlansB.len() == 0", plan)
        self.assertIn("OpexRailRepairJoinSite(candidate.joinPlatform, candidate.joinStationId", plan)
        self.assertIn("p.stationId <- candidate.joinStationId", plan)
        self.assertIn("if (strictOriginReuseJoin)", plan)
        self.assertIn("EB2_NEW_STATION_FALLBACK == 0", plan)
        self.assertLess(plan.index("OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB)"),
                        plan.index("jointPlansB = OpexRailRepairJoinSite("))

    def test_site_repair_is_countable_only_after_both_sites_exist(self):
        plan = function(self.builder, "OpexRailPlatformPlans")
        self.assertIn('if (repairedJoinB) candidate.rawset("railSiteRepair", 1);', plan)
        self.assertLess(plan.index('if (plansA.len() > 0)'),
                        plan.index('if (repairedJoinB) candidate.rawset("railSiteRepair", 1);'))
        self.assertIn('OpexDecide("RAIL_SITE_REPAIR"', plan)
        record = function(self.rail, "OpexAI::_recordRailAttempt")
        self.assertEqual(record.count('" site_repair="'), 1)
        self.assertEqual(record.count('" v131_repair="'), 1)
        self.assertIn('if (RAIL_REPAIR_JOIN_SITE || RAIL_REPAIR_V131_FOCUS)', record)
        self.assertIn('" phases=" + phasesStr + p2Trace + repairTrace', record)
        self.assertIn('p2Trace + repairTrace', record)
        self.assertIn('OpexDecide("RAIL_BUILD"', record)

    def test_focused_repair_has_one_bounded_local_search_and_rollback(self):
        plan = function(self.rail, "OpexAI::_v131PlanRepairs")
        start = function(self.rail, "OpexAI::_v131TryStartRepair")
        commit = function(self.rail, "OpexAI::_v131CommitRepair")
        self.assertIn('"focus_not_local"', plan)
        self.assertIn('"focus_station_far"', plan)
        self.assertIn('"focus_not_splice"', plan)
        self.assertIn("shiftA != null && shiftB == null", plan)
        self.assertIn("shiftB != null && shiftA == null", plan)
        self.assertIn('if (RAIL_REPAIR_V131_FOCUS && budget > 900) budget = 900;', start)
        self.assertIn('kind = "v131_repair"', start)
        self.assertIn('OpexTestRailTrack(tiles, structures)', commit)
        self.assertIn('this._v131FailRepair(state, "retest")', commit)
        self.assertIn("OpexV131WriteRepairedPlan", commit)
        self.assertIn("OpexRollback(null, planA, planB, null, null)", self.builder)

    def test_save_load_drops_nonserializable_repair_search(self):
        self.assertIn('railSearchPending = this._railSearch != null', self.persist)
        self.assertIn('this._railSearch = null;', self.persist)
        self.assertIn('this._railReadyStock = {};', self.persist)
        self.assertIn('this._railStockCooldown = {};', self.persist)
        self.assertIn('this._portfolioInvalidated = true;', self.persist)
        self.assertIn('this._activeWorker = null;', self.persist)


if __name__ == "__main__":
    unittest.main()
