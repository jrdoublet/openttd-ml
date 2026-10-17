#!/usr/bin/env python3
"""Contrat statique de la memoire d'echec des doublements de voie.

rail_upgrade_failure_memory vaut 0 aux quatre difficultes. La lecture et
l'ecriture restent sous RAIL_UPGRADE_FAILURE_MEMORY. Aucune partie OpenTTD
n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


class TestRailUpgradeFailureMemoryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.lines = _read("ai/OpexAI/lines.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.consume_body = _function_body(
            cls.task_rail, "function OpexAI::_consumeRailUpgrade()"
        )

    def test_setting_enabled_by_default_in_info_nut(self):
        self.assertNotIn('name = "rail_upgrade_failure_memory"', _read("ai/OpexAI/info.nut"))
        self.assertNotIn('GetSetting("rail_upgrade_failure_memory")', _read("ai/OpexAI/settings.nut"))
        self.assertNotIn("RAIL_UPGRADE_FAILURE_MEMORY <-", _read("ai/OpexAI/globals_pre.nut"))

    def test_global_declared_and_loaded_once(self):
        self.assertNotIn('name = "rail_upgrade_failure_memory"', _read("ai/OpexAI/info.nut"))
        self.assertNotIn('GetSetting("rail_upgrade_failure_memory")', _read("ai/OpexAI/settings.nut"))
        self.assertNotIn("RAIL_UPGRADE_FAILURE_MEMORY <-", _read("ai/OpexAI/globals_pre.nut"))

    def test_reject_key_defined_in_lines_nut(self):
        pair_key = self.lines.index("function OpexAbandonedPairKey(candidate)")
        reject_key = self.lines.index("function OpexRailUpgradeRejectKey(lineId)")
        mark = self.lines.index("function OpexAI::_markPairAbandoned(key)")
        self.assertLess(pair_key, reject_key)
        self.assertLess(reject_key, mark)
        body = _function_body(self.lines, "function OpexRailUpgradeRejectKey(lineId)")
        self.assertIn('return "rail_upgrade|" + lineId;', body)

    def test_resumable_failure_is_marked_under_both_guards(self):
        body = self.consume_body
        call = "this._markPairAbandoned(OpexRailUpgradeRejectKey(state.line.lineId));"
        self.assertEqual(self.task_rail.count("_markPairAbandoned(OpexRailUpgradeRejectKey("), 1)
        cash_return = body.index('if (upgrade.reason == "CASH")')
        guard = body.index("if (!upgrade.ok)")
        release = body.index("this._railSearch = null;", guard)
        window = body[guard:release]
        self.assertIn(call, window)
        self.assertIn("!upgrade.ok", window)
        self.assertLess(cash_return, guard)
        self.assertNotIn(call, body[cash_return:guard])
        success = body.index("if (upgrade.ok)")
        self.assertNotIn(call, body[success:guard])

    def test_case2_read_guard_mentions_memory_and_abandoned_pairs(self):
        start = self.task_rail.index("// Cas 2 :")
        prepare = self.task_rail.index("OpexPrepareUpgradeSearch(line, HARD_ITERATION_CAP)", start)
        block = self.task_rail[start:prepare]
        header_end = block.index(") {")
        header = block[:header_end]
        body = block[header_end:]
        self.assertNotIn("RAIL_UPGRADE_FAILURE_MEMORY", header)
        self.assertIn(
            '(!("doubleTrack" in line) || line.doubleTrack == 0)',
            header,
        )
        self.assertNotIn("RAIL_UPGRADE_FAILURE_MEMORY", body)
        self.assertIn("ABANDON_MEMORY", body)
        self.assertIn("this._abandonedPairs != null", body)
        self.assertIn('("lineId" in line)', body)
        self.assertIn(
            "(OpexRailUpgradeRejectKey(line.lineId) in this._abandonedPairs)",
            body,
        )
        null_at = body.index("this._abandonedPairs != null")
        member_at = body.index("in this._abandonedPairs")
        self.assertLess(null_at, member_at)
        self.assertIn("continue;", body)


if __name__ == "__main__":
    unittest.main()
