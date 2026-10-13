#!/usr/bin/env python3
"""Tests pour V163 — second cargo d'une ligne rail de fret (même source, même destination).

Couvre :
1. Contrats statiques : réglage (info.nut ↔ globals_pre.nut ↔ settings.nut), défaut 0, génération
   gardée par V163_MULTI_CARGO, second cargo repassé aux deux réévaluations du constructeur,
   wagons du second cargo construits, comptés au capital et dans les limites de quai.
2. Modèle Python du dimensionnement des wagons du second cargo dans OpexLineEconomics.
"""
from __future__ import annotations

import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
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


def _setting_block(name: str) -> str:
    info = _read("info.nut")
    start = info.index('name = "' + name + '"')
    return info[start:info.index("});", start)]


def wagons2(monthly2, capacity2, trips, wagons, max_wagons, rating_pct=50):
    """Modèle Python du dimensionnement V163 (avant le choix de locomotive)."""
    w = math.ceil((monthly2 * rating_pct / 100.0) / (capacity2 * trips))
    if w < 1:
        w = 1
    if wagons + w > max_wagons:
        w = max_wagons - wagons
    return max(w, 0)


class StaticContracts(unittest.TestCase):
    def test_setting_default_off(self):
        block = _setting_block("v163_multi_cargo")
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")
        self.assertIn("V163_MULTI_CARGO <- false;", _read("globals_pre.nut"))
        self.assertIn('V163_MULTI_CARGO = AIController.GetSetting("v163_multi_cargo") == 1;',
                      _read("settings.nut"))

    def test_generation_guarded(self):
        body = _function_body(_read("candidates.nut"), "OpexFreightCandidates")
        self.assertIn("local secondary = V163_MULTI_CARGO\n"
                      "            ? OpexV163SecondaryCargo(catalog, source.id, industries[di].id, cargo) : null;",
                      body)
        self.assertEqual(body.count("OpexV163SecondaryCargo"), 1)
        reeval = _function_body(_read("economy.nut"), "OpexV163CandidateSecondary")
        self.assertIn("if (!V163_MULTI_CARGO", reeval)

    def test_secondary_cargo_selection(self):
        body = _function_body(_read("economy.nut"), "OpexV163SecondaryCargo")
        self.assertIn("c == cargo", body)
        self.assertIn("AIIndustry.IsCargoAccepted(sinkId, c) != AIIndustry.CAS_ACCEPTED", body)
        self.assertIn("(c in catalog.wagonByCargo)", body)
        self.assertIn("monthly <= 0", body)

    def test_builder_reevaluations_keep_secondary(self):
        src = _read("builder_rail.nut")
        self.assertEqual(src.count("OpexV163CandidateSecondary(candidate)"), 2)

    def test_economics_counts_secondary(self):
        body = _function_body(_read("economy.nut"), "OpexLineEconomics")
        self.assertIn("vehicleCost += trains * wagons2 * wagon2.price;", body)
        self.assertIn("revenueAnnual += revenue2;", body)
        self.assertIn("OpexRailWantedPlatformLength(wagons + wagons2, catalog.platformLength)", body)
        self.assertIn("if (wagons + wagons2 > maxWagons) wagons2 = maxWagons - wagons;", body)
        # une reevaluation sur le quai reel doit pouvoir remettre le second cargo a zero
        apply = _function_body(_read("economy.nut"), "OpexApplyRailEconomics")
        self.assertIn("candidate.wagons2 = economics.wagons2;", apply)
        self.assertIn('} else if ("wagons2" in candidate) {', apply)

    def test_trains_built_with_secondary_wagons(self):
        src = _read("builder_rail.nut")
        body = _function_body(src, "OpexBuildTrains")
        self.assertIn("wagons + wagons2 > nominalMaxWagons", body)
        self.assertIn("w < wagons ? wagon.id : wagon2.id", body)
        # construction initiale (2 rames), doublement et second train passent le second cargo
        self.assertEqual(src.count("OpexV163Cargo2(candidate), OpexV163Wagons2(candidate)"), 2)
        self.assertEqual(src.count("OpexV163Cargo2(line), OpexV163Wagons2(line)"), 2)
        # definition + doublement + second train
        self.assertEqual(src.count("OpexV163WagonsPrice(catalog, line)"), 3)
        quote = _function_body(src, "OpexQuoteRailCapital")
        self.assertIn("OpexV163WagonsPrice(catalog, candidate)", quote)

    def test_line_and_expansion(self):
        src = _read("task_rail.nut")
        self.assertIn("built.cargo2 <- candidate.cargo2;", src)
        self.assertIn("built.wagons2 <- candidate.wagons2;", src)
        self.assertIn("line.wagons + OpexV163Wagons2(line) >= OpexRailNominalMaxWagons(line.platformLength)", src)
        self.assertEqual(src.count("OpexV163WagonsPrice(this._catalog, line)"), 2)


class SizingModel(unittest.TestCase):
    def test_prorata_production(self):
        # ferme : 90 GRAI et 60 LVST par mois, 1,5 trajet charge par mois, wagons de 30
        self.assertEqual(wagons2(60, 30, 1.5, 1, 7), 1)
        self.assertEqual(wagons2(180, 30, 1.0, 2, 7), 3)

    def test_platform_room(self):
        self.assertEqual(wagons2(180, 30, 1.0, 6, 7), 1)
        self.assertEqual(wagons2(180, 30, 1.0, 7, 7), 0)


if __name__ == "__main__":
    unittest.main()
