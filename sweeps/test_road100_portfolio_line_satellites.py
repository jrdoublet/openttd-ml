"""Targeted unit tests for Constat 8:
Transfer of PORTFOLIO satellite tiles and StationID to line table and recalculation
of nStopsA/B when a satellite disappears (in task_road.nut and persist.nut).
"""
import unittest
from pathlib import Path

from sweeps.road100_off_projection import off_source

ROOT = Path(__file__).resolve().parents[1]
TASK_ROAD = ROOT / "ai" / "OpexAI" / "task_road.nut"
PERSIST = ROOT / "ai" / "OpexAI" / "persist.nut"
BUILDER_ROAD = ROOT / "ai" / "OpexAI" / "builder_road.nut"


class TestRoad100PortfolioLineSatellites(unittest.TestCase):
    def setUp(self):
        self.task_road_src = TASK_ROAD.read_text(encoding="utf-8")
        self.persist_src = PERSIST.read_text(encoding="utf-8")
        self.builder_road_src = BUILDER_ROAD.read_text(encoding="utf-8")

    def test_task_road_transfers_portfolio_to_line_table(self):
        """Line creation must copy stopsA, stopsB, stationA, and stationB from result.road100PaxPortfolio."""
        self.assertIn('"road100PaxPortfolio" in result', self.task_road_src)
        self.assertIn('rawset("road100PaxPortfolio"', self.task_road_src)
        self.assertIn("stopsA = satA", self.task_road_src)
        self.assertIn("stopsB = satB", self.task_road_src)
        self.assertIn("stationA = sidA", self.task_road_src)
        self.assertIn("stationB = sidB", self.task_road_src)

    def test_task_road_refleet_recalculates_nstops(self):
        """_refleetRoadLines must inspect line.road100PaxPortfolio and recalculate nStopsA/B on lost satellites."""
        self.assertIn('"road100PaxPortfolio" in line', self.task_road_src)
        self.assertIn("line.nStopsA = newCounts[0]", self.task_road_src)
        self.assertIn("line.nStopsB = newCounts[1]", self.task_road_src)
        self.assertIn('reason=LOST_SATELLITE', self.task_road_src)

    def test_persist_reconciles_portfolio_on_load(self):
        """persist.nut Load() must validate line.road100PaxPortfolio and recalculate nStopsA/B."""
        self.assertIn('"road100PaxPortfolio" in line', self.persist_src)
        self.assertIn("line.nStopsA = 1 + remaining.len()", self.persist_src)
        self.assertIn("line.nStopsB = 1 + remaining.len()", self.persist_src)

    def test_no_forbidden_squirrel_patterns(self):
        """Ensure no reserved keywords used as identifiers and all locals explicitly declared."""
        for name, src in [("task_road.nut", self.task_road_src), ("persist.nut", self.persist_src)]:
            # Check around the added sections for reserved words
            self.assertNotIn("clone ", src[src.find("road100PaxPortfolio"):src.find("road100PaxPortfolio") + 500])

    def test_optin_projections_clean_and_idempotent(self):
        """Exact opt-in projection must remove all road100 features cleanly."""
        proj_task = off_source("task_road.nut", self.task_road_src)
        self.assertNotIn("road100PaxPortfolio", proj_task)
        self.assertEqual(off_source("task_road.nut", proj_task), proj_task)


if __name__ == "__main__":
    unittest.main()
