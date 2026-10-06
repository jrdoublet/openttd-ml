#!/usr/bin/env python3
"""Contrat statique AIR 03/10 piste 6 : sonde shadow moteur x N.

probe_air_engine_depth vaut 0 aux quatre difficultes. A 0, le scan
complet C121 et le repli du raccourci V96 gardent leur corps historique
derriere un seul test du drapeau. A 1, le scan shadow retient le second
moteur N=1 et le note avec OpexC121OneOrTwoWinner ; le choix n'est pas
ecrit. Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HISTORICAL_PICK = """) best = item;"""
TERNARY = "C121_AAA_LINE ? 2 : 1"
LOG_FIELDS = (
    "date=",
    "towns=",
    "eng=",
    "n=",
    "score=",
    "alt=",
    "alt_n=",
    "alt_score=",
    "loss=",
    "ops=",
)


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


class TestAir0310_6EngineDepth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.econ = _read("ai/OpexAI/air_economics_c121.nut")
        cls.info = _read("ai/OpexAI/info.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.chooser = _function_body(
            cls.econ, "function OpexC121ChooseRoutePlane(catalog, plan, lines = null)"
        )
        cls.scan = _function_body(
            cls.econ, "function OpexC121ScanRoutePlaneEngines(catalog, plan)"
        )
        cls.shortcut = _function_body(
            cls.econ, "function OpexC121GameEngineTryShortcut(catalog, plan, engineId)"
        )
        cls.full = _function_body(
            cls.econ, "function OpexAirEngineDepthFullScan(catalog, plan)"
        )
        cls.emit = _function_body(
            cls.econ, "function OpexAirEngineDepthEmit(catalog, plan, routeChoice)"
        )
        cls.winner = _function_body(
            cls.econ, "function OpexC121OneOrTwoWinner(catalog, plan, plane, engineContext)"
        )

    def test_setting_defaults_off(self):
        start = self.info.index('name = "probe_air_engine_depth"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("0 = off (default)", block)
        self.assertIn("AIR_ENGINE_DEPTH", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertNotIn("easy_value = 1", block)
        self.assertEqual(self.info.count('name = "probe_air_engine_depth"'), 1)
        self.assertIn("PROBE_AIR_ENGINE_DEPTH <- false;", self.globals)
        self.assertIn("AIR_ENGINE_DEPTH_SCAN <- 0;", self.globals)
        self.assertIn("AIR_ENGINE_DEPTH_CHALLENGER <- null;", self.globals)
        self.assertEqual(self.globals.count("PROBE_AIR_ENGINE_DEPTH"), 1)
        self.assertEqual(self.globals.count("AIR_ENGINE_DEPTH_SCAN"), 1)
        self.assertEqual(self.globals.count("AIR_ENGINE_DEPTH_CHALLENGER"), 1)
        needle = 'AIController.GetSetting("probe_air_engine_depth")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'PROBE_AIR_ENGINE_DEPTH = AIController.GetSetting("probe_air_engine_depth") != 0;',
            self.settings,
        )
        self.assertNotIn("PROBE_AIR_ENGINE_DEPTH <-", self.settings)
        for token in (
            "probe_air_engine_depth",
            "PROBE_AIR_ENGINE_DEPTH",
            "AIR_ENGINE_DEPTH_SCAN",
            "AIR_ENGINE_DEPTH_CHALLENGER",
        ):
            self.assertNotIn(token, self.persist)

    def test_off_path_is_one_flag_then_the_historical_scan(self):
        chooser = self.chooser
        self.assertEqual(chooser.count("PROBE_AIR_ENGINE_DEPTH"), 1)
        self.assertIn("local depthOn = PROBE_AIR_ENGINE_DEPTH;", chooser)
        self.assertLess(
            chooser.index("best = { plane = shortcut.plane, economics = null, context = shortcut.context };"),
            chooser.index("local depthOn = PROBE_AIR_ENGINE_DEPTH;"),
        )
        call = chooser.index("local shortcut = OpexC121GameEngineTryShortcut(catalog, plan, geState.engine);")
        success = chooser.index("if (shortcut != null)", call)
        fallback = chooser.index("geMode = 3;", success)
        hot = chooser[success:fallback]
        self.assertIn("geMode = 1;", hot)
        self.assertNotIn("depthOn", hot)
        self.assertNotIn("AIR_ENGINE_DEPTH", hot)
        self.assertNotIn("PROBE_AIR_ENGINE_DEPTH", self.shortcut)
        self.assertNotIn("AIR_ENGINE_DEPTH", self.shortcut)

        armed = chooser.index("best = OpexAirEngineDepthFullScan(catalog, plan);")
        historical = chooser[chooser.index("} else {", armed):chooser.index("OpexC121GameEngineAfterScan", armed)]
        self.assertIn("local openingPlanes = " + TERNARY + ";", historical)
        self.assertIn(HISTORICAL_PICK, historical)
        self.assertNotIn("AIR_ENGINE_DEPTH", historical)
        self.assertNotIn("OpexAirEngineDepth", historical)
        self.assertLess(armed, chooser.index(HISTORICAL_PICK, armed))

        self.assertNotIn("PROBE_AIR_ENGINE_DEPTH", self.scan)
        self.assertNotIn("AIR_ENGINE_DEPTH_CHALLENGER", self.scan)
        self.assertIn(
            "if (AIR_ENGINE_DEPTH_SCAN != 0) return OpexAirEngineDepthFullScan(catalog, plan);",
            self.scan,
        )
        self.assertEqual(self.scan.count("OpexAirEngineDepthFullScan"), 1)
        self.assertIn("local openingPlanes = " + TERNARY + ";", self.scan)
        self.assertIn(HISTORICAL_PICK, self.scan)
        self.assertEqual(self.econ.count(HISTORICAL_PICK), 2)
        self.assertEqual(self.econ.count(TERNARY), 3)
        self.assertNotIn("C121_AIR_ONE_OR_TWO_PLANES", chooser)

        needle = "if (best != null && candidate.upperScore < best.economics.decisionScore) break;"
        self.assertTrue(chooser.split(needle, 1)[1].lstrip().startswith("if (PROBE_C121_ENGINE_TABLE)"))

    def test_shadow_scores_the_runner_up_without_writing_the_choice(self):
        full = self.full
        emit = self.emit
        chooser = self.chooser
        self.assertNotIn("PROBE_AIR_ENGINE_DEPTH", full)
        self.assertNotIn(TERNARY, full)
        self.assertIn("local openingPlanes = 1;", full)
        self.assertIn("if (C121_AAA_LINE) openingPlanes = 2;", full)
        self.assertIn("AIR_ENGINE_DEPTH_CHALLENGER = null;", full)
        self.assertIn("AIR_ENGINE_DEPTH_CHALLENGER = best;", full)
        self.assertIn("else OpexAirEngineDepthConsider(item);", full)
        self.assertNotIn("c121ChosenEngine", full)
        self.assertNotIn("c121WinnerFullOps", full)
        self.assertLess(
            self.econ.index("function OpexAirEngineDepthFullScan("),
            self.econ.index("function OpexC121ChooseRoutePlane("),
        )

        guard = emit.index("if (!PROBE_AIR_ENGINE_DEPTH) return;")
        kernel = emit.index("OpexC121OneOrTwoWinner(catalog, plan, challenger.plane, ctx);")
        measured = emit.index("ops = OpexAirCalcDeltaOps(tick0, ops0);")
        log = emit.index('AILog.Info("AIR_ENGINE_DEPTH date=')
        self.assertLess(emit.index("local challenger = AIR_ENGINE_DEPTH_CHALLENGER;"), emit.index("OpexAirEngineDepthClear();"))
        self.assertLess(emit.index("OpexAirEngineDepthClear();"), kernel)
        self.assertLess(guard, kernel)
        self.assertLess(guard, log)
        self.assertLess(emit.index("local savedN1 = C121_ENGTAB_N1;"), kernel)
        self.assertLess(emit.index("AIController.GetOpsTillSuspend();"), kernel)
        self.assertLess(kernel, measured)
        self.assertLess(measured, emit.index("C121_ENGTAB_N1 = savedN1;"))
        self.assertLess(emit.index("C121_ENGTAB_N2 = savedN2;"), log)
        self.assertIn("(incScore - altScore) / (incScore + 0.0)", emit)
        self.assertNotIn("OpexC121OneOrTwoFused(", emit)
        self.assertNotIn("c121ChosenEngine", emit)
        self.assertNotIn("c121WinnerFullOps", emit)
        self.assertIsNone(re.search(r"routeChoice\s*=(?!=)", emit))
        self.assertEqual(emit.count("OpexC121OneOrTwoWinner("), 1)
        self.assertEqual(self.econ.count('AILog.Info("AIR_ENGINE_DEPTH'), 1)
        line = emit[log:emit.index(");", log)]
        for field in LOG_FIELDS:
            self.assertIn(field, line)
        for word in ("clone", "base", "parent"):
            self.assertIsNone(re.search(r"\b" + word + r"\b", emit))
            self.assertIsNone(re.search(r"\b" + word + r"\b", full))

        built = chooser.index("local routeChoice = {")
        emit_if = chooser.index(
            "if (depthOn && AIR_ENGINE_DEPTH_SCAN) OpexAirEngineDepthEmit(catalog, plan, routeChoice);"
        )
        self.assertLess(chooser.index("plan.c121ChosenEngine <- best.plane.id;"), built)
        self.assertLess(built, emit_if)
        self.assertLess(emit_if, chooser.index("return routeChoice;", emit_if))
        self.assertEqual(chooser.count("OpexAirEngineDepthEmit"), 1)
        self.assertIn(
            "if (depthOn) AIR_ENGINE_DEPTH_SCAN = 1;\n      best = OpexC121ScanRoutePlaneEngines(catalog, plan);",
            chooser,
        )
        self.assertNotIn("PROBE_AIR_ENGINE_DEPTH", self.winner)
        self.assertNotIn("AIR_ENGINE_DEPTH", self.winner)


if __name__ == "__main__":
    unittest.main()
