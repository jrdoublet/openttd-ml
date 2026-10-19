"""Fixtures for reference-only, pooled, missing-aware accounting decomposition."""
from copy import deepcopy
import unittest

from v274_air_decomposition import decompose, describe, engine_table, YEARS, ARMS


def line(profit=100, vehicles=2):
    return {"mode": "air", "vehicles": vehicles, "profit_this_year_gbp": profit,
            "market_key": "air|1,2", "ordered_station_tiles": [0, 3],
            "station_ids": [1, 2], "capacity_by_cargo": {"pax": vehicles * 90},
            "endpoint_cargo_stats": [
                {"station_id": 1, "cargo": {"pax": {"rated": True, "rating": 128}}},
                {"station_id": 2, "cargo": {"pax": {"rated": False, "rating": None}}}]}


def fixture():
    snapshots, rows = [], []
    for year in YEARS:
        for arm in ARMS:
            for seed in (42, 7):
                count = 2 if seed == 42 else 4
                snapshots.append({"duel_policy_id": "reference", "year": year, "arm": arm,
                                  "seed": seed, "ok": True, "unresolved_vehicles": [],
                                  "date": f"{year}-12-01", "lines": [line(100, count)]})
                rows.append((len(rows) + 1, {"duel_policy_id": "reference", "run": [arm, seed, 0],
                    "date": f"{year}-12-01", "air_engine_counts": {"217": count},
                    "air_capacities_by_cargo": {"pax": count * 90}}))
    data = {"openttd_version": "15.3", "seeds": [42, 7], "repeats": 1,
            "games": [{"policy_id": "reference", "seed": s, "game_ok": True} for s in (42, 7)],
            "campaign_id": "fixture", "source_bundle_sha256": "fixture", "map_size": 8,
            "line_telemetry": {"snapshots": snapshots}}
    return data, rows


class DecompositionTest(unittest.TestCase):
    def test_missing_profit_is_not_zero(self):
        result = describe([line(None)], 256, [])
        self.assertIsNone(result["profit_per_plane"])
        self.assertEqual(result["rating_by_cargo"], {"pax": 128})

    def test_station_is_not_counted_once_per_route(self):
        result = describe([line(), line()], 256, [])
        self.assertEqual(result["airports"], 2)
        self.assertEqual(result["pairs"], 1)
        self.assertEqual(result["planes_per_airport"], 2)

    def test_pool_counts_not_mean_of_ratios_and_keep_local_ids_separate(self):
        data, rows = fixture()
        result = decompose(data, rows, {}, [])
        metric = result["years"]["1979"]["arms"]["OpexAI"]
        self.assertEqual(metric["airports"], 4)
        self.assertAlmostEqual(metric["profit_per_plane"], 200 / 6)
        self.assertFalse(result["causal_factorization_identified"])
        self.assertIn("departure_load_A_to_B", result["unavailable"])

    def test_variant_cannot_contaminate_reference(self):
        data, rows = fixture()
        extra = deepcopy(data["line_telemetry"]["snapshots"][0])
        extra["duel_policy_id"] = "variant"
        extra["lines"] = [line(999999)]
        data["line_telemetry"]["snapshots"].append(extra)
        result = decompose(data, rows, {}, [])
        factors = result["years"]["1973"]["accounting_factors"]
        self.assertAlmostEqual(factors["product"], factors["profit_per_plane_ratio"])
        self.assertAlmostEqual(factors["three_factor_product"], factors["profit_per_plane_ratio"])
        self.assertEqual(factors["product"], 1)

    def test_duplicate_or_unhealthy_snapshots_rejected(self):
        for change in ("duplicate", "unhealthy"):
            data, rows = fixture()
            if change == "duplicate":
                data["line_telemetry"]["snapshots"].append(deepcopy(data["line_telemetry"]["snapshots"][0]))
            else:
                data["line_telemetry"]["snapshots"][0]["ok"] = False
            with self.assertRaises(ValueError):
                decompose(data, rows, {}, [])

    def test_census_disagreement_rejected(self):
        data, rows = fixture()
        rows[0][1]["air_engine_counts"]["217"] += 1
        with self.assertRaises(ValueError):
            decompose(data, rows, {}, [])

    def test_engine_ids_resolved_by_name_not_offset(self):
        source = "MA(0), // 512 FFP Dart\nAVI(2, 16, 130, J, SOUND, 35, 74, 10, 90), // 2 FFP Dart"
        table = engine_table(source)
        self.assertEqual(table["512"]["nominal_kmh"], 947)
        self.assertEqual(table["512"]["nominal_pax"], 90)
        self.assertNotIn("217", table)


if __name__ == "__main__":
    unittest.main()
