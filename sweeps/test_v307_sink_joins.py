"""Tests synthetic decision logs for V307 destination-station counting."""

import gzip
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    from sweeps.diag_v307_sink_joins import parse_lines, sinks_for_builds, summarize
except ModuleNotFoundError:
    # Permet aussi `python sweeps/test_v307_sink_joins.py` depuis la racine.
    from diag_v307_sink_joins import parse_lines, sinks_for_builds, summarize


class SinkJoinsTest(unittest.TestCase):
    def test_join_second_third_and_new_station_on_same_tile(self):
        with TemporaryDirectory() as tmp:
            lines = [
                "[0] OPEX 1971-1-1 RAIL_ATTEMPT src=10 dst=50 ok=1 reason=OK",
                "[0] OPEX 1971-1-1 RAIL_BUILD line=1 src=10 dst=50 cargo=COAL join_end=- shared_dest=0",
                "[0] OPEX 1971-2-1 RAIL_ATTEMPT src=11 dst=50 ok=1 reason=OK",
                "[0] OPEX 1971-2-1 RAIL_BUILD line=2 src=11 dst=50 cargo=COAL join_end=B shared_dest=1",
                "[0] OPEX 1971-3-1 RAIL_ATTEMPT src=12 dst=50 ok=1 reason=OK",
                "[0] OPEX 1971-3-1 RAIL_BUILD line=3 src=12 dst=50 cargo=COAL join_end=B shared_dest=1",
                "[0] OPEX 1971-3-5 RAIL_ATTEMPT src=13 dst=50 ok=1 reason=OK",
                "[0] OPEX 1971-3-5 RAIL_BUILD line=4 src=13 dst=50 cargo=COAL join_end=- shared_dest=0",
            ]
            path = Path(tmp) / "reference_seed42_r0.log.gz"
            with gzip.open(path, "wt") as fp:
                fp.write("\n".join(lines) + "\n")
            builds, n = parse_lines([path])
            sinks, issues = sinks_for_builds(builds)
            self.assertEqual(n["attempts"], 4)
            self.assertEqual(n["builds"], 4)
            self.assertEqual(len(sinks), 2)
            self.assertEqual([len(s["lines"]) for s in sinks], [3, 1])
            self.assertEqual(issues["same_destination_new_stations"], 1)
            total = summarize(sinks)[0]
            self.assertEqual((total["one"], total["two"], total["three"]), (1, 0, 1))
            self.assertEqual(total["median_second_days"], 31)

    def test_unknown_join_flag_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "reference_seed7_r0.log"
            path.write_text("OPEX 1972-1-1 RAIL_ATTEMPT ok=1\n"
                            "OPEX 1972-1-1 RAIL_BUILD line=1 src=4 dst=5 cargo=WOOD shared_dest=1 join_end=A\n")
            with self.assertRaisesRegex(ValueError, "Jointure B"):
                parse_lines([path])


if __name__ == "__main__":
    unittest.main()
