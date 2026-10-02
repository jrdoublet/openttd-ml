"""Fixture manuelle du choix d'avion : âge, signature, Manhattan, test apparié."""

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sweeps.analyse_air_engine_choice import (
    aaa_formula_counterfactual,
    aaa_rank_bidirectional_passenger,
    analyse_campaign,
    analyse_path,
    collect_air_lines,
    decompose_profit_gap,
    main,
    per_vehicle_signature,
)


def _line(key, vehicles, capacity, profit, tiles, mode="air", towns=(10, 20), stations=(1, 2)):
    ends = []
    for index, tile in enumerate(tiles):
        ends.append({
            "station_id": stations[index],
            "town_id": towns[index],
            "tile": tile,
            "airport": {"tile": tile, "width": 6, "height": 6, "type": 1, "layout": 0, "rotation": 0},
            "cargo": {"0": {"rating": 100, "max_waiting_cargo": 10, "rated": True}},
        })
    line = {
        "line_key_local": key,
        "mode": mode,
        "station_ids": list(stations),
        "ordered_station_tiles": list(tiles),
        "town_ids": list(towns),
        "vehicles": vehicles,
        "capacity_by_cargo": capacity,
        "endpoint_cargo_stats": ends,
    }
    if profit is not None:
        line["profit_this_year_gbp"] = profit
    return line


def _snapshot(year, arm, lines, seed=42, policy="reference"):
    return {
        "duel_policy_id": policy,
        "arm": arm,
        "seed": seed,
        "repeat": 0,
        "year": year,
        "date": f"{year}-12-01",
        "lines": lines,
    }


def fixture_payload():
    """Deux décembre. Seule la seconde année est mûre. Manhattan 1+1 = 2 sur carte 256."""
    opex_young = _line("air|1,2", 1, {"0": 90, "2": 10}, 1, [0, 257])
    opex_mature = _line("air|1,2", 2, {"0": 180, "2": 20}, 200, [0, 257])
    opex_without_profit = _line("air|3,4", 1, {"0": 91}, None, [0, 514])
    opex_without_profit_next = _line("air|3,4", 2, {"0": 91}, None, [0, 514])
    aaa_young = _line("group:7", 2, {"0": 180, "2": 20}, 10, [0, 257], stations=(8, 9), towns=(30, 31))
    aaa_mature = _line("group:7", 2, {"0": 180, "2": 20}, 400, [0, 257], stations=(8, 9), towns=(30, 31))
    aaa_mail = _line("group:8", 1, {"2": 100}, 50, [10, 300], stations=(11, 12), towns=(40, 41))
    aaa_mail_next = _line("group:8", 1, {"2": 100}, 90, [10, 300], stations=(11, 12), towns=(40, 41))
    road = _line("road|1,2", 1, {"0": 30}, 999, [0, 257], mode="road")
    return {
        "campaign_id": "fixture_air_engine",
        "configuration": {"parsed": {"game_creation": {"map_x": "8", "map_y": "8"}}},
        "policies": [{"id": "reference", "explicit_settings": []}],
        "line_telemetry": {
            "snapshots": [
                _snapshot(1970, "OpexAI", [opex_young, opex_without_profit, road]),
                _snapshot(1970, "AAAHogEx", [aaa_young, aaa_mail]),
                _snapshot(1971, "OpexAI", [opex_mature, opex_without_profit_next, road]),
                _snapshot(1971, "AAAHogEx", [aaa_mature, aaa_mail_next]),
            ]
        },
    }


