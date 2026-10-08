from pathlib import Path
import unittest
from campaign_freeze import parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class VisibleFluxContracts(unittest.TestCase):
    def test_default_off_and_observable_api_only(self):
        self.assertEqual(parse_ai_settings(AI / "info.nut")["c121_air_visible_competition"], 0)
        text = (AI / "air_coverage.nut").read_text(encoding="utf8")
        scan = text.split("function OpexC121VisibleAirportOwners", 1)[1].split(
            "function OpexC121StationCompetitionBuckets", 1)[0]
        self.assertIn("AIAirport.IsAirportTile", scan)
        self.assertIn("AITile.GetOwner", scan)
        self.assertNotIn("GetAirportType", scan)
        self.assertNotIn("GetCargoRating", scan)
        self.assertNotIn("IsValidCompany", scan)
        self.assertIn("AICompany.ResolveCompanyID(owner)", scan)
        self.assertIn("owners[source].rawset(owner, true)", scan)

    def test_common_new_hub_and_live_fleet_paths(self):
        econ = (AI / "air_economics_c121.nut").read_text(encoding="utf8")
        self.assertGreaterEqual(econ.count("OpexC121StationAllocatedMonthly("), 9)
        fleet = (AI / "air_fleet.nut").read_text(encoding="utf8")
        self.assertIn("if (other != line) others.append(other)", fleet)
        self.assertIn("if (samples <= 0)", fleet)
        self.assertIn("OpexC121PrepareDemandShadow(catalog, quote, others)", fleet)
        self.assertIn("OpexC121PrepareEngineStatic(catalog, quote)", fleet)
        self.assertIn("OpexC121RefreshVisibleFleet(catalog, line, lines)", fleet)
        task = (AI / "task_air.nut").read_text(encoding="utf8")
        self.assertLess(task.index("OpexC121RefreshVisibleFleet(this._catalog, line, this._lines)"),
                        task.index("local c121BelowTarget ="))

    def test_caches_reconstructible_and_expire(self):
        settings = (AI / "settings.nut").read_text(encoding="utf8")
        self.assertIn("C121_AIR_VISIBLE_COMPETITION = C121_AIR_ECONOMICS", settings)
        self.assertIn("C121_VISIBLE_AIRPORT_CACHE.clear()", settings)
        self.assertIn("C121_VISIBLE_FLEET_CACHE.clear()", settings)
        persist = (AI / "persist.nut").read_text(encoding="utf8")
        self.assertNotIn("C121_VISIBLE_FLEET_CACHE", persist)
