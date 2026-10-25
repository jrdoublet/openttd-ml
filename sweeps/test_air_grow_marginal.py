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
    """(D, existing total seats, old rotations, new seats, new rotations, fare).

    Existing aircraft are not upgraded when a different engine is bought.
    Each sense and cargo has its own demand and capacity.
    """
    revenue = sum(fare * (min(demand, old_cap * old_rot + new_cap * new_rot)
                          - min(demand, old_cap * old_rot))
                  for demand, old_cap, old_rot, new_cap, new_rot, fare in components)
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
        for field in ("line", "n", "d", "kn", "kn1", "drev", "cost", "amort", "dp", "prior", "decision", "fallback", "win_days", "wins", "shared", "wshare", "old_engine", "buy_engine", "rot_old", "rot_buy"):
            self.assertIn(field + "=", body)

    def test_engine_choice_and_rotation_provenance_are_log_only(self):
        estimate = _function_body(read("air_fleet.nut"), "OpexAirGrowMarginalEstimate")
        log = _function_body(read("air_fleet.nut"), "OpexAirGrowMarginalLog")
        # The choice is made by the unchanged selector. No further API lookup
        # or trip model is introduced merely to print the engine identifiers.
        self.assertIn("if (engine == null) engine = OpexAirBestEngineForLine(line, catalog);", estimate)
        self.assertIn('if (DECISION_LOG) {\n    r.rawset("oldEngine", oldEngine);\n    r.rawset("buyEngine", engine);\n  }', estimate)
        self.assertIn('local rotationOld = (s.legDaysN >= 2 && s.legDays > 0) ? "c117" : "c121";', estimate)
        self.assertIn('r.rawset("rotationOld", rotationOld);', estimate)
        self.assertIn('r.rawset("rotationBuy", engine == oldEngine ? rotationOld : "c121");', estimate)
        self.assertRegex(estimate, r'if \(DECISION_LOG\) \{\s+local rotationOld = .*?\s+r\.rawset\("rotationOld", rotationOld\);\s+r\.rawset\("rotationBuy", .*?\);\s+\}')
        self.assertIn('" old_engine=" + (("oldEngine" in r) ? r.oldEngine : -1)', log)
        self.assertIn('" buy_engine=" + (("buyEngine" in r) ? r.buyEngine : -1)', log)
        self.assertIn('" rot_old=" + (("rotationOld" in r) ? r.rotationOld : "unknown")', log)
        self.assertIn('" rot_buy=" + (("rotationBuy" in r) ? r.rotationBuy : "unknown")', log)
        self.assertEqual(estimate.count('r.rawset("oldEngine"'), 1)
        self.assertEqual(estimate.count('r.rawset("buyEngine"'), 1)
        self.assertNotIn('"oldEngine"', read("persist.nut"))
        self.assertNotIn('"buyEngine"', read("persist.nut"))

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
        self.assertIn("existingPaxCap += livePaxCap;", body)
        self.assertIn("existingMailCap += liveMailCap;", body)
        self.assertIn("local existingCap = cargoIndex == 0 ? existingPaxCap : existingMailCap;", body)
        self.assertIn("local kn = existingCap * rotationsExisting;", body)
        self.assertIn("local kn1 = kn + cap * rotationsAdded;", body)
        self.assertNotIn("r.n * cap * rotations", body)
        self.assertIn("(demand < kn1 ? demand : kn1) - (demand < kn ? demand : kn)", body)
        self.assertIn("OpexC121AirTripModel", body)
        self.assertIn("s.legDaysN >= 2", body)
        self.assertIn("OpexC121AirTripModel(plan, { id = oldEngine })", body)
        self.assertIn("local addedRoundDays = engine == oldEngine ? oldRoundDays : trip.roundTripDays;", body)
        self.assertNotIn("GetCargoRating", body)
        for reason in ("obs_days", "obs_stale", "obs_trips", "obs_invalid_order", "obs_unobserved",
                       "obs_engine_change", "obs_mixed_engine", "fleet_changed",
                       "engine_capacity", "cargo", "station", "rotation", "cost", "flow_or_fare"):
            self.assertIn('"' + reason + '"', body)
        self.assertNotIn('"observation"', body)
        self.assertNotIn('"shared_station"', body)
        self.assertIn("GetCargoWaitingVia", body)

    def test_closed_window_is_bounded_transient_and_opt_in(self):
        source = read("probes.nut")
        flush = _function_body(source, "OpexC117FlushLine")
        step = _function_body(source, "OpexC117AirThroughputStep")
        self.assertIn("AIR_GROW_MARGINAL > 0 && state.lastDate > state.startDate", flush)
        self.assertIn('state.rawset("marginalHistory", history)', flush)
        self.assertIn("while (history.len() > 3) history.remove(0)", flush)
        self.assertLess(flush.index('state.rawset("marginalHistory", history)'), flush.index("if (skipChain)"))
        self.assertIn("history[history.len() - 1].bucket == bucket - 1", step)
        estimate = _function_body(read("air_fleet.nut"), "OpexAirGrowMarginalEstimate")
        fields = set(re.findall(r"\bs\.([A-Za-z]+)", estimate)) - {"wins"}
        for field in fields:
            self.assertIn('"' + field + '"', flush)
        self.assertNotIn("marginalHistory", read("persist.nut"))

    def test_observation_bounds_and_current_fleet_guards(self):
        body = _function_body(read("air_fleet.nut"), "OpexAirGrowMarginalEstimate")
        self.assertIn("local s = OpexAirGrowMarginalWindow(current)", body)
        self.assertIn("local days = s.days", body)
        self.assertIn("AIDate.GetCurrentDate() - current.lastDate > C117_AIR_SAMPLE_DAYS + 2", body)
        self.assertIn("s.invalidOrderSamples * 4 > s.liveSum", body)
        self.assertIn("s.unobservedTransitions * 4 > s.tripsA + s.tripsB", body)
        self.assertIn("s.engineChanges > 0 || current.engineChanges > 0", body)
        self.assertIn("s.mixedEngineSamples > 0 || current.mixedEngineSamples > 0", body)
        self.assertIn("current.liveSum != current.samples * r.n", body)
        self.assertIn("AIVehicle.GetEngineType(v) != current.lastEngine", body)

    def test_shortest_window_stops_at_fleet_break_or_gap(self):
        body = _function_body(read("air_fleet.nut"), "OpexAirGrowMarginalWindow")
        self.assertIn("for (local i = history.len() - 1; i >= 0; i--)", body)
        self.assertLess(body.index("s.days >= 14 && s.tripsA >= 1 && s.tripsB >= 1"),
                        body.index("local w = history[i]"))
        for guard in ("w.bucket != nextBucket - 1", "w.lastDate != nextDate",
                      "w.lastLive != s.lastLive", "w.lastEngine != s.lastEngine",
                      "w.engineChanges > 0", "w.mixedEngineSamples > 0",
                      "w.liveSum != w.samples * w.lastLive",
                      "s.liveSum != s.samples * s.lastLive"):
            self.assertIn(guard, body)
        self.assertIn("foreach (field in sums) s[field] += w[field]", body)
        self.assertIn("s.days += w.days", body)
        self.assertIn("s.wins++", body)
        self.assertNotIn(".rawset(\"marginalHistory\"", body)

    def test_no_new_saved_state_or_valuate(self):
        helper = read("air_fleet.nut").split("function OpexAirGrowMarginalWindow", 1)[1]
        self.assertNotIn(".Valuate(", helper)
        self.assertNotIn("function(", helper)
        self.assertNotIn(".find(", helper)
        self.assertNotRegex(helper, r"\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield)\b")
        self.assertNotIn("airGrowMarginal", read("persist.nut"))
        self.assertIn("C117_AIR_LINE_STATE = {};", read("settings.nut"))

    def test_satisfied_demand_has_zero_extra_revenue(self):
        for demand in (0, 500, 1000):
            revenue, profit = marginal([(demand, 100, 10, 50, 10, 70)], 5000, 40000, 20 * 365.25)
            self.assertEqual(revenue, 0)
            self.assertEqual(profit, -7000)

    def test_common_demand_caps_partial_increment(self):
        revenue, profit = marginal([(1200, 100, 10, 50, 10, 70)], 5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 200 * 70)
        self.assertEqual(profit, 7000)

    def test_senses_and_cargos_are_not_pooled(self):
        components = [(3000, 100, 10, 50, 10, 70), (100, 100, 10, 50, 10, 70),
                      (250, 20, 10, 10, 10, 20), (0, 20, 10, 10, 10, 20)]
        revenue, profit = marginal(components, 5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 500 * 70 + 50 * 20)
        self.assertEqual(profit, 29000)

    def test_faster_larger_new_engine_does_not_upgrade_existing_fleet(self):
        # Two old aircraft, 50 seats x 4 trips/year; one new, 100 seats x 10.
        # A wrong baseline using the new engine on old aircraft would be 2000.
        revenue, profit = marginal([(1000, 2 * 50, 4, 100, 10, 70)],
                                   5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 600 * 70)
        self.assertEqual(profit, 35000)

    def test_slower_smaller_new_engine_preserves_old_fleet_capacity(self):
        # Existing fast planes already cover most of the demand; the new slow
        # engine contributes only the remaining 20 units before saturation.
        revenue, _ = marginal([(1220, 3 * 40, 10, 20, 4, 70)],
                              5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 20 * 70)

    def test_sum_of_live_capacities_and_distinct_cargo_compartments(self):
        # Same-engine aircraft may have different observed refit capacities.
        # Existing PASS = (50+40) x 6; newly purchased = 30 x 12.
        # Existing MAIL = (8+12) x 6; newly purchased = 5 x 12.
        components = [(700, 90, 6, 30, 12, 70),
                      (150, 20, 6, 5, 12, 20)]
        revenue, _ = marginal(components, 5000, 40000, 20 * 365.25)
        self.assertEqual(revenue, 160 * 70 + 30 * 20)


if __name__ == "__main__":
    unittest.main()
