"""AIR-GROW source contracts and dimensional mirror; no engine qualification.

The off-path pins are rebased on air-grow-marginal's HEAD before this change.
They remove only the opt-in guards, then compare the entire historical bodies.
Pre-existing failing isolation pins elsewhere deliberately remain visible.
"""
import hashlib
import json
from pathlib import Path
import re
import unittest

from test_v161_fleet_net_marginal import _function_body

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def without_guards(body):
    """Remove opt-in statements, preserving every byte of the off body."""
    pattern = re.compile(r"^ *if \(AIR_GROW_MARGINAL[^\n]*", re.M)
    while match := pattern.search(body):
        start = match.start()
        pos = body.index("(", start)
        depth = 1
        pos += 1
        while depth:
            depth += (body[pos] == "(") - (body[pos] == ")")
            pos += 1
        while body[pos].isspace():
            pos += 1
        if body[pos] == "{":
            depth = 1
            pos += 1
            while depth:
                depth += (body[pos] == "{") - (body[pos] == "}")
                pos += 1
        else:
            pos = body.index(";", pos) + 1
        if body[pos:pos + 1] == "\n":
            pos += 1
        body = body[:start] + body[pos:]
    body = body.replace("  /* Flow marginal is already net of the purchased engine's costs. */\n", "")
    return body.replace("local skipUnused = AIR_GROW_MARGINAL == 0;", "local skipUnused = true;")


def marginal(components, annual_cost, price, life_days):
    """(annual D, N, units/aircraft, rotations/year, £/unit) for each sense/cargo."""
    revenue = sum(fare * (min(demand, (n + 1) * cap * rotations)
                          - min(demand, n * cap * rotations))
                  for demand, n, cap, rotations, fare in components)
    return revenue, revenue - annual_cost - price * 365.25 / life_days


class AirGrowMarginal(unittest.TestCase):
    def test_setting_defaults_bounds_and_single_load(self):
        block = read("info.nut").split('name = "air_grow_marginal",', 1)[1].split("});", 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0, max_value = 2", block)
        self.assertIn("step_size = 1", block)
        self.assertEqual(read("settings.nut").count('GetSetting("air_grow_marginal")'), 1)
        self.assertIn("AIR_GROW_MARGINAL <- 0;", read("globals_pre.nut"))

    def test_off_path_whole_bodies_match_prechange_head(self):
        pins = json.loads((ROOT / "sweeps/fixtures/air_grow_marginal_off.json").read_text())
        for item in pins["functions"]:
            with self.subTest(function=item["function"]):
                body = _function_body(read(item["file"]), item["function"])
                self.assertEqual(hashlib.sha256(without_guards(body).encode()).hexdigest(), item["sha256"])

    def test_logs_require_decision_log(self):
        source = read("air_fleet.nut")
        occurrences = list(re.finditer(r'OpexDecide\("AIR_GROW_MARGINAL"', source))
        self.assertEqual(len(occurrences), 1)
        self.assertTrue(source[:occurrences[0].start()].endswith("if (DECISION_LOG) "))
        for name in ("air_fleet.nut", "projects_builders.nut"):
            self.assertIn("if (DECISION_LOG) OpexAirGrowMarginalLog(", read(name))
        body = _function_body(source, "OpexAirGrowMarginalLog")
        for field in ("line", "n", "d", "kn", "kn1", "drev", "cost", "amort", "dp", "prior", "decision", "fallback"):
            self.assertIn(field + "=", body)

    def test_shadow_and_unknown_do_not_apply_decision(self):
        fleet = _function_body(read("projects_builders.nut"), "OpexProjectFromFleet")
        self.assertIn('AIR_GROW_MARGINAL == 2 && marginal.fallback == "none"', fleet)
        self.assertIn("profit = marginal.dp * entry.want;", fleet)
        self.assertIn("revenue = marginal.drev * entry.want;", fleet)
        self.assertIn('entry.airGrowMarginal.fallback == "none"', fleet)
        self.assertIn("project.airGrowMarginalProfit <- true;", fleet)
        c70 = _function_body(read("projects_models.nut"), "OpexC70Profit")
        self.assertIn("project.airGrowMarginalProfit) return project.profitAnnual;", c70)
        for name in ("task_air.nut", "task_projects.nut", "air_fleet.nut"):
            self.assertIn('AIR_GROW_MARGINAL == 2 && marginal.fallback == "none" && marginal.dp <= 0', read(name))

    def test_observed_units_direction_capacity_and_fallbacks(self):
        body = _function_body(read("air_fleet.nut"), "OpexAirGrowMarginalEstimate")
        self.assertIn("(direction == 0 ? s.paxB : s.paxA)", body)
        self.assertIn("(direction == 0 ? s.mailB : s.mailA)", body)
        self.assertIn("(picked.tofloat() + waiting) * 365.25 / days", body)
        self.assertIn("r.n * cap * rotations", body)
        self.assertIn("(r.n + 1) * cap * rotations", body)
        self.assertIn("(demand < kn1 ? demand : kn1) - (demand < kn ? demand : kn)", body)
        self.assertIn("OpexC121AirTripModel", body)
        self.assertIn("s.legDaysN >= 2", body)
        self.assertNotIn("GetCargoRating", body)
        for reason in ("observation", "fleet_changed", "shared_station", "engine_capacity", "cargo", "station", "rotation", "cost", "flow_or_fare"):
            self.assertIn('"' + reason + '"', body)

    def test_no_new_saved_state_or_valuate(self):
        helper = read("air_fleet.nut").split("function OpexAirGrowMarginalEstimate", 1)[1]
        self.assertNotIn(".Valuate(", helper)
        self.assertNotIn("function(", helper)
        self.assertNotIn(".find(", helper)
        self.assertNotRegex(helper, r"\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield)\b")
        self.assertNotIn("airGrowMarginal", read("persist.nut"))
        self.assertIn("C117_AIR_LINE_STATE = {};", read("settings.nut"))

    def test_satisfied_demand_has_zero_extra_revenue(self):
        for demand in (0, 500, 1000):
            revenue, profit = marginal([(demand, 2, 50, 10, 70)], 5000, 40000, 20 * 365.25)
            self.assertEqual(revenue, 0)
            self.assertEqual(profit, -7000)

    def test_common_demand_caps_partial_increment(self):
        revenue, profit = marginal([(1200, 2, 50, 10, 70)], 5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 200 * 70)
        self.assertEqual(profit, 7000)

    def test_senses_and_cargos_are_not_pooled(self):
        components = [(3000, 2, 50, 10, 70), (100, 2, 50, 10, 70),
                      (250, 2, 10, 10, 20), (0, 2, 10, 10, 20)]
        revenue, profit = marginal(components, 5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 500 * 70 + 50 * 20)
        self.assertEqual(profit, 29000)


if __name__ == "__main__":
    unittest.main()
