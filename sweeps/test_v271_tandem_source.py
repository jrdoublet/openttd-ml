"""V271 : contrats du tandem source, sans moteur ni mesure economique."""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def code(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', "", text, flags=re.S)


class TandemSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v271.nut"]
        cls.builder = cls.sources["builder_rail.nut"]
        cls.geometry = cls.builder[cls.builder.index("function OpexV271PlatformPlan"):
                                   cls.builder.index("function OpexTileTrackCount")]

    def test_integer_setting_zero_at_every_difficulty(self):
        block = re.search(r'name = "v271_rail_tandem_source",(.*?)\}\);', self.sources["info.nut"], re.S)[1]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, level + r"_value = 0\b")
        self.assertIn("min_value = 0, max_value = 9", block)
        self.assertIn("step_size = 1", block)
        self.assertIn("V271_RAIL_TANDEM_SOURCE <- 0;", self.sources["globals_pre.nut"])

    def test_setting_read_once_and_range_checked(self):
        self.assertEqual(sum(s.count('GetSetting("v271_rail_tandem_source")') for s in self.sources.values()), 1)
        self.assertIn("tandemSource > 0 && tandemSource <= 9", self.sources["settings.nut"])

    def test_off_is_single_short_circuit_before_api(self):
        body = self.sources["task_rail.nut"].split("function OpexAI::_expandRailLines(year)\n{", 1)[1]
        self.assertTrue(body.lstrip().startswith("if (V271_RAIL_TANDEM_SOURCE > 0 && this._v271TandemSource(year)) return;"))

    def test_year_cash_and_transaction_guards(self):
        for guard in ("year < OPEX_START_YEAR + V271_RAIL_TANDEM_SOURCE", "OpexAvailableCapital() < V270_IDLE_CASH_MIN",
                      "this._v271Year == quotaKey", "this._railExpansion != null", "this._v257Pending != null",
                      "this._railSearch != null", "!SAVE_FULL_STATE"):
            self.assertIn(guard, self.task)

    def test_eligibility_and_score(self):
        for guard in ('line.kind != "freight"', "line.trains != 1", "line.vehicles.len() != 1",
                      "line.doubleTrack != 0", "line.scrapping", "line.expandBlocked", "line.lastProfit <= 0",
                      "rating <= 0 || rating >= 75", "line.v271Failed"):
            self.assertIn(guard, self.task)
        self.assertIn("line.lastProfit * (min(rating + 20, 85).tofloat() / rating - 1.0)", self.task)
        self.assertIn("gain > best.gain", self.task)

    def test_running_cost_is_actual_consist_and_net_payback(self):
        self.assertIn("AIVehicle.GetNumWagons(best.vehicle)", self.task)
        self.assertIn("AIEngine.GetRunningCost(AIVehicle.GetWagonEngineType(best.vehicle, unit))", self.task)
        self.assertIn("local remaining = OPEX_START_YEAR + 10 - year;", self.task)
        self.assertIn("state.gain <= running", self.task)
        self.assertIn("state.cost >= (state.gain - running) * remaining", self.task)

    def test_only_strict_bidirectional_pbs(self):
        self.assertIn("AIRail.SIGNALTYPE_PBS", self.task)
        self.assertNotIn("SIGNALTYPE_PBS_ONEWAY", self.task + self.geometry)
        self.assertNotIn("SIGNALTYPE_NORMAL", self.task + self.geometry)
        self.assertIn("OpexC41BuildPbsAtApproach({ lead = state.lead, station_exit = state.exit })", self.task)
        self.assertIn("OpexC41BuildPbsAtApproach(state.platform)", self.task)
        helper = self.sources["task_rail.nut"].split("function OpexC41BuildPbsAtApproach", 1)[1].split("\n}", 1)[0]
        self.assertIn("AIRail.BuildSignal(lead, exit, AIRail.SIGNALTYPE_PBS)", helper)
        self.assertNotIn("SIGNALTYPE_NORMAL", helper)

    def test_geometry_same_station_and_line_side(self):
        self.assertIn("OpexV190FindParallelPlatformPlans(original, true, 2)", self.geometry)
        self.assertIn("i <= 12 && i + 1 < route.len()", self.geometry)
        self.assertIn("signalTile = route[signalIndex], signalFront = route[signalIndex - 1]", self.geometry)
        self.assertIn("AIRail.BuildRailStation(plan.anchor, plan.direction, 1, plan.length, state.stationId)", self.task)

    def test_merge_and_primary_signal_are_straight_and_ordered(self):
        for guard in ("OpexTileTrackCount(tile) == 1", "!AIRail.IsRailStationTile(tile)",
                      "!AIRail.IsRailDepotTile(tile)", "!AIBridge.IsBridgeTile(tile)",
                      "!AITunnel.IsTunnelTile(tile)",
                      "tile - route[i - 1] == route[i + 1] - tile"):
            self.assertIn(guard, self.geometry)
        self.assertLess(self.geometry.index("if (signalIndex >= 0) merges[tile]"),
                        self.geometry.index("if (signalIndex < 0) signalIndex = i"))
        for reason in ("no_primary_signal", "no_merge_tile", "no_adjacent_platform", "path", "test_build"):
            self.assertIn('V271_LAST_GEOMETRY_ISSUE = "' + reason + '"', self.geometry)

    def test_connection_is_bounded_free_ground_and_straight_at_secondary_pbs(self):
        for guard in ("head < 256", "queued >= 256", "n >= 17",
                      "n == 2 && offset != d", "OpexWaterContains(path, next)",
                      "!AITile.IsBuildable(next)", "AIRail.IsRailTile(next)",
                      "AIBridge.IsBridgeTile(next)", "AITunnel.IsTunnelTile(next)",
                      "next == plan.anchor + i * plan.step",
                      "offset == path[n - 3] - prev", "goal.next - next == prev - cur",
                      "goal.after - goal.next == cur - next",
                      "AIRail.BuildRail(cur, next, goal.next)"):
            self.assertIn(guard, self.geometry)
        # Only the last two entries can belong to the existing route; the last
        # entry is context for BuildRail, never a command target.
        self.assertIn("if (!joining &&", self.geometry)
        self.assertIn("result.append(next);\n        result.append(goal.next);", self.geometry)
        self.assertIn("local testMode = AITestMode();", self.geometry)

    def test_v190_defaults_and_both_sides_preserved(self):
        helper = self.builder.split("function OpexV190FindParallelPlatformPlans", 1)[1].split("/* V190 : Collecte", 1)[0]
        self.assertIn("allowSlopes = false, maxSide = JOIN_PARALLEL_MAX_SIDE", helper)
        self.assertIn("dist = 1; dist <= maxSide; dist++", helper)
        self.assertIn("flip = -1; flip <= 1; flip += 2", helper)
        self.assertIn("anchor2 = platform.anchor + sideways * (dist * flip)", helper)

    def test_route_audited_without_removing_existing_signals(self):
        self.assertIn("OpexTraceTrackTiles(line.stationA, line.platformA.lead, line.stationB, true)", self.geometry)
        self.assertIn("route[route.len() - 1] != line.stationB", self.geometry)
        self.assertIn("AIRail.GetSignalType(tile, neighbor) != AIRail.SIGNALTYPE_NONE", self.geometry)
        self.assertIn("neighbor == line.depot", self.geometry)

    def test_train_stopped_before_station_mutation(self):
        self.assertIn("AIVehicle.IsStoppedInDepot(state.vehicle)", self.task)
        self.assertIn("AIVehicle.GetLocation(state.vehicle) != line.depot", self.task)
        self.assertLess(self.task.index('state.phase == "wait"'), self.task.index('state.phase == "station_intent"'))
        for guard in ("OpexTileTrackCount(state.lead) != 1", "OpexTileTrackCount(merge) != 1",
                      "AIRail.AreTilesConnected(merge - (next - merge), merge, next)"):
            self.assertIn(guard, self.task)

    def test_clone_actual_consist_and_orders_starts_at_source(self):
        self.assertIn("AIVehicle.CloneVehicle(line.depot, state.vehicle, false)", self.task)
        self.assertIn("AIOrder.SkipToOrder(state.newVehicle, 0)", self.task)
        self.assertIn("AIVehicle.GetLength(state.newVehicle) > state.platform.length * 16", self.task)
        self.assertIn("OpexV271FindNewVehicle(state, line.depot)", self.task)

    def test_commit_inventory_before_start_and_never_rollback(self):
        commit = self.task.split('if (state.phase == "commit")', 1)[1].split('if (!AIVehicle.IsValidVehicle(state.vehicle))', 1)[0]
        self.assertLess(commit.index("line.vehicles.append(state.newVehicle)"), commit.index("AIVehicle.StartStopVehicle(vehicle)"))
        for field in ("line.trains = line.vehicles.len()", "line.vehCount", "line.lastLiveVehicles", "line.v271Tandem <- true"):
            self.assertIn(field, commit)
        self.assertNotIn('state.phase = "rollback"', commit)
        self.assertIn("AIOrder.SkipToOrder(vehicle, 0)", commit)

    def test_marker_transaction_and_annual_quota_persist(self):
        persist = self.sources["persist.nut"]
        self.assertIn("v271Tandem/v271Failed", persist)
        self.assertIn("local serializableLine = clone line;", persist)
        self.assertIn("saveObj.v271TandemSource <- { year = this._v271Year, pending = this._v271Pending }", persist)
        self.assertIn('this._v271Pending = ("pending" in tandem) ? tandem.pending : null;', persist)
        self.assertIn("this._saveProjection = null", self.task)

    def test_existing_lifecycle_protected(self):
        self.assertIn('if (("v271Tandem" in line) && line.v271Tandem) continue;', self.sources["task_rail.nut"])
        self.assertIn("if (this._v271Pending != null) return;", self.sources["task_v257.nut"])
        self.assertIn("this._v271Pending.lineId == line.lineId", self.sources["task_report.nut"])
        self.assertEqual(self.sources["task_rail.nut"].count('if (("v271Tandem" in line) && line.v271Tandem) continue;'), 2)

    def test_disabling_after_load_recovers_pending_work_only(self):
        self.assertIn("this._v271Pending != null && V271_RAIL_TANDEM_SOURCE == 0", self.sources["persist.nut"])
        self.assertIn('this._v271Pending.reason = "disabled_after_load";', self.sources["persist.nut"])
        self.assertIn('name = "v271_recover"', self.sources["persist.nut"])
        self.assertNotIn('name = "v271_recover"', self.sources["main.nut"])
        self.assertIn("task.enabled = this._v271Pending != null;", self.sources["scheduler.nut"])

    def test_rollback_preserves_primary_station_and_tracks(self):
        self.assertNotIn("DemolishTile(", code(self.task + self.geometry))
        self.assertNotIn("OpexRollback(", code(self.task + self.geometry))
        self.assertIn("AIRail.GetRailTracks(snapshot.tile) & ~snapshot.tracks", self.geometry)
        self.assertIn("AIRail.RemoveRailTrack(snapshot.tile, bit)", self.geometry)
        self.assertIn("state.platform.anchor + i * state.platform.step", self.task)
        self.assertIn("state.signalsIntent", self.task)
        self.assertIn("i + 1 < state.tiles.len(); i++) touched.append(state.tiles[i])", self.task)
        self.assertLess(self.task.index("state.snapshots.append"), self.task.index('state.phase = "track"'))

    def test_remove_temporary_is_replay_safe(self):
        helper = self.task.split("function OpexV271RemoveTemporary", 1)[1].split("\n}", 1)[0]
        self.assertLess(helper.index("AIOrder.IsGotoDepotOrder"), helper.index("AIOrder.RemoveOrder"))
        self.assertIn("AIOrder.GetOrderDestination(state.vehicle, state.order) == state.depot", helper)

    def test_log_actions_include_economic_context(self):
        for action in ("pick", "skip", "build", "done", "fail"):
            self.assertRegex(self.task, r'OpexV271Log\([^;\n]*"' + action + '"')
        for field in ("action=", "reason=", "line=", "cargo=", "note=", "gain=", "cost="):
            self.assertIn(field, self.task)
        self.assertIn('OpexDecide("V271",', self.task)

    def test_new_symbols_are_declared_referenced_and_loaded(self):
        all_code = code("\n".join(self.sources.values()))
        definitions = set(re.findall(r"function\s+(?:OpexAI::)?(\w+)\s*\(", all_code))
        calls = set(re.findall(r"\b(OpexV271\w+|_v271\w+)\s*\(", code(self.task + self.geometry)))
        self.assertFalse(calls - definitions)
        for symbol in re.findall(r"function\s+(?:OpexAI::)?(\w+)\s*\(", code(self.task + self.geometry)):
            self.assertGreater(len(re.findall(r"\b" + symbol + r"\s*\(", all_code)), 1, symbol)
        self.assertIn('require("task_v271.nut");', self.sources["main.nut"])
        globals_defined = set(re.findall(r"\b([A-Z][A-Z_0-9]+)\s*<-", all_code))
        self.assertIn("V271_RAIL_TANDEM_SOURCE", globals_defined)

    def test_no_reserved_identifiers_nested_closures_or_sleep(self):
        new_code = code(self.task + self.geometry)
        self.assertNotRegex(new_code, r"\b(?:local|function)\s+(?:clone|base|parent)\b")
        self.assertNotRegex(new_code, r"=\s*function\s*\(")
        self.assertNotRegex(new_code, r"\bSleep\s*\(")
        self.assertNotRegex(new_code, r"\.\s*(?:find|map|filter|reduce|apply)\s*\(")

    def test_new_functions_have_no_undeclared_bare_variables(self):
        all_code = code("\n".join(self.sources.values()))
        known = set(re.findall(r"\b(\w+)\s*<-", all_code))
        known.update(re.findall(r"\bconst\s+(\w+)", all_code))
        known.update(re.findall(r"\bfunction\s+(?:OpexAI::)?(\w+)", all_code))
        known.update(re.findall(r"\bclass\s+(\w+)", code("\n".join(
            p.read_text(encoding="utf-8") for p in AI.rglob("*.nut")))))
        known.update("function local if else return foreach for while continue break null true false this in typeof min max clone".split())
        source = code(self.task + self.geometry)
        for match in re.finditer(r"function\s+(?:OpexAI::)?(\w+)\s*\(([^)]*)\)\s*\{", source):
            end = match.end()
            depth = 1
            while depth:
                depth += (source[end] == "{") - (source[end] == "}")
                end += 1
            body = source[match.end():end - 1]
            declared = known | set(re.findall(r"\b\w+\b", match[2]))
            declared.update(re.findall(r"\blocal\s+(\w+)", body))
            for loop in re.findall(r"\bforeach\s*\((.*?)\bin\b", body):
                declared.update(re.findall(r"\w+", loop))
            for token in re.finditer(r"\b[A-Za-z_]\w*\b", body):
                name = token[0]
                prefix = body[:token.start()].rstrip()
                suffix = body[token.end():].lstrip()
                if prefix.endswith(".") or (suffix.startswith("=") and not suffix.startswith("==")):
                    continue  # propriete/cle de table, pas une variable lue
                if re.fullmatch(r"AI[A-Za-z_]\w*", name):
                    continue  # classe de l'API NoAI
                self.assertIn(name, declared, f"{match[1]}: {name}")

    def test_balanced_delimiters_in_touched_squirrel(self):
        names = ("task_v271.nut", "builder_rail.nut", "globals_pre.nut", "info.nut", "main.nut",
                 "persist.nut", "settings.nut", "task_rail.nut", "task_report.nut", "task_v257.nut", "scheduler.nut")
        for name in names:
            stack = []
            for char in code(self.sources[name]):
                if char in "([{":
                    stack.append(char)
                elif char in ")]}":
                    self.assertTrue(stack, name)
                    self.assertEqual(stack.pop(), {")": "(", "]": "[", "}": "{"}[char], name)
            self.assertEqual(stack, [], name)


if __name__ == "__main__":
    unittest.main()
