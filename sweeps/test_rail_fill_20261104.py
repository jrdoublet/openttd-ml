"""Contrats RAIL-FILL (rail_fill, défaut 0) — 04/11/2026.

Mode opt-in de V284 : porte de caisse 250 k£ / deux ans, taille visée sur la
production réelle de l'industrie (note cible 75 %, 1,5 cycle) bornée par le
quai existant, seconde rame toujours à 1 M£, rame remplie protégée de V257.
Tests de source : câblage, projection OFF octet pour octet, ordre des gardes,
références et arités des appels (pas de compilateur Squirrel ici).
"""

import hashlib
import re
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))

from rail_fill_off import INSERTIONS, REPLACED, off_source  # noqa: E402
from rail_loop_off import off_source as rail_loop_off  # noqa: E402
from rail_keep_off import off_source as rail_keep_off  # noqa: E402
from rail_net_off import off_source as rail_net_off  # noqa: E402
from test_rail_loop_20261104 import (  # noqa: E402
    PRE_INTERVENTION_SHA, call_args, function_body, global_signatures, read, strip_squirrel)

# Empreintes au commit 47395b4 des fichiers touchés par RAIL-FILL seulement.
PRE_SHA = dict(PRE_INTERVENTION_SHA)
PRE_SHA.update({
    "task_v284.nut": "088b1e624cb68c4e996924a47cdf685f616ee1fe8fdf97e5e4a4fd50eec91574",
    "task_v257.nut": "d6bef0f569bd840162aa743079802fe68124b2e53f23a59608d90afb96190cd5",
})


