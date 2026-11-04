"""Contrats RAIL-KEEP (rail_expand_keep, défaut 0) — 04/11/2026.

Une fois V284 actif, la garde historique de _expandRailLines saute toutes les
lignes fret (doublement Cas 1/2 coupé). Sous RAIL-KEEP, seule la ligne de la
transaction V284 en cours est exclue. Tests de source uniquement.
"""

import hashlib
import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from rail_keep_off import INSERTIONS, REPLACED, off_source  # noqa: E402
from rail_fill_off import off_source as rail_fill_off  # noqa: E402
from rail_loop_off import off_source as rail_loop_off  # noqa: E402
from revue_rail_t3_off import off_source as revue_rail_t3_off  # noqa: E402
from test_rail_loop_20261104 import (  # noqa: E402
    PRE_INTERVENTION_SHA, call_args, function_body, global_signatures, read, strip_squirrel)

HISTORIC_GUARD = ('        if (V284_RAIL_GROWTH > 0 && this._v284State != null'
                  ' && (("kind" in line) && line.kind == "freight")) continue;\n')


class RailKeepContracts(unittest.TestCase):
    def test_setting_default_zero_boolean_single_read(self):
        info = read("info.nut")
        block = info[info.index('name = "rail_expand_keep"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0", block)
        self.assertIn("AICONFIG_BOOLEAN", block)
        self.assertEqual(read("globals_pre.nut").count("RAIL_EXPAND_KEEP <- false;"), 1)
        self.assertEqual(read("settings.nut").count('GetSetting("rail_expand_keep")'), 1)
        self.assertEqual(read("main.nut").count('require("rail_keep.nut");'), 1)

    def test_historic_guard_kept_byte_identical_as_else_branch(self):
        expand = function_body(read("task_rail.nut"), "OpexAI::_expandRailLines")
        on_form = REPLACED["task_rail.nut"][0][0]
        self.assertIn(on_form, expand)
        self.assertTrue(on_form.endswith("} else " + HISTORIC_GUARD.lstrip()))
        self.assertEqual(REPLACED["task_rail.nut"][0][1], HISTORIC_GUARD)

    def test_only_the_line_of_the_pending_v284_transaction_is_skipped(self):
        skip = function_body(strip_squirrel(read("rail_keep.nut")), "OpexRailExpandKeepSkip")
        self.assertIn("OpexV284Busy(owner)", skip)
        self.assertIn("owner._v284State.pending.lineId == line.lineId", skip)
        self.assertNotIn("_railSearch", skip)

    def test_v284_still_refuses_to_pick_during_an_upgrade_search(self):
        select = function_body(read("task_v284.nut"), "OpexV284Select")
        self.assertIn('if (owner._railSearch != null && owner._railSearch.kind == "upgrade") return false;', select)

    def test_off_projection_restores_pre_intervention_bytes(self):
        for name, digest in PRE_INTERVENTION_SHA.items():
            with self.subTest(name=name):
                projected = rail_loop_off(name, rail_fill_off(name, off_source(name, revue_rail_t3_off(name, read(name)))))
                self.assertEqual(hashlib.sha256(projected.encode("utf8")).hexdigest(), digest)
                once = off_source(name, revue_rail_t3_off(name, read(name)))
                self.assertEqual(off_source(name, once), once)

    def test_partial_hunk_fails_closed(self):
        damaged = read("task_rail.nut").replace("OpexRailExpandKeepSkip(this, line)", "OpexRailExpandKeepSkip(this, null)")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", damaged)
        with self.assertRaises(AssertionError):
            off_source("main.nut", read("main.nut") + INSERTIONS["main.nut"][0])

    def test_module_static_safety_and_arity(self):
        code = strip_squirrel(read("rail_keep.nut"))
        for bad in ("getroottable", ".find(", "Sleep(", ".Valuate("):
            self.assertNotIn(bad, code)
        self.assertIsNone(re.search(r"function\s*\(", code))
        sigs = global_signatures()
        expand = strip_squirrel(function_body(read("task_rail.nut"), "OpexAI::_expandRailLines"))
        for text in (code, expand):
            for m in re.finditer(r"\b(OpexRailExpandKeep\w*|OpexV284Busy)\s*\(", text):
                if re.search(r"function\s+$", text[max(0, m.start() - 12):m.start()]):
                    continue
                n = len(call_args(text, m.end() - 1))
                self.assertTrue(any(r <= n <= t for r, t in sigs[m.group(1)]), m.group(1))


if __name__ == "__main__":
    unittest.main()
