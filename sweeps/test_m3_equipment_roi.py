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
AIR_ENGINE_CHOICE = ROOT / "ai" / "OpexAI" / "air_engine_choice.nut"
AIR_PLANNING = ROOT / "ai" / "OpexAI" / "air_planning.nut"
AIR_CONSTRUCTION = ROOT / "ai" / "OpexAI" / "air_construction.nut"
TASK_ROAD = ROOT / "ai" / "OpexAI" / "task_road.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
CANDIDATES = ROOT / "ai" / "OpexAI" / "candidates.nut"

class TestM3EquipmentRoi(unittest.TestCase):
    def test_builder_air_requires_modules(self):
        builder = AIR.read_text(encoding="utf-8")
        for module in ("air_engine_choice.nut", "air_planning.nut", "air_construction.nut"):
            self.assertIn(f'require("{module}");', builder)

    def test_probe_default_off_and_c68_default_on(self):
        defaults = parse_ai_settings(INFO)
        self.assertNotIn("probe_events", defaults)
        self.assertNotIn("air_route_plane_selection", defaults)
        self.assertIn("EQUIPMENT_ROI_PROBE <- false;", GLOBALS.read_text(encoding="utf-8"))
        self.assertNotIn("AIR_ROUTE_PLANE_SELECTION <- true;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn('EQUIPMENT_ROI_PROBE = probeEvents;', SETTINGS.read_text(encoding="utf-8"))
        self.assertNotIn('AIR_ROUTE_PLANE_SELECTION = AIController.GetSetting("air_route_plane_selection") != 0;', SETTINGS.read_text(encoding="utf-8"))
    def test_current_selection_rules_are_preserved(self):
        src = CATALOG.read_text(encoding="utf-8")
        for token in ("capacity > this.wagonByCargo[cargo].capacity", "engine.capacity > best.capacity", "engine.capacity == best.capacity && engine.speed > best.speed", "(isBig && !bestIsBig)"):
            self.assertIn(token, src)
        self.assertEqual(src.count("if (!replaces && !keepPlaneChoices) continue;"), 2)
        self.assertIn("local keepPlaneChoices = true", " ".join(src.split()))
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
        src = AIR_ENGINE_CHOICE.read_text(encoding="utf-8")
        for token in ("function OpexM3ProbeAirEquipment", "catalog.airPlaneChoicesByAirport[plan.airport.type]", "fixedPlanes"):
            self.assertIn(token, src)
        self.assertIn("phase=post_refit", AIR_CONSTRUCTION.read_text(encoding="utf-8"))
        task = TASK_AIR.read_text(encoding="utf-8")
        planning_src = AIR_PLANNING.read_text(encoding="utf-8")
        self.assertNotIn('OpexM3ProbeAirEquipment(this._catalog, plan, "direct_selected")', task)
        self.assertIn('OpexM3ProbeAirEquipment(this._catalog, plan, "portfolio_selected")', task)
        self.assertIn("function OpexM3ProbeAirPreAdmission", src)
        for phase in ("pre_admission_newpair", "pre_admission_hubsite", "pre_admission_hubhub"):
            self.assertIn(phase, planning_src)
    def test_proxy_labels_and_airport_policy(self):
        probe_src = ECONOMY.read_text(encoding="utf-8") + AIR_ENGINE_CHOICE.read_text(encoding="utf-8")
        self.assertIn("refit_proxy_choices=", probe_src)
        self.assertIn("native_choices=", probe_src)
        self.assertIn('economics, "post_route"', TASK_ROAD.read_text(encoding="utf-8"))
        # V93 : le break apres un plan grand reste le chemin par defaut (reglage a 0).
        air_src = AIR_PLANNING.read_text(encoding="utf-8")
        self.assertIn("if (bestPlan != null && bestPlan.airport.allowBig) {", air_src)
        self.assertNotIn("V93_AIRPORT_NO_POP_FLOOR", air_src)
        self.assertIn("if (nextCombo < 0) break;", air_src)
        self.assertIn("OpexAirPlansCompleteCombo(ctx, comboIndex, combo)", air_src)

if __name__ == "__main__":
    unittest.main()
