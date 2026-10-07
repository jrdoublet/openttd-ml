#!/usr/bin/env python3
"""Contrat statique AIR 03/10 3b : N=1 et N=2 partagent les invariants.

air0310_one_two_fused vaut 0 aux quatre difficultes. A 0,
OpexC121OneOrTwoWinner garde les deux appels OpexC121EngineEconomics.
A 1, OpexC121OneOrTwoFused prepare une fois tarifs, duree, amortissement,
capacites et couts d'aeroport, puis calcule les deux profondeurs. Le
contexte generique rejete n'est pas consulte. Aucune partie n'est lancee.
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


# Bloc historique, sous le reglage 0. Le departage reste N=1 si les scores
# puis les profits de decision sont egaux.
LEGACY_BODY = """\
  local econ1 = engineContext == null
      ? OpexC121EngineEconomics(catalog, plan, plane, 1, false)
      : OpexC121EngineEconomics(catalog, plan, plane, 1, false, null, null, engineContext);
  local econ2 = engineContext == null
      ? OpexC121EngineEconomics(catalog, plan, plane, 2, false)
      : OpexC121EngineEconomics(catalog, plan, plane, 2, false, null, null, engineContext);
  local chosen = econ1;
  if (econ2 != null) {
    if (chosen == null) {
      chosen = econ2;
    } else {
      local score1 = ("decisionScore" in econ1) ? econ1.decisionScore : econ1.score;
      local score2 = ("decisionScore" in econ2) ? econ2.decisionScore : econ2.score;
      local profit1 = ("decisionProfitAnnual" in econ1) ? econ1.decisionProfitAnnual : econ1.profitAnnual;
      local profit2 = ("decisionProfitAnnual" in econ2) ? econ2.decisionProfitAnnual : econ2.profitAnnual;
      if (score2 > score1 || (score2 == score1 && profit2 > profit1)) chosen = econ2;
    }
  }
  if (PROBE_C121_ENGINE_TABLE) {
    C121_ENGTAB_N1 = econ1;
    C121_ENGTAB_N2 = econ2;
  }
  return { initial = chosen, full = chosen };
