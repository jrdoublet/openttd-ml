#!/usr/bin/env python3
"""Tests pour V166 — interrupteurs de mode d'OpexAI (air, rail, route, eau).

Contrats statiques :
1. Réglages `mode_*` déclarés à 1 (info.nut ↔ globals_pre.nut ↔ settings.nut), lus avant les
   faisceaux `policy_*`.
2. Chaque mode est coupé à sa source unique :
   - air : catalogue vide (`_refreshAir`), le chemin « aucun appareil disponible » ;
   - eau : aucune coque au catalogue (`_refreshWater`) ;
   - rail : `OpexBuildCandidates`, seul point d'entrée des candidats rail, et `OpexBuildProjects` ;
   - route : `ROAD_BUILD_ENABLED`, qui garde aussi le catalogue route et le rabattement.
3. Sans avion, l'année 1 « AIR seul » est désactivée (sinon une partie rail seul ne génère rien la
   première année) ; sans rail, sa préparation rail aussi.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
MODES = ("air", "rail", "road", "water")


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


class Settings(unittest.TestCase):
    def test_settings_default_on(self):
        globals_pre = _read("globals_pre.nut")
        settings = _read("settings.nut")
        for mode in MODES:
            block = _setting_block("mode_" + mode)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(block, key + r" = 1\b")
            self.assertIn("AICONFIG_BOOLEAN", block)
            glob = "MODE_" + mode.upper()
            self.assertIn(glob + " <- true;", globals_pre)
            self.assertIn(glob + ' = AIController.GetSetting("mode_' + mode + '") != 0;', settings)

    def test_modes_read_before_policies(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        first_policy = body.index('GetSetting("policy_rail")')
        for mode in MODES:
            self.assertLess(body.index('GetSetting("mode_' + mode + '")'), first_policy)


class Gates(unittest.TestCase):
    def test_air_catalog_empty(self):
        body = _function_body(_read("catalog.nut"), "OpexCatalog::_refreshAir")
        guard = body.index("if (!MODE_AIR) return;")
        # le catalogue est vide AVANT la sortie : c'est le chemin « aucun appareil » existant
        for reset in ("this.airport = null;", "this.airCombos = [];", "this.airPlaneChoicesByAirport = {};"):
            self.assertLess(body.index(reset), guard)
        # l'ordonnanceur AIR et la reconstruction C78 se taisent sur ce catalogue vide
        air = _function_body(_read("task_air.nut"), "OpexAI::_tryBuildAir")
        self.assertIn("(combos == null || combos.len() == 0) && this._catalog.airport == null", air)
        c78 = _function_body(_read("scheduler_tasks.nut"), "OpexC78StartCatalogAirRebuild")
        self.assertIn("if (!doAir || !hasAir) return false;", c78)

    def test_water_catalog_empty(self):
        body = _function_body(_read("catalog.nut"), "OpexCatalog::_refreshWater")
        self.assertLess(body.index("this.ships = [];"), body.index("if (!MODE_WATER) return;"))
        plans = _function_body(_read("builder_water.nut"), "OpexWaterPlans")
        self.assertIn("if (catalog.ships.len() == 0 || catalog.paxCargo < 0) {", plans)

    def test_rail_candidates_single_entry(self):
        body = _function_body(_read("candidates.nut"), "OpexBuildCandidates")
        gate = body.index("if (!MODE_RAIL) {")
        self.assertLess(gate, body.index("if (generatePax) {"))
        self.assertRegex(body[gate:gate + 120], r"generatePax = false;\s*generateFreight = false;")
        # aucun autre appelant des generateurs rail que OpexBuildCandidates
        for name in ("OpexPaxCandidates", "OpexFreightCandidates", "OpexGoodsChainCandidates"):
            for path in AI.glob("*.nut"):
                src = path.read_text(encoding="utf-8")
                calls = len(re.findall(r"(?<!function )\b" + name + r"\(", src))
                if path.name == "candidates.nut":
                    self.assertEqual(calls, 1, name)
                else:
                    self.assertEqual(calls, 0, (path.name, name))

    def test_rail_projects_flags(self):
        body = _function_body(_read("projects.nut"), "OpexBuildProjects")
        override = body.index("if (C121_CATALOG_AIR_FIRST_YEAR && C121_CATALOG_FIRST_YEAR_ACTIVE) {")
        gate = body.index("if (!MODE_RAIL) {")
        self.assertLess(override, gate)
        self.assertLess(gate, body.index("if (doPaxRail || doFreight) {"))
        self.assertRegex(body[gate:gate + 80], r"doFreight = false;\s*doPaxRail = false;")
        for flag, mode in (("doRoad", "ROAD"), ("doAir", "AIR"), ("doWater", "WATER")):
            line = "if (!MODE_" + mode + ") " + flag + " = false;"
            self.assertLess(body.index(line), body.index('OpexDecide("BOOTSTRAP_STAGE"'))

    def test_road_gate(self):
        settings = _read("settings.nut")
        self.assertIn("ROAD_BUILD_ENABLED = polRoad && MODE_ROAD;", settings)
        self.assertEqual(settings.count("ROAD_BUILD_ENABLED ="), 1)
        # le catalogue route (dont depend le rabattement) n'est rafraichi que sous ROAD_BUILD_ENABLED
        refresh = _function_body(_read("catalog.nut"), "OpexCatalog::refresh")
        self.assertLess(refresh.index("if (ROAD_BUILD_ENABLED) {"), refresh.index("this._refreshRoad();"))
        feeder = _function_body(_read("feeder_bus.nut"), "OpexBuildFeederCandidates")
        self.assertIn("!(catalog.paxCargo in catalog.roadEngineByCargo)) return [];", feeder)
        road = _function_body(_read("task_road.nut"), "OpexAI::_tryBuildRoadProject")
        self.assertLess(road.index("if (!ROAD_BUILD_ENABLED"), road.index("_tryBuildFeederProject"))

    def test_road_off_keeps_airport_joined_stops(self):
        # sans catalogue route, le type de route courant reste pose pour les arrets joints aux
        # aeroports : sans lui, BuildDriveThroughRoadStation echoue (0 arret en air seul, 13/10)
        refresh = _function_body(_read("catalog.nut"), "OpexCatalog::refresh")
        gate = refresh.index("if (ROAD_BUILD_ENABLED) {")
        other = refresh.index("} else if (AIR_JOINED_STOPS && AIRoad.IsRoadTypeAvailable(AIRoad.ROADTYPE_ROAD)) {")
        self.assertLess(gate, other)
        self.assertLess(refresh.index("this._refreshRoad();"), other)
        self.assertIn("AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);", refresh[other:other + 600])

    def test_first_year_air_only_needs_air(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        first_year = body.index("C121_CATALOG_AIR_FIRST_YEAR = C121_CATALOG_INCREMENTAL")
        off = body.index("if (!MODE_AIR) C121_CATALOG_AIR_FIRST_YEAR = false;")
        prep = body.index("C121_AIR_FIRST_YEAR_RAIL_PREP = C121_CATALOG_AIR_FIRST_YEAR\n")
        no_rail = body.index("if (!MODE_RAIL) C121_AIR_FIRST_YEAR_RAIL_PREP = false;")
        self.assertLess(first_year, off)
        self.assertLess(off, prep)
        self.assertLess(prep, no_rail)
        self.assertEqual(body.count("C121_CATALOG_AIR_FIRST_YEAR ="), 2)
        self.assertEqual(body.count("C121_AIR_FIRST_YEAR_RAIL_PREP ="), 2)


if __name__ == "__main__":
    unittest.main()
