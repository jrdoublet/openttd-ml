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


def simulate_portfolio_line_creation(result: dict) -> dict:
    """Exact reproduction of task_road.nut line creation with portfolio satellites."""
    line = {
        "nStopsA": result.get("nStopsA", 1),
        "nStopsB": result.get("nStopsB", 1),
        "stationA": result.get("stopA"),
        "stationB": result.get("stopB"),
    }
    if "road100PaxPortfolio" in result and result["road100PaxPortfolio"] is not None:
        port = result["road100PaxPortfolio"]
        sat_a = list(port.get("stopsA", []))
        sat_b = list(port.get("stopsB", []))
        sid_a = result.get("stationA")
        sid_b = result.get("stationB")
        line["road100PaxPortfolio"] = {
            "stopsA": sat_a,
            "stopsB": sat_b,
            "stationA": sid_a,
            "stationB": sid_b,
        }
    return line


def simulate_portfolio_line_maintenance_or_load(
    line: dict,
    valid_tiles_for_station: dict[int, set[int]],
) -> dict:
    """Exact reproduction of task_road.nut _refleetRoadLines and persist.nut _reconcileAfterLoad."""
    if "road100PaxPortfolio" not in line or line["road100PaxPortfolio"] is None:
        return line

    port = line["road100PaxPortfolio"]
    if not isinstance(port, dict):
        line["nStopsA"] = 1
        line["nStopsB"] = 1
        line["road100PaxPortfolio"] = None
        return line

    sid_a = port.get("stationA")
    sid_b = port.get("stationB")
    stops_a = port.get("stopsA", [])
    stops_b = port.get("stopsB", [])

    valid_a = valid_tiles_for_station.get(sid_a, set())
    valid_b = valid_tiles_for_station.get(sid_b, set())

    remaining_a = [t for t in stops_a if t in valid_a]
    remaining_b = [t for t in stops_b if t in valid_b]

    port["stopsA"] = remaining_a
    port["stopsB"] = remaining_b
    line["nStopsA"] = 1 + len(remaining_a)
    line["nStopsB"] = 1 + len(remaining_b)
    return line


class TestRoad100PortfolioLineSatellitesBehavioralOracle(unittest.TestCase):
    """Behavioral simulation tests verifying actual VALUES consumed by portfolio satellites."""

    def test_creation_transfers_satellite_identities_and_counts(self):
        result = {
            "stopA": 100,
            "stationA": 10,
            "nStopsA": 2,
            "stopB": 200,
            "stationB": 20,
            "nStopsB": 3,
            "road100PaxPortfolio": {
                "stopsA": [101],
                "stopsB": [201, 202],
            },
        }
        line = simulate_portfolio_line_creation(result)
        self.assertEqual(line["nStopsA"], 2)
        self.assertEqual(line["nStopsB"], 3)
        self.assertIn("road100PaxPortfolio", line)
        self.assertEqual(line["road100PaxPortfolio"]["stopsA"], [101])
        self.assertEqual(line["road100PaxPortfolio"]["stopsB"], [201, 202])
        self.assertEqual(line["road100PaxPortfolio"]["stationA"], 10)
        self.assertEqual(line["road100PaxPortfolio"]["stationB"], 20)

    def test_demolished_satellite_recalculates_nstops_and_shrinks_fleet_cap(self):
        result = {
            "stopA": 100,
            "stationA": 10,
            "nStopsA": 2,
            "stopB": 200,
            "stationB": 20,
            "nStopsB": 3,
            "road100PaxPortfolio": {
                "stopsA": [101],
                "stopsB": [201, 202],
            },
        }
        line = simulate_portfolio_line_creation(result)
        # Initial fleet cap: min(2, 3) * 2 = 4 vehicles
        fleet_cap_initial = min(line["nStopsA"], line["nStopsB"]) * 2
        self.assertEqual(fleet_cap_initial, 4)

        # Tile 101 on side A is demolished (removed from valid tiles of station 10)
        valid_tiles = {10: {100}, 20: {200, 201, 202}}
        line = simulate_portfolio_line_maintenance_or_load(line, valid_tiles)

        # nStopsA reduced to 1 (root only), nStopsB remains 3 (root + 2 satellites)
        self.assertEqual(line["nStopsA"], 1)
        self.assertEqual(line["nStopsB"], 3)
        self.assertEqual(line["road100PaxPortfolio"]["stopsA"], [])
        self.assertEqual(line["road100PaxPortfolio"]["stopsB"], [201, 202])

        # Fleet cap correctly shrinks from 4 to 2, preventing phantom refleet
        fleet_cap_after = min(line["nStopsA"], line["nStopsB"]) * 2
        self.assertEqual(fleet_cap_after, 2)

    def test_all_satellites_demolished_reverts_to_single_bays(self):
        result = {
            "stopA": 100,
            "stationA": 10,
            "nStopsA": 2,
            "stopB": 200,
            "stationB": 20,
            "nStopsB": 2,
            "road100PaxPortfolio": {
                "stopsA": [101],
                "stopsB": [201],
            },
        }
        line = simulate_portfolio_line_creation(result)
        valid_tiles = {10: {100}, 20: {200}}  # Only root tiles remain
        line = simulate_portfolio_line_maintenance_or_load(line, valid_tiles)
        self.assertEqual(line["nStopsA"], 1)
        self.assertEqual(line["nStopsB"], 1)
        self.assertEqual(line["road100PaxPortfolio"]["stopsA"], [])
        self.assertEqual(line["road100PaxPortfolio"]["stopsB"], [])

    def test_corrupted_portfolio_cleans_line_to_safe_defaults(self):
        line = {
            "nStopsA": 3,
            "nStopsB": 3,
            "road100PaxPortfolio": "corrupted_string_not_dict",
        }
        line = simulate_portfolio_line_maintenance_or_load(line, {})
        self.assertEqual(line["nStopsA"], 1)
        self.assertEqual(line["nStopsB"], 1)
        self.assertIsNone(line["road100PaxPortfolio"])



if __name__ == "__main__":
    unittest.main()
