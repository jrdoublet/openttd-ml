"""ESTIM-1 lot 3 (bit 4) : contrats de projets M1 existants.

Tests statiques : le Python hote ne compile pas le Squirrel. Le smoke NoAI
sera lance par le pilote de la campagne apres integration des autres lots.
"""

import unittest

from test_v261_forum_behaviours import body, source


class EstimVProjectsContracts(unittest.TestCase):
    def test_shared_contract_loaded_before_all_projects(self):
        main = source("main.nut")
        first = main.index('require("task_v249.nut")')
        for name in ("task_v252.nut", "task_v257.nut", "task_v284.nut", "task_v259.nut"):
            self.assertLess(first, main.index('require("' + name + '")'))
        model = body("task_v249.nut", "OpexEstimVProject")
        for field in ("deltaR", "deltaE", "deltaA", "deltaC", "deltaP", "score"):
            self.assertIn(field + " =", model)
        self.assertIn("kR * deltaR", model)
        self.assertIn("calibrated - deltaE - deltaA", model)
        self.assertIn("OpexProjectScore(deltaP, denominator)", model)
        self.assertNotRegex(model, r"ESTIM_UNIFIE\s*&\s*1\b")

    def test_statue_uses_mode_specific_revenues_and_no_five_year_payback_on_bit4(self):
        code = source("task_v249.nut")
        self.assertIn("townModeRevenues", code)
        self.assertIn("cargoModeRevenues", code)
        self.assertIn("revenueMode in ESTIM_K_R", body("task_v249.nut", "OpexEstimVProject"))
        self.assertIn('OpexEstimVProject("mixed", townGain, 0, 0, statueCost,', code)
        self.assertIn("V249_STATUE == 2 || (ESTIM_UNIFIE & 4) != 0", code)
        self.assertIn("(ESTIM_UNIFIE & 4) == 0 && bestGain * V249_HORIZON_YEARS <= cost", code)

    def test_air_replacement_same_fleet_model_and_calibrated_delta(self):
        code = source("task_v252.nut")
        fn = body("task_v252.nut", "OpexEstimV252Project")
        self.assertEqual(fn.count("OpexAirEconomics("), 2)
        self.assertIn("after.revenueAnnual - before.revenueAnnual", fn)
        self.assertIn("newPlane.runningCost - oldPlane.runningCost", fn)
        self.assertIn("netCapital / years", fn)
        self.assertIn('OpexEstimVProject("air"', fn)
        self.assertIn("project.score <= bestProject.score", code)
        self.assertIn("if ((ESTIM_UNIFIE & 4) == 0) break;", code)

    def test_rail_replacement_checks_same_contract_again_at_depot(self):
        fn = body("task_v257.nut", "OpexEstimV257Project")
        self.assertIn("target.revenue - current.revenue", fn)
        self.assertIn("target.running - AIVehicle.GetRunningCost(oldVehicle)", fn)
        self.assertIn("netPrice / years", fn)
        source_code = source("task_v257.nut")
        self.assertIn('OpexEstimVLog("V257_DEPOT"', source_code)
        self.assertIn("estimPays = refreshed.deltaP > 0 && refreshed.score > 0", source_code)
        self.assertIn("(remaining <= 0 || pending.gain <= 0 || pending.gain * remaining < cost)", source_code)
        self.assertIn("estimProject.score > selectedScore", source_code)

    def test_bridge_replacement_no_remaining_years_gate_under_bit4(self):
        fn = body("task_v259.nut", "OpexAI::_v259EvaluateAndRenew")
        self.assertIn("OpexEstimVProject(mode, cycleFraction * revenue, 0, 0, cost,", fn)
        self.assertIn("-1, null, line.distance", fn)
        self.assertIn("estimViable = project.deltaP > 0 && project.score > 0", fn)
        self.assertIn("(ESTIM_UNIFIE & 4) == 0 && totalGain < cost.tofloat()", fn)
        self.assertIn("AIBridge.BuildBridge", fn)

    def test_rail_growth_compares_one_and_two_trains_and_scores_candidates(self):
        fn = body("task_v284.nut", "OpexEstimV284Project")
        self.assertIn("OpexV257Plan(", fn)
        self.assertIn("add ? monthly / 2.0 : monthly", fn)
        self.assertIn("newRevenue += existing.revenue", fn)
        self.assertIn("newRunning += oldRunning", fn)
        self.assertIn("netVehiclePrice / years", fn)
        code = source("task_v284.nut")
        self.assertIn("score = candidateEquipment.project.score", code)
        self.assertIn('OpexEstimVLog("V284"', code)
        self.assertIn("if (v233Input && (ESTIM_UNIFIE & 4) == 0", code)

    def test_no_unconditional_lot3_computation_for_default_off(self):
        for name in ("task_v249.nut", "task_v252.nut", "task_v257.nut",
                     "task_v259.nut", "task_v284.nut"):
            with self.subTest(name=name):
                code = source(name)
                self.assertIn("ESTIM_UNIFIE & 4", code)
                self.assertIn("OpexEstimVProject" if name == "task_v249.nut"
                              else "OpexEstimV", code)


if __name__ == "__main__":
    unittest.main()
