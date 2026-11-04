"""Revue rail T4 (pathfinder et recherche segmentée) — 04/11/2026.

Mesure seule, sans effet au défaut : sous decision_log, la ligne V214_PATH
compte les coudes à 90° (trois pas unitaires en U, refusés par l'A* via le
grand-parent du nœud) et le nombre de segments. La jonction de deux segments
repart de [front, previous] sans grand-parent : c'est là que le contrôle saute.
Tests de source uniquement : le Squirrel ne se compile pas ici.
"""

import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from revue_rail_t4_off import MARKERS, REPLACED, off_source  # noqa: E402
from test_rail_loop_20261104 import function_body, read, strip_squirrel  # noqa: E402

WIDTH = 256


def manh(a, b):
    return abs(a % WIDTH - b % WIDTH) + abs(a // WIDTH - b // WIDTH)


def ninety(tiles):
    """Portage exact du compteur Squirrel de _continueRailSearch."""
    count = 0
    for k in range(len(tiles) - 3):
        if (manh(tiles[k], tiles[k + 3]) == 1 and manh(tiles[k], tiles[k + 1]) == 1
                and manh(tiles[k + 1], tiles[k + 2]) == 1 and manh(tiles[k + 2], tiles[k + 3]) == 1):
            count += 1
    return count


def walk(start, moves):
    step = {"E": 1, "W": -1, "S": WIDTH, "N": -WIDTH}
    tiles = [start]
    for m in moves:
        tiles.append(tiles[-1] + step[m])
    return tiles


class NinetyCounterSemantics(unittest.TestCase):
    def test_u_turn_pattern_is_counted(self):
        # E puis N puis W : le voisin interdit par "Disallow 90 degree turns".
        self.assertEqual(ninety(walk(1000, "EENWW")), 1)

    def test_legal_shapes_are_not_counted(self):
        self.assertEqual(ninety(walk(1000, "EEEEEE")), 0)          # droite
        self.assertEqual(ninety(walk(1000, "ENENEN")), 0)          # diagonale en escalier
        self.assertEqual(ninety(walk(1000, "EEENNN")), 0)          # coude V214 « tight », légal
        self.assertEqual(ninety(walk(1000, "EENEENN")), 0)

    def test_library_rule_matches_the_counter(self):
        # blocked = gp - par ; next = cur + blocked est refusé. Cela donne t3 - t0 = s1, unitaire.
        lib = (SWEEPS.parent / "ai" / "OpexAI" / "pathfinder_v90" / "v129.nut").read_text(encoding="utf8")
        self.assertIn("local blocked = (gp != null) ? (gp._tile - par_tile) : 0;", lib)
        self.assertIn("if (gp != null && offset == blocked) continue;", lib)
        for gp, par, cur in ((0, 1, 1 + WIDTH), (0, WIDTH, WIDTH + 1)):
            nxt = cur + (gp - par)
            self.assertEqual(ninety([gp, par, cur, nxt]), 1)


class SegmentJunctionHasNoGrandParent(unittest.TestCase):
    """Documente le constat T4-01 (non corrigé : opt-in et qualification requis)."""

    def test_segment_sources_have_two_tiles(self):
        body = function_body(read("builder_rail.nut"), "OpexAdvanceSegmentedSearch")
        self.assertIn("state.activeSources = [[front, previous]];", body)
        self.assertIn("state.activeSources = [[nonLoopChoices[0].to, front]];", body)
        self.assertNotIn("[[front, previous, ", body)

    def test_library_uses_a_third_source_tile_only_as_v233_approach(self):
        lib = (SWEEPS.parent / "ai" / "OpexAI" / "pathfinder_v90" / "v129.nut").read_text(encoding="utf8")
        self.assertIn("if (V233_LONG_GOOD > 0 && node.len() >= 3 && node[2] != null) {", lib)
        self.assertIn("V233_LONG_GOOD <- 1;", read("globals_pre.nut"))


class V214PathInstrumentation(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read("task_rail.nut"), "OpexAI::_continueRailSearch")

    def test_counter_is_inside_decision_log_block(self):
        log = self.body.index("if (DECISION_LOG) {\n\n    OpexDecide(\"RAIL_SEARCH\", \"type=resumable outcome=\"")
        counter = self.body.index("local ninety = 0;")
        self.assertLess(log, counter)
        block = self.body[log:]
        depth, end = 0, None
        for i, ch in enumerate(strip_squirrel(block)):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        self.assertGreater(end, counter - log)

    def test_fields_appended_to_v214_path(self):
        self.assertIn('+ " tight_cost=" + V214_RAIL_TIGHT_TURN_COST + " ninety=" + ninety', self.body)
        self.assertIn('+ " segments=" + (("segments" in slice) ? slice.segments : 1));', self.body)

    def test_squirrel_counter_matches_python_port(self):
        loop = re.search(r"for \(local k = 0; k \+ 3 < v214Tiles\.len\(\); k\+\+\) \{(.*?)ninety\+\+;",
                         self.body, re.S).group(1)
        pairs = re.findall(r"DistanceManhattan\(v214Tiles\[k( \+ \d)?\], v214Tiles\[k \+ (\d)\]\) == 1", loop)
        self.assertEqual(sorted((a.strip(" +") or "0", b) for a, b in pairs),
                         [("0", "1"), ("0", "3"), ("1", "2"), ("2", "3")])

    def test_no_reserved_word_or_closure(self):
        hunk = strip_squirrel(REPLACED["task_rail.nut"][0][0])
        self.assertIsNone(re.search(r"\b(clone|base)\b", hunk))
        self.assertIsNone(re.search(r"function\s*\(", hunk))


class RevueT4OffProjection(unittest.TestCase):
    def test_projection_restores_historic_log_and_is_idempotent(self):
        source = read("task_rail.nut")
        projected = off_source("task_rail.nut", source)
        new, old = REPLACED["task_rail.nut"][0]
        self.assertIn(old, projected)
        for marker in MARKERS:
            self.assertNotIn(marker, projected)
        self.assertEqual(off_source("task_rail.nut", projected), projected)

    def test_other_modules_unchanged(self):
        for name in ("builder_rail.nut", "orchestrator.nut", "rail_loop.nut", "globals_pre.nut"):
            with self.subTest(name=name):
                self.assertEqual(off_source(name, read(name)), read(name))

    def test_partial_or_duplicated_hunk_fails_closed(self):
        source = read("task_rail.nut")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source.replace("ninety++;", "ninety += 1;"))
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", source + REPLACED["task_rail.nut"][0][0])

    def test_chain_head_strips_t4_first(self):
        chain = (SWEEPS / "invest_stall_diagnostic_off.py").read_text(encoding="utf8")
        self.assertLess(chain.index("revue_rail_t4_off"), chain.index("rail_keep_off"))


if __name__ == "__main__":
    unittest.main()
