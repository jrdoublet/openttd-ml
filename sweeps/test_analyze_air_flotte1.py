"""Targeted no-game contracts for the AIR-FLOTTE-1 retrospective reader."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sweeps.analyze_air_flotte1 import analyze_log, summarize


def opex(day, name, attrs):
    return f"[log] OPEX {day} {name} {attrs}\n"


class AirFlotte1Test(unittest.TestCase):
    def analyze(self, log):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            path.write_text(log, encoding="utf-8")
            return summarize([analyze_log(path)])

    def test_ranking_after_purchase_is_not_preceding_opportunity(self):
        result = self.analyze(
            opex("1971-3-2", "FLEET_PROJECT",
                 "action=grow line=2 added=1 price=100 profit=10 roi=100 v161_model=50")
            + opex("1971-3-2", "PORTFOLIO_RANK",
                   "rank=0 mode=rail roi=500 rank_score=550 finance_capital=200 src=1 dst=3")
            + "[log] C121_FLEET_MARGINAL line=2 year=1973 added=1 obs_profit=20\n")
        self.assertEqual(result["same_day_air_buy_and_top5_rail"], 1)
        self.assertEqual(result["same_day_best_ranked_rail_roi_gt_fleet"], 1)
        self.assertEqual(result["fleet_with_preceding_rail_rank_same_day"], 0)
        self.assertEqual(result["two_year_air_c121_marginal_proxy_matched"], 1)
        self.assertEqual(result["two_year_air_c121_proxy_roi_median_permille"], 200)
        self.assertIsNone(result["rail_unbuilt_two_year_realized_roi"])

    def test_same_day_preceding_rank_still_not_causal(self):
        result = self.analyze(
            opex("1971-3-2", "PORTFOLIO_RANK",
                 "rank=0 mode=rail roi=200 rank_score=10 finance_capital=200 src=1 dst=3")
            + opex("1971-3-2", "FLEET_PROJECT",
                   "action=grow line=2 added=1 price=100 profit=10 roi=100 v161_model=50")
            + opex("1971-3-2", "V252_REPLACE", "line=3 price=200")
        )
        self.assertEqual(result["fleet_with_preceding_rail_rank_same_day"], 1)
        self.assertEqual(result["renewal_with_preceding_rail_rank_same_day"], 1)
        self.assertFalse(result["contemporaneous_displacement_identified"])

    def test_intervening_renewal_excludes_marginal_proxy(self):
        result = self.analyze(
            opex("1971-3-2", "FLEET_PROJECT",
                 "action=grow line=2 added=1 price=100 profit=10 roi=100 v161_model=50")
            + opex("1972-1-2", "V252_REPLACE", "line=2 price=200")
            + "[log] C121_FLEET_MARGINAL line=2 year=1973 added=1 obs_profit=-15\n")
        self.assertEqual(result["two_year_air_c121_marginal_intervening_renewal_excluded"], 1)
        self.assertEqual(result["two_year_air_c121_marginal_proxy_matched"], 0)

    def test_latest_growth_is_used_and_future_purchase_not_backdated(self):
        result = self.analyze(
            opex("1971-1-2", "FLEET_PROJECT",
                 "action=grow line=2 added=1 price=100 profit=10 roi=100 v161_model=50")
            + opex("1971-6-2", "FLEET_PROJECT",
                   "action=grow line=2 added=1 price=100 profit=30 roi=300 v161_model=50")
            + "[log] C121_FLEET_MARGINAL line=2 year=1973 added=1 obs_profit=20\n"
            + opex("1973-4-2", "FLEET_PROJECT",
                   "action=grow line=2 added=1 price=100 profit=15 roi=150 v161_model=20")
        )
        self.assertEqual(result["two_year_air_c121_marginal_proxy_matched"], 1)
        self.assertEqual(result["two_year_air_c121_proxy_roi_median_permille"], 200)


if __name__ == "__main__":
    unittest.main()
