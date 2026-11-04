"""Revue rail T3 (stock, upgrade, réparations) — 04/11/2026.

Deux correctifs sans condition dans _consumeRailUpgrade, avant l'exécution :
- F1 : pas de doublement sans slot train (invariant M4/16.2). Avant, voie 2,
  gares et dépôt étaient posés puis démolis sur TRAINFAIL ;
- F2 : si RAIL-LOOP a pris la ligne (railLoop > 0) pendant l'A* d'upgrade,
  le slot est rendu sans pose ni mémoire d'échec.
Tests de source uniquement : le Squirrel ne se compile pas ici.
"""

import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from revue_rail_t3_off import MARKERS, REPLACED, off_source  # noqa: E402
from test_rail_loop_20261104 import (  # noqa: E402
    call_args, function_body, global_signatures, read, strip_squirrel)


def matching_brace(text, open_index):
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


class UpgradeVehicleSlotGuard(unittest.TestCase):
    def setUp(self):
        self.raw = function_body(read("task_rail.nut"), "OpexAI::_consumeRailUpgrade")
        # Code sans commentaires ni chaînes pour la structure ; brut pour les motifs.
        self.body = strip_squirrel(self.raw)

    def test_slot_is_checked_before_any_upgrade_execution(self):
        guard = self.body.index("OpexRailVehicleSlotAvailable()")
        execute = self.body.index("OpexExecuteUpgradeAfterSearch(")
        self.assertLess(guard, execute)
        self.assertEqual(self.body.count("OpexExecuteUpgradeAfterSearch("), 1)
        self.assertIn('reason = "NOVEHSLOT"', self.raw)

    def test_no_slot_takes_the_existing_failure_path(self):
        # Pas la sortie CASH (sans mémoire) : même mémoire qu'un TRAINFAIL, slot libéré.
        self.assertEqual(re.findall(r'upgrade\.reason == "(\w+)"', self.raw), ["CASH"])
        tail = self.body[self.body.index("if (!upgrade.ok) {"):]
        self.assertIn("this._markPairAbandoned(OpexRailUpgradeRejectKey(state.line.lineId));", tail)
        self.assertIn("this._railSearch = null;", tail)

    def test_fallback_result_covers_fields_read_outside_the_success_branch(self):
        ok_branch = self.body.index("if (upgrade.ok) {")
        end = matching_brace(self.body, self.body.index("{", ok_branch))
        outside = self.body[:ok_branch] + self.body[end + 1:]
        fields = set(re.findall(r"\bupgrade\.(\w+)", outside))
        fallback = re.search(r':\s*\{ ok = false, reason = "NOVEHSLOT"([^}]*)\}', self.raw)
        self.assertIsNotNone(fallback)
        keys = {"ok", "reason"} | set(re.findall(r"(\w+)\s*=", fallback.group(1)))
        self.assertTrue(fields <= keys, fields - keys)

    def test_slot_helper_signature_and_predicate_unchanged(self):
        sigs = global_signatures()
        self.assertIn((0, 0), sigs["OpexRailVehicleSlotAvailable"])
        helper = function_body(read("builder_rail.nut"), "OpexRailVehicleSlotAvailable")
        self.assertIn("return used < cap;", helper)
        m = re.search(r"OpexRailVehicleSlotAvailable\s*\(", self.body)
        self.assertEqual(call_args(self.body, m.end() - 1), [])

    def test_upgrade_builder_itself_is_untouched(self):
        builder = function_body(read("builder_rail.nut"), "OpexExecuteUpgradeAfterSearch")
        self.assertNotIn("OpexRailVehicleSlotAvailable", builder)
        self.assertNotIn("NOVEHSLOT", read("builder_rail.nut"))


