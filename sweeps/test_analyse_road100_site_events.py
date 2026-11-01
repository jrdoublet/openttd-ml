import tempfile
import unittest
from pathlib import Path

from analyse_road100_site_events import as_markdown, parse_campaign, parse_log


class Road100SiteEventsTests(unittest.TestCase):
    def test_admit_does_not_mean_build_and_missing_is_null(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "variant_seed42_r0.log"
            path.write_text(
                "[time] [I] OPEX 1970-1-5 ROAD100_SITE_FIRST phase=admit src=11 dst=22 monthly=21 profit=75\n"
                "[time] [I] OPEX 1970-1-6 ROAD100_SITE_FIRST phase=summary plans=3 accepted=1 ops=2500000\n"
                "[time] [I] OPEX 1970-2-1 ROAD_BUILD line=0 src=90 dst=91 cargo=PASS cost=10000 profit=500 vehicles=1\n"
                "[time] [I] OPEX 1970-2-2 PROJECT_DISCARD rank=0 src=11 dst=22 reason=build_failed detail=BSTOP error=260\n",
                encoding="utf-8")
            report = parse_log(path)
            self.assertEqual(report["admission_events"], 1)
            self.assertEqual(report["passenger_build_events"], 1)
            self.assertEqual(report["matched_passenger_build_events"], 0)
            self.assertEqual(report["site_summary_last"]["ops"], 2500000)
            self.assertEqual(report["refusals"]["build_failed/BSTOP"], 1)
            self.assertFalse(report["has_realized_line_revenue"])
            self.assertIn("non", as_markdown({"logs": [report]}))

    def test_duplicate_events_and_missing_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "reference_seed100_r0.log"
            file.write_text(
                "[I] OPEX 1970-1-1 ROAD_BUILD line=0 src=1 dst=2 cargo=COAL cost=9 vehicles=2\n"
                "[I] OPEX 1970-1-5 ROAD_BUILD line=1 src=3 dst=4 cargo=PASS cost=19 vehicles=1\n"
                "[I] OPEX 1970-1-6 ROAD_BUILD line=2 src=3 dst=4 cargo=PASS cost=19 vehicles=1\n",
                encoding="utf-8")
            parsed = parse_campaign(Path(directory))["logs"][0]
            self.assertIsNone(parsed["site_summary_last"])
            self.assertEqual(parsed["admission_events"], 0)
            self.assertEqual(parsed["passenger_build_events"], 2)
            self.assertEqual(parsed["matched_passenger_build_events"], 0)

    def test_joined_satellite_and_reprice_are_separate_events(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "variant_seed7_r0.log"
            file.write_text(
                "[I] OPEX 1970-2-1 ROAD100_JOINED_STOP end=A station=9 tile=77 cover_marginal=26 cost=440 ops=12345 reason=OK\n"
                "[I] OPEX 1970-2-1 ROAD100_REPRICE src=1 dst=2 gen_capital=8200 live_capital=8100 actual_paid=9900 game_cash=190000 gen_profit=800 live_profit=810 bought=1 ok=1\n",
                encoding="utf-8")
            parsed = parse_log(file)
            self.assertEqual(parsed["event_counts"]["ROAD100_JOINED_STOP"], 1)
            self.assertEqual(parsed["reprice_events"], 1)
            self.assertEqual(parsed["records"][0]["fields"]["cover_marginal"], 26)
            self.assertIsNone(parsed["site_summary_last"])


if __name__ == "__main__":
    unittest.main()
