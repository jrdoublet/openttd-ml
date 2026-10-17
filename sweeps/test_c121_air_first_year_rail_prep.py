"""Contrats statiques des reglages C121 rail-prep et 1-ou-2 avions.

Pas de partie OpenTTD : defauts, dependances, gardes de journal et de syntaxe.
"""
from pathlib import Path
import re
import unittest

from sweeps.campaign_freeze import parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

RAIL_PREP_KINDS = (
    "trigger", "catalog", "astar_start", "astar_done", "astar_fail",
    "stock_used", "stock_dropped", "yield_to_air",
)


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_code(text):
    """Masque litteraux et commentaires, en gardant les sauts de ligne."""
    return re.sub(
        r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
        lambda m: re.sub(r"[^\n]", " ", m.group()),
        text,
        flags=re.S,
    )


def balanced(text, open_ch, close_ch):
    depth = 0
    for ch in text:
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


class TestC121RailPrepAndOneOrTwoSettings(unittest.TestCase):
    def test_defaults_and_dependencies(self):
        # Decision utilisateur du 2026-10-02 : prepa rail et 1 ou 2 avions a 1
        # par defaut sur la branche C121 (derogation, sans banc de qualification).
        # Ils restent inertes hors bras C121 (c121_air_economics et
        # c121_catalog_incremental a 0 par defaut).
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c121_catalog_incremental', 'c121_catalog_air_first_year', 'c121_flat_bootstrap', 'c121_air_first_year_rail_prep', 'c121_air_one_or_two_planes'))

    def test_opposite_departure_does_not_force_full_load(self):
        air = source("air_construction.nut")
        self.assertIn(
            'local hangarB = (wanted == 2)\n      ? AIAirport.GetHangarOfAirport(airportB) : null;',
            air)
        self.assertIn("if (fromB && AIVehicle.IsValidVehicle(extra)) AIOrder.SkipToOrder(extra, 1);", air)
        self.assertIn("AIAirport.IsHangarTile(hangarB)", air)
        code = squirrel_code(air)
        hangar = code.split("local hangarB", 1)[1].split("for (local i = 1;", 1)[0]
        self.assertNotIn("AIR_FULL_LOAD", hangar)

    def test_year1_rail_catalog_stays_out_of_best(self):
        projects = source("projects.nut")
        gate = projects.split("if (MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE)", 1)[1]
        gate = gate.split("local paxBand", 1)[0]
        self.assertIn("doFreight = false;", gate)
        self.assertIn("doPaxRail = false;", gate)
        self.assertIn("doAir = true;", gate)
        prep = source("rail_prep_c121.nut")
        self.assertIn("const C121_RAIL_PREP_MAX = 3;", prep)
        self.assertIn(
            "OpexBuildCandidates(this._catalog, this._budget, this._lines,\n"
            "      this._abandonedPairs, null, null, null, null, null, true, true, PAX_BAND_ALL, null);",
            prep)
        self.assertNotIn("OpexBuildCandidates", gate)
        code = squirrel_code(prep)
        self.assertNotIn("C80_RAIL_STOCK_GATE", code)
        self.assertNotIn("C80_RAIL_STOCK_WORKER", code)
        self.assertNotIn("_tryStartRailStockWorker", code)
        self.assertIn("this._railSearch.isC121RailPrep <- true;", prep)
        merge = source("projects_generation.nut").split(
            "function OpexRailPrepMergeAlternatives(", 1)[1].split(
            "function OpexProjectAttemptKey(", 1)[0]
        self.assertNotIn("OpexFilterRailStockGate", merge)
        self.assertIn('!(MODE_AIR && MODE_RAIL) || C121_CATALOG_FIRST_YEAR_ACTIVE', merge)
        for name in ("projects.nut", "projects_update.nut", "projects_selection.nut"):
            text = source(name)
            self.assertIn(
                'if ((MODE_AIR && MODE_RAIL) && !C121_CATALOG_FIRST_YEAR_ACTIVE)',
                text)
            self.assertIn("OpexRailPrepMergeAlternatives(", text)

    def test_prep_state_is_not_saved(self):
        persist = source("persist.nut")
        save = persist.split("function OpexAI::Save()", 1)[1].split(
            "function OpexAI::Load(", 1)[0]
        for field in ("_c121RailPrepCandidates", "_c121RailPrepMonth", "_c121RailPrepHold",
                      "_c121RailPrepYieldLogged", "_c121RailPrepMinAirCap", "_railReadyStock"):
            self.assertNotIn(field, save)
        reconcile = persist.split("function OpexAI::_reconcileAfterLoad(", 1)[1]
        for field in ("_c121RailPrepCandidates = null", "_c121RailPrepMonth = -1",
                      "_c121RailPrepHold = false", "_c121RailPrepYieldLogged = false",
                      "_c121RailPrepMinAirCap = -1", "_railReadyStock = {}"):
            self.assertIn("this." + field, reconcile)

if __name__ == "__main__":
    unittest.main()
