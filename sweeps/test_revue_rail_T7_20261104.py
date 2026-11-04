"""Revue rail T7 (exécution du plan, mise en service) — 04/11/2026.

Mesure seule, sans effet au défaut : sous decision_log, RAIL_ATTEMPT porte
pred_trains (rames du devis) et built_trains (rames posées). Les contrats
documentent T7-01 : le devis peut compter 2 rames sur une voie unique alors
que le constructeur n'en pose qu'une.
"""

import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from revue_rail_t7_off import MARKERS, REPLACED, off_source  # noqa: E402
from test_rail_loop_20261104 import function_body, read, strip_squirrel  # noqa: E402


class RailAttemptTrainsInstrumentation(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read("task_rail.nut"), "OpexAI::_recordRailAttempt")

    def test_fields_inside_decision_log_attempt_line(self):
        guard = self.body.index("if (DECISION_LOG) {\n    local p2Trace = OpexP2RailTraceKey(candidate);")
        field = self.body.index('" pred_trains=" + (("trains" in candidate) ? candidate.trains : -1)')
        build = self.body.index('OpexDecide("RAIL_BUILD", "line="')
        self.assertLess(guard, field)
        self.assertLess(field, build)
        self.assertIn('" built_trains=" + (("trains" in result) ? result.trains : -1)', self.body)

    def test_existing_parsed_fields_kept_in_order(self):
        a = self.body.index('" pred_astar="')
        b = self.body.index('" pred_trains="')
        c = self.body.index('" pre="')
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_no_reserved_word_or_closure(self):
        hunk = strip_squirrel(REPLACED["task_rail.nut"][0][0])
        self.assertIsNone(re.search(r"\b(clone|base)\b", hunk))
        self.assertIsNone(re.search(r"function\s*\(", hunk))


class T7FindingsDocumented(unittest.TestCase):
    def test_t7_01_quote_allows_two_trains_builder_lays_one_on_single_track(self):
        economy = read("economy.nut")
        self.assertIn("const MAX_RAIL_TRAINS = 2;", economy)
        execute = function_body(read("builder_rail.nut"), "OpexExecuteRailPlan")
        self.assertIn("local want = 1;", execute)
        self.assertIn("want = candidate.trains > 2 ? 2 : candidate.trains;", execute)
        trains = execute.index("local trains = OpexBuildTrains(")
        self.assertIn("planA.station_exit, planB.station_exit, 1, candidate.loco,", execute[trains:trains + 300])
        double = function_body(read("builder_rail.nut"), "OpexTryDoubleTrack")
        self.assertIn("if (!AIStation.IsValidStation(stationIdA) || !AIStation.IsValidStation(stationIdB)) return acc;",
                      double)

    def test_orders_full_load_source_only_for_freight(self):
        build = function_body(read("builder_rail.nut"), "OpexBuildTrains")
        self.assertIn("local flagsA = AIOrder.OF_FULL_LOAD_ANY | nonstopFlag;", build)
        self.assertIn('local flagsB = ((kind == "freight") ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | nonstopFlag;',
                      build)
        # Les rames ne démarrent qu'après les deux ordres : rollback atomique.
        self.assertLess(build.index("AIOrder.AppendOrder(train, exitB, flagsB)"),
                        build.index("AIVehicle.StartStopVehicle(train)"))


class RevueT7OffProjection(unittest.TestCase):
    def test_projection_restores_historic_line_and_is_idempotent(self):
        source = read("task_rail.nut")
        projected = off_source("task_rail.nut", source)
        self.assertIn(REPLACED["task_rail.nut"][0][1], projected)
        for marker in MARKERS:
            self.assertNotIn(marker, projected)
        self.assertEqual(off_source("task_rail.nut", projected), projected)

    def test_other_modules_unchanged(self):
        for name in ("builder_rail.nut", "economy.nut", "rail_loop.nut"):
            with self.subTest(name=name):
                self.assertEqual(off_source(name, read(name)), read(name))

    def test_partial_or_duplicated_hunk_fails_closed(self):
        source = read("task_rail.nut")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source.replace('" built_trains="', '" built="'))
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source + REPLACED["task_rail.nut"][0][0])

    def test_chain_head_strips_t7_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("revue_rail_t7_off"), chain.index("rail_keep_off"))


if __name__ == "__main__":
    unittest.main()
