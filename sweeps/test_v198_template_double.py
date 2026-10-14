#!/usr/bin/env python3
"""Tests de contrats statiques pour V198 — Double voie par gabarits de gare d'AAAHogEx.

Contrats statiques :
1. Déclaration :
   - `v198_template_double` déclaré dans info.nut (booléen, défaut 0 sur tous profils).
   - Variable globale V198_TEMPLATE_DOUBLE initialisée à false dans globals_pre.nut.
   - OpexV198Active() actif seulement si V198_TEMPLATE_DOUBLE et OpexV190Active().
   - Lecture unique dans settings.nut.
2. Inertie au défaut (0) :
   - À 0, OpexV198Active() retourne false.
   - builder_rail.nut et economy.nut restent au comportement V190/historique.
3. Gabarits de gare (rail_templates.nut) :
   - Gabarit source à boucle (SrcRailStation AAAHogEx) avec 4 orientations (NW, NE, SW, SE).
   - Gabarit destination traversant (DestRailStation AAAHogEx) avec 4 orientations.
   - Points de raccord départ/arrivée conformes au modèle.
   - Dépôt sur la boucle source et signaux PBS.
4. Ordonnancement et rollback :
   - Voie 1 avec outwardSide, Voie 2 avec guideTiles et tuiles interdites.
   - Signaux de cantonnement tous les ~7 tuiles.
   - Rollback atomique sur échec (démolition voies, gares, dépôt, signaux) + repli voie unique.
5. Économie et devis :
   - candidate.capital / OpexLineEconomics inclut 2 voies, gares gabarits et signaux.
   - Prédiction 2 trains.
6. Enregistrement de ligne et clonage :
   - line.doubleTrack = 1, line.loop = 1, line.v181Loop = true.
   - Compatibilité _expandRailLines pour ajout de rames.
7. Journalisation DECISION_LOG :
   - OpexDecide("V198", "step=... ok=... reason=...").
8. Sécurité des mots réservés et syntaxe Squirrel :
   - Aucun 'clone', 'parent', 'base' comme identifiant.
   - Syntaxe équilibrée (accolades, parenthèses, crochets).
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


class Declaration(unittest.TestCase):
    def test_setting_in_info_nut(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertIn("v198_template_double", specs)
        s = specs["v198_template_double"]
        self.assertEqual(s["default"], 0)
        self.assertTrue(s["boolean"])

        content = _read("info.nut")
        block = content.split('name = "v198_template_double"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")

    def test_global_and_active_helper_in_globals_pre(self):
        content = _read("globals_pre.nut")
        self.assertIn("V198_TEMPLATE_DOUBLE <- false;", content)
        body = _function_body(content, "OpexV198Active")
        self.assertIn("V198_TEMPLATE_DOUBLE && OpexV190Active()", body)

    def test_setting_loaded_in_settings_nut(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v198_template_double")'), 1)
        self.assertIn('V198_TEMPLATE_DOUBLE = AIController.GetSetting("v198_template_double") != 0;', body)

    def test_main_requires_rail_templates(self):
        main = _read("main.nut")
        self.assertIn('require("rail_templates.nut");', main)


class InertDefault(unittest.TestCase):
    def test_inert_when_setting_zero(self):
        # When V198_TEMPLATE_DOUBLE is false, OpexV198Active() returns false
        builder = _read("builder_rail.nut")
        build_line = _function_body(builder, "OpexBuildLine")
        self.assertIn("if (OpexV198Active() && candidate.kind == \"freight\")", build_line)
        self.assertIn("return OpexV198ExecuteRailPlan(", build_line)
        # Fallback to V190 or legacy is intact
        self.assertIn("if (OpexV190Active() && candidate.kind == \"freight\")", build_line)
        self.assertIn("return OpexExecuteRailPlan(", build_line)


class RailTemplatesDesign(unittest.TestCase):
    def setUp(self):
        self.templates = _read("rail_templates.nut")

    def test_orientations_defined(self):
        self.assertIn("const OPEX_ORIENT_NW = 0;", self.templates)
        self.assertIn("const OPEX_ORIENT_NE = 1;", self.templates)
        self.assertIn("const OPEX_ORIENT_SW = 2;", self.templates)
        self.assertIn("const OPEX_ORIENT_SE = 3;", self.templates)

    def test_source_template_geometry(self):
        # Origin from platform and platform from origin for all 4 orientations
        self.assertIn("function OpexSourceOriginFromPlatform(platformTile, orientation, length)", self.templates)
        self.assertIn("function OpexSourcePlatformFromOrigin(originTile, orientation, length)", self.templates)
        body_origin = _function_body(self.templates, "OpexSourceOriginFromPlatform")
        for orient in ("OPEX_ORIENT_SE", "OPEX_ORIENT_SW", "OPEX_ORIENT_NW", "OPEX_ORIENT_NE"):
            self.assertIn(orient, body_origin)

        # Rails for source loop
        body_rails = _function_body(self.templates, "OpexSourceRails")
        self.assertIn("OpexSourceAt(originTile, 0, 1, orientation)", body_rails)
        self.assertIn("OpexSourceAt(originTile, 0, 0, orientation)", body_rails)
        self.assertIn("OpexSourceAt(originTile, 1, 0, orientation)", body_rails)
        self.assertIn("OpexSourceAt(originTile, 2, 0, orientation)", body_rails)
        self.assertIn("OpexSourceAt(originTile, 2, 1, orientation)", body_rails)

    def test_dest_template_geometry(self):
        self.assertIn("function OpexDestOriginFromPlatform(platformTile, orientation, length)", self.templates)
        self.assertIn("function OpexDestPlatformFromOrigin(originTile, orientation, length)", self.templates)
        body_origin = _function_body(self.templates, "OpexDestOriginFromPlatform")
        for orient in ("OPEX_ORIENT_SE", "OPEX_ORIENT_SW", "OPEX_ORIENT_NW", "OPEX_ORIENT_NE"):
            self.assertIn(orient, body_origin)

        body_dest_rails = _function_body(self.templates, "OpexDestRails")
        self.assertIn("OpexDestAt(originTile, 0, length, orientation, length)", body_dest_rails)

    def test_test_mode_and_accounting_shield(self):
        body_test_src = _function_body(self.templates, "OpexTestSourceTemplate")
        self.assertIn("AITestMode()", body_test_src)
        self.assertIn("AIAccounting()", body_test_src)

        body_test_dst = _function_body(self.templates, "OpexTestDestTemplate")
        self.assertIn("AITestMode()", body_test_dst)
        self.assertIn("AIAccounting()", body_test_dst)

    def test_site_search_reusing_platform_cargo_value(self):
        body_find_src = _function_body(self.templates, "OpexFindSourceTemplateSite")
        self.assertIn("OpexRailPlatformCargoValue(platformBase, ", body_find_src)
        self.assertIn("OpexTestSourceTemplate(", body_find_src)

        body_find_dst = _function_body(self.templates, "OpexFindDestTemplateSite")
        self.assertIn("OpexRailPlatformCargoValue(platformBase, ", body_find_dst)
        self.assertIn("OpexTestDestTemplate(", body_find_dst)

    def test_pbs_signals_built(self):
        body_real_src = _function_body(self.templates, "OpexBuildSourceTemplateReal")
        self.assertIn("BuildSignal", body_real_src)
        self.assertIn("SIGNALTYPE_PBS", body_real_src)

        body_real_dst = _function_body(self.templates, "OpexBuildDestTemplateReal")
        self.assertIn("BuildSignal", body_real_dst)
        self.assertIn("SIGNALTYPE_PBS", body_real_dst)

    def test_block_signals_on_running_tracks(self):
        self.assertIn("function OpexBuildBlockSignals(tiles, interval = 7)", self.templates)
        body_sig = _function_body(self.templates, "OpexBuildBlockSignals")
        self.assertIn("BuildSignal(cur, prev,", body_sig)


class ExecutionAndRollback(unittest.TestCase):
    def setUp(self):
        self.templates = _read("rail_templates.nut")
        self.exec_body = _function_body(self.templates, "OpexV198ExecuteRailPlan")

    def test_track1_outward_and_track2_guided(self):
        self.assertIn("OpexSearchPath(plansA1, plansB1,", self.exec_body)
        self.assertIn("OpexV197BuildGuideTiles(tiles1, 1, forbidden)", self.exec_body)
        self.assertIn("OpexSearchPath(plansA2, plansB2, plan.iterationBudget, deadlineTick, ignored2, null, null, guideTiles)", self.exec_body)

    def test_demolition_and_fallback_at_every_step(self):
        self.assertIn("OpexDemolishSourceTemplate", self.templates)
        self.assertIn("OpexDemolishDestTemplate", self.templates)
        self.assertIn("OpexDemolishTrack", self.templates)
        self.assertIn("function OpexV198FallbackSingle(", self.templates)

        # Rollback on template build failure
        self.assertIn("OpexDemolishSourceTemplate(builtSrc);", self.exec_body)
        self.assertIn("OpexDemolishDestTemplate(builtDst);", self.exec_body)
        # Rollback on track 1 path failure
        self.assertIn("step=path_track1 ok=0", self.exec_body)
        # Rollback on track 2 path failure
        self.assertIn("step=path_track2 ok=0", self.exec_body)
        # Rollback on track build failure
        self.assertIn("OpexDemolishTrack(tiles1);", self.exec_body)
        self.assertIn("OpexDemolishTrack(tiles2);", self.exec_body)
        # Rollback on train failure
        self.assertIn("step=build_train ok=0", self.exec_body)

    def test_train_creation_and_shared_orders_compatibility(self):
        self.assertIn("OpexBuildTrains(", self.exec_body)
        self.assertIn("result.doubleTrack <- 1;", self.exec_body)
        self.assertIn("result.loop <- 1;", self.exec_body)
        self.assertIn("result.v181Loop <- true;", self.exec_body)
        self.assertIn("result.stationA2 <- builtSrc.platformTile;", self.exec_body)
        self.assertIn("result.stationB2 <- builtDst.platformTile;", self.exec_body)
        self.assertIn("result.depot2 <- builtSrc.depotTile;", self.exec_body)


class EconomyAndQuoting(unittest.TestCase):
    def test_line_economics_accounts_for_v198_infra_and_trains(self):
        econ = _read("economy.nut")
        body = _function_body(econ, "OpexLineEconomics")
        self.assertIn("if (OpexV198Active() && kind == \"freight\")", body)
        self.assertIn("3 * platformLength * catalog.costStation", body)
        self.assertIn("2 * travelDist * effectiveTrackCost", body)
        self.assertIn("numSignals", body)
        self.assertIn("local startTrains = (OpexV190Active() && kind == \"freight\") ? 2 : 1;", body)


class LineRegistration(unittest.TestCase):
    def test_task_rail_records_loop_and_v181_loop(self):
        task = _read("task_rail.nut")
        self.assertIn('loop = ("loop" in result) ? result.loop : 0,', task)
        self.assertIn('v181Loop = ("v181Loop" in result) ? result.v181Loop : false,', task)


class DecisionLogging(unittest.TestCase):
    def test_v198_decision_logging(self):
        templates = _read("rail_templates.nut")
        self.assertIn('OpexDecide("V198", "step=place_src', templates)
        self.assertIn('OpexDecide("V198", "step=place_dst', templates)
        self.assertIn('OpexDecide("V198", "step=build_src', templates)
        self.assertIn('OpexDecide("V198", "step=build_dst', templates)
        self.assertIn('OpexDecide("V198", "step=path_track1', templates)
        self.assertIn('OpexDecide("V198", "step=path_track2', templates)
        self.assertIn('OpexDecide("V198", "step=build_track1', templates)
        self.assertIn('OpexDecide("V198", "step=build_track2', templates)
        self.assertIn('OpexDecide("V198", "step=build_train', templates)
        self.assertIn('OpexDecide("V198", "step=fallback_single', templates)
        self.assertIn('OpexDecide("V198", "step=complete ok=1', templates)


class SquirrelSafetyAndSyntax(unittest.TestCase):
    def test_no_reserved_keywords(self):
        templates = _read("rail_templates.nut")
        for kw in ("clone", "parent", "base"):
            pattern = rf"\b(local|function)\s+{kw}\b"
            self.assertIsNone(re.search(pattern, templates), f"Reserved keyword '{kw}' found as local/function in rail_templates.nut")
            param_pattern = rf"\(\s*{kw}\s*[,)]"
            self.assertIsNone(re.search(param_pattern, templates), f"Reserved keyword '{kw}' used as parameter in rail_templates.nut")

    def test_balanced_braces_and_parens(self):
        for name in ("info.nut", "globals_pre.nut", "settings.nut", "rail_templates.nut", "builder_rail.nut", "task_rail.nut", "economy.nut"):
            content = _read(name)
            clean = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            clean = re.sub(r'//.*$', '', clean, flags=re.MULTILINE)
            clean = re.sub(r'"(\\.|[^"\\])*"', '""', clean)

            self.assertEqual(clean.count("{"), clean.count("}"), f"Unbalanced braces in {name}")
            self.assertEqual(clean.count("("), clean.count(")"), f"Unbalanced parens in {name}")
            self.assertEqual(clean.count("["), clean.count("]"), f"Unbalanced brackets in {name}")


if __name__ == "__main__":
    unittest.main()
