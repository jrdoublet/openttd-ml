#!/usr/bin/env python3
"""Contrat statique AIR 03/10 3a : borne V96 du raccourci, derriere un reglage.

air0310_v96_shortcut_lean vaut 0 aux quatre difficultes. A 0,
OpexC121GameEngineTryShortcut garde le calcul historique d'upperScore.
A 1, OpexC121EngineShortcutViable ne garde que les gardes null (capacites,
tarifs, couts, duree, MAIL, frontiere de mois) et geMode=1 ne lit que
l'avion et le contexte. Aucune partie OpenTTD n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


BOUND_ARITHMETIC = (
    "departuresPerDirectionMonth",
    "paxDirectionCapacity",
    "paxUpperA",
    "paxUpperB",
    "mailUpperA",
    "mailUpperB",
    "rawRevenueUpper",
    "revenueUpper",
    "profitUpper",
    "OpexC121EngineDecisionRealizationFactor",
)

NULL_GUARDS = (
    '!("c121Demand" in plan)',
    "plan.c121EngineStatic == null",
    "plane.price <= 0",
    "plane.runningCost < 0",
    "OpexC121EngineContextMatches(engineContext, catalog, plan, plane)",
    "OpexC119AirIncomeDays(plane, plan.distance)",
    "AICargo.GetCargoIncome(catalog.paxCargo, st.paymentDistance, incomeDays)",
    "paxIncome < 0",
    "C121_AIR_ENGINE_CAPACITY_OBS",
    "paxCapacity <= 0",
    "useMail && mailIncome < 0",
    "OpexC121AirTripModel(plan, plane)",
    "trip == null || trip.roundTripDays <= 0.0",
)


class TestAir0310_3aV96Shortcut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.econ = _read("ai/OpexAI/air_economics_c121.nut")
        cls.info = _read("ai/OpexAI/info.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.shortcut = _function_body(
            cls.econ, "function OpexC121GameEngineTryShortcut(catalog, plan, engineId)"
        )
        cls.viable = _function_body(
            cls.econ, "function OpexC121EngineShortcutViable(catalog, plan, plane, engineContext = null)"
        )
        cls.upper = _function_body(
            cls.econ, "function OpexC121InitialEngineUpperScore(catalog, plan, plane, engineContext = null)"
        )
        cls.chooser = _function_body(
            cls.econ, "function OpexC121ChooseRoutePlane(catalog, plan, lines = null)"
        )
        cls.scan = _function_body(
            cls.econ, "function OpexC121ScanRoutePlaneEngines(catalog, plan)"
        )

    def test_setting_defaults_on(self):  # adopte le 04/10 (porte B C121 + gain d'opcodes)
        start = self.info.index('name = "air0310_v96_shortcut_lean"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn(
            "1 = on (default), 0 = previous bound",
            block,
        )
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 1", block)
        self.assertNotIn("easy_value = 0", block)
        self.assertEqual(self.info.count('name = "air0310_v96_shortcut_lean"'), 1)
        self.assertIn("AIR0310_V96_SHORTCUT_LEAN <- false;", self.globals)
        self.assertEqual(self.globals.count("AIR0310_V96_SHORTCUT_LEAN"), 1)
        needle = 'AIController.GetSetting("air0310_v96_shortcut_lean")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'AIR0310_V96_SHORTCUT_LEAN = AIController.GetSetting("air0310_v96_shortcut_lean") != 0;',
            self.settings,
        )
        self.assertNotIn("AIR0310_V96_SHORTCUT_LEAN <-", self.settings)
        self.assertIn("C121_AIR_GAME_ENGINE <- false;", self.globals)
        self.assertIn(
            'C121_AIR_GAME_ENGINE = C121_AIR_ECONOMICS\n      && AIController.GetSetting("c121_air_game_engine") != 0;',
            self.settings,
        )

    def test_both_paths_present_and_default_is_the_old_bound(self):
        body = self.shortcut
        self.assertIn("OpexC121GameEngineFindPlane(catalog, airportType, engineId)", body)
        self.assertIn("AIEngine.IsValidEngine(plane.id)", body)
        self.assertIn("AIEngine.IsBuildable(plane.id)", body)
        self.assertIn("OpexC118EngineFitsPlan(plan, plane)", body)
        self.assertIn("OpexAirPlaneInRange(plane, plan.distance)", body)
        self.assertIn("local context = null;", body)
        gate = body.index("if (AIR0310_V96_SHORTCUT_LEAN) {")
        close = body.index("\n  }\n  local upperScore = context == null", gate)
        lean = body[gate:close]
        legacy = body[close:]
        self.assertIn(
            "if (!OpexC121EngineShortcutViable(catalog, plan, plane, context)) return null;",
            lean,
        )
        self.assertIn("return { plane = plane, context = context };", lean)
        self.assertNotIn("OpexC121InitialEngineUpperScore", lean)
        self.assertNotIn("upperScore", lean)
        for token in BOUND_ARITHMETIC:
            self.assertNotIn(token, lean)
        self.assertIn(
            "local upperScore = context == null\n"
            "      ? OpexC121InitialEngineUpperScore(catalog, plan, plane)\n"
            "      : OpexC121InitialEngineUpperScore(catalog, plan, plane, context);\n"
            "  if (upperScore == null) return null;\n"
            "  if (context != null) context.upperScore = upperScore;\n"
            "  return { plane = plane, context = context, upperScore = upperScore };",
            legacy,
        )
        self.assertNotIn("OpexC121EngineShortcutViable", legacy)

    def test_viable_keeps_null_guards_without_score(self):
        body = self.viable
        for token in NULL_GUARDS:
            self.assertIn(token, body)
        for token in BOUND_ARITHMETIC:
            self.assertNotIn(token, body)
        self.assertIn("return false;", body)
        self.assertIn("return true;", body)
        self.assertNotIn("return null;", body)
        self.assertNotIn("upperScore", body)
        # Frontiere de mois / MAIL : mismatch jette le contexte, puis les
        # tarifs, la duree et la soute sont recalcules comme l'ancienne borne.
        mismatch = body.index(
            "if (engineContext != null && !OpexC121EngineContextMatches"
        )
        self.assertGreater(body.index("engineContext = null;", mismatch), mismatch)
        self.assertGreater(
            body.index("AICargo.GetCargoIncome(catalog.paxCargo", mismatch), mismatch
        )
        self.assertGreater(body.index("C121_AIR_ENGINE_CAPACITY_OBS", mismatch), mismatch)
        self.assertGreater(body.index("OpexC121AirTripModel(plan, plane)", mismatch), mismatch)

    def test_upper_score_still_prunes_scans(self):
        for token in BOUND_ARITHMETIC:
            self.assertIn(token, self.upper)
        for path in (self.chooser, self.scan):
            self.assertIn("OpexC121InitialEngineUpperScore(catalog, plan, plane)", path)
            self.assertIn("if (upperScore == null) continue;", path)
            self.assertIn("candidate.upperScore < best.economics.decisionScore", path)

    def test_ge_mode_one_keeps_plane_and_context_only(self):
        chooser = self.chooser
        call = chooser.index("local shortcut = OpexC121GameEngineTryShortcut(catalog, plan, geState.engine);")
        success = chooser.index("if (shortcut != null)", call)
        fallback = chooser.index("geMode = 3;", success)
        block = chooser[success:fallback]
        self.assertIn("geMode = 1;", block)
        self.assertIn(
            "best = { plane = shortcut.plane, economics = null, context = shortcut.context };",
            block,
        )
        self.assertNotIn("shortcut.upperScore", chooser)
        self.assertNotIn("context.upperScore", block)
        self.assertIn('OpexC121GameEngineLog("fallback"', chooser[fallback:fallback + 400])
        late = chooser.index("if (initialEconomics == null)")
        retry = chooser[late:]
        self.assertIn("C121_AIR_GAME_ENGINE && geMode == 1", retry)
        self.assertIn("best = OpexC121ScanRoutePlaneEngines(catalog, plan);", retry)


if __name__ == "__main__":
    unittest.main()
