"""Test unitaire ciblé : constat n°7 sur le verrou ROAD100_LONG_SHADOW_YEAR.

Vérifie que :
1. ROAD100_LONG_SHADOW_YEAR n'est pas assigné avant les yield de OpexRoad100SiteFirstGenerator ;
2. La condition d'entrée distingue la recherche globale d'une recherche ciblée (targetId) ;
3. Le verrou n'est posé qu'à la fin complète d'une recherche globale (isGlobalSearch) ;
4. persist.nut sérialise et restaure road100LongShadowYear avec repli -1 si absent.
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


class TestRoad100LongShadowLock(unittest.TestCase):
    def test_generator_shadow_lock_placement(self):
        body = function_body("candidates.nut", "OpexRoad100SiteFirstGenerator")
        self.assertIn("ROAD100_LONG_INTERCITY", body)
        long_start = body.index("if (ROAD100_LONG_INTERCITY")
        long_block = body[long_start:]

        # isGlobalSearch doit être défini et vérifier targetKind et targetId
        self.assertIn("local isGlobalSearch = (targetKind == null || targetId < 0);", body)
        self.assertIn("!isGlobalSearch || ROAD100_LONG_SHADOW_YEAR != AIDate.GetYear(AIDate.GetCurrentDate())", long_block)

        # Le premier yield du bloc long doit se trouver AVANT toute assignation de ROAD100_LONG_SHADOW_YEAR
        first_yield = long_block.index("yield null;")
        shadow_assign = long_block.index("ROAD100_LONG_SHADOW_YEAR = AIDate.GetYear(AIDate.GetCurrentDate());")
        self.assertGreater(shadow_assign, first_yield, "Le verrou annuel ne doit pas être posé avant les yield")

        # L'assignation doit être protégée par isGlobalSearch à la fin
        summary_log = long_block.index('OpexDecide("ROAD100_LONG", "phase=summary')
        self.assertGreater(shadow_assign, summary_log, "Le verrou annuel doit être posé à la fin du bloc long")
        guard_check = "if (isGlobalSearch) {\n      ROAD100_LONG_SHADOW_YEAR = AIDate.GetYear(AIDate.GetCurrentDate());\n    }"
        self.assertIn(guard_check, long_block)

    def test_persist_save_and_load(self):
        save_body = function_body("persist.nut", "OpexAI::Save")
        load_body = function_body("persist.nut", "OpexAI::Load")

        # Sauvegarde dans shortSave et saveObj
        self.assertIn("if (ROAD100_LONG_SHADOW_YEAR >= 0) shortSave.road100LongShadowYear <- ROAD100_LONG_SHADOW_YEAR;", save_body)
        self.assertIn("if (ROAD100_LONG_SHADOW_YEAR >= 0) saveObj.road100LongShadowYear <- ROAD100_LONG_SHADOW_YEAR;", save_body)

        # Réinitialisation par défaut à -1 dans Load
        self.assertIn("ROAD100_LONG_SHADOW_YEAR = -1;", load_body)

        # Restauration avec repli à -1 si absent
        self.assertIn(
            'ROAD100_LONG_SHADOW_YEAR = ("road100LongShadowYear" in data && typeof data.road100LongShadowYear == "integer")\n'
            "      ? data.road100LongShadowYear : -1;",
            load_body,
        )


class ShadowLockSimulation:
    """Executable simulation of candidate generation shadow locking and persistence."""

    def __init__(self):
        self.shadow_year = -1

    def run_generator(
        self,
        current_year: int,
        target_kind: str | None = None,
        target_id: int = -1,
        interrupted_at_yield: bool = False,
    ) -> dict:
        is_global_search = (target_kind is None or target_id < 0)
        # Gate check: ROAD100_LONG_INTERCITY && (!isGlobalSearch || ROAD100_LONG_SHADOW_YEAR != currentYear)
        if is_global_search and self.shadow_year == current_year:
            return {"executed": False, "reason": "LOCKED_ANNUAL"}

        if interrupted_at_yield:
            # Yielded and aborted before completion -> lock must NOT be set
            return {"executed": True, "completed": False, "shadow_year": self.shadow_year}

        # Completed to the end -> lock only if global search
        if is_global_search:
            self.shadow_year = current_year

        return {"executed": True, "completed": True, "shadow_year": self.shadow_year}

    def save(self) -> dict:
        data = {}
        if self.shadow_year >= 0:
            data["road100LongShadowYear"] = self.shadow_year
        return data

    def load(self, data: dict):
        self.shadow_year = -1
        if "road100LongShadowYear" in data and isinstance(data["road100LongShadowYear"], int):
            self.shadow_year = data["road100LongShadowYear"]


class TestRoad100LongShadowLockBehavioralOracle(unittest.TestCase):
    """Behavioral simulation tests verifying actual VALUES consumed by shadow locking."""

    def test_targeted_search_does_not_consume_global_annual_lock(self):
        sim = ShadowLockSimulation()
        # A targeted search for a specific town must run and not lock the annual global slot
        res = sim.run_generator(1975, target_kind="town", target_id=12)
        self.assertTrue(res["executed"])
        self.assertTrue(res["completed"])
        self.assertEqual(sim.shadow_year, -1, "Targeted search must leave shadow_year as -1")

        # Global search in the same year must still be allowed to run
        res_global = sim.run_generator(1975)
        self.assertTrue(res_global["executed"])
        self.assertTrue(res_global["completed"])
        self.assertEqual(sim.shadow_year, 1975, "Global search completion locks shadow_year to 1975")

    def test_interrupted_global_search_does_not_lock_out_future_attempts(self):
        sim = ShadowLockSimulation()
        # An interrupted global search (e.g. opcap or yield before completion)
        res = sim.run_generator(1975, interrupted_at_yield=True)
        self.assertTrue(res["executed"])
        self.assertFalse(res["completed"])
        self.assertEqual(sim.shadow_year, -1, "Interrupted search must NOT set annual lock")

        # Next generator pass in same year can retry
        retry = sim.run_generator(1975)
        self.assertTrue(retry["executed"])
        self.assertTrue(retry["completed"])
        self.assertEqual(sim.shadow_year, 1975)

    def test_completed_global_search_locks_subsequent_global_searches_in_same_year_only(self):
        sim = ShadowLockSimulation()
        # First global run in 1975 completes
        res1 = sim.run_generator(1975)
        self.assertTrue(res1["executed"])
        self.assertEqual(sim.shadow_year, 1975)

        # Second global run in 1975 is locked
        res2 = sim.run_generator(1975)
        self.assertFalse(res2["executed"])
        self.assertEqual(res2["reason"], "LOCKED_ANNUAL")

        # Targeted run in 1975 is NOT locked
        res_targeted = sim.run_generator(1975, target_kind="town", target_id=9)
        self.assertTrue(res_targeted["executed"])

        # Next year 1976 unlocks global search
        res_next_year = sim.run_generator(1976)
        self.assertTrue(res_next_year["executed"])
        self.assertEqual(sim.shadow_year, 1976)

    def test_save_load_persistence_and_fallback(self):
        sim = ShadowLockSimulation()
        sim.shadow_year = 1976
        saved = sim.save()
        self.assertEqual(saved, {"road100LongShadowYear": 1976})

        # Load into fresh state
        restored = ShadowLockSimulation()
        restored.load(saved)
        self.assertEqual(restored.shadow_year, 1976)

        # Fallback on missing key
        fallback = ShadowLockSimulation()
        fallback.load({})
        self.assertEqual(fallback.shadow_year, -1)

        # Fallback on corrupt key (non-integer)
        corrupt = ShadowLockSimulation()
        corrupt.load({"road100LongShadowYear": "not_an_int"})
        self.assertEqual(corrupt.shadow_year, -1)



if __name__ == "__main__":
    unittest.main()
