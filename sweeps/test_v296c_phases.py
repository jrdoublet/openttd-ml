"""Contrats V296c : journal des phases d'une tentative rail.

Verifie :
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


class TestV296cPhases(unittest.TestCase):
    def setUp(self):
        self.builder_rail = read("builder_rail.nut")
        self.task_rail = read("task_rail.nut")

    def test_phase_ops_in_plan_and_result(self):
        """Table phaseOps dans plan et result, mise a jour sur les phases rail."""
        prep_body = function_body(self.builder_rail, "function OpexPrepareRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)")
        self.assertIn("phaseOps = { plans = -1, search = -1, stations = -1, track = -1, trains = -1 }", prep_body)
        self.assertIn("plan.phaseOps.plans", prep_body)

        plan_route_body = function_body(self.builder_rail, "function OpexPlanRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)")
        self.assertIn("plan.phaseOps.search", plan_route_body)

        exec_body = function_body(self.builder_rail, "function OpexExecuteRailPlan(catalog, budget, candidate, plan)")
        self.assertIn("phaseOps = { plans = plan.phaseOps.plans", exec_body)
        self.assertIn("result.phaseOps.stations", exec_body)
        self.assertIn("result.phaseOps.track", exec_body)
        self.assertIn("result.phaseOps.trains", exec_body)

        v190_exec_body = function_body(self.builder_rail, "function OpexV190ExecuteRailPlan(catalog, budget, candidate, plan)")
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
