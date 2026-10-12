#!/usr/bin/env python3
"""Tests pour V160 — fleet.resize : indexation des routes air par aéroport.

Couvre :
1. Contrats statiques :
   - Présence du réglage air_fleet_routes_index dans info.nut (0/1/2, défaut 0).
   - Présence de la globale AIR_FLEET_ROUTES_INDEX dans globals_pre.nut (défaut 0).
   - Chargement dans settings.nut.
   - Présence des spans sous PROBE_SPAN_TRACE (fleet.cadence_cap, fleet.marginal, fleet.add_plane,
     fleet.first_live, fleet.refusal, fleet.sort).
   - Invalidation de l'index (remise à null) lors de modifications/achats/refleet.
   - Journalisation de non-concordance sous AIR_FLEET_ROUTES_INDEX == 2.
2. Équivalence fonctionnelle :
   - Implémentation de référence (OpexAirLiveRoutesAtAirport) vs implémentation indexée
     (OpexAirBuildRoutesIndex + lookup indexé).
   - Jeux de lignes aléatoires, stations partagées, lignes mortes, même station aux deux bouts,
     véhicules valides vs invalides, modes non-air.
"""
from __future__ import annotations

import random
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def simulate_live_routes_at_airport(airport_station_id: int, lines: list[dict]) -> int:
    """Modèle exact en Python de OpexAirLiveRoutesAtAirport."""
    if airport_station_id is None or airport_station_id < 0 or lines is None:
        return 0
    routes = 0
    for other in lines:
        if other.get("mode") != "air":
            continue
        live = False
        if "vehicles" in other and other["vehicles"] is not None:
            for v in other["vehicles"]:
                if v.get("valid", False):
                    live = True
                    break
        elif "vehicle" in other and other["vehicle"] is not None:
            if other["vehicle"].get("valid", False):
                live = True
        if not live:
            continue
        other_a = other.get("stationA_id", -1)
        other_b = other.get("stationB_id", -1)
        if other_a == airport_station_id or other_b == airport_station_id:
            routes += 1
    return routes


def simulate_build_routes_index(lines: list[dict]) -> dict[int, int]:
    """Modèle exact en Python de OpexAirBuildRoutesIndex."""
    index: dict[int, int] = {}
    if lines is None:
        return index
    for other in lines:
        if other.get("mode") != "air":
            continue
        live = False
        if "vehicles" in other and other["vehicles"] is not None:
            for v in other["vehicles"]:
                if v.get("valid", False):
                    live = True
                    break
        elif "vehicle" in other and other["vehicle"] is not None:
            if other["vehicle"].get("valid", False):
                live = True
        if not live:
            continue
        other_a = other.get("stationA_id", -1)
        other_b = other.get("stationB_id", -1)
        valid_a = other_a is not None and other_a >= 0
        valid_b = other_b is not None and other_b >= 0
        if valid_a:
            index[other_a] = index.get(other_a, 0) + 1
        if valid_b and (not valid_a or other_b != other_a):
            index[other_b] = index.get(other_b, 0) + 1
    return index


class TestV160FleetRoutesIndexStaticContracts(unittest.TestCase):
    def setUp(self):
        self.globals = _read("ai/OpexAI/globals_pre.nut")
        self.info = _read("ai/OpexAI/info.nut")
        self.settings = _read("ai/OpexAI/settings.nut")
        self.task_air = _read("ai/OpexAI/task_air.nut")
        self.air_trip = _read("ai/OpexAI/air_trip.nut")

    def test_setting_declaration_and_defaults(self):
        self.assertIn("AIR_FLEET_ROUTES_INDEX <- 0;", self.globals)
        self.assertIn('name = "air_fleet_routes_index"', self.info)

        # Check info.nut values (must all be 0)
        idx = self.info.index('name = "air_fleet_routes_index"')
        block = self.info[idx : idx + 350]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 2", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)
        self.assertIn("custom_value = 0", block)

        # Check settings.nut loading
        self.assertIn('local afri = AIController.GetSetting("air_fleet_routes_index");', self.settings)
        self.assertIn("if (afri >= 0) AIR_FLEET_ROUTES_INDEX = afri;", self.settings)

    def test_spans_in_task_air(self):
        # Spans must be gated on PROBE_SPAN_TRACE with zero overhead when off
        self.assertIn('OpexSpanAgg("fleet.cadence_cap", spCap)', self.task_air)
        self.assertIn('OpexSpanAgg("fleet.marginal", spMarg)', self.task_air)
        self.assertIn('OpexSpanAgg("fleet.add_plane", spAdd)', self.task_air)
        self.assertIn('OpexSpanAgg("fleet.first_live", spFirstLive)', self.task_air)
        self.assertIn('OpexSpanAgg("fleet.refusal", spRef)', self.task_air)
        self.assertIn('OpexSpanAgg("fleet.sort", spSort)', self.task_air)

        # Check gating
        self.assertIn('PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null', self.task_air)

    def test_functions_in_air_trip(self):
        self.assertIn("function OpexAirBuildRoutesIndex(lines)", self.air_trip)
        self.assertIn("function OpexAirCadenceCapIndexed(line, catalog, lines, routesIndex)", self.air_trip)
        self.assertIn("function OpexAirCadenceCap(line, catalog, lines, routesIndex = null)", self.air_trip)

    def test_index_invalidation_points(self):
        # Invalidation must occur whenever vehicles/lines can change during the pass
        resize_body = self.task_air[self.task_air.index("function OpexAI::_resizeAirFleets") :]
        # Crash recovery invalidation
        self.assertIn("routesIndex = null;", resize_body)
        # Check that routesIndex = null occurs at multiple points (V92 resumed, crash refleet, add plane)
        self.assertGreaterEqual(resize_body.count("routesIndex = null;"), 3)

    def test_comparison_mode_and_mismatch_logging(self):
        self.assertIn("if (AIR_FLEET_ROUTES_INDEX == 1)", self.task_air)
        self.assertIn("else if (AIR_FLEET_ROUTES_INDEX == 2)", self.task_air)
        self.assertIn('OpexDecide("FLEET_ROUTES_MISMATCH"', self.task_air)
        self.assertIn('OpexDecide("FLEET_ROUTES_INDEX"', self.task_air)


