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

    def test_loop_conversion_before_cloning(self):
        self.assertIn('if (!("v181Loop" in line) || !line.v181Loop) {', self.body)
        self.assertIn('local loopOk = OpexConvertDoubleTrackToLoop(line);', self.body)
        self.assertIn('line.v181LoopFailed <- true;', self.body)
        self.assertIn('line.v181Loop <- true;', self.body)

    def test_station_id_concordance_checked(self):
        self.assertIn('srcStationId != srcStationId2 || dstStationId != dstStationId2', self.body)

    def test_waiting_exceeds_train_capacity(self):
        self.assertIn("local trainCapacity = line.wagons * wagon.capacity;", self.body)
        self.assertIn("if (waiting <= trainCapacity) continue;", self.body)

    def test_no_train_waiting_at_source_station(self):
        self.assertIn('local srcStationId = ("stationA" in line) ? AIStation.GetStationID(line.stationA) : AIStation.STATION_INVALID;', self.body)
        self.assertIn("if (AIMap.IsValidTile(vLoc) && AIStation.GetStationID(vLoc) == srcStationId) {", self.body)
        self.assertIn("trainWaitingAtSource = true;", self.body)
        self.assertIn("if (trainWaitingAtSource) continue;", self.body)

    def test_clones_with_shared_orders(self):
        self.assertIn("local extraTrain = AIVehicle.CloneVehicle(targetDepot, modelTrain, true);", self.body)
        self.assertIn("if (!AIVehicle.StartStopVehicle(extraTrain)) {", self.body)
        self.assertIn("AIVehicle.SellVehicle(extraTrain);", self.body)

    def test_decision_log(self):
        self.assertIn('OpexDecide("RAIL_EXPAND", "action=clone line=" + line.lineId + " trains=" + line.trains);', self.body)


class LoopConversionContract(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.loop_body = _function_body(self.builder, "OpexConvertDoubleTrackToLoop")

    def test_trace_track_tiles_defined(self):
        self.assertIn("function OpexTraceTrackTiles(", self.builder)

    def test_test_mode_before_execution(self):
        self.assertIn("local testMode = AITestMode();", self.loop_body)

    def test_rollback_on_failure(self):
        self.assertIn("AIRail.RemoveRail(rec.prev, rec.cur, rec.next);", self.loop_body)

    def test_one_way_signals_placed(self):
        self.assertIn("OpexV181BuildOneWaySignal(tiles1[endIdx1], tiles1[endIdx1 - 1]);", self.loop_body)
        self.assertIn("OpexV181BuildOneWaySignal(tiles1[k], tiles1[k - 1]);", self.loop_body)
        self.assertIn("OpexV181BuildOneWaySignal(tiles2[startIdx2], tiles2[startIdx2 + 1]);", self.loop_body)
        self.assertIn("OpexV181BuildOneWaySignal(tiles2[k], tiles2[k + 1]);", self.loop_body)

    def test_shared_orders_unified(self):
        self.assertIn("local sharedOk = AIOrder.ShareOrders(otherTrain, firstTrain);", self.loop_body)
        self.assertIn("AIOrder.RemoveOrder(otherTrain, 0);", self.loop_body)


class SquirrelKeywordSafety(unittest.TestCase):
    def test_no_reserved_keywords_as_variables(self):
        task_body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")
        builder_code = _read("builder_rail.nut")
        loop_body = _function_body(builder_code, "OpexConvertDoubleTrackToLoop")
        switch_body = _function_body(builder_code, "OpexV181TryBuildSwitch")
        trace_body = _function_body(builder_code, "OpexTraceTrackTiles")

        for kw in ("clone", "parent", "base"):
            for code, name in [(task_body, "task_rail::_expandRailLines"),
                               (loop_body, "OpexConvertDoubleTrackToLoop"),
                               (switch_body, "OpexV181TryBuildSwitch"),
                               (trace_body, "OpexTraceTrackTiles")]:
                pattern = rf"\b(local|function)\s+{kw}\b"
                self.assertIsNone(re.search(pattern, code), f"Reserved Squirrel keyword '{kw}' used as identifier in {name}")
                param_pattern = rf"\(\s*{kw}\s*[,)]"
                self.assertIsNone(re.search(param_pattern, code), f"Reserved Squirrel keyword '{kw}' used as parameter in {name}")


if __name__ == "__main__":
    unittest.main()

