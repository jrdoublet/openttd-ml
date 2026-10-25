"""V252 annual follow-up is coverage, not a post hoc causal ROI."""

import gzip
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_air_renewal_coverage import audit, directory_report


def e(date, tag, data):
    return f"[script:4] [0] [I] OPEX {date} {tag} {data}\n"


class RenewalCoverageTests(unittest.TestCase):
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
