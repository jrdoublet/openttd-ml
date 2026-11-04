"""RAIL-OPEN: strict opt-in, funding, and safe station reuse contracts."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function(name, symbol):
    code = source(name)
    start = code.index("function " + symbol + "(")
    begin = code.index("{", start)
    depth = 0
    for index in range(begin, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return code[start:index + 1]
    raise AssertionError("unterminated function: " + symbol)


class RailOpenContracts(unittest.TestCase):
    def test_setting_default_zero_and_loaded_once(self):
        info = source("info.nut")
        setting = re.search(r'AddSetting\(\{ name = "rail_open",.*?\}\);', info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(0), rf"{difficulty}_value\s*=\s*0\b")
        self.assertIn("min_value = 0, max_value = 1", setting.group(0))
        self.assertIn("RAIL_OPEN <- 0;", source("globals_pre.nut"))
        self.assertEqual(source("settings.nut").count('AIController.GetSetting("rail_open")'), 1)
        self.assertIn("RAIL_OPEN = (railOpen != null && railOpen > 0) ? 1 : 0;", source("settings.nut"))

    def test_open_requires_cash_and_actual_candidate_capital(self):
        checker = function("candidates.nut", "OpexRailOpenCashReady")
        self.assertIn("if (RAIL_OPEN == 0) return false;", checker)
        self.assertIn("AICompany.GetBankBalance(AICompany.COMPANY_SELF)", checker)
        self.assertIn("RAIL_OPEN_MIN_CASH", checker)
        self.assertIn("capital + RAIL_OPEN_CASH_HEADROOM", checker)
        emit = function("candidates.nut", "OpexRailSiblingEmit")
        self.assertLess(emit.index("OpexRailOpenCashReady(estimatedCash)"),
                        emit.index("candidate.sibling_src <- 1;"))
        self.assertIn("candidate.capital + candidate.immobilise", emit)
        self.assertIn("stats.accepted--;", emit)
        self.assertIn("candidate.railOpen <- 1;", emit)
        self.assertIn('("railOpen" in candidate) && candidate.profitAnnual <= 0', emit)

    def test_open_gate_extends_legacy_sibling_without_changing_off_thresholds(self):
        parent = function("candidates.nut", "OpexRailSiblingParent")
        self.assertIn("if (RAIL_SIBLING == 0 && RAIL_OPEN == 0) return null;", parent)
        self.assertIn("if (RAIL_SIBLING == 0 && !openMode) return null;", parent)
        self.assertIn("if (!openMode) return null;", parent)
        self.assertIn("if (stationLines >= 3) return null;", parent)
        self.assertIn("if (revPct < (openMode ? 80 : 100)) return null;", parent)
        self.assertIn("waiting * 4 < trainCapacity && transported >= 75", parent)
        self.assertIn("waiting * 2 < trainCapacity && transported >= RAIL_SIBLING_TRANSPORTED_PCT", parent)
        self.assertIn("if (openMode) mother.railOpen <- 1;", parent)
        scale = function("candidates.nut", "OpexRailSiblingApplyRevenue")
        self.assertIn('candidate.siblingRevPct <= 100 && !("railOpen" in candidate)', scale)
        self.assertIn("candidate.revenueAnnual * candidate.siblingRevPct", scale)

    def test_both_generators_reject_dual_join_and_preserve_v264(self):
        for name, fn in (("candidates.nut", "OpexFreightCandidates"),
                         ("po01c_generators.nut", "OpexPO01CFreightCandidates")):
            with self.subTest(name=name):
                body = function(name, fn)
                self.assertIn("RAIL_OPEN != 0 && RAIL_SIBLING == 0 && ss != null", body)
                self.assertIn("if (sibling != null && sd == null) {", body)
                self.assertIn("if (RAIL_OPEN != 0 && sibling != null && sd != null) {", body)
                self.assertIn("reason=both_ends_served", body)
                self.assertLess(body.index("reason=both_ends_served"),
                                body.index("OpexV264ConvergentService(lines, sd, cargo, source.tile)"))
                self.assertIn("if (ss == null && sd != null) {", body)
                self.assertIn("OpexV264EmitConvergent(", body)
        join = source("builder_rail.nut")
        self.assertIn('"sibling_src" in candidate', join)

    def test_no_squirrel_reserved_identifiers_or_new_valuate(self):
        added = (function("candidates.nut", "OpexRailOpenCashReady")
                 + function("candidates.nut", "OpexRailSiblingParent"))
        self.assertIsNone(re.search(r"\blocal\s+(?:clone|base|parent|static|delegate|resume|yield|constructor|instanceof)\b", added))
        self.assertNotIn(".Valuate(", added)
        self.assertNotIn("function(", added)


if __name__ == "__main__":
    unittest.main()
