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
        defaults = parse_ai_settings(AI / "info.nut")
        for name in ("c121_air_first_year_rail_prep", "c121_air_one_or_two_planes"):
            self.assertEqual(defaults[name], 1, name)
        # V110, 2026-10-03 : c121_flat_bootstrap passe a 1 sur QUALIFICATION, pas
        # sur derogation. Porte A (gain_short, 40 graines x 3 ans, seuils fixes
        # avant lancement) : +135 997 £/an, 25/15/0, p_wilcoxon = 0,01154, IC95
        # bootstrap [+39 461 ; +231 092], valeur +19,13 % -> pass. Porte B
        # (non_erosion, 20 graines x 10 ans) : IC95 [-19 052 ; +307 787], borne
        # haute > 0 -> pass. Il reste inerte hors bras C121.
        self.assertEqual(defaults["c121_flat_bootstrap"], 1)
        info = source("info.nut")
        for name in ("c121_air_first_year_rail_prep", "c121_air_one_or_two_planes",
                     "c121_flat_bootstrap"):
            i = info.index('name = "%s"' % name)
            window = info[i:i + 500]
            for key in ("easy_value = 1", "medium_value = 1", "hard_value = 1",
                        "custom_value = 1", "flags = AICONFIG_BOOLEAN"):
                self.assertIn(key, window, name)
        settings = source("settings.nut")
        self.assertIn(
            'C121_FLAT_BOOTSTRAP = C121_CATALOG_INCREMENTAL\n'
            '      && AIController.GetSetting("c121_flat_bootstrap") != 0;\n'
            "  if (C121_FLAT_BOOTSTRAP) STAGED_BOOTSTRAP = false;",
            settings)
        self.assertIn(
            "C121_AIR_FIRST_YEAR_RAIL_PREP = C121_CATALOG_AIR_FIRST_YEAR\n"
            '      && AIController.GetSetting("c121_air_first_year_rail_prep") != 0;',
            settings)
        self.assertIn(
            "C121_AIR_ONE_OR_TWO_PLANES = C121_AIR_ECONOMICS\n"
            '      && AIController.GetSetting("c121_air_one_or_two_planes") != 0;',
            settings)
        self.assertLess(
            settings.index("if (C121_FLAT_BOOTSTRAP) STAGED_BOOTSTRAP = false;"),
            settings.index("C121_AIR_FIRST_YEAR_RAIL_PREP = C121_CATALOG_AIR_FIRST_YEAR"))
        self.assertLess(
            settings.index('GetSetting("c121_air_one_or_two_planes")'),
            settings.index("C121_CATALOG_FIRST_YEAR_ACTIVE = false;"))
        globals_pre = source("globals_pre.nut")
        self.assertIn("C121_AIR_FIRST_YEAR_RAIL_PREP <- false;", globals_pre)
        self.assertIn("C121_AIR_ONE_OR_TWO_PLANES <- false;", globals_pre)
        self.assertNotIn("C121_AIR_FIRST_YEAR_RAIL_PREP = false;", globals_pre)
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES = false;", globals_pre)

    def test_full_load_stays_on_aaa_only(self):
        settings = source("settings.nut")
        self.assertEqual(settings.count("if (C121_AAA_LINE) AIR_FULL_LOAD = 1;"), 1)
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES) AIR_FULL_LOAD", settings)
        air_full = settings.index("AIR_FULL_LOAD = AIController.GetSetting(\"air_full_load\");")
        aaa_force = settings.index("if (C121_AAA_LINE) AIR_FULL_LOAD = 1;")
        self.assertLess(air_full, aaa_force)
        planes_assign = settings.index("C121_AIR_ONE_OR_TWO_PLANES = C121_AIR_ECONOMICS")
        self.assertLess(planes_assign, aaa_force)

    def test_one_or_two_replaces_only_the_winner_depth(self):
        econ = source("air_economics_c121.nut")
        winner = econ.split("function OpexC121WinnerEconomics(", 1)[1].split(
            "\nfunction ", 1)[0]
        self.assertIn(
            "if (C121_AIR_ONE_OR_TWO_PLANES) {\n"
            "    return OpexC121OneOrTwoWinner(catalog, plan, plane, engineContext);\n"
            "  }",
            winner)
        self.assertLess(winner.index("OpexC121OneOrTwoWinner"),
                        winner.index("if (!fusion || C121_AAA_LINE)"))
        pair = econ.split("function OpexC121OneOrTwoWinner(", 1)[1].split(
            "function OpexC121WinnerEconomics(", 1)[0]
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 1, false)", pair)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 2, false)", pair)
        self.assertIn("return { initial = chosen, full = chosen };", pair)
        self.assertNotIn("fixedPlanes = 0", pair)
        chooser = econ.split("function OpexC121ChooseRoutePlane(", 1)[1].split(
            "\nfunction ", 1)[0]
        self.assertIn("local openingPlanes = C121_AAA_LINE ? 2 : 1;", chooser)
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES", chooser)
        self.assertEqual(econ.count("C121_AAA_LINE ? 2 : 1"), 3)
        air_econ = econ.split("function OpexC121AirEconomics(", 1)[1].split(
            "\nfunction ", 1)[0]
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES", air_econ)
        catalog = source("air_catalog_c121.nut")
        measured = catalog.split("function OpexC121MeasureBuiltEconomics(", 1)[1].split(
            "\nfunction ", 1)[0]
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES", measured)

    def test_opposite_departure_does_not_force_full_load(self):
        air = source("air_construction.nut")
        self.assertIn(
            "local hangarB = (C121_AAA_LINE || (C121_AIR_ONE_OR_TWO_PLANES && wanted == 2))\n"
            "      ? AIAirport.GetHangarOfAirport(airportB) : null;",
            air)
        self.assertIn("if (fromB && AIVehicle.IsValidVehicle(extra)) AIOrder.SkipToOrder(extra, 1);", air)
        self.assertIn("AIAirport.IsHangarTile(hangarB)", air)
        code = squirrel_code(air)
        hangar = code.split("local hangarB", 1)[1].split("for (local i = 1;", 1)[0]
        self.assertNotIn("AIR_FULL_LOAD", hangar)

    def test_year1_rail_catalog_stays_out_of_best(self):
        projects = source("projects.nut")
        gate = projects.split("if (C121_CATALOG_AIR_FIRST_YEAR && C121_CATALOG_FIRST_YEAR_ACTIVE)", 1)[1]
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
            "function OpexRailStockMergeAlternatives(", 1)[0]
        self.assertNotIn("OpexFilterRailStockGate", merge)
        self.assertIn("!C121_AIR_FIRST_YEAR_RAIL_PREP || C121_CATALOG_FIRST_YEAR_ACTIVE", merge)
        for name in ("projects.nut", "projects_update.nut", "projects_selection.nut"):
            text = source(name)
            self.assertIn(
                "if (C121_AIR_FIRST_YEAR_RAIL_PREP && !C121_CATALOG_FIRST_YEAR_ACTIVE)",
                text)
            self.assertIn("OpexRailPrepMergeAlternatives(", text)

    def test_prep_never_consumed_as_a_build_and_is_revalidated(self):
        projects = source("task_projects.nut")
        consume = projects.split("function OpexAI::_consumeResumableRailAtPassStart(", 1)[1].split(
            "local railCandidate = this._railSearch.candidate;", 1)[0]
        self.assertIn('("isC121RailPrep" in this._railSearch)', consume)
        self.assertIn('this._railSearch.phase == "build"', consume)
        self.assertIn("this._handleRailStockSearchCompleted();", consume)
        self.assertIn("return false;", consume)
        self.assertLess(consume.index("this._railSearch != null"),
                        consume.index("isC121RailPrep"))
        rail = source("task_rail.nut")
        self.assertIn('reason = "rail_prep_held"', rail)
        self.assertIn("this._revalidateRailStockPlan(candidate, candidate.railPlan);", rail)
        self.assertIn('reval.reason == "cash" || reval.reason == "no_vehicle_slot"', rail)
        self.assertIn('OpexC121RailPrepLog(this, "stock_used", 0, 0);', rail)
        self.assertIn('OpexC121RailPrepLog(this, "stock_dropped", 0, 0);', rail)
        self.assertIn("&& !c121PrepPlan", rail)
        scheduler = source("scheduler.nut")
        self.assertIn("C121_AIR_FIRST_YEAR_RAIL_PREP && this._c121RailPrepHold", scheduler)
        self.assertNotIn("_tryStartC121RailPrepSearch", source("orchestrator.nut"))

    def test_journal_is_behind_the_probe_guard(self):
        prep = source("rail_prep_c121.nut")
        log = prep.split("function OpexC121RailPrepLog(", 1)[1].split("\nfunction ", 1)[0]
        guard = log.index("if (!C121_AIR_FIRST_YEAR_RAIL_PREP || !CATALOG_COST_PROBE) return;")
        self.assertLess(guard, log.index("AIDate.GetCurrentDate()"))
        self.assertLess(guard, log.index("OpexAvailableCapital()"))
        self.assertIn(
            '"OPEX " + year + "-" + month + "-" + day\n'
            '      + " RAIL_PREP k=" + kind\n'
            '      + " cash=" + cash\n'
            '      + " avail=" + avail\n'
            '      + " air_cap=" + airCap\n'
            '      + " stock=" + stock\n'
            '      + " ops=" + ops\n'
            '      + " ticks=" + ticks',
            log)
        logged = prep + source("task_rail.nut") + source("orchestrator.nut")
        for kind in RAIL_PREP_KINDS:
            self.assertIn('"%s"' % kind, logged)
        self.assertNotIn("RAIL_PREP k=", source("projects.nut"))
        self.assertNotIn("OpexC121RailPrepLog", source("projects.nut"))

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

    def test_modified_squirrel_syntax(self):
        names = (
            "info.nut", "globals_pre.nut", "settings.nut", "rail_prep_c121.nut",
            "projects_generation.nut", "main.nut", "persist.nut", "orchestrator.nut",
            "scheduler.nut", "task_rail.nut", "task_projects.nut", "projects.nut",
            "projects_update.nut", "projects_selection.nut", "air_economics_c121.nut",
            "air_construction.nut",
        )
        for name in names:
            code = squirrel_code(source(name))
            self.assertTrue(balanced(code, "{", "}"), name + " braces")
            self.assertTrue(balanced(code, "(", ")"), name + " parens")
            self.assertTrue(balanced(code, "[", "]"), name + " brackets")
            self.assertIsNone(re.search(r"\blocal\s+static\b", code), name)
            self.assertNotIn("in null", code)


if __name__ == "__main__":
    unittest.main()
