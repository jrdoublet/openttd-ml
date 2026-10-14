"""Static tests for V204: shrink rail train length to fit cash budget when portfolio has no fundable rail candidates."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "ai" / "OpexAI"


class TestV204ShrinkToFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info_src = (AI_DIR / "info.nut").read_text(encoding="utf-8")
        cls.globals_src = (AI_DIR / "globals_pre.nut").read_text(encoding="utf-8")
        cls.settings_src = (AI_DIR / "settings.nut").read_text(encoding="utf-8")
        cls.economy_src = (AI_DIR / "economy.nut").read_text(encoding="utf-8")
        cls.selection_src = (AI_DIR / "projects_selection.nut").read_text(encoding="utf-8")
        cls.task_rail_src = (AI_DIR / "task_rail.nut").read_text(encoding="utf-8")
        cls.builder_rail_src = (AI_DIR / "builder_rail.nut").read_text(encoding="utf-8")

    def test_setting_declaration_and_defaults(self):
        """Setting v204_shrink_to_fit declared with 4 values = 0, range 0..8, step 1."""
        self.assertIn('"v204_shrink_to_fit"', self.info_src)
        match = re.search(
            r'name\s*=\s*"v204_shrink_to_fit".*?'
            r'min_value\s*=\s*0.*?max_value\s*=\s*8.*?step_size\s*=\s*1.*?'
            r'easy_value\s*=\s*0.*?medium_value\s*=\s*0.*?hard_value\s*=\s*0.*?custom_value\s*=\s*0',
            self.info_src,
            re.DOTALL
        )
        self.assertIsNotNone(match, "v204_shrink_to_fit setting declaration does not match required 0..8 defaults 0")

    def test_global_pre_initialization(self):
        """Global V204_SHRINK_TO_FIT initialized to 0."""
        self.assertRegex(self.globals_src, r'V204_SHRINK_TO_FIT\s*<-\s*0;')

    def test_single_read_in_settings(self):
        """Setting read once into V204_SHRINK_TO_FIT in settings.nut."""
        self.assertEqual(self.settings_src.count('GetSetting("v204_shrink_to_fit")'), 1)
        self.assertIn("V204_SHRINK_TO_FIT =", self.settings_src)

    def test_no_forbidden_squirrel_words_in_v204_code(self):
        """Forbidden Squirrel words (clone, parent, base) must not appear in V204 additions."""
        v204_snippets = []
        for src in (self.economy_src, self.selection_src, self.task_rail_src, self.builder_rail_src):
            for block in re.findall(r'(?:/\*\s*V204[^*]*\*/.*?)(?=\n/\*|\nfunction [A-Z]|\Z)', src, re.DOTALL):
                v204_snippets.append(block)

        all_v204 = "\n".join(v204_snippets)
        for forbidden in ("clone", "parent", "base"):
            matches = re.findall(rf'\b{forbidden}\b', all_v204)
            self.assertEqual(matches, [], f"Forbidden word '{forbidden}' found in V204 code")

    def test_economy_shrink_functions_exist(self):
        """OpexRailShrinkEconomics and OpexRailShrinkEconomicsInPlace exist in economy.nut."""
        self.assertIn("function OpexRailShrinkEconomics(candidate, targetWagons)", self.economy_src)
        self.assertIn("function OpexRailShrinkEconomicsInPlace(candidate, targetWagons)", self.economy_src)

    def test_apply_rail_economics_preserves_shrunk_state(self):
        """OpexApplyRailEconomics preserves candidate.wagons, platformLength and re-shrinks when v204Shrunk."""
        apply_fn = self.economy_src.split("function OpexApplyRailEconomics(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn('"v204Shrunk" in candidate', apply_fn)
        self.assertIn("shrunkWagons", apply_fn)
        self.assertIn("origPlatformLength", apply_fn)
        self.assertIn("OpexRailShrinkEconomicsInPlace(candidate, shrunkWagons);", apply_fn)

    def test_selection_fit_rail_alternatives_exists(self):
        """OpexV204FitRailAlternativesToBudget exists and is called in OpexProjectSelectAffordable."""
        self.assertIn("function OpexV204FitRailAlternativesToBudget(alternatives, capitalBudget)", self.selection_src)
        self.assertIn("function OpexV204CompareProjects(a, b)", self.selection_src)

        select_fn = self.selection_src.split("function OpexProjectSelectAffordable(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("if (V204_SHRINK_TO_FIT > 0)", select_fn)
        self.assertIn("alternatives = OpexV204FitRailAlternativesToBudget(alternatives, capitalBudget);", select_fn)

    def test_shrink_only_when_no_rail_is_fundable(self):
        """OpexV204FitRailAlternativesToBudget checks if any rail candidate is already fundable before shrinking."""
        fit_fn = self.selection_src.split("function OpexV204FitRailAlternativesToBudget(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("local hasFundableRail = false;", fit_fn)
        self.assertIn("if (hasFundableRail) return alternatives;", fit_fn)

    def test_shrink_marks_candidate_fields(self):
        """Candidate is marked with v204Shrunk <- true and v204FullWagons <- origWagons."""
        fit_fn = self.selection_src.split("function OpexV204FitRailAlternativesToBudget(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("candidate.v204Shrunk <- true;", fit_fn)
        self.assertIn("candidate.v204FullWagons <- origWagons;", fit_fn)

    def test_decision_log_emits_v204_step_shrink_and_grow(self):
        """OpexDecide('V204', 'step=shrink|grow ok=.. wagons=a->b capital=.. budget=..') emitted under DECISION_LOG."""
        self.assertIn('OpexDecide("V204", "step=shrink ok=', self.selection_src)
        self.assertIn('OpexDecide("V204", "step=grow ok=', self.task_rail_src)

    def test_builder_rail_updates_plan_capital_from_candidate(self):
        """builder_rail.nut sets plan.capital = candidate.capital after OpexApplyRailEconomics."""
        prepare_fn = self.builder_rail_src.split("function OpexPrepareRailRoute(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("OpexApplyRailEconomics(candidate, economics);\n  plan.capital = candidate.capital;", prepare_fn)

        complete_fn = self.builder_rail_src.split("function OpexCompleteRailRouteAfterSearch(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("OpexApplyRailEconomics(candidate, economics);\n      plan.capital = candidate.capital;", complete_fn)

    def test_line_records_v204_shrunk(self):
        """Recorded rail line captures v204Shrunk and v204FullWagons."""
        record_fn = self.task_rail_src.split("function OpexAI::_recordRailAttempt(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn('("v204Shrunk" in candidate) && candidate.v204Shrunk', record_fn)
        self.assertIn("built.v204Shrunk <- true;", record_fn)
        self.assertIn("built.v204FullWagons <-", record_fn)

    def test_shrink_arithmetic_formulas(self):
        """Python verification of the shrink arithmetic logic."""
        # Simulated candidate
        trains = 1
        loco_price = 15000
        wagon_price = 2500
        orig_wagons = 8
        orig_vehicle_cost = trains * (loco_price + orig_wagons * wagon_price)  # 35000
        infra_cost = 25000
        orig_capital = orig_vehicle_cost + infra_cost  # 60000
        loco_life = 20
        infra_amort = 0
        orig_amort = orig_vehicle_cost // loco_life + infra_amort  # 1750
        running_cost = 4000
        monthly_prod = 300
        station_rating = 70
        offered = int(monthly_prod * station_rating / 100.0)  # 210
        wagon_cap = 30
        trips = 2
        orig_capacity = trains * orig_wagons * wagon_cap * trips  # 8 * 30 * 2 = 480
        orig_carried = min(offered, orig_capacity)  # 210
        orig_revenue = orig_carried * 100 * 12  # 252000
        orig_profit = orig_revenue - running_cost - orig_amort

        # Shrink to 4 wagons
        target_wagons = 4
        new_vehicle_cost = trains * (loco_price + target_wagons * wagon_price)  # 25000
        delta_cost = orig_vehicle_cost - new_vehicle_cost  # 10000
        new_capital = orig_capital - delta_cost  # 50000
        new_capacity = (orig_capacity * target_wagons) // orig_wagons  # 240
        new_carried = min(offered, new_capacity)  # min(210, 240) = 210 (still fully carried!)
        new_revenue = int(orig_revenue * new_carried / orig_carried)  # 252000
        delta_amort = delta_cost // loco_life  # 500
        new_amort = orig_amort - delta_amort  # 1250
        new_profit = new_revenue - running_cost - new_amort

        self.assertEqual(new_capital, 50000)
        self.assertEqual(new_capacity, 240)
        self.assertEqual(new_carried, 210)
        self.assertEqual(new_revenue, 252000)
        self.assertGreater(new_profit, orig_profit)  # Fewer wagons carrying same cargo -> higher profit!

        # Shrink to 2 wagons
        target_wagons_2 = 2
        new_veh_2 = trains * (loco_price + target_wagons_2 * wagon_price)  # 20000
        delta_2 = orig_vehicle_cost - new_veh_2  # 15000
        new_cap_2 = orig_capital - delta_2  # 45000
        new_capacity_2 = (orig_capacity * target_wagons_2) // orig_wagons  # 120
        new_carried_2 = min(offered, new_capacity_2)  # min(210, 120) = 120 (capacity capped!)
        new_revenue_2 = int(orig_revenue * new_carried_2 / orig_carried)  # 252000 * 120 / 210 = 144000
        self.assertEqual(new_carried_2, 120)
        self.assertEqual(new_revenue_2, 144000)


if __name__ == "__main__":
    unittest.main()
