"""Contrats REVUE-T2 (revue de l'ordonnanceur rail I, 04/11/2026).

F1 : `_startRailUpgradeSearch` n'écrase jamais un slot `_railSearch` occupé.
     Sans effet au défaut : son unique appelant est après la garde
     `_railSearch != null && (RAIL_SEARCH_PRIO || !OpexV190Active())`.
F2 : `rail_upgrade_cash_memory` (défaut 0) mémorise le vrai devis de la voie 2
     après un refus CASH et le réutilise à l'admission du Cas 2.
"""

import hashlib
import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))
AI = SWEEPS.parent / "ai" / "OpexAI"

from revue_rail_t2_off import INSERTIONS, off_source  # noqa: E402
from rail_keep_off import off_source as rail_keep_off  # noqa: E402
from rail_fill_off import off_source as rail_fill_off  # noqa: E402
from rail_loop_off import off_source as rail_loop_off  # noqa: E402
from test_rail_loop_20261104 import (  # noqa: E402
    PRE_INTERVENTION_SHA, call_args, function_body, global_signatures, read, strip_squirrel)

PRE_SHA = dict(PRE_INTERVENTION_SHA)
PRE_SHA["builder_rail.nut"] = "4fbb28a0fb30afcb0fb39257e5103a9b028b7895332de6b68b652e48460c6d65"


def all_layers_off(name, source):
    return rail_loop_off(name, rail_fill_off(name, rail_keep_off(name, off_source(name, source))))


class RevueT2SlotGuard(unittest.TestCase):
    def test_upgrade_search_never_overwrites_an_active_slot(self):
        body = function_body(read("task_rail.nut"), "OpexAI::_startRailUpgradeSearch")
        guard = body.index("if (this._railSearch != null) return;")
        self.assertLess(guard, body.index("this._railSearch = {"))
        self.assertLess(guard, body.index("OpexCreateRailPathfinder("))

    def test_single_caller_runs_after_the_default_early_return(self):
        callers = []
        for path in AI.glob("*.nut"):
            text = strip_squirrel(path.read_text(encoding="utf8"))
            for m in re.finditer(r"_startRailUpgradeSearch\s*\(", text):
                if not re.search(r"function\s+OpexAI::$", text[max(0, m.start() - 20):m.start()]) \
                        and "function _startRailUpgradeSearch" not in text[max(0, m.start() - 30):m.end()]:
                    callers.append(path.name)
        self.assertEqual(callers, ["task_rail.nut"])
        expand = function_body(read("task_rail.nut"), "OpexAI::_expandRailLines")
        early = expand.index("if (this._railSearch != null && (RAIL_SEARCH_PRIO || !OpexV190Active())) return;")
        self.assertLess(early, expand.index("this._startRailUpgradeSearch(line, prep);"))


class RevueT2CashMemory(unittest.TestCase):
    def test_setting_default_zero_and_single_read(self):
        info = read("info.nut")
        block = info[info.index('name = "rail_upgrade_cash_memory"'):]
        block = block[:block.index("});")]
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0", block)
        self.assertIn("AICONFIG_BOOLEAN", block)
        self.assertEqual(read("globals_pre.nut").count("RAIL_UPGRADE_CASH_MEMORY <- false;"), 1)
        self.assertEqual(read("settings.nut").count('GetSetting("rail_upgrade_cash_memory")'), 1)

    def test_admission_estimate_is_manhattan_but_execution_uses_route_length(self):
        """Le constat (a) lui-même : deux devis différents pour la même voie 2."""
        expand = function_body(read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn("line.distance * this._catalog.costTrackPerTile", expand)
        upgrade = function_body(read("builder_rail.nut"), "OpexExecuteUpgradeAfterSearch")
        self.assertIn("tiles2.len() * catalog.costTrackPerTile", upgrade)

    def test_memory_is_written_on_cash_and_read_at_admission_only_when_enabled(self):
        consume = function_body(read("task_rail.nut"), "OpexAI::_consumeRailUpgrade")
        cash = consume[consume.index('if (upgrade.reason == "CASH") {'):]
        cash = cash[:cash.index("return;")]
        write = cash.index('if (RAIL_UPGRADE_CASH_MEMORY && upgrade.cost > 0) state.line.rawset("upgradeCashNeed", upgrade.cost);')
        self.assertLess(write, cash.index("this._railSearch = null;"))
        expand = function_body(read("task_rail.nut"), "OpexAI::_expandRailLines")
        read_at = expand.index('if (RAIL_UPGRADE_CASH_MEMORY && ("upgradeCashNeed" in line) && line.upgradeCashNeed > need)')
        self.assertLess(expand.index("local need = trackCost + trainCost;"), read_at)
        prep = expand.index("OpexPrepareUpgradeSearch(line, HARD_ITERATION_CAP)")
        self.assertLess(read_at, expand.index("if (money >= need) {", read_at))
        self.assertLess(expand.index("if (money >= need) {", read_at), prep)
        upgrade = function_body(read("builder_rail.nut"), "OpexExecuteUpgradeAfterSearch")
        self.assertIn('result.reason = "CASH";\n    if (RAIL_UPGRADE_CASH_MEMORY) result.cost = totalNeeded;\n    return result;', upgrade)


class RevueT2Projection(unittest.TestCase):
    def test_all_layers_off_restore_pre_intervention_bytes(self):
        for name, digest in PRE_SHA.items():
            with self.subTest(name=name):
                projected = all_layers_off(name, read(name))
                self.assertEqual(hashlib.sha256(projected.encode("utf8")).hexdigest(), digest)
                once = off_source(name, read(name))
                self.assertEqual(off_source(name, once), once)

    def test_partial_hunk_fails_closed(self):
        damaged = read("task_rail.nut").replace(
            "  if (this._railSearch != null) return;\n  local searchWeight",
            "  if (this._railSearch != null) { return; }\n  local searchWeight")
        with self.assertRaises(AssertionError):
            off_source("task_rail.nut", damaged)
        with self.assertRaises(AssertionError):
            off_source("builder_rail.nut", read("builder_rail.nut") + INSERTIONS["builder_rail.nut"][0])

    def test_static_arity_of_touched_functions(self):
        sigs = global_signatures()
        for name, fn in (("task_rail.nut", "OpexAI::_startRailUpgradeSearch"),
                         ("task_rail.nut", "OpexAI::_consumeRailUpgrade"),
                         ("builder_rail.nut", "OpexExecuteUpgradeAfterSearch")):
            text = strip_squirrel(function_body(read(name), fn))
            for m in re.finditer(r"\b(Opex\w+)\s*\(", text):
                if m.group(1) not in sigs:
                    continue
                n = len(call_args(text, m.end() - 1))
                self.assertTrue(any(r <= n <= t for r, t in sigs[m.group(1)]), m.group(1))


if __name__ == "__main__":
    unittest.main()
