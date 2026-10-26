"""CLI contracts for V307 rail choice-to-attempt duration diagnostics."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("diag_v307_rail_attempts.py")


def chosen(day, src, dst):
    return (f"[0] [I] OPEX {day} PROJECT_CHOSEN "
            f"mode=rail src={src} dst={dst}\n")


def attempted(day, src, dst, reason):
    return (f"[0] [I] OPEX {day} RAIL_ATTEMPT "
            f"src={src} dst={dst} reason={reason} join_end=- shared_dest=0\n")


class V307RailAttemptsTests(unittest.TestCase):
    def run_log(self, *events):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "reference_seed42_r0.log").write_text("".join(events), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), folder],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )

    def test_reselection_uses_latest_chosen_date(self):
        result = self.run_log(
            chosen("1975-1-1", 3, 4),
            chosen("1975-2-1", 3, 4),
            attempted("1975-2-3", 3, 4, "ABND"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ABND: n=1 jours med=2 q90=2 total=2", result.stdout)

    def test_interleaved_pairs_keep_their_own_latest_choice(self):
        result = self.run_log(
            chosen("1975-1-1", 3, 4),
            chosen("1975-1-2", 5, 6),
            chosen("1975-1-10", 3, 4),
            attempted("1975-1-12", 5, 6, "OK"),
            attempted("1975-1-13", 3, 4, "ABND"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK: n=1 jours med=10 q90=10 total=10", result.stdout)
        self.assertIn("ABND: n=1 jours med=3 q90=3 total=3", result.stdout)

    def test_orphan_attempt_keeps_missing_duration_and_prints_summary(self):
        result = self.run_log(attempted("1975-1-12", 9, 10, "ABND"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ABND: n=1 jours med=- q90=- total=0", result.stdout)
        self.assertIn("ABND par jointure:", result.stdout)
        self.assertIn("annee: n, ABND {1975: [1, 1]}", result.stdout)


if __name__ == "__main__":
    unittest.main()
