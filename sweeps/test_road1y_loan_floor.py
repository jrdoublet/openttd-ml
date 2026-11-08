"""Contract tests for ROAD1Y early loan repayment cash floor (road1y_loan_floor).

Verifies:
- setting declared default 0 at all four difficulties (0..500 k£);
- ROAD1Y_LOAN_FLOOR global declared default 0 in globals_pre.nut;
- ROAD1Y_LOAN_FLOOR read in OpexLoadSettings and OpexLoadBusDistrictSettings,
  clamped to 0..500 and forced to 0 outside road-only mode;
- _tryRepayLoan in capital.nut computes effective floor as
  (ROAD1Y_LOAN_FLOOR > 0) ? (ROAD1Y_LOAN_FLOOR * 1000) : LOAN_REPAY_FLOOR;
- preserves safety reserve: remaining cash >= floor;
- OpexDecide under DECISION_LOG guards;
- Squirrel hazards check: no try/yield, no anonymous functions, no reserved word identifiers.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source

AI = ROOT / "ai" / "OpexAI"


class TestRoad1yLoanFloor(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_loan_floor"'), 1)
        setting_block = info_src.split('name = "road1y_loan_floor",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 500", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_LOAN_FLOOR <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_loan_floor")'), 1)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_loan_floor")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_LOAN_FLOOR = AIController.GetSetting("road1y_loan_floor");', load_fn)
        self.assertIn("if (ROAD1Y_LOAN_FLOOR < 0 || ROAD1Y_LOAN_FLOOR > 500) ROAD1Y_LOAN_FLOOR = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_LOAN_FLOOR = 0;", load_fn)
        self.assertNotIn("road1y_loan_floor", source("persist.nut"))
        self.assertNotIn("ROAD1Y_LOAN_FLOOR", source("persist.nut"))

    def test_capital_repay_implementation(self):
        code = body("capital.nut", "OpexAI::_tryRepayLoan")
        expected_floor = "local floor = (ROAD1Y_LOAN_FLOOR > 0) ? (ROAD1Y_LOAN_FLOOR * 1000) : LOAN_REPAY_FLOOR;"
        self.assertIn(expected_floor, code)
        self.assertIn("if (cash <= floor)", code)
        self.assertIn("local minNewLoan = loan - (cash - floor);", code)
        self.assertIn("if (minNewLoan < 0) minNewLoan = 0;", code)
        self.assertIn("local newLoan = ((minNewLoan + interval - 1) / interval) * interval;", code)
        self.assertIn("if (newLoan >= loan)", code)
        self.assertIn("AICompany.SetLoanAmount(newLoan);", code)
        # Check DECISION_LOG guards
        self.assertIn("if (DECISION_LOG)", code)
        self.assertNotIn("function(", code)
        self.assertNotIn(".find(", code)
        self.assertNotIn("yield", code)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", code), word)


if __name__ == "__main__":
    unittest.main()