class RailFillWiring(unittest.TestCase):
    def test_setting_default_zero_boolean(self):
        info = read("info.nut")
        block = info[info.index('name = "rail_fill"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0", block)
        self.assertIn("AICONFIG_BOOLEAN", block)
        self.assertEqual(read("globals_pre.nut").count("RAIL_FILL <- false;"), 1)
        self.assertEqual(read("settings.nut").count('GetSetting("rail_fill")'), 1)
        self.assertEqual(read("main.nut").count('require("rail_fill.nut");'), 1)

    def test_every_new_line_is_guarded(self):
        for name, fragments in INSERTIONS.items():
            for fragment in fragments:
                code = fragment.strip()
                if code.startswith("if ("):
                    self.assertTrue("RAIL_FILL" in code or "railFillPlan" in code, (name, code))
        self.assertTrue(REPLACED["task_v284.nut"][0][0].startswith("  if (!v233Input && RAIL_FILL) {"))

    def test_off_projection_restores_pre_intervention_bytes(self):
        for name, digest in PRE_SHA.items():
            with self.subTest(name=name):
                source = rail_keep_off(name, rail_net_off(name, read(name)))
                projected = rail_loop_off(name, off_source(name, source))
                self.assertEqual(hashlib.sha256(projected.encode("utf8")).hexdigest(), digest)
                self.assertEqual(off_source(name, off_source(name, source)), off_source(name, source))

    def test_partial_hunk_fails_closed(self):
        damaged = read("task_v284.nut").replace("OpexRailFillGateClosed(year)", "OpexRailFillGateClosed(year + 0)")
        with self.assertRaises(AssertionError):
            off_source("task_v284.nut", damaged)


class RailFillBehaviour(unittest.TestCase):
    def setUp(self):
        self.v284 = read("task_v284.nut")
        self.select = function_body(self.v284, "OpexV284Select")
        self.module = read("rail_fill.nut")
        self.code = strip_squirrel(self.module)

    def test_historic_gate_kept_off_and_new_gate_only_on(self):
        self.assertIn("  if (!v233Input && RAIL_FILL) {\n    if (OpexRailFillGateClosed(year)) return false;\n"
                      "  } else if (!v233Input && (year < OPEX_START_YEAR + V284_RAIL_GROWTH"
                      " || OpexAvailableCapital() < 1000000)) return false;", self.select)
        self.assertIn("RAIL_FILL_MIN_CASH <- 250000;", self.module)
        gate = function_body(self.code, "OpexRailFillGateClosed")
        self.assertIn("OPEX_START_YEAR + RAIL_FILL_START_YEARS", gate)

    def test_skips_a_line_while_rail_loop_converts_it(self):
        self.assertIn('if (RAIL_FILL && ("railLoop" in line) && line.railLoop == 1) continue;', self.select)

    def test_second_train_keeps_the_one_million_gate(self):
        self.assertIn("if (RAIL_FILL && atLimit && !v233Input && !OpexRailFillAddAllowed()) continue;",
                      self.select)
        self.assertIn(">= 1000000", function_body(self.code, "OpexRailFillAddAllowed"))

    def test_fill_plan_only_replaces_the_wagon_step_and_before_the_traction_guard(self):
        plan_at = self.select.index("local railFillPlan =")
        self.assertLess(self.select.index("OpexV284Equipment(line, best.vehicle, best.wagon, number)"), plan_at)
        self.assertLess(plan_at, self.select.index("if (equipment == null) {"))
        self.assertIn("RAIL_FILL && !best.add && !v233Input && (ESTIM_UNIFIE & 4) == 0", self.select)
        self.assertLess(plan_at, self.select.index("state.pending = {"))
        self.assertIn("if (railFillPlan != null) state.pending.railFill <- true;", self.select)

    def test_target_uses_uncensored_production_and_platform_cap(self):
        target = function_body(self.code, "OpexRailFillTarget")
        self.assertIn("OpexRailFillProduction(line)", target)
        self.assertIn("if (target > maxWagons) target = maxWagons;", target)
        self.assertIn("if (target < number + 1) target = number + 1;", target)
        prod = function_body(self.code, "OpexRailFillProduction")
        self.assertIn("AIIndustry.GetLastMonthProduction(industry, line.cargo)", prod)
        self.assertNotIn("GetCargoWaiting", prod)

    def test_plan_keeps_v284_traction_rule_and_cash_reserve(self):
        plan = function_body(self.code, "OpexRailFillPlan")
        self.assertIn("OpexV284Equipment(line, vehicle, wagon, n)", plan)
        self.assertIn("price + RAIL_FILL_RESERVE", plan)
        self.assertIn("for (local n = target; n > number + 1; n--)", plan)

    def test_filled_line_is_marked_after_adoption_and_skipped_by_v257(self):
        adopt = self.v284.index("OpexV284Adopt(owner, line, pending);\n  if (RAIL_FILL")
        self.assertGreater(adopt, 0)
        review = function_body(read("task_v257.nut"), "OpexAI::_v257Review")
        self.assertIn('if (RAIL_FILL && ("railFill" in line) && line.railFill) return;', review)

    def test_depot_recheck_still_bounds_the_consist(self):
        self.assertIn("pending.wagons > OpexRailNominalMaxWagons(limit)", self.v284)
        self.assertIn("local cashNeed = price + 50000;", self.v284)

    def test_module_static_safety(self):
        stack, pairs = [], {")": "(", "]": "[", "}": "{"}
        for ch in self.code:
            if ch in "([{":
                stack.append(ch)
            elif ch in ")]}":
                self.assertTrue(stack and stack[-1] == pairs[ch])
                stack.pop()
        self.assertEqual(stack, [])
        for bad in ("getroottable", ".find(", "Sleep(", ".Valuate(", "_railSearch"):
            self.assertNotIn(bad, self.code)
        self.assertIsNone(re.search(r"function\s*\(", self.code))
        sigs = global_signatures()
        for text in (self.code, strip_squirrel(self.select)):
            for m in re.finditer(r"\b(Opex\w+)\s*\(", text):
                if re.search(r"function\s+$", text[max(0, m.start() - 12):m.start()]):
                    continue
                with self.subTest(call=m.group(1)):
                    self.assertIn(m.group(1), sigs)
                    n = len(call_args(text, m.end() - 1))
                    self.assertTrue(any(r <= n <= t for r, t in sigs[m.group(1)]),
                                    f"{m.group(1)}: {n} args, {sigs[m.group(1)]}")


if __name__ == "__main__":
    unittest.main()