"""

TIE_BREAK = "if (score2 > score1 || (score2 == score1 && profit2 > profit1)) chosen = econ2;"

NULL_GUARDS = (
    "if (plane == null) return null;",
    '!("c121Demand" in plan)',
    "paxCapacity <= 0",
    "mailCapacity < 0",
    "catalog.paxCargo < 0",
    "trip == null || trip.roundTripDays <= 0",
    "paxIncome < 0",
    "useMail && mailIncome < 0",
)

REJECTED_CONTEXT = (
    "OpexC121EngineContextMatches",
)


class TestAir0310_3bOneTwoFused(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.econ = _read("ai/OpexAI/air_economics_c121.nut")
        cls.info = _read("ai/OpexAI/info.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.winner = _function_body(
            cls.econ, "function OpexC121OneOrTwoWinner(catalog, plan, plane, engineContext)"
        )
        cls.fused = _function_body(
            cls.econ, "function OpexC121OneOrTwoFused(catalog, plan, plane)"
        )
        cls.invariants = _function_body(
            cls.econ, "function OpexC121OneOrTwoInvariants(catalog, plan, plane)"
        )
        cls.depth = _function_body(
            cls.econ, "function OpexC121OneOrTwoDepth(inv, planes)"
        )

    def test_setting_defaults_on(self):  # adopte le 04/10 (porte B C121 + gain d'opcodes)
        start = self.info.index('name = "air0310_one_two_fused"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("1 = on (default), 0 = two full economics calls", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("step_size = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 1", block)
        self.assertNotIn("easy_value = 0", block)
        self.assertEqual(self.info.count('name = "air0310_one_two_fused"'), 1)
        self.assertIn("AIR0310_ONE_TWO_FUSED <- false;", self.globals)
        self.assertEqual(self.globals.count("AIR0310_ONE_TWO_FUSED"), 1)
        needle = 'AIController.GetSetting("air0310_one_two_fused")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'AIR0310_ONE_TWO_FUSED = AIController.GetSetting("air0310_one_two_fused") != 0;',
            self.settings,
        )
        self.assertNotIn("AIR0310_ONE_TWO_FUSED <-", self.settings)
        self.assertNotIn("air0310_one_two_fused", self.persist)
        self.assertNotIn("AIR0310_ONE_TWO_FUSED", self.persist)
        # Le reglage 3a reste a cote, inchange dans son chargement.
        self.assertEqual(self.info.count('name = "air0310_v96_shortcut_lean"'), 1)
        self.assertIn(
            'AIR0310_V96_SHORTCUT_LEAN = AIController.GetSetting("air0310_v96_shortcut_lean") != 0;',
            self.settings,
        )

    def test_default_path_is_the_two_historical_calls(self):
        body = self.winner
        gate = body.index("if (AIR0310_ONE_TWO_FUSED) {")
        fused_call = body.index("return OpexC121OneOrTwoFused(catalog, plan, plane);", gate)
        legacy = body[body.index("  local econ1", fused_call):]
        self.assertLess(gate, fused_call)
        self.assertNotIn("engineContext", body[gate:fused_call])
        self.assertNotIn("OpexC121EngineEconomics", body[gate:fused_call])
        self.assertTrue(legacy.startswith(LEGACY_BODY))
        self.assertEqual(legacy[len(LEGACY_BODY):].strip(), "}")
        self.assertNotIn("fixedPlanes = 0", body)
        self.assertEqual(body.count("OpexC121EngineEconomics(catalog, plan, plane, 1, false)\n"), 1)
        self.assertEqual(
            body.count("OpexC121EngineEconomics(catalog, plan, plane, 1, false, null, null, engineContext)"),
            1,
        )
        self.assertEqual(body.count("OpexC121EngineEconomics(catalog, plan, plane, 2, false)\n"), 1)
        self.assertEqual(
            body.count("OpexC121EngineEconomics(catalog, plan, plane, 2, false, null, null, engineContext)"),
            1,
        )
        self.assertLess(
            self.econ.index("function OpexC121OneOrTwoFused("),
            self.econ.index("function OpexC121OneOrTwoWinner("),
        )

    def test_fused_shares_invariants_and_keeps_guards(self):
        fused = self.fused
        invariants = self.invariants
        depth = self.depth
        for token in REJECTED_CONTEXT:
            self.assertNotIn(token, fused)
            self.assertNotIn(token, invariants)
            self.assertNotIn(token, depth)
        joined = fused + invariants + depth
        # Le nom historique peut apparaitre dans un commentaire. Pas d'appel.
        self.assertNotIn("OpexC121AirEconomics(catalog", joined)
        self.assertNotIn("= OpexC121AirEconomics(", joined)
        for token in NULL_GUARDS:
            self.assertIn(token, invariants)
        # L'avion null est teste avant toute lecture de catalog ou de plan.
        self.assertLess(
            invariants.index("if (plane == null) return null;"),
            invariants.index('!("c121Demand" in plan)'),
        )
        self.assertLess(
            invariants.index('!("c121Demand" in plan)'),
            invariants.index("AICargo.GetCargoIncome"),
        )
        self.assertIn("local paxCapacity = plane.capacity;", invariants)
        self.assertIn("local mailCapacity = 0;", invariants)
        self.assertIn("if (plane.id in C121_AIR_ENGINE_CAPACITY_OBS)", invariants)
        self.assertIn("mailCapacity = caps.mail;", invariants)
        self.assertIn(
            "local useMail = mailCapacity > 0 && (\"mailCargo\" in catalog) && catalog.mailCargo >= 0;",
            invariants,
        )
        # MAIL inconnu : pas de GetCargoIncome courrier. MAIL observe a 0 non plus.
        self.assertIn(
            "local mailIncome = useMail ? AICargo.GetCargoIncome(catalog.mailCargo, paymentDistance, incomeDays) : 0;",
            invariants,
        )
        self.assertIn(
            "AICargo.GetCargoIncome(catalog.paxCargo, paymentDistance, incomeDays)",
            invariants,
        )
        self.assertIn("OpexC121AirTripModel(plan, plane)", invariants)
        self.assertIn("OpexC119AirIncomeDays(plane, plan.distance)", invariants)
        self.assertIn("plane.price / lifeYears", invariants)
        self.assertIn("OpexC121AirFleetScanCap(", invariants)
        self.assertIn("local observedMail = false;", invariants)
        self.assertIn("observedMail = true;", invariants)
        # Service present mais null : ne pas le remplacer par la table vide.
        self.assertIn('!("c121ServiceA" in plan)', invariants)
        self.assertIn('!("c121ServiceB" in plan)', invariants)
        self.assertIn("if (!(\"c121ServiceA\" in plan)) serviceA = emptyService;", invariants)
        self.assertNotIn("if (serviceA == null) serviceA = emptyService;", invariants)

    def test_both_depths_and_date_boundary(self):
        fused = self.fused
        date = fused.index("local dateBefore = AIDate.GetCurrentDate();")
        first = fused.index("OpexC121OneOrTwoDepth(inv, 1)", date)
        refresh = fused.index("if (AIDate.GetCurrentDate() != dateBefore)", first)
        second_prep = fused.index("inv = OpexC121OneOrTwoInvariants(catalog, plan, plane);", refresh)
        second = fused.index("OpexC121OneOrTwoDepth(inv, 2)", second_prep)
        self.assertLess(date, first)
        self.assertLess(first, refresh)
        self.assertLess(refresh, second_prep)
        self.assertLess(second_prep, second)
        self.assertEqual(fused.count("OpexC121OneOrTwoInvariants(catalog, plan, plane)"), 2)
        self.assertEqual(fused.count("OpexC121OneOrTwoDepth("), 2)
        self.assertIn(TIE_BREAK, fused)
        self.assertIn("C121_ENGTAB_N1 = econ1;", fused)
        self.assertIn("C121_ENGTAB_N2 = econ2;", fused)
        self.assertIn("return { initial = chosen, full = chosen };", fused)
        # N=1 reste choisi si le score puis le profit sont egaux : pas de >=.
        self.assertNotIn("score2 >= score1", fused)
        self.assertNotIn("profit2 >= profit1", fused)
        self.assertLess(
            fused.index("if (PROBE_C121_ENGINE_TABLE)"),
            fused.index("return { initial = chosen, full = chosen };"),
        )

    def test_depth_materializes_only_the_useful_snapshots(self):
        depth = self.depth
        self.assertIn("if (candidatePickupRate <= 0.0) return null;", depth)
        self.assertIn("local decisionOnly = false;", depth)
        self.assertIn("OpexC121RatingTarget(", depth)
        self.assertIn("OpexC121StationAllocatedMonthly(", depth)
        self.assertIn("OpexC121RealizationFactor(plan)", self.invariants)
        self.assertIn("local decisionCapital = totalCapital;", depth)
        self.assertIn("mailKnown = useMail", depth)
        self.assertIn("score = decisionScore", depth)
        self.assertIn("local best = clone scoreBest;", depth)
        self.assertIn("delete best.score;", depth)
        self.assertNotIn("best.score <-", depth)
        self.assertLess(depth.index("score = decisionScore"), depth.index("delete best.score;"))
        self.assertLess(depth.index("delete best.score;"), depth.index("best.decisionEconomics <- scoreBest;"))
        self.assertIn("scoreBest.fleetEvaluated <- fleetEvaluated;", depth)
        self.assertIn("scoreBest.fleetBoundPruned <- false;", depth)
        self.assertNotIn("best.fleetEvaluated", depth)
        self.assertNotIn("best.fleetBoundPruned", depth)
        self.assertIn("best.engineMailKnown <- inv.observedMail;", depth)
        self.assertIn("scoreBest.engineMailKnown <- inv.observedMail;", depth)
        self.assertIn("scoreBest.decisionCapital <- scoreBest.capital;", depth)
        self.assertIn("best.decisionCapital <- scoreBest.capital;", depth)
        # Table MAIL vide seulement hors courrier, et une seule, partagee.
        use_mail = depth.index("if (useMail) {")
        else_mail = depth.index("} else {", use_mail)
        mail_block = depth[use_mail:else_mail]
        dummy = depth[else_mail:depth.index("local paxRatingPointsA", else_mail)]
        self.assertNotIn("points = 0", mail_block)
        self.assertIn(
            "mailRatingA = { points = 0, offered = 0.0, waitingUpper = 0.0, ratingWaiting = 0.0, cycled = false };",
            dummy,
        )
        self.assertIn("mailRatingB = mailRatingA;", dummy)
        self.assertEqual(depth.count("points = 0"), 1)
        # Borne de scan et revenu plafond : reserves au chemin decisionOnly.
        self.assertNotIn("rawMaxRevenueUpper", depth)
        self.assertNotIn("decisionScoreFloor", depth)
        self.assertNotIn("fixedPlanes = 0", depth)


if __name__ == "__main__":
    unittest.main()