class AirEngineChoiceTests(unittest.TestCase):
    def test_signature_divides_by_vehicles(self):
        self.assertEqual(per_vehicle_signature({"2": 20, "0": 180}, 2), "0:90|2:10")
        self.assertEqual(per_vehicle_signature({"0": 91}, 2), "mixed")

    def test_mature_lines_signature_and_manhattan(self):
        report = analyse_campaign(fixture_payload())
        self.assertEqual(report["map"]["width"], 256)
        self.assertEqual(report["mature_air_lines"], 4)
        opex = report["by_arm"]["reference|OpexAI"]["pooled"]
        self.assertEqual(opex["models"][0]["signature"], "0:90|2:10")
        self.assertEqual(opex["profit"]["lines"], 2)
        self.assertEqual(opex["profit"]["lines_with_profit"], 1)
        self.assertEqual(opex["profit"]["profit_per_aircraft_line_level"]["median"], 100)
        self.assertEqual(opex["structure"]["aircraft_per_line"]["n"], 2)
        mixed = [item for item in opex["models"] if item["signature"] == "mixed"]
        self.assertEqual(mixed[0]["lines_with_profit"], 0)
        self.assertIsNone(mixed[0]["profit_per_aircraft_line_level"]["median"])

    def test_same_model_and_distance_still_separates_the_ais(self):
        report = analyse_campaign(fixture_payload())
        comparison = report["comparisons"][0]
        summary = comparison["matched_same_model_same_manhattan"]["summary"]
        self.assertEqual(summary["cell_count"], 1)
        self.assertEqual(summary["cells_aaa_median_strictly_higher"], 1)
        self.assertEqual(summary["conclusion_code"], "aaa_higher_inside_cells")
        cell = comparison["matched_same_model_same_manhattan"]["cells"][0]
        self.assertEqual(cell["signature"], "0:90|2:10")
        self.assertEqual(cell["distance"], 2)
        self.assertEqual(cell["median_gap_aaa_minus_opex_gbp"], 100)
        self.assertTrue(any(item["mail_only"] for item in report["by_arm"]["reference|AAAHogEx"]["pooled"]["models"]))

    def test_map_from_sibling_manifest(self):
        payload = fixture_payload()
        del payload["configuration"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "fixture_air_engine.json"
            manifest = root / "fixture_air_engine.manifest.json"
            campaign.write_text(json.dumps(payload), encoding="utf-8")
            manifest.write_text(json.dumps({
                "configuration": {"parsed": {"game_creation": {"map_x": "8", "map_y": "8"}}},
            }), encoding="utf-8")
            report = analyse_path(campaign)
        self.assertEqual(report["map"]["width"], 256)
        self.assertIn("fixture_air_engine.manifest.json", report["map"]["source"])

    def test_kitagawa_identity(self):
        opex = [
            {"profit_gbp": 10, "vehicles": 1, "signature": "A", "profit_per_aircraft_gbp": 10},
            {"profit_gbp": 30, "vehicles": 1, "signature": "B", "profit_per_aircraft_gbp": 30},
        ]
        aaa = [
            {"profit_gbp": 50, "vehicles": 1, "signature": "A", "profit_per_aircraft_gbp": 50},
            {"profit_gbp": 10, "vehicles": 1, "signature": "C", "profit_per_aircraft_gbp": 10},
        ]
        gap = decompose_profit_gap(opex, aaa, lambda row: (row["signature"],))
        self.assertAlmostEqual(gap["identity_residual_gbp"], 0)
        self.assertAlmostEqual(gap["gap_aaa_minus_opex_gbp"], 10)
        self.assertAlmostEqual(gap["composition_at_opex_rates_gbp"], 0)
        self.assertAlmostEqual(gap["same_cell_rate_gbp"], 20)
        self.assertAlmostEqual(gap["outside_support_gbp"], -10)

    def test_aaa_formula_numbers_and_incomplete_real_routes(self):
        route = {
            "dx": 0,
            "dy": 48,
            "production": 255,
            "order_distance": 48,
            "supports_big": True,
            "income_pax": lambda _distance, _days: 100,
            "income_mail": lambda _distance, _days: 0,
            "profit_model": "vehicle",
            "station_date_span": 10,
            "building_cost": 0,
            "infrastructure_cost": 0,
            "vehicles_room": 50,
            "rich": False,
            "day_length": 1,
            "future_income_rate": 100,
        }
        engine = {
            "id": "A",
            "speed": 400,
            "running_cost": 0,
            "price": 1000,
            "pax_capacity": 80,
            "mail_capacity": 0,
            "max_order_distance": 0,
            "is_big": False,
        }
        loser = dict(engine, id="B", running_cost=400000)
        too_big = dict(engine, id="C", is_big=True)
        short_range = dict(engine, id="D", max_order_distance=10)
        ranked = aaa_rank_bidirectional_passenger(
            [engine, loser, too_big, short_range],
            dict(route, supports_big=False),
        )
        self.assertEqual(ranked["winner"], "A")
        chosen = ranked["ranked"][0]
        self.assertEqual(chosen["vehicles"], 2)
        self.assertEqual(chosen["cruise_days"], 5)
        self.assertEqual(chosen["waiting"], 4)
        self.assertEqual(chosen["loading_time"], 2)
        self.assertEqual(chosen["route_income"], 730000)
        self.assertEqual(chosen["value"], 365000)
        self.assertEqual(chosen["roi"], 27037)
        reasons = {item["engine_id"]: item["reason"] for item in ranked["refused"]}
        self.assertEqual(reasons["C"], "gros_avion_aeroport")
        self.assertEqual(reasons["D"], "autonomie")
        self.assertEqual(reasons["B"], "revenu_ligne_negatif")

        _map, rows = collect_air_lines(fixture_payload())
        opex_only = [row for row in rows if row["arm"] == "OpexAI" and row["profit_gbp"] is not None]
        counterfactual = aaa_formula_counterfactual(opex_only)
        self.assertEqual(counterfactual["status"], "incomplete")
        self.assertIsNone(counterfactual["choices"])
        self.assertGreaterEqual(counterfactual["routes_with_distance"], 1)
        self.assertTrue(counterfactual["missing"])

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "fixture_air_engine.json"
            destination = root / "out.json"
            campaign.write_text(json.dumps(fixture_payload()), encoding="utf-8")
            with redirect_stdout(StringIO()):
                code = main([str(campaign), "--json", str(destination)])
            self.assertEqual(code, 0)
            written = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(written["comparisons"][0]["matched_same_model_same_manhattan"]["summary"]["cell_count"], 1)


if __name__ == "__main__":
    unittest.main()
