"""ROAD1Y truck_fleet : contrats statiques (ne compilent ni n'executent le Squirrel).

road1y_truck_fleet = 1 (0..1, defaut 0) remplace, pour les lignes de fret
routier en route seule, le plafond fixe ROAD1Y_FLEET x min(quais) de
OpexRoad1yRefleetSaved par la gestion de flotte d'AAAHogEx (route.nut) pour
une ligne unidirectionnelle : plafond EstimateMaxVehicles, ajout sur l'attente
a la source sans deux camions arretes en charge a la source, retrait des
camions arretes au-dela de trois quand la source est peu fournie. A 0 : aucun
appel, chemin historique inchange ; hors route seule, force a 0.
"""
import re
import unittest
from pathlib import Path

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
MODULE = "road1y_truck_fleet.nut"
HOOK = ('    if (ROAD1Y_TRUCK_FLEET && ("kind" in line) && line.kind == "freight")\n'
        '      target = OpexRoad1yTruckFleetTarget(line, have, capacity, waitingA, year);\n')


def estimate(distance, speed):
    """Modele Python d'EstimateMaxVehicles (AAAHogEx route.nut:2374-2380, quai route = 1 jour)."""
    speed = max(4, speed)
    days = distance * 664 // speed // 24
    return min(days * 2 + 1, (distance + 4) * 16 // 8) + 2


def decide(have, capacity, wait_a, stopped, stopped_src, cap):
    """Modele Python d'une decision mensuelle (sans vente en attente)."""
    bottom = min(50, capacity)
    if have > 3 and wait_a < bottom and stopped > 3:
        return "send", 0
    needs = 30 if have < 10 else 100
    want = 0
    if wait_a > needs and stopped_src < 2 and capacity > 0:
        want = max(0, min((wait_a - bottom) // capacity, 4, cap - have))
    return ("add" if want > 0 else "state"), want


class TruckFleetDeclaration(unittest.TestCase):
    def test_global_info_and_both_loaders(self):
        self.assertIn("ROAD1Y_TRUCK_FLEET <- 0;", source("globals_pre.nut"))
        block = source("info.nut").split('name = "road1y_truck_fleet",')[1].split("});")[0]
        self.assertIn("min_value = 0, max_value = 1", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            get_at = code.index('ROAD1Y_TRUCK_FLEET = AIController.GetSetting("road1y_truck_fleet");')
            bound_at = code.index("if (ROAD1Y_TRUCK_FLEET < 0 || ROAD1Y_TRUCK_FLEET > 1) ROAD1Y_TRUCK_FLEET = 0;")
            gate_at = code.index("if (!road1yRoadOnly) ROAD1Y_TRUCK_FLEET = 0;")
            self.assertLess(code.index("local road1yRoadOnly"), get_at, loader)
            self.assertLess(get_at, bound_at, loader)
            self.assertLess(bound_at, gate_at, loader)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertLess(bus.index("if (!road1yRoadOnly) ROAD1Y_TRUCK_FLEET = 0;"),
                        bus.index('require("bus_districts_overrides.nut")'))

    def test_global_used_only_by_loaders_and_the_hook(self):
        # String literals (the OpexDecide kind "ROAD1Y_TRUCK_FLEET") are not reads.
        def code(text):
            return re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        users = sorted(p.name for p in AI.glob("*.nut")
                       if "ROAD1Y_TRUCK_FLEET" in code(p.read_text(encoding="utf-8")))
        self.assertEqual(users, ["bus_districts_overrides.nut", "globals_pre.nut", "settings.nut"])
        self.assertNotIn("ROAD1Y_TRUCK_FLEET", code(source(MODULE)))

    def test_module_is_required_with_the_other_road1y_modules(self):
        main = source("main.nut")
        self.assertEqual(main.count('require("road1y_truck_fleet.nut");'), 1)
        self.assertLess(main.index('require("road1y_spread.nut");'),
                        main.index('require("road1y_truck_fleet.nut");'))
        self.assertLess(main.index('require("road1y_truck_fleet.nut");'),
                        main.index('require("opcode_exact.nut");'))


class TruckFleetHook(unittest.TestCase):
    def setUp(self):
        self.raw = source("bus_districts_overrides.nut")
        self.code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")

    def test_single_guarded_call_after_historical_rules_before_refleet(self):
        joined = "".join(p.read_text(encoding="utf-8") for p in AI.glob("*.nut"))
        self.assertEqual(joined.count("OpexRoad1yTruckFleetTarget("), 2)  # definition + hook
        self.assertEqual(self.raw.count(HOOK), 1)
        hook_at = self.code.index('if (ROAD1Y_TRUCK_FLEET && ("kind" in line) && line.kind == "freight")')
        self.assertLess(self.code.index("local road1yCap = fleetPerStop * road1yStops;"), hook_at)
        self.assertLess(hook_at, self.code.index("if (have >= target) {"))
        self.assertLess(hook_at, self.code.index("OpexRoadRefleet(this._catalog, line, have, target)"))

    def test_off_path_is_the_historical_refleet(self):
        """Removing the guarded hook (and its comment) leaves no truck_fleet token."""
        stripped = self.raw.replace(HOOK, "")
        fn = stripped[stripped.index("function OpexRoad1yRefleetSaved"):]
        fn = fn[:fn.index("\nif (ROAD1Y_EXTRA_STOPS > 0 || ROAD1Y_MAIL_ON_PAX)")]
        fn = re.sub(r"/\*[\s\S]*?\*/", "", fn)
        self.assertNotIn("TRUCK_FLEET", fn)
        self.assertNotIn("TruckFleet", fn)
        self.assertNotIn("road1yTruck", fn)


class TruckFleetModule(unittest.TestCase):
    def setUp(self):
        self.target = body(MODULE, "OpexRoad1yTruckFleetTarget")
        self.estimate = body(MODULE, "OpexRoad1yTruckFleetEstimate")

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

    def test_add_rule_is_source_waiting_and_fewer_than_two_stopped_at_source(self):
        code = self.target
        for fragment in (
            "local bottom = capacity < 50 ? capacity : 50;",
            "local needs = count < 10 ? 30 : 100;",
            "if (waitingA > needs && stoppedAtSource < 2 && capacity > 0) {",
            "want = (waitingA - bottom) / capacity;",
            "if (want > 4) want = 4;",
            "if (want > line.road1yTruckCap - have) want = line.road1yTruckCap - have;",
            "OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, want)",
            "return have + want;",
        ):
            self.assertIn(fragment, code)
        self.assertIn("AIStation.GetStationID(AIVehicle.GetLocation(v)) == stationA", code)
        self.assertIn("AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION", code)
        # Unidirectional: the destination stock never drives the fleet.
        self.assertNotIn("waitingB", code)

    def test_removal_rule_one_truck_per_month_sold_only_in_depot(self):
        code = self.target
        self.assertIn("if (count > 3 && waitingA < bottom && stopped > 3 && lastStopped >= 0) {", code)
        self.assertEqual(code.count("AIVehicle.SendVehicleToDepot("), 1)
        self.assertEqual(code.count("AIVehicle.SellVehicle("), 1)
        sell_at = code.index("AIVehicle.SellVehicle(pending)")
        self.assertLess(code.index("AIVehicle.IsStoppedInDepot(pending)"), sell_at)
        dedupe_at = code.index('if (("road1yTruckYm" in line) && line.road1yTruckYm == ym) return have;')
        self.assertLess(sell_at, dedupe_at)
        for later in ("line.road1yTruckCap += step;", "AIVehicle.SendVehicleToDepot(", "want = (waitingA - bottom)"):
            self.assertLess(dedupe_at, code.index(later), later)

    def test_cap_lowered_on_removal_and_raised_on_overflow(self):
        code = self.target
        self.assertIn("local lowered = (count < line.road1yTruckCap ? count : line.road1yTruckCap) - 1;", code)
        self.assertIn("ratingA < 40) || waitingA > 1000)", code)
        self.assertIn("local step = estimate / 12;", code)
        self.assertIn("if (line.road1yTruckCap > estimate) line.road1yTruckCap = estimate;", code)

    def test_decision_log_is_guarded(self):
        log = body(MODULE, "OpexRoad1yTruckFleetLog")
        self.assertTrue(log.split("{", 1)[1].lstrip().startswith("if (!DECISION_LOG) return;"))
        self.assertIn('OpexDecide("ROAD1Y_TRUCK_FLEET"', log)
        self.assertEqual(source(MODULE).count("OpexDecide("), 1)
        for action in ('"sell"', '"raise"', '"send"', '"add" : "state"'):
            self.assertIn(action, source(MODULE))

    def test_squirrel_traps_absent(self):
        code = re.sub(r"/\*[\s\S]*?\*/", "", source(MODULE))
        self.assertNotIn("function(", code)
        self.assertNotIn("const ", code)
        for word in ("clone", "base", "static", "delegate"):
            self.assertIsNone(re.search(r"\b" + word + r"\b", code), word)


class TruckFleetModel(unittest.TestCase):
    def test_estimate_grows_with_distance(self):
        previous = 0
        for distance in range(16, 200, 8):
            value = estimate(distance, 48)
            self.assertGreaterEqual(value, previous)
            previous = value
        # A 60-tile coal line with 48 km/h trucks: AAA allows about 70 trucks.
        self.assertEqual(estimate(60, 48), 71)

    def test_decisions_follow_aaa(self):
        # Coal piling at the source: build (wait - 20) / 20, at most 4.
        self.assertEqual(decide(4, 20, 400, 0, 0, 70), ("add", 4))
        self.assertEqual(decide(4, 20, 70, 0, 0, 70), ("add", 2))
        # Two trucks already loading at the source: no addition.
        self.assertEqual(decide(4, 20, 400, 2, 2, 70), ("state", 0))
        # Over ten trucks the threshold becomes 100.
        self.assertEqual(decide(10, 20, 90, 0, 0, 70), ("state", 0))
        # Cap reached.
        self.assertEqual(decide(70, 20, 400, 0, 0, 70), ("state", 0))
        # Drained source with more than three stopped trucks: send one to the depot.
        self.assertEqual(decide(8, 20, 10, 5, 4, 70), ("send", 0))
        # Never below three trucks.
        self.assertEqual(decide(3, 20, 0, 3, 3, 70)[0], "state")


if __name__ == "__main__":
    unittest.main()
