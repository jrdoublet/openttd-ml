#!/usr/bin/env python3
"""Tests pour V181 — nombre maximal de trains par ligne rail (clonage sur double voie).

Contrats statiques :
1. `v181_rail_max_trains` declare (entier 0..8, defaut 0) et lu une seule fois dans OpexLoadSettings.
2. A 0 (defaut), chemin inerte : la limite historique de 2 trains s'applique directement
   sans verification de clonage ni surcout d'opcodes.
3. Hors defaut (> 0), clonage de trains supplementaires jusqu'a N trains sur ligne deja doublee,
   conditionne par l'attente depassant la capacite d'une rame et l'absence de train a la gare source.
4. Journalisation `RAIL_EXPAND action=clone line=.. trains=..` sous DECISION_LOG.
5. Aucun mot reserve Squirrel (clone, parent, base) utilise comme variable.
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
    def test_setting(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v181_rail_max_trains"]
        self.assertEqual(spec["default"], 0)
        self.assertFalse(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 8))
        block = _read("info.nut").split('name = "v181_rail_max_trains"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")

    def test_loaded_once(self):
        self.assertIn("V181_RAIL_MAX_TRAINS <- 0;", _read("globals_pre.nut"))
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v181_rail_max_trains")'), 1)
        self.assertIn("local maxTrains = AIController.GetSetting(\"v181_rail_max_trains\");", body)
        self.assertIn("V181_RAIL_MAX_TRAINS = (maxTrains != null && maxTrains > 0 && maxTrains <= 8) ? maxTrains : 0;", body)


class InertDefault(unittest.TestCase):
    def test_default_gate_short_circuits_at_two_trains(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn("if (V181_RAIL_MAX_TRAINS <= 0) {", body)
        self.assertIn("if (line.trains >= 2 || line.vehicles.len() >= 2) continue;", body)

    def test_clone_branch_only_for_positive_setting(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn("else if (V181_RAIL_MAX_TRAINS > 0 && line.trains >= 2 &&", body)


class ActiveCloningContract(unittest.TestCase):
    def setUp(self):
        self.body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")

    def test_requires_double_track(self):
        self.assertIn('("doubleTrack" in line) && line.doubleTrack == 1', self.body)

    def test_waiting_exceeds_train_capacity(self):
        self.assertIn("local trainCapacity = line.wagons * wagon.capacity;", self.body)
        self.assertIn("if (waiting <= trainCapacity) continue;", self.body)

    def test_no_train_waiting_at_source_station(self):
        self.assertIn('local srcStationId = ("stationA" in line) ? AIStation.GetStationID(line.stationA) : AIStation.STATION_INVALID;', self.body)
        self.assertIn("if (AIStation.GetStationID(AIVehicle.GetLocation(v)) == srcStationId) {", self.body)
        self.assertIn("trainWaitingAtSource = true;", self.body)
        self.assertIn("if (trainWaitingAtSource) continue;", self.body)

    def test_clones_with_shared_orders(self):
        self.assertIn("local extraTrain = AIVehicle.CloneVehicle(targetDepot, modelTrain, true);", self.body)
        self.assertIn("if (!AIVehicle.StartStopVehicle(extraTrain)) {", self.body)
        self.assertIn("AIVehicle.SellVehicle(extraTrain);", self.body)

    def test_decision_log(self):
        self.assertIn('OpexDecide("RAIL_EXPAND", "action=clone line=" + line.lineId + " trains=" + line.trains);', self.body)


class SquirrelKeywordSafety(unittest.TestCase):
    def test_no_reserved_keywords_as_variables(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")
        # Aucun mot reserve Squirrel utilise comme variable (local clone, local parent, local base, etc.)
        for kw in ("clone", "parent", "base"):
            pattern = rf"\b(local|function)\s+{kw}\b"
            self.assertIsNone(re.search(pattern, body), f"Reserved Squirrel keyword '{kw}' used as identifier")
            param_pattern = rf"\(\s*{kw}\s*[,)]"
            self.assertIsNone(re.search(param_pattern, body), f"Reserved Squirrel keyword '{kw}' used as parameter")


if __name__ == "__main__":
    unittest.main()
