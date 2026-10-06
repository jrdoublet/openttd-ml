#!/usr/bin/env python3
"""Contrat statique du plafond de detention du creneau A* rail.

rail_search_day_cap vaut 0 aux quatre difficultes. La difference de jours
et la liberation du creneau restent dans la garde RAIL_SEARCH_DAY_CAP > 0.
Aucune partie OpenTTD n'est lancee.
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


class TestRailSearchDayCapContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.continue_body = _function_body(
            cls.task_rail, "function OpexAI::_continueRailSearch()"
        )

    def test_setting_declared_inert_in_info_nut(self):
        block = _setting_block(self.info, "rail_search_day_cap")
        self.assertIn(
            "max days a single rail A* search may hold the one search slot "
            "before being abandoned and the slot released; 0 = off (default)",
            block,
        )
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 400", block)
        self.assertIn("step_size = 10", block)
        self.assertIn("flags = 0", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)

    def test_global_declared_in_globals_pre_nut(self):
        self.assertIn("RAIL_SEARCH_DAY_CAP <- 0;", self.globals)

    def test_setting_loaded_once_in_settings_nut(self):
        needle = 'AIController.GetSetting("rail_search_day_cap")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'RAIL_SEARCH_DAY_CAP = AIController.GetSetting("rail_search_day_cap");',
            self.settings,
        )
        self.assertNotIn("RAIL_SEARCH_DAY_CAP <-", self.settings)

    def test_day_cap_guard_releases_slot_and_probes_daycap(self):
        body = self.continue_body
        guard = body.index("if (RAIL_SEARCH_DAY_CAP > 0)")
        normal_begin = body.index("\n  this._budget.begin();", guard)
        block = body[guard:normal_begin]

        self.assertNotIn("AIDate.GetCurrentDate()", body[:guard])
        self.assertIn("AIDate.GetCurrentDate()", block)
        self.assertIn("heldDays > RAIL_SEARCH_DAY_CAP", block)
        self.assertIn('this._budget.end("build_search")', block)
        self.assertIn("this._railSearch = null;", block)
        # Pas de hook de registre ici : le contrat test_c75bis_v89_railfactor l'interdit dans
        # task_rail.nut. L'abandon reste lisible par le journal de decision et la trace C56.
        self.assertIn("outcome=daycap result=none", block)
        self.assertIn('outcome=daycap iters=', block)

        search_days = body.index('local searchDays = ("startDate" in state)')
        self.assertGreater(search_days, normal_begin)
        self.assertIn("if (C56_TASK_TRACE)", body[:search_days])
        self.assertNotIn("local searchDays", block)


if __name__ == "__main__":
    unittest.main()
