"""ROAD1Y pair_fleet : contrats statiques (ne compilent ni n'executent le Squirrel).

road1y_pair_fleet = N (0..24, defaut 0) reclasse, en route seule, les paires
bus-quartier de 127 tuiles au plus sur l'economie d'une flotte mure de N bus
(OpexRoadLineEconomics, fleetCapOverride = N). Flotte de construction,
capital, sites et ordre de generation restent ceux de l'estimation
historique ; le constructeur recalcule l'economie historique apres trace.
A 0 : aucun appel et aucune branche d'economie nouvelle ; hors route seule,
force a 0.
"""
import re
import unittest
from pathlib import Path

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
MODULE = "road1y_pair_fleet.nut"
HOOK = ('          if (ROAD1Y_PAIR_FLEET > 0)\n'
        '            OpexRoad1yPairFleetRank(catalog, candidate, cargo, distance, monthly, ROAD1Y_PAIR_FLEET);\n')
ECON = ('  if (ROAD1Y_PAIR_FLEET > 0 && kind == "pax" && fleetCapOverride == ROAD1Y_PAIR_FLEET) {\n'
        '    roadVehicleCap = ROAD1Y_PAIR_FLEET;\n'
        '    vehicles = vehiclesForVolume;\n'
        '    if (vehicles < 1) vehicles = 1;\n'
        '    if (vehicles > roadVehicleCap) vehicles = roadVehicleCap;\n'
        '  }\n')


def strip_comments(text):
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    return re.sub(r"//[^\n]*", "", text)


