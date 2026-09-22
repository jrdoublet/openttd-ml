import unittest
from datetime import date
from pathlib import Path

from sweeps.diag_1v1_shared_monthly import summarize_air_slot_intercept

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


class C78SlotInterceptProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.events = read("ai/OpexAI/event_handlers.nut")
        cls.probes = read("ai/OpexAI/probes.nut")
        cls.projects = read("ai/OpexAI/task_projects.nut")
        cls.air_task = read("ai/OpexAI/task_air.nut")
        cls.main = read("ai/OpexAI/main.nut")
        cls.diag = read("sweeps/diag_1v1_shared_monthly.py")

    def test_probe_is_portfolio_gated_and_default_off(self):
        self.assertIn("C78_SLOT_INTERCEPT_PROBE <- false;", self.globals)
        self.assertIn("C78_SLOT_INTERCEPT_PROBE = probePort;", self.settings)
        self.assertNotIn("C78_SLOT_INTERCEPT_PROBE = probePort && probeEvents", self.settings)

    def test_probe_does_not_try_to_inspect_foreign_station_ids(self):
        handler = body(self.events, "function OpexAI::_onStationFirstVehicle(")
        self.assertNotIn("C78_SLOT_INTERCEPT_PROBE", handler)
        self.assertNotIn("_c78SlotObserveStation", self.probes)
        self.assertNotIn("_c78ForeignAirStations", self.main)
        self.assertNotIn("_c78ForeignAirTowns", self.main)
        self.assertNotIn("_c78SlotPending", self.main)

    def test_projects_pass_logs_air_candidate_economics_and_physical_towns(self):
        snapshot = body(self.probes, "function OpexAI::_c78SlotOnProjectsPass(")
        for token in (
            'project.mode != "air"',
            "OpexC78AirPhysicalTown(plan.siteA)",
            "OpexC78AirPhysicalTown(plan.siteB)",
            "OpexProjectFinanceCapital(project)",
            "OpexC78FundedRank(this._projects, project)",
            "project.budgetCapital",
            "project.profitAnnual",
            "project.roi",
            'capital=',
            'finance=',
            'phase=project_candidate',
            'phase=projects_pass',
            "local cycle = this._taskCycle",
            "local tick = AIController.GetTick()",
            '" cycle=" + cycle + " tick=" + tick',
        ):
            self.assertIn(token, snapshot)

        funded_rank = body(self.probes, "function OpexC78FundedRank(")
        self.assertIn("OpexProjectAttemptKey(project)", funded_rank)
        self.assertIn("OpexProjectAttemptKey(fundedProject)", funded_rank)

    def test_projects_task_emits_pass_and_successful_build_timestamps(self):
        attempt = body(self.projects, "function OpexAI::_tryBuildProjects(")
        self.assertIn("this._c78SlotOnProjectsPass();", attempt)
        self.assertIn('OpexC78SlotLog("phase=build pass=" + C78_SLOT_PASS_COUNTER', attempt)
        self.assertIn('" cycle=" + this._taskCycle + " tick=" + AIController.GetTick()', attempt)
        self.assertIn('" built_count=" + builtCount', attempt)
        self.assertIn('phase=air_attempt', attempt)
        self.assertIn('phase=air_outcome', attempt)
        self.assertIn('phase=pass_stop', attempt)
        self.assertIn('phase=projects_exit', attempt)
        self.assertIn('reason=rail_search blocker_rank=', attempt)
        self.assertIn('c78ExitStop = (!C75_MULTI_BUILD) ? "single" : "list_end";', attempt)

        air_attempt = body(self.air_task, "function OpexAI::_tryBuildAirProject(")
        self.assertIn("MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE", air_attempt)
        self.assertIn("C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE", air_attempt)

    def test_double_airport_requires_concurrent_stations(self):
        def od(y, m, d):
            return date(y, m, d).toordinal() + 365

        rows = [
            {
                "seed": 42, "arm": "AAAHogEx", "date": "1970-02-28",
                "stations_by_town": {
                    "7": {"count": 1, "stations": [
                        {"id": 10, "build_date": od(1970, 2, 1), "facilities": ["airport"]},
                    ]}
                },
            },
            # Le premier aéroport a disparu : le suivant ne doit pas être compté comme "deuxième".
            {
                "seed": 42, "arm": "AAAHogEx", "date": "1970-03-31",
                "stations_by_town": {
                    "7": {"count": 1, "stations": [
                        {"id": 11, "build_date": od(1970, 3, 15), "facilities": ["airport"]},
                    ]}
                },
            },
            # Première coexistence réelle : stations 11 et 12.
            {
                "seed": 42, "arm": "AAAHogEx", "date": "1970-04-30",
                "stations_by_town": {
                    "7": {"count": 2, "stations": [
                        {"id": 11, "build_date": od(1970, 3, 15), "facilities": ["airport"]},
                        {"id": 12, "build_date": od(1970, 4, 10), "facilities": ["airport"]},
                    ]}
                },
            },
        ]
        analysis = summarize_air_slot_intercept(rows)
        self.assertEqual(analysis["summary"]["second_airport_cases"], 1)
        opp = analysis["opportunities"][0]
        self.assertEqual(opp["aaa_first_ever_station"], 10)
        self.assertEqual(opp["aaa_first_station"], 11)
        self.assertEqual(opp["aaa_second_station"], 12)
        self.assertEqual(opp["window_days"], od(1970, 4, 10) - od(1970, 3, 15))

    def test_shared_diagnostic_uses_portfolio_probe_and_station_build_dates(self):
        build_arms = body(self.diag, "def build_arms(")
        self.assertIn('if funnel or air_slot_intercept:', build_arms)
        self.assertNotIn('opex_params.append(("probe_events", 1))', build_arms)
        self.assertIn("town_station_detail=args.town_station_detail or args.air_slot_intercept", self.diag)
        self.assertIn("parse_c78_slot_events", self.diag)
        self.assertIn("summarize_air_slot_intercept", self.diag)
        self.assertIn('"air_slot_intercept_analysis": slot_intercept', self.diag)

    def test_slot_summary_counts_candidate_groups_not_equipment_variants(self):
        def od(y, m, d):
            return date(y, m, d).toordinal() + 365

        rows = [
            {
                "seed": 42, "arm": "AAAHogEx", "date": "1971-08-31",
                "stations_by_town": {
                    "34": {"count": 2, "stations": [
                        {"id": 91, "build_date": od(1971, 3, 10), "facilities": ["airport"]},
                        {"id": 92, "build_date": od(1971, 8, 10), "facilities": ["airport"]},
                    ]}
                },
            },
            {
                "seed": 42, "arm": "OpexAI", "date": "1971-03-31",
                "stations_by_town": {},
                "c78_slot_events": [
                    {"date": "1971-03-12", "phase": "projects_pass", "pass": 9, "cycle": 9, "tick": 300},
                    {"date": "1971-03-12", "phase": "project_candidate", "pass": 9, "cycle": 9, "tick": 300,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 3,
                     "affordable": 1, "profit": 42000, "finance": 120000},
                    # Meme paire, autre variante d'equipement : un seul candidat de portefeuille.
                    {"date": "1971-03-12", "phase": "project_candidate", "pass": 9, "cycle": 9, "tick": 300,
                     "townA": 34, "townB": 52, "src": 200, "dst": 100, "rank": 3,
                     "affordable": 1, "profit": 41000, "finance": 110000},
                    {"date": "1971-03-12", "phase": "air_attempt", "pass": 9, "cycle": 9, "tick": 301,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 3},
                    {"date": "1971-03-12", "phase": "air_outcome", "pass": 9, "cycle": 9, "tick": 302,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 3,
                     "outcome": "rejected", "reason": "siteA_unbuildable", "error": 0},
                ],
            },
        ]

        opp = summarize_air_slot_intercept(rows)["opportunities"][0]
        self.assertEqual(opp["candidate_variant_count"], 2)
        self.assertEqual(opp["candidate_count"], 1)
        self.assertEqual(opp["affordable_candidate_count"], 1)
        self.assertEqual(opp["funded_candidate_count"], 1)
        self.assertEqual(opp["best_funded_rank"], 3)
        self.assertEqual(opp["funded_candidate_attempted_count"], 1)
        self.assertEqual(opp["funded_candidate_built_count"], 0)
        self.assertEqual(opp["funded_air_outcomes"][0]["reason"], "siteA_unbuildable")

    def test_slot_summary_keeps_same_pass_across_date_boundary(self):
        def od(y, m, d):
            return date(y, m, d).toordinal() + 365

        rows = [
            {
                "seed": 42, "arm": "AAAHogEx", "date": "1971-08-31",
                "stations_by_town": {
                    "34": {"count": 2, "stations": [
                        {"id": 91, "build_date": od(1971, 3, 10), "facilities": ["airport"]},
                        {"id": 92, "build_date": od(1971, 8, 10), "facilities": ["airport"]},
                    ]}
                },
            },
            {
                "seed": 42, "arm": "OpexAI", "date": "1971-03-31",
                "stations_by_town": {},
                "c78_slot_events": [
                    {"date": "1971-03-12", "phase": "projects_pass", "pass": 9, "cycle": 9, "tick": 300},
                    {"date": "1971-03-12", "phase": "project_candidate", "pass": 9, "cycle": 9, "tick": 300,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 0,
                     "affordable": 1, "profit": 42000, "finance": 120000},
                    {"date": "1971-03-13", "phase": "air_attempt", "pass": 9, "cycle": 9, "tick": 301,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 0},
                    {"date": "1971-03-14", "phase": "air_outcome", "pass": 9, "cycle": 9, "tick": 302,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 0,
                     "outcome": "rejected", "reason": "siteA_unbuildable", "error": 0},
                    {"date": "1971-03-14", "phase": "air_outcome", "pass": 10, "cycle": 10, "tick": 303,
                     "townA": 34, "townB": 52, "src": 100, "dst": 200, "rank": 0,
                     "outcome": "built", "reason": "built", "error": 0},
                    {"date": "1971-03-14", "phase": "projects_exit", "pass": 9, "cycle": 9, "tick": 304,
                     "built_count": 0, "stop": "none"},
                ],
            },
        ]

        opp = summarize_air_slot_intercept(rows)["opportunities"][0]
        self.assertEqual(opp["funded_candidate_attempted_count"], 1)
        self.assertEqual(opp["funded_candidate_built_count"], 0)
        self.assertEqual(len(opp["funded_air_outcomes"]), 1)
        self.assertEqual(opp["funded_air_outcomes"][0]["reason"], "siteA_unbuildable")
        self.assertEqual(opp["projects_exit"]["stop"], "none")


if __name__ == "__main__":
    unittest.main()
