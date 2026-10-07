import tempfile
import unittest
from pathlib import Path

from sweeps.analyse_rail_depot_cost_exposure import analyse


def _line(date, rank, mode, src, dst, *, cost, finance, profit, roi, score):
    return (
        f"[x] dbg: [script:4] [0] [I] OPEX {date} PORTFOLIO_RANK "
        f"rank={rank} mode={mode} kind=pax cargo=PASS src={src} dst={dst} dist=50 "
        f"roi={roi} turnover_bonus=100 generation_ratio=0 score={score} "
        f"rank_score={score} rank_score_raw={score} budget_score={score} "
        f"cost={cost} finance_capital={finance} profit={profit}\n"
    )


def _attempt(date, src, dst, *, pre, model, quote, profit=10000, roi=250):
    return (
        f"[x] dbg: [script:4] [0] [I] OPEX {date} RAIL_ATTEMPT "
        f"src={src} dst={dst} kind=pax manh=50 reuse=0 reuse_alt=0 join_end=- "
        f"pred_profit={profit} pred_roi={roi} pred_astar=100 pre={pre} model={model} "
        f"quote={quote} actual=0 ok=1 reason=- iters=100 ops=1000 startx=0 endx=0\n"
    )


def _chosen(date, mode, src, dst, *, cargo="PASS"):
    return (
        f"[x] dbg: [script:4] [0] [I] OPEX {date} PROJECT_CHOSEN "
        f"rank=0 mode={mode} cargo={cargo} src={src} dst={dst} dist=50 "
        f"cost=100 profit=200 roi=2000\n"
    )


class RailDepotExposureAnalysisTests(unittest.TestCase):
    def _write_pair(self, root, reference, variant):
        (root / "rail_depot_off_seed42_r0.log").write_text(reference, encoding="utf-8")
        (root / "rail_depot_on_seed42_r0.log").write_text(variant, encoding="utf-8")

    def test_detects_rail_economics_delta_while_order_is_still_identical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            air = _line("1971-1-1", 0, "air", 1, 2, cost=100, finance=100, profit=200, roi=2000, score=2)
            rail_off = _line("1971-1-1", 1, "rail", 3, 4, cost=40000, finance=40000, profit=10000, roi=250, score=1)
            rail_on = _line("1971-1-1", 1, "rail", 3, 4, cost=42000, finance=42000, profit=9800, roi=233, score=0.9)
            self._write_pair(root, air + rail_off, air + rail_on)

            result = analyse(root, "rail_depot_off", "rail_depot_on")
            row = result["seeds"][0]["first_same_order_rail_economics_delta"]
            self.assertIsNotNone(row)
            self.assertEqual("1971-1-1", row["date"])
            self.assertEqual(2000.0, row["delta"]["cost"])
            self.assertEqual(2000.0, row["delta"]["finance_capital"])
            self.assertLess(row["delta"]["profit"], 0)

    def test_does_not_call_post_order_divergence_a_direct_signature(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rail_off = _line("1971-1-1", 0, "rail", 3, 4, cost=40000, finance=40000, profit=10000, roi=250, score=1)
            air_off = _line("1971-1-1", 1, "air", 1, 2, cost=100, finance=100, profit=200, roi=2000, score=2)
            air_on = _line("1971-1-1", 0, "air", 1, 2, cost=100, finance=100, profit=200, roi=2000, score=2)
            rail_on = _line("1971-1-1", 1, "rail", 3, 4, cost=42000, finance=42000, profit=9800, roi=233, score=0.9)
            self._write_pair(root, rail_off + air_off, air_on + rail_on)

            result = analyse(root, "rail_depot_off", "rail_depot_on")
            seed = result["seeds"][0]
            self.assertIsNone(seed["first_same_order_rail_economics_delta"])
            self.assertIsNotNone(seed["first_same_rail_candidate_economics_delta"])
            self.assertIsNotNone(seed["first_portfolio_order_delta"])

    def test_attempt_signature_separates_model_from_same_physical_quote(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reference = _attempt("1971-2-1", 3, 4, pre=40000, model=40000, quote=47000)
            variant = _attempt("1971-2-1", 3, 4, pre=42000, model=42000, quote=47000, profit=9800, roi=233)
            self._write_pair(root, reference, variant)

            result = analyse(root, "rail_depot_off", "rail_depot_on")
            row = result["seeds"][0]["first_same_attempt_model_delta"]
            self.assertIsNotNone(row)
            self.assertTrue(row["same_quote"])
            self.assertTrue(row["same_outcome"])
            self.assertEqual(2000.0, row["delta"]["pre"])
            self.assertEqual(0.0, row["delta"]["quote"])

    def test_choice_sequence_reports_timing_before_identity_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reference = _chosen("1970-9-14", "air", 1, 2) + _chosen("1970-9-14", "air", 1, 3)
            variant = _chosen("1970-9-7", "air", 1, 2) + _chosen("1970-10-13", "air", 4, 5)
            self._write_pair(root, reference, variant)

            result = analyse(root, "rail_depot_off", "rail_depot_on")
            seed = result["seeds"][0]
            timing = seed["first_project_chosen_timing_delta"]
            identity = seed["first_project_chosen_identity_delta"]
            self.assertEqual(0, timing["index"])
            self.assertEqual("1970-9-14", timing["reference_date"])
            self.assertEqual("1970-9-7", timing["variant_date"])
            self.assertEqual(1, identity["index"])
            self.assertEqual(["air", "PASS", "1", "3"], identity["reference_candidate"])
            self.assertEqual(["air", "PASS", "4", "5"], identity["variant_candidate"])


if __name__ == "__main__":
    unittest.main()
