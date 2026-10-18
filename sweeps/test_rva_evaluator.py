from pathlib import Path
import re
import unittest

AI=Path(__file__).resolve().parents[1]/'ai/OpexAI'


class Evaluator(unittest.TestCase):
    def test_guards_and_attempt_line_link(self):
        self.assertIn('if (RVA_CYCLE_PROBE) OpexRvaEvalStep();',(AI/'scheduler.nut').read_text())
        self.assertIn('if (RVA_CYCLE_PROBE) OpexRvaObserveAttempt(candidate, result, this._nextLineId);',
                      (AI/'task_rail.nut').read_text())
        text=(AI/'rva_evaluator.nut').read_text()
        for token in ('reason=busy','reason=month_changed','excludeA','excludeB','id=',
                      'C67_SLACK_MIN','C67_SLACK_RESERVE','OpexOpsMeasureEnd',
                      'reference_fallback','rivals=unobserved'):
            self.assertIn(token,text)

    def test_readonly_and_no_reserved_identifiers(self):
        text=(AI/'rva_evaluator.nut').read_text()
        self.assertNotRegex(text,r'\b(?:candidate|result)\.\w+\s*(?:<-|=(?!=))')
        self.assertNotRegex(text,r'\blocal\s+(?:clone|base|parent)\b')
        self.assertNotRegex(text,r'\bAI\w+\.(?:Build\w+|Sell\w+|Demolish\w+|AppendOrder)\(')
        self.assertNotIn('function(',text)
        for token in ('AITileList_StationCoverage', 'GetHouseCount','GetLastMonthProduction',
                      'GetCargoProduction','GetCargoRating','GetCargoWaiting'):
            self.assertIn(token,text)

    def test_no_persistent_observations(self):
        self.assertNotIn('RVA_EVAL_WORK',(AI/'persist.nut').read_text())
        self.assertIn('require("rva_evaluator.nut");',(AI/'main.nut').read_text())
