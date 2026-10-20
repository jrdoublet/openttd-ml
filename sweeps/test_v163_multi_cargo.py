#!/usr/bin/env python3
"""Retrait V163 fret ; contrats de la plomberie second cargo conservee pour V207.

Le dimensionnement, le devis, les constructeurs et les champs de lignes restent
couverts. Les generateurs et extracteurs fret propres a V163 sont retires.
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
        self.assertNotIn('name = "v163_multi_cargo"', _read("info.nut"))
        self.assertNotIn("V163_MULTI_CARGO", _read("globals_pre.nut"))
        self.assertNotIn('GetSetting("v163_multi_cargo")', _read("settings.nut"))

    def test_generation_guarded(self):
        body = _function_body(_read("candidates.nut"), "OpexFreightCandidates")
        self.assertIn("local others2 = null;", body)
        self.assertNotIn("OpexV163SourceOtherCargos", body)
        reeval = _function_body(_read("economy.nut"), "OpexV163CandidateSecondary")
        self.assertIn('V207_RAIL_MAIL && (("kind" in candidate) && candidate.kind == "pax")', reeval)

    def test_secondary_cargo_selection(self):
        for name in ("OpexV163SourceOtherCargos", "OpexV163SecondaryCargo"):
            self.assertNotIn(name, _read("economy.nut"))

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
        self.assertNotIn("line.wagons + OpexV163Wagons2(line) >= OpexRailNominalMaxWagons(line.platformLength)", src)
        self.assertEqual(src.count("OpexV163WagonsPrice(this._catalog, line)"), 2)

    def test_probe_decision_log_only(self):
        src = _read("task_report.nut")
        start = src.index("V163 : le second cargo est-il reellement charge")
        dl = src.rfind("if (DECISION_LOG) {", 0, start)
        self.assertGreater(dl, 0)
        # la sonde vit dans le bloc DECISION_LOG de LINE_REVENUE, avant l'appel
        self.assertLess(start, src.index('OpexDecide("LINE_REVENUE"', dl))
        self.assertIn("AIVehicle.GetCargoLoad(v, line.cargo2)", src)
        self.assertIn('" wait2_a=" + AIStation.GetCargoWaiting(stationA, line.cargo2)', src)


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
