"""V252 annual follow-up is coverage, not a post hoc causal ROI."""

import gzip
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_air_renewal_coverage import audit, directory_report


def e(date, tag, data):
    return f"[script:4] [0] [I] OPEX {date} {tag} {data}\n"


class RenewalCoverageTests(unittest.TestCase):
    def test_numeric_seed_aliases_are_rejected_even_when_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = e("1974-9-8", "V252_REPLACE", "line=3 old_veh=40 new_veh=416 price=153808")
            (root / "reference_seed1_r0.log").write_text(content, encoding="utf-8")
            (root / "reference_seed01_r0.log").write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite de partie V252 ambigue"):
                directory_report(root)

    def test_numeric_repeat_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reference_seed42_r0.log").write_text("", encoding="utf-8")
            (root / "reference_seed42_r00.log").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite de partie V252 ambigue"):
                directory_report(root)

    def test_distinct_arms_seeds_repeats_are_not_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ("reference_seed42_r0.log", "variant_seed42_r0.log",
                     "reference_seed7_r0.log", "reference_seed42_r1.log")
            for name in names:
                (root / name).write_text("", encoding="utf-8")
            self.assertEqual(directory_report(root)["games"], len(names))

    def test_follow_up_strictly_after_replacement_and_mature(self):
        rows = [
            e("1974-9-8", "V252_REPLACE", "line=3 old_veh=40 new_veh=416 price=153808 profit=37890"),
            e("1974-9-9", "V252_SKIP", "reason=cash_stop"),
            e("1974-12-1", "LINE_REVENUE", "mode=air line=3 age=1 year=1974 real_prof=100"),
            e("1975-1-5", "LINE_REVENUE", "mode=air line=3 age=2 year=1975 real_prof=120"),
        ]
        result = audit(rows)
        self.assertEqual(result["replace_events"], 1)
        self.assertEqual(result["purchase_price_reported"], 1)
        self.assertEqual(result["skip_cash_stop"], 1)
        self.assertEqual(result["events_with_later_mature_line_report"], 1)
        self.assertEqual(result["observed_net_purchase_minus_sale_cost"], 0)

    def test_no_future_report_and_intervening_v252(self):
        rows = [
            e("1974-1-1", "V252_REPLACE", "line=3 old_veh=40 new_veh=41 price=100 profit=50"),
            e("1974-6-1", "V252_REPLACE", "line=3 old_veh=41 new_veh=42 price=100 profit=50"),
            e("1975-1-1", "LINE_REVENUE", "mode=air line=3 age=3 year=1975 real_prof=999"),
            e("1979-12-1", "V252_REPLACE", "line=4 old_veh=4 new_veh=5 price=100 profit=50"),
        ]
        result = audit(rows)
        self.assertEqual(result["events_with_later_mature_line_report"], 2)
        self.assertEqual(result["events_with_intervening_v252"], 1)
        self.assertEqual(result["events_without_later_mature_line_report"], 1)

    def test_invalid_line_id_cannot_claim_mature_followup(self):
        rows = [
            e("1974-9-8", "V252_REPLACE", "line=oops old_veh=40 new_veh=41 price=100"),
            e("1975-1-1", "LINE_REVENUE", "mode=air line=oops year=1975 age=2 real_prof=100"),
        ]
        result = audit(rows)
        self.assertEqual(result["replace_events"], 1)
        self.assertEqual(result["incomplete_identity"], 1)
        self.assertEqual(result["invalid_mature_line_id"], 1)
        self.assertEqual(result.get("events_with_later_mature_line_report", 0), 0)
        self.assertEqual(result["events_without_later_mature_line_report"], 1)

    def test_fractional_year_cannot_prove_annual_followup(self):
        prefix = [e("1974-9-8", "V252_REPLACE", "line=3 old_veh=40 new_veh=41 price=100")]
        invalid = audit(prefix + [
            e("1975-1-1", "LINE_REVENUE", "mode=air line=3 year=1975.75 age=2 real_prof=100"),
        ])
        self.assertEqual(invalid["invalid_mature_revenue_year"], 1)
        self.assertEqual(invalid.get("events_with_later_mature_line_report", 0), 0)
        self.assertEqual(invalid["events_without_later_mature_line_report"], 1)
        valid = audit(prefix + [
            e("1975-1-1", "LINE_REVENUE", "mode=air line=3 year=1975.0 age=2 real_prof=100"),
        ])
        self.assertEqual(valid["events_with_later_mature_line_report"], 1)
        self.assertEqual(valid.get("invalid_mature_revenue_year", 0), 0)

    def test_noncanonical_line_alias_does_not_create_extra_replacement_cohort(self):
        rows = [
            e("1974-9-8", "V252_REPLACE", "line=01 old_veh=40 new_veh=41 price=100"),
            e("1974-9-8", "V252_REPLACE", "line=1 old_veh=42 new_veh=43 price=100"),
            e("1975-1-1", "LINE_REVENUE", "mode=air line=01 year=1975 age=2 real_prof=100"),
            e("1975-1-1", "LINE_REVENUE", "mode=air line=1 year=1975 age=2 real_prof=100"),
        ]
        result = audit(rows)
        self.assertEqual(result["incomplete_identity"], 1)
        self.assertEqual(result["invalid_mature_line_id"], 1)
        self.assertEqual(result["events_without_later_mature_line_report"], 1)
        self.assertEqual(result["events_with_later_mature_line_report"], 1)

    def test_line_zero_and_integer_year_remain_valid(self):
        rows = [
            e("1974-9-8", "V252_REPLACE", "line=0 old_veh=40 new_veh=41 price=100"),
            e("1975-1-1", "LINE_REVENUE", "mode=air line=0 year=1975 age=2 real_prof=100"),
        ]
        self.assertEqual(audit(rows)["events_with_later_mature_line_report"], 1)

    def test_later_published_report_can_cover_only_pre_replacement_year(self):
        rows = [
            e("1979-1-10", "V252_REPLACE", "line=74 old_veh=4 new_veh=5 price=100"),
            e("1979-2-4", "LINE_REVENUE", "mode=air line=74 year=1979 age=2 real_prof=100"),
        ]
        result = audit(rows)
        self.assertEqual(result["events_with_later_mature_line_report"], 1)
        self.assertEqual(result["events_with_published_later_only_pre_purchase_period"], 1)
        self.assertEqual(result.get("events_with_any_profit_period_after_purchase", 0), 0)
        self.assertEqual(result.get("events_with_full_calendar_year_after_purchase", 0), 0)

    def test_followup_measuring_purchase_year_is_only_partially_post(self):
        rows = [
            e("1974-9-8", "V252_REPLACE", "line=3 old_veh=4 new_veh=5 price=100"),
            e("1975-2-1", "LINE_REVENUE", "mode=air line=3 year=1975 age=2 real_prof=100"),
        ]
        result = audit(rows)
        self.assertEqual(result["events_with_later_mature_line_report"], 1)
        self.assertEqual(result["events_with_any_profit_period_after_purchase"], 1)
        self.assertEqual(result["events_with_later_partial_post_period_only"], 1)
        self.assertEqual(result.get("events_with_full_calendar_year_after_purchase", 0), 0)
        self.assertEqual(result["events_without_full_calendar_year_after_purchase"], 1)

    def test_intervening_replacement_before_first_full_post_year_is_distinct(self):
        rows = [
            e("1973-7-2", "V252_REPLACE", "line=3 old_veh=4 new_veh=5 price=100"),
            e("1974-1-5", "LINE_REVENUE", "mode=air line=3 year=1974 age=2 real_prof=100"),
            e("1974-6-3", "V252_REPLACE", "line=3 old_veh=5 new_veh=6 price=100"),
            e("1975-1-5", "LINE_REVENUE", "mode=air line=3 year=1975 age=3 real_prof=120"),
            e("1976-1-5", "LINE_REVENUE", "mode=air line=3 year=1976 age=4 real_prof=130"),
        ]
        result = audit(rows)
        self.assertEqual(result["events_with_later_mature_line_report"], 2)
        self.assertEqual(result.get("events_with_intervening_v252", 0), 0)
        self.assertEqual(result["events_with_full_calendar_year_after_purchase"], 2)
        self.assertEqual(result["events_with_intervening_v252_before_full_calendar_year"], 1)


    def test_copy_log_gzip_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = e("1974-1-1", "V252_REPLACE", "line=3 old_veh=4 new_veh=5 price=100")
            (root / "reference_seed42_r0.log").write_text(text, encoding="utf-8")
            with gzip.open(root / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as stream:
                stream.write(text)
            self.assertEqual(directory_report(root)["games"], 1)
            with gzip.open(root / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as stream:
                stream.write(text.replace("price=100", "price=120"))
            with self.assertRaisesRegex(ValueError, "copies V252 contradictoires"):
                directory_report(root)


if __name__ == "__main__":
    unittest.main()
