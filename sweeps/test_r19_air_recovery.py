"""R19 source contracts only: no NoAI failure injection or Save/Load execution."""
from pathlib import Path
import re
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    return source.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


class TestAirRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ai = ROOT / "ai/OpexAI"
        cls.recovery = (ai / "air_recovery.nut").read_text(encoding="utf-8")
        cls.builder = read_builder_air()
        cls.persist = (ai / "persist.nut").read_text(encoding="utf-8")
        cls.task = (ai / "task_air.nut").read_text(encoding="utf-8")
        cls.scheduler = (ai / "scheduler_tasks.nut").read_text(encoding="utf-8")
        cls.cleanup = function(cls.recovery, "OpexAirContinueRollback")
        cls.route = function(cls.builder, "OpexBuildAirRoute")

    def test_state_registered_before_any_cleanup_command(self):
        rollback = function(self.builder, "OpexAirRollback")
        self.assertLess(rollback.index("OPEX_AIR_ROLLBACKS.append(ticket)"),
                        rollback.index("OpexAirContinueRollback(ticket)"))
        self.assertIn("vehicles = clone planes", rollback)
        self.assertIn("if (OpexAirContinueRollback(ticket)) {\n    OPEX_AIR_ROLLBACKS.pop();", rollback)
        self.assertIn('require("air_recovery.nut");', self.builder)

    def test_first_and_later_start_failures_keep_entire_built_inventory(self):
        start = self.route.split("foreach (aircraft in built)", 1)[1].split("if (AIR_JOINED_STOPS)", 1)[0]
        self.assertIn("if (!AIVehicle.StartStopVehicle(aircraft))", start)
        self.assertLess(start.index("result.error = AIError.GetLastError();"), start.index("OpexAirRollback("))
        self.assertRegex(start, r"OpexAirRollback\(reuseA \? null : airportA, reuseB \? null : airportB, built,\s*"
                               r"OpexAirPairKey\(plan.siteA, plan.siteB\)\);")
        self.assertIn('result.reason = "START";', start)
        self.assertIn("return result;", start)
        self.assertNotIn("result.ok = true", start)

    def test_sale_failure_and_running_aircraft_block_demolition(self):
        self.assertIn("if (AIVehicle.IsStoppedInDepot(vehicle))", self.cleanup)
        self.assertIn("if (AIVehicle.SellVehicle(vehicle)) continue;", self.cleanup)
        self.assertIn("remaining.append(vehicle);", self.cleanup)
        self.assertIn("ticket.vehicles = remaining;", self.cleanup)
        guard = self.cleanup.index("if (remaining.len() > 0) return false;")
        self.assertLess(guard, self.cleanup.index("AIAirport.RemoveAirport("))
        self.assertNotIn("StartStopVehicle", self.cleanup)

    def test_retry_preserves_existing_halt_and_allows_service_conversion(self):
        self.assertIn("AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT)", self.cleanup)
        self.assertIn("AIOrder.GetOrderFlags(vehicle, AIOrder.ORDER_CURRENT)", self.cleanup)
        self.assertIn("flags == AIOrder.OF_INVALID || (flags & AIOrder.OF_STOP_IN_DEPOT) != 0", self.cleanup)
        self.assertIn("if (!halted) AIVehicle.SendVehicleToDepot(vehicle);", self.cleanup)
        self.assertNotIn("ResolveOrderPosition", self.cleanup)

    def test_airport_removal_checks_ownership_users_and_command_success(self):
        self.assertIn("!AICompany.IsMine(AITile.GetOwner(tile))", self.cleanup)
        self.assertIn("line.stationA == tile || line.stationB == tile", self.cleanup)
        self.assertIn("AIVehicleList_Station(station)", self.cleanup)
        self.assertIn("if (users.Count() > 0) used = true;", self.cleanup)
        self.assertIn("if (!used && AIAirport.RemoveAirport(tile)) continue;", self.cleanup)
        self.assertIn("airports.append(tile);", self.cleanup)
        self.assertIn("return airports.len() == 0;", self.cleanup)
        # Every route rollback still excludes both reused endpoints (BFAIL has only A).
        for call in re.findall(r"OpexAirRollback\((.*?);", self.route, flags=re.S):
            self.assertTrue(call.startswith("reuseA ? null : airportA,"))
            self.assertTrue("reuseB ? null : airportB" in call or ", null, []" in call)

    def test_retry_is_blocked_before_build_and_before_batch_bypass(self):
        blocks = function(self.recovery, "OpexAirRecoveryBlocksPlan")
        self.assertIn("OpexAirPairKey(plan.siteA, plan.siteB)", blocks)
        self.assertIn("ticket.pairKey == pairKey", blocks)
        self.assertIn("local a = plan.siteA.anchor;", blocks)
        self.assertIn("local b = plan.siteB.anchor;", blocks)
        self.assertIn("if (tile == a || tile == b) return true;", blocks)
        self.assertLess(self.route.index("OpexAirRecoveryBlocksPlan(plan)"), self.route.index("budget.begin();"))
        live = function(self.task, "OpexAirBatchPlanStillLive")
        self.assertIn("if (OpexAirRecoveryBlocksPlan(plan)) return false;", live)
        site = function(self.builder, "OpexAirSiteStillBuildable")
        self.assertLess(site.index("OpexAirRecoveryOwnsAirport"), site.index("if (reuse)"))
        lines = (ROOT / "ai/OpexAI/lines.nut").read_text(encoding="utf-8")
        abandon = function(lines, "OpexBuildFailureIsAbandonable")
        self.assertLess(abandon.index('result.reason == "RECOVERY"'), abandon.index("ABANDON_MEMORY_TRANSIENT_GUARD"))

    def test_recovery_is_saved_even_in_short_format_without_feature_gates(self):
        save = function(self.persist, "OpexAI::Save")
        for target in ("shortSave", "saveObj"):
            self.assertIn(f"if (OPEX_AIR_ROLLBACKS.len() > 0) {target}.airRollbacks <- OPEX_AIR_ROLLBACKS;", save)
        load = function(self.persist, "OpexAI::Load")
        self.assertLess(load.index("OPEX_AIR_ROLLBACKS = [];"), load.index("if (data == null) return;"))
        self.assertIn('if ("airRollbacks" in data) OPEX_AIR_ROLLBACKS = OpexLoadAirRollbacks(data.airRollbacks);', load)

    def test_loader_validates_and_copies_without_world_api(self):
        load = function(self.recovery, "OpexLoadAirRollbacks")
        for check in ('typeof data != "array"', 'typeof ticket != "table"', 'ticket.version != 1',
                      'typeof ticket.vehicles != "array"', 'typeof ticket.airports != "array"',
                      'typeof ticket.pairKey != "string"', 'typeof ticket.nextDate != "integer"',
                      'typeof id != "integer" || id < 0', 'if (!valid) continue;'):
            self.assertIn(check, load)
        self.assertIn("vehicles = clone ticket.vehicles", load)
        self.assertIn("airports = clone ticket.airports", load)
        self.assertNotRegex(load, r"\bAI[A-Za-z]+\.")

    def test_reload_prunes_disappeared_ids_before_new_construction(self):
        reconcile = function(self.persist, "OpexAI::_reconcileAfterLoad")
        self.assertIn("OpexAirReconcileRollbacks();", reconcile)
        prune = function(self.recovery, "OpexAirReconcileRollbacks")
        self.assertIn("if (AIVehicle.IsValidVehicle(vehicle)) vehicles.append(vehicle);", prune)
        self.assertIn("ticket.vehicles = vehicles;", prune)
        self.assertIn("OPEX_AIR_ROLLBACKS = pending;", prune)
        self.assertNotIn("SellVehicle", prune)
        self.assertNotIn("RemoveAirport", prune)

    def test_one_ticket_per_scrap_with_rotation_and_bounded_retry_frequency(self):
        dispatch = function(self.scheduler, "OpexAI::_dispatchScrap")
        self.assertIn("OpexAirProcessRollbacks(this._lines);", dispatch)
        process = function(self.recovery, "OpexAirProcessRollbacks")
        self.assertIn("AIDate.GetCurrentDate() >= ticket.nextDate", process)
        self.assertEqual(process.count("OpexAirContinueRollback(ticket, lines)"), 1)
        self.assertIn("local rotated = OPEX_AIR_ROLLBACKS.slice(1);", process)
        self.assertIn("rotated.append(ticket);", process)
        self.assertIn("OPEX_AIR_ROLLBACKS = rotated;", process)
        # Only confirmed completion may remove a ticket from the published queue.
        rotation = process.split("local rotated =", 1)[1]
        self.assertNotIn(".remove(", rotation)
        self.assertNotIn("OPEX_AIR_ROLLBACKS.append(", process)
        self.assertIn("ticket.nextDate = AIDate.GetCurrentDate() + 30;", self.cleanup)
        self.assertNotRegex(process, r"\b(?:foreach|while|Sleep)\s*\(")
        self.assertNotIn("TIMEOUT", self.recovery)  # never forget unsold survivors


if __name__ == "__main__":
    unittest.main()