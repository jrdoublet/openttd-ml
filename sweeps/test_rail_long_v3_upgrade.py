"""Contrats source non-moteur : RAIL-LONG v3 EXISTANT, opt-in seulement.

Ne traite pas des multi-locos non certifiees et ne lance PAS OpenTTD.
La verification Save/Load moteur necessite un smoke retenu par le prime.
"""

from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
SOURCE = (AI / "rail_long_v3_upgrade.nut").read_text(encoding="utf-8")
V2 = (AI / "task_rail_long_v2.nut").read_text(encoding="utf-8")


def function(name, text=SOURCE):
    pos = text.index("function " + name + "(")
    pos = text.index("{", pos)
    count = 0
    for stop in range(pos, len(text)):
        if text[stop] == "{":
            count += 1
        elif text[stop] == "}":
            count -= 1
            if count == 0:
                return text[pos:stop + 1]
    raise AssertionError(f"unterminated function {name}")


class RailLongV3ExistingContracts(unittest.TestCase):
    def test_occupied_extensions_wait_without_dropping_safety_guards(self):
        step = function("OpexRailLongV3UpgradeStep")
        for end in ("a", "b"):
            upper = end.upper()
            block = step[step.index(f'if (state.phase == "intent_{end}")'):]
            block = block[:block.index(f'OpexRailLongV2BuildPart(state, "{upper}")')]
            self.assertIn(f'OpexRailLongV2StationFree(state.tiles{upper})', block)
            self.assertIn(f'!OpexRailLongV2NoVehicleNear(state.tiles{upper})', block)
            self.assertIn(f'OpexRailLongV3UpgradeWait(state, "vehicle_near_{end}"', block)
            self.assertIn(f'"build_{end}_site_changed"', block)
        self.assertIn('"timeout_" + state.phase', step)

    def test_b_command_failure_is_distinct_from_commit_validation(self):
        step = function("OpexRailLongV3UpgradeStep")
        self.assertNotIn("build_b_or_commit", step)
        for end in ("a", "b"):
            self.assertIn(f'"build_{end}", "{end.upper()}", error', step)
        commit = function("OpexRailLongV3UpgradeCommitReason")
        for reason in ("line_unsafe", "identity", "station_id", "platform_a",
                       "platform_b", "metadata"):
            self.assertIn(f'return "{reason}"', commit)
        self.assertIn('"commit_" + reason', step)

    def test_complete_platform_geometry_is_certified_before_adoption(self):
        platform = function("OpexRailLongV3UpgradePlatformOK")
        for check in ("OpexRailLongV2ExtendPlan", "plan.step != step",
                      "plan.lead != expectedLead", "AIRail.GetRailStationDirection"):
            self.assertIn(check, platform)
        metadata = function("OpexRailLongV3UpgradeMetadataSafe")
        for end in ("A", "B"):
            self.assertIn(f'OpexRailLongV3UpgradePlatformOK(state.target{end}, state.station{end}Id)', metadata)

    def test_explicit_depot_order_preserves_old_orders_and_checks_empty_train(self):
        step = function("OpexRailLongV3UpgradeStep")
        self.assertNotIn("AIVehicle.SendVehicleToDepot", step)
        self.assertNotIn("RAIL_EXPAND_APPROACH_TILES", step)
        self.assertIn("AIVehicle.GetState(state.vehicle) == AIVehicle.VS_AT_STATION", step)
        self.assertIn("AIRail.GetRailDepotFrontTile(state.depot)", step)
        self.assertIn("AIEngine.HasPowerOnRail", step)
        self.assertLess(step.index('state.explicitDetour = true'),
                        step.index('AIOrder.AppendOrder(state.vehicle'))
        self.assertLess(step.index('state.phase = "detour_route"'),
                        step.index('AIOrder.SkipToOrder(state.vehicle, 2)'))
        self.assertIn('"append_depot_order", "", error', step)
        self.assertIn('"skip_depot_order", "", error', step)
        self.assertIn('"depot_timeout"', step)
        self.assertIn("AIVehicle.GetCargoLoad(state.vehicle, line.cargo) != 0",
                      function("OpexRailLongV3UpgradeDepotReady"))
        self.assertIn("AIVehicle.HasSharedOrders(vehicle)",
                      function("OpexRailLongV3UpgradeLineSafe"))

    def test_rollback_restores_orders_before_restart_and_never_toggles_failed_send(self):
        restore = function("OpexRailLongV3UpgradeRestoreOrders")
        self.assertIn("OpexRailLongV3UpgradeTemporaryOrder(state)", restore)
        self.assertIn("AIOrder.RemoveOrder(state.vehicle, 2)", restore)
        self.assertIn("AIOrder.IsGotoDepotOrder(state.vehicle, AIOrder.ORDER_CURRENT)", restore)
        self.assertNotIn("AIOrder.RemoveOrder(state.vehicle, 0)", SOURCE)
        self.assertNotIn("AIOrder.RemoveOrder(state.vehicle, 1)", SOURCE)
        rollback = function("OpexRailLongV3UpgradeRollback")
        self.assertLess(rollback.index("OpexRailLongV3UpgradeRestoreOrders"),
                        rollback.index("AIVehicle.StartStopVehicle"))
        self.assertNotIn("SendVehicleToDepot", rollback)
        step = function("OpexRailLongV3UpgradeStep")
        self.assertLess(step.index("OpexRailLongV3UpgradeRestoreOrders"),
                        step.index("AIOrder.CopyOrders"))

    def test_save_load_detour_append_skip_remove_are_idempotent(self):
        step = function("OpexRailLongV3UpgradeStep")
        append = step[step.index('if (state.phase == "detour_order")'):]
        self.assertLess(append.index("!OpexRailLongV3UpgradeTemporaryOrder(state)"),
                        append.index("AIOrder.AppendOrder"))
        route = step[step.index('if (state.phase == "detour_route")'):]
        self.assertLess(route.index("AIOrder.ResolveOrderPosition"), route.index("AIOrder.SkipToOrder"))
        restore = function("OpexRailLongV3UpgradeRestoreOrders")
        self.assertLess(restore.index("AIOrder.GetOrderCount(state.vehicle) == 3"),
                        restore.index("AIOrder.RemoveOrder"))
        self.assertIn('state.rawset("explicitDetour", false)', function("OpexRailLongV3UpgradeReconcile"))

    def test_build_snapshot_protects_preexisting_vehicles_arriving_later(self):
        step = function("OpexRailLongV3UpgradeStep")
        snapshot = step[step.index("state.beforeDepot = [];"):step.index('state.phase = "building"')]
        self.assertIn("state.beforeDepot.append(vehicle)", snapshot)
        self.assertNotIn("AIVehicle.GetLocation(vehicle) == state.depot", snapshot)

    def test_failure_trace_captures_phase_before_rollback_and_last_error(self):
        abort = function("OpexRailLongV3UpgradeAbort")
        self.assertLess(abort.index("OpexRailLongV3UpgradeTrace"), abort.index('state.phase = "rollback"'))
        trace = function("OpexRailLongV3UpgradeTrace")
        for field in ("phase=", "reason=", "tile=", "station=", "anchor=",
                      "dir=", "vehicle_state=", "load=", "error="):
            self.assertIn(field, trace)

    def test_three_public_hooks_and_independent_persisted_pending(self):
        for name in ("OpexRailLongV3UpgradeSelect", "OpexRailLongV3UpgradeStep",
                     "OpexRailLongV3UpgradeReconcile"):
            self.assertIn("function " + name + "(", SOURCE)
        selector = function("OpexRailLongV3UpgradeSelect")
        self.assertIn("if (!RAIL_LONG_V3 || !SAVE_FULL_STATE", selector)
        self.assertIn("owner._railLongV3UpgradePending =", selector)
        self.assertNotIn("owner._railLongV2Pending =", selector)
        self.assertIn("owner._railLongV3UpgradePending", function("OpexRailLongV3UpgradeBusy"))
        self.assertIn("!RAIL_LONG_V3 && state.phase != \"adopt\"",
                      function("OpexRailLongV3UpgradeReconcile"))

    def test_v2_platform_transaction_reused_no_track_or_signal_mutations(self):
        for name in ("OpexRailLongV2ExtendPlan", "OpexRailLongV2Quote",
                     "OpexRailLongV2BuildPart", "OpexRailLongV2RollbackPart",
                     "OpexRailLongV2CommitReady"):
            self.assertIn(name + "(", SOURCE)
            self.assertIn("function " + name + "(", V2)
        for prohibited in ("AIRail.BuildRail(", "AIRail.RemoveRail(",
                           "AIRail.BuildSignal(", "AIRail.RemoveSignal(",
                           "AIRail.DemolishTile(", "AITile.DemolishTile("):
            self.assertNotIn(prohibited, SOURCE)
        self.assertIn('state.intentA = true;', function("OpexRailLongV3UpgradeStep"))
        self.assertIn('state.intentB = true;', function("OpexRailLongV3UpgradeStep"))
        self.assertLess(function("OpexRailLongV3UpgradeStep").index("state.intentA = true"),
                        function("OpexRailLongV3UpgradeStep").index(
                            'OpexRailLongV2BuildPart(state, "A")'))
        self.assertLess(function("OpexRailLongV3UpgradeStep").index("state.intentB = true"),
                        function("OpexRailLongV3UpgradeStep").index(
                            'OpexRailLongV2BuildPart(state, "B")'))

    def test_seven_before_six_then_existing_and_bounded_scan(self):
        select = function("OpexRailLongV3UpgradeSelect")
        self.assertIn("local top = min(7, trainLimit);", select)
        self.assertIn("length >= max(6, line.platformLength); length--", select)
        self.assertLess(select.index("OpexRailLongV2ExtendPlan"),
                        select.index("OpexRailLongV3UpgradeConsist"))
        self.assertIn("min(count, RAIL_LONG_V3_UPGRADE_SCAN)", select)
        self.assertIn("now + RAIL_LONG_V3_UPGRADE_RETRY_DAYS", select)
        self.assertIn("R A I L".replace(" ", "") + "_LONG_V3_UPGRADE_CURSOR = "
                      "(RAIL_LONG_V3_UPGRADE_CURSOR + scans) % count", select)

    def test_strict_freight_shared_station_v190_double_and_single_loco(self):
        safe = function("OpexRailLongV3UpgradeLineSafe")
        v2safe = function("OpexRailLongV2LineSafe", V2)
        self.assertIn("OpexRailLongV2LineSafe(owner, line)", safe)
        for guard in ("line.kind != \"freight\"", "line.trains != 1",
                      "line.vehicles.len() != 1", "line.wagons2 > 0",
                      "line.doubleTrack != 0", "line.v190Directional",
                      "line.v190Independent", "foreach (other in owner._lines)"):
            self.assertIn(guard, v2safe)
        self.assertIn("AIEngine.IsWagon(AIVehicle.GetEngineType(vehicle))", safe)
        self.assertIn("AIEngine.IsWagon(part)", safe)
        self.assertIn("part != firstWagon", safe)
        self.assertIn("OpexV190Active()", function("OpexRailLongV3UpgradeSlotFree"))
        self.assertIn("OpexV198Active()", function("OpexRailLongV3UpgradeSlotFree"))

    def test_priority_no_parallel_v257_v284_or_primary_work(self):
        expand = (AI / "task_rail.nut").read_text(encoding="utf8")
        expand = expand[expand.index("function OpexAI::_expandRailLines(year)"):]
        reservation = "if (this._railLongV3UpgradePending != null) return;"
        self.assertLess(expand.index(reservation), expand.index("OpexRailPairReview(this)"))
        self.assertLess(expand.index(reservation), expand.index("OpexV284Select(this, year)"))
        slot = function("OpexRailLongV3UpgradeSlotFree")
        for required in ("owner._railLongV2Pending == null",
                         "owner._v257Pending == null", "owner._v271Pending == null",
                         "owner._railExpansion == null", "owner._railSearch == null",
                         "owner._activeWorker == null", "!owner._po01cPending",
                         "!OpexV284Busy(owner)"):
            self.assertIn(required, slot)
        step = function("OpexRailLongV3UpgradeStep")
        self.assertIn("owner._v257Pending != null", step)
        self.assertIn("OpexV284Busy(owner)", step)

    def test_eight_and_two_hundred_in_one_replacement_no_incremental_v284(self):
        choose = function("OpexRailLongV3UpgradeConsist")
        self.assertIn("OpexRailLongV3WagonFloor(wagon, targetLength)", choose)
        self.assertIn("for (local count = upper; count >= minimum; count--)", choose)
        self.assertIn("if (count <= oldCount) continue", choose)
        self.assertIn("OpexRailLongV3SingleTractionOK(loco, wagon, count)", choose)
        self.assertIn("count * wagon.capacity", choose)
        self.assertIn("gain <= 0", choose)
        self.assertIn("life < 10.0 ? life : 10.0", choose)
        self.assertIn("gain * economicYears <= grossPrice - resale", choose)
        self.assertNotIn("min(10.0, life)", choose)
        self.assertNotIn("oldWagons + 1", SOURCE)
        self.assertNotIn("OpexV284Tick(", SOURCE)
        self.assertNotIn("OpexRailLongV2FleetSelect(", SOURCE)
        self.assertIn("state.wagons < 8", function("OpexRailLongV3UpgradeReconcile"))

    def test_reality_not_nominal_length_and_one_loco_only(self):
        cert = function("OpexRailLongV3UpgradeVehicleCertified")
        for check in ("AIVehicle.GetNumWagons(train) != state.wagons + 1",
                      "AIVehicle.GetLength(train) > state.targetLength * 16",
                      "AIVehicle.GetCapacity(train, line.cargo) < 200",
                      "AIEngine.IsWagon(part)", "part != state.wagon"):
            self.assertIn(check, cert)
        step = function("OpexRailLongV3UpgradeStep")
        self.assertLess(step.index("OpexRailLongV3UpgradeVehicleCertified(state, line)"),
                        step.index("AIOrder.CopyOrders(state.newVehicle, state.vehicle)"))
        self.assertLess(step.index('state.phase = "ordered"'),
                        step.index("AIVehicle.StartStopVehicle(state.newVehicle)"))
        self.assertIn("!OpexRailLongV3UpgradeOrdersOK(state.newVehicle, line)", step)

    def test_quotes_and_cash_reserve_before_build(self):
        self.assertIn("const RAIL_LONG_V3_UPGRADE_CASH_RESERVE = 50000;", SOURCE)
        select = function("OpexRailLongV3UpgradeSelect")
        self.assertIn("(quote + consist.grossPrice) * 1.10", select)
        self.assertIn("RAIL_LONG_V3_UPGRADE_CASH_RESERVE", select)
        depot = function("OpexRailLongV3UpgradeDepotReady")
        self.assertIn("OpexAvailableCapital() >= price * 1.10", depot)
        self.assertIn("AICompany.GetBankBalance(AICompany.COMPANY_SELF)", depot)
        self.assertIn("OpexRailLongV3UpgradeConsist(owner, line, state.targetLength)", depot)
        self.assertIn("OpexRailLongV3UpgradeDepotReady(owner, line, state)",
                      function("OpexRailLongV3UpgradeStep"))

    def test_old_train_retained_until_new_started_and_adopted(self):
        step = function("OpexRailLongV3UpgradeStep")
        adopt = function("OpexRailLongV3UpgradeAdopt")
        self.assertIn("state.phase = \"adopt\";", step)
        self.assertIn("AIVehicle.StartStopVehicle(state.newVehicle)", step)
        self.assertNotIn("AIVehicle.SellVehicle(state.vehicle)", step)
        self.assertIn("line.vehicles[0] = state.newVehicle", adopt)
        self.assertIn("line.platformA = clone state.targetA", adopt)
        self.assertIn("line.platformB = clone state.targetB", adopt)
        self.assertIn("AIVehicle.SellVehicle(state.vehicle)", adopt)
        self.assertLess(adopt.index("line.vehicles[0] = state.newVehicle"),
                        adopt.index("AIVehicle.SellVehicle(state.vehicle)"))
        self.assertIn("owner._vehiclesToRetire.rawset(state.vehicle", adopt)

    def test_rollback_only_our_depot_delta_and_only_new_station_tiles(self):
        cleanup = function("OpexRailLongV3UpgradeCleanup")
        self.assertIn("if (!state.buildStarted) return true", cleanup)
        self.assertIn("OpexWaterContains(state.beforeDepot, vehicle)", cleanup)
        self.assertIn("vehicle == state.vehicle", cleanup)
        self.assertIn("AIVehicle.IsStoppedInDepot(vehicle)", cleanup)
        self.assertIn("OpexWaterContains(other.vehicles, vehicle)", cleanup)
        self.assertIn("if (assigned) continue", cleanup)
        rollback = function("OpexRailLongV3UpgradeRollback")
        self.assertIn('OpexRailLongV2RollbackPart(state, "B")', rollback)
        self.assertIn('OpexRailLongV2RollbackPart(state, "A")', rollback)
        self.assertLess(rollback.index('RollbackPart(state, "B")'),
                        rollback.index('RollbackPart(state, "A")'))
        self.assertIn("state.rollbackAttempts >= RAIL_LONG_V3_UPGRADE_ROLLBACK_LIMIT", rollback)
        self.assertIn('OpexRailLongV3UpgradeLog("orphan_safe"', rollback)
        self.assertIn("!OpexRailLongV2NoVehicleNear(tiles)",
                      function("OpexRailLongV2RollbackPart", V2))

    def test_save_load_before_build_rolls_back_running_train_is_adopted(self):
        select = function("OpexRailLongV3UpgradeSelect")
        for field in ("oldA", "oldB", "targetA", "targetB", "tilesA", "tilesB",
                      "beforeA", "beforeB", "beforeDepot", "intentA", "intentB",
                      "buildStarted", "detourIssued", "newVehicle", "phase"):
            self.assertRegex(select, r"\b" + field + r"\s*=")
        reconcile = function("OpexRailLongV3UpgradeReconcile")
        self.assertIn('state.phase = "adopt";', reconcile)
        self.assertIn('OpexRailLongV3UpgradeAbort(state, "load_during_builder")', reconcile)
        self.assertIn('OpexRailLongV3UpgradeAbort(state, "disabled_after_load")', reconcile)
        self.assertIn("owner._saveProjection = null", reconcile)
        step = function("OpexRailLongV3UpgradeStep")
        self.assertLess(step.index("!AIVehicle.IsStoppedInDepot(state.newVehicle)"),
                        step.index('if (state.phase == "rollback")'))

    def test_pending_upgrade_waits_for_catalog_rebuild_after_load(self):
        line_safe = function("OpexRailLongV3UpgradeLineSafe")
        self.assertIn("line.cargo in owner._catalog.wagonByCargo", line_safe)
        step = function("OpexRailLongV3UpgradeStep")
        self.assertIn('OpexRailLongV3UpgradeWait(state, "catalog_after_load")', step)
        self.assertIn("owner._catalog.platformLength <= 0", step)
        self.assertLess(step.index('OpexRailLongV3UpgradeWait(state, "catalog_after_load")'),
                        step.index("!OpexRailLongV3UpgradeLineSafe(owner, line)"))
        self.assertLess(step.index("AIDate.GetCurrentDate() >= state.deadline"),
                        step.index('OpexRailLongV3UpgradeWait(state, "catalog_after_load")'))
        reconcile = function("OpexRailLongV3UpgradeReconcile")
        self.assertIn("owner._lastCatalogMonth = -1", reconcile)
        self.assertIn("owner._catalog.platformLength <= 0", reconcile)

    def test_squirrel_syntax_traps_and_balanced_source(self):
        self.assertNotRegex(SOURCE, r"\.find\s*\(")
        self.assertNotRegex(SOURCE, r"\bfunction\s*\(")
        self.assertNotRegex(SOURCE, r"\blocal\s+(?:clone|base|parent|resume|static)\b")
        for statement in re.findall(r"(?m)^\s*const\s+\w+\s*=\s*([^;]+);", SOURCE):
            self.assertRegex(statement.strip(), r"^[0-9]+$")
        self.assertEqual(SOURCE.count("{"), SOURCE.count("}"))
        self.assertEqual(SOURCE.count("("), SOURCE.count(")"))


if __name__ == "__main__":
    unittest.main()
