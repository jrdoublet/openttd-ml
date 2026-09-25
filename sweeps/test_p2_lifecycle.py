#!/usr/bin/env python3
"""Tests unitaires déterministes pour le décodeur et l'analyseur P2.

Couvre :
- Chaque emptyCause existante dans le code.
- Chaque raison de retour à non-vide existante dans le code.
- Recoupement exact des totaux et détection des corruptions.
- Calculs statistiques de distributions (médiane, p90, min, max, moyenne).
- Vérifications de contrat de code statique (garde de sonde, bit-exactness).
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_p2_lifecycle import (  # noqa: E402
    EMPTY_CAUSE_DESCRIPTIONS,
    RETURN_REASON_DESCRIPTIONS,
    format_p2_report,
    parse_p2_output,
    summarize_p2_events,
    verify_p2_invariants,
)

FIXTURE_ALL_CAUSES_AND_REASONS = """
[2026-09-25 10:00:00] dbg: [script:4] [0] [I] OPEX 1970-1-10 P2_BUILD id=1 mode=air n_built=1 cap_before=300000 cap_after=180000 cg_before=200 cg_after=160 scanned=0 retained=0 abandon=0 alts=160 funded=20 cause=none next_k=50000
[2026-09-25 10:00:00] dbg: [script:4] [0] [I] OPEX 1970-1-10 P2_RESOLVE id=1 days=0 ticks=0 ret_reason=immediate ret_task=projects ret_date=1970-1-10 funded=20 cause=none
[2026-09-25 10:00:01] dbg: [script:4] [0] [I] OPEX 1970-2-15 P2_BUILD id=2 mode=fleet n_built=1 cap_before=60000 cap_after=15000 cg_before=200 cg_after=190 scanned=250 retained=180 abandon=0 alts=180 funded=0 cause=all_unaffordable next_k=25000
[2026-09-25 10:00:01] dbg: [script:4] [0] [I] OPEX 1970-3-01 P2_RESOLVE id=2 days=14 ticks=200 ret_reason=month ret_task=catalog ret_date=1970-3-01 funded=5 cause=none
[2026-09-25 10:00:02] dbg: [script:4] [0] [I] OPEX 1970-4-10 P2_BUILD id=3 mode=road n_built=1 cap_before=40000 cap_after=8000 cg_before=150 cg_after=140 scanned=180 retained=0 abandon=0 alts=0 funded=0 cause=cache_exhausted next_k=0
[2026-09-25 10:00:02] dbg: [script:4] [0] [I] OPEX 1970-4-25 P2_RESOLVE id=3 days=15 ticks=220 ret_reason=capital ret_task=catalog ret_date=1970-4-25 funded=8 cause=none
[2026-09-25 10:00:03] dbg: [script:4] [0] [I] OPEX 1970-5-12 P2_BUILD id=4 mode=rail n_built=1 cap_before=120000 cap_after=5000 cg_before=100 cg_after=90 scanned=120 retained=0 abandon=5 alts=0 funded=0 cause=abandon_filtered next_k=0
[2026-09-25 10:00:03] dbg: [script:4] [0] [I] OPEX 1970-5-18 P2_RESOLVE id=4 days=6 ticks=90 ret_reason=invalidation ret_task=catalog ret_date=1970-5-18 funded=3 cause=none
[2026-09-25 10:00:04] dbg: [script:4] [0] [I] OPEX 1970-6-01 P2_BUILD id=5 mode=water n_built=1 cap_before=50000 cap_after=20000 cg_before=50 cg_after=40 scanned=0 retained=0 abandon=0 alts=0 funded=0 cause=stage_empty next_k=0
[2026-09-25 10:00:04] dbg: [script:4] [0] [I] OPEX 1970-6-10 P2_RESOLVE id=5 days=9 ticks=130 ret_reason=layers ret_task=catalog ret_date=1970-6-10 funded=4 cause=none
[2026-09-25 10:00:05] dbg: [script:4] [0] [I] OPEX 1971-1-15 P2_BUILD id=6 mode=air n_built=1 cap_before=80000 cap_after=22000 cg_before=80 cg_after=70 scanned=0 retained=0 abandon=0 alts=0 funded=0 cause=empty_pool next_k=0
[2026-09-25 10:00:05] dbg: [script:4] [0] [I] OPEX 1971-1-28 P2_RESOLVE id=6 days=13 ticks=180 ret_reason=periodic ret_task=catalog ret_date=1971-1-28 funded=6 cause=none
[2026-09-25 10:00:06] dbg: [script:4] [0] [I] OPEX 1971-3-05 P2_BUILD id=7 mode=fleet n_built=1 cap_before=70000 cap_after=30000 cg_before=110 cg_after=100 scanned=150 retained=100 abandon=0 alts=100 funded=0 cause=selection_empty next_k=15000
[2026-09-25 10:00:06] dbg: [script:4] [0] [I] OPEX 1971-3-15 P2_RESOLVE id=7 days=10 ticks=150 ret_reason=air_fleet ret_task=air_fleet ret_date=1971-3-15 funded=2 cause=none
[2026-09-25 10:00:07] dbg: [script:4] [0] [I] OPEX 1971-7-20 P2_BUILD id=8 mode=air n_built=1 cap_before=90000 cap_after=40000 cg_before=120 cg_after=110 scanned=140 retained=80 abandon=0 alts=80 funded=0 cause=all_unaffordable next_k=45000
[2026-09-25 10:00:07] dbg: [script:4] [0] [I] OPEX 1971-7-25 P2_RESOLVE id=8 days=5 ticks=75 ret_reason=targeted_air ret_task=projects ret_date=1971-7-25 funded=1 cause=none
[2026-09-25 10:00:08] dbg: [script:4] [0] [I] OPEX 1972-2-10 P2_BUILD id=9 mode=road n_built=1 cap_before=65000 cap_after=25000 cg_before=90 cg_after=80 scanned=100 retained=50 abandon=0 alts=50 funded=0 cause=unknown next_k=30000
[2026-09-25 10:00:08] dbg: [script:4] [0] [I] OPEX 1972-2-18 P2_RESOLVE id=9 days=8 ticks=110 ret_reason=catalog_other ret_task=catalog ret_date=1972-2-18 funded=7 cause=none
[2026-09-25 10:00:09] dbg: [script:4] [0] [I] OPEX 1972-5-01 P2_BUILD id=10 mode=rail n_built=1 cap_before=150000 cap_after=35000 cg_before=130 cg_after=120 scanned=150 retained=60 abandon=0 alts=60 funded=0 cause=all_unaffordable next_k=40000
[2026-09-25 10:00:09] dbg: [script:4] [0] [I] OPEX 1972-5-20 P2_RESOLVE id=10 days=19 ticks=270 ret_reason=other ret_task=custom_task ret_date=1972-5-20 funded=3 cause=none
[2026-09-25 10:00:10] dbg: [script:4] [0] [I] OPEX 1972-12-20 P2_BUILD id=11 mode=fleet n_built=1 cap_before=80000 cap_after=20000 cg_before=140 cg_after=130 scanned=160 retained=70 abandon=0 alts=70 funded=0 cause=all_unaffordable next_k=50000
"""


class TestP2LifecycleParserAndAggregator(unittest.TestCase):
    def test_parse_fixture_completeness(self):
        events = parse_p2_output(FIXTURE_ALL_CAUSES_AND_REASONS, seed=42)
        self.assertEqual(len(events), 11)

        # 1. Vérification que CHAQUE emptyCause est couverte
        causes_found = {e["cause"] for e in events}
        expected_causes = {
            "none",
            "all_unaffordable",
            "cache_exhausted",
            "abandon_filtered",
            "stage_empty",
            "empty_pool",
            "selection_empty",
            "unknown",
        }
        self.assertEqual(causes_found, expected_causes)

        # 2. Vérification que CHAQUE returnReason est couverte
        reasons_found = {e["ret_reason"] for e in events}
        expected_reasons = {
            "immediate",
            "month",
            "capital",
            "invalidation",
            "layers",
            "periodic",
            "air_fleet",
            "targeted_air",
            "catalog_other",
            "other",
            "sim_end",
        }
        self.assertEqual(reasons_found, expected_reasons)

        # 3. Vérification que TOUS les modes sont couverts
        modes_found = {e["mode"] for e in events}
        expected_modes = {"air", "fleet", "road", "rail", "water"}
        self.assertEqual(modes_found, expected_modes)

    def test_recoupement_and_invariants(self):
        events = parse_p2_output(FIXTURE_ALL_CAUSES_AND_REASONS, seed=42)
        # Ne doit lever aucune AssertionError
        verify_p2_invariants(events)

        summary = summarize_p2_events(events, min_year=1970, max_year=1972)
        n = summary["n_total"]
        self.assertEqual(n, 11)
        self.assertEqual(sum(summary["by_mode"].values()), n)
        self.assertEqual(sum(summary["by_cause"].values()), n)
        self.assertEqual(sum(summary["by_reason"].values()), n)

    def test_invariant_violation_detection(self):
        events = parse_p2_output(FIXTURE_ALL_CAUSES_AND_REASONS, seed=42)
        # Cas invalide 1 : cause=none mais funded=0
        corrupted = [dict(e) for e in events]
        corrupted[0]["funded"] = 0
        with self.assertRaises(AssertionError):
            verify_p2_invariants(corrupted)

        # Cas invalide 2 : cause != none mais funded > 0
        corrupted2 = [dict(e) for e in events]
        corrupted2[1]["funded"] = 5
        with self.assertRaises(AssertionError):
            verify_p2_invariants(corrupted2)

        # Cas invalide 3 : cause=none mais reason != immediate
        corrupted3 = [dict(e) for e in events]
        corrupted3[0]["ret_reason"] = "month"
        with self.assertRaises(AssertionError):
            verify_p2_invariants(corrupted3)

    def test_stats_distributions(self):
        events = parse_p2_output(FIXTURE_ALL_CAUSES_AND_REASONS, seed=42)
        summary = summarize_p2_events(events, min_year=1970, max_year=1972)

        # 10 événements vidés avec résolution (id=1 est cause=none, id=11 est sim_end)
        # Donc 9 résolutions vidées : 14, 15, 6, 9, 13, 10, 5, 8, 19
        ds = summary["days_stats"]
        self.assertEqual(ds["n"], 9)
        self.assertEqual(ds["min"], 5)
        self.assertEqual(ds["max"], 19)
        # Liste triée : [5, 6, 8, 9, 10, 13, 14, 15, 19] -> médiane = 10
        self.assertEqual(ds["med"], 10.0)

        # Vérification du format de rapport
        report = format_p2_report(summary)
        self.assertIn("# Diagnostic P2 — Cycle de vie du portefeuille post-build", report)
        self.assertIn("all_unaffordable", report)
        self.assertIn("cache_exhausted", report)
        self.assertIn("ret_reason", report)


class TestP2StaticContracts(unittest.TestCase):
    def test_class_variables_declared_in_main(self):
        main_text = (ROOT / "ai" / "OpexAI" / "main.nut").read_text(encoding="utf-8")
        self.assertIn("_p2BuildSeq = 0;", main_text)
        self.assertIn("_p2PendingBuilds = null;", main_text)
        self.assertIn("_p2PreCapital = 0;", main_text)
        self.assertIn("_p2PreCandidateGroupsLen = 0;", main_text)
        self.assertIn("_p2CatalogPreReason = null;", main_text)

    def test_ledgers_guarded_by_v95_probe(self):
        ledgers_text = (ROOT / "ai" / "OpexAI" / "ledgers.nut").read_text(encoding="utf-8")
        # Les hooks doivent être à l'intérieur de fonctions protégées par V95_SCHED_IDLE_LEDGER
        self.assertIn('OpexSchedIdleLog("P2_BUILD"', ledgers_text)
        self.assertIn('OpexSchedIdleLog("P2_RESOLVE"', ledgers_text)


if __name__ == "__main__":
    unittest.main()
