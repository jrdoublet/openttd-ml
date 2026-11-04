"""Contrats du parseur RAIL-LONG v1/v2 et INVEST-STALL ; sans OpenTTD/Docker.

    python -B -X utf8 -m unittest sweeps.test_analyse_rail_long_v2_events -v

Les réalisations de journaux ne sont PAS un inventaire final des sauvegardes.
"""

import contextlib
import io
import json
import unittest
from pathlib import Path

from sweeps.analyse_rail_long_v2 import (
    EVENT_COUNT_FIELDS,
    analyze,
    display,
    engine_log,
    parse_engine_log_lines,
)


ROOT = Path(__file__).resolve().parents[1]
STEM = "rail_long_v2_invest_stall_smoke_4x10_20261103_r1"
REPORT = ROOT / "results" / (STEM + ".json")
ENGINE = ROOT / "results" / (STEM + "_engine")
SEEDS = (17, 512, 65537, 841478)


def line(date, source, fields):
    return f"[2026-11-03 19:00:00] OPEX {date} {source} {fields}\n"


class SyntheticEventContracts(unittest.TestCase):
    def parse(self, *lines, minimum=6):
        return parse_engine_log_lines(lines, minimum)

    def test_legacy_v1_unchanged_and_initial_wagons_not_terminal(self):
        result = self.parse(
            line("1970-1-1", "RAIL_BUILD", "cargo=COAL wagons=3 wagons2=2 trains=2"),
            line("1970-1-2", "RAIL_BUILD", "cargo=PASS wagons=1 trains=1"),
            line("1970-1-3", "RAIL_LONG", "event=build line=10 len_a=6 len_b=7 wagons=5 trains=2"),
            line("1970-1-4", "RAIL_LONG", "event=build line=11 len_a=5 len_b=8 wagons=3 trains=1"),
            line("1970-1-5", "RAIL_LONG", "event=fallback reason=budget"),
        )
        self.assertEqual(result["rail_build_events"], 2)
        self.assertEqual(result["freight_build_events"], 1)
        self.assertEqual(result["initial_all_train_wagons_median"], 5)
        self.assertEqual(result["initial_freight_train_wagons_median"], 5)
        self.assertEqual(result["initial_freight_train_wagons_count"], 2)
        self.assertEqual(result["initial_freight_train_wagons_histogram"], {5: 2})
        self.assertEqual(result["long_station_build_count"], 2)
        self.assertEqual(result["long_both_ends_over_threshold"], 1)
        self.assertEqual(result["long_fallback_events"], 1)
        self.assertEqual(result["long_station_builds"][0], {
            "line": 10, "date": "1970-1-3", "length_a": 6,
            "length_b": 7, "initial_wagons": 5, "trains": 2,
        })
        self.assertTrue(all(result[key] == 0 for key in EVENT_COUNT_FIELDS))

    def test_v2_new_build_is_distinct_from_v1_build_and_extension(self):
        result = self.parse(
            line("1970-2-1", "RAIL_LONG_V2",
                 "event=build line=15 len_a=6 len_b=7 wagons=9 trains=1"),
            line("1970-2-2", "RAIL_LONG_V2",
                 "event=build line=16 len_a=5 len_b=8 wagons=9 trains=1"),
            line("1970-2-3", "RAIL_LONG_V2", "event=pick line=17 target=7"),
        )
        self.assertEqual(result["v2_initial_build_count"], 2)
        self.assertEqual(result["v2_initial_both_ends_over_threshold"], 1)
        self.assertEqual(result["v2_initial_builds"][0]["length_a"], 6)
        self.assertEqual(result["v2_initial_builds"][0]["length_b"], 7)
        self.assertEqual(result["v2_extension_done_count"], 0)
        self.assertEqual(result["long_station_build_count"], 0)  # V1 only

    def test_v2_done_len_nested_in_reason_and_threshold(self):
        result = self.parse(
            line("1974-2-25", "RAIL_LONG_V2", "event=done line=35 reason=len=7 cost=4466"),
            line("1975-2-25", "RAIL_LONG_V2", "event=done line=36 reason=len=5 cost=5000"),
            line("1976-2-25", "RAIL_LONG_V2", "event=done line=37 reason=unknown"),
            line("1977-2-25", "RAIL_LONG_V2", "event=fail line=38 reason=build_a"),
        )
        self.assertEqual(result["v2_extension_done_count"], 3)
        self.assertEqual(result["v2_extension_to_threshold_count"], 1)
        self.assertEqual(result["v2_extensions_done"][0]["target_length"], 7)
        self.assertEqual(result["v2_extensions_done"][0]["cost"], 4466)
        self.assertIsNone(result["v2_extensions_done"][2]["target_length"])
        self.assertEqual(result["v2_initial_build_count"], 0)
        self.assertEqual(result["v2_failed_count"], 1)

    def test_v2_fleet_done_and_invest_fleet_done_are_disjoint(self):
        result = self.parse(
            line("1977-1-1", "RAIL_LONG_V2", "event=fleet_pick line=44 wagons_old=8 wagons_new=9"),
            line("1977-4-13", "RAIL_LONG_V2",
                 "event=fleet_done line=44 wagons_old=8 wagons_new=9 new_vehicle=166 capacity=225"),
            line("1978-1-2", "INVEST_STALL",
                 "event=done route=fleet line=7 kind=wagon old_vehicle=8 "
                 "new_vehicle=9 old_wagons=3 wagons=4"),
            line("1978-1-3", "INVEST_STALL", "event=done route=origin line=8"),
            line("1978-1-4", "INVEST_STALL", "event=fleet_pick route=fleet line=7"),
        )
        self.assertEqual(result["v2_fleet_done_count"], 1)
        self.assertEqual(result["v2_fleet_done"][0]["wagons_new"], 9)
        self.assertEqual(result["v2_fleet_done"][0]["new_vehicle"], 166)
        self.assertEqual(result["invest_fleet_done_count"], 1)
        self.assertEqual(result["invest_fleet_done"][0]["old_wagons"], 3)
        self.assertEqual(result["v2_extension_done_count"], 0)

    def test_stations_staged_and_matched_to_build_ok_not_final_inventory(self):
        result = self.parse(
            line("1975-2-28", "INVEST_STALL",
                 "event=station_built src=22372 dst=13279 parent=108 new_a=66 new_b=67"),
            line("1975-3-3", "INVEST_STALL",
                 "event=build_ok src=22372 dst=13279 parent=108 new_a=66 trains=1 cost=99012"),
        )
        self.assertEqual(result["invest_station_built_count"], 1)
        self.assertEqual(result["invest_new_line_build_ok_count"], 1)
        self.assertEqual(result["invest_station_pair_matched_count"], 1)
        self.assertEqual(result["invest_stations_confirmed_at_build_count"], 2)
        self.assertEqual(result["invest_unmatched_station_built_count"], 0)
        self.assertEqual(result["invest_unmatched_build_ok_count"], 0)
        self.assertEqual(result["invest_station_pairs_matched"][0]["new_b"], 67)
        self.assertTrue(result["invest_station_built"][0]["matched_build_ok"])

    def test_unmatched_missing_stage_ambiguous_and_fifo(self):
        result = self.parse(
            line("1975-1-1", "INVEST_STALL",
                 "event=station_built src=1 dst=2 parent=3 new_a=6 new_b=7"),
            line("1975-1-2", "INVEST_STALL",
                 "event=station_built src=1 dst=2 parent=3 new_a=6 new_b=8"),
            line("1975-1-3", "INVEST_STALL",
                 "event=build_ok src=1 dst=2 parent=3 new_a=6 trains=1 cost=100"),
            line("1975-1-4", "INVEST_STALL",
                 "event=build_ok src=9 dst=2 parent=3 new_a=6 trains=1 cost=100"),
            line("1975-1-5", "INVEST_STALL",
                 "event=station_built src=4 dst=5 parent=9 new_a=10"),
            line("1975-1-6", "INVEST_STALL",
                 "event=build_ok src=4 dst=5 parent=9 new_a=10 trains=1 cost=100"),
        )
        self.assertEqual(result["invest_station_built_count"], 3)
        self.assertEqual(result["invest_new_line_build_ok_count"], 3)
        self.assertEqual(result["invest_station_pair_matched_count"], 1)
        self.assertEqual(result["invest_station_pairs_matched"][0]["new_b"], 7)
        self.assertEqual(result["invest_unmatched_station_built_count"], 2)
        self.assertEqual(result["invest_unmatched_build_ok_count"], 2)
        self.assertEqual(result["invest_stations_confirmed_at_build_count"], 2)

    def test_fail_rollback_and_orphan_safe_are_not_success(self):
        result = self.parse(
            line("1974-1-28", "RAIL_LONG_V2", "event=pick line=41 target=7"),
            line("1974-1-28", "RAIL_LONG_V2", "event=fail line=41 reason=build_a"),
            line("1974-2-15", "RAIL_LONG_V2", "event=rolled_back line=41 reason=build_a"),
            line("1974-3-15", "RAIL_LONG_V2", "event=fail line=42 reason=build_b"),
            line("1974-4-15", "RAIL_LONG_V2", "event=orphan_safe line=42 reason=build_b"),
        )
        self.assertEqual(result["v2_failed_count"], 2)
        self.assertEqual(result["v2_rolled_back_count"], 1)
        self.assertEqual(result["v2_orphan_safe_count"], 1)
        self.assertEqual(result["v2_extension_done_count"], 0)
        self.assertEqual(result["v2_initial_build_count"], 0)

    def test_missing_log_returns_missing_evidence_not_zero(self):
        counts, missing = engine_log(ROOT / "nonexistent_engine_logs", "reference", 841478, 0, 6)
        self.assertIsNone(counts)
        self.assertIn("reference_seed841478_r0.log", missing)

    def test_v1_historical_metrics_unchanged_and_label_explicit(self):
        zero = {key: 0 for key in EVENT_COUNT_FIELDS}
        legacy = dict(
            initial_freight_train_wagons_median_pooled=3.0,
            long_both_ends_over_threshold=2,
            final_rail_vehicles=8,
            **zero,
        )
        checkpoint = dict(
            rail_vehicles=8, observed_profit_per_vehicle_gbp=9.0,
            observed_revenue_per_vehicle_gbp=None,
        )
        builds = dict(
            initial_freight_train_wagons_median=3.0,
            long_both_ends_over_threshold=2,
            **zero,
        )
        result = {
            "source": "historique.json", "source_bundle_sha256": "fixture",
            "verdict": "fixture", "mean_profit_year_delta_gbp": 0,
            "wins": 0, "losses": 0, "ties": 1, "wilcoxon_p": 1.0,
            "minimum_long_platform_tiles": 6,
            "aggregate": {"reference": legacy, "variant": legacy},
            "rows": [dict(
                seed=42, policy_delta_profit_year_gbp=0,
                reference_checkpoint=checkpoint, variant_checkpoint=checkpoint,
                reference_builds=builds, variant_builds=builds,
            )],
            "notes": ["historique"], "missing_evidence": [],
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            display(result)
        text = out.getvalue()
        self.assertIn("créations longues v1 ≥6 tuiles aux deux bouts 2/2", text)
        self.assertIn("Créations longues v1 REF/ON", text)
        self.assertIn("| Graine | Δ profit/an | Trains fin REF/ON |", text)
        self.assertNotIn("## Événements v2 / INVEST_STALL", text)


@unittest.skipUnless(REPORT.is_file() and ENGINE.is_dir(), "fixture smoke combo 4×10 absente")
class FrozenSmoke4x10Contracts(unittest.TestCase):
    def test_actual_logs_per_seed_and_no_double_counting(self):
        expected = {
            17:     dict(extension=1, v2_fleet=1, build_ok=0, pairs=0, invest_fleet=12),
            512:    dict(extension=1, v2_fleet=3, build_ok=1, pairs=1, invest_fleet=6),
            65537:  dict(extension=0, v2_fleet=0, build_ok=2, pairs=2, invest_fleet=7),
            841478: dict(extension=2, v2_fleet=1, build_ok=3, pairs=3, invest_fleet=9),
        }
        totals = {
            "v2_extension_done_count": 0, "v2_fleet_done_count": 0,
            "invest_new_line_build_ok_count": 0, "invest_station_pair_matched_count": 0,
            "invest_fleet_done_count": 0,
        }
        for seed in SEEDS:
            with self.subTest(seed=seed):
                reference, missing = engine_log(ENGINE, "reference", seed, 0, 6)
                self.assertIsNone(missing)
                self.assertTrue(all(reference[key] == 0 for key in EVENT_COUNT_FIELDS))
                variant, missing = engine_log(ENGINE, "rail_long_v2_invest_stall", seed, 0, 6)
                self.assertIsNone(missing)
                want = expected[seed]
                self.assertEqual(variant["v2_initial_build_count"], 0)
                self.assertEqual(variant["v2_extension_done_count"], want["extension"])
                self.assertEqual(variant["v2_fleet_done_count"], want["v2_fleet"])
                self.assertEqual(variant["invest_new_line_build_ok_count"], want["build_ok"])
                self.assertEqual(variant["invest_station_built_count"], want["pairs"])
                self.assertEqual(variant["invest_station_pair_matched_count"], want["pairs"])
                self.assertEqual(variant["invest_fleet_done_count"], want["invest_fleet"])
                for metric in totals:
                    totals[metric] += variant[metric]
                if seed == 841478:
                    self.assertEqual(variant["v2_failed_count"], 1)
                    self.assertEqual(variant["v2_rolled_back_count"], 1)
                    self.assertEqual(variant["v2_orphan_safe_count"], 0)
                    self.assertEqual(
                        {(x["line"], x["target_length"], x["cost"])
                         for x in variant["v2_extensions_done"]},
                        {(35, 7, 4466), (32, 7, 4690)},
                    )
                    self.assertEqual(
                        {(x["new_a"], x["new_b"])
                         for x in variant["invest_station_pairs_matched"]},
                        {(66, 67), (129, 130), (136, 140)},
                    )
        self.assertEqual(totals, {
            "v2_extension_done_count": 4,
            "v2_fleet_done_count": 5,
            "invest_new_line_build_ok_count": 6,
            "invest_station_pair_matched_count": 6,
            "invest_fleet_done_count": 34,
        })

    def test_c66_original_economics_and_added_event_totals(self):
        result = analyze(REPORT, ENGINE)
        self.assertEqual(len(result["rows"]), 4)
        by_seed = {item["seed"]: item for item in result["rows"]}
        self.assertEqual(by_seed[841478]["policy_delta_profit_year_gbp"], 476838)
        self.assertEqual(by_seed[841478]["reference_profit_year_gbp"], 1787193)
        self.assertEqual(by_seed[841478]["variant_profit_year_gbp"], 2264031)
        self.assertEqual(result["aggregate"]["variant"]["v2_initial_build_count"], 0)
        self.assertEqual(result["aggregate"]["variant"]["v2_extension_done_count"], 4)
        self.assertEqual(result["aggregate"]["variant"]["v2_fleet_done_count"], 5)
        self.assertEqual(result["aggregate"]["variant"]["invest_new_line_build_ok_count"], 6)
        self.assertEqual(result["aggregate"]["variant"]["invest_station_pair_matched_count"], 6)
        self.assertEqual(result["aggregate"]["variant"]["invest_fleet_done_count"], 34)
        # V1 historique inchangé ; 0 ne représente PAS les extensions v2.
        self.assertEqual(result["aggregate"]["variant"]["long_both_ends_over_threshold"], 0)
        self.assertIsNone(result["aggregate"]["variant"]["observed_revenue_per_vehicle_gbp"])
        self.assertFalse(result["missing_evidence"])
        self.assertIsInstance(json.dumps(result, ensure_ascii=False), str)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            display(result)
        text = out.getvalue()
        self.assertIn("créations longues v1 ≥6 tuiles aux deux bouts 0/0", text)
        self.assertIn("Créations longues v1 REF/ON", text)
        self.assertIn("Événements v2 / INVEST_STALL (journaux, PAS inventaire final)", text)
        self.assertIn("extensions v2 terminées : 0/4", text)
        self.assertIn("paires appariées à build_ok : 0/6", text)


if __name__ == "__main__":
    unittest.main()
