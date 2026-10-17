#!/usr/bin/env python3
"""Contrats de retrait V181 — v181_rail_max_trains (defaut 0, inerte).

Le clonage au-dela de 2 trains n'etait jamais atteint au defaut. Le chemin
historique (plafond 2, sauf fret V190) est fige. OpexConvertDoubleTrackToLoop
et le champ v181Loop restent : V190/V198 les consomment.
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


class SettingRemoved(unittest.TestCase):
    def test_not_declared(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertNotIn("v181_rail_max_trains", specs)
        self.assertNotIn('name = "v181_rail_max_trains"', _read("info.nut"))

    def test_not_loaded(self):
        self.assertNotIn("V181_RAIL_MAX_TRAINS", _read("globals_pre.nut"))
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertNotIn("v181_rail_max_trains", body)
        self.assertNotIn("V181_RAIL_MAX_TRAINS", body)


class DefaultPathFrozen(unittest.TestCase):
    def setUp(self):
        self.body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")

    def test_two_train_cap_without_v181_gate(self):
        self.assertNotIn("V181_RAIL_MAX_TRAINS", self.body)
        self.assertIn('if (!OpexV190Active() || line.kind != "freight") {', self.body)
        self.assertIn("if (line.trains >= 2 || line.vehicles.len() >= 2) continue;", self.body)
        self.assertIn(
            "if (line.trains >= V190_RAIL_MAX_TRAINS || line.vehicles.len() >= V190_RAIL_MAX_TRAINS) continue;",
            self.body,
        )

    def test_clone_branch_removed(self):
        self.assertNotIn("Cas 3 : V181", self.body)
        self.assertNotIn("waiting <= trainCapacity", self.body)

    def test_v190_clone_branch_kept(self):
        self.assertIn('OpexV190Active() && line.kind == "freight" && line.trains >= 2 &&', self.body)
        self.assertIn("OpexConvertDoubleTrackToLoop(line)", self.body)
        self.assertIn("action=add_train", self.body)


class SharedLoopInfrastructureKept(unittest.TestCase):
    def test_loop_helpers_remain_for_v190(self):
        builder = _read("builder_rail.nut")
        self.assertIn("function OpexConvertDoubleTrackToLoop(", builder)
        self.assertIn("function OpexV181TryBuildSwitch(", builder)
        self.assertIn("function OpexV181BuildOneWaySignal(", builder)


if __name__ == "__main__":
    unittest.main()
