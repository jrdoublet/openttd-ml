#!/usr/bin/env python3
"""Tests pour V174 — sonde inverse A* rail (recherche bidirectionnelle B->A).

Contrats statiques et comportementaux :
1. Declaration : reglage `v174_rail_reverse_probe` (entier 0..1000, defaut 0 = inerte).
2. Globale et chargement : V174_RAIL_REVERSE_PROBE dans globals_pre.nut, lu une seule fois dans
   OpexLoadSettings (settings.nut), borne 0..1000.
3. Recherche reprenable : dans _startRailSearch / _continueRailSearch (task_rail.nut),
   la sonde inverse B->A est menee par tranches de RAIL_SEARCH_SLICE dans le meme creneau,
   sans nouvelle tache ni worker.
4. Inversion et compatibilite : sur succes de la sonde, les tuiles sont inversees (B->A vers A->B)
   pour s'aligner sur les plans de gare A et B, le plan recoit rev=1, et la pose de voie
   s'execute dans le bon sens.
5. Repli : si la sonde inverse epuise son budget sans chemin, la recherche principale (segmentee
   ou classique) prend le relais en deduisant les iterations consommees.
6. Synchronisation et telemetrie : OpexSearchPath integre la sonde inverse, et RAIL_ATTEMPT
   enregistre rev= (0 ou 1) apres endx=.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    needle = "function " + name + "("
    start = source.index(needle)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class Declaration(unittest.TestCase):
    def test_setting_declaration(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v174_rail_reverse_probe"]
        self.assertEqual(spec["default"], 0)
        self.assertEqual(spec["min_value"], 0)
        self.assertEqual(spec["max_value"], 1000)
        self.assertFalse(spec["boolean"])

        block = _read("info.nut").split('name = "v174_rail_reverse_probe"', 1)[1].split("});", 1)[0]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1000", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r"\s*=\s*0\b")

    def test_global_declared_in_globals_pre(self):
        content = _read("globals_pre.nut")
        self.assertIn("V174_RAIL_REVERSE_PROBE <- 0;", content)

    def test_loaded_once_in_settings(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v174_rail_reverse_probe")'), 1)
        self.assertIn("if (V174_RAIL_REVERSE_PROBE < 0) V174_RAIL_REVERSE_PROBE = 0;", body)
        self.assertIn("if (V174_RAIL_REVERSE_PROBE > 1000) V174_RAIL_REVERSE_PROBE = 1000;", body)
        for p in AI.glob("*.nut"):
            if p.name == "settings.nut":
                continue
            self.assertNotIn('AIController.GetSetting("v174_rail_reverse_probe")', p.read_text(encoding="utf-8"))


class ResumableSearchContracts(unittest.TestCase):
    def setUp(self):
        self.task_rail = _read("task_rail.nut")

    def test_start_rail_search_initializes_probe(self):
        body = _function_body(self.task_rail, "OpexAI::_startRailSearch")
        self.assertIn("V174_RAIL_REVERSE_PROBE > 0", body)
        self.assertIn("OpexCreateRailPathfinder(plan.plansB, plan.plansA, clearanceTiles)", body)
        self.assertIn("revProbe = revProbe", body)
        self.assertIn("revSpent = 0", body)
        self.assertIn("revBudget =", body)
        self.assertIn("revDone = (revProbe == null)", body)

    def test_continue_rail_search_advances_probe_in_slices(self):
        body = _function_body(self.task_rail, "OpexAI::_continueRailSearch")
        self.assertIn('state.kind == "primary"', body)
        self.assertIn('"revProbe" in state', body)
        self.assertIn("!state.revDone", body)
        self.assertIn("OpexAdvanceRailPathfinder(state.revProbe", body)
        self.assertIn("state.revSpent", body)
        # Aucune nouvelle tâche planifiée ni worker invoqué
        self.assertNotIn("_scheduler.ScheduleTask", body)
        self.assertNotIn("Worker(", body)

    def test_probe_reverses_path_on_success(self):
        body = _function_body(self.task_rail, "OpexAI::_continueRailSearch")
        self.assertIn("local rawTiles = OpexPathTiles(revResult.path);", body)
        self.assertIn("rawTiles.reverse();", body)
        self.assertIn("slice = { path = revResult.path, tiles = rawTiles, iterations = state.spent, stop = \"OK\", done = true, rev = 1 };", body)

    def test_probe_fallback_to_forward_search(self):
        body = _function_body(self.task_rail, "OpexAI::_continueRailSearch")
        # Quand revResult est NOPA ou revSpent >= revBudget, revDone passe à true
        self.assertIn('revResult.stop == "NOPA" || state.revSpent >= state.revBudget', body)
        self.assertIn("state.revDone = true;", body)
        self.assertIn("state.revProbe = null;", body)
        # Et la branche suivante reprend la recherche avant
        self.assertIn("OpexAdvanceSegmentedSearch(state.segmented", body)
        self.assertIn("OpexAdvanceRailPathfinder(state.pathfinder", body)


class SynchronousSearchContracts(unittest.TestCase):
    def setUp(self):
        self.builder_rail = _read("builder_rail.nut")

    def test_search_path_integrates_reverse_probe(self):
        body = _function_body(self.builder_rail, "OpexSearchPath")
        self.assertIn("V174_RAIL_REVERSE_PROBE > 0", body)
        self.assertIn("OpexCreateRailPathfinder(plansB, plansA, ignoredTiles)", body)
        self.assertIn("rawTiles.reverse();", body)
        self.assertIn("return { path = revResult.path, tiles = rawTiles, iterations = revSpent, stop = \"OK\", rev = 1 };", body)
        self.assertIn("iterationBudget -= revSpent;", body)
        self.assertIn("res.iterations += revSpent;", body)
        self.assertIn("res.rev <- 0;", body)


class TelemetryAndRouteCompletionContracts(unittest.TestCase):
    def setUp(self):
        self.builder_rail = _read("builder_rail.nut")
        self.task_rail = _read("task_rail.nut")

    def test_complete_route_records_rev(self):
        body = _function_body(self.builder_rail, "OpexCompleteRailRouteAfterSearch")
        self.assertIn('plan.rev <- (("rev" in search) && search.rev) ? 1 : 0;', body)

    def test_build_line_carries_rev(self):
        body = _function_body(self.builder_rail, "OpexBuildLine")
        self.assertIn('result.rev <- (("rev" in plan) && plan.rev) ? 1 : 0;', body)
        self.assertIn('rev = (("rev" in plan) && plan.rev) ? 1 : 0', body)

    def test_rail_attempt_logs_rev(self):
        body = _function_body(self.task_rail, "OpexAI::_recordRailAttempt")
        self.assertIn('OpexDecide("RAIL_ATTEMPT"', body)
        self.assertIn('endx="', body)
        self.assertIn('rev="', body)
        # rev= vient bien après endx=
        endx_pos = body.index('endx="')
        rev_pos = body.index('rev="')
        self.assertGreater(rev_pos, endx_pos)
        self.assertIn('((("rev" in result) && result.rev) ? 1 : 0)', body)


if __name__ == "__main__":
    unittest.main()
