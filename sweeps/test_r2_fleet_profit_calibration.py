"""R2 source contracts only; no Squirrel execution or economic simulation."""
from pathlib import Path
import unittest
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    return source.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


class TestFleetProfitCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_projects_source()
        cls.fleet = function(cls.source, "OpexProjectFromFleet")
        cls.c70 = function(cls.source, "OpexC70Profit")
        cls.c82 = function(cls.source, "OpexC82Profit")

    def test_only_positive_legacy_observation_sets_marker(self):
        self.assertIn("local profitIsObserved = false;", self.fleet)
        self.assertEqual(self.fleet.count("profitIsObserved = true;"), 1)
        self.assertRegex(
            self.fleet,
            r'if \(\("lastProfit" in line\) && line.lastProfit > 0\)\s*\{\s*'
            r'perPlaneProfit = line.lastProfit / have;\s*profitIsObserved = true;',
        )

    def test_prediction_fallback_remains_model_based(self):
        fallback = self.fleet.split('} else if (("predRevenue" in line)', 1)[1]
        self.assertIn("perPlaneProfit = (line.predRevenue - running) / planes;", fallback)
        self.assertIn("if (perPlaneProfit <= 0) return null;", fallback)
        self.assertNotIn("profitIsObserved = true;", fallback)
        self.assertIn("profit = perPlaneProfit * entry.want;", fallback)

    def test_provenance_travels_with_profit_not_live_line_state(self):
        self.assertIn("profitIsObserved = profitIsObserved,", self.fleet)
        self.assertIn("profitAnnual = profit, revenueAnnual = revenue,", self.fleet)
        for calibrated in (self.c70, self.c82):
            with self.subTest(calibrated=calibrated[:35]):
                self.assertNotIn("lastProfit", calibrated)
                self.assertIn('("profitIsObserved" in project) && project.profitIsObserved', calibrated)

    def test_c70_observed_profit_returns_before_model_factor(self):
        self.assertRegex(
            self.c70,
            r'if \(project != null && \("profitIsObserved" in project\) && project.profitIsObserved\)'
            r'\s*return project.profitAnnual;',
        )
        self.assertLess(self.c70.index("project.profitIsObserved"), self.c70.index("if (!C70_MODE_CALIBRATION)"))
        self.assertIn("return project.profitAnnual * OpexC70Factor(project);", self.c70)

    def test_c82_observed_profit_returns_before_engine_lookup(self):
        self.assertRegex(
            self.c82,
            r'if \(project != null && \("profitIsObserved" in project\) && project.profitIsObserved\)'
            r'\s*return project.profitAnnual;',
        )
        self.assertLess(self.c82.index("project.profitIsObserved"), self.c82.index("OpexC82ProjectEngine(project)"))
        self.assertIn("project.profitAnnual * OpexC82EngineFactor(e)", self.c82)
        self.assertIn("return OpexC70Profit(project);", self.c82)

    def test_c84_model_and_c121_specific_realization_are_preserved(self):
        marginal = self.fleet.split("if (c121BelowTarget)", 1)[1].split("if (!usedTargetMarginal)", 1)[0]
        self.assertNotIn("profitIsObserved = true;", marginal)
        self.assertIn("profit = entry.c84MarginalProfit;", marginal)
        self.assertIn("learnedFactor / builtFactor", marginal)
        self.assertIn("profit = perPlaneProfit * entry.want;", marginal)
        for calibrated in (self.c70, self.c82):
            self.assertIn('project.mode == "fleet"', calibrated)
            self.assertIn("&& OpexC121ProjectHasRealization(project, false)) return project.profitAnnual;", calibrated)


if __name__ == "__main__":
    unittest.main()
