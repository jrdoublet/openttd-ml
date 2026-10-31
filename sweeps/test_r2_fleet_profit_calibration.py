"""R2/V161: la provenance d'un gain net doit rester attachee au projet."""
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

    def test_next_marginal_only(self):
        self.assertIn("local profit = entry.v161Profit;", self.fleet)
        self.assertIn("local revenue = entry.v161DeltaR;", self.fleet)
        self.assertIn("entry.v161BaseVehicles != have", self.fleet)
        self.assertIn("entry.v161Profit != entry.v161DeltaR - entry.v161DeltaE - entry.v161DeltaA",
                      self.fleet)
        self.assertNotIn("line.lastProfit / have", self.fleet)
        self.assertNotIn("line.predRevenue", self.fleet)

    def test_provenance_travels_with_project(self):
        self.assertIn("profitIsObserved = false,", self.fleet)
        self.assertIn("profitAnnual = profit, revenueAnnual = revenue,", self.fleet)
        self.assertIn("project.v161Source <- entry.v161Source;", self.fleet)
        self.assertIn("project.v161NetMarginalModeled <- true;", self.fleet)
        self.assertNotIn("lastProfit", self.c70)
        self.assertIn('("profitIsObserved" in project) && project.profitIsObserved', self.c70)

    def test_c70_does_not_calibrate_net_marginal_twice(self):
        self.assertIn('("v161NetMarginalModeled" in project)', self.c70)
        self.assertLess(self.c70.index("project.v161NetMarginalModeled"),
                        self.c70.index("return project.profitAnnual * OpexC70Factor(project);"))
        self.assertIn("return project.profitAnnual * OpexC70Factor(project);", self.c70)

    def test_c82_calibration_removed(self):
        for token in (
            "OpexC82Profit", "OpexC82EngineFactor", "OpexC82ProjectEngine",
            "OpexC82RecomputeFactors", "C82_ENGINE_CALIBRATION",
        ):
            self.assertNotIn(token, self.source)

    def test_c121_net_and_snapshot_validation(self):
        fleet = (ROOT / "ai" / "OpexAI" / "air_fleet.nut").read_text(encoding="utf-8")
        self.assertIn("line.c121MarginalBaseVehicles == have", fleet)
        self.assertIn("line.c121LastMarginalProfit <= 0", fleet)
        self.assertIn("if (neighbours > 0) return null;", fleet)
        self.assertIn('project.mode == "fleet"', self.c70)
        self.assertIn("&& OpexC121ProjectHasRealization(project)) return project.profitAnnual;",
                      self.c70)


if __name__ == "__main__":
    unittest.main()
