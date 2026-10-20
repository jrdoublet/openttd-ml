"""Contrats V296c : journal des phases d'une tentative rail et predicats natifs AITileList.

Verifie :
- reglage v296_native_sites a defaut 0 aux 4 niveaux (easy, medium, hard, custom), lu une seule fois ;
- globale V296_NATIVE_SITES declaree dans globals_pre.nut et lue dans settings.nut ;
- predicats historiques conserves dans la branche par defaut (branche 0 inchangee) ;
- HasItem utilise dans la branche native (branche 1) ;
- helper OpexV296cBuildFlatBuildableSet avec AddRectangle, Valuate, KeepValue ;
- mode controle 2 avec mesure OpexOpsMeasureBegin/End, OpexV296cPlansSame et OpexDecide("V296C_CHECK", ...) ;
- table phaseOps dans plan et result, et champ phases= dans le journal RAIL_ATTEMPT de task_rail.nut.
"""
import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
if str(SWEEPS) not in sys.path:
    sys.path.insert(0, str(SWEEPS))

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV296cNativeSites(unittest.TestCase):
    def setUp(self):
        self.info = read("info.nut")
        self.settings = read("settings.nut")
        self.globals_pre = read("globals_pre.nut")
        self.builder_rail = read("builder_rail.nut")
        self.task_rail = read("task_rail.nut")
        self.rail_templates = read("rail_templates.nut")

    def test_setting_declaration_and_defaults(self):
        """v296_native_sites declare dans info.nut avec min=0, max=2, defaut=0 aux 4 niveaux."""
        block = re.search(r'AddSetting\(\{\s*name = "v296_native_sites",(.*?)\}\);',
                          self.info, re.S)
        self.assertIsNotNone(block, "v296_native_sites doit etre declare dans info.nut")
        body = block.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(body, rf"{level}_value\s*=\s*0\b",
                             f"defaut {level} doit etre 0")
        self.assertIn("min_value = 0, max_value = 2", body)
        self.assertEqual(self.settings.count('GetSetting("v296_native_sites")'), 1,
                         "v296_native_sites doit etre lu exactement une fois dans settings.nut")
        self.assertIn("V296_NATIVE_SITES <- 0;", self.globals_pre,
                      "V296_NATIVE_SITES doit etre declaree a 0 dans globals_pre.nut")

    def test_settings_load_assigns_global(self):
        """settings.nut charge V296_NATIVE_SITES."""
        self.assertIn('local v296Native = AIController.GetSetting("v296_native_sites");', self.settings)
        self.assertIn("V296_NATIVE_SITES = (v296Native != null && v296Native >= 0 && v296Native <= 2) ? v296Native : 0;", self.settings)

    def test_native_set_builder_helper(self):
        """OpexV296cBuildFlatBuildableSet construit le rectangle et applique KeepValue."""
        body = function_body(self.builder_rail, "function OpexV296cBuildFlatBuildableSet(centerTile, span)")
        self.assertIsNotNone(body, "OpexV296cBuildFlatBuildableSet doit exister")
        self.assertIn("AITileList()", body)
        self.assertIn("AddRectangle", body)
        self.assertIn("Valuate(AITile.IsBuildable)", body)
        self.assertIn("KeepValue(1)", body)
        self.assertIn("Valuate(AITile.GetSlope)", body)
        self.assertIn("KeepValue(AITile.SLOPE_FLAT)", body)

    def test_plans_same_helper(self):
        """OpexV296cPlansSame compare anchor, direction et station_exit de chaque plan dans l'ordre."""
        body = function_body(self.builder_rail, "function OpexV296cPlansSame(plansA, plansB)")
        self.assertIsNotNone(body, "OpexV296cPlansSame doit exister")
        self.assertIn("a.anchor != b.anchor", body)
        self.assertIn("a.direction != b.direction", body)
        self.assertIn("a.station_exit != b.station_exit", body)

    def test_branch_zero_unchanged_predicates(self):
        """La branche historique (set == null) conserve le test IsValidTile && IsBuildable && GetSlope == SLOPE_FLAT."""
        station_body = function_body(self.builder_rail, "function OpexStationPlans(")
        self.assertIsNotNone(station_body, "OpexStationPlans doit exister")
        self.assertIn("AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&", station_body)
        self.assertIn("AITile.GetSlope(lead) == AITile.SLOPE_FLAT", station_body)
        self.assertIn("AIMap.IsValidTile(platformTile) && AITile.IsBuildable(platformTile) &&", station_body)
        self.assertIn("AITile.GetSlope(platformTile) == AITile.SLOPE_FLAT", station_body)

        join_body = function_body(self.builder_rail, "function OpexJoinPlatformPlans(")
        self.assertIsNotNone(join_body, "OpexJoinPlatformPlans doit exister")
        self.assertIn("AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&", join_body)
        self.assertIn("AITile.GetSlope(lead) == AITile.SLOPE_FLAT", join_body)
        self.assertIn("AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) &&", join_body)
        self.assertIn("AITile.GetSlope(tile) == AITile.SLOPE_FLAT", join_body)

        parallel_body = function_body(self.builder_rail, "function OpexV190FindParallelPlatformPlans(")
        self.assertIsNotNone(parallel_body, "OpexV190FindParallelPlatformPlans doit exister")
        self.assertIn("AIMap.IsValidTile(lead2) && AITile.IsBuildable(lead2) &&", parallel_body)
        self.assertIn("AITile.GetSlope(lead2) == AITile.SLOPE_FLAT", parallel_body)
        self.assertIn("AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) &&", parallel_body)
        self.assertIn("AITile.GetSlope(tile) == AITile.SLOPE_FLAT", parallel_body)

    def test_branch_one_has_item_predicate(self):
        """La branche native utilise nativeSet.HasItem."""
        station_body = function_body(self.builder_rail, "function OpexStationPlans(")
        self.assertIn("AIMap.IsValidTile(lead) && nativeSet.HasItem(lead)", station_body)
        self.assertIn("AIMap.IsValidTile(platformTile) && nativeSet.HasItem(platformTile)", station_body)

        join_body = function_body(self.builder_rail, "function OpexJoinPlatformPlans(")
        self.assertIn("AIMap.IsValidTile(lead) && nativeSet.HasItem(lead)", join_body)
        self.assertIn("AIMap.IsValidTile(tile) && nativeSet.HasItem(tile)", join_body)

        parallel_body = function_body(self.builder_rail, "function OpexV190FindParallelPlatformPlans(")
        self.assertIn("AIMap.IsValidTile(lead2) && nativeSet.HasItem(lead2)", parallel_body)
        self.assertIn("AIMap.IsValidTile(tile) && nativeSet.HasItem(tile)", parallel_body)

    def test_mode_two_control_and_check_log(self):
        """Mode 2 : mesure ops_old et ops_new, OpexDecide V296C_CHECK sous DECISION_LOG, et rend plansOld."""
        for fn_name in ("function OpexStationPlans(",
                        "function OpexJoinPlatformPlans(",
                        "function OpexV190FindParallelPlatformPlans("):
            body = function_body(self.builder_rail, fn_name)
            self.assertIsNotNone(body, f"{fn_name} doit exister")
            self.assertIn("V296_NATIVE_SITES == 2", body)
            self.assertIn("OpexOpsMeasureBegin()", body)
            self.assertIn("OpexOpsMeasureEnd(", body)
            self.assertIn("OpexV296cPlansSame(", body)
            self.assertIn('OpexDecide("V296C_CHECK"', body)
            self.assertIn("fn=", body)
            self.assertIn("same=", body)
            self.assertIn("n_old=", body)
            self.assertIn("n_new=", body)
            self.assertIn("ops_old=", body)
            self.assertIn("ops_new=", body)
            self.assertIn("return plansOld", body)

    def test_phase_ops_in_plan_and_result(self):
        """Table phaseOps dans plan et result, mise a jour sur les phases rail."""
        prep_body = function_body(self.builder_rail, "function OpexPrepareRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)")
        self.assertIn("phaseOps = { plans = -1, search = -1, stations = -1, track = -1, trains = -1 }", prep_body)
        self.assertIn("plan.phaseOps.plans", prep_body)

        plan_route_body = function_body(self.builder_rail, "function OpexPlanRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)")
        self.assertIn("plan.phaseOps.search", plan_route_body)

        exec_body = function_body(self.builder_rail, "function OpexExecuteRailPlan(catalog, budget, candidate, plan, cashReserve)")
        self.assertIn("phaseOps = { plans = plan.phaseOps.plans", exec_body)
        self.assertIn("result.phaseOps.stations", exec_body)
        self.assertIn("result.phaseOps.track", exec_body)
        self.assertIn("result.phaseOps.trains", exec_body)

        v190_exec_body = function_body(self.builder_rail, "function OpexV190ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve)")
        self.assertIn("phaseOps = { plans = plan.phaseOps.plans", v190_exec_body)
        self.assertIn("result.phaseOps.stations", v190_exec_body)
        self.assertIn("result.phaseOps.track", v190_exec_body)
        self.assertIn("result.phaseOps.trains", v190_exec_body)

    def test_rail_attempt_phases_field(self):
        """task_rail.nut RAIL_ATTEMPT journalise phases=<plans>/<search>/<stations>/<track>/<trains>."""
        body = function_body(self.task_rail, "function OpexAI::_recordRailAttempt(candidate, result, posPacked, year, railPlan = null)")
        self.assertIsNotNone(body, "OpexAI::_recordRailAttempt doit exister")
        self.assertIn('phasesStr = "-1/-1/-1/-1/-1";', body)
        self.assertIn('"phaseOps" in result', body)
        self.assertIn('phases=" + phasesStr', body)
        self.assertIn('OpexDecide("RAIL_ATTEMPT"', body)


if __name__ == "__main__":
    unittest.main()
