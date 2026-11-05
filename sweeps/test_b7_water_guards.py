"""Contrats de connectivité du chemin eau historique conservé après retrait de Lakes."""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = fleet_read_text(ROOT / "ai" / "OpexAI" / "builder_water.nut", encoding="utf-8")


class B7WaterGuardsTest(unittest.TestCase):
    def test_unknown_distance_is_rejected_before_economics(self):
        start = BUILDER.index("navigableDistance = OpexWaterFindConnection(sites[a], sites[b]);")
        end = BUILDER.index("local economics = OpexWaterEconomics(", start)
        self.assertRegex(BUILDER[start:end], r"if \(navigableDistance < 0\) \{[^}]*continue;\s*\}")
        self.assertNotIn("navigableDistance = tariffDistance", BUILDER[start:end])

    def test_real_docks_checked_before_depot(self):
        start = BUILDER.index("OpexWaterFindConnection(realA, realB) < 0")
        end = BUILDER.index("local depotPlan = OpexWaterFindDepot(realA, realB);", start)
        self.assertIn("OpexWaterRollback(dockA, dockB, null, null)", BUILDER[start:end])
        self.assertIn("return OpexWaterStampCost(result, costs);", BUILDER[start:end])


if __name__ == "__main__":
    unittest.main()
