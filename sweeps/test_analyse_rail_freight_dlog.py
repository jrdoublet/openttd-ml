import unittest

from analyse_rail_freight_dlog import count_log, decode_line


class RailFreightLogTests(unittest.TestCase):
    def test_decode_and_split_freight_passenger(self):
        rows = [
            "[now] dbg OPEX 1973-1-8 VIVIER_GEN mode=rail produced=50 kept=10\n",
            "[now] dbg OPEX 1973-1-8 RAIL_PREPAIR generate_pax=1 generate_freight=1 freight_cargo=4 target_kind=none freight_ind_pairs=12 freight_town_pairs=6 freight_town_zero_monthly=3\n",
            "[now] dbg OPEX 1973-1-8 VIVIER_REJECT reason=origin_served n=5\n",
            "[now] dbg OPEX 1973-1-8 VIVIER_GEN mode=rail produced=50 kept=0\n",
            "[now] dbg OPEX 1973-1-9 PORTFOLIO_RANK rank=1 mode=rail kind=freight cargo=GRAI src=10 dst=20 rank_score=1\n",
            "[now] dbg OPEX 1973-1-10 PORTFOLIO_RANK rank=2 mode=rail kind=freight cargo=GRAI src=10 dst=20 rank_score=1\n",
            "[now] dbg OPEX 1973-1-10 PORTFOLIO_RANK rank=0 mode=rail kind=pax cargo=PASS src=40 dst=50\n",
            "[now] dbg OPEX 1973-1-11 PROJECT_CHOSEN rank=1 mode=rail kind=freight cargo=GRAI src=10 dst=20\n",
            "[now] dbg OPEX 1973-1-12 RAIL_ATTEMPT kind=freight reason=ABND iters=10000\n",
            "[now] dbg OPEX 1973-1-12 RAIL_ATTEMPT kind=pax reason=OK iters=100\n",
            "[now] dbg RAIL_FREIGHT_SELECT_SHADOW year=1973 month=1 total_f=4 cash_f=1 floor_f=1 eligible_f=2 selected_f=0 head_mode=air head_tier=2\n",
            "[now] dbg RAIL_FREIGHT_SELECT_SHADOW year=1973 month=1 total_f=1 cash_f=0 floor_f=0 eligible_f=1 selected_f=1 head_mode=air head_tier=1\n",
            "non-OPEX line\n",
        ]
        by_year = count_log(rows)
        y = by_year["1973"]
        self.assertEqual(y["rail_generation_calls"], 2)
        self.assertEqual(y["rail_generation_empty_calls"], 1)
        self.assertEqual(y["distinct_ranked_rail_pairs_by_kind"]["freight"], 1)
        self.assertEqual(y["ranked_top5_occurrences"]["rail/freight"], 2)
        self.assertEqual(y["chosen_occurrences"]["rail/freight"], 1)
        self.assertEqual(y["rail_attempt_occurrences"]["freight/ABND"], 1)
        self.assertEqual(y["rail_attempt_occurrences"]["pax/OK"], 1)
        self.assertEqual(y["rail_generation_details"][0]["freight_town_pairs"], 6)
        self.assertEqual(y["rail_generation_details"][0]["rejects"]["origin_served"], 5)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_but_none_selected_calls"], 1)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_head_defensive_air_calls"], 1)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_calls"], 2)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_head_modes"]["air"], 2)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_head_defensive_air_any_calls"], 2)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_selected_calls"], 1)
        self.assertEqual(y["freight_select_shadow"]["eligible_freight_head_air_score_unknown_calls"], 2)

    def test_air_head_can_have_lower_score_than_freight(self):
        rows = [
            "RAIL_FREIGHT_SELECT_SHADOW year=1975 month=4 eligible_f=3 selected_f=1 head_mode=air head_tier=0 head_score=20.1 best_f_score=21.5\n",
            "RAIL_FREIGHT_SELECT_SHADOW year=1975 month=5 eligible_f=2 selected_f=1 head_mode=air head_tier=0 head_score=21.5 best_f_score=21.5\n",
        ]
        stats = count_log(rows)["1975"]["freight_select_shadow"]
        self.assertEqual(stats["eligible_freight_head_air_score_below_freight_calls"], 1)
        self.assertEqual(stats["eligible_freight_head_air_score_at_least_freight_calls"], 1)
        self.assertEqual(stats["eligible_freight_head_air_score_unknown_calls"], 0)

    def test_no_greedy_match_on_malformed_dates(self):
        self.assertIsNone(decode_line("OPEX yesterday RAIL_ATTEMPT kind=freight"))
        self.assertIsNone(decode_line("SOME_OTHER_LOG 1974-1-1 mode=rail"))


if __name__ == "__main__":
    unittest.main()
