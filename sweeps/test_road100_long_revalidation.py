"""Test unitaire ciblé : constat n°6 sur la revalidation des plans LONG.

Vérifie que :
1. OpexRoad100LongBuildCandidate conserve le plan complet dans candidate.road100StoredPlan ;
2. OpexRoad100LongVerifyStoredPlan revérifie d'abord le plan stocké (gares, arêtes,
   dépôt, devis/finances) et catégorise l'échec (physical, drift, resource) ;
3. OpexRoadPlanForActive teste le plan stocké avant de relancer scanners + sélection ;
4. _tryBuildRoadProject dans task_road.nut ne bannit durablement la paire
   (_markPairAbandoned) que pour une invalidité physique (pas pour dérive ni ressource) ;
5. Modèle / oracle de décision vérifiant les scénarios de revalidation.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def function_body(filename: str, name: str) -> str:
    source = (AI / filename).read_text(encoding="utf-8")
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    raise AssertionError("Unclosed function: " + name)


class TestRoad100LongRevalidation(unittest.TestCase):
    def test_candidate_stores_plan(self):
        body = function_body("candidates.nut", "OpexRoad100LongBuildCandidate")
        self.assertIn("candidate.road100StoredPlan <- plan;", body)
        self.assertIn("candidate.road100LongBuild <- true;", body)

    def test_verify_stored_plan_function_contracts(self):
        body = function_body("builder_road.nut", "OpexRoad100LongVerifyStoredPlan")
        # Doit vérifier gares, arêtes, dépôt et devis
        self.assertIn("BuildDriveThroughRoadStation", body)
        self.assertIn("OpexRoad100LongVerifyTrace", body)
        self.assertIn("OpexRoad100LongDepotPreflight", body)
        self.assertIn("costRoadPerTile", body)
        self.assertIn("OpexVehicleSlotAvailable", body)

        # Doit catégoriser les retours
        self.assertIn('category = "physical"', body)
        self.assertIn('category = "resource"', body)
        self.assertIn('category = "drift"', body)
        self.assertIn('category = "ok"', body)

    def test_opcode_exact_revalidation_order(self):
        source = (AI / "opcode_exact.nut").read_text(encoding="utf-8")
        self.assertIn("OpexRoad100LongVerifyStoredPlan", source)
        verify_pos = source.index("OpexRoad100LongVerifyStoredPlan(catalog, candidate, candidate.road100StoredPlan)")
        construct_pos = source.index("OpexRoad100LongConstructPlan(catalog, candidate)")
        self.assertLess(verify_pos, construct_pos,
                        "OpexRoad100LongVerifyStoredPlan doit être appelé AVANT OpexRoad100LongConstructPlan")

    def test_task_road_does_not_abandon_on_drift_or_resource(self):
        body = function_body("task_road.nut", "OpexAI::_tryBuildRoadProject")
        self.assertIn("local isAbandonable = true;", body)
        self.assertIn("road100LongBuild", body)
        self.assertIn("LONG_DRIFT", body)
        self.assertIn("CASH", body)
        self.assertIn("NOSLOT", body)
        self.assertIn("OPCAP", body)
        self.assertIn("if (isAbandonable) {", body)
        self.assertIn("this._markPairAbandoned(abandonedKey);", body)

    def test_revalidation_decision_oracle(self):
        """Oracle simulant le cycle de vie d'un candidat LONG à la revalidation."""

        def evaluate_plan(candidate, stored_plan_status, scanner_fallback_status=None):
            # 1. Vérification du plan stocké
            if candidate.get("road100StoredPlan"):
                status = stored_plan_status
                if status["ok"]:
                    return {"plan": candidate["road100StoredPlan"], "reason": "OK", "category": "ok"}
                if status["category"] == "resource":
                    return {"plan": None, "reason": status["reason"], "category": "resource"}
                # Si invalidité physique, fallback scanners+sélection
            # 2. Scanner fallback
            if scanner_fallback_status:
                status = scanner_fallback_status
                if status.get("drift"):
                    return {"plan": None, "reason": "LONG_DRIFT", "category": "drift"}
                if status.get("plan"):
                    return {"plan": status["plan"], "reason": "OK", "category": "ok"}
                return {"plan": None, "reason": "LONG_TRACEX", "category": "physical"}
            return {"plan": None, "reason": "LONG_TRACEX", "category": "physical"}

        def is_abandonable(candidate, planning):
            if candidate.get("road100LongBuild"):
                r = planning.get("reason", "")
                if planning.get("category") and planning["category"] != "physical":
                    return False
                if r in ("LONG_DRIFT", "GRAPH_DRIFT", "SEGMENT_DRIFT", "SPARSE_DRIFT",
                         "PORTAL_DRIFT", "QUOTE_EXCEEDED", "LONG_SETTING", "PORTAL_SETTING",
                         "CASH", "NOSLOT", "OPCAP"):
                    return False
            return True

        fake_plan = {"routeDistance": 100, "trace": [{"from": 1, "to": 2}]}
        cand = {"road100LongBuild": True, "road100StoredPlan": fake_plan}

        # Scénario A : Plan stocké valide physiquement et économiquement
        resA = evaluate_plan(cand, {"ok": True, "category": "ok", "reason": "OK"})
        self.assertIsNotNone(resA["plan"])
        self.assertEqual(resA["reason"], "OK")

        # Scénario B : Manque de liquidité transitoire lors de la revalidation
        resB = evaluate_plan(cand, {"ok": False, "category": "resource", "reason": "CASH"})
        self.assertIsNone(resB["plan"])
        self.assertEqual(resB["category"], "resource")
        self.assertFalse(is_abandonable(cand, resB), "Un manque de caisse ne doit pas bannir la paire")

        # Scénario C : Obstacle physique sur le plan stocké, le scanner trouve un tracé dévié (drift)
        resC = evaluate_plan(cand, {"ok": False, "category": "physical", "reason": "TRACE_BLOCKED"},
                             {"drift": True})
        self.assertIsNone(resC["plan"])
        self.assertEqual(resC["category"], "drift")
        self.assertFalse(is_abandonable(cand, resC), "Une dérive de classement ne doit pas bannir la paire")

        # Scénario D : Obstacle physique sur le plan stocké, le scanner ne trouve plus aucun tracé
        resD = evaluate_plan(cand, {"ok": False, "category": "physical", "reason": "TRACE_BLOCKED"},
                             {"drift": False, "plan": None})
        self.assertIsNone(resD["plan"])
        self.assertEqual(resD["category"], "physical")
        self.assertTrue(is_abandonable(cand, resD), "Une impossibilité physique durable doit bannir la paire")


if __name__ == "__main__":
    unittest.main()
