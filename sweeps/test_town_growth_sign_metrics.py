"""TG exposure: real sign format, ownership, snapshot and policy propagation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from sweeps import bench_1v1_5y_20seeds as bench


class TownGrowthSignMetricsTests(unittest.TestCase):
    def setUp(self):
        self.chunks = json.loads(
            (Path(__file__).parent / "fixtures/town_growth_signs.json").read_text(encoding="utf-8")
        )

    def test_fixture_counts_builds_not_station_increments(self):
        metrics = bench.town_growth_sign_metrics(self.chunks, current_year=1971)
        self.assertEqual(metrics["town_growth_builds_sign_total"], 4)
        self.assertEqual(metrics["town_growth_builds_sign_by_year"], {"1970": 2, "1971": 2})
        self.assertEqual(metrics["town_growth_signs_invalid"], 6)

    def test_list_chunk_and_owner_filter(self):
        self.chunks["SIGN"] = list(self.chunks["SIGN"].values())
        metrics = bench.town_growth_sign_metrics(self.chunks, current_year=1971, target_owner=1)
        # The sign without an owner is accepted for older chunk schemas.
        self.assertEqual(metrics["town_growth_builds_sign_total"], 2)

    def test_missing_chunk_is_unknown_empty_chunk_is_zero(self):
        for chunks in ({}, {"SIGN": None}, {"SIGN": "bad"}):
            self.assertTrue(all(value is None for value in bench.town_growth_sign_metrics(chunks).values()))
        for empty in ({}, []):
            metrics = bench.town_growth_sign_metrics({"SIGN": empty})
            self.assertEqual(metrics["town_growth_builds_sign_total"], 0)
            self.assertEqual(metrics["town_growth_builds_sign_by_year"], {})

    def test_century_rollover(self):
        metrics = bench.town_growth_sign_metrics(
            {"SIGN": [{"name": "TG|99|1|1|3"}, {"name": "TG|0|2|1|3"}]}, current_year=2000
        )
        self.assertEqual(metrics["town_growth_builds_sign_by_year"], {"1999": 1, "2000": 1})

    def test_keep_writes_metrics_to_jsonl(self):
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = Path(temp) / "rows.jsonl"
            with mock.patch.object(bench, "CHECKPOINT_PATH", checkpoint):
                rows = bench.keep({"chunks": self.chunks, "date": "1971-12-01",
                                   "experiment": {"seed": 42, "policy_id": "reference"}})
            persisted = [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(persisted), 2)
        for record in persisted:
            self.assertEqual(record["town_growth_builds_sign_total"], 4)
            self.assertEqual(record["town_growth_builds_sign_by_year"], {"1970": 2, "1971": 2})

    def test_summary_uses_last_snapshot_without_summing_durable_signs(self):
        metrics = bench.town_growth_sign_metrics(self.chunks, current_year=1971)
        raw = [{"run": ["OpexAI", 42, 0], "date": date, **metrics}
               for date in ("1971-11-01", "1971-12-01")]
        summary = bench._stamp_structural_metrics([{}, {}], raw)
        self.assertEqual([row["town_growth_builds_sign_total"] for row in summary], [4, 4])

    def test_policy_report_totals_annual_counts_and_unknowns(self):
        summary = []
        rows = []
        for policy, chunks in (("reference", self.chunks), ("tg_off", {"SIGN": {}})):
            metrics = bench.town_growth_sign_metrics(chunks, current_year=1971)
            for arm in ("OpexAI", "AAAHogEx"):
                record = {"duel_policy_id": policy, "arm": arm, "seed": 42, "repeat": 0,
                          "run_ok": True, "game_ok": True, "profit_year": 100,
                          "company_value": 1000, **metrics}
                summary.append(record)
                rows.append({**record, "run": [arm, 42, 0], "date": "1971-12-01"})
        comparison = bench.build_policy_comparison(
            summary, rows, seeds=[42], repeats=1, reference_policy_id="reference",
            variant_policy_id="tg_off", primary_metric="profit_year", min_useful_primary_delta=0,
            value_guard_max_loss_pct=5, starting_year=1970, years=2
        )
        pair = comparison["per_pair"][0]
        self.assertEqual(pair["town_growth_metrics"]["builds_total"],
                         {"reference": 4, "variant": 0, "policy_delta": -4})
        self.assertEqual([row["town_growth_builds"]["policy_delta"] for row in pair["annual_trajectory"]], [-2, -2])
        self.assertEqual(comparison["town_growth_aggregates"]["builds_total"]["mean"], -4)
        self.assertEqual(comparison["town_growth_aggregates"]["builds_by_year"]["1970"]["mean"], -2)
        unknown = bench._town_growth_policy_metrics({}, {}, 1970, 2)
        self.assertIsNone(unknown["builds_total"]["policy_delta"])
        self.assertIsNone(unknown["builds_by_year"]["1970"]["reference"])


if __name__ == "__main__":
    unittest.main()
