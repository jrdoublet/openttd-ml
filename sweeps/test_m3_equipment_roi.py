from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
CATALOG = ROOT / "ai" / "OpexAI" / "catalog.nut"
ECONOMY = ROOT / "ai" / "OpexAI" / "economy.nut"
RAIL = ROOT / "ai" / "OpexAI" / "builder_rail.nut"
ROAD = ROOT / "ai" / "OpexAI" / "builder_road.nut"
AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
TASK_ROAD = ROOT / "ai" / "OpexAI" / "task_road.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
CANDIDATES = ROOT / "ai" / "OpexAI" / "candidates.nut"

class TestM3EquipmentRoi(unittest.TestCase):
    def test_probe_default_off_and_c68_default_on(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["equipment_roi_probe"], 0)
        self.assertEqual(defaults["air_route_plane_selection"], 1)
        self.assertIn("EQUIPMENT_ROI_PROBE <- false;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn("AIR_ROUTE_PLANE_SELECTION <- true;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn('EQUIPMENT_ROI_PROBE = AIController.GetSetting("equipment_roi_probe") != 0;', SETTINGS.read_text(encoding="utf-8"))
        self.assertIn('AIR_ROUTE_PLANE_SELECTION = AIController.GetSetting("air_route_plane_selection") != 0;', SETTINGS.read_text(encoding="utf-8"))
    def test_current_selection_rules_are_preserved(self):
        src = CATALOG.read_text(encoding="utf-8")
        for token in ("capacity > this.wagonByCargo[cargo].capacity", "engine.capacity > best.capacity", "engine.capacity == best.capacity && engine.speed > best.speed", "(isBig && !bestIsBig)"):
            self.assertIn(token, src)
        self.assertEqual(src.count("if (!replaces && !keepPlaneChoices) continue;"), 2)
        self.assertIn("local keepPlaneChoices = EQUIPMENT_ROI_PROBE || AIR_ROUTE_PLANE_SELECTION;", src)
    def test_probe_catalogs_and_rail_overrides(self):
        src = CATALOG.read_text(encoding="utf-8")
        for token in ("wagonChoicesByCargo", "roadEngineChoicesByCargo", "airPlaneChoicesByAirport"):
            self.assertIn(token, src)
        econ = ECONOMY.read_text(encoding="utf-8")
        self.assertIn("wagonOverride = null, locoChoicesOverride = null", econ)
        self.assertIn("OpexM3ProbeRailEquipment(catalog, candidate, plan.length, routeDistance, economics);", RAIL.read_text(encoding="utf-8"))
        self.assertIn('OpexM3ProbeRailEquipment(catalog, m3Candidate, 0, null, economics, "pre_admission")', CANDIDATES.read_text(encoding="utf-8"))
    def test_road_probe_separates_refit_truth(self):
        self.assertIn('economics, "post_route"', TASK_ROAD.read_text(encoding="utf-8"))
        self.assertIn('economics, "pre_admission"', CANDIDATES.read_text(encoding="utf-8"))
        build = ROAD.read_text(encoding="utf-8")
        for token in ("phase=post_refit", "catalog_capacity=", "actual_capacity="):
            self.assertIn(token, build)
    def test_air_probe_is_fixed_airport_and_same_fleet(self):
        src = AIR.read_text(encoding="utf-8")
        for token in ("function OpexM3ProbeAirEquipment", "catalog.airPlaneChoicesByAirport[plan.airport.type]", "fixedPlanes", "phase=post_refit"):
            self.assertIn(token, src)
        task = TASK_AIR.read_text(encoding="utf-8")
        self.assertIn('OpexM3ProbeAirEquipment(this._catalog, plan, "direct_selected")', task)
        self.assertIn('OpexM3ProbeAirEquipment(this._catalog, plan, "portfolio_selected")', task)
        self.assertIn("function OpexM3ProbeAirPreAdmission", src)
        for phase in ("pre_admission_newpair", "pre_admission_hubsite", "pre_admission_hubhub"):
            self.assertIn(phase, src)
    def test_air_route_plane_selection_reuses_m3_choices_and_economics(self):
        src = AIR.read_text(encoding="utf-8")
        catalog = CATALOG.read_text(encoding="utf-8")
        self.assertIn("function OpexAirChooseRoutePlane", src)
        self.assertIn("if (!AIR_ROUTE_PLANE_SELECTION || !(airport.type in catalog.airPlaneChoicesByAirport))", src)
        self.assertIn("economics.profitAnnual > bestEconomics.profitAnnual", src)
        self.assertIn("local keepPlaneChoices = EQUIPMENT_ROI_PROBE || AIR_ROUTE_PLANE_SELECTION;", catalog)
        self.assertEqual(src.count("OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,"), 3)
        self.assertIn('"AV|" + routePlane.speed + "|" + routePlane.capacity', src)
    def test_proxy_labels_and_airport_policy(self):
        probe_src = ECONOMY.read_text(encoding="utf-8") + AIR.read_text(encoding="utf-8")
        self.assertIn("refit_proxy_choices=", probe_src)
        self.assertIn("native_choices=", probe_src)
        self.assertIn('economics, "post_route"', TASK_ROAD.read_text(encoding="utf-8"))
        self.assertIn("if (bestPlan != null && bestPlan.airport.allowBig) break;", AIR.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
