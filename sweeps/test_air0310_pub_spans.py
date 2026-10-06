#!/usr/bin/env python3
"""Contrat statique des sous-spans pub.* de la publication partielle AIR 03/10.

Les spans ne s'ouvrent que si PROBE_SPAN_TRACE est vrai. A 0, le ternaire
n'appelle ni OpexSpanBegin ni OpexOpsMeasureBegin : pas d'allocation, pas
d'appel hors sonde. Aucune partie n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


def _brace_balance(text):
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            if i < 0:
                break
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return depth
        i += 1
    return depth


# Une fois par publication : OpexSpanBegin / OpexSpanEnd.
PUBLISH_SPANS = (
    ("pub.prior", "spPubPrior"),
    ("pub.new_plans", "spPubNew"),
    ("pub.filter", "spPubFilter"),
    ("pub.partition", "spPubPart"),
    ("pub.insert", "spPubInsert"),
    ("pub.store", "spPubStore"),
    ("pub.recount", "spPubRecount"),
    ("pub.capital", "spPubCap"),
    ("pub.select", "spPubSelect"),
)

# Une fois par reelection : meme forme, un niveau sous la selection.
SELECT_SPANS = (
    ("pub.select.flatten", "spPubFlat"),
    ("pub.select.merge", "spPubMerge"),
    ("pub.select.filter", "spPubFilt"),
    ("pub.select.score", "spPubScore"),
    ("pub.select.log", "spPubLog"),
    ("pub.select.stats", "spPubStats"),
    ("pub.select.vivier", "spPubVivier"),
)


class TestAir0310PubSpans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.update = _read("ai/OpexAI/projects_update.nut")
        cls.selection = _read("ai/OpexAI/projects_selection.nut")
        cls.capital = _read("ai/OpexAI/capital.nut")
        cls.publish = _function_body(cls.update, "function OpexAir0310PublishIncremental(")
        cls.reselect = _function_body(cls.selection, "function OpexReselectProjects(")
        cls.fund = _function_body(cls.selection, "function OpexProjectFundProfit(")
        cls.cash = _function_body(cls.capital, "function OpexCashReserve(")
        cls.available = _function_body(cls.capital, "function OpexAvailableCapital(")

    def test_publish_steps_are_probe_gated_spans(self):
        previous = -1
        for name, token in PUBLISH_SPANS:
            begin = f'local {token} = PROBE_SPAN_TRACE ? OpexSpanBegin("{name}") : null;'
            end = f"if ({token} != null) OpexSpanEnd({token});"
            self.assertIn(begin, self.publish, name)
            self.assertIn(end, self.publish, name)
            self.assertLess(self.publish.index(begin), self.publish.index(end), name)
            self.assertGreater(self.publish.index(begin), previous, name)
            previous = self.publish.index(begin)
            self.assertEqual(self.publish.count(f'OpexSpanBegin("{name}")'), 1)
        self.assertNotIn('OpexSpanBegin("pub.', self.publish.replace(
            "PROBE_SPAN_TRACE ? OpexSpanBegin(", ""
        ))

    def test_publish_order_keeps_capital_before_reselect(self):
        capital = self.publish.index('OpexSpanBegin("pub.capital")')
        read = self.publish.index("local publishCapital = OpexAvailableCapital();")
        capital_end = self.publish.index("if (spPubCap != null) OpexSpanEnd(spPubCap);")
        select = self.publish.index('OpexSpanBegin("pub.select")')
        call = self.publish.index(
            "OpexReselectProjects(projects, publishCapital, owner._abandonedPairs, owner._lines,"
        )
        select_end = self.publish.index("if (spPubSelect != null) OpexSpanEnd(spPubSelect);")
        self.assertLess(capital, read)
        self.assertLess(read, capital_end)
        self.assertLess(capital_end, select)
        self.assertLess(select, call)
        self.assertLess(call, select_end)
        self.assertIn("OpexProjectsRecountGroups(projects);", self.publish)
        self.assertLess(
            self.publish.index('OpexSpanBegin("pub.recount")'),
            self.publish.index("OpexProjectsRecountGroups(projects);"),
        )
        self.assertLess(
            self.publish.index("OpexProjectsRecountGroups(projects);"),
            self.publish.index("if (spPubRecount != null) OpexSpanEnd(spPubRecount);"),
        )

    def test_reselect_steps_are_probe_gated_spans(self):
        previous = -1
        for name, token in SELECT_SPANS:
            begin = f'local {token} = PROBE_SPAN_TRACE ? OpexSpanBegin("{name}") : null;'
            end = f"if ({token} != null) OpexSpanEnd({token});"
            self.assertIn(begin, self.reselect, name)
            self.assertIn(end, self.reselect, name)
            self.assertLess(self.reselect.index(begin), self.reselect.index(end), name)
            self.assertGreater(self.reselect.index(begin), previous, name)
            previous = self.reselect.index(begin)
            self.assertEqual(self.reselect.count(f'OpexSpanBegin("{name}")'), 1)
        flat = self.reselect.index('OpexSpanBegin("pub.select.flatten")')
        filt = self.reselect.index("OpexFilterAirAlternativesStillValid(")
        score = self.reselect.index("OpexProjectSelectAffordable(")
        log = self.reselect.index('OpexB6LogSelectionCausality("reselect"')
        vivier = self.reselect.index('OpexLogVivier("reselect"')
        self.assertLess(flat, filt)
        self.assertLess(filt, score)
        self.assertLess(score, log)
        self.assertLess(log, vivier)
        self.assertLess(
            self.reselect.index('OpexSpanBegin("pub.select.score")'),
            score,
        )
        self.assertLess(
            score,
            self.reselect.index("if (spPubScore != null) OpexSpanEnd(spPubScore);"),
        )
        self.assertNotIn('OpexSpanBegin("pub.', self.reselect.replace(
            "PROBE_SPAN_TRACE ? OpexSpanBegin(", ""
        ))

    def test_frequent_calls_use_aggregated_spans(self):
        calib = 'local calibMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;'
        self.assertIn(calib, self.fund)
        self.assertIn(
            'local calibrated = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(project) : project.profitAnnual;',
            self.fund,
        )
        self.assertLess(self.fund.index(calib), self.fund.index("OpexCalibratedProfit(project)"))
        self.assertIn(
            'if (calibMark != null) OpexSpanAgg("pub.select.calibrate", calibMark);',
            self.fund,
        )
        self.assertLess(
            self.fund.index("OpexCalibratedProfit(project)"),
            self.fund.index('OpexSpanAgg("pub.select.calibrate"'),
        )
        self.assertNotIn("OpexSpanBegin(", self.fund)
        cash_mark = "local cashMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;"
        self.assertIn(cash_mark, self.cash)
        self.assertEqual(self.cash.count('OpexSpanAgg("pub.cash", cashMark)'), 2)
        self.assertLess(self.cash.index(cash_mark), self.cash.index("AIVehicleList()"))
        self.assertIn("if (cashMark != null) OpexSpanAgg(\"pub.cash\", cashMark);", self.cash)
        self.assertNotIn("OpexSpanBegin(", self.cash)
        self.assertNotIn("OpexSpanBegin(", self.available)
        self.assertIn("OpexCashReserve()", self.available)

    def test_sources_stay_balanced(self):
        self.assertEqual(_brace_balance(self.update), 0)
        self.assertEqual(_brace_balance(self.selection), 0)
        self.assertEqual(_brace_balance(self.capital), 0)


if __name__ == "__main__":
    unittest.main()
