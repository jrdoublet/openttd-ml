"""V262 T10/T15: preserve game identity and missing data in orphan reports.

Synthetic logs only: these contracts do not establish probe exposure or an
economic result. Maintenance covers the whole company, not just orphan assets.
"""
from contextlib import redirect_stdout
import gzip
import io
from pathlib import Path
import sys
import tempfile
import unittest


SWEEPS = Path(__file__).resolve().parent
if str(SWEEPS) not in sys.path:
    sys.path.insert(0, str(SWEEPS))

import analyze_v262_orphans as analyzer


PREFIX = "dbg: [script:4] [0] [I] OPEX "
TRAIN = (PREFIX + "1972-12-1 V262_ORPHAN_STATION station=4 train=1 truck=0 "
         "bus=0 airport=0 dock=0 age=400 built=100 in_lines=0\n")
BUS = (PREFIX + "1972-12-1 V262_ORPHAN_STATION station=4 train=0 truck=0 "
       "bus=1 airport=0 dock=0 age=200 built=300 in_lines=1\n")
AIRPORT_DOCK = (PREFIX + "1972-12-1 V262_ORPHAN_STATION station=4 train=0 "
                "truck=0 bus=0 airport=1 dock=1 age=-1 built=-1 in_lines=0\n")
SUMMARY = (PREFIX + "1972-12-1 V262_ORPHAN_SUM year=1972 timekeeping=0 maint=1 "
           "orphan_n=1 cost_rail=11 cost_signals=2 cost_road=3 cost_canal=4 "
           "cost_station=5 cost_airport=6\n")
ZERO_SUMMARY = (PREFIX + "1973-12-1 V262_ORPHAN_SUM year=1973 timekeeping=0 "
                "maint=0 orphan_n=0 cost_rail=0 cost_signals=0 cost_road=0 "
                "cost_canal=0 cost_station=0 cost_airport=0\n")


class OrphanReportContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_log(self, name, content):
        path = self.root / name
        if name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def report(self):
        output = io.StringIO()
        with redirect_stdout(output):
            analyzer.main([str(self.root)])
        return output.getvalue()

    def test_same_seed_arms_and_repetitions_keep_separate_station_maps(self):
        # Reusing the same StationID and year across games must not merge them.
        logs = {
            "reference_seed42_r0.log": TRAIN + SUMMARY,
            "variant_seed42_r0.log.gz": BUS + SUMMARY,
            "reference_seed42_r1.log": AIRPORT_DOCK + SUMMARY,
        }
        for name, content in logs.items():
            self.write_log(name, content)
        self.write_log("notes.log", TRAIN + SUMMARY)
        self.write_log("reference_seed42_r0.log.bak", TRAIN + SUMMARY)

        paths = analyzer.log_paths(str(self.root))
        self.assertEqual({Path(path).name for path in paths}, set(logs))
        grouped = analyzer.games_by_seed(paths)
        self.assertEqual(set(grouped), {42})
        games = dict(grouped[42])
        self.assertEqual(set(games), set(logs))
        expected = {
            "reference_seed42_r0.log": (1, 0, 0, 0, 0),
            "variant_seed42_r0.log.gz": (0, 0, 1, 0, 0),
            "reference_seed42_r1.log": (0, 0, 0, 1, 1),
        }
        for name, flags in expected.items():
            with self.subTest(log=name):
                bucket = games[name][1972]
                self.assertEqual(set(bucket["stations"]), {4})
                self.assertEqual(analyzer.orphans_by_type(bucket), dict(zip(
                    ("train", "truck", "bus", "airport", "dock"), flags)))

        report = self.report()
        self.assertEqual(report.count("## graine 42 — "), 3)
        for name in logs:
            self.assertIn(f"## graine 42 — `{name}`", report)
        self.assertEqual(report.count("| 1972 |"), 3)

    def test_reload_uses_last_summary_without_counting_facilities_as_stations(self):
        # A reload can repeat the survey. The last station and SUM rows win;
        # one station with two facilities is still one physical orphan.
        replacement = SUMMARY.replace("cost_rail=11", "cost_rail=21")
        path = self.write_log("reference_seed7_r0.log.gz",
                              TRAIN + SUMMARY + AIRPORT_DOCK + replacement)

        years = analyzer.parse_log(str(path))
        self.assertEqual(set(years), {1972})
        self.assertEqual(len(years[1972]["stations"]), 1)
        self.assertEqual(years[1972]["sum"]["orphan_n"], 1)
        self.assertEqual(analyzer.total_maintenance(years[1972]["sum"]), 41)
        rows = [line for line in self.report().splitlines()
                if line.startswith("| 1972 |")]
        self.assertEqual(rows, ["| 1972 | 0 | 0 | 0 | 1 | 1 | 1 | 41 | 1 |"])

    def test_report_distinguishes_missing_summary_from_measured_zero(self):
        self.write_log("reference_seed100_r0.log", TRAIN + ZERO_SUMMARY)

        grouped = analyzer.games_by_seed(analyzer.log_paths(str(self.root)))
        years = grouped[100][0][1]
        self.assertIsNone(years[1972]["sum"])
        self.assertIsNone(analyzer.total_maintenance(years[1972]["sum"]))
        self.assertEqual(analyzer.total_maintenance(years[1973]["sum"]), 0)
        report = self.report()
        self.assertIn("| 1972 | 1 | 0 | 0 | 0 | 0 | 1 | None | — |", report)
        self.assertIn("| 1973 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |", report)


if __name__ == "__main__":
    unittest.main()
