"""ROAD100-31: physical-bilateral initial fleet is opt-in and rollbackable."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_road100_pax_producer_units import body

AI = Path(__file__).resolve().parent.parent / "ai" / "OpexAI"


class Road100PaxInitialBerthFleet(unittest.TestCase):
    def test_off_by_default_and_only_with_corrected_pax_road(self):
        info = (AI / "info.nut").read_text(encoding="utf8")
        setting = info.split('name = "road100_pax_initial_berth_fleet"', 1)[1].split("});", 1)[0]
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", setting)
        self.assertIn("custom_value = 0", setting)
        settings = (AI / "settings.nut").read_text(encoding="utf8")
        block = settings.split("ROAD100_PAX_INITIAL_BERTH_FLEET =", 1)[1].split(";", 1)[0]
        for fragment in (
            'GetSetting("road100_pax_initial_berth_fleet") == 1',
            "ROAD100_PAX_PRODUCER_UNITS",
            "ROAD100_PAX_PORTFOLIO",
            "!ROAD100_PAX_DOUBLE_BERTHS",
            "!ROAD100_PAX_BERTH_BALANCE",
            "MODE_ROAD",
            "!MODE_AIR",
            "!MODE_RAIL",
            "!MODE_WATER",
        ):
            self.assertIn(fragment, block)
        self.assertIn("ROAD100_PAX_INITIAL_BERTH_FLEET <- false;",
                      (AI / "globals_pre.nut").read_text(encoding="utf8"))

    def test_extras_only_after_real_joined_stations_and_incremental_roi(self):
        src = (AI / "builder_road.nut").read_text(encoding="utf8")
        build = body(src, "OpexBuildRoadRoute")
        first = build.index("local first = AIVehicle.BuildVehicleWithRefit")
        phys = build.index("if (ROAD100_PAX_INITIAL_BERTH_FLEET")
        clones = build.index("for (local i = 1; i < want; i++)")
        self.assertLess(first, phys)
        self.assertLess(phys, clones)
        for fragment in (
            "portfolioSummary.stopsA.len() > 0",
            "portfolioSummary.stopsB.len() > 0",
            "result.nStopsA >= 2 && result.nStopsB >= 2",
            "AIStation.GetStationID(bayA) == stationA",
            "AIStation.GetStationID(bayB) == stationB",
            "AIVehicle.GetCapacity(first, cargo) == candidate.engine.capacity",
            "option.profitAnnual <= base.profitAnnual",
            "extraRoi < 250",
            "extraCapital + 50000",
            "OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, vehicles)",
            "AIRoad.IsRoadStationTile(bayA)",
            "AIRoad.IsRoadStationTile(bayB)",
            "road100PaxExtraInit.economics.trains",
            "AIVehicle.CloneVehicle",
            "AIVehicle.StartStopVehicle",
            "OpexRoadRollback",
        ):
            self.assertIn(fragment, build)
        self.assertNotIn("AIStation.GetCargoWaiting", build[phys:clones])
        self.assertNotIn("AAAHogEx", build[phys:clones])
        self.assertIn("road100PaxInitialBays <- [", build)
        self.assertIn("OpexApplyRoadEconomics(candidate, actual,", build)
        self.assertLess(build.index("if (startFailed)"), build.index("OpexApplyRoadEconomics(candidate, actual,"))

    def test_real_site_count_is_the_fleet_cap(self):
        economy = (AI / "economy.nut").read_text(encoding="utf8")
        self.assertIn("if (fleetCapOverride == 8 && kind == \"pax\") roadVehicleCap = 8;", economy)
        self.assertIn("if (ROAD100_PAX_INITIAL_BERTH_FLEET && kind == \"pax\"", economy)
        self.assertIn("fleetCapOverride >= 3 && fleetCapOverride <= 7", economy)
        self.assertIn("roadVehicleCap = fleetCapOverride;", economy)
        self.assertIn("return 2 * nMin;", body(economy, "OpexRoadPhysicalVehicleCap"))
        src = (AI / "builder_road.nut").read_text(encoding="utf8")
        self.assertIn("OpexRoadPhysicalVehicleCap(result.nStopsA, result.nStopsB)", src)

    def test_save_load_and_external_demolition_recover_bay_cap(self):
        src = (AI / "task_road.nut").read_text(encoding="utf8")
        self.assertIn('"road100PaxInitialBays", result.road100PaxInitialBays', src)
        restore = body(src, "OpexAI::_refleetRoadLines")
        for fragment in (
            '("road100PaxInitialBays" in line)',
            'typeof line.road100PaxInitialBays == "array"',
            "line.road100PaxInitialBays.len() == 2",
            "AIRoad.IsRoadStationTile(root)",
            "AIRoad.IsRoadStationTile(bay)",
            "AIStation.GetStationID(bay) == AIStation.GetStationID(root)",
            "line.nStopsA = 1",
            "line.nStopsB = 1",
            "reason=LOST_BAY",
        ):
            self.assertIn(fragment, restore)
        persist = (AI / "persist.nut").read_text(encoding="utf8")
        self.assertIn("local serializableLine = clone line;", persist)
        self.assertIn('valType != "array"', persist)


if __name__ == "__main__":
    unittest.main()