class UpgradeYieldsToRailLoop(unittest.TestCase):
    def setUp(self):
        self.raw = function_body(read("task_rail.nut"), "OpexAI::_consumeRailUpgrade")
        self.body = strip_squirrel(self.raw)
        start = self.body.index('if (RAIL_LOOP && ("" in state.line) && state.line.railLoop > 0) {')
        self.block = self.body[start:matching_brace(self.body, self.body.index("{", start)) + 1]
        self.start = start

    def test_guard_runs_before_slot_check_and_execution(self):
        self.assertLess(self.start, self.body.index("OpexRailVehicleSlotAvailable()"))
        self.assertLess(self.start, self.body.index("OpexExecuteUpgradeAfterSearch("))

    def test_guard_releases_slot_without_memory_or_spending(self):
        self.assertIn("this._railSearch = null;", self.block)
        self.assertTrue(self.block.rstrip("}").rstrip().endswith("return;"))
        for forbidden in ("_markPairAbandoned", "OpexExecute", "Build", "Demolish", "rawset"):
            self.assertNotIn(forbidden, self.block)

    def test_same_predicate_as_expand_skip(self):
        expand = function_body(read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn('if (RAIL_LOOP && ("railLoop" in line) && line.railLoop > 0) continue;', expand)
        self.assertIn('if (RAIL_LOOP && ("railLoop" in state.line) && state.line.railLoop > 0) {', self.raw)
        self.assertIn('reason=RLOOP_OWNED ok=0', self.raw)

    def test_loop_admission_excludes_doubled_lines(self):
        # Invariant que F2 protège : une boucle ne coexiste pas avec un doublement.
        eligible = function_body(read("rail_loop.nut"), "OpexRailLoopEligible")
        self.assertIn('(!("doubleTrack" in line) || line.doubleTrack == 0)', eligible)
        begin = read("rail_loop.nut")
        self.assertIn('line.rawset("railLoop", 1);', begin)


class RevueT3OffProjection(unittest.TestCase):
    def test_projection_restores_historic_call_and_is_idempotent(self):
        source = read("task_rail.nut")
        projected = off_source("task_rail.nut", source)
        new, old = REPLACED["task_rail.nut"][0]
        self.assertIn(old, projected)
        self.assertNotIn(new, projected)
        for marker in MARKERS:
            self.assertNotIn(marker, projected)
        self.assertEqual(off_source("task_rail.nut", projected), projected)
        self.assertEqual(len(source) - len(projected), len(new) - len(old))

    def test_other_modules_unchanged(self):
        for name in ("builder_rail.nut", "orchestrator.nut", "lines.nut", "rail_prep_c121.nut"):
            with self.subTest(name=name):
                self.assertEqual(off_source(name, read(name)), read(name))

    def test_partial_or_duplicated_hunk_fails_closed(self):
        source = read("task_rail.nut")
        for old, new in (('reason = "NOVEHSLOT", cost = 0', 'reason = "NOVEHSLOT", cost = 1'),
                         ('reason=RLOOP_OWNED ok=0', 'reason=RLOOP_OWNED ok=1')):
            with self.subTest(old=old):
                with self.assertRaises(AssertionError):
                    off_source("task_rail.nut", source.replace(old, new))
        new = REPLACED["task_rail.nut"][0][0]
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source + new)

    def test_chain_head_strips_t3_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("revue_rail_t3_off"), chain.index("rail_keep_off"))


class M4HarnessLowTrainCap(unittest.TestCase):
    """Le harnais M4 garde max_trains_0 et accepte max_trains_<n> (exposition de F1)."""

    def _cfg_for(self):
        import ast
        source = (SWEEPS / "run_m4_conformity.py").read_text(encoding="utf8")
        tree = ast.parse(source)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "cfg_for")
        namespace = {"bench_v2": type("B", (), {"make_cfg": staticmethod(lambda y, m: "BASE")})}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "cfg_for", "exec"), namespace)
        return namespace["cfg_for"]

    def test_low_cap_and_historic_scenarios(self):
        cfg_for = self._cfg_for()
        self.assertEqual(cfg_for("max_trains_0"), "BASE\n[vehicle]\nmax_trains = 0\n")
        self.assertEqual(cfg_for("max_trains_8"), "BASE\n[vehicle]\nmax_trains = 8\n")
        self.assertEqual(cfg_for("control"), "BASE")
        self.assertIn("forbid_90_deg = true", cfg_for("forbid_90"))
        with self.assertRaises(ValueError):
            cfg_for("max_trains_x")


if __name__ == "__main__":
    unittest.main()
