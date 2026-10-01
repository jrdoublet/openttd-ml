"""R1 source/arithmetic contracts only; no Squirrel VM, purchases or game."""
import ast
from pathlib import Path
import re
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    return source.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


def arithmetic(expression, **values):
    """Evaluate only nonnegative integer arithmetic extracted from the source."""
    expression = expression.replace(".tointeger()", "")
    for name, value in values.items():
        expression = re.sub(rf"\b{re.escape(name)}\b", str(value), expression)
    tree = ast.parse(expression.replace("/", "//"), mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise AssertionError(f"Unsupported arithmetic: {expression}")
    return eval(compile(tree, "<source arithmetic>", "eval"), {"__builtins__": {}})


class TestPartialFleet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ai = ROOT / "ai/OpexAI"
        cls.projects = read_projects_source()
        cls.task = (ai / "task_projects.nut").read_text(encoding="utf-8")
        cls.air = (ai / "task_air.nut").read_text(encoding="utf-8")
        cls.builder = read_builder_air()
        cls.fit = function(cls.projects, "OpexProjectFitFleetToBudget")
        cls.select = function(cls.projects, "OpexProjectSelectAffordable")

    def test_fit_precedes_floor_probes_and_common_ranking(self):
        fit = self.select.index("OpexProjectFitFleetToBudget(project, capitalBudget)")
        for marker in ("OpexC118PrepareSelection", "local floorProfit", "project.fundScore <-"):
            self.assertLess(fit, self.select.index(marker))
        self.assertIn("alternatives = fittedAlternatives;", self.select)
        self.assertIn("OpexProjectInsertDefensive(affordable, project, scoreKey", self.select)

    def test_four_requested_quantity_arithmetic_and_unit_boundary(self):
        purchase = re.search(r"local purchaseBudget = ([^;]+);", self.fit).group(1)
        quantity = re.search(r"local quantity = ([^;]+);", self.fit).group(1)
        self.assertIn("purchaseBudget < entry.planePrice) return null;", self.fit)
        self.assertIn("if (quantity >= entry.want) return project;", self.fit)
        # Capital is already net of cash reserve; the extra 1000 is not per plane.
        for budget, expected in ((1000, 0), (30999, 0), (31000, 1), (60999, 1),
                                 (61000, 2), (91000, 3), (121000, 4), (181000, 4)):
            with self.subTest(budget=budget):
                available = arithmetic(purchase, capitalBudget=budget)
                count = arithmetic(quantity, **{"purchaseBudget": available, "entry.planePrice": 30000})
                self.assertEqual(min(count, 4), expected)

    def test_linear_profit_revenue_and_capital_match_reduced_quantity(self):
        for quantity in (1, 2, 3):
            for field, total in (("profitAnnual", 80000), ("revenueAnnual", 120000)):
                expression = re.search(rf"fitted\.{field} = (\(project\.[^;]+);", self.fit).group(1)
                actual = arithmetic(expression, **{f"project.{field}": total,
                                                     "entry.want": 4, "quantity": quantity})
                self.assertEqual(actual, total // 4 * quantity)
        self.assertIn("fitted.capital = quantity * entry.planePrice;", self.fit)
        self.assertIn("fitted.budgetCapital = fitted.capital + 1000;", self.fit)
        self.assertIn("fitted.budgetScore = OpexProjectScore(fitted.revenueAnnual, fitted.budgetCapital);", self.fit)

    def test_no_mutation_of_pool_or_provenance_and_one_slice_only(self):
        self.assertIn("local fitted = clone project;", self.fit)
        self.assertIn("local reduced = clone entry;", self.fit)
        self.assertIn("reduced.want = quantity;", self.fit)
        self.assertNotRegex(self.fit, r"\b(?:entry\.want|project\.profitAnnual)\s*=")
        self.assertNotIn("profitIsObserved =", self.fit)
        self.assertNotIn(".append(", self.fit)
        self.assertIn('project.mode != "fleet") return project;', self.fit)

    def test_c84_recomputes_exact_marginal_not_proportional_profit(self):
        c84 = self.fit.split("if (!c121BelowTarget", 1)[1].split("} else {", 1)[0]
        self.assertIn('if (!("c84Catalog" in entry)) return null;', c84)
        self.assertIn("OpexAirExistingLineMarginalEconomics(entry.c84Catalog, line, have, quantity)", c84)
        self.assertIn("fitted.profitAnnual = marginal.profitAnnual;", c84)
        self.assertNotIn("project.profitAnnual / entry.want", c84)
        resize = function(self.air, "OpexAI::_resizeAirFleets")
        self.assertIn("baseVehicles = have", resize)
        self.assertIn("fleetEntry.c84Catalog <- { paxCargo = this._catalog.paxCargo", resize)
        self.assertIn('("mailCargo" in this._catalog)', resize)

    def test_changed_inventory_rejected_before_purchase_and_at_selection(self):
        self.assertIn('have != entry.baseVehicles) return null;', self.fit)
        execute = function(self.task, "OpexAI::_tryBuildFleetProject")
        guard = execute.index("liveCount != entry.baseVehicles")
        self.assertLess(guard, execute.index("OpexAirAddPlane("))
        self.assertIn('reason = "fleet_stale"', execute)
        self.assertIn("k < entry.want", execute)

    def test_existing_reserve_and_last_purchase_guard_are_preserved(self):
        make = function(self.projects, "OpexProjectFromFleet")
        add = function(self.builder, "OpexAirAddPlane")
        execute = function(self.task, "OpexAI::_tryBuildFleetProject")
        self.assertIn("budgetCapital = capital + 1000", make)
        self.assertIn("price + OpexCashReserve() + 1000", add)
        self.assertIn("if (money < need)", add)
        self.assertIn("entry.planePrice + OpexCashReserve()", execute)
        self.assertNotIn("SetLoanAmount", self.fit)
        self.assertIn("c75BuiltKeys[OpexC69AttemptKey(project)] <- true;", self.task)

    def test_c121_and_c69_scoring_stay_in_common_selector(self):
        self.assertIn("local c121BelowTarget = C121_AIR_ECONOMICS", self.fit)
        self.assertIn("&& !OpexC121ProjectHasRealization(project);", self.select)
        self.assertIn("OpexCalibratedProfit(project) : project.profitAnnual", self.select)
        self.assertIn("!fleetExemptDecision) ? kDec : decisionFinanceCapital", self.select)
        self.assertNotIn("fundScore", self.fit)


if __name__ == "__main__":
    unittest.main()