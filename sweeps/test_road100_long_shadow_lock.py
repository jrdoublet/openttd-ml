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


if __name__ == "__main__":
    unittest.main()
