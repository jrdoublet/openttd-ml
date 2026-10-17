#!/usr/bin/env python3
"""Tests pour V161 — valeur des renforts AIR plafonnée par un a priori net des voisines.

Couvre :
1. Contrats statiques : réglages (info.nut ↔ globals_pre.nut ↔ settings.nut), défaut 0,
   chaque point d'entrée gardé par V161_FLEET_NET_MARGINAL, exemption C70/C82 levée
   seulement pour un projet marqué v161Calibrate, aucune mesure en jeu résiduelle.
2. Modèle Python de OpexV161PerPlaneProfit et du compte de voisines de _resizeAirFleets.
"""
from __future__ import annotations

import re
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


def per_plane(model, neighbours, amort, own=13000, loss=2600):
    """Modèle Python de OpexV161PerPlaneProfit."""
    prior = own - loss * neighbours - amort
    if prior <= 0:
        return None
    if model <= prior:
        return (model, "model")
    return (prior, "prior")


def neighbours_from_index(index, station_a, station_b):
    """Modèle Python du compte de voisines (index des routes V160) dans _resizeAirFleets."""
    nb = 0
    if station_a in index:
        nb += index[station_a] - 1
    if station_b != station_a and station_b in index:
        nb += index[station_b] - 1
    return nb if nb > 0 else 0


class StaticContracts(unittest.TestCase):
    def test_settings_declared_with_default_on(self):
        # défaut 1 depuis le 13/10 (décision utilisateur après la porte A 40x3, +2,7 %) ;
        # le global reste à 0 : seul info.nut porte le défaut
        block = _setting_block("v161_fleet_net_marginal")
        self.assertIn("min_value = 0, max_value = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 1\b")
        self.assertIn("custom_value = 13000", _setting_block("v161_prior_own"))
        self.assertIn("custom_value = 2600", _setting_block("v161_prior_neighbour"))
        globals_pre = _read("globals_pre.nut")
        self.assertIn("V161_FLEET_NET_MARGINAL <- 0;", globals_pre)
        self.assertIn("V161_PRIOR_OWN <- 13000;", globals_pre)
        self.assertIn("V161_PRIOR_NEIGHBOUR <- 2600;", globals_pre)
        settings = _read("settings.nut")
        for name, glob in (("v161_fleet_net_marginal", "V161_FLEET_NET_MARGINAL"),
                           ("v161_prior_own", "V161_PRIOR_OWN"),
                           ("v161_prior_neighbour", "V161_PRIOR_NEIGHBOUR")):
            m = re.search(r'local (\w+) = AIController\.GetSetting\("' + name + r'"\);\s*'
                          r'if \(\1 >= 0\) ' + glob + r' = \1;', settings)
            self.assertIsNotNone(m, name)

    def test_every_hook_is_gated(self):
        resize = _function_body(_read("task_air.nut"), "OpexAI::_resizeAirFleets")
        self.assertIn("if (V161_FLEET_NET_MARGINAL > 0) {\n", resize)
        self.assertIn("fleetEntry.v161Neighbours <- v161Nb > 0 ? v161Nb : 0;", resize)
        # le compte reutilise l'index V160, construit une fois par passe
        self.assertIn("if (routesIndex == null) routesIndex = OpexAirBuildRoutesIndex(this._lines);\n"
                      "          local v161A", resize)
        builder = _function_body(_read("projects_builders.nut"), "OpexProjectFromFleet")
        self.assertIn("if (V161_FLEET_NET_MARGINAL > 0) {", builder)
        self.assertNotIn("c84BelowTarget", builder)
        self.assertIn("if (v161Source != null) {", builder)
        self.assertIn("project.v161Calibrate <- true;", builder)
        self.assertLess(builder.index("OpexV161PerPlaneProfit("),
                        builder.index("local capital = entry.planePrice * entry.want;"))
        build = _function_body(_read("task_projects.nut"), "OpexAI::_tryBuildFleetProject")
        self.assertIn('(("v161Source" in project) ? " v161_src=" + project.v161Source', build)

    def test_calibration_exemption_lifted_only_for_v161_projects(self):
        models = _read("projects_models.nut")
        for fn in ("OpexC70Profit", "OpexC82Profit"):
            body = _function_body(models, fn)
            self.assertIn('project.mode == "fleet"\n      && !("v161Calibrate" in project)\n'
                          "      && OpexC121ProjectHasRealization(project)) return project.profitAnnual;",
                          body, fn)
            # la valeur plafonnee par l'a priori (mesure) reste brute
            self.assertLess(body.index("profitIsObserved"), body.index("v161Calibrate"))
        builder = _function_body(_read("projects_builders.nut"), "OpexProjectFromFleet")
        self.assertIn('profitIsObserved = v161Source != "model";', builder)

    def test_in_game_cluster_measure_removed(self):
        # la mesure de grappe (smoke 12/10 : -5 a -110 k par avion, biais des lignes neuves)
        # ne doit laisser aucun champ de ligne ni lecteur residuel
        for name in ("task_report.nut", "task_projects.nut", "air_fleet.nut", "globals_pre.nut",
                     "settings.nut", "persist.nut"):
            src = _read(name)
            for token in ("V161_POOL", "V161_TREND", "v161ClusterIds", "v161ObserveYear",
                          "OpexV161ObserveClusters", "OpexV161ArmObservation"):
                self.assertNotIn(token, src, name + ":" + token)
        self.assertNotIn("line.v161", _read("air_fleet.nut"))

    def test_prior_net_of_amortisation(self):
        body = _function_body(_read("air_fleet.nut"), "OpexV161PerPlaneProfit")
        self.assertIn("local prior = V161_PRIOR_OWN - V161_PRIOR_NEIGHBOUR * neighbours - amort;", body)
        self.assertIn("if (prior <= 0) return null;", body)
        self.assertIn('if (modelPerPlane <= prior) return { profit = modelPerPlane, source = "model" };', body)
        self.assertIn("line.c121VehicleAmortPerPlane.tointeger() : 0;", body)


class PriorModel(unittest.TestCase):
    def test_cap_and_refusal(self):
        # 1972, ligne isolee : le modele C121 (79 880) est plafonne a 13 000 - 1 948
        self.assertEqual(per_plane(79880, 0, 1948), (11052, "prior"))
        # hub plein (4 voisines) : 13 000 - 10 400 - 1 948 = 652
        self.assertEqual(per_plane(41456, 4, 1948), (652, "prior"))
        # 5 voisines : refuse
        self.assertIsNone(per_plane(41456, 5, 1948))
        # un modele deja plus bas reste a sa valeur (calibree C70 ensuite)
        self.assertEqual(per_plane(4000, 2, 1948), (4000, "model"))
        self.assertEqual(per_plane(6779, 2, 1948), (5852, "prior"))

    def test_neighbour_count_matches_routes_index(self):
        # index V160 : nombre de lignes vivantes touchant chaque gare (la ligne comprise)
        index = {10: 3, 11: 3, 12: 1}
        self.assertEqual(neighbours_from_index(index, 10, 11), 4)   # hub plein (3 routes max)
        self.assertEqual(neighbours_from_index(index, 12, 10), 2)
        self.assertEqual(neighbours_from_index(index, 10, 10), 2)   # meme gare aux deux bouts
        self.assertEqual(neighbours_from_index({}, -1, -1), 0)      # gares invalides


if __name__ == "__main__":
    unittest.main()
