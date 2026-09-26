import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diag_homog_preselect import extract_events, analyze_diagnostics

FIXTURE_OUTPUT = """
dbg: [script] [1] OPEX 1970-2-15 C50_CHRONO phase=treasury_monthly year=1970 month=2 cash=100000 loan=0
dbg: [script] [1] OPEX 1970-3-12 C50_CHRONO phase=project_built mode=air rank=0 line=0 cost=15000 profit=45000 roi=300.0 cash_after=85000 available=85000
dbg: [script] [1] OPEX 1970-5-20 C50_CHRONO phase=project_built mode=rail rank=1 line=1 cost=32000 profit=24000 roi=75.0 cash_after=53000 available=53000
dbg: [script] [1] OPEX 1970-7-14 C50_CHRONO phase=project_built mode=road rank=2 line=2 cost=6500 profit=9000 roi=138.5 cash_after=46500 available=46500
dbg: [script] [1] OPEX 1970-8-1 C50_CHRONO phase=fleet_built mode=air line=0 added=1 total=2 cash_after=35000
dbg: [script] [1] OPEX 1970-9-10 C50_CHRONO phase=refused_cash mode=rail rank=0 cost=50000 profit=30000 roi=60.0
dbg: [script] [1] OPEX 1970-10-5 C78_BUILD year=1970 rank=2 mode=road townA=10 townB=12 indA=-1 indB=-1 P=9000 C=6500 outcome=built reason=none detail= error=0
dbg: [script] [1] Some unrelated log line without prefix
"""


class TestDiagHomogPreselect(unittest.TestCase):
    def test_extract_events(self):
        events = extract_events(FIXTURE_OUTPUT)
        self.assertEqual(len(events), 6)
        # Check project_built events
        built = [e for e in events if e["type"] == "project_built"]
        self.assertEqual(len(built), 3)
        modes = [b["mode"] for b in built]
        self.assertEqual(modes, ["air", "rail", "road"])
        self.assertEqual(built[1]["cost"], 32000)
        self.assertEqual(built[1]["profit"], 24000)
        self.assertEqual(built[1]["rank"], 1)

        # Check fleet_built event
        fleet = [e for e in events if e["type"] == "fleet_built"]
        self.assertEqual(len(fleet), 1)
        self.assertEqual(fleet[0]["mode"], "air")
        self.assertEqual(fleet[0]["total"], 2)

        # Check c78_build event
        c78 = [e for e in events if e["type"] == "c78_build"]
        self.assertEqual(len(c78), 1)
        self.assertEqual(c78[0]["outcome"], "built")

    def test_analyze_diagnostics(self):
        events = extract_events(FIXTURE_OUTPUT)
        summary_rec = {
            "company_value": 500000,
            "profit_year": 250000,
            "performance_history": 600,
            "n_stations": 15,
            "n_vehicles": 25,
            "primary_vehicles_by_mode": {"air": 10, "rail": 5, "road": 10, "water": 0},
            "stations_by_facility": {"airport": 4, "rail": 4, "bus": 7},
        }
        diag = analyze_diagnostics(events, summary_rec)

        self.assertEqual(diag["lines_built_by_mode"]["air"], 1)
        self.assertEqual(diag["lines_built_by_mode"]["rail"], 1)
        self.assertEqual(diag["lines_built_by_mode"]["road"], 1)
        self.assertEqual(diag["lines_built_by_mode"]["water"], 0)

        self.assertEqual(diag["fleet_additions_by_mode"]["air"], 1)
        self.assertEqual(diag["fleet_additions_by_mode"]["rail"], 0)

        self.assertEqual(len(diag["rail_projects_built"]), 1)
        self.assertEqual(diag["rail_projects_built"][0]["rank_in_portfolio"], 1)
        self.assertEqual(diag["rail_projects_built"][0]["cost"], 32000)

        self.assertEqual(len(diag["road_projects_built"]), 1)
        self.assertEqual(diag["road_projects_built"][0]["rank_in_portfolio"], 2)
        self.assertEqual(diag["road_projects_built"][0]["profit"], 9000)

        self.assertEqual(diag["primary_vehicles_by_mode"]["air"], 10)
        self.assertEqual(diag["company_value"], 500000)
        self.assertEqual(diag["profit_year"], 250000)

        # Ensure limitations are explicitly documented in probe_limitations
        self.assertIn("candidate_fund_score", diag["probe_limitations"])
        self.assertIn("modal_top_k_rank", diag["probe_limitations"])
        self.assertIn("top_k_overlap", diag["probe_limitations"])


if __name__ == "__main__":
    unittest.main()
