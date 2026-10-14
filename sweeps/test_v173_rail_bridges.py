#!/usr/bin/env python3
"""Tests pour V173 — portees max de ponts/tunnels et cout tunnel du pathfinder rail.

Contexte :
AAAHogEx autorise des ponts de 30 tuiles, des tunnels de 11 (ou 14) tuiles, et fixe le
cout unitaire de tunnel par tuile a 0 (ai/AAAHogEx-115/pathfinder.nut:133-141).
OpexAI etait bride a 6 tuiles pour les ponts, 6 tuiles pour les tunnels, et taxait les
tunnels a 120 (ai/OpexAI/pathfinder_v90/rail.nut:64-70).

Trois reglages introduits (style V168, inertes par defaut) :
- `v173_rail_max_bridge` (entier 0..30, defaut 0 = inerte / historique 6 tuiles)
- `v173_rail_max_tunnel` (entier 0..30, defaut 0 = inerte / historique 6 tuiles)
- `v173_rail_tunnel_cost` (entier -1..200, defaut -1 = inerte / historique 120 ; >=0 remplace 120)

Contrats statiques :
1. Declarations dans info.nut : bornes, defauts inertes (0, 0, -1) sur tous les profils de difficulte.
2. Initialisation dans globals_pre.nut et chargement borne dans settings.nut::OpexLoadSettings.
3. Prise en compte dans le constructeur de OpexRailPathFinderV90 et dans OpexRailPathfinderCheckerV90.
4. Support des accesseurs de cout dans OpexRailPathFinderV90.Cost (_set et _get).
5. Application dans OpexCreateRailPathfinder et OpexAdvanceSegmentedSearch (couvre voie principale,
   seconde voie, stock et reparation).
6. Prise en compte par OpexRailPathFinderV129 (heritage de V90, InitializePath, _TunnelsBridgesInto, _Cost).
7. Construction reelle et simulation de cout adaptees dynamiquement via AIBridgeList_Length et AITunnel.BuildTunnel.
8. Absence de longueur 6 hardcodee ailleurs dans le rail d'OpexAI.
"""
from __future__ import annotations

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
    def test_settings_declared(self):
        specs = parse_ai_setting_specs(AI / "info.nut")

        spec_b = specs["v173_rail_max_bridge"]
        self.assertEqual(spec_b["default"], 0)
        self.assertFalse(spec_b["boolean"])
        self.assertEqual((spec_b["min_value"], spec_b["max_value"]), (0, 30))

        spec_t = specs["v173_rail_max_tunnel"]
        self.assertEqual(spec_t["default"], 0)
        self.assertFalse(spec_t["boolean"])
        self.assertEqual((spec_t["min_value"], spec_t["max_value"]), (0, 30))

        spec_c = specs["v173_rail_tunnel_cost"]
        self.assertEqual(spec_c["default"], -1)
        self.assertFalse(spec_c["boolean"])
        self.assertEqual((spec_c["min_value"], spec_c["max_value"]), (-1, 200))

    def test_settings_all_difficulties_inert(self):
        info_text = _read("info.nut")
        for setting_name, default_val in [
            ("v173_rail_max_bridge", 0),
            ("v173_rail_max_tunnel", 0),
            ("v173_rail_tunnel_cost", -1),
        ]:
            block = info_text.split(f'name = "{setting_name}"', 1)[1].split("});", 1)[0]
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(block, key + rf"\s*=\s*{default_val}\b")

    def test_globals_declared(self):
        globals_text = _read("globals_pre.nut")
        self.assertIn("V173_RAIL_MAX_BRIDGE <- 0;", globals_text)
        self.assertIn("V173_RAIL_MAX_TUNNEL <- 0;", globals_text)
        self.assertIn("V173_RAIL_TUNNEL_COST <- -1;", globals_text)

    def test_loaded_and_clamped(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v173_rail_max_bridge")'), 1)
        self.assertEqual(body.count('AIController.GetSetting("v173_rail_max_tunnel")'), 1)
        self.assertEqual(body.count('AIController.GetSetting("v173_rail_tunnel_cost")'), 1)

        self.assertIn("if (V173_RAIL_MAX_BRIDGE < 0) V173_RAIL_MAX_BRIDGE = 0;", body)
        self.assertIn("else if (V173_RAIL_MAX_BRIDGE > 30) V173_RAIL_MAX_BRIDGE = 30;", body)

        self.assertIn("if (V173_RAIL_MAX_TUNNEL < 0) V173_RAIL_MAX_TUNNEL = 0;", body)
        self.assertIn("else if (V173_RAIL_MAX_TUNNEL > 30) V173_RAIL_MAX_TUNNEL = 30;", body)

        self.assertIn("if (V173_RAIL_TUNNEL_COST < -1) V173_RAIL_TUNNEL_COST = -1;", body)
        self.assertIn("else if (V173_RAIL_TUNNEL_COST > 200) V173_RAIL_TUNNEL_COST = 200;", body)


class PathfinderV90Integration(unittest.TestCase):
    def test_constructor_defaults_respect_v173(self):
        rail_nut = _read("pathfinder_v90/rail.nut")
        self.assertIn(
            "this._cost_tunnel_per_tile = (V173_RAIL_TUNNEL_COST >= 0) ? V173_RAIL_TUNNEL_COST : 120;",
            rail_nut,
        )
        self.assertIn(
            "this._max_bridge_length = (V173_RAIL_MAX_BRIDGE > 0) ? V173_RAIL_MAX_BRIDGE : 6;",
            rail_nut,
        )
        self.assertIn(
            "this._max_tunnel_length = (V173_RAIL_MAX_TUNNEL > 0) ? V173_RAIL_MAX_TUNNEL : 6;",
            rail_nut,
        )

    def test_checker_constructor_sync(self):
        rail_nut = _read("pathfinder_v90/rail.nut")
        checker_ctor = rail_nut.split("class OpexRailPathfinderCheckerV90", 1)[1].split("function InitializePath", 1)[0]
        self.assertIn("if (V173_RAIL_MAX_BRIDGE > 0) this._orig.cost.max_bridge_length = V173_RAIL_MAX_BRIDGE;", checker_ctor)
        self.assertIn("if (V173_RAIL_MAX_TUNNEL > 0) this._orig.cost.max_tunnel_length = V173_RAIL_MAX_TUNNEL;", checker_ctor)
        self.assertIn("if (V173_RAIL_TUNNEL_COST >= 0) this._orig.cost.tunnel_per_tile = V173_RAIL_TUNNEL_COST;", checker_ctor)

    def test_cost_class_accessors(self):
        rail_nut = _read("pathfinder_v90/rail.nut")
        self.assertIn('case "max_bridge_length": this._main._max_bridge_length = val; break;', rail_nut)
        self.assertIn('case "max_tunnel_length": this._main._max_tunnel_length = val; break;', rail_nut)
        self.assertIn('case "tunnel_per_tile":   this._main._cost_tunnel_per_tile = val; break;', rail_nut)
        self.assertIn('case "max_bridge_length": return this._main._max_bridge_length;', rail_nut)
        self.assertIn('case "max_tunnel_length": return this._main._max_tunnel_length;', rail_nut)
        self.assertIn('case "tunnel_per_tile":   return this._main._cost_tunnel_per_tile;', rail_nut)


class BuilderIntegration(unittest.TestCase):
    def test_create_rail_pathfinder_configures_cost(self):
        body = _function_body(_read("builder_rail.nut"), "OpexCreateRailPathfinder")
        self.assertIn("if (V173_RAIL_MAX_BRIDGE > 0) pathfinder.cost.max_bridge_length = V173_RAIL_MAX_BRIDGE;", body)
        self.assertIn("if (V173_RAIL_MAX_TUNNEL > 0) pathfinder.cost.max_tunnel_length = V173_RAIL_MAX_TUNNEL;", body)
        self.assertIn("if (V173_RAIL_TUNNEL_COST >= 0) pathfinder.cost.tunnel_per_tile = V173_RAIL_TUNNEL_COST;", body)

    def test_advance_segmented_search_configures_cost(self):
        body = _function_body(_read("builder_rail.nut"), "OpexAdvanceSegmentedSearch")
        self.assertIn("if (V173_RAIL_MAX_BRIDGE > 0) pathfinder.cost.max_bridge_length = V173_RAIL_MAX_BRIDGE;", body)
        self.assertIn("if (V173_RAIL_MAX_TUNNEL > 0) pathfinder.cost.max_tunnel_length = V173_RAIL_MAX_TUNNEL;", body)
        self.assertIn("if (V173_RAIL_TUNNEL_COST >= 0) pathfinder.cost.tunnel_per_tile = V173_RAIL_TUNNEL_COST;", body)


class PathfinderV129Integration(unittest.TestCase):
    def test_v129_inherits_v90(self):
        v129_nut = _read("pathfinder_v90/v129.nut")
        self.assertIn("class OpexRailPathFinderV129 extends OpexRailPathFinderV90", v129_nut)

    def test_v129_bridge_table_uses_max_bridge_length(self):
        v129_nut = _read("pathfinder_v90/v129.nut")
        self.assertIn("for (local i = 2; i < this._max_bridge_length; i++) {", v129_nut)

    def test_v129_neighbours_use_max_lengths(self):
        v129_nut = _read("pathfinder_v90/v129.nut")
        self.assertIn("for (local i = 2; i < this._max_bridge_length; i++) {", v129_nut)
        self.assertIn("tunnel_length < this._max_tunnel_length", v129_nut)

    def test_v129_cost_uses_tunnel_cost(self):
        v129_nut = _read("pathfinder_v90/v129.nut")
        self.assertIn("cost += distManhattan * (self._cost_tile + self._cost_tunnel_per_tile);", v129_nut)


class RealConstructionDynamic(unittest.TestCase):
    def test_build_track_bridges_dynamic(self):
        body = _function_body(_read("builder_rail.nut"), "OpexBuildTrack")
        self.assertIn("local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);", body)
        self.assertIn("AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next)", body)
        self.assertIn("AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)", body)

    def test_test_track_bridges_dynamic(self):
        body = _function_body(_read("builder_rail.nut"), "OpexTestRailTrack")
        self.assertIn("local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);", body)
        self.assertIn("AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next)", body)
        self.assertIn("AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)", body)

    def test_simulate_rail_infra_cost_dynamic(self):
        body = _function_body(_read("builder_rail.nut"), "OpexSimulateRailInfraCost")
        self.assertIn("local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);", body)
        self.assertIn("AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next)", body)
        self.assertIn("AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)", body)

    def test_no_other_hardcoded_6_for_rail_bridges_or_tunnels(self):
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                    continue
                if 'description = "' in stripped:
                    continue
                if "V173_RAIL_MAX_BRIDGE" in stripped or "V173_RAIL_MAX_TUNNEL" in stripped:
                    continue
                if "bridge" in stripped.lower() or "tunnel" in stripped.lower():
                    code_part = stripped.split("//")[0]
                    if " 6" in code_part or "=6" in code_part or "== 6" in code_part or "(6" in code_part:
                        self.fail(f"Longueur 6 hardcodee trouvee dans {path.name}:{line_no}: {stripped}")


if __name__ == "__main__":
    unittest.main()
