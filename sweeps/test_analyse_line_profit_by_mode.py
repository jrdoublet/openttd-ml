#!/usr/bin/env python3
"""Tests unitaires pour sweeps/analyse_line_profit_by_mode.py et contrat des traces C56."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from sweeps.analyse_line_profit_by_mode import (
    compute_mode_summary,
    format_num,
    format_pct,
    format_pounds,
    mean,
    median,
    parse_raw_records,
    process_lines,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


class TestLineProfitAnalysis(unittest.TestCase):
    def test_math_helpers(self):
        self.assertIsNone(mean([]))
        self.assertIsNone(median([]))
        self.assertEqual(mean([10.0, 20.0, 30.0]), 20.0)
        self.assertEqual(median([10.0, 20.0, 30.0]), 20.0)
        self.assertEqual(median([10.0, 20.0, 30.0, 40.0]), 25.0)

    def test_format_helpers(self):
        self.assertEqual(format_pounds(None), "None")
        self.assertEqual(format_pct(None), "None")
        self.assertEqual(format_num(None), "None")
        self.assertEqual(format_pounds(50000), "50 000 £")
        self.assertEqual(format_pounds(-12000), "-12 000 £")
        self.assertEqual(format_pct(0.125), "12.5 %")
        self.assertEqual(format_num(3.1415, 2), "3.14")

    def test_deduplication(self):
        logs = [
            json.dumps({"seed": 1, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=10 opsclk=10 year=1973 profit=10000 veh=2 mode=rail"}),
            # Doublon exact du même enregistrement pour la même année de profit (1972)
            json.dumps({"seed": 1, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=10 opsclk=10 year=1973 profit=10000 veh=2 mode=rail"}),
            # Autre année de profit (1973, rapportée en 1974)
            json.dumps({"seed": 1, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=20 opsclk=20 year=1974 profit=12000 veh=2 mode=rail"}),
        ]
        seeds_raw, dup_count = parse_raw_records(logs)
        self.assertEqual(dup_count, 1)
        self.assertEqual(len(seeds_raw[1]["profit_obs"]), 2)

    def test_build_year_exclusion(self):
        # Ligne construite en 1971.
        # Rapport 1972 -> profit 1971 (année de construction, incomplète)
        # Rapport 1973 -> profit 1972 (année pleine)
        # Rapport 1974 -> profit 1973 (année pleine)
        logs = [
            json.dumps({"seed": 10, "grep": "OPEX 1971-06-01 C56_TASK RAIL_COMMISSION primary line=5 src=1 dst=2 cost=100000 dist=50 trains=2 iters=500 delay_days=10 search_to_service_days=5"}),
            json.dumps({"seed": 10, "grep": "OPEX 1972-01-01 C56_TASK LINE_PROFIT name=5 cycle=- tick=10 opsclk=10 year=1972 profit=2000 veh=2 mode=rail capital=100000 dist=50 built=1971"}),
            json.dumps({"seed": 10, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=5 cycle=- tick=20 opsclk=20 year=1973 profit=20000 veh=2 mode=rail capital=100000 dist=50 built=1971"}),
            json.dumps({"seed": 10, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=5 cycle=- tick=30 opsclk=30 year=1974 profit=30000 veh=2 mode=rail capital=100000 dist=50 built=1971"}),
        ]
        seeds_raw, _ = parse_raw_records(logs)

        # 1. Par défaut (exclusion de l'année de mise en service)
        res_excl = process_lines(seeds_raw, include_incomplete_year=False)
        line_excl = res_excl["rail_lines"][0]
        self.assertTrue(line_excl["has_incomplete_year"])
        self.assertEqual(line_excl["full_years_count"], 2)
        # Moyenne de (20000 + 30000) / 2 = 25000
        self.assertEqual(line_excl["profit_per_year"], 25000.0)
        self.assertEqual(line_excl["roi_annual"], 0.25)

        # 2. Avec inclusion de l'année de mise en service
        res_incl = process_lines(seeds_raw, include_incomplete_year=True)
        line_incl = res_incl["rail_lines"][0]
        self.assertEqual(line_incl["full_years_count"], 3)
        # Moyenne de (2000 + 20000 + 30000) / 3 = 17333.333...
        self.assertAlmostEqual(line_incl["profit_per_year"], 52000.0 / 3.0)

    def test_preserve_none_not_zero(self):
        # Ligne sans capital et sans distance
        logs = [
            json.dumps({"seed": 99, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=42 year=1973 profit=1000 veh=1 mode=road"}),
        ]
        seeds_raw, _ = parse_raw_records(logs)
        res = process_lines(seeds_raw)
        road_stat = res["total_summary"]["road"]
        self.assertIsNone(road_stat["capital_mean"], "Capital manquant doit être None")
        self.assertIsNone(road_stat["roi_annual_mean"], "ROI avec capital manquant doit être None")
        self.assertIsNone(road_stat["age_mean"], "Âge avec année de construction manquante doit être None")

    def test_rail_line_breakdown(self):
        logs = [
            json.dumps({"seed": 1, "grep": "OPEX 1972-04-10 C56_TASK RAIL_COMMISSION primary line=1 src=10 dst=20 cost=120000 dist=75 trains=2"}),
            json.dumps({"seed": 1, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=1 year=1973 profit=3000 veh=2 mode=rail capital=120000 dist=75 built=1972"}),
            json.dumps({"seed": 1, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=1 year=1974 profit=18000 veh=2 mode=rail capital=120000 dist=75 built=1972"}),
            json.dumps({"seed": 1, "grep": "OPEX 1973-01-01 C56_TASK RAIL_COMMISSION primary line=2 src=30 dst=40 cost=160000 dist=110 trains=1"}),
            json.dumps({"seed": 1, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=2 year=1974 profit=-5000 veh=1 mode=rail capital=160000 dist=110 built=1973"}),
            json.dumps({"seed": 1, "grep": "OPEX 1975-01-01 C56_TASK LINE_PROFIT name=2 year=1975 profit=-6000 veh=1 mode=rail capital=160000 dist=110 built=1973"}),
        ]
        seeds_raw, _ = parse_raw_records(logs)
        res = process_lines(seeds_raw)
        rail_summary = res["total_summary"]["rail"]
        self.assertEqual(rail_summary["lines_count"], 2)
        self.assertEqual(rail_summary["negative_lines_count"], 1)
        self.assertEqual(rail_summary["negative_profit_share"], 0.5)

        lines = res["rail_lines"]
        self.assertEqual(len(lines), 2)
        l1 = lines[0]
        self.assertEqual(l1["line_id"], 1)
        self.assertEqual(l1["distance"], 75.0)
        self.assertEqual(l1["trains"], 2)
        self.assertEqual(l1["capital"], 120000.0)
        self.assertEqual(l1["profit_per_year"], 18000.0)
        self.assertEqual(l1["status"], "PROFITABLE")

        l2 = lines[1]
        self.assertEqual(l2["line_id"], 2)
        self.assertEqual(l2["distance"], 110.0)
        self.assertEqual(l2["trains"], 1)
        self.assertEqual(l2["capital"], 160000.0)
        self.assertEqual(l2["profit_per_year"], -6000.0)
        self.assertEqual(l2["status"], "LOSS")


class TestSquirrelTraceContracts(unittest.TestCase):
    """Vérifie que les traces C56 sont complètes, homogènes et gardées."""

    def test_task_report_emits_line_profit_for_all_modes_under_guard(self):
        report = _read("ai/OpexAI/task_report.nut")
        # Ne doit plus être restreint à vehicleType == AIVehicle.VT_AIR
        self.assertNotIn("if (C56_TASK_TRACE && vehicleType == AIVehicle.VT_AIR)", report)
        self.assertIn("if (C56_TASK_TRACE)", report)

        # Vérifier que les champs mode, capital, dist et built sont bien émis
        self.assertIn('OpexC56TaskLog("LINE_PROFIT"', report)
        idx = report.index('OpexC56TaskLog("LINE_PROFIT"')
        call_snippet = report[idx:idx + 500]
        self.assertIn('" mode=" + modeName', call_snippet)
        self.assertIn('" capital=" + cap', call_snippet)
        self.assertIn('" dist=" + dist', call_snippet)
        self.assertIn('" built=" + buildYr', call_snippet)

    def test_task_rail_records_capital_and_emits_rail_commission(self):
        rail = _read("ai/OpexAI/task_rail.nut")
        # Vérifier RAIL_COMMISSION enrichi
        self.assertIn('OpexC56TaskLog("RAIL_COMMISSION"', rail)
        idx = rail.index('OpexC56TaskLog("RAIL_COMMISSION"')
        snippet = rail[idx:idx + 350]
        self.assertIn('" cost=" + result.capital', snippet)
        self.assertIn('" dist=" + candidate.distance', snippet)
        self.assertIn('" trains=" + result.trains', snippet)

        # Le capital vient des traces de construction (jointure par line=) : rien n'est ajoute
        # aux tables de lignes, pour ne changer ni la sauvegarde ni le chemin par defaut.
        self.assertNotIn("capital = result.capital, actualCost", rail)

    def test_road_water_build_traces_under_probe_only(self):
        for path, kind in (("ai/OpexAI/task_road.nut", "ROAD_BUILT"), ("ai/OpexAI/task_water.nut", "WATER_BUILT")):
            src = _read(path)
            idx = src.index('OpexC56TaskLog("' + kind + '"')
            self.assertIn("if (C56_TASK_TRACE) {", src[idx - 60:idx])
            self.assertIn('"line=" + ', src[idx:idx + 200])
            self.assertIn('" cost=" + ', src[idx:idx + 200])
        for path in ("ai/OpexAI/task_road.nut", "ai/OpexAI/task_town.nut", "ai/OpexAI/task_water.nut"):
            self.assertNotIn("actualCost = ", _read(path))


if __name__ == "__main__":
    unittest.main()
