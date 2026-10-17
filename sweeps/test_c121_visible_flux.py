from pathlib import Path
import unittest
from campaign_freeze import parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class VisibleFluxContracts(unittest.TestCase):
    def test_default_off_and_observable_api_only(self):
        self.assertNotIn("c121_air_visible_competition", parse_ai_settings(AI / "info.nut"))
        text = (AI / "air_coverage.nut").read_text(encoding="utf8")
        self.assertNotIn("function OpexC121VisibleAirportOwners", text)
        self.assertNotIn("C121_AIR_VISIBLE_COMPETITION", text)
        self.assertNotIn("C121_VISIBLE_AIRPORT_CACHE", text)

    def test_common_new_hub_and_live_fleet_paths(self):
        econ = (AI / "air_economics_c121.nut").read_text(encoding="utf8")
        self.assertGreaterEqual(econ.count("OpexC121StationAllocatedMonthly("), 9)
        self.assertNotIn("function OpexC121VisibleFleetEconomics", econ)
        fleet = (AI / "air_fleet.nut").read_text(encoding="utf8")
        self.assertNotIn("OpexC121RefreshVisibleFleet", fleet)
        self.assertNotIn("C121_AIR_VISIBLE_COMPETITION", fleet)
        task = (AI / "task_air.nut").read_text(encoding="utf8")
        self.assertNotIn("OpexC121RefreshVisibleFleet", task)
        self.assertIn("local c121BelowTarget =", task)

    def test_caches_reconstructible_and_expire(self):
        globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf8")
        self.assertNotIn("C121_AIR_VISIBLE_COMPETITION", globals_pre)
        self.assertNotIn("C121_VISIBLE_AIRPORT_CACHE", globals_pre)
        self.assertNotIn("C121_VISIBLE_FLEET_CACHE", globals_pre)
        settings = (AI / "settings.nut").read_text(encoding="utf8")
        self.assertNotIn("C121_AIR_VISIBLE_COMPETITION", settings)
        self.assertNotIn("C121_VISIBLE_AIRPORT_CACHE", settings)
        self.assertNotIn("C121_VISIBLE_FLEET_CACHE", settings)
        persist = (AI / "persist.nut").read_text(encoding="utf8")
        self.assertNotIn("C121_VISIBLE_FLEET_CACHE", persist)
