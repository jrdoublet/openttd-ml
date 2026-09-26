#!/usr/bin/env python3
"""Tests unitaires deterministes pour analyse_p2bis_reconciliation.py."""
from __future__ import annotations

import unittest
from pathlib import Path

from sweeps.analyse_p2bis_reconciliation import (
    analyze_reconciliation,
    format_reconciliation_report,
    parse_p2bis_output,
)


class TestP2BisReconciliation(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_parse_p2_pass_all_stop_reasons(self):
        fixture = """
OPEX 1970-1-10 P2_PASS pass=1 date=1970-1-10 tick=100 in_best=64 in_cap=300000 n_built=1 stop=k_pass post_best=64 post_cap=200000 d_cap=0 d_best=0 tasks_since=catalog:catalog_refresh:1
OPEX 1970-2-10 P2_PASS pass=2 date=1970-2-10 tick=200 in_best=64 in_cap=200000 n_built=2 stop=cash post_best=0 post_cap=15000 d_cap=0 d_best=0 tasks_since=catalog:catalog_refresh:1
OPEX 1970-3-10 P2_PASS pass=3 date=1970-3-10 tick=300 in_best=0 in_cap=15000 n_built=0 stop=empty_pool post_best=0 post_cap=15000 d_cap=0 d_best=0 tasks_since=expand:expand_no_work:0
OPEX 1970-4-10 P2_PASS pass=4 date=1970-4-10 tick=400 in_best=5 in_cap=40000 n_built=0 stop=insufficient_cash post_best=5 post_cap=40000 d_cap=25000 d_best=5 tasks_since=catalog:catalog_refresh:1
OPEX 1970-5-10 P2_PASS pass=5 date=1970-5-10 tick=500 in_best=1 in_cap=50000 n_built=1 stop=list_end post_best=0 post_cap=20000 d_cap=10000 d_best=-4 tasks_since=catalog:catalog_refresh:1
OPEX 1970-6-10 P2_PASS pass=6 date=1970-6-10 tick=600 in_best=3 in_cap=60000 n_built=0 stop=rail_search post_best=3 post_cap=60000 d_cap=40000 d_best=3 tasks_since=expand:expand_no_work:0
OPEX 1970-7-10 P2_PASS pass=7 date=1970-7-10 tick=700 in_best=2 in_cap=70000 n_built=0 stop=c83_reactive post_best=2 post_cap=70000 d_cap=10000 d_best=-1 tasks_since=catalog:catalog_fresh:0
OPEX 1970-8-10 P2_PASS pass=8 date=1970-8-10 tick=800 in_best=4 in_cap=80000 n_built=1 stop=marginal_floor post_best=3 post_cap=60000 d_cap=10000 d_best=2 tasks_since=catalog:catalog_refresh:1
OPEX 1970-9-10 P2_PASS pass=9 date=1970-9-10 tick=900 in_best=3 in_cap=60000 n_built=0 stop=no_candidate_built post_best=3 post_cap=60000 d_cap=0 d_best=0 tasks_since=expand:expand_no_work:0
OPEX 1970-10-10 P2_PASS pass=10 date=1970-10-10 tick=1000 in_best=2 in_cap=60000 n_built=0 stop=invalidated post_best=2 post_cap=60000 d_cap=0 d_best=-1 tasks_since=expand:expand_no_work:0
"""
        data = parse_p2bis_output(fixture, seed=100)
        self.assertEqual(len(data["passes"]), 10)
        summary = analyze_reconciliation(data, max_year=1970)
        self.assertEqual(summary["n_passes"], 10)
        self.assertEqual(summary["n_useful"], 4)
        self.assertEqual(summary["n_empty"], 1)
        self.assertEqual(summary["n_examined"], 5)
        self.assertEqual(summary["total_projects_built"], 5)

        stops = summary["stop_counts_all"]
        expected_stops = {
            "k_pass", "cash", "empty_pool", "insufficient_cash", "list_end",
            "rail_search", "c83_reactive", "marginal_floor", "no_candidate_built",
            "invalidated",
        }
        self.assertEqual(set(stops.keys()), expected_stops)

    def test_reconciliation_funded_immediate_vs_empty(self):
        fixture = """
OPEX 1970-1-1 P2_PASS pass=1 date=1970-1-1 tick=100 in_best=10 in_cap=100000 n_built=1 stop=k_pass post_best=9 post_cap=70000 d_cap=0 d_best=0 tasks_since=none
OPEX 1970-1-25 P2_PASS pass=2 date=1970-1-25 tick=300 in_best=9 in_cap=70000 n_built=1 stop=cash post_best=0 post_cap=10000 d_cap=0 d_best=0 tasks_since=catalog:catalog_refresh:1
OPEX 1970-1-27 P2_PASS pass=3 date=1970-1-27 tick=330 in_best=0 in_cap=10000 n_built=0 stop=empty_pool post_best=0 post_cap=10000 d_cap=0 d_best=0 tasks_since=expand:expand_no_work:0
OPEX 1970-1-29 P2_PASS pass=4 date=1970-1-29 tick=360 in_best=0 in_cap=10000 n_built=0 stop=empty_pool post_best=0 post_cap=10000 d_cap=0 d_best=0 tasks_since=expand:expand_no_work:0
OPEX 1970-2-15 P2_PASS pass=5 date=1970-2-15 tick=600 in_best=5 in_cap=50000 n_built=1 stop=list_end post_best=0 post_cap=20000 d_cap=40000 d_best=5 tasks_since=catalog:catalog_refresh:1
"""
        data = parse_p2bis_output(fixture, seed=42)
        summary = analyze_reconciliation(data, max_year=1970)
        self.assertEqual(summary["n_passes"], 5)
        self.assertEqual(summary["n_useful"], 3)
        self.assertEqual(summary["funded_count"], 1)
        self.assertEqual(summary["funded_outcomes"].get("immediate_build"), 1)
        self.assertEqual(summary["unaff_count"], 2)
        self.assertEqual(summary["empty_episodes_count"], 1)
        self.assertEqual(summary["empty_episodes_sum"], 2)

    def test_report_generation(self):
        fixture = """
OPEX 1970-1-1 P2_PASS pass=1 date=1970-1-1 tick=100 in_best=10 in_cap=100000 n_built=1 stop=k_pass post_best=9 post_cap=70000 d_cap=0 d_best=0 tasks_since=none
OPEX 1970-1-25 P2_PASS pass=2 date=1970-1-25 tick=300 in_best=9 in_cap=70000 n_built=1 stop=cash post_best=0 post_cap=10000 d_cap=0 d_best=0 tasks_since=catalog:catalog_refresh:1
"""
        data = parse_p2bis_output(fixture, seed=42)
        summary = analyze_reconciliation(data, max_year=1970)
        report = format_reconciliation_report(summary, [42])
        self.assertIn("Rapport P2 bis", report)
        self.assertIn("Arrêt par seuil K_pass", report)
        self.assertIn("Arrêt trésorerie", report)


if __name__ == "__main__":
    unittest.main()
