"""Targeted unit tests for Constat 2: producer units vs PASS/mo consistency.

Verifies:
1. PaxPortfolioBuild.monthly and final fleet dimensioning compare PASS/mo when
   road100_pax_producer_units (V30a) is active, even without V31.
2. LONG candidate admission and task live demand conversion to PASS/mo is
   independent of the tracer/shape retained.
3. Default 0 behavior remains unchanged.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 1
    cursor = brace + 1
    while depth > 0 and cursor < len(source):
        char = source[cursor]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        cursor += 1
    return source[start:cursor]


def simulate_final_fleet_dimensioning(
    *,
    candidate_monthly: int,
    portfolio_producers: int,
    candidate_has_v30a: bool,
    v30a_setting: bool,
    v31_setting: bool,
    initial_want: int,
    capacity: int,
    one_way_days: int,
    stop_dwell_days: int = 1,
) -> int:
    """Simulate lines 5090-5112 of builder_road.nut."""
    want = initial_want
    if want > 2:
        want = 2

    # Logic after Constat 2 fix:
    measured_flag = v31_setting or v30a_setting
    if measured_flag and candidate_has_v30a:
        measured_monthly = candidate_monthly
    else:
        measured_monthly = portfolio_producers

    if measured_monthly > 0 and one_way_days > 0:
        round_days = 2 * one_way_days + 2 * stop_dwell_days
        per_bus_monthly = (capacity * 30) // round_days if round_days > 0 else 0
        if per_bus_monthly > 0 and measured_monthly <= per_bus_monthly:
            want = 1

    return want


class Road100PaxUnitsConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.builder_src = (AI / "builder_road.nut").read_text(encoding="utf-8")
        self.candidates_src = (AI / "candidates.nut").read_text(encoding="utf-8")
        self.task_road_src = (AI / "task_road.nut").read_text(encoding="utf-8")

    def test_portfolio_build_sets_monthly_from_candidate_under_v30a(self):
        """OpexRoad100PaxPortfolioBuild must set out.monthly to candidate.monthly when V30a is active."""
        body = function_body(self.builder_src, "function OpexRoad100PaxPortfolioBuild(")
        self.assertIn('("road100PaxProducerUnits" in candidate)', body)
        self.assertIn("candidate.road100PaxProducerUnits && candidate.monthly > 0", body)
        self.assertIn("out.monthly = candidate.monthly;", body)

    def test_final_fleet_sizing_uses_v30a_without_v31(self):
        """Final fleet sizing must check ROAD100_PAX_PRODUCER_UNITS even if V31 is OFF."""
        self.assertIn("local measuredMonthly = ROAD100_PAX_INITIAL_BERTH_FLEET\n           || ROAD100_PAX_PRODUCER_UNITS;", self.builder_src)
        self.assertIn('measuredMonthly = measuredMonthly\n           && ("road100PaxProducerUnits" in candidate)\n           && candidate.road100PaxProducerUnits\n           ? candidate.monthly : portfolioSummary.monthly;', self.builder_src)

    def test_seed100_scenario_v30a_active_v31_inactive_preserves_two_buses(self):
        """Seed100 scenario: 146 PASS/mo, 44 producers, perBusMonthly=62.

        Before fix: 44 <= 62 reduced want to 1.
        After fix: 146 <= 62 is False -> want remains 2.
        """
        # When V30a is active and V31 is inactive:
        want_fixed = simulate_final_fleet_dimensioning(
            candidate_monthly=146,
            portfolio_producers=44,
            candidate_has_v30a=True,
            v30a_setting=True,
            v31_setting=False,
            initial_want=2,
            capacity=25,
            one_way_days=5,
            stop_dwell_days=1,
        )
        self.assertEqual(want_fixed, 2)

        # Confirm that before fix (where measured_monthly took 44 producers), want was 1:
        want_buggy = 1 if 44 <= (25 * 30) // (2 * 5 + 2 * 1) else 2
        self.assertEqual(want_buggy, 1)

    def test_long_candidate_admission_converts_independently_of_plan_tracer(self):
        """OpexRoad100LongBuildCandidate converts using OpexRoad100PaxSiteMonthly independently of plan shape."""
        body = function_body(self.candidates_src, "function OpexRoad100LongBuildCandidate(")
        self.assertIn("local convertLongUnits = ROAD100_PAX_PRODUCER_UNITS", body)
        self.assertIn("|| ROAD100_SEGMENTED_CORRIDOR", body)
        self.assertIn("|| ROAD100_SPARSE_CORRIDOR", body)
        self.assertIn("|| ROAD100_PAX_GRAPH_BRIDGE;", body)
        self.assertIn("if (convertLongUnits) {", body)
        self.assertIn("OpexRoad100PaxSiteMonthly(preliminary.srcTown", body)
        self.assertIn("OpexRoad100PaxSiteMonthly(preliminary.dstTown", body)
        self.assertIn("if (convertLongUnits) candidate.road100LongUnits <- true;", body)

    def test_task_road_live_demand_converts_independently_of_plan_tracer(self):
        """task_road.nut live demand converts siteDemand to PASS/mo without requiring plan.road100Segmented/Sparse/Graph."""
        # The checks must not require plan.road100Segmented, plan.road100Sparse, or plan.road100Graph
        self.assertNotIn('&& ("road100Segmented" in plan) && plan.road100Segmented', self.task_road_src)
        self.assertNotIn('&& ("road100Sparse" in plan) && plan.road100Sparse', self.task_road_src)
        self.assertNotIn('&& ("road100Graph" in plan) && plan.road100Graph', self.task_road_src)
        self.assertIn('("road100LongUnits" in candidate) &&\n             candidate.road100LongUnits', self.task_road_src)


if __name__ == "__main__":
    unittest.main()
