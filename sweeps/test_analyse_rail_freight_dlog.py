import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from analyse_rail_freight_dlog import count_log, decode_line, main


class RailFreightLogTests(unittest.TestCase):
    def report(self, *files):
        output = io.StringIO()
        with patch.object(sys, "argv", ["analyse_rail_freight_dlog.py", *(str(p) for p in files)]):
            with contextlib.redirect_stdout(output):
                main()
        return json.loads(output.getvalue())

    def test_independent_campaigns_with_same_basename_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            a, b = base / "solo", base / "duel"
            a.mkdir()
            b.mkdir()
            left, right = a / "reference_seed42_r0.log", b / "reference_seed42_r0.log"
            left.write_text("OPEX 1972-1-1 VIVIER_GEN mode=rail produced=10 kept=3\n", encoding="utf-8")
            right.write_text("OPEX 1972-1-1 VIVIER_GEN mode=rail produced=20 kept=4\n", encoding="utf-8")
            result = self.report(left, right)
            self.assertEqual(set(result["logs"]), {str(left.resolve()), str(right.resolve())})
            self.assertEqual(result["logs"][str(left.resolve())]["1972"]["rail_generated_pairs_examined_sum"], 10)
            self.assertEqual(result["logs"][str(right.resolve())]["1972"]["rail_generated_pairs_examined_sum"], 20)
            self.assertEqual(result["log_basenames"][str(left.resolve())], left.name)
            self.assertEqual(result["log_basenames"][str(right.resolve())], right.name)

    def test_campaign_result_is_independent_of_input_order(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            a, b = base / "solo", base / "duel"
            a.mkdir()
            b.mkdir()
            left, right = a / "reference_seed42_r0.log", b / "reference_seed42_r0.log"
            left.write_text("OPEX 1972-1-1 VIVIER_GEN mode=rail produced=12 kept=3\n", encoding="utf-8")
            right.write_text("OPEX 1972-1-1 VIVIER_GEN mode=rail produced=30 kept=7\n", encoding="utf-8")
            self.assertEqual(self.report(left, right), self.report(right, left))

    def test_repeated_physical_path_collapses_but_distinct_names_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "reference_seed42_r0.log", root / "reference_seed42_r1.log"
            content = "OPEX 1972-1-1 VIVIER_GEN mode=rail produced=15 kept=5\n"
            a.write_text(content, encoding="utf-8")
            b.write_text(content, encoding="utf-8")
            got = self.report(a, a, b, a.resolve())
            self.assertEqual(set(got["logs"]), {str(a.resolve()), str(b.resolve())})
            self.assertEqual(len(got["log_basenames"]), 2)

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

    def test_rail_rejects_on_following_day_still_belong_to_same_generation(self):
        rows = [
            "OPEX 1970-2-5 VIVIER_GEN mode=rail produced=1295 kept=142\n",
            "OPEX 1970-2-5 VIVIER_REJECT reason=no_monthly n=18\n",
            "OPEX 1970-2-5 VIVIER_REJECT reason=distance_long n=41\n",
            "OPEX 1970-2-6 VIVIER_REJECT reason=profit_non_positive n=392\n",
            "OPEX 1970-2-6 VIVIER_REJECT reason=ratio_too_low n=247\n",
        ]
        year = count_log(rows)["1970"]
        self.assertEqual(year["rail_generation_details"][0]["rejects"], {
            "no_monthly": 18, "distance_long": 41,
            "profit_non_positive": 392, "ratio_too_low": 247,
        })
        self.assertEqual(sum(year["rail_reject_occurrences"].values()), 698)

    def test_other_mode_generation_ends_rail_reject_attribution(self):
        rows = [
            "OPEX 1972-3-1 VIVIER_GEN mode=rail produced=10 kept=2\n",
            "OPEX 1972-3-2 VIVIER_GEN mode=road produced=9 kept=1\n",
            "OPEX 1972-3-2 VIVIER_REJECT reason=road_site n=99\n",
            "OPEX 1972-3-3 VIVIER_GEN mode=rail produced=8 kept=2\n",
            "OPEX 1972-3-4 VIVIER_REJECT reason=rail_site n=5\n",
        ]
        year = count_log(rows)["1972"]
        first, second = year["rail_generation_details"]
        self.assertEqual(first["rejects"], {})
        self.assertEqual(second["rejects"], {"rail_site": 5})
        self.assertEqual(year["rail_reject_occurrences"], {"road_site": 99, "rail_site": 5})

    def test_two_rail_generations_keep_separate_rejects_across_years(self):
        rows = [
            "OPEX 1974-12-31 VIVIER_GEN mode=rail produced=40 kept=5\n",
            "OPEX 1975-1-1 VIVIER_REJECT reason=late n=7\n",
            "OPEX 1975-1-1 VIVIER_GEN mode=rail produced=20 kept=2\n",
            "OPEX 1975-1-2 VIVIER_REJECT reason=fresh n=3\n",
        ]
        report = count_log(rows)
        self.assertEqual(report["1974"]["rail_generation_details"][0]["rejects"], {"late": 7})
        self.assertEqual(report["1975"]["rail_generation_details"][0]["rejects"], {"fresh": 3})
        self.assertEqual(report["1975"]["rail_reject_occurrences"], {"late": 7, "fresh": 3})


if __name__ == "__main__":
    unittest.main()
