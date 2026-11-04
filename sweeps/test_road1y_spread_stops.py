"""Static contracts only: these tests do not compile or execute Squirrel."""
import json
import unittest
from pathlib import Path
from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]


class SpreadStopsContracts(unittest.TestCase):
    def test_zero_and_cargo_guards_precede_api_and_fields(self):
        code = body("road1y_spread.nut", "OpexRoad1ySpreadStops")
        self.assertLess(code.index("ROAD1Y_SPREAD_STOPS <= 0"), code.index("AICargo."))
        self.assertLess(code.index('line.kind != "pax"'), code.index("line.rawset"))
        self.assertIn("AICargo.CC_PASSENGERS", code)
        self.assertIn('ROAD1Y_SPREAD_STOPS <- 0;', source("globals_pre.nut"))
        block = source("info.nut").split('name = "road1y_spread_stops",')[1].split("});")[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 2", block)
        self.assertIn("min_value = 0, max_value = 4", block)
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            self.assertIn('GetSetting("road1y_spread_stops")', code)
            self.assertIn("if (!road1yRoadOnly) ROAD1Y_SPREAD_STOPS = 0;", code)

    def test_geometry_selection_join_cash_and_refusal(self):
        code = body("road1y_spread.nut", "OpexRoad1ySpreadStops")
        for fragment in (
            'AIStation.GetStationID(root)', 'stationId == 65535',
            'local radius = 12', 'station.station_spread',
            'AIStation.STATION_ANY', 'AIBridge.IsBridgeTile(tile)',
            'AITunnel.IsTunnelTile(tile)', 'AITile.SLOPE_FLAT',
            'OpexBusDistrictAxis(tile)', 'AreRoadTilesConnected(back, tile)',
            'acceptance > 1', 'candidates.sort(OpexRoad1ySpreadSort)',
            'AIExecMode()', 'AIRoad.ROADVEHTYPE_BUS, stationId)',
            'live.len() >= ROAD1Y_SPREAD_STOPS',
            'local reserve = 5000;',
            'reserve + catalog.costRoadBusStop',
            'AIError.ERR_LOCAL_AUTHORITY_REFUSES',
            'occupied.append(site.tile)', 'live.append(site.tile)',
        ):
            self.assertIn(fragment, code)
        self.assertIn("dx <= 5 && dy <= 5", body("road1y_spread.nut", "OpexRoad1ySpreadNear"))
        self.assertNotIn("BuildDriveThrough", code.split("try {")[1].split("catch")[0])
        self.assertNotIn("AIOrder.", source("road1y_spread.nut"))

    def test_opening_before_fleet_and_rollback_separate_from_portfolio(self):
        code = body("builder_road.nut", "OpexBuildRoadRoute")
        self.assertLess(code.index('OpexRoad1ySpreadStops(catalog, spreadLine, "A")'),
                        code.index("AIVehicle.BuildVehicle"))
        self.assertIn('OpexRoad1ySpreadStops(catalog, spreadLine, "B")', code)
        self.assertIn("portfolioSatellites.append({ tile = tile, id = stationA })", code)
        self.assertIn("portfolioSatellites.append({ tile = tile, id = stationB })", code)
        self.assertNotIn("portfolioSummary.stopsA.append", code)
        for filename in ("task_road.nut", "bus_districts_overrides.nut"):
            self.assertIn("if (ROAD1Y_SPREAD_STOPS > 0) plan.road1ySpreadLineId <- idx;", source(filename))
            self.assertIn('if ("road1ySpreadA" in result)', source(filename))
            self.assertIn("OpexRoad1ySpreadCopy(result, this._lines[this._lines.len() - 1])", source(filename))
            self.assertIn('if ("road1ySpreadA" in line) OpexRoad1ySpreadCount(line);', source(filename))

    def test_monthly_persistent_throttle_and_save(self):
        code = body("road1y_spread.nut", "OpexRoad1ySpreadStep")
        self.assertIn("== month) return;", code)
        self.assertIn("!OpexRoad1ySpreadDue(line.road1ySpreadDone, now)", code)
        self.assertIn("OpexRoad1ySpreadMark(line, now);", code)
        self.assertIn("ROAD1Y_SPREAD_LAST_MONTH = month;", code)
        self.assertIn("OpexSaveProjectLine(line)", code)
        self.assertIn("break;", code)
        self.assertIn("if (ROAD1Y_SPREAD_STOPS > 0) OpexRoad1ySpreadStep(this);",
                      body("scheduler_tasks.nut", "OpexAI::_dispatchRefleet"))
        skip = source("persist.nut").split("OPEX_SAVE_LINE_SKIP <-")[1].split("};")[0]
        for key in ("road1ySpreadA", "road1ySpreadB", "road1ySpreadDone"):
            self.assertNotIn(key, skip)
        self.assertIn('valType != "array"', body("persist.nut", "OpexSaveProjectLine"))
        self.assertIn("OpexRoad1ySpreadCount(line)", body("bus_districts_overrides.nut", "OpexAI::_reconcileAfterLoad"))

    def test_logging_and_historical_fixtures(self):
        code = body("road1y_spread.nut", "OpexRoad1ySpreadStops")
        self.assertIn('if (DECISION_LOG) OpexDecide("ROAD1Y_SPREAD"', code)
        for field in ("line=", " end=", " candidates=", " built=", " refused=", " cost=", " nStops="):
            self.assertIn(field, code)
        # Earlier fixtures are layered historical projections. Only the new
        # spread-containing "after" blocks describe the live source directly.
        for path in (ROOT / "sweeps/fixtures").glob("road100_*_hunks.json"):
            for filename, hunks in json.loads(path.read_text()).items():
                for hunk in hunks:
                    if "SPREAD_STOPS" in hunk["after"] or "SpreadCopy" in hunk["after"]:
                        self.assertEqual(source(filename).count(hunk["after"]), 1,
                                         (path.name, filename))

    def test_tour_stays_single_stop_only_and_cap_unchanged(self):
        self.assertIn("line.nStopsA != 1 || line.nStopsB != 1",
                      body("builder_road.nut", "OpexRoad100TryTourAddStop"))
        self.assertNotIn("SPREAD", body("economy.nut", "OpexRoadPhysicalVehicleCap"))


if __name__ == "__main__":
    unittest.main()
