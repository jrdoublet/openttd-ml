"""R25 : couverture économique et refus des trimestres partiellement décodés."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import openttdlab
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    for name in ("bananas_ai", "bananas_ai_library", "local_folder", "run_experiments"):
        setattr(fake_lab, name, mock.MagicMock())
    sys.modules["openttdlab"] = fake_lab

import bench_v2
from bench_v2 import quarter_profit, summarise, year_profit, year_profit_metrics
from bench_1v1_5y_20seeds import build_policy_comparison, extract_company_record
from game_health import annotate_summary


class ProfitCoverageTests(unittest.TestCase):
    @staticmethod
    def quarters():
        return [
            {"income": 100, "expenses": -10, "company_value": 1000, "performance_history": 100},
            {"income": 10, "expenses": -200},
            {"income": 100, "expenses": 20},
            {"income": 100, "expenses": -30},
        ]

    @staticmethod
    def chunks(closed):
        return {"PLYR": {0: {"old_economy": closed}}, "VEHS": {}, "STNN": {}}

    def test_complete_window_preserves_losses_and_expense_conventions(self):
        closed = self.quarters()
        original = deepcopy(closed)
        self.assertEqual(year_profit(closed), 50)
        self.assertEqual(year_profit_metrics(closed), {
            "profit_year": 50, "profit_year_quarters_available": 4,
            "profit_year_quarters_valid": 4, "profit_year_coverage": "complete",
        })
        self.assertEqual(closed, original)
        self.assertEqual(quarter_profit({"income": 0, "expenses": 0}), 0)

    def test_every_missing_field_invalidates_whole_window(self):
        for index in range(4):
            for field in ("income", "expenses"):
                with self.subTest(index=index, field=field):
                    closed = self.quarters()
                    del closed[index][field]
                    metrics = year_profit_metrics(closed)
                    self.assertIsNone(year_profit(closed))
                    self.assertEqual(metrics["profit_year_coverage"], "invalid")
                    self.assertEqual(metrics["profit_year_quarters_available"], 4)
                    self.assertEqual(metrics["profit_year_quarters_valid"], 3)

    def test_short_history_is_partial_not_invalid_or_annualized(self):
        for count in (1, 2, 3):
            with self.subTest(count=count):
                closed = self.quarters()[:count]
                metrics = year_profit_metrics(closed)
                self.assertEqual(metrics["profit_year"], sum(quarter_profit(q) for q in closed))
                self.assertEqual(metrics["profit_year_coverage"], "partial")
                self.assertEqual(metrics["profit_year_quarters_valid"], count)

    def test_empty_history_is_missing_not_zero(self):
        for closed in (None, [], ()):
            with self.subTest(closed=closed):
                metrics = year_profit_metrics(closed)
                self.assertIsNone(metrics["profit_year"])
                self.assertEqual(metrics["profit_year_coverage"], "missing")
                self.assertEqual(metrics["profit_year_quarters_available"], 0)

    def test_invalid_values_and_entries_fail_closed(self):
        for invalid in (None, "100", True, float("nan"), float("inf"), float("-inf")):
            for field in ("income", "expenses"):
                with self.subTest(invalid=invalid, field=field):
                    closed = self.quarters()
                    closed[2][field] = invalid
                    self.assertIsNone(year_profit(closed))
        for invalid in (None, {}, [], "quarter"):
            with self.subTest(entry=invalid):
                self.assertIsNone(year_profit([invalid]))
        self.assertEqual(year_profit_metrics({"0": self.quarters()[0]})["profit_year_coverage"], "invalid")

    def test_only_last_four_closed_quarters_are_used(self):
        self.assertEqual(year_profit(self.quarters() + [{}]), 50)

    def test_collectors_and_summary_keep_coverage(self):
        closed = self.quarters()
        del closed[1]["expenses"]
        chunks = self.chunks(closed)
        duel = extract_company_record(chunks, 0, ["OpexAI", 42, 0], "1979-12-01")
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "checkpoints.jsonl"
            with mock.patch.object(bench_v2, "CHECKPOINT_PATH", checkpoint):
                solo, = bench_v2.keep({
                    "chunks": chunks, "date": "1979-12-01",
                    "experiment": {"bench_run": ["OpexAI", 42, 0]},
                })
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(saved, solo)
        for row in (duel, solo):
            with self.subTest(run=row["run"]):
                self.assertIsNone(row["profit_year"])
                self.assertEqual(row["profit_year_coverage"], "invalid")
                self.assertEqual(row["profit_year_quarters_valid"], 3)
                summary, = summarise([row])
                self.assertFalse(summary["run_ok"])
                self.assertEqual(summary["profit_year_coverage"], "invalid")
                self.assertEqual(summary["failure_reason"], "economic_decode_failure: invalid_closed_quarter")

    def test_health_cannot_rehabilitate_invalid_economic_window(self):
        closed = self.quarters()
        del closed[1]["expenses"]
        row = extract_company_record(self.chunks(closed), 0, ["OpexAI", 42, 0], "1979-12-01")
        assessment = {
            "companies": {"OpexAI": {"run_ok": True, "status": "complete"}},
            "game_ok": True, "game_status": "complete",
            "expected_last_checkpoint": "1979-12-01",
        }
        result, = annotate_summary(summarise([row]), [row], assessment)
        self.assertFalse(result["run_ok"])
        self.assertFalse(result["game_ok"])
        self.assertEqual(result["status"], "missing_data")
        self.assertEqual(result["failure_reason"], "economic_decode_failure: invalid_closed_quarter")

    def test_missing_first_entry_does_not_crash_collectors(self):
        closed = self.quarters()
        closed[0] = None
        row = extract_company_record(self.chunks(closed), 0, ["OpexAI", 42, 0], "1979-12-01")
        self.assertIsNone(row["profit_year"])
        self.assertEqual(row["profit_year_coverage"], "invalid")

    def test_invalid_deficit_quarter_makes_comparison_incomplete(self):
        summary = []
        for seed in range(20):
            for policy in ("ref", "var"):
                for owner, arm in enumerate(("OpexAI", "AAAHogEx")):
                    closed = self.quarters()
                    if seed == 0 and policy == "var" and arm == "OpexAI":
                        del closed[1]["expenses"]  # Ne pas omettre ce déficit de 190.
                    row = extract_company_record(
                        {"PLYR": {owner: {"old_economy": closed}}, "VEHS": {}, "STNN": {}},
                        owner, [arm, seed, 0], "1979-12-01",
                    )
                    row.update({"duel_policy_id": policy, "arm": arm, "seed": seed, "repeat": 0,
                                "run_ok": True, "game_ok": True, "status": "complete"})
                    summary.append(row)
        # Santé supposée bonne pour isoler le garde économique, même sans summarise.
        result = build_policy_comparison(
            summary, [], seeds=list(range(20)), repeats=1,
            reference_policy_id="ref", variant_policy_id="var",
            primary_metric="profit_year", min_useful_primary_delta=5,
            value_guard_max_loss_pct=5, starting_year=1970, years=10,
        )
        self.assertEqual(result["verdict"], "incomplete")
        self.assertFalse(result["comparison_complete"])
        self.assertEqual(result["complete_pairs"], 19)
        self.assertIsNone(result["primary_pass"])


if __name__ == "__main__":
    unittest.main()