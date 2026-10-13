"""Unit checks for top-level occupancy and paired gate health."""
import tempfile
from pathlib import Path
import unittest

from analyse_p0_visible_competition_porteA_20261012 import event_occupancy


def entry(year, post, ops, tk=1):
    return f"dbg: [script:4] [0] [I] LOOP_OPS y={year} post={post} n=1 ops={ops} tk={tk} max=0"


class C121VisibleGateAuditTests(unittest.TestCase):
    def test_nested_loop_ops_not_double_counted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.log"
            path.write_text("\n".join([
                entry(1970, "_year", 0, 80),
                entry(1970, "orchestrator", 100),
                entry(1970, "catalog_continuation", 70),
                entry(1970, "C39_PROJECTS", 800),
                entry(1970, "sleep_left", 40),
            ]), encoding="utf-8")
            values = event_occupancy(path, (1970,))
            self.assertEqual(170, values[1970]["global_top_level_occupied"])
            self.assertEqual(40, values[1970]["sleep_left"])
            self.assertEqual(800_000, values[1970]["tick_budget"])

    def test_duplicate_post_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.log"
            path.write_text("\n".join([
                entry(1970, "_year", 0), entry(1970, "orchestrator", 100),
                entry(1970, "orchestrator", 200), entry(1970, "sleep_left", 10),
            ]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                event_occupancy(path, (1970,))

    def test_missing_year_close_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engine.log"
            path.write_text(entry(1970, "orchestrator", 100), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "closure incomplete"):
                event_occupancy(path, (1970,))


if __name__ == "__main__":
    unittest.main()
