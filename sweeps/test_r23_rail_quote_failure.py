"""R23 source contracts, not execution of AITestMode or a physical-cost proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestRailQuoteFailure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "ai/OpexAI/builder_rail.nut").read_text(encoding="utf-8")
        cls.simulate = cls.source.split("function OpexSimulateRailInfraCost(", 1)[1].split("\nfunction ", 1)[0]
        cls.quote = cls.source.split("function OpexQuoteRailCapital(", 1)[1].split("\nfunction ", 1)[0]
        cls.execute = cls.source.split("function OpexExecuteRailPlan(", 1)[1].split("\nfunction ", 1)[0]

    def test_simulated_clearance_and_stations_fail_closed(self):
        self.assertIn("local testMode = AITestMode();", self.simulate)
        self.assertIn("local accounting = AIAccounting();", self.simulate)
        self.assertEqual(self.simulate.count("if (!AITile.DemolishTile(tile)) return OpexRailQuoteFailure("), 2)
        for side in ("A", "B"):
            self.assertIn(f"if (!AIRail.BuildRailStation(plan{side}.anchor", self.simulate)
            self.assertIn(f'failure, "STNFAIL", plan{side}.anchor, AIError.GetLastError()', self.simulate)

    def test_all_track_command_results_and_empty_bridge_list_are_checked(self):
        for command in ("AIRail.BuildRail(prev, cur, next)", "AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)",
                        "AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next)"):
            self.assertIn(f"ok = {command};", self.simulate)
        self.assertIn("if (bridges.IsEmpty())", self.simulate)
        self.assertIn('return OpexRailQuoteFailure(failure, "TRKFAIL", cur, error);', self.simulate)

    def test_existing_track_exception_requires_actual_own_compatible_connection(self):
        self.assertIn("if (!ok) {\n        local error = AIError.GetLastError();", self.simulate)
        self.assertIn("if (error == AIError.ERR_ALREADY_BUILT &&", self.simulate)
        self.assertIn("AIMap.DistanceManhattan(prev, cur) == 1 && AIMap.DistanceManhattan(cur, next) == 1", self.simulate)
        self.assertIn("AIRail.IsRailTile(cur)", self.simulate)
        self.assertIn("AITile.GetOwner(cur) == AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)", self.simulate)
        self.assertIn("AIRail.GetRailType(cur) == AIRail.GetCurrentRailType()", self.simulate)
        self.assertIn("AIRail.AreTilesConnected(prev, cur, next)) continue;", self.simulate)
        self.assertNotIn("if (ok &&", self.simulate)  # no connectivity check on simulated new rails

    def test_partial_cost_cannot_be_promoted_to_actual_capital(self):
        self.assertIn("if (realInfra == null) return null;", self.quote)
        guard = self.execute.split("if (realCapital == null)", 1)[1].split("if (realCapital > 0)", 1)[0]
        self.assertIn("result.error = quoteFailure.error;", guard)
        self.assertIn("return result;", guard)
        self.assertLess(self.execute.index("if (realCapital == null)"), self.execute.index("OpexApplyRailActualCapital("))
        self.assertLess(self.execute.index("if (realCapital == null)"), self.execute.index("budget.begin();"))
        self.assertLess(self.execute.index("if (realCapital == null)"), self.execute.index("AITile.DemolishTile("))

    def test_cash_failure_retains_retry_contract(self):
        guard = self.execute.split("if (realCapital == null)", 1)[1].split("if (realCapital > 0)", 1)[0]
        # CASH must take precedence even when an exact-platform refresh requests
        # REPLAN_GEOM; other failures retain the original quote reason.
        self.assertRegex(
            guard,
            r'result\.reason\s*=\s*result\.error\s*==\s*AIError\.ERR_NOT_ENOUGH_CASH'
            r'\s*\?\s*"CASH"\s*:\s*\(\s*replanGeometry\s*\?\s*"REPLAN_GEOM"'
            r'\s*:\s*quoteFailure\.reason\s*\)\s*;',
        )
        task = (ROOT / "ai/OpexAI/task_rail.nut").read_text(encoding="utf-8")
        consume = task.split("function OpexAI::_consumeRailSearch(", 1)[1].split("\nfunction ", 1)[0]
        cash_at = consume.index('if (result.reason == "CASH")')
        clear_at = consume.index("candidate.railPlan = null;")
        self.assertLess(cash_at, clear_at)
        cash_branch = consume[cash_at:clear_at]
        self.assertIn('return { outcome = "cash", reason = "cash_at_build", error = cashError };', cash_branch)
        self.assertNotIn("candidate.railPlan =", cash_branch)
        self.assertLess(clear_at, consume.index("this._recordRailAttempt("))

    def test_valid_quote_keeps_depot_vehicle_and_finance_components(self):
        self.assertIn("simulatedInfra = accounting.GetCosts();", self.simulate)
        self.assertIn("return realInfra + depotCost + vehicleCost;", self.quote)
        self.assertIn("OpexApplyRailActualCapital(candidate, realCapital);", self.execute)
        self.assertIn("if (!OpexRailVehicleSlotAvailable())", self.execute)


if __name__ == "__main__":
    unittest.main()
