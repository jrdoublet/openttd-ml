"""Contrats d'identite et d'ordre des checkpoints annuels AIR."""

import unittest

try:
    from sweeps.analyse_air_portfolio_quality import analyse
except ImportError:
    from analyse_air_portfolio_quality import analyse


def _snap(month, profit, *, seed=42, repeat=0, year=1974, arm="OpexAI"):
    return {
        "duel_policy_id": "air_defaults", "arm": arm, "seed": seed,
        "repeat": repeat, "year": year, "date": f"{year}-{month:02d}-01",
        "lines": [{
            "mode": "air", "market_key": "air|1,2", "town_ids": [1, 2],
            "vehicles": 1, "capacity_by_cargo": {"0": 50},
            "profit_this_year_gbp": profit,
        }],
    }


def _analyse(snaps):
    return analyse({"campaign_id": "fixture", "line_telemetry": {"snapshots": snaps}},
                   "air_defaults")


class AirPortfolioIdentityTests(unittest.TestCase):
    def test_monthly_snapshots_have_order_independent_annual_result(self):
        rows = [_snap(1, 10), _snap(12, 90), _snap(6, 50)]
        forward = _analyse(rows)
        reverse = _analyse(list(reversed(rows)))
        self.assertEqual(forward, reverse)
        opex = next(row for row in forward["annual"] if row["arm"] == "OpexAI")
        self.assertEqual(opex["games"], 1)
        self.assertEqual(opex["mean"]["profit"], 90)

    def test_repetitions_remain_distinct_and_missing_year_is_not_zero(self):
        rows = [
            _snap(12, 100), _snap(12, 300, repeat=1),
            _snap(12, 40, seed=100, year=1973),
        ]
        report = _analyse(rows)
        opex_1974 = next(row for row in report["annual"]
                         if row["arm"] == "OpexAI" and row["year"] == 1974)
        self.assertEqual((opex_1974["seeds"], opex_1974["games"]), (1, 2))
        self.assertEqual(opex_1974["mean"]["profit"], 200)
        self.assertEqual(opex_1974["mean"]["markets"], 1)
        self.assertEqual(sum(r["markets"] for r in report["final_year_cohorts"]
                             if r["arm"] == "OpexAI"), 2)

    def test_contradictory_or_malformed_checkpoint_rejected(self):
        valid = _snap(12, 90)
        with self.assertRaisesRegex(ValueError, "contradictoires"):
            _analyse([valid, _snap(12, 999)])
        with self.assertRaisesRegex(ValueError, "annee contradictoire"):
            _analyse([dict(valid, year=1973)])
        with self.assertRaisesRegex(ValueError, "date valide"):
            _analyse([dict(valid, date="1974-02-30")])


if __name__ == "__main__":
    unittest.main()