class TestV160FleetRoutesEquivalence(unittest.TestCase):
    def test_empty_lines(self):
        lines = []
        idx = simulate_build_routes_index(lines)
        self.assertEqual(idx, {})
        self.assertEqual(simulate_live_routes_at_airport(10, lines), 0)

    def test_single_line_distinct_stations(self):
        lines = [
            {
                "mode": "air",
                "stationA_id": 10,
                "stationB_id": 20,
                "vehicles": [{"valid": True}],
            }
        ]
        idx = simulate_build_routes_index(lines)
        self.assertEqual(idx.get(10, 0), 1)
        self.assertEqual(idx.get(20, 0), 1)
        self.assertEqual(idx.get(30, 0), 0)

        self.assertEqual(simulate_live_routes_at_airport(10, lines), idx.get(10, 0))
        self.assertEqual(simulate_live_routes_at_airport(20, lines), idx.get(20, 0))
        self.assertEqual(simulate_live_routes_at_airport(30, lines), idx.get(30, 0))

    def test_single_line_same_station_both_ends(self):
        lines = [
            {
                "mode": "air",
                "stationA_id": 10,
                "stationB_id": 10,
                "vehicles": [{"valid": True}],
            }
        ]
        idx = simulate_build_routes_index(lines)
        # Must count exactly ONCE for station 10
        self.assertEqual(idx.get(10, 0), 1)
        self.assertEqual(simulate_live_routes_at_airport(10, lines), 1)

    def test_dead_lines_ignored(self):
        lines = [
            {
                "mode": "air",
                "stationA_id": 10,
                "stationB_id": 20,
                "vehicles": [{"valid": False}],
            },
            {
                "mode": "air",
                "stationA_id": 10,
                "stationB_id": 30,
                "vehicle": {"valid": False},
            },
            {
                "mode": "air",
                "stationA_id": 10,
                "stationB_id": 40,
                "vehicles": [],
            },
        ]
        idx = simulate_build_routes_index(lines)
        self.assertEqual(idx, {})
        for st in (10, 20, 30, 40):
            self.assertEqual(simulate_live_routes_at_airport(st, lines), 0)

    def test_non_air_lines_ignored(self):
        lines = [
            {
                "mode": "rail",
                "stationA_id": 10,
                "stationB_id": 20,
                "vehicles": [{"valid": True}],
            },
            {
                "mode": "road",
                "stationA_id": 10,
                "stationB_id": 30,
                "vehicles": [{"valid": True}],
            },
        ]
        idx = simulate_build_routes_index(lines)
        self.assertEqual(idx, {})
        self.assertEqual(simulate_live_routes_at_airport(10, lines), 0)

    def test_multiple_lines_and_shared_airports_random_equivalence(self):
        rng = random.Random(42)
        stations = list(range(1, 15))

        for iteration in range(50):
            lines = []
            num_lines = rng.randint(0, 30)
            for _ in range(num_lines):
                st_a = rng.choice(stations)
                st_b = rng.choice(stations)
                mode = rng.choice(["air", "air", "air", "rail", "road"])
                veh_mode = rng.choice(["list", "single", "empty"])
                has_live = rng.choice([True, False])

                line = {
                    "mode": mode,
                    "stationA_id": st_a,
                    "stationB_id": st_b,
                }
                if veh_mode == "list":
                    num_v = rng.randint(1, 5)
                    vehs = []
                    for i in range(num_v):
                        vehs.append({"valid": has_live and (i == 0 or rng.choice([True, False]))})
                    line["vehicles"] = vehs
                elif veh_mode == "single":
                    line["vehicle"] = {"valid": has_live}
                else:
                    line["vehicles"] = []

                lines.append(line)

            index = simulate_build_routes_index(lines)

            for st in stations:
                direct = simulate_live_routes_at_airport(st, lines)
                indexed = index.get(st, 0)
                self.assertEqual(
                    direct,
                    indexed,
                    f"Mismatch at station {st} on iteration {iteration}: direct={direct}, indexed={indexed}",
                )


if __name__ == "__main__":
    unittest.main()
