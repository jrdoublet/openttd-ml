"""Revue rail T8 (rames : moteur, wagons, longueur, clonage) — 04/11/2026.

Correctif F1 dans la revalidation au dépôt d'INVEST-STALL (task_v284.nut,
invest_stall défaut 0) : une locomotive sans cargo rend
AIEngine.GetCapacity == -1, pas 0. La garde historique « == 0 » annulait donc
chaque complément de flotte (10/10 mesurés en moteur, marge positive).
"""

import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from revue_rail_t8_off import MARKERS, REPLACED, off_source  # noqa: E402
from test_rail_loop_20261104 import function_body, read, strip_squirrel  # noqa: E402

AI = SWEEPS.parent / "ai" / "OpexAI"


class InvestStallLocoCapacityGuard(unittest.TestCase):
    def test_recheck_accepts_minus_one_capacity(self):
        v284 = read("task_v284.nut")
        self.assertIn("local homogeneous = AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle)) <= 0;", v284)
        self.assertNotIn("GetEngineType(oldVehicle)) == 0", v284)

    def test_every_loco_capacity_guard_now_uses_the_same_predicate(self):
        offenders = []
        for path in sorted(AI.glob("*.nut")):
            code = strip_squirrel(path.read_text(encoding="utf8"))
            for m in re.finditer(r"AIEngine\.GetCapacity\(AIVehicle\.GetEngineType\(\w+(?:\.\w+)?\)\)\s*(==|!=)\s*0", code):
                offenders.append((path.name, m.group(0)))
        self.assertEqual(offenders, [])

    def test_wagon_identity_check_and_invest_stall_scope_unchanged(self):
        v284 = read("task_v284.nut")
        i = v284.index("local homogeneous = AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle))")
        block = v284[i:i + 1200]
        self.assertIn("if (AIVehicle.GetWagonEngineType(oldVehicle, w) != pending.wagon) homogeneous = false;", block)
        self.assertIn('if (("investStall" in pending) && pending.investStall) {', v284[i - 800:i])
        self.assertIn("INVEST_STALL <- false;", read("globals_pre.nut"))

    def test_selection_side_already_used_greater_than_zero(self):
        fleet = read("invest_stall_fleet.nut")
        self.assertIn("AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) > 0", fleet)


class T8FindingsDocumented(unittest.TestCase):
    def test_t8_02_v3_traction_selector_minimises_cost_at_35_kmh(self):
        multi = function_body(read("rail_long_v3_multi.nut"), "OpexRailLongV3MultiChoose")
        self.assertIn("if (gradeSpeed < 35) continue;", multi)
        self.assertIn("local cost = profile.price + 5 * profile.runningCost;", multi)
        self.assertIn("if (best == null || cost < best.cost", multi)

    def test_t8_01_catalogue_loco_choice_is_flat_track_only(self):
        choices = function_body(read("catalog.nut"), "OpexM3RailLocoChoices")
        self.assertNotIn("Slope", choices)
        self.assertIn("local totalWeight = loco.weight + wagons * wagon.fullWeight;", choices)

    def test_autorenew_enabled(self):
        main = read("main.nut")
        self.assertIn("AICompany.SetAutoRenewStatus(true);", main)
        self.assertIn("AICompany.SetAutoRenewMonths(-6);", main)


class RevueT8OffProjection(unittest.TestCase):
    def test_projection_restores_historic_line_and_is_idempotent(self):
        source = read("task_v284.nut")
        projected = off_source("task_v284.nut", source)
        self.assertIn(REPLACED["task_v284.nut"][0][1], projected)
        for marker in MARKERS:
            self.assertNotIn(marker, projected)
        self.assertEqual(off_source("task_v284.nut", projected), projected)

    def test_other_modules_unchanged(self):
        for name in ("task_rail.nut", "invest_stall_fleet.nut", "builder_rail.nut"):
            with self.subTest(name=name):
                self.assertEqual(off_source(name, read(name)), read(name))

    def test_partial_or_duplicated_hunk_fails_closed(self):
        source = read("task_v284.nut")
        with self.assertRaises(AssertionError):
            off_source("task_v284.nut", source.replace("GetEngineType(oldVehicle)) <= 0;",
                                                       "GetEngineType(oldVehicle)) < 1;"))
        with self.assertRaises(AssertionError):
            off_source("task_v284.nut", source + REPLACED["task_v284.nut"][0][0])

    def test_chain_head_strips_t8_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("revue_rail_t8_off"), chain.index("rail_keep_off"))


if __name__ == "__main__":
    unittest.main()
