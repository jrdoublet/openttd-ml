"""Independent contracts of bounded ASTAR/POSE rail repair options.

Static tests deliberately make no claim to compile Squirrel or run OpenTTD.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def body(text, label):
    pos = text.index("function " + label + "(")
    opening = text.index("{", pos)
    level = 0
    for end in range(opening, len(text)):
        if text[end] == "{":
            level += 1
        elif text[end] == "}":
            level -= 1
            if level == 0:
                return text[pos : end + 1]
    raise AssertionError("unclosed " + label)


class TestRailRepairAstarPose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pre = read("globals_pre.nut")
        cls.settings = read("settings.nut")
        cls.info = read("info.nut")
        cls.task = read("task_rail.nut")
        cls.builder = read("builder_rail.nut")
        cls.persist = read("persist.nut")

    def test_opt_in_default_zero_each_difficulty(self):
        for name, constant in (("rail_repair_astar_pair", "RAIL_REPAIR_ASTAR_PAIR"),
                               ("rail_repair_pose_order", "RAIL_REPAIR_POSE_ORDER")):
            with self.subTest(name=name):
                self.assertIn(constant + " <- false;", self.pre)
                self.assertEqual(self.settings.count('GetSetting("' + name + '")'), 1)
                block = re.search(r'name = "' + name + r'"(.*?)}\);', self.info, flags=re.S)
                self.assertIsNotNone(block)
                for difficulty in ("easy", "medium", "hard", "custom"):
                    self.assertRegex(block.group(1), difficulty + r"_value\s*=\s*0\b")

    def test_astar_selection_is_alternative_bounded_and_physical(self):
        helper = body(self.builder, "OpexRailRepairAlternatePair")
        self.assertIn("plansA.len() == 1 && plansB.len() == 1", helper)
        self.assertIn("limitA = plansA.len() < 8", helper)
        self.assertIn("limitB = plansB.len() < 8", helper)
        self.assertIn("dist > direct + 12", helper)
        self.assertIn("shift < 2 || shift > 12", helper)
        self.assertIn("AIMap.IsValidTile(pA.lead)", helper)
        self.assertNotIn("reverse", helper)
        step = body(self.task, "OpexAI::_continueRailSearch")
        self.assertIn('slice.stop == "ABND" || slice.stop == "NOPA"', step)
        self.assertIn("!state.astarRepairTried", step)
        self.assertIn("OpexRailRepairAlternatePair(state.plan.plansA, state.plan.plansB)", step)
        self.assertIn("if (cap > 900) cap = 900", step)
        self.assertIn("cap >= 250", step)
        self.assertIn("OpexCreateRailPathfinder([pair.a], [pair.b]", step)
        self.assertIn("state.astarRepairTried = true", step)
        self.assertIn("state.safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS", step)
        self.assertIn("state.spent += state.astarFirstSpent", step)
        self.assertIn("slice.iterations = state.spent", step)

    def test_astar_uses_existing_repair_search_resume_and_no_serialized_pathfinder(self):
        start = body(self.task, "OpexAI::_startRailSearch")
        self.assertIn("if (RAIL_REPAIR_ASTAR_PAIR)", start)
        self.assertIn("this._railSearch.astarRepairTried <- false", start)
        self.assertIn("this._railSearch.astarFirstSpent <- 0", start)
        self.assertIn("state.plan.iterationBudget", body(self.task, "OpexAI::_continueRailSearch"))
        self.assertIn("railSearchPending = this._railSearch != null", self.persist)
        self.assertIn("this._railSearch = null;", self.persist)
        self.assertIn("this._portfolioInvalidated = true;", self.persist)

    def test_pose_guard_requires_virgin_tiles_and_order_is_one_attempt(self):
        virgin = body(self.builder, "OpexRailRepairPoseVirgin")
        next_first = body(self.builder, "OpexRailRepairPoseFollowing")
        track = body(self.builder, "OpexBuildTrack")
        self.assertIn("t in seen", virgin)
        self.assertIn("AIRail.IsRailTile(t)", virgin)
        self.assertIn("AIRail.IsRailStationTile(t)", virgin)
        self.assertIn("AIBridge.IsBridgeTile(t)", virgin)
        self.assertIn("AITunnel.IsTunnelTile(t)", virgin)
        self.assertIn("i + 2 >= tiles.len() - 1", next_first)
        self.assertIn("AITile.IsBuildable(cur)", next_first)
        self.assertIn("AITile.IsBuildable(next)", next_first)
        self.assertLess(next_first.index("AIRail.BuildRail(cur, next, after)"),
                        next_first.index("AIRail.BuildRail(prev, cur, next)"))
        self.assertIn("AIRail.AreTilesConnected", next_first)
        self.assertIn("poseTried = true", track)
        self.assertIn("!poseTried && !isDouble && !V199_ROBUST_BUILD", track)
        self.assertIn("OpexRailRepairPoseFollowing(tiles, i)", track)
        self.assertIn("i++;", track)
        self.assertIn("return failed;", track)
        self.assertIn('"railPoseRepaired", 1', track)

    def test_pose_failure_uses_original_transaction_rollback(self):
        execute = body(self.builder, "OpexExecuteRailPlan")
        v190 = body(self.builder, "OpexV190ExecuteRailPlan")
        rollback = body(self.builder, "OpexRollback")
        self.assertIn("OpexRailRepairPoseVirgin(tiles)", execute)
        self.assertIn("poseSafe = true", execute)
        self.assertIn("OpexRailRepairPoseVirgin(tiles)", v190)
        self.assertIn("poseSafe <- true", v190)
        self.assertIn("OpexRollback(tiles, planA, planB, null, null)", execute)
        self.assertIn("OpexRollback(tiles, planA, planB, null, null)", v190)
        self.assertIn("AIVehicle.SellVehicle(vehicle)", rollback)
        self.assertIn("AIRail.RemoveRailStationTileRectangle", rollback)
        self.assertIn("AITile.DemolishTile(tiles[i])", rollback)
        record = body(self.task, "OpexAI::_recordRailAttempt")
        self.assertIn('if (RAIL_REPAIR_ASTAR_PAIR || RAIL_REPAIR_POSE_ORDER)', record)
        self.assertIn('" astar_repair="', record)
        self.assertIn('" pose_repair="', record)
        self.assertIn("p2Trace + repairTrace", record)


if __name__ == "__main__":
    unittest.main()
