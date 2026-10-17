"""V139 retirement: no generation/build hooks; old saves remain readable."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
def source(name):
    return (AI / name).read_text(encoding="utf-8")
class V139FeederBusTests(unittest.TestCase):
    def test_setting_and_module_removed(self):
        self.assertFalse((AI / "feeder_bus.nut").exists())
        for name in ("info.nut", "settings.nut", "globals_pre.nut", "main.nut"):
            self.assertNotIn("v139_feeder_bus", source(name))
            self.assertNotIn("V139_FEEDER_BUS", source(name))
        self.assertNotIn('require("feeder_bus.nut")', source("main.nut"))
    def test_no_feeder_candidates_or_dispatch(self):
        for name in ("projects.nut", "projects_generation.nut", "projects_update.nut",
                     "projects_selection.nut", "lines.nut", "task_road.nut"):
            for token in ("isFeeder", "OpexBuildFeederCandidates", "_tryBuildFeederProject",
                          "roadFeederAirports"):
                self.assertNotIn(token, source(name))
    def test_old_unjoined_stop_key_is_ignored(self):
        persist = source("persist.nut")
        self.assertIn("Legacy v139UnjoinedStops is deliberately ignored", persist)
        self.assertNotIn("OpexV139", persist)
        self.assertNotIn("V139_UNJOINED_STOPS", persist)
    def test_interurban_roads_and_airport_joined_stops_remain(self):
        self.assertIn("function OpexAI::_tryBuildRoadProject(", source("task_road.nut"))
        self.assertIn("OpexTownBusPaxServed", source("task_road.nut"))
        self.assertIn("function OpexAirBuildJoinedStops(", source("air_construction.nut"))
        self.assertIn("BuildDriveThroughRoadStation", source("air_construction.nut"))
