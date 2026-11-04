"""ROAD1Y pax_min : contrats statiques (ne compilent ni n'executent le Squirrel).

road1y_pax_min = N (0..100, defaut 0) remplace N % de la demande mensuelle
d'une paire bus-quartier (somme des deux captages) par la demande equilibree
2 * min(A, B), comme l'estimation bidirectionnelle d'AAAHogEx
(main.nut:1758 : production = min(orgPlaceProduction, placeProduction)).
A 0, la somme historique est inchangee ; hors route seule, force a 0.
"""
import re
import unittest
from pathlib import Path

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
FUNC = "OpexRoad100SoloPaxCandidates"


def _blend(captured_a, captured_b, weight):
    """Modele Python de la formule Squirrel (division entiere, valeurs >= 0)."""
    total = captured_a + captured_b
    low = min(captured_a, captured_b)
    if weight <= 0:
        return total
    return (total * (100 - weight) + 2 * low * weight) // 100


class PaxMinDeclaration(unittest.TestCase):
    def test_global_info_and_both_loaders(self):
        self.assertIn("ROAD1Y_PAX_MIN <- 0;", source("globals_pre.nut"))
        block = source("info.nut").split('name = "road1y_pax_min",')[1].split("});")[0]
        self.assertIn("min_value = 0, max_value = 100", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            get_at = code.index('ROAD1Y_PAX_MIN = AIController.GetSetting("road1y_pax_min");')
            bound_at = code.index("if (ROAD1Y_PAX_MIN < 0 || ROAD1Y_PAX_MIN > 100) ROAD1Y_PAX_MIN = 0;")
            gate_at = code.index("if (!road1yRoadOnly) ROAD1Y_PAX_MIN = 0;")
            self.assertLess(code.index("local road1yRoadOnly"), get_at, loader)
            self.assertLess(get_at, bound_at, loader)
            self.assertLess(bound_at, gate_at, loader)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertLess(bus.index("if (!road1yRoadOnly) ROAD1Y_PAX_MIN = 0;"),
                        bus.index('require("bus_districts_overrides.nut")'))

    def test_global_used_only_by_loaders_and_pair_estimate(self):
        users = sorted(p.name for p in AI.glob("*.nut")
                       if "ROAD1Y_PAX_MIN" in p.read_text(encoding="utf-8"))
        self.assertEqual(users, ["bus_districts_overrides.nut", "globals_pre.nut", "settings.nut"])
        self.assertNotIn("ROAD1Y_PAX_MIN", body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved"))


class PaxMinEstimate(unittest.TestCase):
    def setUp(self):
        self.code = body("bus_districts_overrides.nut", FUNC)

    def test_guard_sits_between_historical_sum_and_candidate(self):
        code = self.code
        monthly_at = code.index("local monthly = ROAD1Y_PAX_SITES")
        guard_at = code.index("if (ROAD1Y_PAX_MIN > 0 && ROAD1Y_PAX_SITES) {")
        make_at = code.index('OpexMakeRoadCandidate(catalog, "pax"')
        self.assertLess(monthly_at, guard_at)
        self.assertLess(guard_at, make_at)
        # The historical sum is untouched: only the guarded block rewrites monthly.
        self.assertIn("? (src.captured + dst.captured)", code)
        guarded = code[guard_at:make_at]
        for fragment in (
            "local paxMinLow = src.captured < dst.captured ? src.captured : dst.captured;",
            "(monthly * (100 - ROAD1Y_PAX_MIN)",
            "+ 2 * paxMinLow * ROAD1Y_PAX_MIN) / 100;",
            "monthly = paxMinBlend;",
            "paxMinScored++;",
            "paxMinPenalized++;",
            "paxMinLost += monthly - paxMinBlend;",
        ):
            self.assertIn(fragment, guarded)
        self.assertEqual(code.count("monthly = paxMinBlend;"), 1)
        # No other rewrite of the pair demand between the historical sum and the guard.
        self.assertNotIn("monthly =", code[monthly_at + len("local monthly ="):guard_at])
        self.assertNotIn("paxMin", code[:code.index("local paxMinScored = 0;")])

    def test_decision_log_is_guarded_and_after_generation(self):
        code = self.code
        log_at = code.index('OpexDecide("ROAD1Y_PAX_MIN"')
        self.assertIn("if (DECISION_LOG && ROAD1Y_PAX_MIN > 0) {", code)
        self.assertLess(code.index("if (DECISION_LOG && ROAD1Y_PAX_MIN > 0) {"), log_at)
        self.assertLess(code.index('OpexDecide("ROAD100_PAX_GEN"'), log_at)
        for field in ('"weight="', '" scored="', '" penalized="', '" lost_monthly="', '" positive="'):
            self.assertIn(field, code[log_at:])
        for counter in ("paxMinScored", "paxMinPenalized", "paxMinLost"):
            self.assertIn("local " + counter + " = 0;", code)

    def test_squirrel_traps_absent_from_new_code(self):
        code = self.code
        start = code.index("local paxMinScored = 0;")
        new_code = code[start:]
        self.assertNotIn("function(", new_code)
        self.assertNotIn(".find(", new_code)
        for word in ("clone", "base", "parent", "static", "delegate"):
            self.assertIsNone(re.search(r"\b" + word + r"\b", new_code.split("/*")[0]), word)

    def test_off_path_is_the_historical_generator(self):
        """Removing the guarded additions gives back the function without them."""
        code = self.code
        # body() blanks comments: anchor on code, the blanked comment stays as spaces.
        guard_at = code.index("      if (ROAD1Y_PAX_MIN > 0 && ROAD1Y_PAX_SITES) {")
        make_at = code.index('      local candidate = OpexMakeRoadCandidate(catalog, "pax"')
        self.assertLess(guard_at, make_at)
        stripped = code[:guard_at] + code[make_at:]
        stripped = stripped.replace(
            "  local paxMinScored = 0;\n  local paxMinPenalized = 0;\n  local paxMinLost = 0;\n", "")
        log_start = stripped.index("  if (DECISION_LOG && ROAD1Y_PAX_MIN > 0) {")
        log_end = stripped.index("  }\n", log_start) + 4
        stripped = stripped[:log_start] + stripped[log_end:]
        self.assertNotIn("PAX_MIN", stripped)
        self.assertNotIn("paxMin", stripped)


class PaxMinModel(unittest.TestCase):
    def test_zero_weight_is_sum_and_full_weight_is_twice_the_min(self):
        for a, b in ((371, 389), (363, 150), (184, 56), (0, 90), (120, 120)):
            self.assertEqual(_blend(a, b, 0), a + b)
            self.assertEqual(_blend(a, b, 100), 2 * min(a, b))

    def test_balanced_pairs_unchanged_unbalanced_penalised(self):
        for weight in (25, 50, 100):
            self.assertEqual(_blend(150, 150, weight), 300)
            self.assertLess(_blend(250, 50, weight), 300)
            # Monotone in the weight for an unbalanced pair.
            self.assertGreaterEqual(_blend(250, 50, weight), _blend(250, 50, min(100, weight + 25)))
        # Ranking flips as AAA does: balanced 165/165 now beats 300/30 at weight 100.
        self.assertGreater(_blend(165, 165, 100), _blend(300, 30, 100))
        self.assertEqual(_blend(165, 165, 0), _blend(300, 30, 0))

    def test_never_above_historical_sum(self):
        for a in range(0, 400, 37):
            for b in range(0, 400, 41):
                for weight in (1, 33, 50, 99, 100):
                    self.assertLessEqual(_blend(a, b, weight), a + b)


if __name__ == "__main__":
    unittest.main()
