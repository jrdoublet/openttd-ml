"""Contract tests: no nested opcode double-counting or fake zero builds."""
import tempfile
from pathlib import Path
import unittest

from analyse_p0_abandon_b20x10 import loops, stats, YEARS


def entry(year, post, ops, ticks=0):
    return (f"[2026-10-12] dbg: [script:4] [0] [I] LOOP_OPS "
            f"y={year} post={post} n=1 ops={ops} tk={ticks} max=0")


class AbandonB20AnalyzerTests(unittest.TestCase):
    def make_log(self, *, duplicate=False, missing=False):
        rows = []
        for y in YEARS:
            rows.extend((entry(y, "_year", 0, 100),
                         entry(y, "orchestrator", 500, 1),
                         entry(y, "catalog_continuation", 60, 0),
                         entry(y, "projects", 400),
                         entry(y, "sleep_left", 120),
                         entry(y, "SPAN_BUILD", 800)))
        if duplicate:
            rows.append(entry(1973, "orchestrator", 501))
        if missing:
            rows = [x for x in rows if "y=1973 post=_year" not in x]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "engine.log"
        path.write_text("\n".join(rows), encoding="utf-8")
        return path

    def test_only_disjoint_top_level_posts_are_counted(self):
        years = loops(self.make_log())
        self.assertEqual(560, years[1973]["occupied_top"])
        self.assertEqual(120, years[1973]["sleep_left"])
        self.assertEqual(1_000_000, years[1973]["tick_budget"])
        self.assertEqual(list(YEARS), list(years))

    def test_duplicate_closure_or_post_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            loops(self.make_log(duplicate=True))

    def test_missing_year_close_rejected(self):
        with self.assertRaisesRegex(ValueError, "closure missing"):
            loops(self.make_log(missing=True))

    def test_bootstrap_is_seeded_and_keeps_negative_direction(self):
        a, b = stats([-4, -2, 1]), stats([-4, -2, 1])
        self.assertEqual(a, b)
        self.assertEqual(2, a["wins_variant_lower"])
        self.assertEqual(1, a["losses_variant_higher"])
        self.assertAlmostEqual(-5 / 3, a["mean"], places=3)


if __name__ == "__main__":
    unittest.main()
