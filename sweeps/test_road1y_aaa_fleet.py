"""ROAD1Y aaa_fleet : contrats statiques (ne compilent ni n'executent le Squirrel).

road1y_aaa_fleet = 1 (0..1, defaut 0) remplace, pour les lignes bus PAX en
route seule, le plafond fixe 4 x min(arrets) et la regle somme >= capacite de
OpexRoad1yRefleetSaved par la gestion de flotte d'AAAHogEx (route.nut) :
plafond EstimateMaxVehicles, ajout sur min(attente A, B) sans deux bus arretes
en charge a la source, retrait des bus arretes au-dela de trois quand la gare
est peu fournie. A 0 : aucun appel, chemin historique inchange ; hors route
seule, force a 0.
"""
import re
import unittest
from pathlib import Path

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
MODULE = "road1y_aaa_fleet.nut"
HOOK = ('    if (ROAD1Y_AAA_FLEET && ("kind" in line) && line.kind == "pax")\n'
        '      target = OpexRoad1yAaaFleetTarget(this, line, have, capacity, waitingA, waitingB, year);\n')


def estimate(distance, speed):
    """Modele Python d'EstimateMaxVehicles (AAAHogEx route.nut:2374-2380, quai route = 1 jour)."""
    speed = max(4, speed)
    days = distance * 664 // speed // 24
    return min(days * 2 + 1, (distance + 4) * 16 // 8) + 2


def decide(have, capacity, wait_a, wait_b, stopped, stopped_src, cap):
    """Modele Python d'une decision mensuelle (sans vente en attente)."""
    low = min(wait_a, wait_b)
    bottom = min(50, capacity)
    if have > 3 and low < bottom and stopped > 3:
        return "send", 0
    needs = 30 if have < 10 else 100
    want = 0
    if low > needs and stopped_src < 2 and capacity > 0:
        want = max(0, min((low - bottom) // capacity, 4, cap - have))
    return ("add" if want > 0 else "state"), want


class AaaFleetDeclaration(unittest.TestCase):
    def test_global_info_and_both_loaders(self):
        self.assertIn("ROAD1Y_AAA_FLEET <- 0;", source("globals_pre.nut"))
        block = source("info.nut").split('name = "road1y_aaa_fleet",')[1].split("});")[0]
        self.assertIn("min_value = 0, max_value = 1", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            get_at = code.index('ROAD1Y_AAA_FLEET = AIController.GetSetting("road1y_aaa_fleet");')
            bound_at = code.index("if (ROAD1Y_AAA_FLEET < 0 || ROAD1Y_AAA_FLEET > 1) ROAD1Y_AAA_FLEET = 0;")
            gate_at = code.index("if (!road1yRoadOnly) ROAD1Y_AAA_FLEET = 0;")
            self.assertLess(code.index("local road1yRoadOnly"), get_at, loader)
            self.assertLess(get_at, bound_at, loader)
            self.assertLess(bound_at, gate_at, loader)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertLess(bus.index("if (!road1yRoadOnly) ROAD1Y_AAA_FLEET = 0;"),
                        bus.index('require("bus_districts_overrides.nut")'))

    def test_global_used_only_by_loaders_and_the_hook(self):
        # String literals (the OpexDecide kind "ROAD1Y_AAA_FLEET") are not reads.
        def code(text):
            return re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        users = sorted(p.name for p in AI.glob("*.nut")
                       if "ROAD1Y_AAA_FLEET" in code(p.read_text(encoding="utf-8")))
        self.assertEqual(users, ["bus_districts_overrides.nut", "globals_pre.nut", "settings.nut"])
        # The module itself never reads the switch: only the guarded hook calls it.
        self.assertNotIn("ROAD1Y_AAA_FLEET", code(source(MODULE)))

    def test_module_is_required_with_the_other_road1y_modules(self):
        main = source("main.nut")
        self.assertEqual(main.count('require("road1y_aaa_fleet.nut");'), 1)
        self.assertLess(main.index('require("road1y_spread.nut");'),
                        main.index('require("road1y_aaa_fleet.nut");'))
        self.assertLess(main.index('require("road1y_aaa_fleet.nut");'),
                        main.index('require("opcode_exact.nut");'))


class AaaFleetHook(unittest.TestCase):
    def setUp(self):
        self.raw = source("bus_districts_overrides.nut")
        self.code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")

    def test_single_guarded_call_after_historical_rules_before_refleet(self):
        joined = "".join(p.read_text(encoding="utf-8") for p in AI.glob("*.nut"))
        self.assertEqual(joined.count("OpexRoad1yAaaFleetTarget("), 2)  # definition + hook
        self.assertEqual(self.raw.count(HOOK), 1)
        hook_at = self.code.index("if (ROAD1Y_AAA_FLEET && (\"kind\" in line) && line.kind == \"pax\")")
        self.assertLess(self.code.index("local road1yCap = fleetPerStop * road1yStops;"), hook_at)
        self.assertLess(hook_at, self.code.index("if (have >= target) {"))
        self.assertLess(hook_at, self.code.index("OpexRoadRefleet(this._catalog, line, have, target)"))

    def test_off_path_is_the_historical_refleet(self):
        """Removing the guarded hook (and its comment) leaves no aaa_fleet token."""
        stripped = self.raw.replace(HOOK, "")
        fn = stripped[stripped.index("function OpexRoad1yRefleetSaved"):]
        fn = fn[:fn.index("\nif (ROAD1Y_EXTRA_STOPS > 0 || ROAD1Y_MAIL_ON_PAX)")]
        fn = re.sub(r"/\*[\s\S]*?\*/", "", fn)
        self.assertNotIn("AAA_FLEET", fn)
        self.assertNotIn("AaaFleet", fn)
        self.assertNotIn("road1yAaa", fn)


class AaaFleetModule(unittest.TestCase):
    def setUp(self):
        self.target = body(MODULE, "OpexRoad1yAaaFleetTarget")
        self.estimate = body(MODULE, "OpexRoad1yAaaFleetEstimate")

    def test_estimate_is_aaa_estimate_max_vehicles(self):
        for fragment in (
            "local days = distance * 664 / speed / 24;",
            "local byTime = days * 2 + 1;",
            "local byLength = (distance + 4) * 16 / 8;",
            "return (byTime < byLength ? byTime : byLength) + 2;",
            "AIMap.DistanceManhattan(line.stationA, line.stationB)",
            "(100 + AIEngine.GetReliability(engine)) / 200",
        ):
            self.assertIn(fragment, self.estimate)

    def test_add_rule_is_min_waiting_and_fewer_than_two_stopped_at_source(self):
        code = self.target
        for fragment in (
            "local minWait = waitingA < waitingB ? waitingA : waitingB;",
            "local bottom = capacity < 50 ? capacity : 50;",
            "local needs = count < 10 ? 30 : 100;",
            "if (minWait > needs && stoppedAtSource < 2 && capacity > 0) {",
            "want = (minWait - bottom) / capacity;",
            "if (want > 4) want = 4;",
            "if (want > line.road1yAaaCap - have) want = line.road1yAaaCap - have;",
            "OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, want)",
            "return have + want;",
        ):
            self.assertIn(fragment, code)
        self.assertIn("AIStation.GetStationID(AIVehicle.GetLocation(v)) == stationA", code)
        self.assertIn("AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION", code)

    def test_removal_rule_one_bus_per_month_sold_only_in_depot(self):
        code = self.target
        self.assertIn("if (count > 3 && minWait < bottom && stopped > 3 && lastStopped >= 0) {", code)
        self.assertEqual(code.count("AIVehicle.SendVehicleToDepot("), 1)
        self.assertEqual(code.count("AIVehicle.SellVehicle("), 1)
        sell_at = code.index("AIVehicle.SellVehicle(pending)")
        self.assertLess(code.index("AIVehicle.IsStoppedInDepot(pending)"), sell_at)
        # Monthly dedupe guards raise, removal and addition (sale is checked every pass).
        dedupe_at = code.index("if ((\"road1yAaaYm\" in line) && line.road1yAaaYm == ym) return have;")
        self.assertLess(sell_at, dedupe_at)
        for later in ("line.road1yAaaCap += step;", "AIVehicle.SendVehicleToDepot(", "want = (minWait - bottom)"):
            self.assertLess(dedupe_at, code.index(later), later)

    def test_cap_lowered_on_removal_and_raised_on_overflow(self):
        code = self.target
        self.assertIn("local lowered = (count < line.road1yAaaCap ? count : line.road1yAaaCap) - 1;", code)
        self.assertIn("ratingA < 40) || waitingA > 1000)", code)
        self.assertIn("local step = estimate / 12;", code)
        self.assertIn("if (line.road1yAaaCap > estimate) line.road1yAaaCap = estimate;", code)

    def test_decision_log_is_guarded(self):
        log = body(MODULE, "OpexRoad1yAaaFleetLog")
        self.assertTrue(log.split("{", 1)[1].lstrip().startswith("if (!DECISION_LOG) return;"))
        self.assertIn('OpexDecide("ROAD1Y_AAA_FLEET"', log)
        self.assertEqual(source(MODULE).count("OpexDecide("), 1)
        for action in ('"sell"', '"raise"', '"send"', '"add" : "state"'):
            self.assertIn(action, source(MODULE))

    def test_squirrel_traps_absent(self):
        code = re.sub(r"/\*[\s\S]*?\*/", "", source(MODULE))
        self.assertNotIn("function(", code)
        self.assertNotIn("const ", code)
        for word in ("clone", "base", "static", "delegate"):
            self.assertIsNone(re.search(r"\b" + word + r"\b", code), word)


class AaaFleetModel(unittest.TestCase):
    def test_estimate_grows_with_distance(self):
        previous = 0
        for distance in range(16, 200, 8):
            value = estimate(distance, 56)
            self.assertGreaterEqual(value, previous)
            previous = value
        self.assertEqual(estimate(100, 56), 101)

    def test_decisions_follow_aaa(self):
        # Drained weak end: AAA adds nothing even with stock at the strong end.
        self.assertEqual(decide(6, 31, 400, 20, 1, 0, 50), ("state", 0))
        # Both ends stocked: build (min - 31) / 31, at most 4.
        self.assertEqual(decide(6, 31, 400, 160, 0, 0, 50), ("add", 4))
        self.assertEqual(decide(6, 31, 400, 70, 0, 0, 50), ("add", 1))
        # Two buses already loading at the source: no addition.
        self.assertEqual(decide(6, 31, 400, 160, 2, 2, 50), ("state", 0))
        # Over ten buses the threshold becomes 100.
        self.assertEqual(decide(10, 31, 400, 90, 0, 0, 50), ("state", 0))
        # Drained line with more than three stopped buses: send one to the depot.
        self.assertEqual(decide(8, 31, 400, 10, 5, 4, 50), ("send", 0))
        # Never below three buses.
        self.assertEqual(decide(3, 31, 0, 0, 3, 3, 50)[0], "state")


if __name__ == "__main__":
    unittest.main()
