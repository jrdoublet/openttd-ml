"""Contrats de granularite et provenance pour le lecteur AIR historique."""

import unittest

try:
    from sweeps.analyse_air_service_quality import analyse
except ImportError:
    from analyse_air_service_quality import analyse


def _line(market="air|1,2", profit=100, vehicles=1):
    return {
        "mode": "air", "market_key": market, "service_key": market,
        "line_key_local": market, "ordered_station_tiles": [10, 30],
        "capacity_by_cargo": {"0": 100}, "cargo_types": [0],
        "vehicles": vehicles, "profit_this_year_gbp": profit,
        "endpoint_cargo_stats": [],
    }


def _snap(arm, seed, year, month, lines, repeat=0):
    return {
        "duel_policy_id": "air_defaults", "arm": arm, "seed": seed,
        "repeat": repeat, "year": year, "date": f"{year}-{month:02d}-01",
        "lines": lines,
    }


def _run(snapshots):
    return analyse({"campaign_id": "fixture", "line_telemetry": {"snapshots": snapshots}},
                   "air_defaults")


class AnnualCheckpointTests(unittest.TestCase):
    def test_last_month_in_year_prevents_duplicate_air_lines(self):
        january = _snap("OpexAI", 42, 1974, 1, [_line(profit=10)])
        december = _snap("OpexAI", 42, 1974, 12,
                         [_line(profit=70), _line("air|3,4", profit=30)])
        other_policy = dict(december, duel_policy_id="other_policy", lines=[_line()])
        result = _run([december, other_policy, january])
        self.assertEqual([(row["year"], row["n_lines"], row["profit_this_year_gbp"])
                          for row in result["annual"]], [(1974, 2, 100)])
        self.assertEqual(sum(row["n_lines"] for row in result["by_fleet_size"]), 2)

    def test_repeated_monthly_market_remains_a_single_matched_pair(self):
        snapshots = [
            _snap("OpexAI", 42, 1974, 1, [_line(profit=1)]),
            _snap("AAAHogEx", 42, 1974, 1, [_line(profit=2)]),
            _snap("OpexAI", 42, 1974, 12, [_line(profit=80)]),
            _snap("AAAHogEx", 42, 1974, 12, [_line(profit=120, vehicles=2)]),
        ]
        result = _run(snapshots)
        self.assertEqual(len(result["matched_markets"]), 1)
        match = result["matched_markets"][0]
        self.assertEqual(match["opex"]["profit_this_year_gbp"], 80)
        self.assertEqual(match["aaahogex"]["profit_this_year_gbp"], 120)
        self.assertEqual(next(row["n_markets"] for row in result["matched_summary"]
                              if row["strict_cargo_match"]), 1)

    def test_game_year_identity_and_conflicting_checkpoint_guard(self):
        snapshots = [
            _snap("OpexAI", 42, 1974, 1, [_line(profit=1)]),
            _snap("OpexAI", 42, 1974, 12, [_line(profit=100)]),
            _snap("OpexAI", 42, 1974, 1, [_line(profit=2)], repeat=1),
            _snap("OpexAI", 100, 1974, 1, [_line(profit=3)]),
            _snap("OpexAI", 42, 1973, 1, [_line(profit=4)]),
        ]
        result = _run(snapshots)
        self.assertEqual({row["year"]: (row["n_lines"], row["profit_this_year_gbp"])
                          for row in result["annual"]},
                         {1973: (1, 4), 1974: (3, 105)})
        duplicate = dict(snapshots[1], lines=[_line(profit=999)])
        with self.assertRaisesRegex(ValueError, "contradictoires"):
            _run(snapshots + [duplicate])
        broken = dict(snapshots[1], year=1973)
        with self.assertRaisesRegex(ValueError, "annee contradictoire"):
            _run([broken])


if __name__ == "__main__":
    unittest.main()
