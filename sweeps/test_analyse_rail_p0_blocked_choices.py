"""Observational rail blocker joins: reject absent or ambiguous identities."""
import unittest

from analyse_rail_p0_blocked_choices import process_log, compact_rows


class BlockedProjectsTest(unittest.TestCase):
    def test_strict_early_join_and_duplicate_visits(self):
        lines = [
            "OPEX 1973-7-31 PORTFOLIO_RANK rank=0 mode=rail kind=freight cargo=GOOD src=100 dst=200 rank_score=201 finance_capital=50000 profit=90000",
            "OPEX 1973-7-31 RAIL_AUDIT stage=early kind=freight cargo=GOOD src=100 dst=200 reason=search_in_progress ok=0 actual=0 ops=0 rank=1",
            "OPEX 1973-7-31 RAIL_BLOCKER requested_kind=freight requested_src=100 requested_dst=200 blocker=upgrade phase=search src=-1 dst=-1 spent=1200 budget=10000 fund_score=210 pred_profit=90000 budget_capital=50000 destination=town",
            "OPEX 1973-8-1 RAIL_AUDIT stage=early kind=freight cargo=GOOD src=100 dst=200 reason=search_in_progress rank=2",
            "OPEX 1973-8-1 RAIL_BLOCKER requested_kind=freight requested_src=100 requested_dst=200 blocker=upgrade phase=search src=-1 dst=-1 spent=1400 budget=10000",
            "OPEX 1974-1-2 RAIL_BUILD line=3 src=100 dst=200 cargo=GOOD cost=52000",
        ]
        result = process_log(lines)
        self.assertEqual(result["annual"]["1973"]["blocker_visits"], 2)
        self.assertEqual(result["annual"]["1973"]["distinct_kind_cargo_od"], 1)
        self.assertEqual(result["annual"]["1973"]["rank_score_same_day_observed"], 1)
        self.assertEqual(result["annual"]["1973"]["score_and_profit_at_block_observed"], 1)
        self.assertEqual(result["annual"]["1973"]["blocked_destination/town"], 1)
        row = result["first_blocked_per_kind_cargo_od"][0]
        self.assertEqual(row["later_build_status"], "one_possible_pair_match")
        self.assertEqual(row["score_at_same_day"]["rank_score"], "201")
        self.assertEqual(row["score_at_block"], "210")
        self.assertFalse(row["same_od_as_primary_search"])

    def test_unmatched_and_same_day_ambiguous_rank(self):
        lines = [
            "OPEX 1974-1-1 RAIL_AUDIT stage=early kind=freight cargo=COAL src=10 dst=20 reason=search_in_progress rank=0",
            "OPEX 1974-1-1 RAIL_BLOCKER requested_kind=freight requested_src=10 requested_dst=21 blocker=primary phase=search src=20 dst=30",
            "OPEX 1974-1-2 PORTFOLIO_RANK rank=0 mode=rail kind=freight cargo=COAL src=10 dst=20 rank_score=90",
            "OPEX 1974-1-2 PORTFOLIO_RANK rank=1 mode=rail kind=freight cargo=COAL src=10 dst=20 rank_score=80",
            "OPEX 1974-1-2 RAIL_AUDIT stage=early kind=freight cargo=COAL src=10 dst=20 reason=search_in_progress rank=0",
            "OPEX 1974-1-2 RAIL_BLOCKER requested_kind=freight requested_src=10 requested_dst=20 blocker=primary phase=search src=20 dst=30",
        ]
        result = process_log(lines)
        self.assertEqual(result["coverage"]["unmatched_early"], 1)
        self.assertEqual(result["coverage"]["ambiguous_same_day_rank"], 1)
        self.assertIsNone(result["blocked_visits"][0]["cargo"])
        self.assertEqual(result["blocked_visits"][1]["score_match_status"], "ambiguous")

    def test_nonadjacent_early_rejected(self):
        lines = [
            "OPEX 1973-1-1 RAIL_AUDIT stage=early kind=freight cargo=COAL src=10 dst=20 reason=search_in_progress",
            "OPEX 1973-1-1 PORTFOLIO_RANK rank=0 mode=rail kind=freight cargo=COAL src=10 dst=20",
            "OPEX 1973-1-1 RAIL_BLOCKER requested_kind=freight requested_src=10 requested_dst=20 blocker=upgrade",
        ]
        result = process_log(lines)
        self.assertEqual(result["coverage"]["unmatched_early"], 1)

    def test_same_pair_revisit_is_not_a_distinct_queued_opportunity(self):
        result = process_log([
            "OPEX 1973-2-1 RAIL_AUDIT stage=early kind=freight cargo=COAL src=10 dst=20 reason=search_in_progress rank=0",
            "OPEX 1973-2-1 RAIL_BLOCKER requested_kind=freight requested_src=10 requested_dst=20 blocker=primary phase=search src=10 dst=20 fund_score=12 pred_profit=3000 destination=industry",
        ])
        self.assertEqual(result["annual"]["1973"]["self_pair_revisits"], 1)
        run = {**result, "seed": 42, "repeat": 0, "arm": "on"}
        report = {"runs": [run]}
        row = list(compact_rows(report))[0]
        self.assertEqual(row["visits"], 1)
        self.assertEqual(row["distinct_od"], 0)
        self.assertEqual(row["same_od_visits"], 1)

    def test_no_rail_build_tag_does_not_mean_no_construction(self):
        result = process_log([
            "OPEX 1973-2-1 RAIL_AUDIT stage=early kind=freight cargo=COAL src=10 dst=20 reason=search_in_progress rank=0",
            "OPEX 1973-2-1 RAIL_BLOCKER requested_kind=freight requested_src=10 requested_dst=20 blocker=upgrade phase=search src=-1 dst=-1 fund_score=12 pred_profit=3000",
            "OPEX 1974-3-5 RAIL_PREASTAR_BUILD rid=123_4 reason=OK ok=1 status=built",
        ])
        self.assertEqual(result["first_blocked_per_kind_cargo_od"][0]["later_build_status"],
                         "none_rail_build_tag_observed")


if __name__ == "__main__":
    unittest.main()
