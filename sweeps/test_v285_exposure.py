"""Contrats de l'instrumentation et du compteur de wagons V285."""

from pathlib import Path
import tempfile
import unittest

from analyze_v285_exposure import analyze, summarize_lines

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class TestV285Exposure(unittest.TestCase):
    def test_parse_attempt_move_failure_and_gates(self):
        lines = [
            "[time] dbg: [script:4] [0] [I] OPEX 1972-1-1 V285 action=wagon line=12 old_wagons=2",
            "[time] dbg: [script:4] [0] [I] OPEX 1972-1-1 V285_RESULT action=moved reason=move_wagon_ok line=12 cost=1250",
            "[time] dbg: [script:4] [0] [I] OPEX 1972-1-1 V285_RESULT action=completed reason=resumed line=12 cost=1250",
            "[time] dbg: [script:4] [0] [I] OPEX 1972-1-1 V285_GATE line=13 reason=platform wagons=3",
            "[time] dbg: [script:4] [1] [I] OPEX 1972-1-1 V285_RESULT action=moved reason=move_wagon_ok line=4 cost=5000",
        ]
        counts, gates, moved = summarize_lines(lines)
        self.assertEqual((counts["attempts"], counts["moved"], counts["completed"]), (1, 1, 1))
        self.assertEqual(counts["wagon_cost"], 1250)
        self.assertEqual(gates["platform"], 1)
        self.assertEqual(moved["12"], 1)

    def test_file_by_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "v285_seed42_r0.log")
            path.write_text("[0] [I] OPEX 1972-1-1 V285_RESULT action=moved reason=ok line=3 cost=800\n", encoding="utf-8")
            rows = analyze(Path(tmp), "v285")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["seed"], 42)
            self.assertEqual(rows[0]["moved"], 1)

    def test_source_has_separate_attempt_and_physical_success(self):
        code = (AI / "task_rail.nut").read_text(encoding="utf-8")
        self.assertIn('OpexV285ResultLog(state, "moved", "move_wagon_ok")', code)
        self.assertIn('OpexV285ResultLog(state, "completed", "resumed")', code)
        self.assertIn('OpexV285GateLog(line, "platform")', code)
        self.assertIn('if (!DECISION_LOG || !("lineId" in line)) return;', code)


if __name__ == "__main__":
    unittest.main()
