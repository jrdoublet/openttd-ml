"""ESTIM-1 bit 16: distance calibration, score/finance separation and contracts."""
import re
import unittest
from pathlib import Path

from estim_unifie_off_lots import estim_off


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(name):
    return (ROOT / name).read_text(encoding="utf-8")


def coefficient(name):
    return float(re.search(r"^" + name + r"\s*<-\s*([0-9.]+);", src("globals_pre.nut"), re.M).group(1))


class EstimRailDistanceContracts(unittest.TestCase):
    def test_profile_revenue_and_cost_are_monotone_and_centered(self):
        ar = coefficient("ESTIM_RAIL_KR_PROFILE_A")
        br = coefficient("ESTIM_RAIL_KR_PROFILE_B")
        ac = coefficient("ESTIM_RAIL_KC_A")
        bc = coefficient("ESTIM_RAIL_KC_B")
        self.assertAlmostEqual(ar + br * 134.497, 0.92, places=4)
        self.assertGreater(br, 0)
        self.assertGreater(bc, 0)
        self.assertLess(ar + br * 70, ar + br * 210)
        self.assertLess(ac + bc * 70, ac + bc * 210)

    def test_rail_only_under_bit16_and_funding_guard_unaffected(self):
        model = src("projects_models.nut")
        select = src("projects_selection.nut")
        finance = src("projects_finance.nut")
        self.assertIn('project.mode == "rail"', model)
        self.assertIn('if ((ESTIM_UNIFIE & 1) == 0', model)
        self.assertIn('project.profitAnnual - (1.0 - kR) * project.revenueAnnual', model)
        self.assertIn('project.capital.tofloat() * factor + 0.5', model)
        self.assertIn('capitalIsActual', model)
        self.assertGreaterEqual(model.count('if (calibratedDistance > 250) calibratedDistance = 250;'), 2)
        self.assertGreaterEqual(model.count('if (calibratedDistance < 15) calibratedDistance = 15;'), 2)
        self.assertEqual(select.count('scoreDecisionFinanceCapital = OpexEstimRailScoreCapital('), 2)
        self.assertEqual(select.count('if ((ESTIM_UNIFIE & 16) != 0)'), 2)
        self.assertNotIn('OpexEstimRailScoreCapital', finance)
        self.assertNotIn('ESTIM_RAIL_KC_', finance)

    def test_learning_is_level_only_and_reload_recalculates(self):
        model = src("projects_models.nut")
        self.assertIn('return ESTIM_K_R.rail * profile / ESTIM_K_R_PRIOR.rail', model)
        self.assertIn('if ((ESTIM_UNIFIE & 1) == 0 && m != "rail") continue;', model)
        self.assertIn('if ((ESTIM_UNIFIE & 1) == 0 && mode != "rail") return;', model)
        self.assertIn('(ESTIM_UNIFIE & 17) != 0', src("persist.nut"))
        self.assertIn('(ESTIM_UNIFIE & 17) != 0', src("task_report.nut"))
        self.assertIn('(ESTIM_UNIFIE & 17) != 0', src("settings.nut"))

    def test_marginal_revenue_uses_same_profile(self):
        self.assertIn('OpexEstimRailRevenueFactor(distance)', src("task_v249.nut"))
        for name in ("task_v257.nut", "task_v284.nut", "task_v259.nut"):
            with self.subTest(name=name):
                self.assertIn('line.distance', src(name))
        self.assertIn('OpexEstimRailRevenueFactor(', src("projects_builders.nut"))

    def test_v257_distance_is_passed_from_both_callers(self):
        code = src("task_v257.nut")
        self.assertIn('function OpexEstimV257Project(current, target, oldVehicle, sale, line)', code)
        self.assertIn('OpexEstimV257Project(current, best, vehicle, sale, line)', code)
        self.assertIn('OpexEstimV257Project(currentPlan, targetPlan, oldVehicle, sale, line)', code)
        self.assertIn('netPrice / years, netPrice, -1, null, line.distance)', code)
        self.assertIn('kDec, null, line.distance)', src('task_v284.nut'))

    def test_off_projection_removes_bit16_and_preserves_historical_behavior(self):
        for name in ("info.nut", "globals_pre.nut", "projects_models.nut", "projects_selection.nut"):
            with self.subTest(name=name):
                historical = estim_off(name, src(name))
                self.assertNotIn('OpexEstimRailScoreCapital', historical)
                self.assertNotIn('ESTIM_RAIL_KC_A', historical)
                self.assertNotIn('ESTIM_RAIL_KR_PROFILE_A', historical)


if __name__ == "__main__":
    unittest.main()
