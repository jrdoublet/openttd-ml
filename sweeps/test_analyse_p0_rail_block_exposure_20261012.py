"""Contrats de la sonde RAIL : attention aux fausses occasions perdues."""

import unittest

from analyse_p0_rail_block_exposure_20261012 import annual, decode, od, quoted_cash_positive


LINE = ("[2026-10-12] dbg: OPEX 1973-3-8 P0_RAIL_BLOCK branch=normal "
        "result=search_in_progress dedup=first physical=unknown self_revisit=0 "
        "rank=1 requested_kind=freight requested_cargo=7 requested_src=100 "
        "requested_dst=200 pred_profit=10000 pred_budget_capital=50000 "
        "pred_construction_capital=50000 cash_available=60000 "
        "blocker_kind=primary blocker_phase=search blocker_src=300 "
        "blocker_dst=400 blocker_start_date=1 blocker_age_days=15 "
        "blocker_start_tick=100 blocker_spent=450 blocker_budget=10000")


class RailBlockTests(unittest.TestCase):
    def test_parse_one(self):
        row = decode(LINE, seed=42, repeat=0)
        self.assertEqual((row["seed"], row["year"], row["requested_cargo"]), (42, 1973, 7))
        self.assertTrue(quoted_cash_positive(row))

    def test_dedup_cross_episodes_without_double_counting_od(self):
        x = decode(LINE, seed=42, repeat=0)
        y = dict(x, blocker_start_tick=101)
        z = dict(x, self_revisit=1)
        result = annual([x, y, z], 1973, 42)
        self.assertEqual(result["dedup_episode_observations"], 3)
        self.assertEqual(result["unique_competitor_od_cargo_kind"], 1)
        self.assertEqual(result["quote_cash_positive_unique_od"], 1)
        self.assertEqual(result["self_revisits"], 1)
        self.assertEqual(result["counterfactual_rail_lines"], "not_measured")

    def test_unfunded_quote_not_counted(self):
        a = dict(decode(LINE, seed=42, repeat=0), cash_available=49999)
        self.assertFalse(quoted_cash_positive(a))

    def test_pax_pair_canonical_freight_directed(self):
        a = decode(LINE, seed=42, repeat=0)
        b = dict(a, requested_src=200, requested_dst=100)
        self.assertNotEqual(od(a), od(b))
        a["requested_kind"] = b["requested_kind"] = "pax"
        self.assertEqual(od(a), od(b))

    def test_invalid_log_rejected(self):
        with self.assertRaises(ValueError):
            decode(LINE.replace("physical=unknown", "physical=proven"), seed=42, repeat=0)
        with self.assertRaises(ValueError):
            decode(LINE.replace("dedup=first", "dedup=again"), seed=42, repeat=0)

    def test_empty_year_is_explicit_zero(self):
        a = decode(LINE, seed=999, repeat=0)
        z = annual([a], 1972, 999)
        self.assertEqual(z["unique_competitor_od_cargo_kind"], 0)
        self.assertEqual(z["occupants_competing"], {})


if __name__ == "__main__":
    unittest.main()
