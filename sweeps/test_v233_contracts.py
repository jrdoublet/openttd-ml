"""V233 source contracts. These checks do not compile Squirrel or run a game."""
import unittest
from pathlib import Path

from bench_1v1_5y_20seeds import extract_company_record

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class V233Observability(unittest.TestCase):
    def test_pending_events_are_guarded_and_do_not_record_build(self):
        text = (AI / "task_projects.nut").read_text()
        self.assertEqual(text.count('if (DECISION_LOG) OpexDecide("V233_SEARCH", "state=pending'), 2)
        self.assertIn('if (DECISION_LOG) OpexDecide("V233_BUILD"', text)

    def test_deliveries_are_closed_quarter_company_totals(self):
        for delivered in (None, {}, {"5": 0}, {"5": 64}):
            with self.subTest(delivered=delivered):
                chunks = {"PLYR": {0: {"old_economy": [
                    {"income": 999, "expenses": 0, "delivered_cargo": delivered}
                ]}}, "VEHS": {}, "STNN": {}}
                row = extract_company_record(chunks, 0, ["OpexAI", 42, 0], "1971-01-01")
                self.assertEqual(row["delivered_cargo_last_quarter"], delivered)


if __name__ == "__main__":
    unittest.main()
