#!/usr/bin/env python3
"""Contrat statique : sonde d'exposition probe_air_finance_margin.

probe_air_finance_margin vaut 0 aux quatre difficultes. A 0, les tests de
caisse AIR (legacy et portefeuille) et la boucle de maintenance de flotte
gardent leur corps historique derriere un test du drapeau. A 1, la sonde
journalise AIR_FINANCE_TRY / AIR_FINANCE_FIRST_REVENUE / AIR_FINANCE_PENDING
sans ecrire un choix. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TRY_FIELDS = (
    "date=",
    "rank=",
    "src_town=",
    "dst_town=",
    "new_airports=",
    "margin=",
    "reserve=",
    "capital=",
    "need=",
    "cash=",
    "outcome=",
    "path=",
)
BUILT_EXTRA_FIELDS = (
    "planned=",
    "actual=",
    "reason=",
    "line=",
)
FIRST_REVENUE_FIELDS = (
    "line=",
    "build_date=",
    "first_date=",
    "days=",
    "cash_min=",
)
PENDING_FIELDS = (
    "line=",
    "build_date=",
    "days=",
)
OUTCOMES = (
    "refused_margin",
    "refused_capital",
    "built",
    "failed",
)
RESERVED = ("clone", "base", "parent")


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


def _probe_blocks(body):
    blocks = []
    start = 0
    while True:
        idx = body.find("if (PROBE_AIR_FINANCE_MARGIN", start)
        if idx < 0:
            break
        open_brace = body.find("{", idx)
        if open_brace < 0:
            blocks.append(body[idx:])
            break
        depth = 0
        end = open_brace
        for i, ch in enumerate(body[open_brace:], open_brace):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        blocks.append(body[idx:end])
        start = end
    return blocks


class TestAirFinanceMarginProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.task = _read("ai/OpexAI/task_air.nut")
        cls.legacy = _function_body(cls.task, "function OpexAI::_tryBuildAir(")
        cls.portfolio = _function_body(
            cls.task, "function OpexAI::_tryBuildAirProject("
        )
        cls.resize = _function_body(cls.task, "function OpexAI::_resizeAirFleets(")
        cls.date_fn = _function_body(cls.task, "function OpexAirFinanceMarginDate(")
        cls.log_try = _function_body(cls.task, "function OpexAirFinanceMarginLogTry(")
        cls.init_line = _function_body(
            cls.task, "function OpexAirFinanceMarginInitLine("
        )
        cls.profit_sum = _function_body(
            cls.task, "function OpexAirFinanceMarginProfitSum("
        )
        cls.tick = _function_body(cls.task, "function OpexAirFinanceMarginTick(")

    def test_setting_defaults_off(self):
        start = self.info.index('name = "probe_air_finance_margin"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("0 = off (default)", block)
        self.assertIn("AIR_FINANCE_TRY", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertNotIn("easy_value = 1", block)
        self.assertEqual(self.info.count('name = "probe_air_finance_margin"'), 1)
        self.assertIn("PROBE_AIR_FINANCE_MARGIN <- false;", self.globals)
        self.assertIn("AIR_FINANCE_MARGIN_YEAR <- -1;", self.globals)
        self.assertEqual(self.globals.count("PROBE_AIR_FINANCE_MARGIN"), 1)
        self.assertEqual(self.globals.count("AIR_FINANCE_MARGIN_YEAR"), 1)
        needle = 'AIController.GetSetting("probe_air_finance_margin")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'PROBE_AIR_FINANCE_MARGIN = AIController.GetSetting("probe_air_finance_margin") != 0;',
            self.settings,
        )
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN <-", self.settings)
        for token in (
            "probe_air_finance_margin",
            "PROBE_AIR_FINANCE_MARGIN",
            "AIR_FINANCE_MARGIN_YEAR",
            "finProbePrev",
        ):
            self.assertNotIn(token, self.persist)

    def test_flag_off_cash_checks_keep_historical_need(self):
        self.assertIn(
            "local need = capital + baseReserve + requiredMargin;", self.legacy
        )
        self.assertEqual(self.legacy.count("OpexCashReserve()"), 1)
        self.assertIn("local baseReserve = OpexCashReserve();", self.legacy)
        self.assertLess(
            self.legacy.index("local need = capital + baseReserve + requiredMargin;"),
            self.legacy.index("if (PROBE_AIR_FINANCE_MARGIN && money < need)"),
        )

        self.assertIn(
            "local need = capital + OpexCashReserve() + requiredMargin;",
            self.portfolio,
        )
        self.assertEqual(self.portfolio.count("OpexCashReserve()"), 1)
        need = self.portfolio.index(
            "local need = capital + OpexCashReserve() + requiredMargin;"
        )
        self.assertLess(
            need,
            self.portfolio.index("if (PROBE_AIR_FINANCE_MARGIN && money < need)"),
        )
        self.assertLess(
            self.portfolio.index("if (PROBE_AIR_FINANCE_MARGIN && money < need)"),
            self.portfolio.index("if (money < need) {"),
        )
        refusal = self.portfolio[
            self.portfolio.index("if (money < need) {") : self.portfolio.index(
                'return { outcome = "rejected", discards = passDiscards };'
            )
        ]
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", refusal)
        self.assertNotIn("AIR_FINANCE", refusal)

        for body in (self.legacy, self.portfolio):
            for block in _probe_blocks(body):
                self.assertNotIn("OpexCashReserve()", block)

    def test_try_logs_are_gated_and_cover_both_paths(self):
        self.assertIn('path=" + path', self.log_try)
        self.assertIn('"AIR_FINANCE_TRY date="', self.log_try)
        for field in TRY_FIELDS:
            self.assertIn(field, self.log_try)
        self.assertIn('AILog.Info(msg)', self.log_try)
        self.assertEqual(self.task.count('"AIR_FINANCE_TRY'), 1)

        self.assertIn('OpexAirFinanceMarginLogTry("legacy"', self.legacy)
        self.assertIn('OpexAirFinanceMarginLogTry("portfolio"', self.portfolio)
        self.assertEqual(self.legacy.count("OpexAirFinanceMarginLogTry("), 2)
        self.assertEqual(self.portfolio.count("OpexAirFinanceMarginLogTry("), 2)

        for body in (self.legacy, self.portfolio):
            self.assertIn("refused_margin", body)
            self.assertIn("refused_capital", body)
            self.assertIn('result.ok ? "built" : "failed"', body)
            self.assertIn("planned=" + '" + result.plannedCapital', body)
            self.assertIn("actual=" + '" + result.actualCost', body)
            self.assertIn("reason=" + '" + result.reason', body)
            self.assertIn("line=" + '" + this._nextLineId', body)
            self.assertLess(
                body.index("if (PROBE_AIR_FINANCE_MARGIN && money < need)"),
                body.index("OpexBuildAirRoute("),
            )
            self.assertGreater(
                body.index("OpexAirFinanceMarginLogTry("),
                body.index("local need ="),
            )

        self.assertIn("need - capital - requiredMargin", self.portfolio)
        self.assertIn("baseReserve", self.legacy)
        self.assertIn("money >= capital + baseReserve", self.legacy)
        self.assertIn("money >= capital + reserve", self.portfolio)

        for outcome in OUTCOMES:
            self.assertIn(outcome, self.task)

        for field in BUILT_EXTRA_FIELDS:
            self.assertIn(field, self.legacy)
            self.assertIn(field, self.portfolio)

        self.assertEqual(self.legacy.count("OpexAirFinanceMarginInitLine("), 1)
        self.assertEqual(self.portfolio.count("OpexAirFinanceMarginInitLine("), 1)
        self.assertIn(
            "if (PROBE_AIR_FINANCE_MARGIN) {\n      OpexAirFinanceMarginInitLine(",
            self.legacy,
        )
        self.assertIn("OpexAirFinanceMarginInitLine(", self.portfolio)
        self.assertIn("buildDate = AIDate.GetCurrentDate()", self.legacy)
        self.assertIn("buildDate = AIDate.GetCurrentDate()", self.portfolio)

    def test_first_revenue_tick_is_gated_on_fleet_maintenance(self):
        self.assertTrue(
            self.resize.lstrip().startswith(
                "function OpexAI::_resizeAirFleets(year, plan = null)\n"
                "{\n  if (PROBE_AIR_FINANCE_MARGIN) "
                "OpexAirFinanceMarginTick(this._lines, year);"
            )
        )
        self.assertIn(
            "local spFleet = PROBE_SPAN_TRACE ? OpexSpanBegin(\"fleet.resize\") : null;",
            self.resize,
        )
        after_tick = self.resize.split("OpexAirFinanceMarginTick(this._lines, year);", 1)[1]
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", after_tick)
        self.assertNotIn("AIR_FINANCE", after_tick)
        self.assertNotIn("finProbePrev", after_tick)

        self.assertIn("AIVehicle.GetProfitThisYear(v)", self.profit_sum)
        self.assertIn("foreach (v in line.vehicles)", self.profit_sum)
        self.assertIn("line.finProbePrev <- { profit = 0, year = year, cashMin = money };", self.init_line)
        self.assertIn("sum > prev.profit", self.tick)
        self.assertIn("else if (sum > 0)", self.tick)
        self.assertIn('"AIR_FINANCE_FIRST_REVENUE line="', self.tick)
        self.assertIn('"AIR_FINANCE_PENDING line="', self.tick)
        self.assertIn("AIR_FINANCE_MARGIN_YEAR != year", self.tick)
        self.assertIn("line.finProbePrev = null;", self.tick)
        self.assertIn("prev.cashMin", self.tick)
        for field in FIRST_REVENUE_FIELDS:
            self.assertIn(field, self.tick)
        for field in PENDING_FIELDS:
            self.assertIn(field, self.tick)
        self.assertIn('"0" + month', self.date_fn)
        self.assertIn('"0" + day', self.date_fn)
        self.assertIn('AIDate.GetYear(date) + "-"', self.date_fn)

        self.assertEqual(self.task.count("OpexAirFinanceMarginTick("), 2)

    def test_no_squirrel_pitfalls_in_probe_helpers(self):
        for body in (
            self.date_fn,
            self.log_try,
            self.init_line,
            self.profit_sum,
            self.tick,
            self.legacy,
            self.portfolio,
            self.resize,
        ):
            for word in RESERVED:
                self.assertIsNone(re.search(r"\b" + word + r"\b", body), word)
            self.assertNotIn("local function", body)
            self.assertIsNone(re.search(r"=\s*function\s*\(", body))

        self.assertIn("finProbePrev <-", self.init_line)
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", self.date_fn)
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", self.log_try)
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", self.tick)
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", self.profit_sum)
        self.assertNotIn("PROBE_AIR_FINANCE_MARGIN", self.init_line)


if __name__ == "__main__":
    unittest.main()
