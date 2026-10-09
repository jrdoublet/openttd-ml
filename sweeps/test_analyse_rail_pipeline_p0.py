"""Contrats d'identité et de dénominateur du funnel rail observationnel."""
import unittest

from analyse_rail_pipeline_p0 import parse_diagnostic_log
from analyse_rail_preastar import parse_lines as parse_rid_lines


class PipelineIdentityTests(unittest.TestCase):
    def test_revisits_are_not_independent_projects(self):
        events = [
            "OPEX 1974-2-1 PROJECT_CHOSEN rank=0 mode=rail kind=freight cargo=COAL src=100 dst=200 cost=40000 profit=12000",
            "OPEX 1974-2-2 PROJECT_CHOSEN rank=0 mode=rail kind=freight cargo=COAL src=100 dst=200 cost=40000 profit=12000",
            "OPEX 1974-2-3 PROJECT_CHOSEN rank=0 mode=rail kind=freight cargo=IORE src=100 dst=200 cost=40000 profit=14000",
        ]
        rows = parse_diagnostic_log(events)["by_year_kind_cargo_destination"]
        self.assertEqual(rows["1974/freight/COAL/destination_unknown"]["chosen/visits"], 2)
        self.assertEqual(rows["1974/freight/COAL/destination_unknown"]["chosen/distinct_od"], 1)
        self.assertEqual(rows["1974/freight/IORE/destination_unknown"]["chosen/distinct_od"], 1)

    def test_missing_cargo_never_joins_attempt_to_chosen(self):
        events = [
            "OPEX 1975-1-2 PROJECT_CHOSEN rank=0 mode=rail kind=freight cargo=COAL src=100 dst=200 cost=40000 profit=12000",
            "OPEX 1975-2-2 RAIL_ATTEMPT src=100 dst=200 kind=freight reason=TRKFAIL actual=5500 ops=10000",
            "OPEX 1975-2-3 RAIL_AUDIT stage=attempt kind=freight cargo=COAL src=100 dst=200 reason=TRKFAIL ok=0 actual=500 ops=9000",
        ]
        result = parse_diagnostic_log(events)
        grouped = result["by_year_kind_cargo_destination"]
        self.assertEqual(grouped["1975/freight/unknown/destination_unknown"]["attempt_no_cargo/distinct_od"], 1)
        self.assertEqual(grouped["1975/freight/COAL/destination_unknown"]["audit_attempt/distinct_od"], 1)
        self.assertEqual(result["annual"]["1975"]["audit_attempt_actual_gbp"], 500)
        self.assertEqual(result["annual"]["1975"]["audit_attempt_opcodes"], 9000)

    def test_selection_is_aggregate_reselection_not_unique_candidates(self):
        sample = [
            "RAIL_FREIGHT_SELECT_SHADOW year=1974 month=4 budget=500000 total_f=2 cash_f=0 floor_f=0 eligible_f=2 selected_f=0 town_f=1 eligible_town_f=1 selected_town_f=0 head_mode=air",
            "RAIL_FREIGHT_SELECT_SHADOW year=1974 month=4 budget=500000 total_f=2 cash_f=0 floor_f=0 eligible_f=2 selected_f=0 town_f=1 eligible_town_f=1 selected_town_f=0 head_mode=air",
            "OPEX 1974-5-7 RAIL_PREPAIR freight_ind_pairs=20 freight_town_pairs=30 freight_town_zero_monthly=29",
        ]
        result = parse_diagnostic_log(sample)["annual"]["1974"]
        self.assertEqual(result["select/eligible_f"], 4)
        self.assertEqual(result["select/calls_eligible_but_not_selected"], 2)
        self.assertEqual(result["prepair/freight_town_pairs"], 30)

    def test_pax_pair_is_numerically_canonical(self):
        lines = [
            "OPEX 1972-1-1 PROJECT_CHOSEN rank=0 mode=rail kind=pax cargo=PASS src=20 dst=100 cost=30000 profit=8000",
            "OPEX 1972-1-2 PROJECT_CHOSEN rank=0 mode=rail kind=pax cargo=PASS src=100 dst=20 cost=30000 profit=8000",
        ]
        row = parse_diagnostic_log(lines)["by_year_kind_cargo_destination"]["1972/pax/PASS/destination_unknown"]
        self.assertEqual(row["chosen/visits"], 2)
        self.assertEqual(row["chosen/distinct_od"], 1)

    def test_rid_without_start_is_censored_not_matched_to_od(self):
        result = parse_rid_lines([
            "OPEX 1974-2-4 RAIL_PREASTAR_END rid=999_1 stop=OK iters=10 budget=1000",
            "OPEX 1974-2-4 RAIL_PREASTAR_END rid=999_1 stop=OK iters=10 budget=1000",
        ], source="obs_seed42_r0.log")
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(result["attempts"][0]["status"], "censored")
        self.assertIsNone(result["attempts"][0]["kind"])

    def test_generation_destination_is_aggregate_not_distinct_pairs(self):
        result = parse_diagnostic_log([
            "OPEX 1973-5-1 RAIL_PREPAIR freight_cargo=-1 freight_ind_pairs=40 freight_town_pairs=60 freight_town_zero_monthly=50",
        ])["by_year_kind_cargo_destination"]
        self.assertEqual(result["1973/freight/cargo_mix_unresolved/town"]["pairs_examined_visits"], 60)
        self.assertNotIn("chosen/distinct_od", result["1973/freight/cargo_mix_unresolved/town"])


if __name__ == "__main__":
    unittest.main()
