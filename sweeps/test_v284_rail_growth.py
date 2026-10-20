"""Contrats V284. Ne compilent pas Squirrel : smoke moteur distinct requis."""
import hashlib
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV284RailGrowth(unittest.TestCase):
    def setUp(self):
        self.code = read("task_v284.nut")

    def test_single_setting_default_three_and_loaded_once(self):
        info = read("info.nut")
        block = re.search(r'AddSetting\(\{\s*name = "v284_rail_growth",(.*?)\}\);',
                          info, re.S).group(1)
        # Defaut 3 depuis le 20/10 (decision utilisateur apres le 40x10 +136 k).
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*3\b")
        self.assertIn("min_value = 0, max_value = 10", block)
        self.assertEqual(read("settings.nut").count('GetSetting("v284_rail_growth")'), 1)
        self.assertIn("V284_RAIL_GROWTH <- 0;", read("globals_pre.nut"))
        self.assertNotIn('name = "v270_rail_late_growth"', info)
        self.assertEqual(info.count("AddSetting("), 78)

    def test_off_expansion_is_master_a9437f8_after_removing_guards(self):
        body = function_body(read("task_rail.nut"), "function OpexAI::_expandRailLines(year)")
        body = body.replace(
            "  /* Port du declencheur V270 c71b707 : avant la garde A*, sans prendre son creneau. */\n"
            "  if (V284_RAIL_GROWTH > 0 && OpexV284Select(this, year)) return;\n", "")
        body = body.replace(
            '        if (V284_RAIL_GROWTH > 0 && this._v284State != null && (("kind" in line) && line.kind == "freight")) continue;\n', "")
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),
                         "c98e8035f3dd2511d94dedff7660b3c726c84bfb43c18bc62f81fc50ac0982f3")

    def test_master_transaction_and_builder_are_unchanged(self):
        for name, signature, digest in [
            ("task_rail.nut", "function OpexAI::_continueRailExpansion()",
             "2fe1df594c6ef94ef54c29f9d0e8ee0c43bfcb2de6bbf830475889720fe1049f"),
            ("builder_rail.nut", "function OpexBuildTrains(",
             "d8be0ba88eddb6bc870948f626f7476c0a24c3dbf639e9cd93f26505b7ebab7c"),
        ]:
            body = function_body(read(name), signature)
            self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), digest)

    def test_off_orchestrator_is_master_and_profiled_loop_uses_same_hook(self):
        body = function_body(read("orchestrator.nut"), "function OpexAI::_runOrchestratorTick()")
        body = body.replace(
            "  /* Point commun aux boucles normale et _mainLoopProfiled. OFF court-circuite. */\n"
            "  if (V284_RAIL_GROWTH > 0) OpexV284Tick(this);\n"
            "  if (V284_RAIL_GROWTH <= 0 || !OpexV284Busy(this)) this._v257ReactiveStep();",
            "  this._v257ReactiveStep();")
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),
                         "8fad3902e5b21792e795d6ae453bfb9112be0d708daf5466fbc6cd65aa3668c8")
        profiled = function_body(read("probes.nut"), "function OpexAI::_mainLoopProfiled()")
        self.assertIn("this._runOrchestratorTick();", profiled)

    def test_selection_requires_idle_cash_freight_backlog_and_limits_cadence(self):
        body = function_body(self.code, "function OpexV284Select(")
        for contract in [
            "year < OPEX_START_YEAR + V284_RAIL_GROWTH",
            "OpexAvailableCapital() < 1000000", 'line.kind != "freight"',
            "line.lastProfit <= 0", "waiting < wagon.capacity",
            "waiting < capacity", "owner._v257Pending != null",
            "owner._railExpansion != null", "state.nextDate = date + 30",
            "state.dates.rawset(line.lineId, date + 365)",
            "line.distance.tofloat() * waiting / capacity",
            "line.vehicles.len() != 1", "OpexV163Wagons2(line) > 0",
        ]:
            self.assertIn(contract, body)
        self.assertNotIn("CloneVehicle", self.code)

    def test_locomotive_preserves_speed_and_track_compatibility(self):
        body = function_body(self.code, "function OpexV284Equipment(")
        for contract in ["OpexRailEffectiveSpeed(current", "OpexRailEffectiveSpeed(loco",
                         "nextSpeed < speed", "loco.speed < current.speed",
                         "AIEngine.HasPowerOnRail", "AIEngine.CanRunOnRail"]:
            self.assertIn(contract, body)
        self.assertNotIn("0.85", body)

    def test_both_lengths_and_actual_builder_measurements_are_used(self):
        body = function_body(self.code, "function OpexV284Limit(")
        self.assertIn('AIGameSettings.GetValue("vehicle.max_train_length")', body)
        self.assertIn("line.platformLength", body)
        self.assertIn("if (limit < length) length = limit", body)
        tick = function_body(self.code, "function OpexV284Tick(")
        self.assertIn("pending.wagons, limit, false", tick)
        self.assertIn("pending.wagons > OpexRailNominalMaxWagons(limit)", tick)
        self.assertIn("trainLength + carLength > trainLengthLimit", read("builder_rail.nut"))

    def test_loop_ready_before_new_train_and_no_early_sale(self):
        tick = function_body(self.code, "function OpexV284Tick(")
        self.assertLess(tick.index("OpexV284BuildLoop"), tick.index("OpexBuildTrains"))
        self.assertLess(tick.index("AIOrder.CopyOrders"), tick.index("AIVehicle.StartStopVehicle(pending.newVehicle)"))
        self.assertLess(tick.index("AIVehicle.StartStopVehicle(pending.newVehicle)"),
                        tick.index("OpexV284Adopt"))
        self.assertIn('pending.phase == "committed" && !pending.add', tick)
        self.assertIn("AIVehicle.GetCargoLoad(oldVehicle, line.cargo) > 0", tick)
        self.assertIn("waitingNow < requiredWaiting", tick)

    def test_loop_geometry_is_bounded_and_accounting_is_shielded(self):
        body = function_body(self.code, "function OpexV284LoopPlan(")
        self.assertIn("attempt < 32", body)
        self.assertEqual(body.count("type = AIRail.SIGNALTYPE_PBS_ONEWAY"), 4)
        self.assertEqual(body.count("type = AIRail.SIGNALTYPE_PBS }"), 2)
        self.assertLess(body.index("AIAccounting()"), body.index("AITestMode()"))
        rollback = function_body(self.code, "function OpexV284RollbackLoop(")
        executable = re.sub(r"/\*.*?\*/", "", rollback, flags=re.S)
        self.assertNotIn("DemolishTile(", executable)
        self.assertIn("signal.before == AIRail.SIGNALTYPE_NONE", rollback)
        build = function_body(self.code, "function OpexV284BuildLoop(")
        self.assertLess(build.index("tracks != piece.before"), build.index("plan.started = true"))
        self.assertLess(build.index("plan.started = true"), build.index("AIRail.BuildRail"))

    def test_persistence_records_transaction_before_commands_and_adopts_by_identity(self):
        persist = read("persist.nut")
        self.assertIn("saveObj.v284Growth <- this._v284State", persist)
        self.assertIn('"v284Growth" in data', persist)
        self.assertIn('if (("v284Growth" in data)', persist)  # Load avant OpexLoadSettings.
        self.assertLess(persist.index("this._lines = liveLines"), persist.index("OpexV284Reconcile(this)"))
        tick = function_body(self.code, "function OpexV284Tick(")
        self.assertLess(tick.index('pending.phase = "building"'), tick.index("OpexBuildTrains"))
        self.assertLess(tick.index('pending.phase = "starting"'),
                        tick.index("AIVehicle.StartStopVehicle(pending.newVehicle)"))
        reconcile = function_body(self.code, "function OpexV284Reconcile(")
        self.assertIn("!AIVehicle.IsStoppedInDepot(pending.newVehicle)", reconcile)
        self.assertIn("OpexV284Adopt(owner, line, pending)", reconcile)
        self.assertIn('pending.phase = "rollback"', reconcile)
        self.assertNotIn("BuildVehicle", reconcile)
        self.assertNotIn("BuildTrains", reconcile)
        adopt = function_body(self.code, "function OpexV284Adopt(")
        self.assertIn("OpexWaterContains(line.vehicles, newVehicle)", adopt)
        self.assertIn("owner._saveProjection = null", adopt)

    def test_no_reserved_locals_closures_or_nonexistent_vehicle_maxspeed(self):
        self.assertNotRegex(self.code, r"\blocal\s+(clone|base|parent)\b")
        self.assertNotRegex(self.code, r"=\s*function\s*\(")
        self.assertNotIn("AIVehicle.GetMaxSpeed", self.code)
        self.assertNotIn("Sleep(", self.code)


if __name__ == "__main__":
    unittest.main()