class PairFleetDeclaration(unittest.TestCase):
    def test_global_info_and_both_loaders(self):
        self.assertIn("ROAD1Y_PAIR_FLEET <- 0;", source("globals_pre.nut"))
        block = source("info.nut").split('name = "road1y_pair_fleet",')[1].split("});")[0]
        self.assertIn("min_value = 0, max_value = 24", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            get_at = code.index('ROAD1Y_PAIR_FLEET = AIController.GetSetting("road1y_pair_fleet");')
            bound_at = code.index("if (ROAD1Y_PAIR_FLEET < 0 || ROAD1Y_PAIR_FLEET > 24) ROAD1Y_PAIR_FLEET = 0;")
            gate_at = code.index("if (!road1yRoadOnly) ROAD1Y_PAIR_FLEET = 0;")
            self.assertLess(code.index("local road1yRoadOnly"), get_at, loader)
            self.assertLess(get_at, bound_at, loader)
            self.assertLess(bound_at, gate_at, loader)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertLess(bus.index("if (!road1yRoadOnly) ROAD1Y_PAIR_FLEET = 0;"),
                        bus.index('require("bus_districts_overrides.nut")'))

    def test_global_used_only_by_loaders_economy_and_the_hook(self):
        def code(text):
            return re.sub(r'"(?:\\.|[^"\\])*"', '""', strip_comments(text))
        users = sorted(p.name for p in AI.glob("*.nut")
                       if "ROAD1Y_PAIR_FLEET" in code(p.read_text(encoding="utf-8")))
        self.assertEqual(users, ["bus_districts_overrides.nut", "economy.nut",
                                 "globals_pre.nut", "settings.nut"])
        # The module receives N as a parameter and never reads the switch.
        self.assertNotIn("ROAD1Y_PAIR_FLEET", code(source(MODULE)))

    def test_module_is_required_with_the_other_road1y_modules(self):
        main = source("main.nut")
        self.assertEqual(main.count('require("road1y_pair_fleet.nut");'), 1)
        self.assertLess(main.index('require("road1y_spread.nut");'),
                        main.index('require("road1y_pair_fleet.nut");'))
        self.assertLess(main.index('require("road1y_pair_fleet.nut");'),
                        main.index('require("opcode_exact.nut");'))


class PairFleetHooks(unittest.TestCase):
    def test_generator_hook_after_abandon_filter_before_append(self):
        raw = source("bus_districts_overrides.nut")
        self.assertEqual(raw.count(HOOK), 1)
        code = body("bus_districts_overrides.nut", "OpexRoad100SoloPaxCandidates")
        hook_at = code.index("if (ROAD1Y_PAIR_FLEET > 0)")
        self.assertLess(code.index("OpexAbandonedPairKey(candidate) in abandonedPairs) continue;"), hook_at)
        self.assertLess(code.index("candidate.road1yBusSite <- true;"), hook_at)
        self.assertLess(hook_at, code.index('OpexDecide("BUS_DISTRICT_CAND"'))
        self.assertLess(hook_at, code.index("out.append(candidate);"))
        joined = "".join(p.read_text(encoding="utf-8") for p in AI.glob("*.nut"))
        self.assertEqual(joined.count("OpexRoad1yPairFleetRank("), 2)  # definition + hook

    def test_economy_rule_only_for_the_requested_override(self):
        econ = body("economy.nut", "OpexRoadLineEconomics")
        self.assertEqual(econ.count(ECON), 1)
        rule_at = econ.index(ECON)
        self.assertLess(econ.index('if (fleetCapOverride == 30 && kind == "pax") roadVehicleCap = 30;'), rule_at)
        self.assertLess(econ.index("if (vehicles > roadVehicleCap) vehicles = roadVehicleCap;"), rule_at)
        self.assertLess(rule_at, econ.index('if (ROAD1Y_PAX_ECONOMY && kind == "pax") {'))
        self.assertLess(rule_at, econ.index("local monthlyCapacity = vehicles * engine.capacity * tripsPerMonth;"))

    def test_off_paths_are_historical(self):
        """Removing both guarded blocks leaves no pair_fleet token in either function."""
        gen = source("bus_districts_overrides.nut").replace(HOOK, "")
        gen = gen[gen.index("function OpexRoad100SoloPaxCandidates"):]
        gen = gen[:gen.index("\nfunction ", 10)]
        econ = source("economy.nut").replace(ECON, "")
        econ = econ[econ.index("function OpexRoadLineEconomics"):]
        econ = econ[:econ.index("\nfunction ", 10)]
        for text in (gen, econ):
            text = strip_comments(text)
            self.assertNotIn("PAIR_FLEET", text)
            self.assertNotIn("PairFleet", text)

    def test_builder_reapplies_historical_economics(self):
        # The built line's prediction never sees the mature estimate.
        raw = source("bus_districts_overrides.nut")
        self.assertIn('("road100FleetCap" in candidate) ? candidate.road100FleetCap : 0);', raw)
        self.assertIn("OpexApplyRoadEconomics(candidate, economics, actualDist);", raw)


class PairFleetModule(unittest.TestCase):
    def setUp(self):
        self.code = body(MODULE, "OpexRoad1yPairFleetRank")

    def test_scope_and_mature_economics(self):
        code = self.code
        self.assertIn("if (fleet <= 0 || distance > 127) return;", code)
        self.assertIn('OpexRoadLineEconomics(catalog, cargo, distance, monthly, engine, "pax",\n      null, fleet);', code)
        self.assertIn("if (mature == null || mature.profitAnnual <= candidate.profitAnnual) {", code)

    def test_ranking_fields_replaced_build_fields_kept(self):
        code = self.code
        for field in ("profitAnnual", "revenueAnnual", "runningAnnual", "amortAnnual", "roi", "ratio"):
            self.assertIn("candidate." + field + " = ", code)
        for kept in ("trains", "capital", "src", "dst", "siteA", "siteB", "monthly",
                     "vehiclesForVolume", "roadVehicleCap", "carried", "immobilise"):
            self.assertNotIn("candidate." + kept + " = ", code)
            self.assertNotIn("candidate." + kept + " <- ", code)
        self.assertIn("(mature.profitAnnual * 1000) / candidate.capital", code)

    def test_decision_log_is_guarded(self):
        text = strip_comments(source(MODULE))
        self.assertEqual(text.count('OpexDecide("ROAD1Y_PAIR_FLEET"'), 2)
        self.assertEqual(text.count("if (DECISION_LOG)\n    OpexDecide("), 1)
        self.assertEqual(text.count("if (DECISION_LOG)\n      OpexDecide("), 1)
        for action in ("action=keep", "action=rank"):
            self.assertIn(action, text)

    def test_squirrel_traps_absent(self):
        code = strip_comments(source(MODULE))
        self.assertNotIn("function(", code)
        self.assertNotIn("const ", code)
        for word in ("clone", "base", "static", "delegate"):
            self.assertIsNone(re.search(r"\b" + word + r"\b", code), word)


if __name__ == "__main__":
    unittest.main()
