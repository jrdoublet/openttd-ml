"""Host-only fixtures for descriptive V249 audit; no simulated causal gain."""

from pathlib import Path
import gzip
import tempfile
import unittest

from diag_v249_estime_realise_offline import parse_log, reference_logs, summarize


def event(when, tag, details, company=0):
    return (f"[timestamp] dbg: [script:4] [{company}] [I] "
            f"OPEX {when} {tag} {details}\n")


class V249OfflineAuditTests(unittest.TestCase):
    def test_leading_zero_seed_alias_is_rejected_even_if_contents_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = event("1974-9-7", "V249_STATUE", "town=41 gain=40 cost=120")
            (root / "reference_seed1_r0.log").write_text(content, encoding="utf-8")
            (root / "reference_seed01_r0.log").write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite de partie V249 ambigue"):
                reference_logs(root)

    def test_leading_zero_repeat_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reference_seed1_r0.log").write_text("", encoding="utf-8")
            (root / "reference_seed1_r00.log").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite de partie V249 ambigue"):
                reference_logs(root)

    def test_distinct_numeric_seeds_and_repeats_remain_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ("reference_seed1_r0.log", "reference_seed2_r0.log",
                     "reference_seed1_r1.log")
            for name in names:
                (root / name).write_text("", encoding="utf-8")
            self.assertEqual({p.name for p in reference_logs(root)}, set(names))

    def test_gzip_only_and_duplicate_text_maintain_one_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain = root / "reference_seed42_r0.log"
            compressed = root / (plain.name + ".gz")
            content = event("1974-9-7", "V249_STATUE", "town=41 gain=40 cost=120")
            with gzip.open(compressed, "wt", encoding="utf-8") as stream:
                stream.write(content)
            self.assertEqual(reference_logs(root), [compressed])
            gzip_read = parse_log(compressed)
            self.assertEqual(gzip_read["run"], "seed42_r0")
            self.assertEqual(len(gzip_read["purchases"]), 1)
            plain.write_text(content, encoding="utf-8")
            self.assertEqual(reference_logs(root), [plain])
            self.assertEqual(sum(len(parse_log(log)["purchases"]) for log in reference_logs(root)), 1)

    def test_conflicting_gzip_copy_is_rejected_without_silent_counter_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain = root / "reference_seed42_r0.log"
            compressed = root / (plain.name + ".gz")
            plain.write_text(event("1974-9-7", "V249_STATUE", "town=41 gain=40 cost=120"), encoding="utf-8")
            with gzip.open(compressed, "wt", encoding="utf-8") as stream:
                stream.write(event("1974-9-7", "V249_STATUE", "town=41 gain=41 cost=120"))
            with self.assertRaisesRegex(ValueError, "copies V249 contradictoires"):
                reference_logs(root)

    def parse(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reference_seed42_r0.log"
            path.write_text("".join(lines), encoding="utf-8")
            return parse_log(path)

    def test_quote_is_not_mislabelled_realized_gain(self):
        log = self.parse([
            event("1973-1-2", "AIR_BUILD", "line=8 src_town=41 dst_town=25"),
            event("1974-1-2", "LINE_REVENUE", "line=8 mode=air year=1974 real_prof=100"),
            event("1974-9-7", "V249_STATUE", "town=41 station=3 cargo=PASS rating=60 prod=100 gain=40 cost=120 horizon=5"),
            event("1975-1-2", "LINE_REVENUE", "line=8 mode=air year=1975 real_prof=500"),
            event("1976-1-2", "LINE_REVENUE", "line=8 mode=air year=1976 real_prof=170"),
            event("1976-1-2", "LINE_REVENUE", "line=9 mode=rail year=1976 real_prof=999"),
        ])
        purchase = log["purchases"][0]
        self.assertEqual(purchase["quoted_gain_annual"], 40)
        self.assertEqual(purchase["rating_percent_at_quote"], 60)
        self.assertEqual(purchase["production_last_month_at_quote"], 100)
        self.assertEqual(purchase["quoted_simple_payback_years"], 3)
        self.assertEqual(purchase["air_lines_with_two_snapshots"], 1)
        self.assertEqual(purchase["associated_air_profit_delta_descriptive"], 70)
        self.assertNotIn("realized_statue_gain", purchase)
        self.assertIn("NOT the realized marginal gain", summarize([log])["interpretation"])

    def test_no_post_snapshot_and_wrong_company_are_not_claimed(self):
        log = self.parse([
            event("1974-4-2", "AIR_BUILD", "line=8 src_town=5 dst_town=25"),
            event("1974-9-7", "V249_STATUE", "town=5 station=2 cargo=PASS gain=20 cost=100"),
            event("1975-1-1", "LINE_REVENUE", "line=8 mode=air year=1975 real_prof=300"),
            event("1974-9-7", "V249_STATUE", "town=6 gain=999", company=1),
            event("1974-9-8", "V249_SKIP", "reason=loan loan=200000"),
        ])
        self.assertEqual(len(log["purchases"]), 1)
        self.assertEqual(log["skipped"], {"loan": 1})
        self.assertEqual(log["purchases"][0]["associated_air_profit_delta_descriptive"], None)
        self.assertEqual(summarize([log])["with_descriptive_air_profit_proxy"], 0)

    def test_future_builds_cannot_be_attributed_to_past_statues(self):
        log = self.parse([
            event("1974-9-7", "V249_STATUE", "town=41 gain=40 cost=120"),
            event("1975-2-1", "AIR_BUILD", "line=7 src_town=41 dst_town=25"),
            event("1974-2-1", "LINE_REVENUE", "line=7 mode=air year=1974 real_prof=10"),
            event("1976-2-1", "LINE_REVENUE", "line=7 mode=air year=1976 real_prof=100"),
        ])
        self.assertEqual(log["purchases"][0]["air_lines_associated"], 0)


if __name__ == "__main__":
    unittest.main()
